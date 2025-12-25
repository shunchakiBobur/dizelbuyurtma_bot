import os
import json
import telebot
from telebot import types

# =========================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = {6419271223, 6994628664}  # Bir nechta adminlar Telegram IDlari
ADMIN_USERNAMES = {"dizel_go", "admin2"}  # Admin nicklari
PRICE_PER_LITR = 10500
USERS_FILE = "users.json"
# =========================

bot = telebot.TeleBot(TOKEN)

# ================= Fayllarni yuklash =================
try:
    with open(USERS_FILE, "r") as f:
        registered_users = set(json.load(f))
except (FileNotFoundError, json.JSONDecodeError):
    registered_users = set()

user_data = {}            # Hozirgi session ma'lumotlari
order_history = []        # Buyurtma tarixi
pending_delivery = {}     # Yetkazib berish vaqtini kiritishni kutayotgan buyurtmalar
broadcast_cache = {}      # Admin xabar yuborish uchun

# ================= Faylga saqlash =================
def save_users():
    with open(USERS_FILE, "w") as f:
        json.dump(list(registered_users), f)

# ================= Main Menu =================
def main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    order_btn = types.KeyboardButton("📦 Buyurtma berish")
    contact_btn = types.KeyboardButton("📞 Admin bilan bog‘lanish")
    info_btn = types.KeyboardButton("ℹ️ Mahsulot haqida ma’lumot")
    markup.add(order_btn, contact_btn, info_btn)
    bot.send_message(chat_id, "Asosiy menyu:", reply_markup=markup)

# ================= Admin Menu =================
def admin_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    users_btn = types.KeyboardButton("👥 Foydalanuvchilar haqida ma’lumot")
    post_btn = types.KeyboardButton("📢 Post yuborish")
    markup.add(users_btn, post_btn)
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, "Admin menyu:", reply_markup=markup)

# ================= /start =================
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    if chat_id not in registered_users:
        registered_users.add(chat_id)
        save_users()
        bot.send_message(chat_id, f"Assalomu alaykum, {message.from_user.first_name}!\nBotimizga xush kelibsiz!")
    if chat_id in ADMIN_IDS:
        admin_menu()
    else:
        main_menu(chat_id)

# ================= Buyurtma berish =================
@bot.message_handler(func=lambda m: m.text == "📦 Buyurtma berish")
def order_start(message):
    chat_id = message.chat.id
    user_data[chat_id] = {}
    bot.send_message(chat_id, "Necha litr dizel kerak? (faqat son kiriting)")

# ================= Admin bilan bog‘lanish =================
@bot.message_handler(func=lambda m: m.text == "📞 Admin bilan bog‘lanish")
def contact_admin(message):
    chat_id = message.chat.id
    admins_text = "\n".join([f"@{u}" for u in ADMIN_USERNAMES])
    bot.send_message(chat_id, f"Adminlar bilan bog‘lanish:\n{admins_text}")

# ================= Mahsulot haqida ma’lumot =================
@bot.message_handler(func=lambda m: m.text == "ℹ️ Mahsulot haqida ma’lumot")
def product_info(message):
    chat_id = message.chat.id
    info = (f"💧 Mahsulot: Dizel yoqilg‘isi\n"
            f"💰 Narx: {PRICE_PER_LITR} so'm / litr\n"
            f"🚚 Yetkazib berish: Buyurtma qabul qilinganidan so‘ng belgilangan vaqtda\n"
            f"📦 Chegirmalar: 50 litrdan ortiq buyurtmalarga chegirma mavjud")
    bot.send_message(chat_id, info)

