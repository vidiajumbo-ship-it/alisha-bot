
# Saare Gemini calls yahan — chat, insights, voice, order parse
import os
import json
import time
from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

MODEL = "gemini-2.5-flash"


# ---------- MENU + SYSTEM PROMPT ----------
def build_system_prompt(menu_items, stopped_items):
    """Dynamic menu + stopped items se system prompt banata hai."""
    menu_lines = []
    for item in menu_items:
        status = "❌ FINISHED" if item["name"].lower() in [s.lower() for s in stopped_items] else ""
        menu_lines.append(f"- {item['name']} (₹{item['price']}) {status}")
    menu_text = "\n".join(menu_lines)

    stopped_text = ", ".join(stopped_items) if stopped_items else "None (All available)"

    return (
        "You are Alisha — the smart, polite, professional female host of 'Eat & Park Restaurant', Girja More, Ara.\n"
        "Speak in friendly Hinglish (Hindi in Roman script + English food words). Use emojis tastefully.\n\n"
        f"📌 LIVE MENU:\n{menu_text}\n\n"
        f"⚠️ OUT OF STOCK TODAY: {stopped_text}\n"
        "If customer asks for an out-of-stock item, politely say it's finished and suggest an alternative.\n\n"
        "🎁 COMBO DEALS:\n"
        "1. Chinese Combo: Veg Noodles + Paneer Chilli = ₹320 (₹370 ka ₹320)\n"
        "2. Burger Combo: Veg Burger + Fries + Cold Drink = ₹210 (₹240 ka ₹210)\n"
        "3. Biryani Combo: Chicken Biryani + Mint Mojito = ₹260 (₹300 ka ₹260)\n\n"
        "📋 RULES:\n"
        "1. Cross-sell: price batane ke baad matching drink/shake suggest karo.\n"
        "2. Combo maange toh upar ke 3 combos savings ke saath dikhao.\n"
        "3. Order/Table booking ke liye helpline do: 📞 8271918062 / 7303267750\n"
        "4. Polite raho, ek baar mein poora menu mat bhejo.\n"
        "5. Agar customer English mein baat kare toh English mein reply do. Hindi mein toh Hinglish.\n"
        "6. ORDER BOOKING: Agar customer clearly order kare (items + quantity), toh reply ke END mein ek JSON line do:\n"
        '   {"order": [{"item": "Chicken Biryani", "qty": 2}, {"item": "Coke", "qty": 1}]}\n'
        "   Warna JSON mat do.\n"
    )


# ---------- MAIN CHAT ----------
def ask_gemini(user_msg, system_prompt, history=None, retries=3):
    """Conversation memory ke saath Gemini call."""
    contents = []

    # Purani conversation inject karo (memory)
    if history:
        for h in history[-5:]:
            role = "user" if h["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=h["text"])]))

    contents.append(types.Content(role="user", parts=[types.Part(text=user_msg)]))

    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(system_instruction=system_prompt),
            )
            if response.text:
                return response.text.strip()
        except Exception as e:
            print(f"Gemini error (attempt {attempt+1}): {e}")
            time.sleep(1.5)
    return None


# ---------- ORDER PARSE ----------
def extract_order_from_reply(ai_reply):
    """AI reply ke end mein JSON order dhundta hai."""
    import re
    match = re.search(r'\{"order"\s*:\s*\[.*?\]\s*\}', ai_reply, re.DOTALL)
    if not match:
        return None, ai_reply
    try:
        data = json.loads(match.group(0))
        clean_reply = ai_reply.replace(match.group(0), "").strip()
        return data.get("order"), clean_reply
    except Exception:
        return None, ai_reply


# ---------- INSIGHTS ----------
def generate_insights(sales_data, expense_data, top_items, stopped_items):
    """Admin ke liye AI business insights."""
    prompt = f"""
You are a restaurant business analyst for Eat & Park.
Data:
- Monthly Sale: ₹{sales_data}
- Monthly Expense: ₹{expense_data}
- Top Selling Items: {json.dumps(top_items)}
- Out of stock: {stopped_items}

Give 3-4 short actionable insights in Hinglish. Each on new line, starting with emoji.
Example:
📈 Chicken Biryani aaj bahut bike. Weekend pe stock badha do.
⚠️ Mushroom Masala 3 din se nahi bika. Promo laga do.
"""
    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        return response.text.strip()
    except Exception as e:
        return f"Insights abhi nahi aa paye. Error: {e}"


# ---------- VOICE TRANSCRIBE ----------
def transcribe_voice(audio_bytes, mime_type="audio/ogg"):
    """Twilio voice note ko Gemini se text mein convert karta hai."""
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                "Transcribe this audio. Only return the transcribed text, nothing else."
            ]
        )
        return response.text.strip() if response.text else None
    except Exception as e:
        print(f"Voice transcribe error: {e}")
        return None
