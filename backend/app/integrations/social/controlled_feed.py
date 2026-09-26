"""Deterministic social-weather connector for prototype demonstrations only."""

from typing import Any

from app.domain.events import EventCategory

WEATHER_HASHTAGS = frozenset(
    {"#imd", "#weather", "#rain", "#rainfall", "#heavyrain", "#flood", "#thunderstorm", "#heatwave", "#fog", "#duststorm", "#strongwind"}
)


def post(
    post_id: str, text: str, hashtags: list[str], city: str, state: str, latitude: float, longitude: float,
    category: EventCategory, severity: str, media: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {"post_id": post_id, "platform": "Prototype Social Dataset", "author_alias": "controlled-demo", "text": text, "hashtags": hashtags, "posted_at": "2026-09-19T08:00:00Z", "city": city, "state": state, "latitude": latitude, "longitude": longitude, "event_type": category.value, "severity": severity, "media": media or [], "source_url": f"demo://social/{post_id}"}


CONTROLLED_POSTS = [
    post("SOCIAL-001", "Heavy waterlogging reported near a city road.", ["#IMD", "#Flood", "#HeavyRain"], "Mumbai", "Maharashtra", 19.076, 72.8777, EventCategory.FLOOD, "HIGH", [{"media_type": "IMAGE", "reference": "demo://media/social-001.jpg", "mime_type": "image/jpeg", "caption": "Controlled flood evidence reference"}]),
    post("SOCIAL-002", "Persistent rainfall affecting the morning commute.", ["#Weather", "#Rainfall"], "Kochi", "Kerala", 9.9312, 76.2673, EventCategory.HEAVY_RAINFALL, "MODERATE"),
    post("SOCIAL-003", "Thunderstorm alerts and strong gusts this evening.", ["#IMD", "#Thunderstorm", "#StrongWind"], "Guwahati", "Assam", 26.1445, 91.7362, EventCategory.THUNDERSTORM, "HIGH"),
    post("SOCIAL-004", "Extreme afternoon heat reported across the city.", ["#IMD", "#Heatwave"], "Jaipur", "Rajasthan", 26.9124, 75.7873, EventCategory.HEATWAVE, "HIGH"),
    post("SOCIAL-005", "Low visibility reported on the highway this morning.", ["#Weather", "#Fog"], "Delhi", "Delhi", 28.6139, 77.209, EventCategory.FOG, "MODERATE"),
    post("SOCIAL-006", "Dust and gusty winds are reducing visibility.", ["#Weather", "#DustStorm", "#StrongWind"], "Jodhpur", "Rajasthan", 26.2389, 73.0243, EventCategory.DUST_STORM, "HIGH", [{"media_type": "VIDEO", "reference": "demo://media/social-006.mp4", "mime_type": "video/mp4", "caption": "Controlled dust storm evidence reference"}]),
    post("SOCIAL-007", "Short but intense rain near the market area.", ["#Rain", "#Weather"], "Bengaluru", "Karnataka", 12.9716, 77.5946, EventCategory.HEAVY_RAINFALL, "MODERATE"),
    post("SOCIAL-008", "Flooded underpass needs an operator check.", ["#IMD", "#Flood"], "Chennai", "Tamil Nadu", 13.0827, 80.2707, EventCategory.FLOOD, "HIGH"),
    post("SOCIAL-009", "Strong winds reported along the coast.", ["#Weather", "#StrongWind"], "Visakhapatnam", "Andhra Pradesh", 17.6868, 83.2185, EventCategory.STRONG_WIND, "MODERATE"),
    post("SOCIAL-010", "Dense fog reported around early rail services.", ["#Fog", "#IMD"], "Lucknow", "Uttar Pradesh", 26.8467, 80.9462, EventCategory.FOG, "MODERATE"),
    post("SOCIAL-011", "Heavy rain is causing local drainage overflow.", ["#HeavyRain", "#Rainfall"], "Bhubaneswar", "Odisha", 20.2961, 85.8245, EventCategory.HEAVY_RAINFALL, "HIGH"),
    post("SOCIAL-012", "Thunderclouds and lightning observed before sunset.", ["#Thunderstorm", "#Weather"], "Kolkata", "West Bengal", 22.5726, 88.3639, EventCategory.THUNDERSTORM, "MODERATE"),
    post("SOCIAL-013", "Heat conditions remain uncomfortable through the afternoon.", ["#Heatwave", "#IMD"], "Nagpur", "Maharashtra", 21.1458, 79.0882, EventCategory.HEATWAVE, "HIGH"),
    post("SOCIAL-014", "Dust haze moving through the outskirts.", ["#DustStorm", "#Weather"], "Ahmedabad", "Gujarat", 23.0225, 72.5714, EventCategory.DUST_STORM, "MODERATE"),
    post("SOCIAL-015", "Rainfall reported near the riverfront.", ["#Rainfall", "#IMD"], "Patna", "Bihar", 25.5941, 85.1376, EventCategory.HEAVY_RAINFALL, "MODERATE"),
    post("SOCIAL-016", "Wind warnings shared for exposed roads.", ["#StrongWind", "#Weather"], "Shimla", "Himachal Pradesh", 31.1048, 77.1734, EventCategory.STRONG_WIND, "MODERATE"),
    post("SOCIAL-017", "Waterlogging reported after sustained rainfall.", ["#Flood", "#Rain"], "Hyderabad", "Telangana", 17.385, 78.4867, EventCategory.FLOOD, "HIGH"),
    post("SOCIAL-018", "Fog conditions have eased near the airport.", ["#Fog", "#Weather"], "Srinagar", "Jammu and Kashmir", 34.0837, 74.7973, EventCategory.FOG, "LOW"),
    post("SOCIAL-019", "Community cultural event this evening.", ["#CityLife"], "Pune", "Maharashtra", 18.5204, 73.8567, EventCategory.UNKNOWN, "LOW"),
    post("SOCIAL-020", "Local road closure update.", ["#Traffic"], "Surat", "Gujarat", 21.1702, 72.8311, EventCategory.UNKNOWN, "LOW"),
]


class SocialWeatherConnector:
    """Contract boundary for future authorized social integrations."""

    async def fetch_posts(self) -> list[dict[str, Any]]:
        return CONTROLLED_POSTS.copy()

    @staticmethod
    def matches_weather_hashtag(post: dict[str, Any]) -> bool:
        return any(str(tag).lower() in WEATHER_HASHTAGS for tag in post.get("hashtags", []))

    @classmethod
    def normalize(cls, post: dict[str, Any]) -> dict[str, Any]:
        return {"source": "Controlled Social Weather Feed", "source_type": "SOCIAL_PROTOTYPE", "external_id": post["post_id"], "event_type": post.get("event_type", EventCategory.UNKNOWN), "severity": post.get("severity", "UNSPECIFIED"), "title": f"Social weather post: {post['post_id']}", "description": post["text"], "raw_text": post["text"], "latitude": post.get("latitude"), "longitude": post.get("longitude"), "state": post.get("state"), "city": post.get("city"), "observed_at": post["posted_at"], "metadata": {"origin_mode": "CONTROLLED_SOCIAL_FEED", "platform": post["platform"], "author_alias": post.get("author_alias"), "hashtags": post.get("hashtags", []), "source_reference": post.get("source_url"), "connector_version": "1.0", "controlled_data": True}}
