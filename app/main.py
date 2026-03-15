
# app/main.py
from fastapi import FastAPI, Request, Response
import httpx
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Get credentials from .env
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# Create FastAPI app
app = FastAPI()

# ─────────────────────────────────
# 1. HEALTH CHECK
# Visit your URL to see if bot lives!
# ─────────────────────────────────
@app.get("/")
async def home():
    return {"status": "KisanKiSamasya Bot is LIVE! 🌾"}


# ─────────────────────────────────
# 2. WEBHOOK VERIFY
# Meta checks if your server is real
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
# 3. RECEIVE MESSAGES
# Every WhatsApp message comes here!
# ─────────────────────────────────
@app.post("/webhook")
async def receive_message(request: Request):
    body = await request.json()
    print(f"📩 Message received: {body}")
    
    try:
        # Get message details
        message = (body["entry"][0]["changes"][0]
                  ["value"]["messages"][0])
        
        from_number = message["from"]
        message_type = message["type"]
        
        # Text message received
        if message_type == "text":
            text = message["text"]["body"]
            print(f"💬 Text from {from_number}: {text}")
            
            # Send reply!
            await send_reply(from_number, text)
    
    except Exception as e:
        print(f"Error: {e}")
    
    return {"status": "ok"}


# ─────────────────────────────────
# 4. SEND REPLY
# This sends message back to farmer!
# ─────────────────────────────────
async def send_reply(phone: str, received_text: str):
    
    # Decide what to reply
    reply = get_response(received_text)
    
    # Send via WhatsApp API
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": reply}
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url, 
            json=payload, 
            headers=headers
        )
        print(f"📤 Reply sent! Status: {response.status_code}")


# ─────────────────────────────────
# 5. BOT BRAIN
# Simple responses for now
# We add AI later!
# ─────────────────────────────────
def get_response(text: str) -> str:
    text = text.lower().strip()
    
    # Greetings
    if any(word in text for word in 
           ["hi", "hello", "नमस्ते", "हेलो", "start"]):
        return (
            "🌾 नमस्ते किसान भाई!\n\n"
            "मैं KisanKiSamasya हूं!\n"
            "आपकी खेती की समस्याओं का समाधान!\n\n"
            "आप पूछ सकते हैं:\n"
            "1️⃣ मंडी भाव\n"
            "2️⃣ फसल सलाह\n"
            "3️⃣ मौसम\n\n"
            "क्या जानना है? 😊"
        )
    
    # Mandi price
    elif any(word in text for word in 
             ["भाव", "price", "मंडी", "rate", "bhav"]):
        return (
            "📊 आज के मंडी भाव:\n\n"
            "🍅 टमाटर: ₹1200/क्विंटल\n"
            "🧅 प्याज: ₹900/क्विंटल\n"
            "🥔 आलू: ₹800/क्विंटल\n"
            "🌾 गेहूं: ₹2200/क्विंटल\n\n"
            "किस फसल का भाव चाहिए?\n"
            "नाम लिखें! 😊"
        )
    
    # Weather
    elif any(word in text for word in 
             ["मौसम", "weather", "बारिश", "rain"]):
        return (
            "🌤️ आज का मौसम:\n\n"
            "तापमान: 28-32°C\n"
            "हवा: सामान्य\n"
            "बारिश: संभावना 20%\n\n"
            "खेती के लिए अच्छा दिन! ✅"
        )
    
    # Crop advice
    elif any(word in text for word in 
             ["फसल", "crop", "सलाह", "advice", "खेती"]):
        return (
            "🌱 फसल सलाह:\n\n"
            "अभी बोने के लिए अच्छी फसलें:\n"
            "✅ टमाटर\n"
            "✅ प्याज\n"
            "✅ मक्का\n\n"
            "किस फसल की सलाह चाहिए?\n"
            "फसल का नाम लिखें! 😊"
        )
    
    # Default response
    else:
        return (
            "🌾 KisanKiSamasya में आपका स्वागत!\n\n"
            "मैं समझ नहीं पाया।\n"
            "कृपया ये लिखें:\n\n"
            "➡️ मंडी भाव\n"
            "➡️ फसल सलाह\n"
            "➡️ मौसम\n\n"
            "या 'Hi' टाइप करें! 😊"
        )