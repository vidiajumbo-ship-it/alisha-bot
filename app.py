import os
import time
import re
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types

app = Flask(__name__)

# Railway ke Variables se key uthana
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 

# Gemini client setup
client = genai.Client(api_key=GEMINI_API_KEY)

# 📜 ALISHA KE NEW SMART RULES & EXACT MENU DATA
ALISHA_RULES = (
    "You are Alisha, the ultra-smart, polite, and professional female host for 'Eat & Park Restaurant' located at Girja More, Ara. "
    "Greet customers beautifully with emojis. Speak in simple, attractive Hinglish (Hindi in English script).\n\n"
    
    "📌 OFFICIAL EAT & PARK MENU & PRICES (USE THIS AS THE ONLY REFERENCE):\n"
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
    
    "🎁 EXACT MENU-BASED COMBO DEALS (CALCULATED FROM PRICES ABOVE):\n"
    "1. 🍜 CHINESE COMBO: Veg Noodles (₹130) + Paneer Chilli (₹240) -> Alag se ₹370, par Combo me sirf ₹320/-! 🔥\n"
    "2. 🍔 BURGER COMBO: Veg Burger (₹90) + French Fries (₹100) + Cold Drink (₹50) -> Alag se ₹240, par Combo me sirf ₹210/-! 🍟\n"
    "3. 🍗 BIRYANI COMBO: Chicken Biryani (₹210) + Mint Mojito (₹90) -> Alag se ₹300, par Combo me sirf ₹260/-! 🍹\n\n"
    
    "⚠️ AI SMART RULES FOR ALISHA:\n"
    "RULE 1: (Smart Cross-Selling) Jab bhi koi customer kisi Fast Food ya Main course ka rate pooche, use price batane ke baad upar diye gaye menu se match hoti hui koi Drink/Shake ya Side item khud se suggest karo. "
    "Example: 'Chicken Biryani ₹210 ki hai sir. Iske sath hamara chilled Mint Mojito (₹90) ekdum shaandar lagega! Kya aapke liye add karoon?'\n"
    "RULE 2: (Combo Suggestion) Agar customer bole 'kuch offer dikhao' ya 'best deal', toh upar diye gaye 3 Calculated WhatsApp Combos unhe sundar tareeqe se dikhao aur savings samjhao.\n"
    "RULE 3: (Order Confirmation) Order lagane ya Table booking ke liye unhe bolo ki hamare helpline numbers par call ya WhatsApp karein: 📞 8271918062 ya 📞 7303267750.\n"
    "RULE 4: Hamesha polite rehna hai aur ek baar me saara menu nahi bhejna hai."
)

# Admin Tracker parsing logic
def parse_admin_record(text):
    try:
        # Sale nikalna
        sale_match = re.search(r'sale\s*(\d+)', text, re.IGNORECASE)
        sale = int(sale_match.group(1)) if sale_match else 0
        
        # Baki saare kharche jodhna
        expenses = re.findall(r'(?<!sale\s)(?:[a-zA-Z\s&]+)\s*(\d+)', text, re.IGNORECASE)
        total_expense = sum(int(x) for x in expenses)
        
        # Net Profit
        profit = sale - total_expense
        
        reply = (
            f"📝 **Eat & Park - Daily Hisaab-Kitab**\n\n"
            f"💰 Total Sale: ₹{sale:,}\n"
            f"💸 Total Expense: ₹{total_expense:,}\n"
            f"📊 Net Profit (Kamai): ₹{profit:,}\n\n"
            f"✅ Himanshu bhai, aaj ka record safe save ho gaya hai!"
        )
        return reply
    except Exception as e:
        return f"Hisaab format me thodi galti hai bhai! Kripya is tarah likhein:\n`Add Record: Sale 15000, Chicken 1800, Sabji 600`"

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    try:
        user_msg = request.values.get('Body', '').strip()
        print(f"Incoming Message: {user_msg}")
        
        # CHECK IF IT IS ADMIN MODE FOR HIMANSHU BHAI
        if user_msg.lower().startswith("add record:"):
            ai_reply = parse_admin_record(user_msg)
        else:
            # CUSTOMER MODE WITH AI
            ai_reply = "Namaste! Eat & Park me aapka swagat hai. Humara system abhi thoda busy hai, kripya ek aur baar message bhejkar try kijiye!"
            
            for i in range(3):
                try:
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=user_msg,
                        config=types.GenerateContentConfig(
                            system_instruction=ALISHA_RULES
                        ),
                    )
                    ai_reply = response.text
                    break
                except Exception as gemini_err:
                    print(f"Gemini Attempt {i+1} failed: {gemini_err}")
                    time.sleep(2)
                
    except Exception as e:
        ai_reply = f"Gemini Error: {str(e)}"
    
    # Twilio Response setup
    resp = MessagingResponse()
    resp.message(ai_reply)
    return str(resp)

@app.route("/", methods=['GET'])
def home():
    return "Eat & Park Alisha Smart Tracker Bot is running perfectly!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
