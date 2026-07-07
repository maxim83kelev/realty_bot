import asyncio
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from bot import bot, dp, ADMIN_ID
from db import init_db
from scheduler import start_scheduler

async def set_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="filter", description="Настроить фильтр"),
        BotCommand(command="myfilter", description="Мой текущий фильтр"),
        BotCommand(command="digest", description="🔍 Объявления из базы по моему фильтру"),
        BotCommand(command="stop", description="Остановить уведомления"),
    ], scope=BotCommandScopeDefault())

    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="filter", description="Настроить фильтр"),
        BotCommand(command="myfilter", description="Мой текущий фильтр"),
        BotCommand(command="stop", description="Остановить уведомления"),
        BotCommand(command="admin", description="📊 Статистика"),
        BotCommand(command="ausers", description="👥 Список пользователей"),
        BotCommand(command="abroadcast", description="📢 Рассылка всем"),
        BotCommand(command="aclear", description="🗑 Очистить старые объявления"),
        BotCommand(command="areply", description="💬 Ответить пользователю"),
        BotCommand(command="aban", description="🔨 Забанить пользователя"),
        BotCommand(command="aunban", description="✅ Разбанить пользователя"),
        BotCommand(command="abandlist", description="🔨 Список забаненных"),
    ], scope=BotCommandScopeChat(chat_id=ADMIN_ID))

async def main():
    await init_db()
    await set_commands()
    start_scheduler()
    print("✅ База подключена, планировщик запущен")
    print("🤖 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())