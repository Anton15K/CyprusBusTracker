from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import requests
import json
import polyline

from constants import GRAPHQL_QUERY
from constants import CYPRUS_TZ

def get_current_time_iso_format():
    now = datetime.now(CYPRUS_TZ)
    return now.isoformat(timespec='minutes')

def parse_iso(s):
    return datetime.fromisoformat(s)

def decode_leg_geometry(leg):
    try:
        encoded_points = leg['legGeometry']['points']
        return polyline.decode(encoded_points)
    except (KeyError, TypeError):
        return []
    
def query_graphql(query, coord_from, coord_to):
    url = "http://localhost:8080/otp/gtfs/v1"
    headers = {"Content-Type": "application/json"}

    time_value = get_current_time_iso_format()
    query = query.format(
        lat_from=coord_from[0],
        lon_from=coord_from[1],
        lat_to=coord_to[0],
        lon_to=coord_to[1],
        time_value=time_value
    )
    
    payload = {"query": query}
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    response_data = response.json()
    response_data = sorted(response_data['data']['planConnection']['edges'], key=lambda e: parse_iso(e['node']['end']))
    for edge in response_data:
      node = edge['node']
      for leg in node['legs']:
          path = decode_leg_geometry(leg)
          geometry = [[lat, lon] for lat, lon in path]
          leg['legGeometry']['points'] = geometry
    return response_data

if __name__ == "__main__":
  try:
      print(get_current_time_iso_format())
      result = query_graphql(GRAPHQL_QUERY, (33.5, 34.0), (33.6, 35.1))
      print(json.dumps(result, indent=2))
  except requests.RequestException as e:
      print(f"GraphQL request failed: {e}")