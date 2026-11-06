#!/usr/bin/env python3
"""English stage-1 inventory of the original game's own reward, spend and item writes (生成时预防 R4Q4, 补查3 第 4 组).

奔跑吧巨人 changed shared memory first and saved afterwards (upgrade, skin, shoe rewards), saved its chest x2 at the end of
the animation, gave keys with no rollback on a failed save, and showed ceil(base*2) while paying 2*ceil(base);
合成进化恐龙 paid the base coins at the result although the battle had already put them in the wallet, and charged a
paid summon twice. All of it is the original game's own wallet code, which the English stage keeps. This scan lists every
place that changes the wallet or an item so it is switched to the kit from the first day:
  reward_add     `<coins / gems / keys / items ...> +=` (or `= x + ...`) on a game or save field
  reward_spend   `-=` (or `= x - ...`) on the same kind of field
  reward_save    a save call (save / saveData / setItem / setStorageSync / setGlobalData ...) in a file with one of the
                 two above
Rows found within 15 lines after a rewarded-ad call carry "in_ad_callback": true.
Every row says what to change: rewards through SaveStore grant({id, add, apply}), spends through ShopTx (2.4/3.x
parts/ShopTx.js; English sync does not install it, copy it like the README says) or grant with a negative add. The order
is fixed: claim id (receipt) -> save and read back -> refresh the UI -> play the animation; an x2 computes ONE base
integer and both the label and the grant read 2 * that integer.
Read only: nothing in the project is written. Code cannot tell a pure UI counter from a wallet field; the list is a
to-do list, not a block.

  python3 reward_inventory.py --project GAME        prints {"reward_todo": [...], "reward_summary": {...}}
`tiktok_finalize.py inventory` adds the same two keys to docs/english/platform-inventory.json.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SKIP_DIRS = {'node_modules', 'library', 'temp', 'build', 'local', 'tiktok-platform', 'packages', 'extensions'}
KIT_STEMS = ('SaveStore', 'ShopTx', 'RewardedService', 'GameUIKit', 'HomeGrowthEntries')
VALUE = (r'(?:coins?|golds?|gems?|diamonds?|money|cash|keys?|energy|stamina|hearts?|lives|tickets?|items?|props?|'
         r'skins?|shoes?|fragments?|shards?|tokens?)')
FIELD = r'((?:this\s*\.\s*)?[\w$]+(?:\s*\.\s*[\w$]+|\s*\[[^\]\n]*\])*)'
ADD = re.compile(FIELD + r'\s*(\+=|-=|\+\+|--)')
SELF = re.compile(FIELD + r'\s*=(?![=>])\s*([^;\n]+)')
SAVE = re.compile(r'(?i)\b(save|saveData|saveGame|saveAll|saveLocal|writeSave|persist|flush|setItem|setStorageSync|'
                  r'setStorage|setGlobalData|setData)\s*\(')
AD_CALL = re.compile(r'(?i)rewarded|showVideo|showAd|watchAd|playAd|videoAd|createRewardedVideoAd|onAdComplete|adSuccess')
FIX = {
    'reward_add': "pay it through SaveStore: store.grant({id: '<what>:' + <run or day id>, add: {<field>: n}, "
                  'apply: d => {/* items */}}); only on ok: read back, refresh the UI, then animate',
    'reward_spend': 'spend through ShopTx (begin -> commit) or store.grant({id, add: {<field>: -price}}); change the '
                    'team / item only after the save is ok, never charge in two places',
    'reward_save': 'one write per reward: the grant above saves; drop this separate save once the change goes through '
                   'grant / ShopTx (a failed grant keeps nothing in memory)',
}


def source_files(project):
    root = Path(project) / 'assets'
    if not root.is_dir():
        return []
    out = []
    for p in sorted(root.rglob('*')):
        if p.suffix in ('.js', '.ts') and p.is_file() and not SKIP_DIRS & set(p.relative_to(project).parts) \
                and not p.name.endswith('.d.ts') and not p.name.endswith('.min.js') \
                and not any(k in p.stem for k in KIT_STEMS) and p.stat().st_size <= 300 * 1024:
            out.append(p)
    return out


def code_lines(text):
    """(line number, line) with // comments and /* */ blocks blanked (strings are not parsed: good enough here)."""
    text = re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group(0).count('\n'), text, flags=re.S)
    for i, line in enumerate(text.splitlines(), 1):
        yield i, re.sub(r'(^|[^:\'"])//.*$', r'\1', line)


def _last(field):
    return re.split(r'[.\[\]\s\'"]+', field.strip().rstrip(']'))[-1] if field else ''


VALUE_WORD = re.compile(r'(?i)' + VALUE + r'(?:_?(?:num|count|amount|total|value))?$')


