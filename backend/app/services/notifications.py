import logging
from datetime import datetime, date
from sqlalchemy import text, select
from app.core.config import CYPRUS_TZ, settings
from app.db.session import db_manager
from app.db.crud import update_stop_times_and_get_buses
from bot.bot_db_functions import get_active_subscriptions_all
from app.models.orm import Notification_Log

logger = logging.getLogger("cyprus_bus_tracker.notifications")

async def check_and_send_notifications(app_state):
    logger.info("Checking for bus notifications...")
    bot = getattr(app_state, "telegram_bot", None)
    if not bot:
        logger.warning("Telegram bot not initialized, skipping notifications")
        return

    async with db_manager.session_factory() as session:
        # 0. Refresh RT data so we have live arrival times in stop_times table
        try:
            await update_stop_times_and_get_buses(session, settings.gtfs_realtime_url)
            logger.info("GTFS-RT data refreshed for notifications")
        except Exception as e:
            logger.error("Failed to refresh GTFS-RT data for notifications: %s", e)

        # 1. Get all active subscriptions
        subs = await get_active_subscriptions_all(session)
        if not subs:
            logger.info("No active subscriptions found")
            return
        
        logger.info(f"Processing {len(subs)} active subscriptions")

        now = datetime.now(CYPRUS_TZ)
        current_time_seconds = now.hour * 3600 + now.minute * 60 + now.second
        today = now.date()

        for sub in subs:
            # 2. Check for trips on this route at this stop in the next ~N minutes
            try:
                stop_id_int = int(sub.stop_id)
                route_id_int = int(sub.route_id)
            except (ValueError, TypeError):
                logger.warning(f"Invalid IDs in sub {sub.id}: stop={sub.stop_id}, route={sub.route_id}")
                continue

            query = text("""
                SELECT st.arrival_time, st.trip_id, r.route_short_name, s.stop_name
                FROM stop_times st
                JOIN trips t ON st.trip_id = t.trip_id
                JOIN routes r ON t.route_id = r.route_id
                JOIN stops s ON st.stop_id = s.stop_id
                WHERE st.stop_id = :stop_id
                  AND t.route_id = :route_id
                  AND st.arrival_time >= :current_time_seconds
                  AND st.arrival_time <= :notify_time_seconds;
            """)
            
            # We notify if bus is <= notify_minutes_before away
            notify_time_seconds = current_time_seconds + (sub.notify_minutes_before * 60) + 60
            
            result = await session.execute(query, {
                "stop_id": stop_id_int,
                "route_id": route_id_int,
                "current_time_seconds": current_time_seconds,
                "notify_time_seconds": notify_time_seconds
            })
            
            rows = result.fetchall()
            for row in rows:
                arrival_time_secs, trip_id, route_short_name, stop_name = row
                minutes_left = round((arrival_time_secs - current_time_seconds) / 60)
                
                if minutes_left < 0: continue
                
                # 3. Check if we already sent a notification for this trip/sub/date
                log_stmt = select(Notification_Log).where(
                    Notification_Log.subscription_id == sub.id,
                    Notification_Log.trip_id == str(trip_id),
                    Notification_Log.service_date == today
                )
                log_res = await session.execute(log_stmt)
                if log_res.scalar_one_or_none():
                    logger.debug(f"Already notified user {sub.chat_id} for trip {trip_id}")
                    continue
                
                # 4. Send notification
                message = f"🚌 Bus {route_short_name} is arriving at {stop_name} in {minutes_left} minutes!"
                logger.info(f"Sending notification to {sub.chat_id}: {message}")
                await bot.send_message(sub.chat_id, message)
                
                # 5. Log it
                new_log = Notification_Log(
                    subscription_id=sub.id,
                    trip_id=str(trip_id),
                    service_date=today,
                    sent_at=datetime.now(),
                    status="sent"
                )
                session.add(new_log)
        
        await session.commit()
