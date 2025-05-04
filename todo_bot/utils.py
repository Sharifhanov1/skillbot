from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Bot
from database import Task
import datetime


def setup_reminders(bot: Bot):
    scheduler = BackgroundScheduler()

    def check_reminders():
        now = datetime.datetime.now()
        # Получаем все задачи с просроченным дедлайном
        tasks = Task.select().where(
            (Task.deadline <= now) &
            (Task.is_done == False)
        )

        for task in tasks:
            try:
                bot.send_message(
                    chat_id=task.user.user_id,
                    text=f"⏰ Напоминание: {task.text}"
                )
                # Помечаем задачу как выполненную после отправки напоминания
                task.is_done = True
                task.save()
            except Exception as e:
                print(f"Ошибка при отправке напоминания: {e}")

    # Проверяем напоминания каждую минуту
    scheduler.add_job(check_reminders, 'interval', minutes=1)
    scheduler.start()