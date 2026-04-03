# encryptedhash# Telegram Bot

Telegram bot version of encryptedhash tool.

## Features

- Base64 encode/decode
- URL encode/decode
- Text <-> Binary
- Text <-> Octal
- Fernet key insert (string or key file path)
- Fernet key generation (`secret.key` + key string output)
- Encrypt/decrypt with Fernet
- SHA-256 hashing

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a Telegram bot with [@BotFather](https://t.me/BotFather) and copy the token.

3. Set environment variable:

### Windows PowerShell

```powershell
$env:TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN_HERE"
```

4. Run bot:

```bash
python "tgencrypt.py"
```

## Usage

- Open your bot chat in Telegram.
- Send `/start`.
- Tap any menu button and send your input text.

## Important

- Keep your bot token private.
