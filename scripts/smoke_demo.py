"""Read-only smoke checks for a running local WeatherFusion API."""
import json
from urllib.request import urlopen

base = "http://localhost:8000"
paths = ["/api/health", "/api/v1/system/status", "/api/v1/events", "/api/v1/events/summary", "/api/v1/review-queue", "/api/v1/analytics/overview", "/api/v1/sources", "/api/v1/weather/forecast"]
for path in paths:
    with urlopen(base + path, timeout=5) as response:  # noqa: S310
        print(path, response.status)
events = json.loads(urlopen(base + "/api/v1/events", timeout=5).read())  # noqa: S310
if not events["items"]:
    raise SystemExit("No demo events returned")
with urlopen(base + "/api/v1/events/" + events["items"][0]["id"], timeout=5) as response:  # noqa: S310
    print("event detail", response.status)
print("Smoke checks do not require a live Open-Meteo response: the forecast endpoint may report cached or unavailable context.")