# ================= Matnli xabarlarni qabul qilish =================
@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()

    # ===== Admin xabar yuborish =====
    if chat_id in ADMIN_IDS and broadcast_cache.get(chat_id, {}).get("step") == "text":
        broadcast_cache[chat_id]["text"] = text
        broadcast_cache[chat_id]["step"] = "confirm"
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add("Ha", "Yo'q")
        bot.send_message(chat_id, f"Xabarni foydalanuvchilarga yuborishni tasdiqlaysizmi?\n\n{text}", reply_markup=markup)
        return

    if chat_id in ADMIN_IDS and broadcast_cache.get(chat_id, {}).get("step") == "confirm":
        if text.lower() == "ha":
            for user in registered_users:
                bot.send_message(user, broadcast_cache[chat_id]["text"])
            bot.send_message(chat_id, "✅ Xabar foydalanuvchilarga yuborildi.")
            broadcast_cache.pop(chat_id)
        elif text.lower() in ["yo'q", "yoq"]:
            bot.send_message(chat_id, "❌ Xabar yuborish bekor qilindi.")
            broadcast_cache.pop(chat_id)
        else:
            bot.send_message(chat_id, "❗️ Tasdiqlash uchun 'Ha' yoki 'Yo'q' deb yozing.")
        return

    # ===== Admin yetkazib berish vaqtini kiritish =====
    if chat_id in ADMIN_IDS and chat_id in pending_delivery and text.isdigit():
        delivery_minutes = int(text)
        order = pending_delivery.pop(chat_id)
        user_id = order['user_id']
        litrs = order['litr']
        total_price = litrs * PRICE_PER_LITR

        bot.send_message(user_id, f"✅ Buyurtmangiz qabul qilindi!\n"
                                  f"💧 Litr: {litrs}\n"
                                  f"💰 Narx: {total_price} so'm\n"
                                  f"⏱️ Taxminiy yetkazib berish: {delivery_minutes} daqiqa")
        bot.send_message(chat_id, f"✅ Yetkazib berish vaqti saqlandi: {delivery_minutes} daqiqa")

        order['status'] = "qabul qilindi"
        order['delivery_minutes'] = delivery_minutes
        order_history.append(order)

        del user_data[user_id]

        main_menu(user_id)
        return

    # ===== Admin menyusi =====
    if chat_id in ADMIN_IDS and chat_id not in user_data:
        if text == "👥 Foydalanuvchilar haqida ma’lumot":
            if not registered_users:
                bot.send_message(chat_id, "Hech qanday foydalanuvchi yo‘q.")
            else:
                text_list = "\n".join([str(user) for user in registered_users])
                bot.send_message(chat_id, f"📋 Foydalanuvchilar ro‘yxati:\n{text_list}")
        elif text == "📢 Post yuborish":
            bot.send_message(chat_id, "📨 Xabar matnini kiriting:")
            broadcast_cache[chat_id] = {"step": "text"}
        return

    # ===== Foydalanuvchi buyurtma =====
    if "litr" not in user_data[chat_id]:
        if not text.isdigit():
            bot.send_message(chat_id, "❗️ Iltimos, faqat son kiriting (litr).")
            return
        user_data[chat_id]["litr"] = int(text)

        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        location_btn = types.KeyboardButton("📍 Lokatsiya yuborish", request_location=True)
        markup.add(location_btn)
        bot.send_message(chat_id, "📍 Endi lokatsiya yuboring:", reply_markup=markup)
        return

    if "telefon" not in user_data[chat_id]:
        user_data[chat_id]["telefon"] = text
        send_to_admin(chat_id, message)
        bot.send_message(chat_id, "📨 Buyurtmangiz operatorga yuborildi. Tez orada javob beramiz.")
        main_menu(chat_id)
        return

# ================= Lokatsiyani qabul qilish =================
@bot.message_handler(content_types=['location'])
def handle_location(message):
    chat_id = message.chat.id
    user_data[chat_id] = user_data.get(chat_id, {})
    user_data[chat_id]["location"] = {
        "latitude": message.location.latitude,
        "longitude": message.location.longitude
    }
    # Lokatsiyani adminlardan biriga forward qilamiz
    bot.forward_message(list(ADMIN_IDS)[0], chat_id, message.message_id)
    bot.send_message(chat_id, "📞 Endi telefon raqamingizni yuboring:")

# ================= Adminga buyurtma yuborish =================
def send_to_admin(chat_id, message):
    data = user_data[chat_id]
    litrs = data["litr"]
    phone = data["telefon"]

    markup = types.InlineKeyboardMarkup()
    accept_btn = types.InlineKeyboardButton("✅ Qabul qilish", callback_data=f"accept_{chat_id}")
    reject_btn = types.InlineKeyboardButton("❌ Rad qilish", callback_data=f"reject_{chat_id}")
    markup.add(accept_btn, reject_btn)

    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    msg = f"🆕 Yangi buyurtma: {username}\n💧 Litr: {litrs}\n📞 Telefon: {phone}"
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, msg, reply_markup=markup)

# ================= Callback tugmalar =================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data
    user_id = int(data.split("_")[1])
    litrs = user_data[user_id]["litr"]

    if data.startswith("accept_") and call.message.chat.id in ADMIN_IDS:
        pending_delivery[call.message.chat.id] = {
            "user_id": user_id,
            "litr": litrs,
            "telefon": user_data[user_id]["telefon"],
            "username": call.from_user.username or call.from_user.first_name,
            "location": user_data[user_id].get("location")
        }
        bot.send_message(call.message.chat.id, "⏱️ Necha daqiqada yetkaziladi? (faqat son kiriting)")
        bot.answer_callback_query(call.id, "Buyurtma qabul qilindi, yetkazish vaqtini kiriting")

    elif data.startswith("reject_") and call.message.chat.id in ADMIN_IDS:
        order_history.append({
            "user_id": user_id,
            "username": user_data[user_id].get("username", ""),
            "litr": litrs,
            "telefon": user_data[user_id]["telefon"],
            "status": "rad qilindi",
            "delivery_minutes": None,
            "location": user_data[user_id].get("location")
        })
        bot.send_message(user_id, "❌ Afsus, buyurtmangiz rad etildi.")
        bot.answer_callback_query(call.id, "Buyurtma rad qilindi")
        main_menu(user_id)

# ================= Botni ishga tushurish =================
bot.infinity_polling()
