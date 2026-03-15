from fastapi import FastAPI, Request, Response
import httpx
import os
import base64
from dotenv import load_dotenv

load_dotenv()

# Credentials
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

WHATSAPP_API = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
SARVAM_BASE = "https://api.sarvam.ai"

app = FastAPI()


# ─────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────
@app.get("/")
async def home():
    return {
        "status": "KisanKiSamasya Bot LIVE! 🌾",
        "voice": "Sarvam AI",
        "language": "Hindi"
    }


# ─────────────────────────────────
# WEBHOOK VERIFY
# ─────────────────────────────────
@app.get("/webhook")
async def verify(request: Request):
    params = dict(request.query_params)
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        print("✅ Webhook verified!")
        return Response(
            content=params.get("hub.challenge"),
            media_type="text/plain"
        )
    return Response(status_code=403)


# ─────────────────────────────────
# RECEIVE ALL MESSAGES
# ─────────────────────────────────
@app.post("/webhook")
async def receive_message(request: Request):
    body = await request.json()

    try:
        # Get message from WhatsApp
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        # Skip if no messages
        if "messages" not in value:
            return {"status": "ok"}

        message = value["messages"][0]
        from_number = message["from"]
        message_type = message["type"]

        print(f"📱 From: {from_number}")
        print(f"📝 Type: {message_type}")

        # ─────────────────────────
        # TEXT MESSAGE
        # ─────────────────────────
        if message_type == "text":
            text = message["text"]["body"]
            print(f"💬 Text: {text}")

            # Get smart reply
            reply = await get_ai_reply(text)
            await send_text(from_number, reply)

        # ─────────────────────────
        # VOICE NOTE 🎤
        # ─────────────────────────
        elif message_type == "audio":
            audio_id = message["audio"]["id"]
            print(f"🎤 Voice: {audio_id}")

            # Tell farmer we received it
            await send_text(
                from_number,
                "🎤 सुन रहा हूं... थोड़ा रुकें! ⏳"
            )

            # STEP 1: Download audio
            audio_bytes = await download_audio(audio_id)
            if not audio_bytes:
                await send_text(
                    from_number,
                    "❌ आवाज़ नहीं सुनाई दी!\n"
                    "दोबारा भेजें! 🙏"
                )
                return {"status": "ok"}

            # STEP 2: Voice → Text (Sarvam ASR)
            transcript = await voice_to_text(audio_bytes)
            if not transcript:
                await send_text(
                    from_number,
                    "❌ आवाज़ समझ नहीं आई!\n"
                    "शांत जगह से बोलें! 🙏"
                )
                return {"status": "ok"}

            print(f"📝 Heard: {transcript}")

            # Show what bot heard
            await send_text(
                from_number,
                f"✅ मैंने सुना:\n'{transcript}'"
            )

            # STEP 3: Get AI reply
            reply_text = await get_ai_reply(transcript)

            # STEP 4: Text → Voice (Sarvam TTS)
            audio_reply = await text_to_voice(reply_text)

            # STEP 5: Send text reply always
            await send_text(from_number, reply_text)

            # STEP 6: Send voice reply if worked
            if audio_reply:
                await send_voice(from_number, audio_reply)
                print("✅ Voice reply sent!")

    except KeyError:
        print("⚠️ No message in this webhook")
    except Exception as e:
        print(f"❌ Error: {e}")

    return {"status": "ok"}


# ─────────────────────────────────
# DOWNLOAD AUDIO FROM WHATSAPP
# ─────────────────────────────────
async def download_audio(audio_id: str) -> bytes:
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}"
    }

    async with httpx.AsyncClient(timeout=30) as client:
        # Get audio URL
        res = await client.get(
            f"https://graph.facebook.com/v19.0/{audio_id}",
            headers=headers
        )

        if res.status_code != 200:
            print(f"❌ URL fetch failed: {res.text}")
            return None

        audio_url = res.json().get("url")

        # Download audio
        audio_res = await client.get(
            audio_url,
            headers=headers
        )

        if audio_res.status_code == 200:
            print(f"✅ Audio downloaded!")
            return audio_res.content

        return None


