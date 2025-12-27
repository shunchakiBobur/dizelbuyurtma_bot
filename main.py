import os
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = {6419271223, 6994628664}
PRICE_PER_LITR = 10500

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ================= DATA =================
user_data = {}
registered_users = set()
pending_delivery = {}      # (admin_id, user_id): True
admin_waiting_time = set() # admin_id
broadcast_cache = {}       # admin_id: {"step": "...", "text": "..."}

# ================= MENULAR =================
def main_menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📦 Buyurtma berish", "📞 Admin bilan bog‘lanish")
    kb.add("ℹ️ Mahsulot haqida ma’lumot")
    bot.send_message(chat_id, "Asosiy menyu:", reply_markup=kb)

def admin_menu(admin_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👥 Foydalanuvchilar", "📢 Post yuborish")
    bot.send_message(admin_id, "Admin menyu:", reply_markup=kb)

# ================= START =================
@bot.message_handler(commands=["start"])
def start(message):
    cid = message.chat.id
    registered_users.add(cid)

    if cid in ADMIN_IDS:
        admin_menu(cid)
    else:
        main_menu(cid)

# ================= INFO =================
@bot.message_handler(func=lambda m: m.text == "ℹ️ Mahsulot haqida ma’lumot")
def info(message):
    bot.send_message(
        message.chat.id,
        f"💧 Dizel yoqilg‘isi\n💰 {PRICE_PER_LITR} so‘m / litr\n🚚 Yetkazib berish mavjud"
    )

# ================= BUYURTMA BOSHLASH =================
@bot.message_handler(func=lambda m: m.text == "📦 Buyurtma berish")
def order_start(message):
    cid = message.chat.id

    if cid in user_data:
        bot.send_message(cid, "❗ Buyurtma allaqachon jarayonda")
        return

    user_data[cid] = {}
    bot.send_message(cid, "💧 Necha litr dizel kerak? (faqat son)")

# ================= MATN =================
@bot.message_handler(content_types=["text"])
def handle_text(message):
    cid = message.chat.id
    text = message.text.strip()

    # ===== BROADCAST =====
    if cid in ADMIN_IDS and cid in broadcast_cache:
        state = broadcast_cache[cid]["step"]

        if state == "text":
            broadcast_cache[cid]["text"] = text
            broadcast_cache[cid]["step"] = "confirm"

            kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            kb.add("Ha", "Yo‘q")
            bot.send_message(cid, "Xabar yuborilsinmi?", reply_markup=kb)
            return

        if state == "confirm":
            if text == "Ha":
                for uid in list(registered_users):
                    if uid not in ADMIN_IDS:
                        try:
                            bot.send_message(uid, broadcast_cache[cid]["text"])
                        except:
                            registered_users.discard(uid)

                bot.send_message(cid, "✅ Xabar yuborildi")
            else:
                bot.send_message(cid, "❌ Bekor qilindi")

            broadcast_cache.pop(cid)
            admin_menu(cid)
            return

    # ===== ADMIN MENU =====
    if cid in ADMIN_IDS:
        if text == "👥 Foydalanuvchilar":
            bot.send_message(cid, f"👤 Jami foydalanuvchilar: {len(registered_users)}")
        elif text == "📢 Post yuborish":
            broadcast_cache[cid] = {"step": "text", "text": ""}
            bot.send_message(cid, "Xabar matnini kiriting")
        return

    # ===== BUYURTMA LITR =====
    if cid in user_data and "litr" not in user_data[cid]:
        if not text.isdigit():
            bot.send_message(cid, "❗ Faqat son kiriting")
            return

        user_data[cid]["litr"] = int(text)
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(types.KeyboardButton("📍 Lokatsiya yuborish", request_location=True))
        bot.send_message(cid, "Lokatsiyani yuboring", reply_markup=kb)

# ================= LOKATSIYA =================
@bot.message_handler(content_types=["location"])
def handle_location(message):
    cid = message.chat.id
    if cid not in user_data:
        return

    user_data[cid]["location"] = message.location

    for admin in ADMIN_IDS:
        bot.send_message(admin, f"📍 Lokatsiya | User ID: {cid}")
        bot.send_location(admin, message.location.latitude, message.location.longitude)

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("📞 Telefon yuborish", request_contact=True))
    bot.send_message(cid, "Telefon raqamingizni yuboring", reply_markup=kb)

# ================= CONTACT =================
@bot.message_handler(content_types=["contact"])
def handle_contact(message):
    cid = message.chat.id
    if cid not in user_data:
        return

    user_data[cid]["phone"] = message.contact.phone_number
    send_to_admin(cid, message)

    bot.send_message(cid, "📨 Buyurtma operatorga yuborildi")
    main_menu(cid)

# ================= ADMINGA YUBORISH =================
def send_to_admin(user_id, message):
    data = user_data[user_id]

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ Qabul", callback_data=f"ok:{user_id}"),
        types.InlineKeyboardButton("❌ Rad", callback_data=f"no:{user_id}")
    )

    text = (
        f"🆕 <b>Yangi buyurtma</b>\n"
        f"👤 {message.from_user.first_name}\n"
        f"💧 {data['litr']} litr\n"
        f"📞 {data['phone']}"
    )

    for admin in ADMIN_IDS:
        bot.send_message(admin, text, reply_markup=kb)

# ================= CALLBACK =================
@bot.callback_query_handler(func=lambda c: True)
def callback(c):
    action, uid = c.data.split(":")
    uid = int(uid)
    admin_id = c.message.chat.id

    if action == "ok":
        pending_delivery[(admin_id, uid)] = True
        admin_waiting_time.add(admin_id)
        bot.send_message(admin_id, "⏱ Necha daqiqada yetkaziladi?")
    else:
        bot.send_message(uid, "❌ Buyurtma rad etildi")
        user_data.pop(uid, None)

    bot.answer_callback_query(c.id)

# ================= YETKAZISH VAQTI =================
@bot.message_handler(func=lambda m: m.chat.id in admin_waiting_time and m.text.isdigit())
def delivery_time(message):
    admin_id = message.chat.id
    minutes = int(message.text)

    for (aid, uid) in list(pending_delivery.keys()):
        if aid == admin_id:
            price = user_data[uid]["litr"] * PRICE_PER_LITR
            bot.send_message(
                uid,
                f"✅ Buyurtma qabul qilindi\n💰 {price} so‘m\n⏱ {minutes} daqiqa"
            )

            pending_delivery.pop((aid, uid))
            user_data.pop(uid, None)
            admin_waiting_time.discard(admin_id)
            break

# ================= RUN =================
bot.infinity_polling(skip_pending=True)