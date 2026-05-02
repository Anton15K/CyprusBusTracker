import logging
import subprocess
from contextlib import asynccontextmanager

import uvicorn
from app.api.v1 import buses, routing, stops, telegram
from app.core.config import CYPRUS_TZ, ZIP_URLS, settings
from app.db.crud import get_all_stops
from app.db.session import db_manager
from app.services.gtfs_loader import GTFSDataReloader
from app.services.notifications import check_and_send_notifications
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from bot.bot import Bot
from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("cyprus_bus_tracker.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    reloader = GTFSDataReloader(
        db_manager=db_manager,
        gtfs_source_folder=settings.gtfs_source_folder,
        gtfs_target_folder=settings.gtfs_target_folder,
        gtfs_osm_folder=settings.gtfs_osm_folder,
        otp_jar=settings.otp_jar,
        zip_urls=ZIP_URLS,
        manage_otp=settings.manage_otp,
    )

    await reloader.run_all()

    async with db_manager.session_factory() as session:
        app.state.all_stops = await get_all_stops(session)

    # Initialize Telegram Bot
    telegram_bot = None
    if settings.telegram_bot_token:
        telegram_bot = Bot(
            token=settings.telegram_bot_token,
            name=settings.telegram_bot_name,
            session_creating_method=db_manager.session_factory,
        )
        await telegram_bot.start()
        app.state.telegram_bot = telegram_bot

    otp_process = None
    if settings.manage_otp:
        cmd = (
            f"java -Xmx128M -jar {settings.otp_jar} "
            f'--load "{settings.gtfs_target_folder}" --port {settings.otp_port}'
        )
        otp_process = subprocess.Popen(cmd, shell=True)
        logger.info("OTP server started (PID %s)", otp_process.pid)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        reloader.run_all,
        CronTrigger(hour=settings.reload_hour, minute=settings.reload_minute, timezone=CYPRUS_TZ),
        id="daily_gtfs_reload",
    )
    scheduler.add_job(
        check_and_send_notifications,
        "interval",
        minutes=1,
        args=[app.state],
        id="bus_notifications",
    )
    scheduler.start()

    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")
        if telegram_bot:
            await telegram_bot.stop()
            logger.info("Telegram bot stopped")
        if otp_process is not None:
            otp_process.terminate()
            logger.info("OTP server terminated")
        await db_manager.engine.dispose()
        logger.info("Database engine disposed")


app = FastAPI(lifespan=lifespan)

templates = Jinja2Templates(directory=settings.templates_dir)
app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

app.include_router(buses.router)
app.include_router(stops.router)
app.include_router(routing.router)
app.include_router(telegram.router)


@app.get("/")
async def home(
    request: Request,
    session: AsyncSession = Depends(db_manager.scoped_session_dependency),
):
    return templates.TemplateResponse(
        "map.html",
        {"request": request, "stops": request.app.state.all_stops, "buses": []},
    )


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
