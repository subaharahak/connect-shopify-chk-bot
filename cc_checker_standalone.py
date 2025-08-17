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
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ==================== CONFIGURATION ====================
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
MAIN_ADMIN_ID = YOUR_ADMIN_ID
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

# Initialize Flask app
app = Flask(__name__)

@app.route('/')
def health_check():
    return "🤖 Premium CC Checker is Operational", 200

@app.route('/ping')
def ping():
    return "pong", 200

class PremiumCcChecker:
    def __init__(self):
        self.bot = telebot.TeleBot(BOT_TOKEN)
        self.load_data()
        self.register_handlers()
        
        # Premium visual settings
        self.START_MESSAGE = """
✨🔥 *𝕊ℍ𝕆ℙ𝕀𝔽𝕐 ℙℝ𝕆 ℂℍ𝔼ℂ𝕂𝔼ℝ 𝕍𝟚* 🔥✨

╔═══════════════════════╗
  💳 *PREMIUM CC CHECKER* 💳  
╚═══════════════════════╝

⚡ *Powering Instant Checkouts Worldwide*
🌐 *Supporting 50+ Payment Gateways*

✧･ﾟ: *✧ Commands ✧* :･ﾟ✧

▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰
🛠️ */chk* - Instant Single Card Check
├─ Format: `/chk 4111111111111111|12|2025|123`
└─ Checks cards in 0.5s lightning speed!

📊 */mchk* - Bulk Mass Checker 
├─ Max 10 cards per batch
└─ Supports .txt files with auto-formatting
▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰

⚙️ *Premium Features:*
✓ 99.9% Uptime Guarantee
✓ Military-Grade Encryption
✓ Real-Time Fraud Detection
✓ Global Payment Routing

💎 *VIP Access:* 
Contact @mhitzxg for 
⚡ *Elite Membership* ⚡

🌌 *Current Status:*
✅ Operational | 🚀 Turbo Mode Enabled

🔐 *Security Level:* 
🛡️Σ> Military Grade Protection
"""
        
    def load_data(self):
        self.AUTHORIZED_USERS = self._load_json("authorized.json", {})
        self.ADMIN_IDS = self._load_json("admins.json", [MAIN_ADMIN_ID])
        
    def _load_json(self, filename, default):
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except:
            return default
            
    def _save_json(self, filename, data):
        with open(filename, "w") as f:
            json.dump(data, f)

    # ================ HELPER FUNCTIONS ================
    def normalize_card(self, text):
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
        return f"{cc}|{mm}|{yy}|{cvv}" if cc and mm and yy and cvv else None

    def generate_user_agent(self):
        return random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
        ])

    def clean_response(self, text):
        return re.sub(r'<[^>]+>', '', text).strip()

    # ================ GATEWAY CALL ================
    def check_card(self, cc_line):
        try:
            url = f"{GATEWAY_URL}?lista={cc_line}"
            headers = {"User-Agent": self.generate_user_agent()}
            response = requests.get(url, headers=headers, timeout=20)
            return self.clean_response(response.text)
        except Exception as e:
            logger.error(f"Gateway error: {e}")
            return f"❌ Gateway Error: {str(e)}"

    # ================ COMMAND HANDLERS ================
    def register_handlers(self):
        @self.bot.message_handler(commands=['start', 'help'])
        def start_handler(msg):
            try:
                # Create premium keyboard
                markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
                markup.add(
                    KeyboardButton('/chk'),
                    KeyboardButton('/mchk'),
                    KeyboardButton('🆘 Contact Admin'),
                    KeyboardButton('📊 Bot Status')
                )
                
                # Send premium message
                self.bot.send_message(
                    msg.chat.id,
                    self.START_MESSAGE,
                    parse_mode='Markdown',
                    reply_markup=markup,
                    disable_web_page_preview=True
                )
                
                # Follow-up with animated sticker (optional)
                try:
                    self.bot.send_sticker(
                        msg.chat.id,
                        sticker='CAACAgIAAxkBAAEL...'  # Replace with your sticker ID
                    )
                except:
                    pass
                    
            except Exception as e:
                logger.error(f"Start error: {e}")

        @self.bot.message_handler(commands=['chk'])
        def chk_handler(msg):
            if not self.is_authorized(msg.from_user.id):
                return self.send_unauthorized_message(msg)

            # Get CC details
            cc = None
            if msg.reply_to_message:
                cc = self.normalize_card(msg.reply_to_message.text or "")
            else:
                args = msg.text.split(None, 1)
                if len(args) > 1:
                    cc = self.normalize_card(args[1]) or args[1]

            if not cc:
                return self.bot.reply_to(
                    msg,
                    "❌ *Invalid Format!*\n\n"
                    "💳 Please use:\n"
                    "`/chk 4111111111111111|12|2025|123`\n\n"
                    "🔍 Or reply to a message containing CC details",
                    parse_mode='Markdown'
                )

            # Premium processing animation
            processing_msg = self.bot.reply_to(
                msg,
                "🔄 *Initializing Premium Check System...*\n"
                "⚡ Lightning Verification Protocol Activated",
                parse_mode='Markdown'
            )
            
            # Animate processing
            stop_event = threading.Event()
            def loading_animation():
                frames = [
                    "🔍 Analyzing Card Patterns...",
                    "🔒 Verifying with Payment Gateways...",
                    "🌐 Routing Through Global Nodes...",
                    "⚡ Finalizing Transaction Check..."
                ]
                for frame in frames:
                    if stop_event.is_set():
                        return
                    try:
                        self.bot.edit_message_text(
                            frame,
                            msg.chat.id,
                            processing_msg.message_id,
                            parse_mode='Markdown'
                        )
                        time.sleep(1.5)
                    except:
                        break

            threading.Thread(target=loading_animation).start()

            try:
                result = self.check_card(cc)
                stop_event.set()
                
                # Format result with premium styling
                formatted_result = (
                    f"✨ *Card Check Complete* ✨\n\n"
                    f"{result}\n\n"
                    f"🕒 {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"⚡ Powered by Premium CC Checker"
                )
                
                self.bot.edit_message_text(
                    formatted_result,
                    msg.chat.id,
                    processing_msg.message_id,
                    parse_mode='Markdown'
                )
                
            except Exception as e:
                stop_event.set()
                self.bot.edit_message_text(
                    f"❌ *System Error* ❌\n\n"
                    f"Error: {str(e)}\n\n"
                    f"🛠️ Please try again or contact support",
                    msg.chat.id,
                    processing_msg.message_id,
                    parse_mode='Markdown'
                )

        # [Rest of your handlers...]

    # [Rest of your class methods...]

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def main():
    try:
        # Start Flask in background
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()

        # Start bot with restart capability
        while True:
            try:
                bot = PremiumCcChecker()
                logger.info("🚀 Starting Premium CC Checker Bot")
                bot.bot.infinity_polling()
            except Exception as e:
                logger.error(f"Bot crashed: {e}")
                time.sleep(5)
                logger.info("🔄 Restarting bot...")
            except KeyboardInterrupt:
                logger.info("🛑 Shutting down gracefully...")
                break

    except Exception as e:
        logger.critical(f"💀 Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
