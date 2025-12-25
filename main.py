import os
import telebot
from telebot import types

# =========================
TOKEN = os.getenv("BOT_TOKEN")  # 🔥 TOKEN serverdan olinadi
ADMIN_ID = 6419271223           # Admin Telegram ID
ADMIN_USERNAME = "admin_nik"    # Telegram username @dizel_go
PRICE_PER_LITR = 10500
# =========================

bot = telebot.TeleBot(TOKEN)

user_data = {}            # Mijoz ma'lumotlari
order_history = []        # Buyurtma tarixi
pending_delivery = {}     # Yetkazib berish vaqtini kiritishni kutayotgan buyurtmalar
registered_users = set()  # Bot foydalanuvchilari
broadcast_cache = {}      # Admin xabar yuborish uchun

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
    bot.send_message(ADMIN_ID, "Admin menyu:", reply_markup=markup)

# ================= /start =================
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    if chat_id not in registered_users:
        registered_users.add(chat_id)
        bot.send_message(chat_id, f"Assalomu alaykum, {message.from_user.first_name}!\nBotimizga xush kelibsiz!")
    if chat_id == ADMIN_ID:
        admin_menu()
    else:
        main_menu(chat_id)

# ================= Buyurtma berish =================
@bot.message_handler(func=lambda m: m.text == "📦 Buyurtma berish")
def order_start(message):
    chat_id = message.chat.id
    user_data[chat_id] = {}
    bot.send_message(chat_id, "Necha litr dizel buyurtma qilmoqchisiz ? (faqat son kiriting)")

# ================= Admin bilan bog‘lanish =================
@bot.message_handler(func=lambda m: m.text == "📞 Admin bilan bog‘lanish")
def contact_admin(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, f"Admin bilan bog‘lanish: @{ADMIN_USERNAME}")

# ================= Mahsulot haqida ma’lumot =================
@bot.message_handler(func=lambda m: m.text == "ℹ️ Mahsulot haqida ma’lumot")
def product_info(message):
    chat_id = message.chat.id
    info = (f"💧 Mahsulot: Dizel yoqilg‘isi\n"
            f"💰 Narx: {PRICE_PER_LITR} so'm / litr\n"
            f"🚚 Yetkazib berish: Buyurtma qabul qilinganidan so‘ng belgilangan vaqtda\n"
            f"📦 Chegirmalar: 1000 litrdan ortiq buyurtmalarga chegirma mavjud")
    bot.send_message(chat_id, info)

# ================= Matnli xabarlarni qabul qilish =================
@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()

    # Handling order quantity input
    if chat_id in user_data and 'order_quantity' not in user_data[chat_id]:
        try:
            order_quantity = int(text)
            if order_quantity > 0:
                user_data[chat_id]['order_quantity'] = order_quantity
                total_price = order_quantity * PRICE_PER_LITR
                bot.send_message(chat_id, f"Buyurtma miqdori: {order_quantity} litr\n"
                                         f"Jami narx: {total_price} so'm\n"
                                         "Buyurtmani tasdiqlash uchun ✅ tugmasini bosing.")
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                confirm_btn = types.KeyboardButton("✅ Tasdiqlash")
                cancel_btn = types.KeyboardButton("❌ Bekor qilish")
                markup.add(confirm_btn, cancel_btn)
                bot.send_message(chat_id, "Buyurtmani tasdiqlaysizmi?", reply_markup=markup)
            else:
                bot.send_message(chat_id, "Iltimos, musbat son kiriting.")
        except ValueError:
            bot.send_message(chat_id, "Iltimos, faqat son kiriting.")
        return

    # Handling order confirmation or cancellation
    if text == "✅ Tasdiqlash":
        if chat_id in user_data and 'order_quantity' in user_data[chat_id]:
            order_quantity = user_data[chat_id]['order_quantity']
            total_price = order_quantity * PRICE_PER_LITR
            order_history.append({'chat_id': chat_id, 'quantity': order_quantity, 'total_price': total_price})
            bot.send_message(chat_id, f"Buyurtmangiz tasdiqlandi! Jami narx: {total_price} so'm.")
            del user_data[chat_id]  # Clear order data
        main_menu(chat_id)

    elif text == "❌ Bekor qilish":
        bot.send_message(chat_id, "Buyurtma bekor qilindi.")
        del user_data[chat_id]  # Clear order data
        main_menu(chat_id)

    # Admin broadcast functionality
    elif chat_id == ADMIN_ID and text.startswith("/broadcast"):
        message_text = text[len("/broadcast "):]  # Extract the message after /broadcast
        if message_text:
            for user in registered_users:
                try:
                    bot.send_message(user, message_text)
                except Exception as e:
                    print(f"Error sending message to {user}: {e}")
            bot.send_message(chat_id, "Xabar barcha foydalanuvchilarga yuborildi.")
        else:
            bot.send_message(chat_id, "Xabarni kiriting.")

    # Admin view user data
    elif chat_id == ADMIN_ID and text == "👥 Foydalanuvchilar haqida ma’lumot":
        users_info = "\n".join([f"Foydalanuvchi: {user}" for user in registered_users])
        bot.send_message(chat_id, f"Foydalanuvchilar:\n{users_info if users_info else 'Hech qanday foydalanuvchi yo‘q.'}")

# ================= Botni ishga tushurish =================
bot.infinity_polling()
