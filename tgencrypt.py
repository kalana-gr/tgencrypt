import base64
import hashlib
import os
from urllib.parse import quote, unquote

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None


KEY_FILE = "secret.key"


def base64_encode_text(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def base64_decode_text(encoded_text: str) -> str:
    raw_bytes = base64.b64decode(encoded_text.encode("ascii"), validate=True)
    return raw_bytes.decode("utf-8")


def url_encode_text(text: str) -> str:
    return quote(text)


def url_decode_text(encoded_text: str) -> str:
    return unquote(encoded_text)


def text_to_binary(text: str) -> str:
    return " ".join(format(ord(ch), "08b") for ch in text)


def binary_to_text(binary_text: str) -> str:
    parts = binary_text.strip().split()
    chars = []
    for part in parts:
        if not all(bit in "01" for bit in part):
            raise ValueError(f"Invalid binary value: {part}")
        chars.append(chr(int(part, 2)))
    return "".join(chars)


def text_to_octal(text: str) -> str:
    return " ".join(format(ord(ch), "o") for ch in text)


def octal_to_text(octal_text: str) -> str:
    parts = octal_text.strip().split()
    chars = []
    for part in parts:
        if not all(d in "01234567" for d in part):
            raise ValueError(f"Invalid octal value: {part}")
        chars.append(chr(int(part, 8)))
    return "".join(chars)


def sha256_hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ensure_fernet_installed() -> None:
    if Fernet is None:
        raise ImportError("cryptography is not installed. Run: pip install cryptography")


def parse_fernet_key(key_text: str) -> bytes:
    ensure_fernet_installed()
    key_bytes = key_text.strip().encode("ascii")
    Fernet(key_bytes)
    return key_bytes


def generate_and_save_key() -> str:
    ensure_fernet_installed()
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key.decode("ascii")


def load_key() -> bytes:
    with open(KEY_FILE, "rb") as f:
        return f.read().strip()


def load_key_from_file(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read().strip()


def encrypt_message(message: str, key: bytes) -> str:
    ensure_fernet_installed()
    return Fernet(key).encrypt(message.encode("utf-8")).decode("ascii")


def decrypt_message(token_text: str, key: bytes) -> str:
    ensure_fernet_installed()
    return Fernet(key).decrypt(token_text.encode("ascii")).decode("utf-8")


def get_effective_key(context: ContextTypes.DEFAULT_TYPE) -> bytes:
    if context.user_data.get("session_key"):
        return context.user_data["session_key"]
    return load_key()


MENU_KEYS = [
    ["Base64 Encode", "Base64 Decode"],
    ["URL Encode", "URL Decode"],
    ["Text -> Binary", "Binary -> Text"],
    ["Text -> Octal", "Octal -> Text"],
    ["Insert Fernet Key", "Generate Fernet Key"],
    ["Encrypt Message", "Decrypt Message"],
    ["SHA-256 Hash", "Help"],
]

ACTION_LABELS = {
    "Base64 Encode",
    "Base64 Decode",
    "URL Encode",
    "URL Decode",
    "Text -> Binary",
    "Binary -> Text",
    "Text -> Octal",
    "Octal -> Text",
    "Insert Fernet Key",
    "Generate Fernet Key",
    "Encrypt Message",
    "Decrypt Message",
    "SHA-256 Hash",
    "Help",
}


def menu_markup() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(MENU_KEYS, resize_keyboard=True)


HELP_TEXT = (
    "Send /start to show menu.\n"
    "Tap a button, then send input text.\n\n"
    "Fernet key tips:\n"
    "- Insert Fernet Key: send key string OR key file path OR default/secret.key/secret\n"
    "- Generate Fernet Key: creates secret.key and sends key string\n\n"
    "SHA-256 is one-way and cannot be decrypted."
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["pending_action"] = None
    await update.message.reply_text(
        "Welcome to encryptedhash# Telegram bot.\nChoose an option:",
        reply_markup=menu_markup(),
    )


async def select_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str) -> None:
    context.user_data["pending_action"] = action
    prompts = {
        "Base64 Encode": "Send text to Base64 encode:",
        "Base64 Decode": "Send Base64 text to decode:",
        "URL Encode": "Send text to URL encode:",
        "URL Decode": "Send URL-encoded text to decode:",
        "Text -> Binary": "Send text to convert into binary:",
        "Binary -> Text": "Send space-separated binary values:",
        "Text -> Octal": "Send text to convert into octal:",
        "Octal -> Text": "Send space-separated octal values:",
        "Insert Fernet Key": (
            "Send Fernet key string OR key file path.\n"
            "You can also send: default / secret.key / secret"
        ),
        "Encrypt Message": "Send message to encrypt:",
        "Decrypt Message": "Send token to decrypt:",
        "SHA-256 Hash": "Send text to hash:",
    }
    await update.message.reply_text(prompts[action], reply_markup=menu_markup())


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    if not text:
        return

    if text == "Help":
        context.user_data["pending_action"] = None
        await update.message.reply_text(HELP_TEXT, reply_markup=menu_markup())
        return

    if text == "Generate Fernet Key":
        try:
            key_str = generate_and_save_key()
            context.user_data["session_key"] = key_str.encode("ascii")
            await update.message.reply_text(
                f"Key saved to '{KEY_FILE}'.\nKey string:\n{key_str}\n\nSession key set.",
                reply_markup=menu_markup(),
            )
        except Exception as e:
            await update.message.reply_text(f"Error: {e}", reply_markup=menu_markup())
        return

    if text in ACTION_LABELS and text != "Generate Fernet Key":
        await select_action(update, context, text)
        return

    action = context.user_data.get("pending_action")
    if action is None:
        await update.message.reply_text(
            "Choose an option first from the menu or use /start.",
            reply_markup=menu_markup(),
        )
        return

    try:
        if action == "Base64 Encode":
            await update.message.reply_text(
                f"Encoded:\n{base64_encode_text(text)}", reply_markup=menu_markup()
            )
        elif action == "Base64 Decode":
            await update.message.reply_text(
                f"Decoded:\n{base64_decode_text(text)}", reply_markup=menu_markup()
            )
        elif action == "URL Encode":
            await update.message.reply_text(
                f"Encoded:\n{url_encode_text(text)}", reply_markup=menu_markup()
            )
        elif action == "URL Decode":
            await update.message.reply_text(
                f"Decoded:\n{url_decode_text(text)}", reply_markup=menu_markup()
            )
        elif action == "Text -> Binary":
            await update.message.reply_text(
                f"Binary:\n{text_to_binary(text)}", reply_markup=menu_markup()
            )
        elif action == "Binary -> Text":
            await update.message.reply_text(
                f"Text:\n{binary_to_text(text)}", reply_markup=menu_markup()
            )
        elif action == "Text -> Octal":
            await update.message.reply_text(
                f"Octal:\n{text_to_octal(text)}", reply_markup=menu_markup()
            )
        elif action == "Octal -> Text":
            await update.message.reply_text(
                f"Text:\n{octal_to_text(text)}", reply_markup=menu_markup()
            )
        elif action == "Insert Fernet Key":
            ensure_fernet_installed()
            lowered = text.lower()
            if lowered in {"default", "secret.key", "secret"}:
                key_bytes = load_key()
                Fernet(key_bytes)
                context.user_data["session_key"] = key_bytes
                await update.message.reply_text(
                    f"Session key loaded from '{KEY_FILE}'.", reply_markup=menu_markup()
                )
            elif os.path.exists(text):
                key_bytes = load_key_from_file(text)
                Fernet(key_bytes)
                context.user_data["session_key"] = key_bytes
                await update.message.reply_text(
                    f"Session key loaded from file: {text}", reply_markup=menu_markup()
                )
            else:
                context.user_data["session_key"] = parse_fernet_key(text)
                await update.message.reply_text(
                    "Session key set from pasted key.", reply_markup=menu_markup()
                )
        elif action == "Encrypt Message":
            key = get_effective_key(context)
            await update.message.reply_text(
                f"Encrypted token:\n{encrypt_message(text, key)}", reply_markup=menu_markup()
            )
        elif action == "Decrypt Message":
            key = get_effective_key(context)
            await update.message.reply_text(
                f"Decrypted message:\n{decrypt_message(text, key)}",
                reply_markup=menu_markup(),
            )
        elif action == "SHA-256 Hash":
            await update.message.reply_text(
                f"SHA-256:\n{sha256_hash_text(text)}\n\n"
                "Reminder: hashes are one-way and cannot be decrypted.",
                reply_markup=menu_markup(),
            )
    except FileNotFoundError:
        await update.message.reply_text(
            f"Error: '{KEY_FILE}' not found. Insert key or generate one first.",
            reply_markup=menu_markup(),
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {e}", reply_markup=menu_markup())


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("Set TELEGRAM_BOT_TOKEN environment variable before running.")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()
import base64
import hashlib
import os
from urllib.parse import quote, unquote

try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None


KEY_FILE = "secret.key"


#-------------------------
# Base64 encode / decode
# -------------------------
def base64_encode_text(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def base64_decode_text(encoded_text: str) -> str:
    raw_bytes = base64.b64decode(encoded_text.encode("ascii"), validate=True)
    return raw_bytes.decode("utf-8")


# -------------------------
# URL encode / decode
# -------------------------
def url_encode_text(text: str) -> str:
    return quote(text)


def url_decode_text(encoded_text: str) -> str:
    return unquote(encoded_text)


# -------------------------
# Binary conversion
# -------------------------
def text_to_binary(text: str) -> str:
    return " ".join(format(ord(ch), "08b") for ch in text)


def binary_to_text(binary_text: str) -> str:
    parts = binary_text.strip().split()
    chars = []
    for part in parts:
        if not all(bit in "01" for bit in part):
            raise ValueError(f"Invalid binary value: {part}")
        value = int(part, 2)
        chars.append(chr(value))
    return "".join(chars)


# -------------------------
# Octal conversion
# -------------------------
def text_to_octal(text: str) -> str:
    return " ".join(format(ord(ch), "o") for ch in text)


def octal_to_text(octal_text: str) -> str:
    parts = octal_text.strip().split()
    chars = []
    for part in parts:
        if not all(d in "01234567" for d in part):
            raise ValueError(f"Invalid octal value: {part}")
        value = int(part, 8)
        chars.append(chr(value))
    return "".join(chars)


# ------------------------
# Fernet key encryption
# ------------------------
def parse_fernet_key(key_text: str) -> bytes:
    """
    Takes a Fernet key you paste in (usually a 44-char string) and validates it.
    Returns the key as bytes if valid.
    """
    if Fernet is None:
        raise ImportError("cryptography is not installed. Run: pip install cryptography")
    key_bytes = key_text.strip().encode("ascii")
    # Creating a Fernet object will validate key format.
    Fernet(key_bytes)
    return key_bytes


def generate_and_save_key() -> str:
    if Fernet is None:
        raise ImportError("cryptography is not installed. Run: pip install cryptography")
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key.decode("ascii")


def load_key() -> bytes:
    with open(KEY_FILE, "rb") as f:
        return f.read()


def load_key_from_file(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read().strip()


def encrypt_message(message: str, key: bytes) -> str:
    if Fernet is None:
        raise ImportError("cryptography is not installed. Run: pip install cryptography")
    fernet = Fernet(key)
    token = fernet.encrypt(message.encode("utf-8"))
    return token.decode("ascii")


def decrypt_message(token_text: str, key: bytes) -> str:
    if Fernet is None:
        raise ImportError("cryptography is not installed. Run: pip install cryptography")
    fernet = Fernet(key)
    message = fernet.decrypt(token_text.encode("ascii"))
    return message.decode("utf-8")


# -------------------------
# SHA-256 hashing
# -------------------------
def sha256_hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def print_menu() -> None:
    print("\n=== encryptedhash# ===")
    print("1. Base64 Encode")
    print("2. Base64 Decode")
    print("3. URL Encode")
    print("4. URL Decode")
    print("5. Text -> Binary")
    print("6. Binary -> Text")
    print("7. Text -> Octal")
    print("8. Octal -> Text")
    print("9. Insert Fernet Secret Key (String or file)")
    print("10. Generate Fernet Key (secret.key)")
    print("11. Encrypt Message (Fernet)")
    print("12. Decrypt Message (Fernet)")
    print("13. SHA-256 Hash")
    print("14. Exit")


def main() -> None:
    session_key: bytes | None = None

    # Main program loop
    while True:
        print_menu()
        choice = input("Choose an option (1-14): ").strip()

        try:
            if choice == "1":
                text = input("Enter text to Base64 encode: ")
                print("Encoded:", base64_encode_text(text))

            elif choice == "2":
                text = input("Enter Base64 text to decode: ")
                print("Decoded:", base64_decode_text(text))

            elif choice == "3":
                text = input("Enter text to URL encode: ")
                print("Encoded:", url_encode_text(text))

            elif choice == "4":
                text = input("Enter URL-encoded text to decode: ")
                print("Decoded:", url_decode_text(text))

            elif choice == "5":
                text = input("Enter text to convert to binary: ")
                print("Binary:", text_to_binary(text))

            elif choice == "6":
                text = input("Enter binary values: ")
                print("Text:", binary_to_text(text))

            elif choice == "7":
                text = input("Enter text to convert to octal: ")
                print("Octal:", text_to_octal(text))

            elif choice == "8":
                text = input("Enter octal values: ")
                print("Text:", octal_to_text(text))

            elif choice == "9":
                if Fernet is None:
                    raise ImportError(
                        "cryptography is not installed. Run: pip install cryptography"
                    )
                key_input = input(
                    "Paste key OR type key file path/name (ex: default/secret.key): "
                ).strip()
                if not key_input:
                    print("No key provided.")
                elif os.path.exists(key_input):
                    session_key = load_key_from_file(key_input)
                    # Validating it is a real Fernet key
                    Fernet(session_key)
                    print(f"Session key loaded from file: {key_input}")
                elif key_input.lower() in {"default", "secret.key", "secret"}:
                    session_key = load_key()
                    Fernet(session_key)
                    print(f"Session key loaded from '{KEY_FILE}'.")
                else:
                    session_key = parse_fernet_key(key_input)
                    print("Session key set from pasted key. (This does not write to disk.)")

            elif choice == "10":
                key_str = generate_and_save_key()
                print(f"Key generated and saved to '{KEY_FILE}'.")
                print("Copy/paste key (string):", key_str)

            elif choice == "11":
                text = input("Enter message to encrypt: ")
                key = session_key if session_key is not None else load_key()
                print("Encrypted token:", encrypt_message(text, key))

            elif choice == "12":
                text = input("Enter encrypted token to decrypt: ")
                key = session_key if session_key is not None else load_key()
                print("Decrypted message:", decrypt_message(text, key))

            elif choice == "13":
                text = input("Enter text to hash with SHA-256: ")
                print("SHA-256:", sha256_hash_text(text))
                print("Reminder: hashes are one-way and cannot be decrypted.")

            elif choice == "14":
                print("Exiting encryptedhash#. Goodbye!")
                break

            else:
                print("Invalid choice. Please enter a number from 1 to 14.")

        except FileNotFoundError:
            print(
                f"Error: '{KEY_FILE}' not found. Paste a key (option 9) or generate one (option 10) first."
            )
        except ImportError as e:
            print(f"Error: {e}")
        except Exception as e:
            
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
