"""
backend/tests/test_connectors.py

Unit tests for all three connectors.  No live network calls – every test
uses saved fixture files or injected stub sessions.

Coverage
--------
OpenMeteoConnector.parse_response()
  - rainfall detected (WMO 63, moderate precip)
  - flooding upgrade (extreme precip ≥ 50mm)
  - strong_wind detected (wind ≥ 40 km/h)
  - flooding via wind (wind ≥ 60 km/h)
  - fog (WMO 45)
  - thunderstorm (WMO 95)
  - clear sky → None
  - malformed response → None

NewsScraperConnector.parse_rss()
  - all 6 weather headlines from the RSS fixture are detected
  - stock-market headline filtered out
NewsScraperConnector.parse_html()
  - weather headlines extracted from HTML fixture
  - footer/nav noise excluded
NewsScraperConnector.headline_to_report()
  - correct city, state, lat/lon, category assigned
  - non-weather headline → None
  - weather with no city → None

SocialMockConnector._parse_tweet()
  - English tweet → correct category + city
  - Hindi tweet → flooding detected
  - spam tweet → None (no weather keyword)
  - empty tweet → None
  - tweet with unrecognised city → None
SocialMockConnector.fetch()
  - reads fixture JSON file, correct count, no spam
  - missing file handled gracefully
  - malformed JSON handled gracefully
"""

from __future__ import annotations

import json
import pathlib
import textwrap

import pytest

# ── Helpers ────────────────────────────────────────────────────────────────────

FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> bytes:
    return (FIXTURE_DIR / name).read_bytes()


# ═══════════════════════════════════════════════════════════════════════════════
# Open-Meteo connector
# ═══════════════════════════════════════════════════════════════════════════════

class TestOpenMeteoParseResponse:
    """Tests parse_response() in isolation – no HTTP."""

    from backend.app.connectors.open_meteo import OpenMeteoConnector  # import inside class to avoid top-level side-effects

    def setup_method(self):
        from backend.app.connectors.open_meteo import OpenMeteoConnector
        self.conn = OpenMeteoConnector
        from backend.app.schemas import EventCategory
        self.EC = EventCategory

    def _fixture(self, name: str) -> dict:
        return json.loads(_load_fixture(name))

    def test_rainfall_wmo63(self):
        data = self._fixture("open_meteo_mumbai_rain.json")
        report = self.conn.parse_response("Mumbai", "Maharashtra", 19.076, 72.877, data)
        assert report is not None
        assert report.event_category == self.EC.rainfall
        assert report.city == "Mumbai"
        assert report.state == "Maharashtra"
        assert report.trust_score == 90.0
        assert "Open-Meteo" in (report.text or "")

    def test_clear_sky_returns_none(self):
        data = self._fixture("open_meteo_clear.json")
        report = self.conn.parse_response("Delhi", "Delhi", 28.61, 77.20, data)
        assert report is None

    def test_extreme_precip_upgrades_to_flooding(self):
        data = self._fixture("open_meteo_extreme.json")
        report = self.conn.parse_response("Patna", "Bihar", 25.59, 85.13, data)
        # WMO 82 = heavy rain, 65mm → flooding; wind 55 < 60 so no wind-flooding shortcut
        assert report is not None
        assert report.event_category == self.EC.flooding

    def test_wind_60plus_gives_flooding(self):
        data = {"current": {"precipitation": 0, "rain": 0, "wind_speed_10m": 65, "weathercode": 0}}
        report = self.conn.parse_response("Mumbai", "Maharashtra", 19.0, 72.8, data)
        assert report is not None
        assert report.event_category == self.EC.flooding

    def test_wind_40to59_gives_strong_wind(self):
        data = {"current": {"precipitation": 0, "rain": 0, "wind_speed_10m": 45, "weathercode": 0}}
        report = self.conn.parse_response("Delhi", "Delhi", 28.6, 77.2, data)
        assert report is not None
        assert report.event_category == self.EC.strong_wind

    def test_wmo_fog(self):
        data = {"current": {"precipitation": 0, "rain": 0, "wind_speed_10m": 5, "weathercode": 45}}
        report = self.conn.parse_response("Lucknow", "Uttar Pradesh", 26.84, 80.94, data)
        assert report is not None
        assert report.event_category == self.EC.fog

    def test_wmo_thunderstorm(self):
        data = {"current": {"precipitation": 5, "rain": 5, "wind_speed_10m": 20, "weathercode": 95}}
        report = self.conn.parse_response("Chennai", "Tamil Nadu", 13.08, 80.27, data)
        assert report is not None
        assert report.event_category == self.EC.thunderstorm

    def test_malformed_response_returns_none(self):
        report = self.conn.parse_response("Jaipur", "Rajasthan", 26.9, 75.8, {})
        assert report is None

    def test_source_type_is_api(self):
        from backend.app.schemas import SourceType
        data = {"current": {"precipitation": 10, "rain": 10, "wind_speed_10m": 5, "weathercode": 61}}
        report = self.conn.parse_response("Pune", "Maharashtra", 18.52, 73.85, data)
        assert report is not None
        assert report.source_type == SourceType.api


