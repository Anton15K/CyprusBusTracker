from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root is three levels up from this file
_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    # Database
    db_url: str = "postgresql+asyncpg://cyprusbus:cyprusbus@localhost:5432/cyprusbus"
    db_echo: bool = False

    # GTFS data paths
    gtfs_source_folder: str = str(_REPO_ROOT / "google_transit_files")
    gtfs_target_folder: str = str(_REPO_ROOT / "otp_data")
    gtfs_osm_folder: str = str(_REPO_ROOT / "osm_data")

    # GTFS realtime
    gtfs_realtime_url: str = "http://20.19.98.194:8328/Api/api/gtfs-realtime"

    # OTP
    otp_url: str = "http://localhost:8080/otp/gtfs/v1"
    otp_jar: str = "otp-shaded-2.7.0.jar"
    otp_port: int = 8085
    manage_otp: bool = True

    # Scheduler
    reload_hour: int = 3
    reload_minute: int = 0

    # Frontend paths
    templates_dir: str = str(_REPO_ROOT / "frontend" / "templates")
    static_dir: str = str(_REPO_ROOT / "frontend" / "static")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

# ---------------------------------------------------------------------------
# Module-level constants (not environment-dependent)
# ---------------------------------------------------------------------------

CYPRUS_TZ = ZoneInfo("Asia/Nicosia")

ZIP_URLS = [
    "https://www.motionbuscard.org.cy/opendata/downloadfile?file=GTFS%5C6_google_transit.zip&rel=True",
    "https://www.motionbuscard.org.cy/opendata/downloadfile?file=GTFS%5C2_google_transit.zip&rel=True",
    "https://www.motionbuscard.org.cy/opendata/downloadfile?file=GTFS%5C4_google_transit.zip&rel=True",
    "https://www.motionbuscard.org.cy/opendata/downloadfile?file=GTFS%5C5_google_transit.zip&rel=True",
    "https://www.motionbuscard.org.cy/opendata/downloadfile?file=GTFS%5C9_google_transit.zip&rel=True",
    "https://www.motionbuscard.org.cy/opendata/downloadfile?file=GTFS%5C10_google_transit.zip&rel=True",
    "https://www.motionbuscard.org.cy/opendata/downloadfile?file=GTFS%5C11_google_transit.zip&rel=True",
]

ALLOWED_FILES = {
    "stops.txt",
    "routes.txt",
    "trips.txt",
    "stop_times.txt",
    "calendar_dates.txt",
    "agency.txt",
    "shapes.txt",
}

GRAPHQL_QUERY = """
query GtfsExampleQuery {{
  planConnection(
    origin: {{
      location: {{ coordinate: {{ latitude: {lat_from}, longitude: {lon_from} }} }}
    }}
    destination: {{
      location: {{ coordinate: {{ latitude: {lat_to}, longitude: {lon_to} }} }}
    }}
    dateTime: {{ earliestDeparture: "{time_value}" }}
    modes: {{
      direct: [WALK]
      transit: {{ transit: [{{ mode: BUS }}, {{ mode: RAIL }}] }}
    }}
  ) {{
    edges {{
      node {{
        start
        end
        legs {{
          mode
          from {{
            name
            lat
            lon
            departure {{
              scheduledTime
              estimated {{
                time
                delay
              }}
            }}
          }}
          to {{
            name
            lat
            lon
            arrival {{
              scheduledTime
              estimated {{
                time
                delay
              }}
            }}
          }}
          route {{
            gtfsId
            longName
            shortName
          }}
          legGeometry {{
            points
          }}
        }}
      }}
    }}
  }}
}}
"""
