from telegram import Update

async def author_info(update: Update):
    await update.message.reply_text("Информация о боте: бот создан в рамках учебы на SkillBOX")