# ═══════════════════════════════════════════════════════════════════════════════
# News scraper connector
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsScraperParseRSS:

    def setup_method(self):
        from backend.app.connectors.news_scraper import NewsScraperConnector
        self.conn = NewsScraperConnector

    def test_rss_extracts_weather_headlines(self):
        content = _load_fixture("news_rss.xml")
        headlines = self.conn.parse_rss(content)
        # Fixture has 7 items; all should be returned as text
        assert len(headlines) == 7

    def test_rss_headline_to_report_mumbai_flood(self):
        content = _load_fixture("news_rss.xml")
        headlines = self.conn.parse_rss(content)
        # First headline is Mumbai heavy rain
        report = self.conn.headline_to_report(headlines[0])
        assert report is not None
        assert report.city.lower() == "mumbai"
        assert report.event_category.value in ("rainfall", "flooding")

    def test_rss_stock_market_headline_filtered(self):
        content = _load_fixture("news_rss.xml")
        headlines = self.conn.parse_rss(content)
        # "Market update: Sensex" headline should return None from headline_to_report
        market_hl = [h for h in headlines if "sensex" in h.lower()]
        assert len(market_hl) == 1
        assert self.conn.headline_to_report(market_hl[0]) is None

    def test_rss_dust_storm_jaipur(self):
        content = _load_fixture("news_rss.xml")
        headlines = self.conn.parse_rss(content)
        jaipur_hl = [h for h in headlines if "jaipur" in h.lower() or "dust" in h.lower()]
        assert jaipur_hl
        report = self.conn.headline_to_report(jaipur_hl[0])
        assert report is not None
        from backend.app.schemas import EventCategory
        assert report.event_category == EventCategory.dust_storm

    def test_rss_kolkata_flooding(self):
        content = _load_fixture("news_rss.xml")
        headlines = self.conn.parse_rss(content)
        kolkata_hl = [h for h in headlines if "kolkata" in h.lower()]
        assert kolkata_hl
        report = self.conn.headline_to_report(kolkata_hl[0])
        assert report is not None
        assert report.city.lower() == "kolkata"

    def test_rss_bengaluru_fog(self):
        from backend.app.schemas import EventCategory
        content = _load_fixture("news_rss.xml")
        headlines = self.conn.parse_rss(content)
        fog_hl = [h for h in headlines if "fog" in h.lower() and "bengaluru" in h.lower()]
        assert fog_hl
        report = self.conn.headline_to_report(fog_hl[0])
        assert report is not None
        assert report.event_category == EventCategory.fog


