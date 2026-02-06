import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
import os
from dotenv import load_dotenv

load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-webapp-url.com")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎵 Открыть Music Search",
                    web_app=WebAppInfo(url=WEBAPP_URL)
                )
            ],
            [
                InlineKeyboardButton(
                    text="ℹ️ Помощь",
                    callback_data="help"
                )
            ]
        ]
    )
    
    await message.answer(
        "👋 Привет! Я бот для поиска и скачивания музыки с YouTube.\n\n"
        "🎵 Нажми на кнопку ниже, чтобы открыть поиск музыки!",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "help")
async def show_help(callback: types.CallbackQuery):
    """Показать справку"""
    help_text = (
        "📱 <b>Как пользоваться ботом:</b>\n\n"
        "1. Нажми кнопку 'Открыть Music Search'\n"
        "2. Введи название песни или исполнителя\n"
        "3. Выбери нужную песню из результатов\n"
        "4. Скачай или слушай прямо в боте\n\n"
        "🎵 <b>Возможности:</b>\n"
        "• Поиск музыки на YouTube\n"
        "• Скачивание в MP3\n"
        "• Прослушивание онлайн\n"
        "• Высокое качество аудио\n\n"
        "❓ Возникли вопросы? Просто начни печатать название песни!"
    )
    
    await callback.message.answer(help_text, parse_mode="HTML")
    await callback.answer()


@dp.message(F.text)
async def handle_text(message: types.Message):
    """Обработка текстовых сообщений - быстрый поиск"""
    query = message.text
    
    # Открываем Web App с предзаполненным поиском
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🔍 Искать '{query[:30]}...'",
                    web_app=WebAppInfo(url=f"{WEBAPP_URL}?q={query}")
                )
            ]
        ]
    )
    
    await message.answer(
        f"🔍 Ищем: <b>{query}</b>\n\n"
        "Нажми на кнопку ниже, чтобы увидеть результаты:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


async def start_bot_polling():
    """Запуск пуллинга бота"""
    logger.info("Бот запускается...")
    # Удаляем вебхук если был (на всякий случай для polling)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(start_bot_polling())
