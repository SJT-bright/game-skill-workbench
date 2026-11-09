#!/usr/bin/env python3
"""Page registry: the check inputs are made from one list while the game is made (总表 P19, 2026-11-04 问题普查:
check_inputs_missing 20 条, checker_input_rejected 29 条, and the empty lists that made a case skip: 割草 ad-entry list
empty, 美人鱼 pause key never written).

Before this, docs/art/screens.json, docs/logic/flows.json, the ad-regression adapter (qa/ad-regression.json) and
resume_play.pause_button were typed in by the AI just before a check, each on its own. One was forgotten and the check
refused, or the list was empty and the case was skipped.

Now there is one source, docs/logic/pages.json (schema pages.v1, see remake-core/references/page-registry.md):
every page and popup with its buttons, its close key, the level's pause key and the rewarded-ad entries. Write it while
the pages are made (GameUIKit popup()/open() calls PageRegistry.record in the dev build, A2 批; ui_dump.js returns
what was recorded) and generate the rest with this script. Never edit the generated files by hand.

  python3 page_registry.py make  --project <game> [--adapter-in qa/ad-regression.json] [--policy new|legacy]
      writes docs/art/screens.json, docs/logic/flows.json (page_flows; F01-F20 template if the file is new),
      docs/game_capabilities.json (pause_button, ad_entries, no_ad_roles; M 批 game_capabilities.py) and
      qa/ad-regression.json (ad_entries, resume_play.pause_button, ad_outcome.none from the record; the hand-written
      page JavaScript request / state / ready / exit is kept, or taken from pages.json "adapter_js").
      Exit 0 written, 1 pages.json invalid, 2 not_run (pages.json missing or empty: nothing was generated).
  python3 page_registry.py merge-dumps --project <game> --dumps docs/test
      marks the pages the dev build really opened (ui_dump "pages", PageRegistry.record) seen_at_runtime and lists
      pages opened at runtime that pages.json does not have (they must be added, then make again).
  python3 page_registry.py check --project <game>
      exit 0 when every generated file still equals what pages.json makes; 1 when one was edited by hand or is stale.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GUARD = HERE.parents[1] / 'cocos-game-check' / 'package-check' / 'scripts'
for _p in (str(HERE), str(GUARD)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import check_guard  # noqa: E402 - J1 批: one not_run shape for every check input
import game_capabilities  # noqa: E402 - M 批: pause_button / ad_entries record and fill_adapter

SCHEMA = 'pages.v1'
PAGES = Path('docs') / 'logic' / 'pages.json'
SCREENS = Path('docs') / 'art' / 'screens.json'
FLOWS = Path('docs') / 'logic' / 'flows.json'
CAPS = game_capabilities.RECORD
ADBOOST_PREFIX = 'ad-boost:'   # R4J2: page ids AdBoostKit records through UI.recordPage
ADAPTER = Path('qa') / 'ad-regression.json'
STAMP = Path('docs') / 'logic' / 'pages.generated.json'
KINDS = ('home', 'gameplay', 'popup', 'page', 'loading')
# R4L4 (lead, 11-05): the one allowed prefix with a colon is ADBOOST_PREFIX, so the ad-boost board pages AdBoostKit
# records as "ad-boost:<board>" can be listed in pages.json; any other colon is still refused (flow ids use ':').
ID = re.compile(r'^(?:ad-boost:)?[A-Za-z][A-Za-z0-9_.-]{0,60}$')
PAGE_KEYS = {'id', 'name', 'kind', 'purpose', 'node', 'prefab', 'buttons', 'close', 'pause', 'ad_entries', 'why',
             'seen_at_runtime', 'note'}
TOP_KEYS = {'schema', 'game', 'required_viewports', 'pages', 'no_ad_roles', 'adapter_js', 'note'}
ADAPTER_JS = {'request', 'request_role', 'state', 'ready', 'exit', 'exit_label', 'home', 'no_music', 'boot_timeout_s', 'home_scene',
              'after_home_js', 'enter_level'}
DEFAULT_VIEWPORTS = [{'name': 'iphone14', 'width': 390, 'height': 844}, {'name': 'iphone-se', 'width': 375, 'height': 667}]


def _none(v):
    return isinstance(v, dict) and set(v) == {'none'} and isinstance(v['none'], str) and bool(v['none'].strip())


def validate(doc):
    """Problems with pages.json ([] = valid). Every rule here is what a downstream check would otherwise refuse."""
    if not isinstance(doc, dict):
        return ['pages.json must be a JSON object']
    errs = [] if doc.get('schema') == SCHEMA else ['schema must be %s' % SCHEMA]
    errs += ['unknown top-level key %s' % k for k in sorted(set(doc) - TOP_KEYS)]
    pages = doc.get('pages')
    if not isinstance(pages, list) or not pages:
        return errs + ['pages must be a nonempty list']
    ids = set()
    for i, p in enumerate(pages):
        if not isinstance(p, dict):
            errs.append('pages[%d] must be an object' % i)
            continue
        where = 'pages[%d] %s' % (i, p.get('id', '?'))
        errs += ['%s: unknown key %s' % (where, k) for k in sorted(set(p) - PAGE_KEYS)]
        if not (isinstance(p.get('id'), str) and ID.match(p['id'])):
            errs.append('%s: id must be a short word (letters, digits, _ . -; ad-boost board pages: ad-boost:<board>)'
                        % where)
        elif p['id'] in ids:
            errs.append('%s: id used twice' % where)
        else:
            ids.add(p['id'])
        if not (isinstance(p.get('name'), str) and p['name'].strip()):
            errs.append('%s: name missing' % where)
        if p.get('kind') not in KINDS:
            errs.append('%s: kind must be one of %s' % (where, ', '.join(KINDS)))
        if p.get('kind') == 'popup' and not ((isinstance(p.get('close'), str) and p['close'].strip()) or _none(p.get('close'))):
            errs.append('%s: a popup needs its close key (node path) or {"none": "why"}' % where)
        if p.get('kind') == 'gameplay' and not ((isinstance(p.get('pause'), str) and p['pause'].strip()) or _none(p.get('pause'))):
            errs.append('%s: the level page needs its pause / settings key (node path) or {"none": "why"} '
                        '(关卡内暂停或设置键, 英化固定入口第 9 项)' % where)
        for j, b in enumerate(p.get('buttons') or []):
            if not (isinstance(b, dict) and isinstance(b.get('node'), str) and b['node'].strip()):
                errs.append('%s: buttons[%d] needs "node" (node path)' % (where, j))
        if 'ad_entries' in p and not isinstance(p['ad_entries'], list):
            errs.append('%s: ad_entries must be a list' % where)
    for p in pages:
        for b in (p.get('buttons') or []) if isinstance(p, dict) else []:
            if isinstance(b, dict) and b.get('to') and b['to'] not in ids:
                errs.append('page %s button %s: "to" names no page (%s)' % (p.get('id'), b.get('node'), b['to']))
    if not any(isinstance(p, dict) and p.get('kind') == 'home' for p in pages):
        errs.append('one page must have kind "home"')
    vps = doc.get('required_viewports', DEFAULT_VIEWPORTS)
    if not isinstance(vps, list) or len({(v.get('width'), v.get('height')) for v in vps if isinstance(v, dict)}) < 2:
        errs.append('required_viewports needs two different phone sizes')
    js = doc.get('adapter_js', {})
    if not isinstance(js, dict) or set(js) - ADAPTER_JS:
        errs.append('adapter_js may hold only %s' % ', '.join(sorted(ADAPTER_JS)))
    entries = all_ad_entries(doc)
    seen = set()
    for e in entries:
        if not (isinstance(e, dict) and game_capabilities.ROLE.match(str(e.get('role', ''))) and
                isinstance(e.get('button'), str) and e['button'].strip()):
            errs.append('ad entry %r needs role (double, revive, home_gift ...) and button (node path)' % (e,))
            continue
        eid = e.get('id') or e['role']
        if eid in seen:
            errs.append('ad entry id %s used twice (give each one an "id")' % eid)
        seen.add(eid)
    return errs


def all_ad_entries(doc):
    out = []
    for p in doc.get('pages') or []:
        if isinstance(p, dict):
            out.extend(e for e in p.get('ad_entries') or [])
    return out


def _pause(doc):
    for p in doc['pages']:
        if p.get('kind') == 'gameplay':
            return p.get('pause')
    return None


def screens_doc(doc, sha):
    rows = []
    for p in doc['pages']:
        row = {'id': p['id'], 'name': p['name'], 'kind': p['kind'], 'purpose': p.get('purpose') or p['kind']}
        for k in ('node', 'prefab', 'why', 'close'):
            if k in p:
                row[k] = p[k]
        rows.append(row)
    return {'generated_by': 'page_registry.py from docs/logic/pages.json', 'pages_sha256': sha,
            'runtime_verified': all(p.get('seen_at_runtime') is True for p in doc['pages']),
            'required_viewports': doc.get('required_viewports', DEFAULT_VIEWPORTS), 'screens': rows}


def page_flows(doc):
    """One flow per button that opens another page, and one per popup close key: tester statuses start untested."""
    out = []
    names = {p['id']: p['name'] for p in doc['pages']}
    for p in doc['pages']:
        for b in p.get('buttons') or []:
            if b.get('to'):
                out.append({'id': 'P:%s>%s:%s' % (p['id'], b['to'], b.get('id') or b['node'].split('/')[-1]),
                            'title': '%s 点 %s 打开 %s' % (p['name'], b.get('label') or b['node'], names[b['to']]),
                            'from': p['id'], 'to': b['to'], 'button': b['node']})
        if isinstance(p.get('close'), str):
            out.append({'id': 'P:%s:close' % p['id'], 'title': '%s 的关闭键回到上一页' % p['name'], 'from': p['id'],
                        'to': 'back', 'button': p['close']})
    return out


def flows_doc(project, doc):
    path = project / FLOWS
    try:
        flows = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        flows = None
    if not isinstance(flows, dict):
        try:
            import logic_check
            flows = {'schema': 'logic_flows.v1', 'flows': [
                {'id': i, 'title': t, 'status': 'untested', 'evidence': '', 'note': ''} for i, t, _ in logic_check.FLOWS]}
        except Exception:  # noqa: BLE001 - logic_check --init still writes the F01-F20 rows later
            flows = {'schema': 'logic_flows.v1', 'flows': []}
    old = {f.get('id'): f for f in flows.get('page_flows') or [] if isinstance(f, dict)}
    rows = []
    for f in page_flows(doc):
        prev = old.get(f['id'], {})
        rows.append(dict(f, status=prev.get('status', 'untested'), evidence=prev.get('evidence', ''),
                         note=prev.get('note', '')))
    flows['page_flows'] = rows
    return flows


def caps_doc(doc):
    pause = _pause(doc)
    entries = all_ad_entries(doc)
    ad = [dict({'id': e.get('id') or e['role']}, **{k: e[k] for k in ('role', 'button', 'states') if k in e})
          for e in entries]
    return game_capabilities.make(
        pause_button=pause, ad_entries=ad or {'none': 'pages.json lists no rewarded-ad entry'},
        no_ad_roles=doc.get('no_ad_roles') or None, evidence={'pages': PAGES.as_posix()},
        written_by='page_registry.py make')


def body_drift(base, adapter_js):
    """11.17 R4Q7: adapter_js keys whose function body in the existing adapter differs from pages.json (sorted)."""
    return sorted(k for k, v in (adapter_js or {}).items() if k in base and base[k] != v)


# 11.17 R4Q7 (合成进化恐龙): GameUIKit button() / wrapExisting() listen to TOUCH_END and take the old cc.Button click
# events off, so a hand-written node.emit('click') in the adapter page JavaScript reaches no handler.
EMIT_CLICK = re.compile(r"""\.emit\(\s*(['"])click\1""")
UIKIT_CLICK_FIX = ("GameUIKit 按钮只听 TOUCH_END（button()/wrapExisting() 会拿掉旧的 click 事件），emit('click') 点不到："
                   "用登记时保存的 handle.tap()，或 node.emit(cc.Node.EventType.TOUCH_END, 事件)")


def uses_gameuikit(project):
    assets = Path(project) / 'assets'
    if not assets.is_dir():
        return False
    return any(assets.rglob('GameUIKit.js')) or any(assets.rglob('GameUIKit.ts'))


def emit_click_keys(adapter):
    """Adapter page-JavaScript fields (ADAPTER_JS names) that still click with emit('click')."""
    return sorted(k for k in ADAPTER_JS if isinstance(adapter.get(k), str) and EMIT_CLICK.search(adapter[k])
                  and not (k == 'request' and adapter.get('request_role') == 'revive'))


def adapter_doc(project, doc, caps_record, adapter_in=None, policy='new', force_body=False):
    path = Path(adapter_in) if adapter_in else project / ADAPTER
    try:
        base = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        base = {}
    if not isinstance(base, dict):
        base = {}
    adapter_js = doc.get('adapter_js') or {}
    drift = body_drift(base, adapter_js)
    for k, v in adapter_js.items():
        if force_body:
            base[k] = v          # R4Q7 --force-body: pages.json adapter_js wins over the old hand-written body
        else:
            base.setdefault(k, v)
    # page-made fields are always the registry's (a hand edit is overwritten, `check` reports it)
    base.pop('ad_entries', None)
    rp = base.get('resume_play')
    if isinstance(rp, dict) and 'n/a' not in rp:
        rp.pop('pause_button', None)
    elif not isinstance(rp, dict):
        base['resume_play'] = {}
    caps = game_capabilities.load(record=None) if caps_record is None else _caps_from(caps_record)
    out, notes, missing = game_capabilities.fill_adapter(base, caps, policy)
    return out, notes, missing, ([] if force_body else drift)


def _caps_from(record):
    caps = {k: None for k in game_capabilities.ECONOMY_KEYS + ('pause_button', 'ad_entries', 'no_ad_roles')}
    caps.update({'source': {}, 'problems': [], 'project': None})
    for k in ('pause_button', 'ad_entries', 'no_ad_roles'):
        if k in record:
            caps[k] = record[k]
            caps['source'][k] = CAPS.as_posix()
    return caps


def _dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2) + '\n'


def build(project, adapter_in=None, policy='new', force_body=False):
    """-> (outputs {relative path: text}, report). report.status is passed / failed / not_run (check-status.json)."""
    project = Path(project)
    try:
        raw = (project / PAGES).read_text(encoding='utf-8-sig')
        doc = json.loads(raw)
    except FileNotFoundError:
        doc, raw = None, ''
    except (OSError, ValueError) as exc:
        return {}, {'tool': 'page_registry', 'status': 'failed', 'passed': False,
                    'problems': ['%s unreadable: %s' % (PAGES.as_posix(), exc)]}
    gap = check_guard.inputs_not_run('page_registry', {PAGES.as_posix(): (doc or {}).get('pages') if isinstance(doc, dict) else doc},
                                     fix='写 docs/logic/pages.json（每个页面、按钮、关闭键、关内暂停键、广告入口），'
                                         '见 remake-core/references/page-registry.md')
    if gap:
        return {}, gap
    errs = validate(doc)
    if errs:
        return {}, {'tool': 'page_registry', 'status': 'failed', 'passed': False, 'problems': errs}
    sha = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    caps, merged = game_capabilities.merge_into(project, caps_doc(doc))   # R4H: keep what `write` wrote, say what changed
    adapter, notes, missing, drift = adapter_doc(project, doc, caps, adapter_in, policy, force_body)
    click_keys = emit_click_keys(adapter) if uses_gameuikit(project) else []
    if click_keys and policy == 'new':
        return {}, {'tool': 'page_registry', 'status': 'failed', 'passed': False,
                    'problems': ['%s "%s": %s' % (ADAPTER.as_posix(), k, UIKIT_CLICK_FIX) for k in click_keys]}
    outputs = {SCREENS.as_posix(): _dump(screens_doc(doc, sha)), FLOWS.as_posix(): _dump(flows_doc(project, doc)),
               CAPS.as_posix(): _dump(caps), ADAPTER.as_posix(): _dump(adapter)}
    stamp = {'schema': 'pages.generated.v1', 'pages_sha256': sha,
             'outputs': {k: hashlib.sha256(v.encode('utf-8')).hexdigest() for k, v in outputs.items()}}
    outputs[STAMP.as_posix()] = _dump(stamp)
    report = {'tool': 'page_registry', 'status': 'passed', 'passed': True, 'checked': len(doc['pages']),
              'written': sorted(outputs), 'notes': notes, 'adapter_missing': missing}
    if missing:
        report['warnings'] = ['adapter still lacks: ' + m for m in missing]
    if drift:   # R4Q7: the old adapter's hand-written body was kept although pages.json adapter_js says otherwise
        report['adapter_body_drift'] = drift
        report.setdefault('warnings', []).extend(
            '%s "%s" 和 pages.json adapter_js 不一样，保留了旧的手写函数体：要用清单里的就加 --force-body 再 make'
            % (ADAPTER.as_posix(), k) for k in drift)
    if click_keys:   # legacy policy: warn only
        report.setdefault('warnings', []).extend('%s "%s": %s' % (ADAPTER.as_posix(), k, UIKIT_CLICK_FIX)
                                                 for k in click_keys)
    if merged:
        report['capabilities_merged'] = merged
        report.setdefault('warnings', []).extend('%s 合并: %s' % (CAPS.as_posix(), m) for m in merged)
    return outputs, report


def write(project, outputs):
    for rel, text in outputs.items():
        path = Path(project) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_text(encoding='utf-8') != text:
            path.write_text(text, encoding='utf-8')


def check(project):
    """Generated files equal what pages.json makes now (no hand edit, not stale)."""
    project = Path(project)
    try:
        stamp = json.loads((project / STAMP).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return check_guard.not_run('page_registry check', '%s 不存在：生成文件不是 page_registry.py 写的，先运行 make'
                                   % STAMP.as_posix(), [STAMP.as_posix()])
    problems = []
    raw = (project / PAGES).read_text(encoding='utf-8-sig') if (project / PAGES).is_file() else ''
    if hashlib.sha256(raw.encode('utf-8')).hexdigest() != stamp.get('pages_sha256'):
        problems.append('pages.json changed after the last make: run make again')
    for rel, digest in (stamp.get('outputs') or {}).items():
        path = project / rel
        now = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if now != digest:
            problems.append('%s was edited by hand or removed: change pages.json and run make' % rel)
    return {'tool': 'page_registry check', 'status': 'failed' if problems else 'passed', 'passed': not problems,
            'checked': len(stamp.get('outputs') or {}), 'problems': problems}


def merge_dumps(project, dumps):
    """Set seen_at_runtime from ui_dump files whose "pages" list (PageRegistry.record) names a page."""
    project = Path(project)
    doc = json.loads((project / PAGES).read_text(encoding='utf-8-sig'))
    seen, extra = set(), set()
    known = {p.get('id') for p in doc.get('pages') or [] if isinstance(p, dict)}
    for f in sorted(Path(dumps).rglob('*ui-dump-*.json')) if Path(dumps).is_dir() else []:
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        for rec in data.get('pages') or [] if isinstance(data, dict) else []:
            pid = rec.get('id') if isinstance(rec, dict) else None
            if pid in known:
                seen.add(pid)
            elif pid:
                extra.add(pid)
    for p in doc['pages']:
        if p.get('id') in seen:
            p['seen_at_runtime'] = True
    (project / PAGES).write_text(_dump(doc), encoding='utf-8')
    # R4J2 (lead decision 11-05): ad-boost board popups (AdBoostKit -> UI.recordPage, id "ad-boost:<board>") are not
    # in pages.json until record_ad_entries.py adds them; this version warns for those, any other unlisted id fails
    board = sorted(x for x in extra if str(x).startswith(ADBOOST_PREFIX))
    other = sorted(x for x in extra if not str(x).startswith(ADBOOST_PREFIX))
    report = {'tool': 'page_registry merge-dumps', 'seen': sorted(seen),
              'never_opened': sorted(known - seen), 'not_in_pages_json': sorted(extra),
              'status': 'failed' if other else 'passed', 'passed': not other,
              'problems': ['opened at runtime but not in pages.json: %s (add it, then make)' % x for x in other]}
    if board:
        report['warnings'] = ['ad-boost 板块页 %s 运行时打开过，但 pages.json 里没有：跑 ad-boost 的 record_ad_entries.py '
                              '把板块页加进 pages.json，再 make' % x for x in board]
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    m = sub.add_parser('make')
    m.add_argument('--project', type=Path, required=True)
    m.add_argument('--adapter-in', type=Path)
    m.add_argument('--policy', choices=['new', 'legacy'], default='new')
    m.add_argument('--force-body', action='store_true',
                   help='R4Q7: take request/state/ready/exit... from pages.json adapter_js even when the old adapter '
                        'already has a hand-written body (default keeps it and warns adapter_body_drift)')
    c = sub.add_parser('check')
    c.add_argument('--project', type=Path, required=True)
    d = sub.add_parser('merge-dumps')
    d.add_argument('--project', type=Path, required=True)
    d.add_argument('--dumps', type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == 'make':
        outputs, report = build(a.project, a.adapter_in, a.policy, a.force_body)
        if report.get('passed'):
            write(a.project, outputs)
    elif a.cmd == 'check':
        report = check(a.project)
    else:
        report = merge_dumps(a.project, a.dumps)
    print(json.dumps(report, ensure_ascii=False))
    return {'passed': 0, 'failed': 1, 'not_run': check_guard.NOT_RUN_EXIT}.get(report.get('status'), 1)


if __name__ == '__main__':
    raise SystemExit(main())
