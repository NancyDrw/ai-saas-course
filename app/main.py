import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

MENU_TEXTS = {
    "💬 AI-сексолог": "Допоможе структурувати запит і підібрати запитання для саморефлексії.",
    "👫 Профіль пари": "Збере потреби, межі та погляди кожного партнера на близькість.",
    "🔥 Сумісність": "Допоможе порівняти бажання, ініціативу та важливі межі.",
    "🃏 Картки для розмов": "Запропонує делікатні запитання для розмови в парі.",
    "❤️ Intimacy Check-in": "Допоможе регулярно оцінювати близькість і задоволеність у стосунках.",
    "🧩 Вправи для пари": "Запропонує практики для комунікації та близькості.",
    "📊 Insights": "Показуватиме динаміку та теми, яким варто приділити більше уваги.",
}

menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💬 AI-сексолог"), KeyboardButton(text="👫 Профіль пари")],
        [KeyboardButton(text="🔥 Сумісність"), KeyboardButton(text="🃏 Картки для розмов")],
        [KeyboardButton(text="❤️ Intimacy Check-in")],
        [KeyboardButton(text="🧩 Вправи для пари"), KeyboardButton(text="📊 Insights")],
    ],
    resize_keyboard=True,
)


async def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set. Copy .env.example to .env and fill in the token.")

    bot = Bot(token=token)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        logger.info("Command /start received: user_id=%s", message.from_user.id)
        await message.answer(
            "Привіт! 👋\n\n"
            "Я Intima — цифровий помічник для турботи про близькість і стосунки.\n"
            "Обери потрібний розділ у меню нижче або напиши /help.",
            reply_markup=menu_keyboard,
        )

    @dp.message(Command("help"))
    async def cmd_help(message: Message) -> None:
        logger.info("Command /help received: user_id=%s", message.from_user.id)
        await message.answer(
            "Intima допомагає дбайливо говорити про близькість у стосунках.\n\n"
            "Доступні команди:\n"
            "/start — розпочати роботу\n"
            "/help — коротка довідка\n"
            "/menu — показати меню",
            reply_markup=menu_keyboard,
        )

    @dp.message(Command("menu"))
    async def cmd_menu(message: Message) -> None:
        logger.info("Command /menu received: user_id=%s", message.from_user.id)
        await message.answer("Обери розділ:", reply_markup=menu_keyboard)

    @dp.message(F.text.in_(MENU_TEXTS))
    async def menu_item_selected(message: Message) -> None:
        logger.info(
            "Menu section selected: user_id=%s section=%s",
            message.from_user.id,
            message.text,
        )
        await message.answer(
            f"{MENU_TEXTS[message.text]}\n\n"
            "Цей розділ поки в розробці — інтерактивний сценарій з’явиться незабаром."
        )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
