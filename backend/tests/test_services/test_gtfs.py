
from app.db.crud import seconds_to_minutes
from app.services.gtfs_static import parse_time


class TestParseTime:
    def test_normal_time(self):
        assert parse_time("08:30:00") == 8 * 3600 + 30 * 60

    def test_midnight(self):
        assert parse_time("00:00:00") == 0

    def test_over_24h(self):
        # GTFS allows times > 24h for trips that go past midnight
        assert parse_time("25:00:00") == 25 * 3600

    def test_empty_string(self):
        assert parse_time("") is None

    def test_none_like_falsy(self):
        result = parse_time("")
        assert result is None


class TestSecondsToMinutes:
    def test_exact(self):
        assert seconds_to_minutes(3600) == 60

    def test_rounding(self):
        assert seconds_to_minutes(90) == 2  # rounds 1.5 → 2

    def test_zero(self):
        assert seconds_to_minutes(0) == 0
