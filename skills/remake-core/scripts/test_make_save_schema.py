#!/usr/bin/env python3
"""make_save_schema.py + SaveStore read-time check (R4E, 问题普查补查 第四节 2, T07:save_value_unvalidated).

A 蛋壳特工队-shaped project (hero / map / vip / skin config tables, the save keys that game wrote as 999999) is made in a
temp folder. The schema is generated from its tables; then Node loads a save holding 999999 for hero level, map, VIP
and skin id, and the game's own table lookups run on what SaveStore hands back:
  - old way (SaveStore 简化.11.13, tools/kit_versions/SaveStore/9fca45e2...txt, no schema): the values come back as they
    are, the hero lookup throws and VIP 999999 unlocks every VIP perk;
  - new SaveStore with the generated schema: each bad value falls back to its default with one [SaveStore] schema line,
    nothing throws; good values are kept; without a schema the new SaveStore behaves like the old one.
Also: the generator refuses a default that breaks its own rule, an unknown table, a missing default; --check reports a
stale schema after a config table changed and a save key the game writes but the spec does not declare.
Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_make_save_schema.py   (seconds; needs node for the load cases)"""
import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_save_schema as M  # noqa: E402

KIT = HERE.parent / 'assets' / 'platform-kit'
NEW_STORE = KIT / 'assets' / 'tiktok-platform' / 'SaveStore.js'
OLD_STORE = KIT / 'tools' / 'kit_versions' / 'SaveStore' / '9fca45e213abf061ffec93f6380e56c12977e26bdbe5a8a1b059807abc46428b.txt'
NODE = shutil.which('node')

SPEC = {
    'tables': {'heroes': {'file': 'assets/resources/config/hero.json', 'id': 'id'},
               'maps': {'file': 'assets/resources/config/map.csv'},
               'vip': {'file': 'assets/resources/config/vip.json', 'id': 'level'},
               'skins': {'file': 'assets/resources/config/skin.json'}},
    'keys': {'coins': {'type': 'int', 'min': 0, 'default': 0},
             'heroLevel': {'type': 'map', 'keyTable': 'heroes', 'of': {'type': 'int', 'min': 1, 'max': 'max:heroes.maxLevel'},
                           'default': {'h1': 1}},
             'mapId': {'type': 'id', 'table': 'maps', 'default': 1},
             'vip': {'type': 'int', 'min': 0, 'max': 'max:vip.level', 'default': 0},
             'skin': {'type': 'id', 'table': 'skins', 'default': 'cat'},
             'ownedSkins': {'type': 'list', 'of': {'type': 'id', 'table': 'skins'}, 'default': ['cat']},
             'settings.music': {'type': 'bool', 'default': True}}}

# the game's own reads (蛋壳特工队 shape): a table row by saved id, then a field of it
DRIVER = r"""
var path = require('path'), store = process.argv[2], schemaFile = process.argv[3], tables = JSON.parse(process.argv[4]);
var SaveStore = require(store);
var mem = {}, storage = {getItem: function (k) { return k in mem ? mem[k] : null; }, setItem: function (k, v) { mem[k] = String(v); }};
mem['egg:save'] = JSON.stringify({coins: 120, heroLevel: {h1: 999999, h2: 3, ghost: 2}, mapId: 999999, vip: 999999,
  skin: 999999, ownedSkins: ['cat', 999999, 'dog'], settings: {music: 'yes'}, platformClaims: {shortcut: false, profile: false}, meta: {}});
var logs = [], schema = schemaFile === '-' ? undefined : require(schemaFile);
var opts = {storage: storage, key: 'egg:save', login: false, log: function (l) { logs.push(l); }};
if (schema) opts.schema = schema;
var s = new SaveStore(schema ? schema.defaults : {coins: 0}, opts);
var r = s.load(), d = s.get(), out = {status: r.status, data: d, logs: logs, repaired: (r.repaired || []).length};
try {
  var heroRow = tables.heroes[d.heroLevel.h1 - 1];                 // hero.json row by level
  out.atk = heroRow.atk;                                           // throws on a missing row
  var mapRow = tables.maps.filter(function (m) { return String(m.id) === String(d.mapId); })[0];
  out.mapName = mapRow.id;                                         // throws on a missing map
  out.vipPerks = tables.vip.filter(function (v) { return v.level <= d.vip; }).length;
} catch (e) { out.error = String(e && e.message || e); }
console.log(JSON.stringify(out));
"""


