from app.integrations.social.controlled_feed import CONTROLLED_POSTS, SocialWeatherConnector


def test_hashtag_matching_is_case_insensitive_and_excludes_non_weather_posts() -> None:
    assert SocialWeatherConnector.matches_weather_hashtag({"hashtags": ["#imd"]})
    assert SocialWeatherConnector.matches_weather_hashtag({"hashtags": ["#IMD"]})
    assert not SocialWeatherConnector.matches_weather_hashtag({"hashtags": ["#CityLife"]})


def test_controlled_post_normalizes_to_existing_event_contract() -> None:
    record = SocialWeatherConnector.normalize(CONTROLLED_POSTS[0])
    assert record["external_id"] == "SOCIAL-001"
    assert record["metadata"]["origin_mode"] == "CONTROLLED_SOCIAL_FEED"
    assert record["metadata"]["hashtags"] == ["#IMD", "#Flood", "#HeavyRain"]
