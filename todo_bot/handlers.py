from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler
from database import User, Task, initialize_db, get_db_connection
from datetime import datetime
import requests
import os
import logging
from dotenv import load_dotenv
from functools import wraps
import telegram
from peewee import DoesNotExist

logger = logging.getLogger(__name__)
load_dotenv()
initialize_db()


def db_connection_handler(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        db = get_db_connection()
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            logger.error(f"Database error: {e}", exc_info=True)
            if update and update.message:
                await update.message.reply_text(
                    "⚠️ Произошла ошибка. Попробуйте позже.",
                    reply_markup=main_menu()
                )
        finally:
            if not db.is_closed():
                db.close()

    return wrapper


def update_user_activity(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            user, _ = User.get_or_create(
                user_id=update.effective_user.id,
                defaults={
                    'username': update.effective_user.username,
                    'first_name': update.effective_user.first_name,
                    'last_name': update.effective_user.last_name
                }
            )
            user.last_activity = datetime.now()
            user.save()
        except Exception as e:
            logger.error(f"User activity error: {e}")
        return await func(update, context, *args, **kwargs)

    return wrapper


def main_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📝 Добавить задачу"), KeyboardButton("📋 Мои задачи")],
        [KeyboardButton("✅ Выполненные")],
        [KeyboardButton("🌤 Погода"), KeyboardButton("💱 Курс валют")]
    ], resize_keyboard=True)


@update_user_activity
@db_connection_handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 To-Do Bot\n\nВыберите действие:",
        reply_markup=main_menu()
    )


@update_user_activity
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Помощь:\n\nФормат задач: <текст>, <категория>\nПример: Купить молоко, продукты",
        reply_markup=main_menu()
    )


@update_user_activity
@db_connection_handler
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📝 Добавить задачу":
        await add_task(update, context)
    elif text == "📋 Мои задачи":
        await show_active_tasks(update, context)
    elif text == "✅ Выполненные":
        await show_completed_tasks(update, context)
    elif text == "🌤 Погода":
        await ask_city(update, context)
    elif text == "💱 Курс валют":
        await show_currency(update, context)
    elif text == "Отмена":
        await cancel(update, context)
    elif context.user_data.get('awaiting_task'):
        await save_task(update, context)
    elif context.user_data.get('awaiting_city'):
        await show_weather(update, context)


async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Введите задачу:\n<текст>, <категория>\nПример: Купить молоко, продукты",
        reply_markup=ReplyKeyboardMarkup([["Отмена"]], resize_keyboard=True)
    )
    context.user_data['awaiting_task'] = True


@update_user_activity
@db_connection_handler
async def save_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "отмена":
        await cancel(update, context)
        return

    try:
        text, category = map(str.strip, update.message.text.split(",", 1))

        if not text or not category:
            raise ValueError("Пустые поля не допускаются")

        user = User.get(User.user_id == update.effective_user.id)
        Task.create(user=user, text=text, category=category)

        await update.message.reply_text(
            f"✅ Добавлено: {text} ({category})",
            reply_markup=main_menu()
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат. Пример: Купить молоко, продукты",
            reply_markup=ReplyKeyboardMarkup([["Отмена"]], resize_keyboard=True)
        )
    except Exception as e:
        logger.error(f"Ошибка сохранения задачи: {e}")
        await update.message.reply_text(
            "❌ Не удалось сохранить задачу",
            reply_markup=main_menu()
        )
    finally:
        context.user_data.pop('awaiting_task', None)


