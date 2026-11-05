#!/usr/bin/env python3
"""P20 第 3 点「能力先判」(问题普查 20261104): one capability record, read by diagnoses and checks.

Fixtures are the census cases: 旋律动物园 / 合成大西瓜 / 人鱼逃脱 (07:467 07:468 07:527: no coin, still asked for B),
弹弹球 (07:460: no coin, no items, x2 asked for and forbidden at once), 美人鱼 (05:158: no pause key written, the case
skipped), 割草 (05:159: ad entry list empty, skipped). The old code is judged through the same calls with no record
(OLD_SCRIPTS=<11.12 remake-core/scripts> runs this file against the old scripts: the new names are missing there).
  python3 -B test_game_capabilities.py
"""
import importlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(os.environ.get('OLD_SCRIPTS') or Path(__file__).resolve().parent)
sys.path.insert(0, str(HERE))
RR_DIR = HERE.parents[1] / 'cocos-game-check' / 'package-check' / 'scripts'
sys.path.insert(0, str(RR_DIR))
pc = importlib.import_module('product_contract')
fp = importlib.import_module('feature_policy')
rr = importlib.import_module('runtime_regression')

# auto-scan snapshot of a no-coin game: no currencies list, B not found, +3 energy platform rows
NO_COIN_SNAPSHOT = {'schema': 'economy_snapshot.v1', 'game': {'name': 'MelodyZoo', 'kind': 'english', 'mode': 'endless'},
                    'meta': {'source': 'auto_scan'}, 'B': {'value': None, 'how': 'unknown'},
                    'inflows': [{'id': 'shortcut', 'rule': 'ECON-SHORTCUT', 'currency': 'energy', 'amount': 3, 'per': 'once'},
                                {'id': 'revisit', 'rule': 'ECON-REVISIT', 'currency': 'energy', 'amount': 3, 'per': 'once'}],
                    'sinks': [], 'systems': {'result_x2': False}}
# 搭桥小能手 / 笨鸟快跑 / 剪纸小子 (07:489 07:490 07:528): energy only, no coin, nothing to pick up
ADAPTER_NO_DOUBLE = {'home': 'return true', 'ad_entries': [
    {'id': 'revive', 'role': 'revive', 'button': 'Canvas/Revive/btn_ad', 'states': [{'name': 'after_fail', 'why': 'x'}]}]}


def eco(wallet, items, skins=False, energy=False):
    return {'schema': 'economy_capabilities.v1', 'wallet': wallet, 'items': items, 'skins': skins, 'energy': energy,
            'wallet_plan': 'keep' if wallet else ('none' if energy else 'add_main_currency_and_skins'),
            'written_by': 'make_economy_config.py'}


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, rel, doc):
        p = self.dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, ensure_ascii=False), encoding='utf-8')

    def gc(self):
        return importlib.import_module('game_capabilities')


class EconomyAuditReadsRecord(Base):
    def test_old_way_blocks_no_coin_game(self):
        """旋律动物园 07:467: without the record the audit asks for B (error) - the census false block."""
        r = pc.economy_audit(json.loads(json.dumps(NO_COIN_SNAPSHOT)), 'english')
        row = {x['id']: x for x in r['results']}['ECON-B']
        self.assertEqual(row['status'], 'error')
        self.assertFalse(r['ok'])

    def test_record_wallet_false_is_not_applicable(self):
        self.write('docs/economy/economy_capabilities.json', eco(False, False, energy=True))
        caps = self.gc().load(self.dir)
        r = pc.economy_audit(json.loads(json.dumps(NO_COIN_SNAPSHOT)), 'english', caps)
        rows = {x['id']: x for x in r['results']}
        self.assertEqual(rows['ECON-B']['status'], 'skip')
        self.assertTrue(any('wallet=false' in d for d in rows['ECON-B']['details']), rows['ECON-B'])
        self.assertEqual(rows['ECON-X2']['status'], 'skip')
        self.assertEqual(rows['ECON-NOCUR']['status'], 'skip')     # 弹弹球: no items -> no x2, not an error
        self.assertTrue(r['ok'], r['counts'])

    def test_no_record_is_not_run_not_error(self):
        caps = self.gc().load(self.dir)        # project given, nothing written
        r = pc.economy_audit(json.loads(json.dumps(NO_COIN_SNAPSHOT)), 'english', caps)
        row = {x['id']: x for x in r['results']}['ECON-B']
        self.assertEqual(row['status'], 'not_run')
        self.assertIn('economy_capabilities.json', row['details'][0])
        self.assertFalse(r['ok'])
        self.assertEqual(r['not_run'], ['ECON-B'])

    def test_cli_exit_codes(self):
        snap = self.dir / 'snap.json'
        snap.write_text(json.dumps(NO_COIN_SNAPSHOT), encoding='utf-8')
        argv = ['economy-audit', '--snapshot', str(snap), '--project', str(self.dir), '--out', str(self.dir / 'r.json')]
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(pc._main(argv), 2)                 # no record: not_run
            self.write('docs/economy/economy_capabilities.json', eco(False, False, energy=True))
            self.assertEqual(pc._main(argv), 0)                 # record: no coin, passes

    def test_record_wallet_true_beats_snapshot(self):
        self.write('docs/economy/economy_capabilities.json', eco(True, True))
        snap = dict(json.loads(json.dumps(NO_COIN_SNAPSHOT)), currencies=[])
        r = pc.economy_audit(snap, 'english', self.gc().load(self.dir))
        self.assertEqual({x['id']: x for x in r['results']}['ECON-B']['status'], 'error')   # has coins: B must be found
        self.assertTrue(any('wallet=true' in w for w in r['schema_warnings']))

    def test_no_capabilities_argument_is_unchanged(self):
        a = pc.economy_audit(json.loads(json.dumps(NO_COIN_SNAPSHOT)), 'english')
        self.assertNotIn('capabilities', a)
        self.assertEqual(a['not_run'], [])


