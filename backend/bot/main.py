import asyncio
import logging
import signal
from types import SimpleNamespace

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.app.core.config import settings
from backend.app.db.session import db_manager
from backend.app.services.notifications import check_and_send_notifications
from backend.bot.bot import Bot


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("cyprus_bus_tracker.bot.main")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


async def main():
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required to start the Telegram bot")

    telegram_bot = Bot(
        token=settings.telegram_bot_token,
        name=settings.telegram_bot_name,
        session_creating_method=db_manager.session_factory,
    )
    app_state = SimpleNamespace(telegram_bot=telegram_bot)
    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_and_send_notifications,
        "interval",
        minutes=1,
        args=[app_state],
        id="bus_notifications",
    )

    await telegram_bot.start()
    scheduler.start()
    logger.info("Telegram bot notification scheduler started")

    try:
        await stop_event.wait()
    finally:
        scheduler.shutdown(wait=False)
        logger.info("Telegram bot notification scheduler shut down")
        await telegram_bot.stop()
        await db_manager.engine.dispose()
        logger.info("Telegram bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