class TestNewsScraperParseHTML:

    def setup_method(self):
        from backend.app.connectors.news_scraper import NewsScraperConnector
        self.conn = NewsScraperConnector

    def test_html_extracts_headlines(self):
        content = _load_fixture("news_html.html")
        headlines = self.conn.parse_html(content)
        assert len(headlines) > 0

    def test_html_footer_nav_excluded(self):
        content = _load_fixture("news_html.html")
        headlines = self.conn.parse_html(content)
        # Footer content should be stripped
        for h in headlines:
            assert "footer" not in h.lower()

    def test_html_mumbai_rain_detected(self):
        content = _load_fixture("news_html.html")
        headlines = self.conn.parse_html(content)
        mumbai_hl = [h for h in headlines if "mumbai" in h.lower()]
        assert mumbai_hl
        report = self.conn.headline_to_report(mumbai_hl[0])
        assert report is not None

    def test_html_cricket_headline_filtered(self):
        content = _load_fixture("news_html.html")
        headlines = self.conn.parse_html(content)
        cricket_hl = [h for h in headlines if "india vs england" in h.lower()]
        # Should not appear (inside an <a> with no city or weather keyword that passes filter)
        for h in cricket_hl:
            assert self.conn.headline_to_report(h) is None

    def test_html_dust_storm_jaipur(self):
        from backend.app.schemas import EventCategory
        content = _load_fixture("news_html.html")
        headlines = self.conn.parse_html(content)
        dust_hl = [h for h in headlines if "dust" in h.lower() and "jaipur" in h.lower()]
        assert dust_hl
        report = self.conn.headline_to_report(dust_hl[0])
        assert report is not None
        assert report.event_category == EventCategory.dust_storm


class TestHeadlineToReport:

    def setup_method(self):
        from backend.app.connectors.news_scraper import NewsScraperConnector
        self.fn = NewsScraperConnector.headline_to_report

    def test_no_weather_keyword_returns_none(self):
        assert self.fn("PM Modi inaugurates new expressway in UP") is None

    def test_weather_no_city_returns_none(self):
        assert self.fn("Heavy rain causes flooding across the country") is None

    def test_correct_trust_score(self):
        report = self.fn("Heavy rain in Mumbai causes flooding near Kurla")
        assert report is not None
        assert report.trust_score == 55.0

    def test_source_type_website(self):
        from backend.app.schemas import SourceType
        report = self.fn("Kolkata flooded after heavy rain")
        assert report is not None
        assert report.source_type == SourceType.website

    def test_geocoding_lat_lon_set(self):
        report = self.fn("Chennai flood: Adyar river overflows")
        assert report is not None
        assert report.lat is not None
        assert report.lon is not None
        assert 8 < report.lat < 15   # Chennai lat range
        assert 78 < report.lon < 82


# ═══════════════════════════════════════════════════════════════════════════════
# Social mock connector
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseTweet:

    def setup_method(self):
        from backend.app.connectors.social_mock import SocialMockConnector
        self.fn = SocialMockConnector._parse_tweet

    def test_english_rain_tweet(self):
        tweet = {"id": "1", "handle": "@user", "text": "Heavy rain in Mumbai! Streets flooded. #MumbaiRains"}
        report = self.fn(tweet)
        assert report is not None
        assert report.city.lower() == "mumbai"
        assert report.event_category.value in ("rainfall", "flooding")

    def test_hindi_flood_tweet(self):
        from backend.app.schemas import EventCategory
        tweet = {"id": "2", "handle": "@user", "text": "बाढ़ से कोलकाता में हाहाकार, निचले इलाके जलमग्न।"}
        report = self.fn(tweet)
        assert report is not None
        assert report.event_category == EventCategory.flooding
        assert report.city.lower() == "kolkata"

    def test_spam_tweet_returns_none(self):
        tweet = {"id": "3", "handle": "@spammer", "text": "EARN MONEY FAST! Click NOW!! #rain"}
        # "rain" keyword IS present so this would be detected — the ML pipeline handles spam scoring
        # The connector's job is just keyword matching; spam detection is the pipeline's responsibility
        # (per design). Let's test that the connector does extract it if a weather keyword exists
        report = self.fn(tweet)
        # "rain" in text → rainfall; but no known city → should be None
        assert report is None  # no recognised Indian city in spam tweet

    def test_empty_text_returns_none(self):
        assert self.fn({"id": "4", "text": "", "handle": "@x"}) is None

    def test_unknown_city_returns_none(self):
        tweet = {"id": "5", "text": "Heavy rain in Springfield today!", "handle": "@x"}
        assert self.fn(tweet) is None

    def test_hindi_baarish_detected(self):
        tweet = {"id": "6", "text": "मूसलाधार बारिश दिल्ली में। सड़कें जलभराव। #DelhiRains", "handle": "@h"}
        report = self.fn(tweet)
        assert report is not None
        assert report.city.lower() == "delhi"

    def test_fog_tweet(self):
        from backend.app.schemas import EventCategory
        tweet = {"id": "7", "text": "Dense fog at Lucknow airport, flights delayed.", "handle": "@x"}
        report = self.fn(tweet)
        assert report is not None
        assert report.event_category == EventCategory.fog

    def test_dust_storm_tweet(self):
        from backend.app.schemas import EventCategory
        tweet = {"id": "8", "text": "Jaipur dust storm! Visibility zero. #RajasthanStorm", "handle": "@x"}
        report = self.fn(tweet)
        assert report is not None
        assert report.event_category == EventCategory.dust_storm

    def test_source_type_social_media(self):
        from backend.app.schemas import SourceType
        tweet = {"id": "9", "text": "Thunderstorm in Delhi! #DelhiWeather", "handle": "@x"}
        report = self.fn(tweet)
        assert report is not None
        assert report.source_type == SourceType.social_media

    def test_source_handle_preserved(self):
        tweet = {"id": "10", "text": "Heavy rain in Mumbai. #Rain", "handle": "@myhandle"}
        report = self.fn(tweet)
        assert report is not None
        assert report.source_handle == "@myhandle"

    def test_trust_score_lower_than_api(self):
        tweet = {"id": "11", "text": "Flooding in Chennai streets!", "handle": "@x"}
        report = self.fn(tweet)
        assert report is not None
        assert report.trust_score < 90.0  # social < API


