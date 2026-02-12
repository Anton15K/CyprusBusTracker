from fastapi import FastAPI, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from crud import get_trips_within_hour, get_all_stops, update_stop_times_and_get_buses, get_shape_for_bus, get_routes_by_stop_id, stops_on_route
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
import subprocess
from db_manager import db_manager
from make_route import query_graphql
from constants import GRAPHQL_QUERY
from DatabaseReset import GTFSDataReloader
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from constants import TARGET
from constants import ZIP_URLS, CYPRUS_TZ, SOURCE
all_stops = []
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000


def start_otp_low_priority():
    cmd = f'java -Xmx128M -jar otp-shaded-2.7.0.jar --load "{TARGET}" --port 8085'
    return subprocess.Popen(cmd, creationflags=BELOW_NORMAL_PRIORITY_CLASS, shell=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    reloader = GTFSDataReloader(
        db_manager=db_manager,
        gtfs_folder=SOURCE,
        zip_urls=ZIP_URLS
    )
    "Upload GTFS data to the database when the app starts"
    await reloader.run_all()
    async with db_manager.session_factory() as session:
        global all_stops
        all_stops = await get_all_stops(session)
    # Start OTP
    otp_process = start_otp_low_priority()
    print(f"OTP server PID {otp_process.pid} started.")
    # Schedule the GTFS data reload job
    scheduler = AsyncIOScheduler()
    trigger = CronTrigger(
        hour=3,
        minute=0,
        timezone=CYPRUS_TZ
    )
    scheduler.add_job(reloader.run_all, trigger, id="daily_gtfs_reload")
    scheduler.start()

    try:
        yield
    finally:
        # Shutdown scheduler and OTP on app exit
        scheduler.shutdown(wait=False)
        print("Scheduler shut down.")
        otp_process.terminate()
        print("OTP server terminated.")
        await db_manager.engine.dispose
        print("Database sessions closed.")

app = FastAPI(lifespan=lifespan)

# Set up templates
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def home(request: Request, session: AsyncSession = Depends(db_manager.scoped_session_dependency)):
    #buses = await update_stop_times_and_get_buses(session)
    return templates.TemplateResponse("map.html", {"request": request, "stops": all_stops, "buses": []})

@app.get("/stops/{stop_id}")
async def trips_within_hour(stop_id: int, session: AsyncSession = Depends(db_manager.scoped_session_dependency)):
    routes = await get_trips_within_hour(session, stop_id)
    return routes

@app.get("/stops/routes_stopping_at/{stop_id}")
async def routes_stopping_at(stop_id: int, session: AsyncSession = Depends(db_manager.scoped_session_dependency)):
    routes = await get_routes_by_stop_id(session, stop_id)
    return routes

@app.get("/api/get_buses")
async def get_buses(session: AsyncSession = Depends(db_manager.scoped_session_dependency)):
    buses = []
    try:
        buses = await update_stop_times_and_get_buses(session)
        # print(buses)
    except Exception as e:
        print(e)                         
    return JSONResponse(content=buses)

@app.get("/buses/get_stops_on_route/{route_id}")
async def get_stops_on_route(route_id: int, session: AsyncSession = Depends(db_manager.scoped_session_dependency)):
    stops = await stops_on_route(session, route_id)
    return JSONResponse(content=stops)

@app.get("/api/get_shape/{route_id}")
async def get_shape(route_id: int, session: AsyncSession = Depends(db_manager.scoped_session_dependency)):
    shape = await get_shape_for_bus(session, route_id)
    return JSONResponse(content=shape)

@app.post("/api/make_route")
async def make_route_endpoint(request: Request):
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from e

    # Validate required data
    origin = payload.get("origin")
    destination = payload.get("destination")
    if not origin or not destination:
        raise HTTPException(status_code=400,
                            detail="Both 'origin' and 'destination' must be provided.")
    
    try:
        origin_lat = float(origin.get("lat"))
        origin_lng = float(origin.get("lng"))
        dest_lat = float(destination.get("lat"))
        dest_lng = float(destination.get("lng"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400,
                            detail="Coordinates must be provided as numbers.")

    try:
        # Call the synchronous function that queries OTP.
        result = query_graphql(
            GRAPHQL_QUERY,
            coord_from=(origin_lat, origin_lng),
            coord_to=(dest_lat, dest_lng)
        )
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Error querying OTP: {str(e)}") from e

    return JSONResponse(content=result)

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