@update_user_activity
@db_connection_handler
async def show_active_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = User.get(User.user_id == update.effective_user.id)
        tasks = Task.select().where(
            (Task.user == user) &
            (Task.is_done == False)
        ).order_by(Task.created_at.desc())

        if not tasks.count():
            await update.message.reply_text("📭 Нет активных задач", reply_markup=main_menu())
            return

        keyboard = [
            [InlineKeyboardButton(
                f"{task.text} ({task.category})",
                callback_data=f"complete_{task.id}"
            )]
            for task in tasks
        ]

        await update.message.reply_text(
            "📋 Активные задачи:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except DoesNotExist:
        await update.message.reply_text("📭 Нет активных задач", reply_markup=main_menu())
    except Exception as e:
        logger.error(f"Ошибка показа задач: {e}")
        await update.message.reply_text(
            "❌ Не удалось загрузить задачи",
            reply_markup=main_menu()
        )


@update_user_activity
@db_connection_handler
async def show_completed_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = User.get(User.user_id == update.effective_user.id)
        tasks = Task.select().where(
            (Task.user == user) &
            (Task.is_done == True)
        ).order_by(Task.completed_at.desc())

        if not tasks.count():
            await update.message.reply_text("📭 Нет выполненных задач", reply_markup=main_menu())
            return

        message = "✅ Выполненные задачи:\n\n" + "\n".join(
            f"• {task.text} ({task.category}) - {task.completed_at.strftime('%d.%m.%Y') if task.completed_at else '??.??.????'}"
            for task in tasks
        )

        await update.message.reply_text(message, reply_markup=main_menu())
    except DoesNotExist:
        await update.message.reply_text("📭 Нет выполненных задач", reply_markup=main_menu())
    except Exception as e:
        logger.error(f"Ошибка показа выполненных задач: {e}")
        await update.message.reply_text(
            "❌ Не удалось загрузить выполненные задачи",
            reply_markup=main_menu()
        )


@update_user_activity
@db_connection_handler
async def complete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()

        task_id = int(query.data.split('_')[1])
        task = Task.get(Task.id == task_id)

        task.is_done = True
        task.completed_at = datetime.now()
        task.save()

        await query.edit_message_text(f"✅ Завершено: {task.text}")
    except DoesNotExist:
        await query.answer("❌ Задача не найдена")
    except Exception as e:
        logger.error(f"Ошибка завершения задачи: {e}")
        await query.answer("❌ Ошибка завершения")


async def ask_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌤 Введите город для прогноза погоды:",
        reply_markup=ReplyKeyboardMarkup([["Отмена"]], resize_keyboard=True)
    )
    context.user_data['awaiting_city'] = True


@update_user_activity
async def show_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "отмена":
        await cancel(update, context)
        return

    city = update.message.text
    try:
        api_key = os.getenv('WEATHER_API_KEY')
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
        response = requests.get(url)
        data = response.json()

        if data.get('cod') != 200:
            raise ValueError(data.get('message', 'Неизвестная ошибка API'))

        weather_info = (
            f"🌤 Погода в {data['name']}:\n"
            f"• Температура: {data['main']['temp']}°C\n"
            f"• Ощущается как: {data['main']['feels_like']}°C\n"
            f"• Влажность: {data['main']['humidity']}%\n"
            f"• Ветер: {data['wind']['speed']} м/с\n"
            f"• {data['weather'][0]['description'].capitalize()}"
        )

        await update.message.reply_text(weather_info, reply_markup=main_menu())
    except Exception as e:
        logger.error(f"Ошибка погодного API: {e}")
        await update.message.reply_text(
            f"❌ Не удалось получить погоду. Ошибка: {str(e)}",
            reply_markup=main_menu()
        )
    finally:
        context.user_data.pop('awaiting_city', None)


@update_user_activity
async def show_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get('https://www.cbr-xml-daily.ru/daily_json.js')
        data = response.json()

        usd = data['Valute']['USD']['Value']
        eur = data['Valute']['EUR']['Value']

        await update.message.reply_text(
            f"💱 Курс валют:\n\nUSD: {usd:.2f}₽\nEUR: {eur:.2f}₽",
            reply_markup=main_menu()
        )
    except Exception as e:
        logger.error(f"Ошибка курса валют: {e}")
        await update.message.reply_text(
            "❌ Не удалось получить курс валют",
            reply_markup=main_menu()
        )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Главное меню:", reply_markup=main_menu())
    context.user_data.clear()


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    error = context.error
    logger.error(f"Global error: {error}", exc_info=True)

    if isinstance(error, telegram.error.Forbidden):
        logger.warning("User blocked the bot")
        return
    elif isinstance(error, telegram.error.NetworkError):
        logger.warning("Network issues")
        return

    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Произошла ошибка. Попробуйте позже.",
                reply_markup=main_menu()
            )
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")