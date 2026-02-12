import gtfs_realtime_pb2
import requests

feed = gtfs_realtime_pb2.FeedMessage()
response = requests.get('http://20.19.98.194:8328/Api/api/gtfs-realtime')
print("Status Code:", response.status_code)
print("Content-Type:", response.headers.get("Content-Type"))
print("First 500 bytes of response:", response.content[:500])  # Show only the first 500 bytes

feed.ParseFromString(response.content)
count = 0
for entity in feed.entity:
  print(entity.trip_update)
  count += 1
print(count)