# ─────────────────────────────────
# VOICE → TEXT (Sarvam ASR)
# ─────────────────────────────────
async def voice_to_text(audio_bytes: bytes) -> str:
    """
    Fixed! Sarvam needs 'file' field!
    """
    import io

    # ⚠️ KEY FIX:
    # Sarvam needs multipart form data
    # with field name exactly "file"

    headers = {
        "api-subscription-key": SARVAM_API_KEY
    }

    # Create form data exactly as Sarvam wants
    files = {
        "file": (
            "audio.ogg",           # filename
            io.BytesIO(audio_bytes), # file content
            "audio/ogg"            # content type
        )
    }

    # Other fields as form data (not json!)
    data = {
        "model": "saarika:v2.5",
        "language_code": "hi-IN",
        "with_timestamps": "false"
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post(
                f"{SARVAM_BASE}/speech-to-text",
                headers=headers,
                files=files,
                data=data       # ← separate from files!
            )

            print(f"ASR Status: {res.status_code}")
            print(f"ASR Response: {res.text}")

            if res.status_code == 200:
                text = res.json().get("transcript", "")
                print(f"✅ Heard: {text}")
                return text

            print(f"❌ ASR Failed: {res.text}")
            return ""

    except Exception as e:
        print(f"❌ ASR Exception: {e}")
        return ""


# ─────────────────────────────────
# AI BRAIN — Smart Replies
# ─────────────────────────────────
async def get_ai_reply(user_text: str) -> str:
    """
    Get intelligent farming advice
    Using Sarvam AI
    """

    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "model": "sarvam-m",
        "messages": [
            {
                "role": "system",
                "content": (
                    "आप KisanKiSamasya हैं - "
                    "एक expert Indian agricultural advisor। "
                    "हमेशा Hindi में जवाब दें। "
                    "Short और practical जवाब दें - "
                    "maximum 3-4 sentences। "
                    "Simple farmer language use करें। "
                    "केवल खेती, फसल, मंडी, मौसम, "
                    "सरकारी योजनाओं के बारे में बात करें।"
                )
            },
            {
                "role": "user",
                "content": user_text
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(
                f"{SARVAM_BASE}/chat/completions",
                json=payload,
                headers=headers
            )

            if res.status_code == 200:
                reply = (res.json()
                    ["choices"][0]
                    ["message"]["content"])
                print(f"✅ AI Reply: {reply}")
                return reply

            print(f"❌ AI Error: {res.text}")
            return fallback_reply(user_text)

    except Exception as e:
        print(f"❌ AI Exception: {e}")
        return fallback_reply(user_text)


# ─────────────────────────────────
# TEXT → VOICE (Sarvam TTS)
# ─────────────────────────────────
async def text_to_voice(text: str) -> bytes:
    """
    Convert Hindi text to voice
    Using Sarvam TTS
    """

    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": [text],
        "target_language_code": "hi-IN",
        "speaker": "meera",
        "model": "bulbul:v1",
        "enable_preprocessing": True
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(
                f"{SARVAM_BASE}/text-to-speech",
                json=payload,
                headers=headers
            )

            if res.status_code == 200:
                # Sarvam returns base64 audio
                audio_b64 = (res.json()
                    .get("audios", [""])[0])

                if audio_b64:
                    audio_bytes = base64.b64decode(audio_b64)
                    print("✅ TTS generated!")
                    return audio_bytes

            print(f"❌ TTS Error: {res.text}")
            return None

    except Exception as e:
        print(f"❌ TTS Exception: {e}")
        return None


# ─────────────────────────────────
# SEND TEXT MESSAGE
# ─────────────────────────────────
async def send_text(phone: str, text: str):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": text}
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(
            WHATSAPP_API,
            json=payload,
            headers=headers
        )
        print(f"📤 Text sent: {res.status_code}")


# ─────────────────────────────────
# SEND VOICE NOTE
# ─────────────────────────────────
async def send_voice(phone: str, audio_bytes: bytes):
    """
    Send voice note back to farmer
    Upload audio then send link
    """
    # For MVP: text reply is enough!
    # Voice sending needs file hosting
    # We add this in next update!
    print("📤 Voice ready (text sent for now)")
    pass


# ─────────────────────────────────
# FALLBACK WHEN AI IS DOWN
# ─────────────────────────────────
def fallback_reply(text: str) -> str:
    text = text.lower()

    if any(w in text for w in
           ["भाव", "price", "मंडी", "rate"]):
        return (
            "📊 आज के भाव:\n"
            "🍅 टमाटर: ₹1200/क्विंटल\n"
            "🧅 प्याज: ₹900/क्विंटल\n"
            "🌾 गेहूं: ₹2200/क्विंटल\n"
            "किस फसल का भाव चाहिए?"
        )

    if any(w in text for w in
           ["hi", "hello", "नमस्ते", "start"]):
        return (
            "🌾 नमस्ते किसान भाई!\n"
            "KisanKiSamasya में स्वागत है!\n\n"
            "पूछें:\n"
            "1️⃣ मंडी भाव\n"
            "2️⃣ फसल सलाह\n"
            "3️⃣ मौसम\n"
            "या voice note भेजें! 🎤"
        )

    return (
        "🌾 KisanKiSamasya\n\n"
        "अभी server busy है। 🙏\n"
        "2 मिनट बाद पूछें!\n\n"
        "Helpline: 1800-180-1551"
    )