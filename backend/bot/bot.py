import asyncio
from tokenize import group

from sqlalchemy.exc import SQLAlchemyError
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from random import randint
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from backend.bot.bot_db_functions import get_user_info
from bot_db_functions import add_code, add_user

class Bot:
    def __init__(self, token, name, logger, session_creating_method, tests=tuple()):
        self.token = token
        self.name = name
        self.__logger = logger
        self.__create_session = session_creating_method
        self.__tests = tests

        self.__app = Application.builder().token(self.token).concurrent_updates(True).build()
        self.__app.add_handler(CommandHandler("start", self.__start_command))
        #self.app.add_handler(CommandHandler("link", self.__link_command))
        self.__app.add_handler(CommandHandler("test", self.__test_command))
        self.__app.add_handler(MessageHandler(filters.ALL, self.__check_if_message_expected), group=1)

        self.code_length = 4
        self.code_lifetime = timedelta(minutes=2)
        self.__allowed_test_users = {"serge_327", "ak_15_ka", "antongalalu", "tratatatanka"}

        self.send_message = self.__app.bot.send_message

        self.__expected_messages = {}

    def run(self):
        self.__app.run_polling()

    async def wait_for_message(self, chat_id=None, message=None, timeout=None):
        event = asyncio.Event()
        expected_message = (chat_id, message)
        self.__expected_messages[expected_message] = event
        try:
            await asyncio.wait_for(event.wait(), timeout)
            to_return = True
        except TimeoutError:
            to_return = False
        self.__expected_messages.pop(expected_message)
        return to_return

    async def __check_if_message_expected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        for chat_id in (None, update.effective_chat.id):
            for text in (None, update.message.text):
                if (chat_id, text) in self.__expected_messages.keys():
                    self.__expected_messages[(chat_id, text)].set()

    async def issue_otp(self, chat):
        async with self.__create_session() as session:
            code = str(randint(1, 10**self.code_length-1)).zfill(self.code_length)
            try:
                if await get_user_info(session, chat.id) == {}:
                    await add_user(session, chat.id, chat.username, chat.first_name)
                await add_code(session, chat.id, code, self.code_lifetime)
                await session.commit()
            except SQLAlchemyError:
                await session.rollback()
                return None
            else:
                return code

    async def run_tests(self, chat, test_num=None):
        if test_num is None:
            for i in range(len(self.__tests)):
                await self.__tests[i](self, chat)
                print(f"Test {i} has run successfully")
            return
        await self.__tests[test_num](self, chat)
        print(f"Test {test_num} has run successfully")

    async def __test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.username not in self.__allowed_test_users:
            await update.message.reply_text("You are not authorized to test the bot", do_quote=True)
            return
        if not len(context.args):
            await self.run_tests(update.effective_chat)
            return
        test_num = context.args[0]
        if not test_num.isnumeric():
            await update.message.reply_text("Usage: /test <test number>", do_quote=True)
            return
        else:
            test_num = int(test_num)
        if test_num >= len(self.__tests) or test_num < 0:
            await update.message.reply_text(f"Test {test_num} does not exist", do_quote=True)
        else:
            await update.message.reply_text(f"Attempting test {test_num}", do_quote=True)
            await self.run_tests(update.effective_chat, test_num)

    async def __start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        otp = await self.issue_otp(update.effective_chat)
        if otp is not None:
            await update.message.reply_text(f"Do not tell anyone the code: {otp}", do_quote=True)
        else:
            await update.message.reply_text("Failed to issue a code, please try again", do_quote=True)

    # @staticmethod
    # def __make_text(self, *args):
    #     return "Filler text for notification"

    # async def send_notifications(self):
    #     session = self.create_session()
    #     notifications = []
    #     subscriptions = await get_all_active_subscriptions(session)
    #     for subscription in subscriptions:
    #         notifications += await get_active_notifications(session, subscription)
    #     to_send = []
    #     for notification in notifications:
    #         if not notification_already_sent(session, notification):
    #             notification["text"] = self.__make_text(notification)
    #             to_send.append(notification)
    #     await asyncio.gather(*[self.send_message(notif["chat_id"], notif["text"]) for notif in to_send])
    #     return True

    # async def __link_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    #     if len(context.args) > 0:
    #         token = context.args[0]
    #         if check_token(token):
    #             await update.message.reply_text("Linked! You can now manage subscriptions on the web.")
    #         else:
    #             await update.message.reply_text("Link failed (invalid token?), please try again")
    #     else:
    #         await update.message.reply_text("Usage: /link <token>")