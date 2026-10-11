import os
import time
import requests
from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

from firebase_config import init_firebase
from admin_handler import (
    is_admin, parse_record, get_monthly_report,
    stop_item, start_item, handle_insights
)
from customer_handler import handle_customer_message, track_order
from ai_helper import transcribe_voice

load_dotenv()
init_firebase()

app = Flask(__name__)

ADMIN_PHONE = os.environ.get("ADMIN_PHONE", "")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")

# Rate limiting (simple in-memory)
_last_msg = {}
RATE_LIMIT_SECONDS = 2


def is_rate_limited(phone):
    now = time.time()
    last = _last_msg.get(phone, 0)
    if now - last < RATE_LIMIT_SECONDS:
        return True
    _last_msg[phone] = now
    return False


def download_twilio_media(media_url):
    """Twilio ka media (voice note) download karta hai."""
    try:
        r = requests.get(media_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), timeout=10)
        if r.status_code == 200:
            return r.content, r.headers.get("Content-Type", "audio/ogg")
    except Exception as e:
        print(f"Media download error: {e}")
    return None, None


@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    resp = MessagingResponse()

    try:
        sender = request.values.get("From", "")
        user_msg = request.values.get("Body", "").strip()
        num_media = int(request.values.get("NumMedia", "0"))
        media_url = request.values.get("MediaUrl0", "")
        media_type = request.values.get("MediaContentType0", "")
        user_msg_lower = user_msg.lower()

        # Rate limit
        if is_rate_limited(sender):
            resp.message("Thoda ruk ke bhejein 🙏")
            return Response(str(resp), mimetype="application/xml")

        admin = is_admin(sender, ADMIN_PHONE)

        # -------- VOICE NOTE HANDLING --------
        if num_media > 0 and "audio" in media_type:
            audio_bytes, mime = download_twilio_media(media_url)
            if audio_bytes:
                transcribed = transcribe_voice(audio_bytes, mime)
                if transcribed:
                    user_msg = transcribed
                    user_msg_lower = user_msg.lower()
                    resp.message(f"🎤 _Suna: {transcribed}_")

        # -------- ADMIN COMMANDS --------
        if admin and user_msg_lower.startswith("add record"):
            ai_reply = parse_record(user_msg)

        elif admin and user_msg_lower == "/report":
            ai_reply = get_monthly_report()

        elif admin and user_msg_lower == "/insights":
            ai_reply = handle_insights()

        elif admin and user_msg_lower.startswith("/stop "):
            ai_reply = stop_item(user_msg[6:].strip())

        elif admin and user_msg_lower.startswith("/start "):
            ai_reply = start_item(user_msg[7:].strip())

        # -------- CUSTOMER: ORDER TRACKING --------
        elif user_msg_lower in ["order status", "mera order", "track order", "/track"]:
            ai_reply = track_order(sender)

        # -------- CUSTOMER: MAIN CHAT --------
        else:
            ai_reply = handle_customer_message(sender, user_msg)

    except Exception as e:
        print(f"Fatal error: {e}")
        ai_reply = "System update chal raha hai. Kripya call karein: 📞 8271918062"

    resp.message(ai_reply)
    return Response(str(resp), mimetype="application/xml")


@app.route("/", methods=["GET"])
def home():
    return "✅ Eat & Park Alisha Bot v2 — Running!"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
