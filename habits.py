import logging
import os
import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CallbackContext
from cryptography.fernet import Fernet

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Папка для хранения данных пользователей
USER_DATA_DIR = "user_data"
if not os.path.exists(USER_DATA_DIR):
    os.makedirs(USER_DATA_DIR)

# Ключ для шифрования данных
KEY_FILE = "secret.key"
if not os.path.exists(KEY_FILE):
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as key_file:
        key_file.write(key)
else:
    with open(KEY_FILE, "rb") as key_file:
        key = key_file.read()
cipher_suite = Fernet(key)

class HabitTracker:
    def __init__(self):
        self.user_data = {}

    def encrypt_data(self, data: str) -> str:
        return cipher_suite.encrypt(data.encode()).decode()

    def decrypt_data(self, encrypted_data: str) -> str:
        return cipher_suite.decrypt(encrypted_data.encode()).decode()

    def load_user_data(self, user_id: int):
        user_file = os.path.join(USER_DATA_DIR, f"{user_id}.json")
        if os.path.exists(user_file):
            with open(user_file, "r") as file:
                encrypted_data = file.read()
                decrypted_data = self.decrypt_data(encrypted_data)
                return json.loads(decrypted_data)
        return {"habits": []}

    def save_user_data(self, user_id: int, data: dict):
        user_file = os.path.join(USER_DATA_DIR, f"{user_id}.json")
        encrypted_data = self.encrypt_data(json.dumps(data))
        with open(user_file, "w") as file:
            file.write(encrypted_data)

    async def start_habit_training(self, update: Update, context: CallbackContext):
        keyboard = [
            [KeyboardButton("Добавить привычку")],
            [KeyboardButton("Мои привычки")],
            [KeyboardButton("Вернуться в главное меню")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text(
            "Добро пожаловать в трекер привычек! Выберите действие:",
            reply_markup=reply_markup
        )

    async def add_habit(self, update: Update, context: CallbackContext):
        await update.message.reply_text("Введите название привычки:")
        context.user_data['awaiting_habit_name'] = True

    async def handle_habit_name(self, update: Update, context: CallbackContext):
        habit_name = update.message.text
        context.user_data['habit_name'] = habit_name
        await update.message.reply_text("Введите описание привычки:")
        context.user_data['awaiting_habit_description'] = True

    async def handle_habit_description(self, update: Update, context: CallbackContext):
        habit_description = update.message.text
        habit_name = context.user_data['habit_name']
        user_id = update.message.from_user.id

        user_data = self.load_user_data(user_id)
        user_data["habits"].append({
            "name": habit_name,
            "description": habit_description,
            "completed": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        self.save_user_data(user_id, user_data)

        await update.message.reply_text(f"Привычка '{habit_name}' успешно добавлена в список!")
        context.user_data.clear()
        await self.start_habit_training(update, context)

    async def list_habits(self, update: Update, context: CallbackContext):
        user_id = update.message.from_user.id
        user_data = self.load_user_data(user_id)
        habits = user_data.get("habits", [])

        if habits:
            message = "Ваши привычки:\n\n"
            for habit in habits:
                status = "✅" if habit["completed"] else "❌"
                message += f"{status} {habit['name']}\n"
                message += f"📝 {habit['description']}\n\n"
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("У вас пока нет привычек.")

        await self.start_habit_training(update, context)