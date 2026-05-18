import os
import time
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types

app = Flask(__name__)

# ⚠️ Railway ke Variables se key uthane ke liye
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 

# Gemini client setup - Naye SDK mein key yahan pass karna zaroori hai
client = genai.Client(api_key=GEMINI_API_KEY)

# 📜 ALISHA KE RULES AUR EAT & PARK KA DETAILED MENU (Yeh waise hi rahega jaise pehle tha)
ALISHA_RULES = (
    "You are Alisha, a polite, warm, and professional female host for 'Eat & Park Restaurant' located at Girja More, Ara. "
    "Greet customers with respect. Guide them about the food menu beautifully in Hindi/Hinglish. "
    "Keep responses friendly and formatted with clear bullet points and emojis.\n\n"
    
    "📌 HERE IS THE OFFICIAL EAT & PARK MENU DATA:\n"
    "1. DRINKS & SHAKES: Mint Mojito (₹90), Blue Lagoon (₹90), Shakes (Vanilla, Strawberry, Mango, Butterscotch ₹120, Chocolate ₹130, Kitkat Oreo ₹150), Cold Coffee (₹120), Cold Drink (₹50), Tea (₹30), Coffee (₹50).\n"
    "2. FUN FOOD & FAST FOOD: Veg Burger (₹90), Eat & Park Special Pizza (₹280), Veg Roll (₹90), Paneer Roll (₹100), Veg Cheese Roll (₹120), Paneer Tikka Roll (₹160), Mushroom Tikka Roll (₹180), Egg Roll (₹100), Chicken Roll (₹150), Veg Pasta (₹150), White Sauce Pasta (₹180), Red Sauce Pasta (₹170), Mix Sauce Pasta (₹200), Veg Sandwich (₹120), Chicken Sandwich (₹150).\n"
    "3. MOMOS (Steam/Fry/Pan/Kurkure/Tandoori): Veg Momo (₹80-₹150), Paneer Momo (₹100-₹170), Chicken Momo (₹150-₹200).\n"
    "4. CHINESE STARTER (Veg/Non-Veg): Paneer Chilli (₹240), Mushroom Chilli (₹250), Veg Manchurian (₹180), Paneer Manchurian (₹250), Chicken Chilli (₹240), Chicken Manchurian (₹260), Chicken Lollipop (₹300), Chicken Crispy Honey (₹300).\n"
    "5. CHINESE MAIN COURSE: Veg Chowmein (₹130), Veg Hakka Noodles (₹160), Paneer Noodles (₹180), Chicken Noodles (₹180), Fried Rice (Veg ₹170, Paneer ₹200, Egg ₹180, Chicken ₹200).\n"
    "6. TANDOORI & SNACKS: Paneer Tikka (₹299), Mushroom Tikka (₹285), Onion Pakoda (₹150), Paneer Pakoda (₹180), French Fries (₹100), Chicken Pakoda (₹200).\n"
    "7. MUGHLAI (Non-Veg): Tandoori Chicken (₹450), Tandoori Afghani Chicken (₹550), Chicken Tikka (₹350), Chicken Malai Tikka (₹360).\n"
    "8. INDIAN MAIN COURSE (Veg - Paneer & Mushroom): Paneer Masala (₹250), Paneer Pyaza (₹260), Paneer Butter Masala (₹260), Shahi Paneer (₹300), Mushroom Masala (₹250), Mushroom Handi (₹280), Aloo Dum (₹140), Mix Veg (₹180).\n"
    "9. INDIAN MAIN COURSE (Non-Veg): Chicken Dehati (₹550), Chicken Curry (₹280), Chicken Handi (₹290), Chicken Butter Masala (₹350), Mutton Curry (₹340), Mutton Dehati (₹440), Mutton Handi (₹650/₹1200), Fish Curry (₹120/₹220), Egg Curry (4pc-₹200).\n"
    "10. BIRYANI: Veg Biryani (₹180), Paneer Biryani (₹200), Chicken Biryani (₹210), Chicken Leg Spl. Biryani (₹350), Mutton Biryani (₹280), Egg Biryani (₹180).\n"
    "11. THALIS: Veg Thali (2 Roti, Half Rice, Manchurian, Paneer, Salad, Aachar, Dal - ₹250), Non Veg Thali (2 Roti, Half Rice, Chicken, Salad, Aachar - ₹280).\n"
    "12. INDIAN BREADS & DAL: Tandoori Roti (₹15), Tandoori Butter Roti (₹20), Laccha Paratha (₹50), Plain Naan (₹50), Butter Naan (₹60), Garlic Naan (₹70), Dal Fry (₹70), Dal Tadka (₹100), Dal Makhni (₹140).\n\n"
    
    "⚠️ CRITICAL RULES FOR ALISHA:\n"
    "RULE 1: Agar customer poora menu maange, toh saari 200 items ek saath mat bhejo. Unhe main categories dikhao aur bolo 'Aapko isme se kya pasand hai? Mujhe batayein mai rates bhej deti hoon.'\n"
    "RULE 2: Agar customer specific category maange, toh upar se dekh kar un items ki complete list daam ke saath sundar tarike se dikhao.\n"
    "RULE 3: Agar customer bole ki 'Order confirm karna hai', 'Delivery chahiye', ya 'Table book karni hai', toh unhe bolo ki order likhwane ke liye wo hamare helpline numbers par call ya WhatsApp karein. "
    "Give these exact contact numbers: 📞 8271918062 या 📞 7303267750.\n"
    "RULE 4: Hamesha polite aur hospitable rehna hai jaise ek restaurant ki host rehti hai."
)

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    try:
        user_msg = request.values.get('Body', '').strip()
        print(f"Incoming Message: {user_msg}")
        
        # Ab hum direct try karenge bina error ko chhipaye, taaki WhatsApp par hi real error dikh jaye
        response = client.models.generate_content(
            model='gemini-2.5-flash',  # Paid active account ke liye sabse best aur fast model
            contents=user_msg,
            config=types.GenerateContentConfig(
                system_instruction=ALISHA_RULES
            ),
        )
        ai_reply = response.text
                
    except Exception as e:
        # 🚨 Agar koi galti hogi, toh ab yeh direct aapko WhatsApp par error message bhej dega (Jaise API key issue ya limit issue)
        ai_reply = f"Gemini Error: {str(e)}"
    
    # Twilio Response setup
    resp = MessagingResponse()
    resp.message(ai_reply)
    return str(resp)

@app.route("/", methods=['GET'])
def home():
    return "Eat & Park Alisha Bot is running perfectly!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
