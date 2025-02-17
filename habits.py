import logging
import os
import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CallbackContext
from cryptography.fernet import Fernet

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

USER_DATA_DIR = "user_data"
if not os.path.exists(USER_DATA_DIR):
    os.makedirs(USER_DATA_DIR)

KEY_FILE = "secret.key"
if not os.path.exists(KEY_FILE):
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as key_file:
        key_file.write(key)
else:
    with open(KEY_FILE, "rb") as key_file:
        key = key_file.read()
cipher_suite = Fernet(key)

def encrypt_data(data: str) -> str:
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    return cipher_suite.decrypt(encrypted_data.encode()).decode()

def load_user_data(user_id: int):
    user_file = os.path.join(USER_DATA_DIR, f"{user_id}.json")
    if os.path.exists(user_file):
        with open(user_file, "r") as file:
            encrypted_data = file.read()
            decrypted_data = decrypt_data(encrypted_data)
            return json.loads(decrypted_data)
    return {"habits": []}

def save_user_data(user_id: int, data: dict):
    user_file = os.path.join(USER_DATA_DIR, f"{user_id}.json")
    encrypted_data = encrypt_data(json.dumps(data))
    with open(user_file, "w") as file:
        file.write(encrypted_data)

async def start_habit_training(update: Update, context: CallbackContext):
    keyboard = [
        [KeyboardButton("Добавить привычку")],
        [KeyboardButton("Мои привычки")],
        [KeyboardButton("Вернуться в главное меню")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text(
        "Добро пожаловать в трек