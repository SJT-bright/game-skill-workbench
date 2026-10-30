#!/usr/bin/env python3
"""Timing validity of chrome_touch.py (v7.5, LunasJade D3 problem 4): every whole second up to the last mark
must reach 30 rAF frames; a covered Ego tab (~1 fps while loading) makes the run invalid. No browser needed."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
import chrome_touch as ct


def doc(per, frames=None, ms=None):
    return {'raf': {'perSec': per, 'frames': frames, 'ms': ms}}


class TimingFps(unittest.TestCase):
    def test_throttled_loading_seconds_are_invalid_even_if_median_is_60(self):
        low, median = ct.frame_rate(doc([1, 1, 60, 60, 60, 60, 60]), window_ms=1500)
        self.assertEqual((low, median), (1, 60))
        self.assertLess(low, ct.MIN_TIMING_FPS)

    def test_smooth_run_is_valid(self):
        low, _ = ct.frame_rate(doc([61, 60, 60, 60, 60]), window_ms=19)
        self.assertGreaterEqual(low, ct.MIN_TIMING_FPS)

    def test_throttle_after_the_last_mark_does_not_count(self):
        low, _ = ct.frame_rate(doc([60, 60, 1, 1]), window_ms=1800)
        self.assertEqual(low, 60)

    def test_no_marks_uses_whole_run(self):
        self.assertEqual(ct.frame_rate(doc([60, 59, 2]))[0], 2)

    def test_short_page_life_uses_average_and_unmeasured_is_none(self):
        self.assertEqual(ct.frame_rate(doc([], frames=18, ms=296))[0], 61)
        self.assertEqual(ct.frame_rate(doc([], frames=1, ms=50)), (None, None))
        self.assertEqual(ct.frame_rate(None), (None, None))

    def test_prelude_starts_screencast_and_records_raf(self):
        self.assertIn('Page.startScreencast', ct.TIMING_PRELUDE)
        self.assertIn('fps.json', ct.TIMING_PRELUDE)
        self.assertIn('requestAnimationFrame', ct.RAF_JS)


if __name__ == '__main__':
    unittest.main()
