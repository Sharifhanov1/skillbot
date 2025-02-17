import logging
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext
from weather import get_weather
from hotels import search_hotels
from habits import (
    start_habit_training, add_habit, handle_habit_name, handle_habit_description,
    list_habits
)
from author import author_info
from crm import handle_crm
from file_sync import handle_file_sync
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Токен бота из переменной окружения
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Функция для записи истории
def log_history(user_name: str, search_type: str, query: str, result: str):
    try:
        with open("history.txt", "a", encoding="utf-8") as file:
            file.write(
                f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Пользователь: {user_name}\n"
                f"Тип запроса: {search_type}\n"
                f"Запрос: {query}\n"
                f"Результат: {result}\n"
                f"{'-' * 40}\n"
            )
    except Exception as e:
        logger.error(f"Ошибка при записи в историю: {e}")

# Приветственное сообщение
async def start(update: Update, context: CallbackContext):
    try:
        keyboard = [
            [KeyboardButton("Прогноз погоды")],
            [KeyboardButton("Поиск отелей")],
            [KeyboardButton("Тренинг привычек")],
            [KeyboardButton("CRM-система")],
            [KeyboardButton("Сервис синхронизации файлов")],
            [KeyboardButton("Инфо об авторе")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_photo(photo=open('images/welcome.jpg', 'rb'))
        await update.message.reply_text(
            "Привет! Я твой помощник. Давай начнем! Выбери одну из опций ниже:",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка в функции start: {e}")

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: CallbackContext):
    user_name = update.message.from_user.first_name
    text = update.message.text

    if text == "Прогноз погоды":
        await update.message.reply_text("Введите название города для прогноза погоды:")
        context.user_data['awaiting_city'] = True
        context.user_data['search_type'] = "Погода"
    elif text == "Поиск отелей":
        await update.message.reply_text("Введите город для поиска отелей:")
        context.user_data['awaiting_hotels_city'] = True
        context.user_data['search_type'] = "Отели"
    elif text == "Тренинг привычек":
        await start_habit_training(update, context)
    elif text == "CRM-система":
        await handle_crm(update, context)
    elif text == "Сервис синхронизации файлов":
        await handle_file_sync(update, context)
    elif text == "Инфо об авторе":
        await update.message.reply_text("Информация об авторе: ...")
        context.user_data['search_type'] = "Инфо об авторе"
    elif text == "Вернуться в главное меню":
        await start(update, context)
    elif text == "Добавить привычку":
        await add_habit(update, context)
    elif text == "Мои привычки":
        await list_habits(update, context)
    elif context.user_data.get('awaiting_city'):
        city = text
        if not city.strip():
            await update.message.reply_text("Название города не может быть пустым. Введите город:")
            return
        weather_info, photo_url = await get_weather(city)
        if photo_url:
            await update.message.reply_photo(photo=photo_url, caption=weather_info)
        else:
            await update.message.reply_text(weather_info)
        log_history(user_name, context.user_data['search_type'], city, weather_info)
        context.user_data['awaiting_city'] = False
    elif context.user_data.get('awaiting_hotels_city'):
        city = text
        if not city.strip():
            await update.message.reply_text("Название города не может быть пустым. Введите город:")
            return
        context.user_data['city'] = city
        await update.message.reply_text("Введите дату заезда (формат: день.месяц, например, 15.05):")
        context.user_data['awaiting_hotels_check_in'] = True
        context.user_data['awaiting_hotels_city'] = False
    elif context.user_data.get('awaiting_hotels_check_in'):
        try:
            datetime.strptime(text, "%d.%m")
            context.user_data['check_in'] = text
            await update.message.reply_text("Введите примерную цену за ночь (в рублях):")
            context.user_data['awaiting_hotels_price'] = True
            context.user_data['awaiting_hotels_check_in'] = False
        except ValueError:
            await update.message.reply_text("Некорректный формат даты. Введите дату в формате день.месяц (например, 15.05):")
    elif context.user_data.get('awaiting_hotels_price'):
        try:
            price_per_night = float(text)
            if price_per_night <= 0:
                await update.message.reply_text("Цена должна быть больше нуля. Введите примерную цену за ночь:")
                return
            context.user_data['price_per_night'] = price_per_night
            city = context.user_data['city']
            check_in = context.user_data['check_in']
            price_per_night = context.user_data['price_per_night']

            hotels_info = await search_hotels(city, check_in, price_per_night)
            await update.message.reply_text(hotels_info)

            query = f"Город: {city}, Дата заезда: {check_in}, Цена за ночь: {price_per_night}"
            log_history(user_name, context.user_data['search_type'], query, hotels_info)

            context.user_data.clear()
        except ValueError:
            await update.message.reply_text("Некорректный формат цены. Введите число (например, 5000):")
    elif context.user_data.get('awaiting_habit_name'):
        await handle_habit_name(update, context)
    elif context.user_data.get('awaiting_habit_description'):
        await handle_habit_description(update, context)
    else:
        await update.message.reply_text("Пожалуйста, выберите опцию из меню.")

# Основная функция
def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен")
    application.run_polling()

if __name__ == '__main__':
    main()