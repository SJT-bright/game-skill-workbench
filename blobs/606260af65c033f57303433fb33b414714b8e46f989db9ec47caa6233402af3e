#!/usr/bin/env python3
"""Check-in / spin result / gift pack claim windows: the "watch ad x2" checkbox (v7.8, Saul 2026-10-31). Read-only.

Saul 2026-10-31 (64 MusicSlice check-in page as the model): a claim window may carry ONE "watch ad x2" checkbox next to
CLAIM, ticked by default. Ticked + CLAIM plays a rewarded video and pays 2x when it is watched to the end; unticked +
CLAIM pays 1x for free. remake-ads/SKILL.md, table row 签到、转盘结果、礼包领奖窗的看广告双倍.

Reads chrome_touch dump_ui files (the same dumps as art_check.py). Claim screens are dumps whose "purpose" is checkin,
wheel_result, spin_result or gift_pack; any other dump that shows a double checkbox is checked for rules 1 and 3 too.
Nodes hidden behind a later full-screen input blocker (the page under a popup) are not counted.
  claim_two_ads           more than one watch-ad entry (checkbox or video button) on one claim screen
  claim_ad_only           a claim screen whose only way to take the reward is a video button (no checkbox, no free
                          CLAIM / Collect): "必须看广告才能领" stays forbidden
  claim_no_claim          a double checkbox without a CLAIM button to press
  claim_double_unchecked  a double checkbox that no dump of that screen shows ticked (default must be ticked)
The home gift box (purpose gift: watch ad -> 5B, 30-minute cooldown, no checkbox) and the end-of-run revive / result
pages (two_video_buttons in audit_page_richness.py) are not claim screens here.
Whether 2x arrives only after a full watch, nothing on a close and 1x when unticked is the ad regression's job
(ad_regression.py double_watch / double_quit / double_free with adapter.double_claim).

  python3 audit_claim_double.py --project <game> [--dumps <folder> ...] --out report.json
Exit codes: 0 pass (also: no claim screen dumped), 1 a problem, 2 bad input.
"""
import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_page_richness import (load, words, node_under, fully_occluded, modal_masks,  # noqa: E402
                                 VIDEO_BUTTON, DOUBLE_BUTTON, REVIVE_BUTTON, CLAIM_LINK)

CLAIM_PURPOSES = {'checkin', 'wheel_result', 'spin_result', 'gift_pack'}
CHECKBOX = re.compile(r'check_?box|toggle|tick_?box|勾选|复选', re.I)
TICK = re.compile(r'check_?mark|checked|(?<![a-z])tick(?!_?box)|(?<![a-z])on(?![a-z])|_on\b|selected|勾|✓|✔|√', re.I)
FREE_ACTION = re.compile(r'claim|collect|(?<![a-z])get(?![a-z])|take|receive|(?<![a-z])ok(?![a-z])|领取|领', re.I)
CLOSE = re.compile(r'close|(?<![a-z])x(?![a-z0-9])|×|✕|back|关闭', re.I)


def sprite_frame(n):
    return str((n.get('comps', {}).get('sprite') or {}).get('frame', ''))


def names(b, nodes):
    """Node name, frame and words of a button and everything under it."""
    parts = [b.get('name', ''), sprite_frame(b), words(b)]
    for n in nodes:
        if n is not b and node_under(n, b):
            parts += [n.get('name', ''), sprite_frame(n), words(n)]
    return ' '.join(p for p in parts if p)


def visible_content(d):
    nodes = [n for n in d.get('nodes', []) if isinstance(n, dict) and isinstance(n.get('comps'), dict) and n.get('rect')]
    masks = modal_masks(nodes)
    return nodes, [n for n in nodes if n.get('opacity', 1) > 0.05 and not fully_occluded(n, masks)]


def ticked(box, nodes):
    """A tick drawn under the checkbox: a sprite named / framed check_mark, checked, tick, *_on ..., or a ✓ label.
    cc.Toggle switches its checkMark Sprite off when unticked, so an unticked mark leaves no sprite in the dump."""
    for n in nodes:
        if not (n is box or node_under(n, box)) or n.get('opacity', 1) <= 0.05:
            continue
        label = str((n['comps'].get('label') or {}).get('string', ''))
        if ('sprite' in n['comps'] and (TICK.search(n.get('name', '')) or TICK.search(sprite_frame(n)))) or re.search(r'[✓✔√]', label):
            return True
    return False


