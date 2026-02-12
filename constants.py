from zoneinfo import ZoneInfo
CYPRUS_TZ = ZoneInfo("Asia/Nicosia")

ZIP_URLS = ["https://www.motionbuscard.org.cy/opendata/downloadfile?file=GTFS%5C6_google_transit.zip&rel=True",
            "https://www.motionbuscard.org.cy/opendata/downloadfile?file=GTFS%5C2_google_transit.zip&rel=True",
            "https://www.motionbuscard.org.cy/opendata/downloadfile?file=GTFS%5C4_google_transit.zip&rel=True",
            "https://www.motionbuscard.org.cy/opendata/downloadfile?file=GTFS%5C5_google_transit.zip&rel=True",
            "https://www.motionbuscard.org.cy/opendata/downloadfile?file=GTFS%5C9_google_transit.zip&rel=True",
            "https://www.motionbuscard.org.cy/opendata/downloadfile?file=GTFS%5C10_google_transit.zip&rel=True",
            "https://www.motionbuscard.org.cy/opendata/downloadfile?file=GTFS%5C11_google_transit.zip&rel=True"]
SOURCE = "google_transit_files"
TARGET = "otp_data"
ALLOWED_FILES = {"stops.txt", "routes.txt", "trips.txt", "stop_times.txt", "calendar_dates.txt", "agency.txt", "shapes.txt"}
OSM_FOLDER = "osm_data"

GTFS_REALTIME_API_PATH = 'http://20.19.98.194:8328/Api/api/gtfs-realtime'

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