class FeaturePolicyByCapability(Base):
    def test_applies_reads_record(self):
        self.assertEqual(fp.applies('econ_b', 'localize', self.dir), 'not_run')
        self.write('docs/economy/economy_capabilities.json', eco(False, True))
        v, why = fp.capability('econ_b', self.dir)
        self.assertEqual(v, 'not_applicable')
        self.assertIn('wallet=false', why)
        self.assertEqual(fp.applies('result_x2_items', 'localize', self.dir), 'block')
        self.assertEqual(fp.applies('skin_rules', 'localize', self.dir), 'not_applicable')
        self.assertEqual(fp.applies('small_value_font', 'localize'), 'hint')     # board rules unchanged

    def test_pause_button_none_and_missing(self):
        """美人鱼 05:158: no pause key written -> before: the case skipped silently; now not_run names the field."""
        v, why = fp.capability('pause_popup_case', self.dir)
        self.assertEqual(v, 'not_run')
        self.assertIn('pause_button', why)
        self.write('docs/game_capabilities.json', {'schema': 'game_capabilities.v1',
                                                   'pause_button': {'none': 'one-screen idle game, no level'}})
        v, why = fp.capability('pause_popup_case', self.dir)
        self.assertEqual(v, 'not_applicable')
        self.assertIn('one-screen idle game', why)


class RecordAndAdapter(Base):
    def test_write_refuses_bad_and_writes_good(self):
        g = self.gc()
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(g.main(['write', '--project', str(self.dir), '--pause-button', 'Canvas/Game/btn_pause',
                                     '--ad-entry', 'double=Canvas/Result/btn_x2', '--ad-entry', 'revive=Canvas/Revive/btn_ad']), 0)
            self.assertEqual(g.main(['write', '--project', str(self.dir), '--no-pause-button', ' ',
                                     '--no-ad-entries', 'x']), 1)          # empty reason refused, file unchanged
        doc = json.loads((self.dir / 'docs/game_capabilities.json').read_text(encoding='utf-8'))
        self.assertEqual(doc['pause_button'], 'Canvas/Game/btn_pause')
        self.assertEqual(g.validate(doc), [])

    def test_adapter_fill_pause_and_empty_ad_entries(self):
        """美人鱼 / 割草: adapter without pause_button and without ad_entries. Old: the runner sees nothing to run.
        New: the record fills pause_button; ad roles listed without states -> not_run names what is missing."""
        g = self.gc()
        adapter = {'home': 'return true', 'resume_play': {'start': [{'tap': 'Canvas/play'}], 'probe': {'tap': 'x'},
                                                          'state_js': 'return 1'}}
        filled, notes, missing = g.fill_adapter(adapter, g.load(self.dir))
        self.assertNotIn('pause_button', filled['resume_play'])
        self.assertTrue(any('pause_button' in m for m in missing))
        self.assertTrue(any('ad_entries' in m for m in missing))
        self.write('docs/game_capabilities.json', {'schema': 'game_capabilities.v1', 'pause_button': 'Canvas/Game/btn_pause',
                                                   'ad_entries': [{'role': 'double', 'button': 'Canvas/Result/btn_x2'}]})
        filled, notes, missing = g.fill_adapter(adapter, g.load(self.dir))
        self.assertEqual(filled['resume_play']['pause_button'], 'Canvas/Game/btn_pause')
        self.assertTrue(any('no "states"' in m or 'states' in m for m in missing), missing)
        self.assertEqual(g.fill_adapter(adapter, g.load(self.dir), 'legacy')[2], [])

    def test_runtime_double_role_by_record(self):
        """弹弹球 07:460: no coin, no items -> ECON-NOCUR shows no x2; the runtime check asked for role double anyway."""
        self.assertTrue(rr.ad_roles_problems(ADAPTER_NO_DOUBLE))                       # old way: refused
        self.write('docs/economy/economy_capabilities.json', eco(False, False))
        caps = rr.load_capabilities(str(self.dir))
        self.assertEqual(rr.ad_roles_problems(ADAPTER_NO_DOUBLE, caps), [])            # record: not applicable
        self.write('docs/economy/economy_capabilities.json', eco(False, True))         # has items: double is required
        self.assertTrue(rr.ad_roles_problems(ADAPTER_NO_DOUBLE, rr.load_capabilities(str(self.dir))))


if __name__ == '__main__':
    unittest.main(verbosity=2)
