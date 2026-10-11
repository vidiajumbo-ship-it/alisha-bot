# Admin ke saare commands
import re
from firebase_config import get_db
from ai_helper import generate_insights


def is_admin(sender, admin_phone):
    return not admin_phone or sender == admin_phone


def parse_record(text):
    """'Add Record: Sale 15000, Chicken 1800' parse karta hai."""
    db = get_db()
    try:
        clean = text.split(":", 1)[1].strip() if ":" in text else text
        entries = [e.strip() for e in clean.split(",") if e.strip()]

        sale = 0
        expenses = []
        for entry in entries:
            m = re.match(r"([a-zA-Z\s&]+)\s+(\d+)", entry)
            if m:
                key = m.group(1).strip().lower()
                amount = int(m.group(2))
                if "sale" in key:
                    sale += amount
                else:
                    expenses.append({"name": m.group(1).strip(), "amount": amount})

        total_expense = sum(e["amount"] for e in expenses)
        profit = sale - total_expense

        # Firestore mein save
        db.collection("bot_records").add({
            "sale": sale,
            "expenses": expenses,
            "total_expense": total_expense,
            "profit": profit,
            "timestamp": __import__("time").time(),
        })

        return (
            f"📝 *Eat & Park — Daily Hisaab*\n\n"
            f"💰 Sale: ₹{sale:,}\n"
            f"💸 Expense: ₹{total_expense:,}\n"
            f"📊 Profit: ₹{profit:,}\n\n"
            f"✅ Record save ho gaya!"
        )
    except Exception as e:
        return f"❌ Format galat! Aise bhejo:\n`Add Record: Sale 15000, Chicken 1800, Sabji 600`\n\nError: {e}"


def get_monthly_report():
    """Monthly sale + expense + profit."""
    db = get_db()
    records = db.collection("bot_records").stream()

    total_sale = 0
    total_expense = 0
    for r in records:
        d = r.to_dict()
        total_sale += d.get("sale", 0)
        total_expense += d.get("total_expense", 0)

    profit = total_sale - total_expense
    return (
        f"📊 *Eat & Park — Monthly Report*\n\n"
        f"💰 Total Sale: ₹{total_sale:,}\n"
        f"💸 Total Expense: ₹{total_expense:,}\n"
        f"📈 Net Profit: ₹{profit:,}\n\n"
        f"🚀 Keep crushing it!"
    )


def stop_item(item):
    db = get_db()
    item_clean = item.strip().lower()
    if not item_clean:
        return "❌ Item naam do. Jaise: `/stop Biryani`"

    doc_ref = db.collection("bot_config").document("stopped_items")
    doc = doc_ref.get()
    current = doc.to_dict().get("items", []) if doc.exists else []

    if item_clean not in [x.lower() for x in current]:
        current.append(item_clean)
        doc_ref.set({"items": current})
    return f"🚫 Alisha ab *{item}* ko finished batayegi."


def start_item(item):
    db = get_db()
    item_clean = item.strip().lower()
    doc_ref = db.collection("bot_config").document("stopped_items")
    doc = doc_ref.get()
    current = doc.to_dict().get("items", []) if doc.exists else []

    updated = [x for x in current if x.lower() != item_clean]
    doc_ref.set({"items": updated})
    return f"✅ *{item}* wapas live!"


def get_stopped_items():
    db = get_db()
    doc = db.collection("bot_config").document("stopped_items").get()
    return doc.to_dict().get("items", []) if doc.exists else []


def handle_insights():
    """AI-powered business insights."""
    db = get_db()
    records = list(db.collection("bot_records").stream())

    total_sale = sum(r.to_dict().get("sale", 0) for r in records)
    total_expense = sum(r.to_dict().get("total_expense", 0) for r in records)

    # Order items count (Firestore orders se)
    orders = list(db.collection("orders").stream())
    item_count = {}
    for o in orders:
        for it in o.to_dict().get("items", []):
            name = it.get("name", "")
            item_count[name] = item_count.get(name, 0) + it.get("qty", 0)

    top_items = sorted(item_count.items(), key=lambda x: -x[1])[:5]
    stopped = get_stopped_items()

    return generate_insights(total_sale, total_expense, top_items, stopped)
