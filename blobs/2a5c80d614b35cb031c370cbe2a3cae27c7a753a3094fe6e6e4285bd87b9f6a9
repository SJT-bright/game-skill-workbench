#!/usr/bin/env python3
"""Regression tests for stable screen IDs across mobile viewport captures."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import extract_ui_layout as extract  # noqa: E402


def dump(path, screen, width, height):
    payload = {
        'tool': 'ui_dump',
        'screen': screen,
        'kind': 'page',
        'page': {'width': width, 'height': height, 'dpr': 3},
        'canvas_css': [0, 0, width, height],
        'nodes': [],
    }
    path.write_text(json.dumps(payload))
    return path


class StableScreenViewportTests(unittest.TestCase):
    def test_same_stable_screen_id_is_allowed_for_distinct_phone_sizes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tall = dump(root / 'tall-ui-dump-home.json', 'home', 393, 852)
            short = dump(root / 'short-ui-dump-home.json', 'home', 375, 667)
            layout = extract.build([tall, short])
            self.assertEqual([s['name'] for s in layout['screens']], ['home_375x667', 'home_393x852'])

    def test_duplicate_stable_id_at_same_phone_size_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = dump(root / 'first-ui-dump-map.json', 'map', 393, 852)
            second = dump(root / 'second-ui-dump-map.json', 'map', 393, 852)
            with self.assertRaisesRegex(ValueError, 'dumped twice'):
                extract.build([first, second])


if __name__ == '__main__':
    unittest.main(verbosity=2)
