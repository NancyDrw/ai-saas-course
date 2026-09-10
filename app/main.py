import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker

from database import Base, Category, Couple, User, UserTransaction, create_database_engine

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

COUPLE_PROFILE_CATEGORY_CODE = "couple_profile"
COUPLE_PROFILE_CATEGORY_TITLE = "Профіль пари"

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

    database_url = os.getenv("DATABASE_URL")
    if not database_url or database_url == "your_database_url_here":
        raise RuntimeError("DATABASE_URL is not set. Add it to the local .env file.")

    engine = create_database_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        category = await session.scalar(
            select(Category).where(Category.code == COUPLE_PROFILE_CATEGORY_CODE)
        )
        if category is None:
            session.add(
                Category(
                    code=COUPLE_PROFILE_CATEGORY_CODE,
                    title=COUPLE_PROFILE_CATEGORY_TITLE,
                    description="Створення та ведення профілю пари.",
                )
            )
            await session.commit()

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
            "/menu — показати меню\n"
            "/couple Анна та Максим — зберегти пару",
            reply_markup=menu_keyboard,
        )

    @dp.message(Command("menu"))
    async def cmd_menu(message: Message) -> None:
        logger.info("Command /menu received: user_id=%s", message.from_user.id)
        await message.answer("Обери розділ:", reply_markup=menu_keyboard)

    @dp.message(Command("couple"))
    async def cmd_couple(message: Message) -> None:
        _, separator, title = (message.text or "").partition(" ")
        couple_title = title.strip()
        if not separator or not couple_title:
            await message.answer("Використайте формат: /couple Анна та Максим")
            return

        telegram_user = message.from_user
        if telegram_user is None:
            await message.answer("Не вдалося визначити користувача Telegram.")
            return

        try:
            async with session_factory() as session:
                user = await session.scalar(
                    select(User).where(User.telegram_id == telegram_user.id)
                )
                if user is None:
                    user = User(
                        telegram_id=telegram_user.id,
                        username=telegram_user.username,
                        first_name=telegram_user.first_name,
                    )
                    session.add(user)
                    await session.flush()

                category = await session.scalar(
                    select(Category).where(
                        Category.code == COUPLE_PROFILE_CATEGORY_CODE
                    )
                )
                if category is None:
                    raise RuntimeError("The couple profile category is missing.")

                couple = Couple(created_by_user_id=user.id, title=couple_title)
                session.add(couple)
                await session.flush()
                session.add(
                    UserTransaction(
                        user_id=user.id,
                        category_id=category.id,
                        couple_id=couple.id,
                        action_type="couple_created",
                        selected_profile="couple",
                        content_summary="Створено профіль пари.",
                    )
                )
                await session.commit()
                await session.refresh(couple)
        except (RuntimeError, SQLAlchemyError):
            logger.error("Could not save couple for Telegram user %s", telegram_user.id)
            await message.answer("Не вдалося зберегти пару. Спробуйте ще раз пізніше.")
            return

        logger.info("Couple created: couple_id=%s user_id=%s", couple.id, telegram_user.id)
        await message.answer(
            f"Пару «{couple_title}» збережено. Унікальний ID: {couple.id}"
        )

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

    try:
        await dp.start_polling(bot)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
