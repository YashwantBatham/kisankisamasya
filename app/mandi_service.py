import httpx
import os

MANDI_API_KEY = os.getenv(
    "MANDI_API_KEY",
    "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"
)

MANDI_API_URL = (
    "https://api.data.gov.in/resource/"
    "35985678-0d79-46b4-9ed6-6f13308a1d24"
)

# ─────────────────────────────────
# CROP NAMES HINDI → ENGLISH
# ─────────────────────────────────
CROP_NAMES = {
    "टमाटर": "Tomato",
    "tamatar": "Tomato",
    "tomato": "Tomato",
    "प्याज": "Onion",
    "pyaj": "Onion",
    "onion": "Onion",
    "आलू": "Potato",
    "aalu": "Potato",
    "aloo": "Potato",
    "potato": "Potato",
    "लहसुन": "Garlic",
    "lahsun": "Garlic",
    "garlic": "Garlic",
    "अदरक": "Ginger",
    "adrak": "Ginger",
    "ginger": "Ginger",
    "बैंगन": "Brinjal",
    "baingan": "Brinjal",
    "गोभी": "Cauliflower",
    "gobhi": "Cauliflower",
    "फूलगोभी": "Cauliflower",
    "भिंडी": "Bhindi",
    "bhindi": "Bhindi",
    "मिर्च": "Chilly",
    "mirch": "Chilly",
    "हरी मिर्च": "Green Chilly",
    "गेहूं": "Wheat",
    "gehun": "Wheat",
    "wheat": "Wheat",
    "धान": "Paddy",
    "dhan": "Paddy",
    "rice": "Paddy",
    "chawal": "Paddy",
    "चावल": "Paddy",
    "मक्का": "Maize",
    "makka": "Maize",
    "corn": "Maize",
    "ज्वार": "Jowar",
    "jowar": "Jowar",
    "बाजरा": "Bajra",
    "bajra": "Bajra",
    "चना": "Gram",
    "chana": "Gram",
    "gram": "Gram",
    "मूंग": "Moong",
    "moong": "Moong",
    "उड़द": "Urad",
    "urad": "Urad",
    "कपास": "Cotton",
    "kapas": "Cotton",
    "cotton": "Cotton",
    "सोयाबीन": "Soyabean",
    "soybean": "Soyabean",
    "soyabean": "Soyabean",
    "मूंगफली": "Groundnut",
    "moongfali": "Groundnut",
    "groundnut": "Groundnut",
    "सरसों": "Mustard",
    "sarson": "Mustard",
    "mustard": "Mustard",
    "गन्ना": "Sugarcane",
    "ganna": "Sugarcane",
    "केला": "Banana",
    "kela": "Banana",
    "banana": "Banana",
    "अनार": "Pomegranate",
    "anar": "Pomegranate",
    "आम": "Mango",
    "aam": "Mango",
    "mango": "Mango",
}

# ─────────────────────────────────
# STATE NAMES HINDI → ENGLISH
# ─────────────────────────────────
STATE_NAMES = {
    "महाराष्ट्र": "Maharashtra",
    "maharashtra": "Maharashtra",
    "उत्तर प्रदेश": "Uttar Pradesh",
    "up": "Uttar Pradesh",
    "मध्य प्रदेश": "Madhya Pradesh",
    "mp": "Madhya Pradesh",
    "राजस्थान": "Rajasthan",
    "rajasthan": "Rajasthan",
    "गुजरात": "Gujarat",
    "gujarat": "Gujarat",
    "पंजाब": "Punjab",
    "punjab": "Punjab",
    "हरियाणा": "Haryana",
    "haryana": "Haryana",
    "कर्नाटक": "Karnataka",
    "karnataka": "Karnataka",
    "बिहार": "Bihar",
    "bihar": "Bihar",
    "दिल्ली": "Delhi",
    "delhi": "Delhi",
    "तेलंगाना": "Telangana",
    "telangana": "Telangana",
}


def detect_crop(user_text: str) -> str:
    """Find crop in user message"""
    text = user_text.lower()
    for name, english in CROP_NAMES.items():
        if name in text:
            return english
    return ""


def detect_state(user_text: str) -> str:
    """Find state in user message"""
    text = user_text.lower()
    for name, english in STATE_NAMES.items():
        if name in text:
            return english
    return ""


def get_hindi_name(english: str) -> str:
    """Get Hindi name for crop"""
    for hindi, eng in CROP_NAMES.items():
        if eng == english:
            if any('\u0900' <= c <= '\u097f'
                   for c in hindi):
                return hindi
    return english


