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

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8228704791:AAH85VvWM1HK0-8EEiJKh533Gc3-ul5r-x8"
MAIN_ADMIN_ID = 5103348494
MAX_CARDS_PER_MCHK = 10
GATEWAY_URL = "https://chk-for-shopify.onrender.com"
# =======================================================

# Configure logging
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
    return "🔥 Premium CC Checker is Operational", 200

@app.route('/ping')
def ping():
    return "pong", 200

class PremiumCcChecker:
    def __init__(self):
        self.bot = telebot.TeleBot(BOT_TOKEN)
        self.load_users()  # Changed from load_data to load_users
        self.register_handlers()
        
        self.START_MESSAGE = """
✨🔥 *𝕊ℍ𝕆ℙ𝕀𝔽𝕐 ℙℝ𝕆 ℂℍ𝔼ℂ�𝔼ℝ 𝕍𝟚* 🔥✨

╔═══════════════════════╗
  💳 *PREMIUM CC CHECKER* 💳  
╚═══════════════════════╝

✧･ﾟ: *✧ Commands ✧* :･ﾟ✧

▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰
🛠️ */chk* - Instant Single Card Check
├─ Format: `/chk 4111111111111111|12|2025|123`
└─ Checks cards in 0.5s lightning speed!

📊 */mchk* - Bulk Mass Checker 
├─ Max 10 cards per batch
└─ Supports .txt files with auto-formatting

🔐 */auth* - Authorize Users/Groups
├─ Format: `/auth user_id` (admin only)
▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰
💎 *VIP Access:* 
Contact @mhitzxg for 
⚡ *Elite Membership* ⚡

🌌 *Current Status:*
✅ Operational | 🚀 Turbo Mode Enabled
"""
        self.PROCESSING_ANIMATION = [
            "🔍 Analyzing Card Patterns...",
            "🔒 Verifying with Payment Gateways...",
            "🌐 Routing Through Global Nodes...",
            "⚡ Finalizing Transaction Check..."
        ]

    def load_users(self):  # Renamed from load_data to load_users
        try:
            with open("authorized.json", "r") as f:
                self.AUTHORIZED_USERS = json.load(f)
        except:
            self.AUTHORIZED_USERS = {}
            
        try:
            with open("admins.json", "r") as f:
                self.ADMIN_IDS = json.load(f)
        except:
            self.ADMIN_IDS = [MAIN_ADMIN_ID]

    def save_data(self):
        with open("authorized.json", "w") as f:
            json.dump(self.AUTHORIZED_USERS, f)
        with open("admins.json", "w") as f:
            json.dump(self.ADMIN_IDS, f)

    # ... [rest of your methods remain exactly the same] ...

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def main():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    bot = PremiumCcChecker()
    logger.info("🚀 Starting Premium CC Checker Bot")
    bot.run()

if __name__ == '__main__':
    main()
