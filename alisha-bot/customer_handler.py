# Customer flow — chat, memory, order booking, tracking
import time
import json
import requests
from firebase_config import get_db
from ai_helper import build_system_prompt, ask_gemini, extract_order_from_reply
from admin_handler import get_stopped_items


def get_menu():
    """Firestore se live menu pull karta hai."""
    db = get_db()
    doc = db.collection("settings").document("menu").get()
    if doc.exists:
        return doc.to_dict().get("items", [])
    return []


def get_history(phone, limit=5):
    """Last N messages from Firestore."""
    db = get_db()
    docs = (
        db.collection("chat_history")
        .document(phone)
        .collection("messages")
        .order_by("timestamp", direction="DESCENDING")
        .limit(limit)
        .stream()
    )
    msgs = [d.to_dict() for d in docs]
    return list(reversed(msgs))


def save_message(phone, role, text):
    db = get_db()
    db.collection("chat_history").document(phone).collection("messages").add({
        "role": role,
        "text": text,
        "timestamp": time.time(),
    })


def handle_customer_message(phone, user_msg):
    """Customer ka message process karta hai."""
    menu = get_menu()
    stopped = get_stopped_items()

    # Agar menu khali hai toh fallback
    if not menu:
        return "Namaste! Eat & Park me aapka swagat hai. Humara menu abhi load ho raha hai. Kripya helpline pe call karein: 📞 8271918062"

    system_prompt = build_system_prompt(menu, stopped)
    history = get_history(phone)

    ai_reply = ask_gemini(user_msg, system_prompt, history)

    if not ai_reply:
        return "Server thoda busy hai. Kripya helpline pe call karein: 📞 8271918062"

    # Save user message
    save_message(phone, "user", user_msg)

    # Order JSON nikalo
    order_items, clean_reply = extract_order_from_reply(ai_reply)

    if order_items:
        # Order Firestore mein save
        db = get_db()
        order_id = f"WA{int(time.time())}"
        db.collection("orders").document(order_id).set({
            "id": order_id,
            "source": "whatsapp",
            "customer": {"phone": phone, "name": "WhatsApp Customer"},
            "items": order_items,
            "status": "new",
            "createdAt": int(time.time() * 1000),
            "payment": "pending",
            "paid": False,
        })
        clean_reply += f"\n\n✅ Aapka order confirm ho gaya! Order ID: *{order_id}*"

    save_message(phone, "model", clean_reply)
    return clean_reply


def track_order(phone):
    """Customer ke latest active order ka status."""
    db = get_db()
    docs = (
        db.collection("orders")
        .where("customer.phone", "==", phone)
        .where("status", "in", ["new", "preparing", "ready"])
        .stream()
    )
    orders = [d.to_dict() for d in docs]

    if not orders:
        return "Aapka koi active order nahi mila. Naya order karne ke liye message karein! 🍽️"

    latest = sorted(orders, key=lambda x: -x.get("createdAt", 0))[0]
    status_map = {
        "new": "🍽️ Order mil gaya, kitchen mein bhej diya",
        "preparing": "👨‍🍳 Banna shuru ho gaya",
        "ready": "✅ Ready hai! Serve hone wala hai",
    }
    status_text = status_map.get(latest["status"], latest["status"])
    items_text = ", ".join([f"{i['qty']}x {i['item']}" for i in latest.get("items", [])])

    return (
        f"📦 *Order #{latest['id']}*\n\n"
        f"{status_text}\n\n"
        f"Items: {items_text}\n\n"
        f"Thoda intezaar karein, jaldi milega! 🙏"
    )
