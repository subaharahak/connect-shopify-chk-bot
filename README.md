# CC Checker Telegram Bot

A Telegram bot that uses the `chk.php` file for credit card checking functionality.

## Features

- **Single Card Check**: Use `/chk` command to check individual cards
- **Mass Check**: Use `/mchk` command to check up to 5 cards at once
- **Admin Management**: Add/remove admins with `/addadmin` and `/removeadmin`
- **User Authorization**: Authorize users with `/auth` command
- **Beautiful UI**: Modern interface with Unicode characters

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure the Bot
Edit `cc_checker_bot.py` and update:
- `BOT_TOKEN`: Your Telegram bot token
- `MAIN_ADMIN_ID`: Your Telegram user ID

### 3. Setup PHP Environment
Make sure you have:
- PHP server running (XAMPP, WAMP, or similar)
- `chk.php` file accessible at `http://localhost/chk.php`
- `ua.php` file in the same directory as `chk.php`

### 4. Run the Bot
```bash
python cc_checker_bot.py
```

## Commands

### Admin Commands
- `/addadmin <user_id>` - Add an admin (main admin only)
- `/removeadmin <user_id>` - Remove an admin (main admin only)
- `/listadmins` - List all admins
- `/auth <user_id> [days]` - Authorize a user
- `/rm <user_id>` - Remove user authorization

### User Commands
- `/start` - Welcome message
- `/chk <card>` - Check single card
- `/mchk` - Mass check (reply to file or text)

## Card Format
Cards should be in the format: `card_number|month|year|cvv`

Examples:
- `4556737586899855|12|2026|123`
- `4111111111111111|01|2025|123`

## File Structure
```
├── cc_checker_bot.py    # Main bot file
├── chk.php             # PHP checker file
├── ua.php              # User agent file
├── requirements.txt     # Python dependencies
├── admins.json         # Admin list (auto-generated)
├── authorized.json      # Authorized users (auto-generated)
└── README.md           # This file
```

## Notes

- The bot uses the existing `chk.php` file without modifications
- Only authorized users can use the bot
- Mass check is limited to 5 cards maximum
- Approved cards are automatically sent to the main admin
- The bot supports both file uploads and text replies for mass checking

## Support
Contact: @pr0xy_xd 