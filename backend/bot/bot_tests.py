import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)

from backend.bot.bot import Bot
from backend.bot.bot_db_functions import check_code, clear_all, get_codes, get_user_info

load_dotenv()
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TEST_DB_URL = os.environ["BOT_TEST_DATABASE_URL"]
NAME = "cyprus_bus_tracker_bot"
TEST_CHAT_ID = -1

engine = create_async_engine(url=TEST_DB_URL)
session_factory = async_sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


async def clear_test_db(bot: Bot, chat=None):
    async with session_factory() as session:
        await clear_all(session)
        await session.commit()


async def test_basic(bot: Bot, chat):
    await bot.send_message(chat.id, "(Testing) I am alive")


async def test_otp_correct(bot: Bot, chat):
    async with session_factory() as session:
        await clear_all(session)
        await session.commit()
    async with session_factory() as session:
        correct_otp = await bot.issue_otp(chat)
        code = (await get_codes(session, chat.id))[0]
        user = await get_user_info(session, chat.id)
        assert (
            code is not None
            and code["otp_code"] == correct_otp
            and not code["is_used"]
            and code["chat_id"] == chat.id
        )
        assert (
            user is not None
            and not user["is_active"]
            and user["username"] == chat.username
            and user["chat_id"] == chat.id
        )
        result = await check_code(session, chat.username, correct_otp)
        assert result
        new_codes = await get_codes(session, chat.id)
        for c in new_codes:
            if c["id"] == code["id"]:
                new_code = c
        new_user = await get_user_info(session, chat.id)
        assert new_code is not None and new_code["is_used"]
        assert new_user is not None and new_user["is_active"]


async def test_otp_incorrect(bot: Bot, chat):
    async with session_factory() as session:
        await clear_all(session)
        await session.commit()
    async with session_factory() as session:
        correct_otp = await bot.issue_otp(chat)
        code = (await get_codes(session, chat.id))[0]
        user = await get_user_info(session, chat.id)
        assert (
            code is not None
            and code["otp_code"] == correct_otp
            and not code["is_used"]
            and code["chat_id"] == chat.id
        )
        assert (
            user is not None
            and not user["is_active"]
            and user["username"] == chat.username
            and user["chat_id"] == chat.id
        )
        result = await check_code(session, chat.username, correct_otp + "0")
        assert not result
        new_codes = await get_codes(session, chat.id)
        for c in new_codes:
            if c["id"] == code["id"]:
                new_code = c
        new_user = await get_user_info(session, chat.id)
        assert new_code == code
        assert new_user == user


async def test_wait_for_message(bot: Bot, chat):
    await bot.send_message(chat.id, "(Testing) Write 'Abracadabra' in the chat")
    await bot.wait_for_message(message="Abracadabra", chat_id=None)
    await bot.send_message(chat.id, "(Testing) Message received")


tests = (clear_test_db, test_basic, test_wait_for_message, test_otp_correct, test_otp_incorrect)
bot = Bot(TOKEN, NAME, None, session_factory, tests)
bot.run()
