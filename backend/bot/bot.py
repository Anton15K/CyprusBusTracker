import asyncio
import logging
from datetime import timedelta
from random import randint

from sqlalchemy.exc import SQLAlchemyError
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from backend.app.core.config import settings
from backend.bot.bot_db_functions import (
    add_code,
    add_subscription,
    add_user,
    get_subscriptions,
    get_user_info,
    remove_subscription,
)

# Set up a dedicated logger for the bot
bot_logger = logging.getLogger("cyprus_bus_tracker.bot")
bot_logger.setLevel(logging.INFO)
if not bot_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    bot_logger.addHandler(handler)


class Bot:
    def __init__(self, token, name, session_creating_method, tests=tuple()):
        self.token = token
        self.name = name
        self.__create_session = session_creating_method
        self.__tests = tests

        self.__app = Application.builder().token(self.token).concurrent_updates(True).build()
        self.__app.add_handler(CommandHandler("start", self.__start_command))
        self.__app.add_handler(CommandHandler("help", self.__help_command))
        self.__app.add_handler(CommandHandler("test", self.__test_command))
        self.__app.add_handler(CommandHandler("subscribe", self.__subscribe_command))
        self.__app.add_handler(CommandHandler("subscriptions", self.__subscriptions_command))
        self.__app.add_handler(CommandHandler("unsubscribe", self.__unsubscribe_command))
        self.__app.add_handler(
            MessageHandler(filters.ALL, self.__check_if_message_expected), group=1
        )

        self.code_length = 4
        self.code_lifetime = timedelta(minutes=2)
        self.__allowed_test_users = set(settings.allowed_test_users)

        self.__expected_messages = {}

    async def start(self):
        bot_logger.info("Starting telegram bot")
        await self.__app.initialize()
        await self.__app.start()
        await self.__app.updater.start_polling()
        bot_logger.info("Telegram bot started")

    async def stop(self):
        bot_logger.info("Stopping telegram bot")
        if self.__app.updater.running:
            await self.__app.updater.stop()
        await self.__app.stop()
        await self.__app.shutdown()
        bot_logger.info("Telegram bot stopped")

    def run(self):
        """Legacy run method for standalone use"""
        self.__app.run_polling()

    async def send_message(self, chat_id, text):
        try:
            await self.__app.bot.send_message(chat_id=chat_id, text=text)
            bot_logger.info(f"Message sent to {chat_id}")
        except Exception as e:
            bot_logger.error(f"Failed to send message to {chat_id}: {e}")

    async def wait_for_message(self, chat_id=None, message=None, timeout=None):
        event = asyncio.Event()
        expected_message = (chat_id, message)
        self.__expected_messages[expected_message] = event
        try:
            await asyncio.wait_for(event.wait(), timeout)
            to_return = True
        except (TimeoutError, asyncio.TimeoutError):
            to_return = False
        self.__expected_messages.pop(expected_message, None)
        return to_return

    async def __check_if_message_expected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return
        for chat_id in (None, update.effective_chat.id):
            for text in (None, update.message.text):
                if (chat_id, text) in self.__expected_messages.keys():
                    self.__expected_messages[(chat_id, text)].set()

    async def issue_otp(self, chat):
        async with self.__create_session() as session:
            code = str(randint(1, 10**self.code_length - 1)).zfill(self.code_length)
            try:
                if await get_user_info(session, chat.id) == {}:
                    await add_user(session, chat.id, chat.username, chat.first_name)
                await add_code(session, chat.id, code, self.code_lifetime)
                await session.commit()
                bot_logger.info(f"Issued OTP for user {chat.id}")
            except SQLAlchemyError as e:
                bot_logger.error(f"Database error while issuing OTP: {e}")
                await session.rollback()
                return None
            else:
                return code

    async def __start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        bot_logger.info(f"Start command from {update.effective_user.id}")
        otp = await self.issue_otp(update.effective_chat)
        if otp is not None:
            await update.message.reply_text(f"Do not tell anyone the code: {otp}", do_quote=True)
        else:
            await update.message.reply_text(
                "Failed to issue a code, please try again", do_quote=True
            )

    async def __help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "Available commands:\n"
            "/start - Get your 4-digit verification code to link your account on the web.\n"
            "/subscribe <stop_id> <route_id> [minutes] - Subscribe to notifications "
            "(default: 10 mins before).\n"
            "/subscriptions - List all your active subscriptions.\n"
            "/unsubscribe <id> - Remove a subscription by its ID.\n"
            "/help - Show this help message."
        )
        await update.message.reply_text(help_text)

    async def __subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /subscribe <stop_id> <route_id> [minutes]")
            return

        stop_id = context.args[0]
        route_id = context.args[1]
        minutes = 10

        if len(context.args) >= 3:
            try:
                minutes = int(context.args[2])
                if minutes <= 0:
                    await update.message.reply_text("Minutes must be a positive number.")
                    return
            except ValueError:
                await update.message.reply_text("Minutes must be a number.")
                return

        chat_id = update.effective_chat.id

        async with self.__create_session() as session:
            try:
                if await get_user_info(session, chat_id) == {}:
                    await add_user(
                        session,
                        chat_id,
                        update.effective_user.username,
                        update.effective_user.first_name,
                    )

                await add_subscription(session, chat_id, stop_id, route_id, minutes)
                await session.commit()
                await update.message.reply_text(
                    f"Subscribed to route {route_id} at stop {stop_id} ({minutes} mins before)."
                )
                bot_logger.info(
                    "User %s subscribed to route %s at stop %s with %s mins",
                    chat_id,
                    route_id,
                    stop_id,
                    minutes,
                )
            except Exception as e:
                bot_logger.error(f"Error in subscribe command: {e}")
                await session.rollback()
                await update.message.reply_text(
                    "Failed to subscribe. Please check stop_id and route_id."
                )

    async def __subscriptions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        async with self.__create_session() as session:
            subs = await get_subscriptions(session, chat_id)
            if not subs:
                await update.message.reply_text("You have no active subscriptions.")
                return

            text = "Your subscriptions:\n"
            for sub in subs:
                text += f"ID: {sub['id']} | Stop: {sub['stop_id']} | Route: {sub['route_id']}\n"
            await update.message.reply_text(text)

    async def __unsubscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 1:
            await update.message.reply_text("Usage: /unsubscribe <subscription_id>")
            return

        try:
            sub_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Subscription ID must be a number.")
            return

        chat_id = update.effective_chat.id
        async with self.__create_session() as session:
            try:
                success = await remove_subscription(session, chat_id, sub_id)
                await session.commit()
                if success:
                    await update.message.reply_text("Unsubscribed successfully.")
                    bot_logger.info(f"User {chat_id} unsubscribed from {sub_id}")
                else:
                    await update.message.reply_text(
                        "Subscription not found or does not belong to you."
                    )
            except Exception as e:
                bot_logger.error(f"Error in unsubscribe command: {e}")
                await session.rollback()
                await update.message.reply_text("Failed to unsubscribe.")

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

    async def run_tests(self, chat, test_num=None):
        if test_num is None:
            for i in range(len(self.__tests)):
                await self.__tests[i](self, chat)
                bot_logger.info(f"Test {i} has run successfully")
            return
        await self.__tests[test_num](self, chat)
        bot_logger.info(f"Test {test_num} has run successfully")

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
    #     await asyncio.gather(
    #         *[self.send_message(notif["chat_id"], notif["text"]) for notif in to_send]
    #     )
    #     return True

    # async def __link_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    #     if len(context.args) > 0:
    #         token = context.args[0]
    #         if check_token(token):
    #             await update.message.reply_text(
    #                 "Linked! You can now manage subscriptions on the web."
    #             )
    #         else:
    #             await update.message.reply_text("Link failed (invalid token?), please try again")
    #     else:
    #         await update.message.reply_text("Usage: /link <token>")
