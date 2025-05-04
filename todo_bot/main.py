from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from handlers import start, handle_text, complete_task, error_handler, help_command
from dotenv import load_dotenv
import os
import logging
import telegram

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()


async def post_init(application):
    await application.bot.set_my_commands([
        ("start", "Запустить бота"),
        ("help", "Помощь")
    ])
    logger.info("Бот инициализирован")


async def post_shutdown(application):
    logger.info("Бот выключается")


def main():
    try:
        app = ApplicationBuilder() \
            .token(os.getenv('TELEGRAM_TOKEN')) \
            .connection_pool_size(10) \
            .pool_timeout(30) \
            .post_init(post_init) \
            .post_shutdown(post_shutdown) \
            .build()

        # Регистрация обработчиков
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        app.add_handler(CallbackQueryHandler(complete_task, pattern="^complete_"))

        app.add_error_handler(error_handler)

        logger.info("Бот запущен")
        app.run_polling(
            drop_pending_updates=True,
            close_loop=False,
            stop_signals=None
        )

    except Exception as e:
        logger.critical(f"Ошибка запуска: {e}", exc_info=True)


if __name__ == "__main__":
    main()