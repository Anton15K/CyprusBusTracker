import os
from dotenv import load_dotenv
from datetime import timedelta

from bot_db_functions import clear_all, check_code, get_codes, add_user, get_user_info, add_pending_session, find_pending_session
from bot_main import Bot

from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)

load_dotenv()
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TEST_DB_URL = os.environ["BOT_TEST_DATABASE_URL"]
NAME = "cyprus_bus_tracker_bot"
TEST_CHAT_ID = -1

engine = create_async_engine(url=TEST_DB_URL)
session_factory = async_sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

async def clear_test_db(bot=None, chat=None):
    async with session_factory() as session:
        await clear_all(session)
        await session.commit()

async def test_basic(bot: Bot, chat):
    await bot.send_message(chat.id, "(Testing) I am alive")

async def test_otp_correct(bot: Bot, chat):
    await clear_test_db()
    async with session_factory() as session:
        correct_otp = await bot.issue_otp(chat)
        code = (await get_codes(session, chat.id))[0]
        user = await get_user_info(session, chat.id)
        assert code is not None and code["otp_code"] == correct_otp and not code["is_used"] and code["chat_id"] == chat.id
        assert user is not None and not user["is_active"] and user["username"] == chat.username and user["chat_id"] == chat.id
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
    await clear_test_db()
    async with session_factory() as session:
        correct_otp = await bot.issue_otp(chat)
        code = (await get_codes(session, chat.id))[0]
        user = await get_user_info(session, chat.id)
        assert code is not None and code["otp_code"] == correct_otp and not code["is_used"] and code["chat_id"] == chat.id
        assert user is not None and not user["is_active"] and user["username"] == chat.username and user["chat_id"] == chat.id
        result = await check_code(session, chat.username, correct_otp + "0")
        assert not result
        new_codes = await get_codes(session, chat.id)
        for c in new_codes:
            if c["id"] == code["id"]:
                new_code = c
        new_user = await get_user_info(session, chat.id)
        assert new_code == code
        assert new_user == user

async def test_link(bot: Bot, chat):
    await clear_test_db()
    async with session_factory() as session:
        await add_pending_session(session, "Placeholder", timedelta(minutes=2))
        await add_user(session, chat.id, chat.username, chat.first_name)
        await session.commit()
    async with session_factory() as session:
        row = await find_pending_session(session, "Placeholder")
        assert row["token"] == "Placeholder" and row["chat_id"] is None
        await bot.link(chat, "Wrong_Placeholder")
        row = await find_pending_session(session, "Placeholder")
        assert row["chat_id"] is None
        await bot.link(chat, "Placeholder")
        row = await find_pending_session(session, "Placeholder")
        assert row["chat_id"] == chat.id

async def test_wait_for_message(bot: Bot, chat):
    await bot.send_message(chat.id, "(Testing) Write 'Abracadabra' in the chat")
    await bot.wait_for_message(message="Abracadabra", chat_id=None)
    await bot.send_message(chat.id, "(Testing) Message received")

tests = (clear_test_db, test_basic, test_wait_for_message, test_otp_correct, test_otp_incorrect, test_link)
bot = Bot(TOKEN, NAME, None, session_factory, tests)
bot.run()