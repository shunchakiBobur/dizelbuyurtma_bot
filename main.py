import os
import telebot
from telebot import types

# =========================
TOKEN = os.getenv("BOT_TOKEN")  # 🔥 TOKEN serverdan olinadi
ADMIN_IDS = {6419271223, 6994628664}  # Bir nechta adminlar Telegram IDlari
ADMIN_USERNAMES = {"dizel_go", "admin2"}  # Admin nicklari
PRICE_PER_LITR = 10500
PRODUCT_INFO_TEXT = (f"💧 Mahsulot: Dizel yoqilg‘isi\n"
                     f"💰 Narx: {PRICE_PER_LITR} so'm / litr\n"
                     f"🚚 Yetkazib berish: Buyurtma qabul qilinganidan so‘ng belgilangan vaqtda\n"
                     f"📦 Chegirmalar: 50 litrdan ortiq buyurtmalarga chegirma mavjud")
# =========================

bot = telebot.TeleBot(TOKEN)

user_data = {}            # Mijoz ma'lumotlari
order_history = []        # Buyurtma tarixi
pending_delivery = {}     # Yetkazib berish vaqtini kiritishni kutayotgan buyurtmalar
registered_users = set()  # Bot foydalanuchilari
broadcast_cache = {}      # Admin xabar yuborish uchun
edit_cache = {}           # Admin ma'lumotlarni tahrirlash uchun

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
    edit_btn = types.KeyboardButton("✏️ Ma’lumotlarni taxrirlash")  # Yangi tugma
    markup.add(users_btn, post_btn, edit_btn)
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, "Admin menyu:", reply_markup=markup)

# ================= /start =================
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    if chat_id not in registered_users:
        registered_users.add(chat_id)
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
    bot.send_message(chat_id, PRODUCT_INFO_TEXT)

# ================= Matnli xabarlarni qabul qilish =================
@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()

    # ======= Admin xabar yuborish =======
    if chat_id in ADMIN_IDS and broadcast_cache.get(chat_id, {}).get("step") == "text":
        broadcast_cache[chat_id]["text"] = text
        broadcast_cache[chat_id]["step"] = "confirm"
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add("Ha", "Yo'q")
        bot.send_message(chat_id, f"Xabarni foydalanuvchilarga yuborishni tasdiqlaysizmi?\n\n{text}", reply_markup=markup)
        return

    # ======= Admin xabar yuborish tasdiqlash =======
    if chat_id in ADMIN_IDS and broadcast_cache.get(chat_id, {}).get("step") == "confirm":
        if text.lower() == "ha":
            for user in registered_users:
                bot.send_message(user, broadcast_cache[chat_id]["text"])
            bot.send_message(chat_id, "✅ Xabar foydalanuvchilarga yuborildi.")
            broadcast_cache.pop(chat_id)
            admin_menu()
        elif text.lower() in ["yo'q", "yoq"]:
            bot.send_message(chat_id, "❌ Xabar yuborish bekor qilindi.")
            broadcast_cache.pop(chat_id)
            admin_menu()
        else:
            bot.send_message(chat_id, "❗️ Tasdiqlash uchun 'Ha' yoki 'Yo'q' deb yozing.")
        return

    # ======= Admin buyurtmalarini tasdiqlash =======
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

    # ======= Admin panel buyruqlari =======
    if chat_id not in user_data:
        if chat_id in ADMIN_IDS:
            if text == "👥 Foydalanuvchilar haqida ma’lumot":
                if not registered_users:
                    bot.send_message(chat_id, "Hech qanday foydalanuvchi yo‘q.")
                else:
                    text_list = "\n".join([f"@{user}" if isinstance(user, str) else str(user) for user in registered_users])
                    bot.send_message(chat_id, f"📋 Foydalanuvchilar ro‘yxati:\n{text_list}")
            elif text == "📢 Post yuborish":
                bot.send_message(chat_id, "📨 Xabar matnini kiriting:")
                broadcast_cache[chat_id] = {"step": "text"}
            elif text == "✏️ Ma’lumotlarni taxrirlash":  # Taxrirlash boshlangan
                edit_cache[chat_id] = {"step": "choose"}
                markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
                markup.add("💰 Narxni o‘zgartirish", "💧 Mahsulot ma’lumotini o‘zgartirish")
                bot.send_message(chat_id, "Qaysi ma’lumotni o‘zgartirmoqchisiz?", reply_markup=markup)
        return

    # ======= Admin ma'lumotlarni tahrirlash jarayoni =======
    if chat_id in edit_cache:
        step = edit_cache[chat_id]["step"]
        global PRICE_PER_LITR, PRODUCT_INFO_TEXT

        if step == "choose":
            if text == "💰 Narxni o‘zgartirish":
                edit_cache[chat_id]["step"] = "price"
                bot.send_message(chat_id, f"Hozirgi narx: {PRICE_PER_LITR} so'm\nYangi narxni kiriting:")
            elif text == "💧 Mahsulot ma’lumotini o‘zgartirish":
                edit_cache[chat_id]["step"] = "product_info"
                bot.send_message(chat_id, "Hozirgi mahsulot haqida ma’lumotni kiriting:")
            else:
                bot.send_message(chat_id, "❗️ Iltimos, menyudan tanlang.")
            return
        if step == "price":
            if not text.isdigit():
                bot.send_message(chat_id, "❗️ Iltimos, faqat son kiriting.")
                return
            PRICE_PER_LITR = int(text)
            PRODUCT_INFO_TEXT = (f"💧 Mahsulot: Dizel yoqilg‘isi\n"
                                 f"💰 Narx: {PRICE_PER_LITR} so'm / litr\n"
                                 f"🚚 Yetkazib berish: Buyurtma qabul qilinganidan so‘ng belgilangan vaqtda\n"
                                 f"📦 Chegirmalar: 50 litrdan ortiq buyurtmalarga chegirma mavjud")
            bot.send_message(chat_id, f"✅ Narx muvaffaqiyatli o‘zgartirildi: {PRICE_PER_LITR} so'm")
            edit_cache.pop(chat_id)
            admin_menu()
            return
        if step == "product_info":
            PRODUCT_INFO_TEXT = text
            bot.send_message(chat_id, "✅ Mahsulot haqida ma’lumot muvaffaqiyatli o‘zgartirildi.")
            edit_cache.pop(chat_id)
            admin_menu()
            return

    # ======= Foydalanuvchi buyurtma =======
    if "litr" not in user_data.get(chat_id, {}):
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

    for admin_id in ADMIN_IDS:
        bot.forward_message(admin_id, chat_id, message.message_id)

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
            "username": call.from_user.username or call.from_user.first_name
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
            "delivery_minutes": None
        })
        bot.send_message(user_id, "❌ Afsus, buyurtmangiz rad etildi.")
        bot.answer_callback_query(call.id, "Buyurtma rad qilindi")
        main_menu(user_id)

# ================= Botni ishga tushurish =================
bot.infinity_polling()