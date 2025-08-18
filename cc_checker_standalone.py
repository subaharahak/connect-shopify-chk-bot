import telebot
from flask import Flask
import re
import threading
import time
import json
import requests
import random
import sys
import logging
from telebot.types import (InlineKeyboardMarkup, InlineKeyboardButton, 
                          ReplyKeyboardMarkup, KeyboardButton)

# Configuration
BOT_TOKEN = "8228704791:AAH85VvWM1HK0-8EEiJKh533Gc3-ul5r-x8"
MAIN_ADMIN_ID = 5103348494
MAX_CARDS_PER_MCHK = 10
GATEWAY_URL = "https://chk-for-shopify.onrender.com"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def health_check():
    return "💳 Premium CC Checker is Operational", 200

@app.route('/ping')
def ping():
    return "pong", 200

class PremiumCcChecker:
    def __init__(self):
        self.bot = telebot.TeleBot(BOT_TOKEN)
        self.load_data()
        self.register_handlers()
        
        self.START_MESSAGE = """
╔══💳 *PREMIUM CC CHECKER* 💳══╗
║                              ║
  🔥 *Commands* 🔥  
══════════════════════
🔹 */chk* - Instant Single Card Check
➖ Format: `/chk 4111111111111111|12|2025|123`
➖ Checks cards in 0.5s lightning speed!
📁 */mchk* - Bulk Mass Checker 
➖ Max 10 cards per batch
➖ Supports .txt files with auto-formatting
👑 */auth* - Authorize Users/Groups
➖ Format: `/auth user_id` or `/auth group group_id` (admin only)
══════════════════════
💎 *VIP Access:* 
Contact @mhitzxg for 
⚡ *Elite Membership* ⚡
📊 *Current Status:*
✅ Operational | 🚀 Turbo Mode Enabled
"""
        self.PROCESSING_ANIMATION = [
            "🔍 Analyzing Card Patterns...",
            "🔎 Verifying with Payment Gateways...",
            "🌐 Routing Through Global Nodes...",
            "⚡ Finalizing Transaction Check..."
        ]

    def load_data(self):
        """Load authorized users and admin data"""
        try:
            with open("authorized.json", "r") as f:
                self.AUTHORIZED_ENTITIES = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.AUTHORIZED_ENTITIES = {"users": {}, "groups": {}}
            
        try:
            with open("admins.json", "r") as f:
                self.ADMIN_IDS = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.ADMIN_IDS = [MAIN_ADMIN_ID]

    def save_data(self):
        """Save current data to files"""
        with open("authorized.json", "w") as f:
            json.dump(self.AUTHORIZED_ENTITIES, f, indent=4)
        with open("admins.json", "w") as f:
            json.dump(self.ADMIN_IDS, f, indent=4)

    def is_admin(self, user_id):
        return user_id in self.ADMIN_IDS
        
    def is_authorized(self, user_id, chat_id=None):
        if self.is_admin(user_id):
            return True
        if str(user_id) in self.AUTHORIZED_ENTITIES["users"]:
            expiry = self.AUTHORIZED_ENTITIES["users"][str(user_id)]
            if expiry == "forever" or time.time() < expiry:
                return True
            else:
                del self.AUTHORIZED_ENTITIES["users"][str(user_id)]
                self.save_data()
        
        if chat_id and str(chat_id) in self.AUTHORIZED_ENTITIES["groups"]:
            expiry = self.AUTHORIZED_ENTITIES["groups"][str(chat_id)]
            if expiry == "forever" or time.time() < expiry:
                return True
            else:
                del self.AUTHORIZED_ENTITIES["groups"][str(chat_id)]
                self.save_data()
                
        return False

    # [Previous functions remain unchanged until auth_handler]

    def register_handlers(self):
        """Register all bot command handlers"""
        @self.bot.message_handler(commands=['start', 'help'])
        def start_handler(msg):
            markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            markup.add(
                KeyboardButton('/chk'),
                KeyboardButton('/mchk'),
                KeyboardButton('/auth'),
                KeyboardButton('📞 Contact Admin'),
                KeyboardButton('📊 Bot Status')
            )
            self.bot.send_message(
                msg.chat.id,
                self.START_MESSAGE,
                parse_mode='Markdown',
                reply_markup=markup,
                disable_web_page_preview=True
            )

        @self.bot.message_handler(commands=['auth'])
        def auth_handler(msg):
            if not self.is_admin(msg.from_user.id):
                return self.bot.reply_to(msg, "❌ Admin access required!")
            
            args = msg.text.split()
            if len(args) < 2:
                return self.bot.reply_to(msg, "Usage: /auth user_id OR /auth group group_id")
            
            # Group authorization
            if len(args) >= 3 and args[1].lower() == "group":
                try:
                    group_id = int(args[2])
                    # Telegram group IDs are negative
                    if group_id > 0:
                        group_id = -group_id
                    
                    self.AUTHORIZED_ENTITIES["groups"][str(group_id)] = "forever"
                    self.save_data()
                    
                    return self.bot.reply_to(
                        msg,
                        f"✅ Successfully authorized group {group_id}\n"
                        f"Access granted: Permanent",
                        parse_mode='Markdown'
                    )
                except ValueError:
                    return self.bot.reply_to(msg, "❌ Invalid group ID format! Must be a number.")
            
            # User authorization
            try:
                user_id = int(args[1])
                self.AUTHORIZED_ENTITIES["users"][str(user_id)] = "forever"
                self.save_data()
                
                self.bot.reply_to(
                    msg,
                    f"✅ Successfully authorized user {user_id}\n"
                    f"Access granted: Permanent",
                    parse_mode='Markdown'
                )
            except ValueError:
                return self.bot.reply_to(msg, "❌ Invalid user ID format! Must be a number.")

        # [Rest of your existing handlers remain unchanged]
        # Make sure to update any command handlers to use the new is_authorized check
        # For example in chk_handler:
        @self.bot.message_handler(commands=['chk'])
        def chk_handler(msg):
            chat_id = msg.chat.id if msg.chat.type in ['group', 'supergroup'] else None
            if not self.is_authorized(msg.from_user.id, chat_id):
                return self.send_unauthorized_message(msg)
            
            # Rest of your chk_handler implementation...

# [Rest of your Flask and main functions remain unchanged]

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def main():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    bot = PremiumCcChecker()
    logger.info("🚀 Starting Premium CC Checker Bot")
    bot.bot.polling(none_stop=True)

if __name__ == '__main__':
    main()
