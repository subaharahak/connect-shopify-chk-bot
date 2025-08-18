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
        self.load_data()  # Correct method name
        self.register_handlers()
        
        # Rest of your initialization code...

    def load_data(self):  # Corrected method name
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

    # ... [rest of your methods remain unchanged] ...

def run_flask():
    """Run Flask web server"""
    app.run(host='0.0.0.0', port=8080)

def main():
    """Main entry point"""
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    bot = PremiumCcChecker()
    logger.info("🚀 Starting Premium CC Checker Bot")
    bot.run()

if __name__ == '__main__':
    main()
