#!/usr/bin/env python3
"""Generate the save schema SaveStore checks on every load, from the game's own config tables (R4E, 问题普查补查 第四节 2).

The AI runs this itself; the user never runs commands.

  python3 make_save_schema.py --project <Cocos project>            # write assets/tiktok-platform/SaveSchema.js
  python3 make_save_schema.py --project <Cocos project> --check    # write nothing; exit 1 when stale or invalid
  [--spec docs/save/save_keys.json] [--out assets/tiktok-platform/SaveSchema.js] [--strict]

Why: storage-guard.js only fixes types (false, '', a missing key). 蛋壳特工队 (T07:save_value_unvalidated, 5 records)
had role level, map, VIP and skin id written as 999999: the next load threw on a missing table row or unlocked
everything. SaveStore (kit, R4E) now checks every value it reads against this schema and puts a bad one back to its
default with one console.warn line. The schema is generated, never hand-written, so its ids and ranges always come
from the same config tables the game reads.

Every save key is declared ONCE, in docs/save/save_keys.json, with its default; add a save key there in the same step
as the code that writes it, then run this script. The generated file also carries the defaults, so the game builds its
SaveStore from it:  var S = require('SaveSchema'); new SaveStore(S.defaults, {schema: S})   (2.4; 3.x: import
SaveSchema.js as a plugin script, it sets globalThis.TikTokSaveSchema, which SaveStore picks up by itself).

docs/save/save_keys.json:
  {"tables": {"heroes": {"file": "assets/resources/config/hero.json", "id": "id"},
              "maps":   {"file": "assets/resources/config/map.csv"}},
   "keys": {"coins":     {"type": "int", "min": 0, "default": 0},
            "mapId":     {"type": "id", "table": "maps", "default": 1},
            "vip":       {"type": "int", "min": 0, "max": "max:vip.level", "default": 0},
            "level":     {"type": "int", "min": 1, "max": "count:levels", "default": 1},
            "skins":     {"type": "list", "of": {"type": "id", "table": "skins"}, "default": ["s1"]},
            "heroLevel": {"type": "map", "keyTable": "heroes", "of": {"type": "int", "min": 1, "max": "max:heroes.maxLevel"},
                          "default": {}},
            "settings.music": {"type": "bool", "default": true}}}
  types: int, number, bool, string, id (value must be an id of table `table`), list (each entry checked with `of`, bad
  entries dropped), map (keys must be ids of `keyTable`, values checked with `of`; a bad value of a known key goes back
  to that key in the map's default, else to `of`'s own "default"; unknown keys are dropped). min / max: a number, "count:T" (rows
  of T), "max:T.field" / "min:T.field" (largest / smallest number in that column). enum: allowed values.
  A dotted key ("settings.music") is a value inside an object; its default goes into that object.
R4J1 (广告skill ad-boost v1.2.17: a registered sub-key put HALF an object into every new save; CheckinFlow repaired
it as "claimed today" and the day-1 reward was lost, GiftCenter cooled the home gift 30 min, energy.value 0 started
new players with 0 energy):
  "in_defaults": false  the key is only CHECKED when a save has it, never written into new saves (default optional:
                        when given it is the repair value, else a bad value is removed and the part rebuilds it).
                        Every key below such a key inherits it ("checkin.state" false -> "checkin.state.claimed" too).
                        Use it for each key of a state object that a part (CheckinFlow, GiftCenter, Energy, a board's
                        norm()) creates itself. Never register such a sub-key without it.
  "nullable": true      null is a valid value too (checkin.state.last_day, a wheel's pending, a revive mark's run).
  type "object"         the value must be an object; its contents are left to the part that owns it (a board's
                        round, may be null with "nullable": true).
  A spec that uses one of these writes "schema": 2; make_save_schema.py refuses to write it when the project's
  SaveStore.js is older than schema 2 (it would wipe every null).
Tables: .json (list of rows, list of ids, {id: row}, or an object holding one such list) or .csv (header row). The
id column defaults to "id"; a {id: row} object uses its keys when the rows have no id column.
Refused (exit 1, nothing written): unknown type, missing default, a default that breaks its own rule, a table that
cannot be read or has no ids, a reference to an unknown table or column.
--inventory (R4N6, English games at the start inventory): list every storage key the ORIGINAL game reads or writes
(getItem / setItem / getStorageSync / setStorageSync with a literal key) into docs/save/save_keys.json
"inventory" {key: {how, where}} and add each missing key to "keys" as {type string, nullable, in_defaults false}
(raw storage holds text); keys already in the spec are kept as written. 弹球传奇 saved no progress at all and
合成进化恐龙 read old coins with `|| 100`: the list is what the save check and the AI's to-do start from.
--check also lists save keys the game's scripts write (draft.X = / draft['X'] =) that the spec does not declare
(warnings; --strict makes them fail). Prints one JSON line. Exit: 0 ok, 1 refused / stale, 2 bad input.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

TYPES = {'int', 'number', 'bool', 'string', 'id', 'list', 'map', 'object'}
SCHEMA2 = ('in_defaults', 'nullable')         # R4J1: rule fields that need SaveStore schema 2 (plus type object)
STORE = 'assets/tiktok-platform/SaveStore.js'
STORE_SCHEMA2 = 'SUPPORTED_SCHEMA = 2'       # marker line in the kit SaveStore that reads schema 2
SPEC = 'docs/save/save_keys.json'
OUT = 'assets/tiktok-platform/SaveSchema.js'
KIT_KEYS = {'meta', 'platformClaims', 'audio'}     # written by the kit itself (SaveStore, MissionFlow, AudioService)
REF = re.compile(r'^(count):([A-Za-z_][\w-]*)$|^(max|min):([A-Za-z_][\w-]*)\.([A-Za-z_][\w-]*)$')
DRAFT_WRITE = re.compile(r'\bdraft(?:\.([A-Za-z_$][\w$]*)|\[\s*[\'"]([^\'"]+)[\'"]\s*\])\s*(?:=(?!=)|\+=|-=|\+\+|--)')
HEAD = ('// GENERATED by remake-core/scripts/make_save_schema.py from %s and its config tables (spec sha256 %s).\n'
        '// Do not edit: add or change a save key in %s, then run make_save_schema.py again.\n'
        '// 2.4: var S = require(\'SaveSchema\'); new SaveStore(S.defaults, {schema: S}).  3.x: import as a plugin\n'
        '// script; it sets globalThis.TikTokSaveSchema, which SaveStore uses when no schema option is given.\n')


class SpecError(Exception):
    pass


def num(text):
    try:
        v = float(text)
    except (TypeError, ValueError):
        return None
    return int(v) if v.is_integer() else v


def rows_of(data):
    if isinstance(data, list):
        return data, None
    if isinstance(data, dict):
        lists = [v for v in data.values() if isinstance(v, list)]
        if len(lists) == 1 and not all(isinstance(v, dict) for v in data.values()):
            return lists[0], None
        if data and all(isinstance(v, dict) for v in data.values()):
            return list(data.values()), list(data.keys())
    raise SpecError('not a list of rows')


def read_table(project: Path, name: str, spec: dict) -> dict:
    rel = spec.get('file') if isinstance(spec, dict) else None
    if not rel:
        raise SpecError('table %s: no "file"' % name)
    path = project / rel
    if not path.is_file():
        raise SpecError('table %s: %s not found' % (name, rel))
    id_col = spec.get('id', 'id')
    try:
        if path.suffix.lower() == '.csv':
            with path.open(newline='', encoding='utf-8-sig') as f:
                rows = [dict(r) for r in csv.DictReader(f)]
            keys = None
        else:
            rows, keys = rows_of(json.loads(path.read_text(encoding='utf-8-sig')))
    except (OSError, ValueError, SpecError) as error:
        raise SpecError('table %s: %s cannot be read (%s)' % (name, rel, error))
    if rows and all(not isinstance(r, dict) for r in rows):
        ids = list(rows)
    elif rows and all(isinstance(r, dict) and id_col in r for r in rows):
        ids = [r[id_col] for r in rows]
    elif keys is not None:
        ids = keys
    else:
        raise SpecError('table %s: rows of %s have no "%s" column' % (name, rel, id_col))
    ids = [num(i) if isinstance(i, str) and num(i) is not None and str(num(i)) == i.strip() else i for i in ids]
    if not ids:
        raise SpecError('table %s: %s has no rows' % (name, rel))
    return {'file': rel, 'ids': ids, 'rows': [r for r in rows if isinstance(r, dict)],
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def resolve_bound(value, tables, where):
    if value is None or isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    m = REF.match(str(value))
    if not m:
        raise SpecError('%s: "%s" is not a number, count:T or max:T.field / min:T.field' % (where, value))
    if m.group(1):
        t = tables.get(m.group(2))
        if t is None:
            raise SpecError('%s: unknown table %s' % (where, m.group(2)))
        return len(t['ids'])
    t = tables.get(m.group(4))
    if t is None:
        raise SpecError('%s: unknown table %s' % (where, m.group(4)))
    vals = [num(r.get(m.group(5))) for r in t['rows'] if m.group(5) in r]
    vals = [v for v in vals if v is not None]
    if not vals:
        raise SpecError('%s: table %s has no numbers in column %s' % (where, m.group(4), m.group(5)))
    return max(vals) if m.group(3) == 'max' else min(vals)


def resolve_rule(rule, tables, where, top=True, outside=False):
    """outside: the key stays out of the defaults (its own or a parent's "in_defaults": false)."""
    if not isinstance(rule, dict):
        raise SpecError('%s: rule must be an object' % where)
    t = rule.get('type')
    if t not in TYPES:
        raise SpecError('%s: unknown type %r (use %s)' % (where, t, ', '.join(sorted(TYPES))))
    out = {'type': t}
    for k in SCHEMA2:
        if k in rule:
            if not isinstance(rule[k], bool):
                raise SpecError('%s: "%s" must be true or false' % (where, k))
            if k == 'in_defaults' and not top:
                raise SpecError('%s: "in_defaults" belongs on the save key, not inside "of"' % where)
            if rule[k] != (k == 'in_defaults'):   # only the non-default value is written (in_defaults false, nullable true)
                out[k] = rule[k]
    if top and outside:
        out['in_defaults'] = False
    for b in ('min', 'max'):
        if b in rule:
            out[b] = resolve_bound(rule[b], tables, '%s.%s' % (where, b))
    for k in ('enum', 'maxLength', 'maxItems'):
        if k in rule:
            out[k] = rule[k]
    for k in ('table', 'keyTable'):
        if k in rule:
            if rule[k] not in tables:
                raise SpecError('%s: unknown table %s' % (where, rule[k]))
            out[k] = rule[k]
    if t == 'id' and 'table' not in out:
        raise SpecError('%s: type id needs "table": <table name>' % where)
    if t in ('list', 'map') and 'of' in rule:
        out['of'] = resolve_rule(rule['of'], tables, where + '.of', top=False)
    if not top and 'default' in rule:     # a map value's own default (used for a known key without one)
        out['default'] = rule['default']
    if top:
        if 'default' in rule:
            out['default'] = rule['default']
        elif not outside:
            raise SpecError('%s: no "default" (every save key needs one, or "in_defaults": false when a part '
                            'creates it itself)' % where)
    return out


def check_value(rule, value, tables):
    """Python twin of SaveStore checkValue for the defaults: None when fine, else why."""
    t = rule['type']
    if value is None and rule.get('nullable'):
        return None
    if t == 'object':
        return None if isinstance(value, dict) else 'not an object'
    if 'enum' in rule and t not in ('list', 'map') and str(value) not in [str(e) for e in rule['enum']]:
        return 'not one of the enum'
    if t in ('int', 'number'):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return 'not a number'
        if t == 'int' and int(value) != value:
            return 'not a whole number'
        if 'min' in rule and value < rule['min']:
            return 'below %s' % rule['min']
        if 'max' in rule and value > rule['max']:
            return 'above %s' % rule['max']
    elif t == 'bool' and not isinstance(value, bool):
        return 'not true/false'
    elif t == 'string' and not isinstance(value, str):
        return 'not text'
    elif t == 'id' and str(value) not in {str(i) for i in tables[rule['table']]['ids']}:
        return 'not in table %s' % rule['table']
    elif t == 'list':
        if not isinstance(value, list):
            return 'not a list'
        for v in value:
            if 'of' in rule and check_value(rule['of'], v, tables):
                return 'entry %r %s' % (v, check_value(rule['of'], v, tables))
    elif t == 'map':
        if not isinstance(value, dict):
            return 'not a map'
        for k, v in value.items():
            if 'keyTable' in rule and str(k) not in {str(i) for i in tables[rule['keyTable']]['ids']}:
                return 'key %r not in table %s' % (k, rule['keyTable'])
            if 'of' in rule and check_value(rule['of'], v, tables):
                return 'value of %r %s' % (k, check_value(rule['of'], v, tables))
    return None


def needs_schema2(rule) -> bool:
    """R4J1: True when the rule uses something a SaveStore before schema 2 reads wrong (it would wipe a null)."""
    if not isinstance(rule, dict):
        return False
    return rule.get('type') == 'object' or any(k in rule for k in SCHEMA2) or needs_schema2(rule.get('of'))


def store_problem(project: Path, schema: dict):
    """R4J1: a schema-2 file next to a SaveStore.js that cannot read it. None when fine or no SaveStore.js there."""
    store = project / STORE
    if schema['schema'] < 2 or not store.is_file():
        return None
    if STORE_SCHEMA2 in store.read_text(encoding='utf-8', errors='replace'):
        return None
    return ('%s is older than save schema 2 ("in_defaults" / "nullable" / type object): put the current kit '
            'SaveStore.js in first (tiktok_finalize installs it), else it removes every null value on load' % STORE)


def build(project: Path, spec_rel: str) -> tuple[str, dict]:
    spec_path = project / spec_rel
    if not spec_path.is_file():
        raise SpecError('%s not found: declare every save key there (see this script\'s help)' % spec_rel)
    raw = spec_path.read_bytes()
    try:
        spec = json.loads(raw.decode('utf-8-sig'))
    except ValueError as error:
        raise SpecError('%s is not JSON: %s' % (spec_rel, error))
    tables = {name: read_table(project, name, t) for name, t in sorted((spec.get('tables') or {}).items())}
    keys_in = spec.get('keys') or {}
    if not isinstance(keys_in, dict) or not keys_in:
        raise SpecError('%s: no "keys"' % spec_rel)
    keys, defaults, problems = {}, {}, []
    # R4J1: a key whose own rule or a parent key's rule says "in_defaults": false stays out of the defaults
    outside_roots = [p for p in keys_in if isinstance(keys_in[p], dict) and keys_in[p].get('in_defaults') is False]
    for path in sorted(keys_in):
        outside = any(path == r or path.startswith(r + '.') for r in outside_roots)
        try:
            rule = resolve_rule(keys_in[path], tables, path, outside=outside)
        except SpecError as error:
            problems.append(str(error))
            continue
        why = check_value(rule, rule['default'], tables) if 'default' in rule else None
        if why:
            problems.append('%s: default %s breaks its own rule (%s)' % (path, json.dumps(rule['default']), why))
            continue
        keys[path] = rule
        if outside:
            continue
        node, parts = defaults, path.split('.')
        for p in parts[:-1]:
            node = node.setdefault(p, {})
            if not isinstance(node, dict):
                problems.append('%s: parent %s is not an object' % (path, p))
                break
        else:
            node[parts[-1]] = rule['default']
    if problems:
        raise SpecError('; '.join(problems))
    used = sorted({n for k in keys.values() for n in (k.get('table'), k.get('keyTable'), (k.get('of') or {}).get('table'),
                                                      (k.get('of') or {}).get('keyTable')) if n})
    schema = {'schema': 2 if any(needs_schema2(k) for k in keys.values()) else 1, 'generated_by': 'make_save_schema.py', 'spec': spec_rel,
              'spec_sha256': hashlib.sha256(raw).hexdigest(),
              'table_files': {n: {'file': tables[n]['file'], 'sha256': tables[n]['sha256']} for n in sorted(tables)},
              'defaults': defaults, 'keys': keys, 'tables': {n: tables[n]['ids'] for n in used}}
    body = json.dumps(schema, ensure_ascii=False, indent=1, sort_keys=True)
    text = (HEAD % (spec_rel, schema['spec_sha256'][:12], spec_rel) +
            '(function (root) {\n  var schema = ' + body.replace('\n', '\n  ') + ';\n'
            "  if (typeof module === 'object' && module && module.exports) module.exports = schema;\n"
            '  if (root) root.TikTokSaveSchema = schema;\n'
            "})(typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : this));\n")
    return text, schema


def undeclared_keys(project: Path, schema: dict) -> list[str]:
    top = {k.split('.')[0] for k in schema['keys']} | KIT_KEYS
    found = set()
    for folder in ('assets', 'extensions'):
        base = project / folder
        if not base.is_dir():
            continue
        for f in base.rglob('*'):
            if f.suffix not in ('.js', '.ts') or 'tiktok-platform' in f.parts or f.name == Path(OUT).name:
                continue
            try:
                text = f.read_text(encoding='utf-8', errors='replace')
            except OSError:
                continue
            for m in DRAFT_WRITE.finditer(text):
                key = m.group(1) or m.group(2)
                if key and key not in top:
                    found.add('%s (%s)' % (key, f.relative_to(project).as_posix()))
    return sorted(found)


STORAGE_CALL = re.compile(r'\b(getItem|setItem|removeItem|getStorageSync|setStorageSync|removeStorageSync|getStorage|setStorage)'
                          r'\s*\(\s*(?:([\'"])([^\'"\n]{1,80})\2|([^,)\n]{1,60}))')
STORAGE_READS = {'getItem', 'getStorageSync', 'getStorage'}


def inventory(project: Path, spec_rel: str = SPEC) -> dict:
    """R4N6: every storage key the game's own scripts use -> the spec (written), with the inventory section."""
    found, dynamic = {}, []
    base = project / 'assets'
    for f in sorted(base.rglob('*')) if base.is_dir() else []:
        rel = f.relative_to(project).as_posix()
        if f.suffix not in ('.js', '.ts') or not f.is_file() or 'tiktok-platform' in f.parts or f.name == Path(OUT).name \
                or {'library', 'temp', 'build'} & set(f.relative_to(project).parts) or f.stat().st_size > 2 * 1024 * 1024:
            continue
        text = f.read_text(encoding='utf-8', errors='replace')
        for m in STORAGE_CALL.finditer(text):
            line = text.count('\n', 0, m.start()) + 1
            how = 'read' if m.group(1) in STORAGE_READS else ('remove' if m.group(1).startswith('remove') else 'write')
            if m.group(3) is None:
                dynamic.append('%s:%d %s(%s)' % (rel, line, m.group(1), (m.group(4) or '').strip()))
                continue
            item = found.setdefault(m.group(3), {'how': [], 'where': []})
            if how not in item['how']:
                item['how'].append(how)
            if len(item['where']) < 8:
                item['where'].append('%s:%d' % (rel, line))
    path = project / spec_rel
    try:
        spec = json.loads(path.read_text(encoding='utf-8-sig')) if path.is_file() else {}
    except ValueError as error:
        raise SpecError('%s is not JSON: %s' % (spec_rel, error))
    keys = spec.setdefault('keys', {})
    added = []
    for key in sorted(found):
        if key not in keys:
            keys[key] = {'type': 'string', 'nullable': True, 'in_defaults': False,
                         'note': 'raw storage key of the original game (inventory); set its real type and default'}
            added.append(key)
    spec['inventory'] = {k: dict(v, how=sorted(v['how'])) for k, v in sorted(found.items())}
    spec['inventory_dynamic_keys'] = dynamic[:50]
    spec['inventory_note'] = ('make_save_schema.py --inventory: keys read but never written (%s) and progress the game '
                              'never saves (level, coins, owned skins) go on the AI\'s to-do list'
                              % (', '.join(k for k, v in sorted(found.items()) if v['how'] == ['read']) or 'none'))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(spec, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return {'status': 'inventory', 'spec': spec_rel, 'keys': len(found), 'added': added, 'dynamic': len(dynamic)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--spec', default=SPEC)
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--check', action='store_true', help='write nothing; exit 1 when the schema file is stale or invalid')
    ap.add_argument('--strict', action='store_true', help='with --check: save keys missing from the spec also fail')
    ap.add_argument('--inventory', action='store_true', help='R4N6: list the original game\'s storage keys into the spec')
    a = ap.parse_args(argv)
    project = a.project.expanduser()
    if not project.is_dir():
        print(json.dumps({'status': 'error', 'error': 'no project folder %s' % project}, ensure_ascii=False))
        return 2
    if a.inventory:                       # R4N6: English start inventory, then build as usual
        try:
            print(json.dumps(inventory(project, a.spec), ensure_ascii=False))
        except SpecError as error:
            print(json.dumps({'status': 'refused', 'problems': [str(error)], 'written': []}, ensure_ascii=False))
            return 1
        return 0
    try:
        text, schema = build(project, a.spec)
    except SpecError as error:
        print(json.dumps({'status': 'refused', 'problems': [str(error)], 'written': []}, ensure_ascii=False))
        return 1
    out = project / a.out
    info = {'keys': len(schema['keys']), 'tables': sorted(schema['table_files']), 'out': a.out}
    old_store = store_problem(project, schema)
    if old_store and not a.check:
        print(json.dumps({'status': 'refused', 'problems': [old_store], 'written': []}, ensure_ascii=False))
        return 1
    if a.check:
        problems = [old_store] if old_store else []
        if not out.is_file():
            problems.append('%s missing: run make_save_schema.py' % a.out)
        elif out.read_text(encoding='utf-8') != text:
            problems.append('%s is stale (spec or a config table changed): run make_save_schema.py' % a.out)
        missing = undeclared_keys(project, schema)
        if a.strict and missing:
            problems.append('save keys written by the game but not in %s: %s' % (a.spec, ', '.join(missing[:10])))
        print(json.dumps(dict(info, status='ok' if not problems else 'stale', problems=problems,
                              undeclared_save_keys=missing), ensure_ascii=False))
        return 0 if not problems else 1
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + '.tmp')
    tmp.write_text(text, encoding='utf-8')
    tmp.replace(out)
    print(json.dumps(dict(info, status='written'), ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