def screen(d):
    """-> dict for one dump: ad entries, checkboxes, free claim buttons, problems."""
    nodes, content = visible_content(d)
    buttons = [(b, names(b, nodes)) for b in content if 'button' in b['comps']]
    is_ad = lambda s: bool(VIDEO_BUTTON.search(s) or DOUBLE_BUTTON.search(s) or REVIVE_BUTTON.search(s))
    checkboxes = [b for b, s in buttons if CHECKBOX.search(s) and is_ad(s)]
    entries, free = list(checkboxes), []
    for b, s in buttons:
        if b in checkboxes or any(node_under(b, x) for x in entries + free if x is not b):
            continue
        claim = bool(CLAIM_LINK.search(s) or (FREE_ACTION.search(s) and not CLOSE.fullmatch(words(b) or '')))
        # Next to a checkbox, CLAIM is the free claim even when it shows a video icon while the box is ticked
        # (64 MusicSlice): unticked, the same button pays 1x without an ad.
        if claim and (checkboxes or not is_ad(s) or CLAIM_LINK.search(s)):
            free.append(b)
        elif is_ad(s):
            entries.append(b)
    return {'nodes': nodes, 'entries': entries, 'checkboxes': checkboxes, 'free': free}


def audit(dumps):
    rows, problems = [], []
    seen = {}
    for d in dumps:
        purpose = str(d.get('purpose') or '')
        s = screen(d)
        if purpose not in CLAIM_PURPOSES and not s['checkboxes']:
            continue
        where = '%s (%s)' % (Path(d.get('_file', '?')).name, purpose or 'no purpose')
        row = {'dump': d.get('_file'), 'purpose': purpose, 'ad_entries': [b['path'] for b in s['entries']],
               'checkboxes': [b['path'] for b in s['checkboxes']], 'free_claim': [b['path'] for b in s['free']],
               'ticked': [b['path'] for b in s['checkboxes'] if ticked(b, s['nodes'])]}
        rows.append(row)
        if len(s['entries']) > 1:
            problems.append('claim_two_ads: %s has %d watch-ad entries (%s): a claim window has one, the ticked-by-default '
                            '"watch ad x2" checkbox next to CLAIM (Saul 2026-10-31)' % (where, len(s['entries']), ', '.join(row['ad_entries'][:4])))
        if purpose in CLAIM_PURPOSES and s['entries'] and not s['checkboxes'] and not s['free']:
            problems.append('claim_ad_only: %s: the reward can only be taken by watching an ad (%s): add a free CLAIM; the '
                            'double is a ticked-by-default checkbox, unticked CLAIM pays 1x for free' % (where, ', '.join(row['ad_entries'][:2])))
        if s['checkboxes'] and not s['free']:
            problems.append('claim_no_claim: %s: double checkbox %s has no CLAIM button next to it' % (where, row['checkboxes'][0]))
        for b in s['checkboxes']:
            key = (purpose, b['path'])
            seen[key] = seen.get(key, False) or b['path'] in row['ticked']
    for (purpose, path), ok in sorted(seen.items()):
        if not ok:
            problems.append('claim_double_unchecked: %s on %s is never shown ticked: the "watch ad x2" checkbox is ticked by '
                            'default (dump the window as it first opens; a tick is a sprite named/framed check_mark, '
                            'checked, tick or *_on under the checkbox)' % (path, purpose or 'a screen'))
    return rows, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--dumps', type=Path, action='append', help='dump_ui folder(s) (default <project>/docs/test)')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    folders = a.dumps or [a.project / 'docs' / 'test']
    missing = [str(f) for f in folders if not f.is_dir()]
    if missing:
        ap.error('no dump folder: %s' % ', '.join(missing))
    rows, problems = audit(load(folders))
    report = {'tool': 'audit_claim_double', 'schema': 1, 'screens': rows, 'problems': problems, 'passed': not problems,
              'status': 'pass' if not problems else 'fail',
              'boundary': 'Structure of the claim windows in the dumps (one ad entry, free CLAIM, ticked by default); '
                          '2x / 0 / 1x payouts are proven by ad_regression.py double_* with adapter.double_claim.'}
    if not rows:
        report['note'] = 'no claim screen (purpose checkin / wheel_result / spin_result / gift_pack) and no double checkbox in the dumps'
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'screens': len(rows), 'problems': problems[:6], 'report': str(a.out)}, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == '__main__':
    raise SystemExit(main())
