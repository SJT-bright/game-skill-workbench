#!/usr/bin/env python3
"""v7.7.4 (总表 B18, C2-自检2): a check that cannot run must refuse, never pass.

- package_gates.run: a gate module file that is missing was only listed in `missing` and skipped; now it blocks.
- kit_parts: a package whose engine is not recognised returned no finding at all, so every standard-part check was
  skipped; now K_engine_unknown blocks a new game and warns for an old one.
Real packages (2026-10-30): FoxDenDash v1 with cocos2d-js-min.js renamed -> K_engine_unknown block under policy new;
the unchanged package has no K_engine_unknown; a copy of the scripts without package_gates/webp.py -> GATE_MISSING_webp.
"""
import unittest

import package_gates as G
from package_gates import kit_parts


class MissingGateBlocks(unittest.TestCase):
    def test_missing_gate_module_blocks(self):
        result = G.run({}, modules=('network', 'no_such_gate'), policy='legacy')
        self.assertIn('no_such_gate', result['missing'])
        self.assertIn('GATE_MISSING_no_such_gate', [b['id'] for b in result['blocks']])

    def test_release_has_every_gate_module(self):
        result = G.run({'game.js': b'console.log(1);'}, policy='legacy')
        self.assertEqual(result['missing'], [])
        self.assertFalse([b for b in result['blocks'] if b['id'].startswith('GATE_MISSING_')], result['blocks'])


class UnknownEngineIsReported(unittest.TestCase):
    FILES = {'game.js': b'require("./main.js");', 'game.json': b'{}', 'main.js': b'console.log(1);'}

    def findings(self, policy):
        view = G.PackageView(dict(self.FILES), policy=policy)
        self.assertNotIn(view.engine_major, (2, 3))
        return kit_parts.check(view)

    def test_new_game_is_blocked(self):
        found = self.findings('new')
        self.assertEqual([(f['id'], f['level']) for f in found], [('K_engine_unknown', 'block')])

    def test_old_game_gets_a_warning(self):
        found = self.findings('legacy')
        self.assertEqual([(f['id'], f['level']) for f in found], [('K_engine_unknown', 'warn')])


if __name__ == '__main__':
    unittest.main()
