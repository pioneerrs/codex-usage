import unittest
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from codex_usage.codex_logs import _day_bounds, _new_timeline_buckets, resolve_time_window


class TimeWindowTests(unittest.TestCase):
    def setUp(self):
        self.new_york = ZoneInfo("America/New_York")

    def test_winter_and_summer_dates_use_date_specific_offsets(self):
        winter_start, _ = _day_bounds(date(2026, 1, 15), tz=self.new_york)
        summer_start, _ = _day_bounds(date(2026, 7, 15), tz=self.new_york)

        self.assertEqual(winter_start.utcoffset(), timedelta(hours=-5))
        self.assertEqual(summer_start.utcoffset(), timedelta(hours=-4))

    def test_spring_dst_day_has_23_real_hours(self):
        start, end = _day_bounds(date(2026, 3, 8), tz=self.new_york)

        elapsed = end.astimezone(timezone.utc) - start.astimezone(timezone.utc)
        self.assertEqual(elapsed, timedelta(hours=23) - timedelta(microseconds=1))

    def test_fall_dst_day_has_25_real_hours(self):
        start, end = _day_bounds(date(2026, 11, 1), tz=self.new_york)

        elapsed = end.astimezone(timezone.utc) - start.astimezone(timezone.utc)
        self.assertEqual(elapsed, timedelta(hours=25) - timedelta(microseconds=1))

    def test_spring_timeline_has_23_distinct_real_hour_buckets(self):
        start, end = _day_bounds(date(2026, 3, 8), tz=self.new_york)
        buckets = _new_timeline_buckets(start, end)

        self.assertEqual(len(buckets), 23)
        starts = [row["bucketStart"].astimezone(timezone.utc) for row in buckets]
        self.assertEqual(len(starts), len(set(starts)))

    def test_fall_timeline_has_25_real_hour_buckets(self):
        start, end = _day_bounds(date(2026, 11, 1), tz=self.new_york)
        buckets = _new_timeline_buckets(start, end)

        self.assertEqual(len(buckets), 25)

    def test_from_and_to_dates_each_resolve_in_target_zone(self):
        start, end = resolve_time_window(
            from_value="2026-03-08",
            to_value="2026-03-09",
            tz=self.new_york,
        )

        self.assertEqual(start.utcoffset(), timedelta(hours=-5))
        self.assertEqual(end.utcoffset(), timedelta(hours=-4))
        self.assertEqual(start.date(), date(2026, 3, 8))
        self.assertEqual(end.date(), date(2026, 3, 9))

    def test_multi_day_timeline_stays_aligned_to_local_midnight_across_dst(self):
        start, _ = _day_bounds(date(2026, 3, 7), tz=self.new_york)
        _, end = _day_bounds(date(2026, 3, 10), tz=self.new_york)
        buckets = _new_timeline_buckets(start, end)

        self.assertEqual([row["bucketStart"].hour for row in buckets], [0, 0, 0, 0])
        self.assertEqual(
            [row["bucketStart"].date() for row in buckets],
            [date(2026, 3, 7), date(2026, 3, 8), date(2026, 3, 9), date(2026, 3, 10)],
        )


if __name__ == "__main__":
    unittest.main()