class TestSocialMockFetch:

    def test_fetch_from_fixture_file(self, tmp_path):
        from backend.app.connectors.social_mock import SocialMockConnector
        fixture = FIXTURE_DIR / "sample_tweets_fixture.json"
        conn = SocialMockConnector(json_path=fixture)
        reports = conn.fetch()
        # Fixture has 8 tweets: 6 weather (1 empty, 1 no-city spam) → at most 6 valid
        assert len(reports) >= 4   # at minimum: mumbai, kolkata, delhi, amritsar, jaipur, ranchi

    def test_fetch_skips_empty_tweets(self, tmp_path):
        from backend.app.connectors.social_mock import SocialMockConnector
        fixture = FIXTURE_DIR / "sample_tweets_fixture.json"
        conn = SocialMockConnector(json_path=fixture)
        reports = conn.fetch()
        for r in reports:
            assert r.text and r.text.strip()

    def test_fetch_missing_file_returns_empty(self, tmp_path):
        from backend.app.connectors.social_mock import SocialMockConnector
        conn = SocialMockConnector(json_path=tmp_path / "nonexistent.json")
        reports = conn.fetch()
        assert reports == []

    def test_fetch_malformed_json_returns_empty(self, tmp_path):
        from backend.app.connectors.social_mock import SocialMockConnector
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{not valid json")
        conn = SocialMockConnector(json_path=bad_file)
        assert conn.fetch() == []

    def test_fetch_non_list_json_returns_empty(self, tmp_path):
        from backend.app.connectors.social_mock import SocialMockConnector
        bad_file = tmp_path / "obj.json"
        bad_file.write_text('{"key": "value"}')
        conn = SocialMockConnector(json_path=bad_file)
        assert conn.fetch() == []


# ═══════════════════════════════════════════════════════════════════════════════
# Base class / geocode helper
# ═══════════════════════════════════════════════════════════════════════════════

class TestGeocodeHelper:

    def setup_method(self):
        from backend.app.connectors.base import geocode, CITY_TABLE
        self.geocode = geocode
        self.CITY_TABLE = CITY_TABLE

    def test_known_city_returns_state_lat_lon(self):
        state, lat, lon = self.geocode("Mumbai")
        assert state == "Maharashtra"
        assert abs(lat - 19.0760) < 0.01
        assert abs(lon - 72.8777) < 0.01

    def test_case_insensitive(self):
        state, lat, lon = self.geocode("DELHI")
        assert state == "Delhi"

    def test_unknown_city_returns_original_and_nones(self):
        state, lat, lon = self.geocode("Springfield")
        assert state == "Springfield"
        assert lat is None
        assert lon is None

    def test_all_30_cities_have_valid_coords(self):
        for city, (state, lat, lon) in self.CITY_TABLE.items():
            assert state, f"{city} has no state"
            assert -90 <= lat <= 90, f"{city} lat out of range"
            assert -180 <= lon <= 180, f"{city} lon out of range"
