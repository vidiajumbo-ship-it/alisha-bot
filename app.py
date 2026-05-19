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

# 📜 GLOBAL VARIABLES FOR REPORT AND AVAILABILITY
# Note: Server restart hone par ye memory clear ho sakti hai, par daily/weekly track ke liye perfect hai.
monthly_sale = 0
monthly_expense = 0
stopped_items = []

# 📜 ALISHA KE SMART RULES & EXACT MENU DATA
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

# Admin Tracker parsing logic
def parse_admin_record(text):
    global monthly_sale, monthly_expense
    try:
        sale_match = re.search(r'sale\s*(\d+)', text, re.IGNORECASE)
        sale = int(sale_match.group(1)) if sale_match else 0
        
        expenses = re.findall(r'(?<!sale\s)(?:[a-zA-Z\s&]+)\s*(\d+)', text, re.IGNORECASE)
        total_expense = sum(int(x) for x in expenses)
        
        # Monthly data update
        monthly_sale += sale
        monthly_expense += total_expense
        profit = sale - total_expense
        
        reply = (
            f"📝 **Eat & Park - Daily Hisaab-Kitab**\n\n"
            f"💰 Today's Sale: ₹{sale:,}\n"
            f"💸 Today's Expense: ₹{total_expense:,}\n"
            f"📊 Today's Profit: ₹{profit:,}\n\n"
            f"✅ Himanshu bhai, aaj ka record save ho gaya aur Monthly Report me jod diya gaya hai!"
        )
        return reply
    except Exception as e:
        return f"Hisaab format me galti hai bhai! Kripya is tarah likhein:\n`Add Record: Sale 15000, Chicken 1800, Sabji 600`"

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    global monthly_sale, monthly_expense, stopped_items
    try:
        user_msg = request.values.get('Body', '').strip()
        print(f"Incoming Message: {user_msg}")
        
        user_msg_lower = user_msg.lower()

        # 1. ADMIN MODE: DAILY HISAAB
        if user_msg_lower.startswith("add record:"):
            ai_reply = parse_admin_record(user_msg)
            
        # 2. ADMIN MODE: MONTHLY REPORT
        elif user_msg_lower == "/report":
            net_monthly_profit = monthly_sale - monthly_expense
            ai_reply = (
                f"📊 **Eat & Park - Monthly Business Report**\n\n"
                f"💰 Total Monthly Sale: ₹{monthly_sale:,}\n"
                f"💸 Total Monthly Expense: ₹{monthly_expense:,}\n"
                f"📈 Net Monthly Profit (Kamai): ₹{net_monthly_profit:,}\n\n"
                f"💼 Keep crushing it, Himanshu bhai! Rocket Business! 🚀"
            )
            
        # 3. ADMIN MODE: STOP ITEM
        elif user_msg_lower.startswith("/stop "):
            item_to_stop = user_msg[6:].strip()
            if item_to_stop not in stopped_items:
                stopped_items.append(item_to_stop)
            ai_reply = f"🚫 Mode Updated: Alisha ab customers ko **{item_to_stop}** finished batayegi aur kuch aur suggest karegi."
            
        # 4. ADMIN MODE: START ITEM
        elif user_msg_lower.startswith("/start "):
            item_to_start = user_msg[7:].strip()
            if item_to_start in stopped_items:
                stopped_items.remove(item_to_start)
            ai_reply = f"✅ Mode Updated: **{item_to_start}** ab wapas menu me available ho gaya hai!"
            
        # 5. CUSTOMER MODE WITH AI
        else:
            ai_reply = "Namaste! Eat & Park me aapka swagat hai. Humara system abhi thoda busy hai, kripya ek aur baar message bhejkar try kijiye!"
            
            # Stopped items ka text format banana
            stopped_list_text = ", ".join(stopped_items) if stopped_items else "None (All items available)"
            dynamic_rules = ALISHA_RULES_TEMPLATE.format(stopped_list_text=stopped_list_text)

            for i in range(3):
                try:
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=user_msg,
                        config=types.GenerateContentConfig(
                            system_instruction=dynamic_rules
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
    return "Eat & Park Alisha Management Bot is running perfectly!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
