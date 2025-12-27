import os import sqlite3 import telebot from telebot import types from threading import Timer

=========================

TOKEN = os.getenv("BOT_TOKEN") ADMIN_IDS = {6419271223, 6994628664} ADMIN_USERNAMES = {"dizel_go", "admin2"} PRICE_PER_LITR = 10500 DISCOUNT_LITR = 50 DISCOUNT_PERCENT = 10  # 50 litrdan ortiq buyurtmaga 10% chegirma TIMEOUT_SECONDS = 1800  # 30 daqiqa timeout

=========================

bot = telebot.TeleBot(TOKEN)

================= SQLite =================

conn = sqlite3.connect('bot.db', check_same_thread=False) cursor = conn.cursor()

cursor.execute(''' CREATE TABLE IF NOT EXISTS users ( user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT )''')

cursor.execute(''' CREATE TABLE IF NOT EXISTS orders ( id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, litrs INTEGER, phone TEXT, location_lat REAL, location_lon REAL, status TEXT, delivery_minutes INTEGER, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP )''')

conn.commit()

================= Temp memory =================

broadcast_cache = {}  # admin_id -> {step, text} pending_orders = {}   # admin_id -> list of orders user_timeout = {}     # user_id -> Timer

================= Helpers =================

def start_timeout(user_id): def timeout(): if user_id in user_timeout: bot.send_message(user_id, "⏱️ Vaqt tugadi. Buyurtma bekor qilindi.") cursor.execute('DELETE FROM orders WHERE user_id=? AND status="pending"', (user_id,)) conn.commit() if user_id in user_timeout: del user_timeout[user_id] timer = Timer(TIMEOUT_SECONDS, timeout) timer.start() user_timeout[user_id] = timer

def cancel_timeout(user_id): if user_id in user_timeout: user_timeout[user_id].cancel() del user_timeout[user_id]

def calculate_price(litrs): price = litrs * PRICE_PER_LITR if litrs >= DISCOUNT_LITR: price -= price * DISCOUNT_PERCENT / 100 return price

def main_menu(chat_id): markup = types.ReplyKeyboardMarkup(resize_keyboard=True) markup.add("📦 Buyurtma berish", "📞 Admin bilan bog‘lanish") markup.add("ℹ️ Mahsulot haqida ma’lumot") bot.send_message(chat_id, "Asosiy menyu:", reply_markup=markup)

def admin_menu(admin_id): markup = types.ReplyKeyboardMarkup(resize_keyboard=True) markup.add("👥 Foydalanuvchilar", "📢 Post yuborish") markup.add("📋 Buyurtmalar ro‘yxati") bot.send_message(admin_id, "Admin menyu:", reply_markup=markup)

================= Start =================

@bot.message_handler(commands=['start']) def start(message): user_id = message.chat.id cursor.execute('INSERT OR IGNORE INTO users (user_id, first_name, username) VALUES (?, ?, ?)', (user_id, message.from_user.first_name, message.from_user.username)) conn.commit()

bot.send_message(user_id, f"Assalomu alaykum, {message.from_user.first_name}! Botimizga xush kelibsiz.")

if user_id in ADMIN_IDS:
    admin_menu(user_id)
else:
    main_menu(user_id)

================= Buyurtma =================

@bot.message_handler(func=lambda m: m.text == "📦 Buyurtma berish") def order_start(message): user_id = message.chat.id cursor.execute('INSERT INTO orders (user_id, status) VALUES (?, ?)', (user_id, 'pending')) conn.commit() start_timeout(user_id) bot.send_message(user_id, "Necha litr dizel kerak? (faqat son kiriting)")

================= Mahsulot info =================

@bot.message_handler(func=lambda m: m.text == "ℹ️ Mahsulot haqida ma’lumot") def product_info(message): info_text = (f"💧 Mahsulot: Dizel yoqilg‘isi\n" f"💰 Narx: {PRICE_PER_LITR} so'm / litr\n" f"🚚 Yetkazib berish: Buyurtma qabul qilinganidan so‘ng\n" f"📦 Chegirmalar: {DISCOUNT_LITR} litrdan ortiq buyurtmalarga {DISCOUNT_PERCENT}%") bot.send_message(message.chat.id, info_text)

================= Admin bilan bog‘lanish =================

@bot.message_handler(func=lambda m: m.text == "📞 Admin bilan bog‘lanish") def contact_admin(message): admins_text = "\n".join([f"@{u}" for u in ADMIN_USERNAMES]) bot.send_message(message.chat.id, f"Adminlar bilan bog‘lanish:\n{admins_text}")

================= Text handler =================

@bot.message_handler(content_types=['text']) def handle_text(message): user_id = message.chat.id text = message.text.strip()

