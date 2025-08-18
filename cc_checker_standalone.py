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

    # ... [keep all existing methods unchanged until start_mass_check] ...

    def start_mass_check(self, chat_id, cc_lines):
        total = len(cc_lines)
        approved = declined = checked = 0
        processing_delay = 1.2  # Optimal delay between checks

        # Beautiful initial message with ASCII art
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
            # Enhanced card result format
            emoji = "✅" if status == "APPROVED" else "❌"
            header = f"{emoji} *CARD {index}/{total} - {status}* {emoji}"
            
            # Format the card info beautifully
            cc_parts = cc.split('|')
            card_info = f"""
💳 *Card Number:* `{cc_parts[0]}`
📅 *Expiry:* `{cc_parts[1]}/{cc_parts[2]}`
🔒 *CVV:* `{cc_parts[3]}`

🔄 *Response:*
{result}
"""
            # Add processing time and footer
            footer = f"""
⏱️ *Processed in:* `{random.uniform(0.8, 1.5):.2f}s`
🕒 {time.strftime('%H:%M:%S')}
⚡ *Powered by Premium CC Checker*
"""
            return f"{header}\n{card_info}\n{footer}"

        def process_cards():
            nonlocal approved, declined, checked
            
            results = []
            for index, cc in enumerate(cc_lines, 1):
                try:
                    checked = index
                    # Small delay to prevent rate limiting
                    time.sleep(processing_delay)
                    
                    # Process the card
                    raw_result = self.check_card(cc)
                    clean_result = self.clean_response(raw_result)
                    
                    # Determine status
                    if any(x in clean_result for x in ["CHARGED", "CVV MATCH", "APPROVED"]):
                        approved += 1
                        status = "APPROVED"
                    else:
                        declined += 1
                        status = "DECLINED"
                    
                    # Send beautiful formatted result
                    result_msg = send_card_result(index, total, cc, clean_result, status)
                    self.bot.send_message(
                        chat_id,
                        result_msg,
                        parse_mode='Markdown'
                    )
                    
                    # Update progress every 3 cards
                    if index % 3 == 0 or index == total:
                        progress = f"""
▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰
⚡ *PROGRESS UPDATE* ⚡

📊 *Processed:* `{index}/{total}`
✅ *Approved:* `{approved}`
❌ *Declined:* `{declined}`
⏳ *Remaining:* `{total - index}`
▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰
"""
                        self.bot.send_message(chat_id, progress, parse_mode='Markdown')
                    
                except Exception as e:
                    logger.error(f"Error processing card {index}: {e}")
                    error_msg = f"""
⚠️ *ERROR PROCESSING CARD {index}* ⚠️

🛠️ *Details:* `{str(e)}`
🔧 *System:* Auto-retry in next batch
"""
                    self.bot.send_message(chat_id, error_msg, parse_mode='Markdown')
                    continue
            
            # Final beautiful summary
            success_rate = (approved/total)*100 if total > 0 else 0
            summary = f"""
╔══════════════════════╗
  🏁 *MASS CHECK COMPLETE* 🏁  
╚══════════════════════╝

🎯 *Final Statistics:*
▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰
📊 *Total Cards:* `{total}`
✅ *Approved:* `{approved}` ({success_rate:.2f}%)
❌ *Declined:* `{declined}`
⏱️ *Total Time:* `{total * processing_delay:.2f}s`
▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰

⚡ *System Shutdown:* `NORMAL`
🕒 *Completed at:* {time.strftime('%H:%M:%S')}

💎 *Thank you for using Premium CC Checker*
            """
            self.bot.send_message(chat_id, summary, parse_mode='Markdown')

        # Start processing in a new thread
        threading.Thread(target=process_cards).start()

    # ... [keep all other methods unchanged] ...

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def main():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    while True:
        try:
            bot = PremiumCcChecker()
            logger.info("🚀 Starting Premium CC Checker Bot")
            bot.run()
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            time.sleep(5)
            logger.info("🔄 Restarting bot...")
        except KeyboardInterrupt:
            logger.info("🛑 Shutting down gracefully...")
            break

if __name__ == '__main__':
    main()