def _value_field(field):
    """coins, _gold, diamondNum, keyCount, totalCoins, player_gems: the value word starts the name or a camel / _ part
    (monkey, turkey are not keys)."""
    name = _last(field).lstrip('_$')
    if VALUE_WORD.match(name):
        return True
    for m in re.finditer(r'_(?=[A-Za-z])|(?<=[a-z0-9])(?=[A-Z])', name):
        if VALUE_WORD.match(name[m.end():]):
            return True
    return False


API_KEY = re.compile(r'(?i)\b(?:update|add|change|give|gain)[\w$]*\s*\(\s*[\'"](' + VALUE + r')[\'"]\s*,\s*(-)?')
API_NAMED = re.compile(r'(?i)\b((?:add|give|gain|spend|cost|use|sub)(?:Coins?|Golds?|Gems?|Diamonds?|Money|Keys?|Energy|'
                       r'Stamina|Hearts?|Tickets?))\s*\(\s*(-)?')


def changes(line):
    """[(kind, field)] of wallet / item changes on one code line (field writes and the game's own wallet calls such as
    updatePlayerInfo('key', 3) / addDiamond(-cost), 奔跑吧巨人)."""
    out = []
    for m in API_KEY.finditer(line):
        out.append(('reward_spend' if m.group(2) else 'reward_add', 'call:%s' % m.group(1)))
    for m in API_NAMED.finditer(line):
        if re.search(r'(?i)\b(?:function|public|private|protected|static)\s+' + m.group(1), line):
            continue
        spend = m.group(2) or re.match(r'(?i)spend|cost|use|sub', m.group(1))
        out.append(('reward_spend' if spend else 'reward_add', 'call:%s' % m.group(1)))
    for m in ADD.finditer(line):
        if _value_field(m.group(1)):
            out.append(('reward_spend' if m.group(2) in ('-=', '--') else 'reward_add', m.group(1).replace(' ', '')))
    for m in SELF.finditer(line):
        field = m.group(1).replace(' ', '')
        rhs = m.group(2).replace(' ', '')
        if _value_field(field) and rhs.startswith(field) and rhs[len(field):len(field) + 1] in '+-':
            out.append(('reward_spend' if rhs[len(field)] == '-' else 'reward_add', field))
    return out


def scan(project):
    project = Path(project)
    rows = []
    for p in source_files(project):
        rel = p.relative_to(project).as_posix()
        text = p.read_text(encoding='utf-8', errors='replace')
        if 'cc._RF.push(' in text or text.count('\n') < len(text) / 2000:
            continue                      # a compiled bundle or a minified file, not the game's own source
        file_rows, saves, ad_lines = [], [], []
        for n, line in code_lines(text):
            if not line.strip():
                continue
            if AD_CALL.search(line):
                ad_lines.append(n)
            for kind, field in changes(line):
                file_rows.append({'kind': kind, 'field': field, 'file': rel, 'line': n, 'code': line.strip()[:160]})
            m = SAVE.search(line)
            if m:
                saves.append({'kind': 'reward_save', 'api': m.group(1), 'file': rel, 'line': n,
                              'code': line.strip()[:160]})
        if file_rows:
            file_rows += saves
        for r in file_rows:
            if any(0 <= r['line'] - a <= 15 for a in ad_lines):
                r['in_ad_callback'] = True
        rows += file_rows
    uniq, out = set(), []
    for r in sorted(rows, key=lambda r: (r['file'], r['line'], r['kind'])):
        k = (r['kind'], r['file'], r['line'], r.get('field', r.get('api')))
        if k not in uniq:
            uniq.add(k)
            out.append(dict(r, fix=FIX[r['kind']]))
    return out


def plan(project):
    rows = scan(project)
    summary = {'add': sum(r['kind'] == 'reward_add' for r in rows),
               'spend': sum(r['kind'] == 'reward_spend' for r in rows),
               'save': sum(r['kind'] == 'reward_save' for r in rows),
               'in_ad_callback': sum(bool(r.get('in_ad_callback')) for r in rows),
               'fields': sorted({r['field'] for r in rows if r.get('field')}),
               'files': sorted({r['file'] for r in rows}),
               'order': 'claim id -> save and read back -> refresh UI -> animation; x2 = 2 * one base integer',
               'advice': 'none' if not rows else
               'switch the original wallet / item writes to SaveStore grant / ShopTx at stage 1 (reward_todo)'}
    return {'reward_todo': rows, 'reward_summary': summary}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    a = ap.parse_args(argv)
    if not (a.project / 'assets').is_dir():
        print(json.dumps({'error': 'not a Cocos project (no assets/): %s' % a.project}))
        return 2
    print(json.dumps(plan(a.project), ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