async def get_live_mandi_prices(
    crop: str,
    state: str = ""
) -> str:

    # Get today's date in correct format
    from datetime import datetime, timedelta
    
    today = datetime.now()
    
    # Try today first
    # Format: dd-MM-yyyy (API format)
    today_str = today.strftime("%d-%m-%Y")
    
    print(f"🌐 Fetching: {crop} | {state} | {today_str}")

    params = {
        "api-key": MANDI_API_KEY,
        "format": "json",
        "limit": "10",
        "filters[Commodity]": crop,
        "filters[Arrival_Date]": today_str
    }

    if state:
        params["filters[State]"] = state

    try:
        async with httpx.AsyncClient(
            timeout=30
        ) as client:

            res = await client.get(
                MANDI_API_URL,
                params=params
            )

            print(f"📡 Status: {res.status_code}")

            if res.status_code == 200:
                data = res.json()
                records = data.get("records", [])

                print(f"✅ Today records: {len(records)}")

                # If no today data, try yesterday
                if not records:
                    yesterday = today - timedelta(days=1)
                    yesterday_str = yesterday.strftime(
                        "%d-%m-%Y"
                    )
                    print(f"🔄 Trying yesterday: {yesterday_str}")
                    
                    params["filters[Arrival_Date]"] = yesterday_str
                    
                    res2 = await client.get(
                        MANDI_API_URL,
                        params=params
                    )
                    
                    if res2.status_code == 200:
                        data2 = res2.json()
                        records = data2.get("records", [])
                        print(f"✅ Yesterday records: {len(records)}")

                # Still no data - try without date
                if not records:
                    print("🔄 Trying without date filter...")
                    del params["filters[Arrival_Date]"]
                    
                    res3 = await client.get(
                        MANDI_API_URL,
                        params=params
                    )
                    
                    if res3.status_code == 200:
                        data3 = res3.json()
                        records = data3.get("records", [])

                if not records:
                    return ask_for_state(crop)

                return format_prices(crop, records)

            return fallback_prices(crop)

    except Exception as e:
        print(f"❌ Error: {e}")
        return fallback_prices(crop)


def ask_for_state(crop: str) -> str:
    """Ask farmer to specify state"""
    hindi = get_hindi_name(crop)
    return (
        f"📊 {hindi} का भाव जानने के लिए\n"
        f"राज्य का नाम बताएं!\n\n"
        f"जैसे लिखें:\n"
        f"• महाराष्ट्र में {hindi}\n"
        f"• उत्तर प्रदेश में {hindi}\n"
        f"• मध्य प्रदेश में {hindi}\n"
        f"• राजस्थान में {hindi}\n"
        f"• गुजरात में {hindi}\n\n"
        f"राज्य बताएं! 😊"
    )


def format_prices(crop: str, records: list) -> str:

    hindi = get_hindi_name(crop)
    
    # Get date from first record
    first_date = records[0].get(
        "Arrival_Date", ""
    ) if records else ""

    msg = f"📊 *{hindi} के भाव*\n"
    
    if first_date:
        msg += f"📅 दिनांक: {first_date}\n"
    
    msg += "━━━━━━━━━━━━━━\n\n"

    for r in records[:3]:

        state = r.get("State", "")
        district = r.get("District", "")
        market = r.get("Market", "")
        min_p = r.get("Min_Price", "N/A")
        max_p = r.get("Max_Price", "N/A")
        modal_p = r.get("Modal_Price", "N/A")
        variety = r.get("Variety", "")

        msg += f"🏪 {market}\n"
        msg += f"📍 {district}, {state}\n"
        if variety and variety != crop:
            msg += f"🌱 किस्म: {variety}\n"
        msg += f"💰 न्यूनतम: ₹{min_p}/क्विंटल\n"
        msg += f"💰 अधिकतम: ₹{max_p}/क्विंटल\n"
        msg += f"💰 औसत: ₹{modal_p}/क्विंटल\n\n"

    msg += "━━━━━━━━━━━━━━\n"
    msg += "📡 स्रोत: भारत सरकार 🇮🇳"

    return msg


def no_data_msg(crop: str) -> str:
    hindi = get_hindi_name(crop)
    return (
        f"❌ {hindi} का डेटा\n"
        f"अभी available नहीं।\n\n"
        f"राज्य का नाम भी बताएं:\n"
        f"जैसे: महाराष्ट्र में टमाटर\n\n"
        f"या देखें: enam.trade.gov.in"
    )


def fallback_prices(crop: str) -> str:
    hindi = get_hindi_name(crop)
    prices = {
        "Tomato": ("800-1400", "1100"),
        "Onion": ("600-1200", "900"),
        "Potato": ("500-900", "700"),
        "Wheat": ("2100-2300", "2200"),
        "Paddy": ("1900-2200", "2050"),
        "Maize": ("1500-1800", "1650"),
        "Soyabean": ("3800-4200", "4000"),
        "Mustard": ("4500-5000", "4750"),
        "Cotton": ("5500-6500", "6000"),
        "Gram": ("4500-5200", "4850"),
    }

    p = prices.get(crop)
    if p:
        return (
            f"📊 {hindi} अनुमानित भाव:\n\n"
            f"💰 रेंज: ₹{p[0]}/क्विंटल\n"
            f"💰 औसत: ₹{p[1]}/क्विंटल\n\n"
            f"⚠️ सटीक भाव के लिए\n"
            f"दोबारा पूछें! 🙏"
        )

    return (
        "❌ सर्वर busy है।\n"
        "2 मिनट बाद पूछें! 🙏"
    )