# ================== Admin menu ==================
if user_id in ADMIN_IDS:
    if text == "👥 Foydalanuvchilar":
        cursor.execute('SELECT user_id, first_name, username FROM users')
        users = cursor.fetchall()
        if not users:
            bot.send_message(user_id, "Hech qanday foydalanuvchi yo'q.")
        else:
            users_list = "\n".join([f"{u[1]} (@{u[2]})" if u[2] else u[1] for u in users])
            bot.send_message(user_id, f"📋 Foydalanuvchilar:\n{users_list}")
        return
    elif text == "📢 Post yuborish":
        broadcast_cache[user_id] = {'step': 'text'}
        bot.send_message(user_id, "Xabar matnini kiriting:", reply_markup=types.ReplyKeyboardRemove())
        return
    elif text == "📋 Buyurtmalar ro‘yxati":
        cursor.execute('SELECT user_id, litrs, phone, status FROM orders')
        orders = cursor.fetchall()
        if not orders:
            bot.send_message(user_id, "Hozircha buyurtma yo'q.")
        else:
            msg = "\n".join([f"UserID: {o[0]}, Litrs: {o[1]}, Phone: {o[2]}, Status: {o[3]}" for o in orders])
            bot.send_message(user_id, msg)
        return

# ================== Foydalanuvchi buyurtma ==================
cursor.execute('SELECT id, litrs, phone, location_lat, location_lon, status FROM orders WHERE user_id=? AND status="pending"', (user_id,))
order = cursor.fetchone()
if order:
    order_id = order[0]
    if not order[1]:
        if not text.isdigit():
            bot.send_message(user_id, "❗️ Iltimos, faqat son kiriting (litr).")
            return
        cursor.execute('UPDATE orders SET litrs=? WHERE id=?', (int(text), order_id))
        conn.commit()
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add(types.KeyboardButton("📍 Lokatsiya yuborish", request_location=True))
        bot.send_message(user_id, "📍 Endi lokatsiya yuboring:", reply_markup=markup)
        return
    elif not order[2]:
        # Telefon raqam matn shaklida emas, keyin kontakt bilan o'zgartiriladi
        cursor.execute('UPDATE orders SET phone=? WHERE id=?', (text, order_id))
        conn.commit()
        bot.send_message(user_id, "📨 Buyurtmangiz operatorga yuborildi. Tez orada javob beramiz.")
        main_menu(user_id)
        return

================= Location handler =================

@bot.message_handler(content_types=['location']) def handle_location(message): user_id = message.chat.id cursor.execute('SELECT id FROM orders WHERE user_id=? AND status="pending"', (user_id,)) order = cursor.fetchone() if order: order_id = order[0] loc = message.location cursor.execute('UPDATE orders SET location_lat=?, location_lon=? WHERE id=?', (loc.latitude, loc.longitude, order_id)) conn.commit() bot.send_message(user_id, "📞 Endi telefon raqamingizni yuboring:") # Adminlarga xabar cursor.execute('SELECT litrs, phone FROM orders WHERE id=?', (order_id,)) order_info = cursor.fetchone() litrs, phone = order_info markup = types.InlineKeyboardMarkup() markup.add(types.InlineKeyboardButton("✅ Qabul qilish", callback_data=f"accept_{order_id}"), types.InlineKeyboardButton("❌ Rad qilish", callback_data=f"reject_{order_id}")) for admin_id in ADMIN_IDS: bot.send_message(admin_id, f"🆕 Yangi buyurtma\nUserID: {user_id}\nLitrs: {litrs}\nPhone: {phone}", reply_markup=markup)

================= Callback =================

@bot.callback_query_handler(func=lambda call: True) def callback_handler(call): data = call.data if data.startswith("accept_") or data.startswith("reject_"): order_id = int(data.split('')[1]) admin_id = call.message.chat.id cursor.execute('SELECT user_id, litrs, phone FROM orders WHERE id=?', (order_id,)) order = cursor.fetchone() if not order: bot.answer_callback_query(call.id, "Buyurtma topilmadi") return user_id, litrs, phone = order if data.startswith("accept"): # Admindan yetkazish vaqti so‘rash pending_orders.setdefault(admin_id, []).append(order_id) bot.send_message(admin_id, "⏱️ Necha daqiqada yetkaziladi? (faqat son kiriting)") bot.answer_callback_query(call.id, "Buyurtma qabul qilindi") else: cursor.execute('UPDATE orders SET status="rad qilindi" WHERE id=?', (order_id,)) conn.commit() bot.send_message(user_id, "❌ Afsus, buyurtmangiz rad etildi.") bot.answer_callback_query(call.id, "Buyurtma rad qilindi")

================= Admin yetkazish vaqti =================

@bot.message_handler(func=lambda m: m.chat.id in pending_orders and m.text.isdigit()) def delivery_time(message): admin_id = message.chat.id minutes = int(message.text) order_ids = pending_orders.pop(admin_id, []) for oid in order_ids: cursor.execute('UPDATE orders SET status="qabul qilindi", delivery_minutes=? WHERE id=?', (minutes, oid)) cursor.execute('SELECT user_id, litrs FROM orders WHERE id=?', (oid,)) user_id, litrs = cursor.fetchone() price = calculate_price(litrs) bot.send_message(user_id, f"✅ Buyurtmangiz qabul qilindi!\n💧 Litr: {litrs}\n💰 Narx: {price} so'm\n⏱️ Taxminiy yetkazib berish: {minutes} daqiqa") conn.commit() bot.send_message(admin_id, f"✅ Yetkazib berish vaqti saqlandi: {minutes} daqiqa")

================= Run =================

bot.infinity_polling(skip_pending=False)