class SaveSchema(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='r4e_schema_'))
        self.project = self.tmp / 'EggAgents'
        cfg = self.project / 'assets/resources/config'
        cfg.mkdir(parents=True)
        self.heroes = [{'id': 'h1', 'atk': 10, 'maxLevel': 30}, {'id': 'h2', 'atk': 14, 'maxLevel': 40}]
        (cfg / 'hero.json').write_text(json.dumps(self.heroes), encoding='utf-8')
        (cfg / 'map.csv').write_text('id,name\n1,Forest\n2,Desert\n3,Snow\n', encoding='utf-8')
        self.vip = [{'level': 1, 'perk': 'x2'}, {'level': 2, 'perk': 'skip'}, {'level': 3, 'perk': 'all'}]
        (cfg / 'vip.json').write_text(json.dumps({'version': 2, 'rows': self.vip}), encoding='utf-8')
        (cfg / 'skin.json').write_text(json.dumps({'cat': {'price': 0}, 'dog': {'price': 50}}), encoding='utf-8')
        self.write_spec(SPEC)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_spec(self, spec):
        p = self.project / M.SPEC
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(spec, indent=1), encoding='utf-8')

    def run_tool(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = M.main(['--project', str(self.project)] + list(args))
        return code, json.loads(buf.getvalue().strip().splitlines()[-1])

    def load(self, store, schema=True):
        tables = {'heroes': self.heroes, 'maps': [{'id': 1}, {'id': 2}, {'id': 3}], 'vip': self.vip}
        drv = self.tmp / 'drv.js'
        drv.write_text(DRIVER, encoding='utf-8')
        st = self.tmp / ('store_%s.js' % store.stem[:8])
        shutil.copy(store, st)
        (self.tmp / 'PlatformConfig.js').write_text("module.exports = {saveKey: function () { return 'k'; }};", encoding='utf-8')
        sch = str(self.project / M.OUT) if schema else '-'
        r = subprocess.run([NODE, str(drv), str(st), sch, json.dumps(tables)], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_generated_schema_takes_ranges_and_ids_from_tables(self):
        code, out = self.run_tool()
        self.assertEqual(code, 0, out)
        text = (self.project / M.OUT).read_text(encoding='utf-8')
        self.assertIn('GENERATED by remake-core/scripts/make_save_schema.py', text)
        schema = json.loads(text.split('var schema = ', 1)[1].rsplit(';\n  if (typeof module', 1)[0])
        self.assertEqual(schema['keys']['heroLevel']['of']['max'], 40)
        self.assertEqual(schema['keys']['vip']['max'], 3)
        self.assertEqual(schema['tables']['maps'], [1, 2, 3])
        self.assertEqual(sorted(schema['tables']['skins']), ['cat', 'dog'])
        self.assertEqual(schema['defaults'], {'coins': 0, 'heroLevel': {'h1': 1}, 'mapId': 1, 'vip': 0, 'skin': 'cat',
                                              'ownedSkins': ['cat'], 'settings': {'music': True}})
        self.assertEqual(self.run_tool('--check')[0], 0)

    @unittest.skipUnless(NODE, 'node not on this machine')
    def test_old_savestore_hands_back_999999_and_the_game_breaks(self):
        self.assertTrue(OLD_STORE.is_file(), OLD_STORE)
        self.run_tool()
        out = self.load(OLD_STORE)
        self.assertEqual(out['data']['heroLevel']['h1'], 999999)
        self.assertEqual(out['data']['mapId'], 999999)
        self.assertIn('error', out, 'the old way must break on the missing hero row')

    @unittest.skipUnless(NODE, 'node not on this machine')
    def test_new_savestore_falls_back_to_defaults_and_logs(self):
        self.run_tool()
        out = self.load(NEW_STORE)
        self.assertNotIn('error', out, out)
        d = out['data']
        self.assertEqual(d['heroLevel'], {'h1': 1, 'h2': 3}, 'h1 999999 back to its default 1, ghost hero dropped')
        self.assertEqual(out['atk'], 10)
        self.assertEqual((d['mapId'], d['vip'], d['skin']), (1, 0, 'cat'))
        self.assertEqual(d['ownedSkins'], ['cat', 'dog'])
        self.assertEqual(d['settings']['music'], True)
        self.assertEqual(d['coins'], 120, 'a good value is kept')
        self.assertEqual(out['vipPerks'], 0, 'VIP 999999 must not unlock every perk')
        self.assertEqual(out['status'], 'loaded')
        self.assertTrue(all(l.startswith('[SaveStore] schema: ') for l in out['logs']), out['logs'])
        self.assertEqual(len(out['logs']), out['repaired'])
        self.assertTrue(any('mapId = 999999 (because: not in table maps) -> 1' in l for l in out['logs']), out['logs'])

    @unittest.skipUnless(NODE, 'node not on this machine')
    def test_new_savestore_without_schema_behaves_like_the_old(self):
        new, old = self.load(NEW_STORE, schema=False), self.load(OLD_STORE, schema=False)
        self.assertEqual(new, old)
        self.assertEqual(new['logs'], [])

    def test_refuses_bad_spec_and_writes_nothing(self):
        bad = json.loads(json.dumps(SPEC))
        bad['keys']['mapId']['default'] = 9
        bad['keys']['vip'].pop('default')
        bad['keys']['skin']['table'] = 'nope'
        self.write_spec(bad)
        code, out = self.run_tool()
        self.assertEqual(code, 1, out)
        msg = out['problems'][0]
        for part in ('mapId: default 9 breaks its own rule', 'vip: no "default"', 'skin: unknown table nope'):
            self.assertIn(part, msg)
        self.assertFalse((self.project / M.OUT).exists())

    def test_check_finds_stale_schema_and_undeclared_keys(self):
        self.run_tool()
        (self.project / 'assets/resources/config/map.csv').write_text('id,name\n1,Forest\n2,Desert\n3,Snow\n4,Moon\n',
                                                                      encoding='utf-8')
        code, out = self.run_tool('--check')
        self.assertEqual(code, 1)
        self.assertIn('stale', out['problems'][0])
        self.run_tool()
        game = self.project / 'assets/scripts/Shop.js'
        game.parent.mkdir(parents=True)
        game.write_text("store.update(function (draft) { draft.coins -= 5; draft.petLevel = 2; draft['gems'] += 1; "
                        "draft.meta.x = 1; if (draft.vip == 3) {} });", encoding='utf-8')
        code, out = self.run_tool('--check')
        self.assertEqual(code, 0, out)
        self.assertEqual(out['undeclared_save_keys'], ['gems (assets/scripts/Shop.js)', 'petLevel (assets/scripts/Shop.js)'])
        self.assertEqual(self.run_tool('--check', '--strict')[0], 1)


# ---- R4J1 (广告skill ad-boost v1.2.17, 20 boards registering their save keys) ----
# Each sub-key a part's state object needs was written into the defaults, so every new save started with HALF an
# object. The three parts below are reduced to the decision their load() made on a new save before the 2026-11-05
# work-arounds (CheckinFlow validState / GiftCenter migrate / Energy normalize, 系统库 07 / 05 / 16 + B2-4..6 reports).
J1_SPEC = {'keys': {
    'coins': {'type': 'int', 'min': 0, 'default': 0},
    'checkin.state.claimed': {'type': 'int', 'min': 0, 'max': 6, 'default': 0, 'in_defaults': False},
    'checkin.state.cycle': {'type': 'int', 'min': 0, 'default': 0, 'in_defaults': False},
    'gifts.v': {'type': 'int', 'min': 1, 'default': 1, 'in_defaults': False},
    'energy.value': {'type': 'int', 'min': 0, 'max': 60, 'default': 0, 'in_defaults': False}}}
HALF_HOUR = 30 * 60 * 1000


def checkin_day1_today(save, today):
    """CheckinFlow.load before 11-05: no state = new (day 1 today); a state without v/created = bad save, repaired
    with last_day = today (claimed today, day 1 lost)."""
    box = save.get('checkin')
    state = box.get('state') if isinstance(box, dict) else None
    if state is None:
        return True
    valid = isinstance(state, dict) and state.get('v') == 1 and isinstance(state.get('created'), int)
    return valid and state.get('last_day') != today


def home_gift_ready(save, now):
    """GiftCenter.load before 11-05: gifts is an object = an old save, migrated; no home in it -> cool down 30 min."""
    g = save.get('gifts')
    if not isinstance(g, dict):
        return True                                   # new: the home gift can be opened at once
    home = g.get('home')
    next_at = home.get('nextClaimAt') if isinstance(home, dict) else now + HALF_HOUR
    return next_at <= now


def energy_at_start(save, full=5):
    """Energy.normalize: a whole value in range is kept as it is (0 = 0 energy), a missing one is filled up."""
    e = save.get('energy')
    v = e.get('value') if isinstance(e, dict) else None
    return v if isinstance(v, int) and 0 <= v <= full else full


class SubKeysAndNulls(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='r4j1_schema_'))
        self.project = self.tmp / 'Boards'
        self.project.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def gen(self, spec, *args):
        p = self.project / M.SPEC
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(spec, indent=1), encoding='utf-8')
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = M.main(['--project', str(self.project)] + list(args))
        return code, json.loads(buf.getvalue().strip().splitlines()[-1])

    def schema(self):
        text = (self.project / M.OUT).read_text(encoding='utf-8')
        return json.loads(text.split('var schema = ', 1)[1].rsplit(';\n  if (typeof module', 1)[0])

    def test_new_player_keeps_day1_reward_home_gift_and_full_energy(self):
        code, out = self.gen(J1_SPEC)
        self.assertEqual(code, 0, out)
        s = self.schema()
        new_save = s['defaults']
        lost = [why for ok, why in ((checkin_day1_today(new_save, today=20397), 'day-1 check-in reward lost'),
                                    (home_gift_ready(new_save, now=1793800000000), 'home gift cools down 30 min first'),
                                    (energy_at_start(new_save) == 5, 'new player starts with 0 energy')) if not ok]
        self.assertEqual(lost, [], 'new save %s' % json.dumps(new_save))
        self.assertEqual(new_save, {'coins': 0}, 'no half checkin / gifts / energy object in a new save')
        self.assertEqual(s['schema'], 2)
        for k in ('checkin.state.claimed', 'gifts.v', 'energy.value'):
            self.assertIs(s['keys'][k]['in_defaults'], False, k)   # still checked when a save has it

    def test_children_of_an_out_of_defaults_key_stay_out_and_may_skip_default(self):
        spec = {'keys': {'checkin.state': {'type': 'object', 'nullable': True, 'in_defaults': False},
                         'checkin.state.claimed': {'type': 'int', 'min': 0, 'max': 6},
                         'checkin.state.last_day': {'type': 'int', 'nullable': True},
                         'settings.music': {'type': 'bool', 'default': True}}}
        code, out = self.gen(spec)
        self.assertEqual(code, 0, out)
        s = self.schema()
        self.assertEqual(s['defaults'], {'settings': {'music': True}})
        self.assertIs(s['keys']['checkin.state.claimed']['in_defaults'], False)
        self.assertNotIn('default', s['keys']['checkin.state.claimed'])
        self.assertTrue(s['keys']['checkin.state.last_day']['nullable'])

    def test_nullable_int_default_null(self):
        spec = {'keys': {'wheel.pending': {'type': 'int', 'min': 0, 'nullable': True, 'default': None},
                         'revive.run': {'type': 'string', 'nullable': True, 'default': None}}}
        code, out = self.gen(spec)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.schema()['defaults'], {'wheel': {'pending': None}, 'revive': {'run': None}})
        self.assertIsNone(M.check_value({'type': 'int', 'nullable': True}, None, {}))
        self.assertIsNotNone(M.check_value({'type': 'int'}, None, {}))

    def test_refuses_bad_new_fields(self):
        bad = {'keys': {'a': {'type': 'int', 'default': None},                                   # null without nullable
                        'b': {'type': 'int', 'default': 0, 'nullable': 'yes'},
                        'c': {'type': 'list', 'default': [], 'of': {'type': 'int', 'in_defaults': False}},
                        'd': {'type': 'object', 'default': []},
                        'e': {'type': 'int'}}}                                                     # no default, in defaults
        code, out = self.gen(bad)
        self.assertEqual(code, 1, out)
        msg = out['problems'][0]
        for part in ('a: default null breaks its own rule', 'b: "nullable" must be true or false',
                     'c.of: "in_defaults" belongs on the save key', 'd: default [] breaks its own rule (not an object)',
                     'e: no "default"'):
            self.assertIn(part, msg)

    def test_old_spec_writes_schema_1_with_no_new_fields(self):
        code, out = self.gen({'keys': {'coins': {'type': 'int', 'min': 0, 'default': 0},
                                       'settings.music': {'type': 'bool', 'default': True}}})
        self.assertEqual(code, 0, out)
        text = (self.project / M.OUT).read_text(encoding='utf-8')
        self.assertIn('"schema": 1', text)
        self.assertNotIn('in_defaults', text)
        self.assertNotIn('nullable', text)

    def test_schema2_refused_next_to_a_savestore_that_cannot_read_it(self):
        store = self.project / M.STORE
        store.parent.mkdir(parents=True)
        shutil.copy(OLD_STORE, store)
        code, out = self.gen(J1_SPEC)
        self.assertEqual(code, 1, out)
        self.assertIn('older than save schema 2', out['problems'][0])
        self.assertFalse((self.project / M.OUT).exists())
        shutil.copy(NEW_STORE, store)
        self.assertEqual(self.gen(J1_SPEC)[0], 0)
        self.assertEqual(self.gen(J1_SPEC, '--check')[0], 0)
        shutil.copy(OLD_STORE, store)
        code, out = self.gen(J1_SPEC, '--check')
        self.assertEqual(code, 1)
        self.assertIn('older than save schema 2', out['problems'][0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
