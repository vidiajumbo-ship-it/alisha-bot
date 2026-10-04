import os
import time
import re
import json
from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types

app = Flask(__name__)

# Environment Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ADMIN_PHONE = os.environ.get("ADMIN_PHONE", "")  # e.g., "whatsapp:+91XXXXXXXXXX"

client = genai.Client(api_key=GEMINI_API_KEY)

# ----------------- PERSISTENT DATA LAYER (JSON) -----------------
DATA_FILE = "bot_data.json"

def load_data():
    default_data = {
        "monthly_sale": 0,
        "monthly_expense": 0,
        "stopped_items": []
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return default_data
    return default_data

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Initialize data
store = load_data()

# ----------------- PROMPT TEMPLATE -----------------
ALISHA_RULES_TEMPLATE = (
    "You are Alisha, the ultra-smart, polite, and professional female host for 'Eat & Park Restaurant' located at Girja More, Ara. "
    "Greet customers beautifully with emojis. Speak in simple, attractive Hinglish (Hindi in English script).\n\n"
    
    "📌 OFFICIAL EAT & PARK MENU & PRICES:\n"
    "- DRINKS & SHAKES: Mint Mojito (₹90), Blue Lagoon (₹90), Shakes (Vanilla/Strawberry/Mango/Butterscotch ₹120, Chocolate ₹130, Kitkat Oreo ₹150), Cold Coffee (₹120), Cold Drink (₹50), Tea (₹30), Coffee (₹50).\n"
    "- FAST FOOD: Veg Burger (₹90), Eat & Park Special Pizza (₹280), Veg Roll (₹90), Paneer Roll (₹100), Veg Cheese Roll (₹120), Paneer Tikka Roll (₹160), Egg Roll (₹100), Chicken Roll (₹150), Veg Pasta (₹150), White Sauce Pasta (₹180), Red Sauce Pasta (₹170), Mix Sauce Pasta (₹200), Veg Sandwich (₹120), Chicken Sandwich (₹150).\n"
    "- MOMOS: Veg Momo (₹80-₹150), Paneer Momo (₹100-₹170), Chicken Momo (₹150-₹200).\n"
    "- CHINESE STARTER: Paneer Chilli (₹240), Mushroom Chilli (₹250), Veg Manchurian (₹180), Chicken Chilli (₹240), Chicken Lollipop (₹300).\n"
    "- CHINESE MAIN COURSE: Veg Chowmein (₹130), Veg Hakka Noodles (₹160), Paneer Noodles (₹180), Chicken Noodles (₹180), Fried Rice (Veg ₹170, Paneer ₹200, Egg ₹180, Chicken ₹200).\n"
    "- INDIAN MAIN COURSE (Veg): Paneer Masala (₹250), Paneer Butter Masala (₹260), Mushroom Masala (₹250), Mix Veg (₹180).\n"
    "- INDIAN MAIN COURSE (Non-Veg): Chicken Dehati (₹550), Chicken Curry (₹280), Chicken Handi (₹290), Mutton Dehati (₹440), Mutton Handi (₹650/₹1200), Egg Curry (4pc-₹200).\n"
    "- BIRYANI: Veg Biryani (₹180), Paneer Biryani (₹200), Chicken Biryani (₹210), Chicken Leg Spl. Biryani (₹350), Mutton Biryani (₹280).\n"
    "- THALIS: Veg Thali (₹250), Non Veg Thali (₹280).\n"
    "- BREADS & DAL: Tandoori Roti (₹15), Tandoori Butter Roti (₹20), Butter Naan (₹60), Laccha Paratha (₹50), Dal Tadka (₹100).\n\n"
    
    "🎁 EXACT MENU-BASED COMBO DEALS:\n"
    "1. 🍜 CHINESE COMBO: Veg Noodles (₹130) + Paneer Chilli (₹240) -> Alag se ₹370, par Combo me sirf ₹320/-! 🔥\n"
    "2. 🍔 BURGER COMBO: Veg Burger (₹90) + French Fries (₹100) + Cold Drink (₹50) -> Alag se ₹240, par Combo me sirf ₹210/-! 🍟\n"
    "3. 🍗 BIRYANI COMBO: Chicken Biryani (₹210) + Mint Mojito (₹90) -> Alag se ₹300, par Combo me sirf ₹260/-! 🍹\n\n"
    
    "⚠️ CRITICAL STATUS (📌 ITEM NOT AVAILABLE TODAY):\n"
    "The following items are OUT OF STOCK today: {stopped_list_text}. If a customer asks for any of these items, politely tell them that it is finished for today, and smartly suggest an alternative item that is available from the menu.\n\n"
    
    "⚠️ AI SMART RULES FOR ALISHA:\n"
    "RULE 1: (Smart Cross-Selling) Jab bhi koi customer kuch pooche, price batane ke baad upar se match hoti hui koi Drink/Shake khud se suggest karo.\n"
    "RULE 2: (Combo Suggestion) Offer maangne par 3 Calculated WhatsApp Combos savings ke saath dikhao.\n"
    "RULE 3: Order ya Table booking ke liye bolna ki hamare helpline numbers par call/WhatsApp karein: 📞 8271918062 ya 📞 7303267750.\n"
    "RULE 4: Hamesha polite rehna hai aur ek baar me saara menu nahi bhejoge."
)

# ----------------- PARSING LOGIC -----------------
def parse_admin_record(text):
    global store
    try:
        clean_text = text.split(":", 1)[1].strip() if ":" in text else text
        entries = [item.strip() for item in clean_text.split(",") if item.strip()]

        sale = 0
        total_expense = 0

        for entry in entries:
            match = re.match(r"([a-zA-Z\s&]+)\s+(\d+)", entry)
            if match:
                key = match.group(1).strip().lower()
                amount = int(match.group(2))

                if "sale" in key:
                    sale += amount
                else:
                    total_expense += amount

        store["monthly_sale"] += sale
        store["monthly_expense"] += total_expense
        save_data(store)

        profit = sale - total_expense
        return (
            f"📝 **Eat & Park - Daily Hisaab-Kitab**\n\n"
            f"💰 Today's Sale: ₹{sale:,}\n"
            f"💸 Today's Expense: ₹{total_expense:,}\n"
            f"📊 Today's Profit: ₹{profit:,}\n\n"
            f"✅ Aaj ka record save ho gaya aur Monthly Report me jod diya gaya hai!"
        )
    except Exception:
        return "Format galat hai! Is format me bhejein:\n`Add Record: Sale 15000, Chicken 1800, Sabji 600`"

# ----------------- ROUTES -----------------
@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    global store
    resp = MessagingResponse()
    
    try:
        user_msg = request.values.get('Body', '').strip()
        sender = request.values.get('From', '')
        user_msg_lower = user_msg.lower()

        # Optional phone validation (leave blank in env to disable)
        is_admin = not ADMIN_PHONE or sender == ADMIN_PHONE

        # 1. ADMIN: DAILY HISAAB
        if is_admin and user_msg_lower.startswith("add record"):
            ai_reply = parse_admin_record(user_msg)

        # 2. ADMIN: MONTHLY REPORT
        elif is_admin and user_msg_lower == "/report":
            net_profit = store["monthly_sale"] - store["monthly_expense"]
            ai_reply = (
                f"📊 **Eat & Park - Monthly Business Report**\n\n"
                f"💰 Total Monthly Sale: ₹{store['monthly_sale']:,}\n"
                f"💸 Total Monthly Expense: ₹{store['monthly_expense']:,}\n"
                f"📈 Net Monthly Profit (Kamai): ₹{net_profit:,}\n\n"
                f"💼 Keep crushing it! Rocket Business! 🚀"
            )

        # 3. ADMIN: STOP ITEM
        elif is_admin and user_msg_lower.startswith("/stop "):
            item = user_msg[6:].strip()
            if item and item not in store["stopped_items"]:
                store["stopped_items"].append(item)
                save_data(store)
            ai_reply = f"🚫 Mode Updated: Alisha ab customers ko **{item}** finished batayegi."

        # 4. ADMIN: START ITEM
        elif is_admin and user_msg_lower.startswith("/start "):
            item = user_msg[7:].strip()
            if item in store["stopped_items"]:
                store["stopped_items"].remove(item)
                save_data(store)
            ai_reply = f"✅ Mode Updated: **{item}** wapas menu me live ho gaya hai!"

        # 5. CUSTOMER MODE (AI RESPONSE)
        else:
            stopped_text = ", ".join(store["stopped_items"]) if store["stopped_items"] else "None (All available)"
            dynamic_rules = ALISHA_RULES_TEMPLATE.format(stopped_list_text=stopped_text)
            
            ai_reply = "Namaste! Eat & Park me aapka swagat hai. Humara server abhi busy hai, kripya thodi der me koshish karein."

            for attempt in range(3):
                try:
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=user_msg,
                        config=types.GenerateContentConfig(
                            system_instruction=dynamic_rules
                        ),
                    )
                    if response.text:
                        ai_reply = response.text.strip()
                    break
                except Exception as err:
                    time.sleep(1.5)

    except Exception as e:
        ai_reply = "System technical update me hai, kripya direct call karein: 📞 8271918062"

    resp.message(ai_reply)
    return Response(str(resp), mimetype="application/xml")

@app.route("/", methods=['GET'])
def home():
    return "Eat & Park Alisha Management Bot is running smoothly!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
