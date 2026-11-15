import json
from pathlib import Path
import tempfile
import unittest
from tiktok_finalize_steps import policy as P


class ProductionAdmission(unittest.TestCase):
    def test_new_localization_requires_inputs_and_keeps_them_on_reinit(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            first = P.write_marker(p, 'localize', 'fixture', reason='init')
            self.assertEqual(first['production_inputs'], 'required')
            again = P.write_marker(p, 'localize', 'fixture2', reason='adopt')
            self.assertEqual(again['production_inputs'], 'required')

    def test_existing_and_adopt_only_work_not_retroactively_admitted(self):
        for existing, reason, board in [(True, 'init', 'localize'), (False, 'adopt', 'localize'),
                                         (False, 'init', 'remake')]:
            with self.subTest(existing=existing, reason=reason, board=board), tempfile.TemporaryDirectory() as temp:
                p = Path(temp)
                if existing:
                    path = p / P.MARKER; path.parent.mkdir(parents=True)
                    path.write_text('{"policy":"new","board":"localize","created":"old"}')
                row = P.write_marker(p, board, 'fixture', reason=reason)
                self.assertNotIn('production_inputs', row)


if __name__ == '__main__':
    unittest.main()
