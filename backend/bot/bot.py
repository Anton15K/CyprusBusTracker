import os

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
NAME = "cyprus_bus_tracker_bot"

class Bot:
    def __init__(self, token, name):
        self.token = token
        self.name = name
        self.app = Application.builder().token(self.token).build()
        self.app.add_handler(CommandHandler("start", self.__start_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.__handle_message))
        self.active_codes = {}

    def run(self):
        self.app.run_polling()

    # returns True if the user has entered the correct code in time, False otherwise
    async def wait_for_code(self, username: str, code: int, exp_time: float) -> bool:
        event = asyncio.Event()
        auth_code = AuthCode(code, event)
        if username in self.active_codes.keys():
            self.active_codes[username].add(auth_code)
        else:
            self.active_codes[username] = {auth_code}

        try:
            await asyncio.wait_for(event.wait(), exp_time)
            to_return = True
        except TimeoutError:
            to_return = False

        if username in self.active_codes.keys() and auth_code in self.active_codes[username]:
            self.active_codes[username].pop(auth_code)
            if not len(self.active_codes[username]):
                self.active_codes.pop(username)
        else:
            return False
        return to_return

    @staticmethod
    async def __start_command(update, context):
        await update.message.reply_text("Hello! Please type in your verification code")

    async def __handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.__check_code(update, context)

    async def __check_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        username = update.effective_user.id
        code_entered = update.message.text.strip()
        if username not in self.active_codes.keys():
            await update.message.reply_text("Your verification code has expired or has not been issued, please request to resend the code")
        else:
            for auth_code in self.active_codes[username]:
                if auth_code.code == code_entered:
                    auth_code.event.set()
                    await update.message.reply_text("Authentication complete")
                    return
            await update.message.reply_text("Incorrect verification code, please enter again")

class AuthCode:
    def __init__(self, code: int, event):
        self.code = str(code)
        self.event = event

# test
bot = Bot(TOKEN, NAME)
bot.run()
async def test_main():
    if await bot.wait_for_code("serge327", 812741247, 99999999999):
        print("Yay")

asyncio.run(test_main())