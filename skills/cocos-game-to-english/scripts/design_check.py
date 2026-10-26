#!/usr/bin/env python3
"""设计关自检（用户 2026-10-24，references/check-stages.md）：玩法和板块设计定下来就跑，不等到最终总检测。

什么时候跑：英化在阶段 1.5（优化做完、进阶段 2 美术之前）；重塑在第一轮玩法（节点 1 之前）；之后只要改了关卡表、
皮肤表、docs/modules.json、docs/features.json 或排名决定，就对改动重跑一次。最终总检测（check_known_issues.py）
不再重复这些检查（MOD-01、ECON-01、LEVEL-01、FEAT-00、RANK-01 标 gate "design"）。

依次运行（缺输入就是"需处理"，不跳过）：
  关卡板块    audit_level_plan.py              70 关及以上（用户 2026-10-24：≥70 都通过，多了不删）、难度逐关递增、
                                               每 10 关一个限定关、每 10 关一个按种子随机的奖励关；限定皮肤两种格式都行：
                                               只在最后一个限定关送（final），或每个限定关各送一款（every_10）
                                               （地图页要 dump，没有 dump 时这里只提示，美术关 art_check.py 再查）
  内置板块    audit_game_modules.py            按钮审查、禁用功能、AdRewards.ts 原样＋模拟、皮肤板块、限定皮肤路线
                                               （礼盒 10 帧动画不在这里，美术关查）
  皮肤数值    audit_acquisition_progression.py unlock_table.json（skin.v1：价格台阶、加成、限定皮肤排最前）
  排名扩展    audit_league.py                  docs/league/decision.json（默认关闭）
  可选扩展    audit_optional_features.py       docs/features.json（签到默认关闭）

  python design_check.py --project <工程> [--dumps <文件夹>] [--board localize|remake] [--out <输出>]

结果：<输出>/design-check.md、design-check.json（tool design_check）、logs/。退出码 0 全部通过，1 有需处理，2 参数错误。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
import time
import sys

HERE = Path(__file__).resolve().parent
TIMEOUT = 600
TABLE_PATHS = ('assets/resources/config/unlock_table.json', 'docs/economy/unlock_table.json')
MAP_CHECKS = {'map_page', 'map_shows_total'}   # pages: blocking at the art stage (art_check.py), a hint here


def run(name, args, logs):
    from check_runner import run_tool
    return run_tool(name, args, logs, HERE, TIMEOUT)


def report_checks(path, text):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))['checks']
    except (OSError, ValueError, KeyError, TypeError):
        return [{'id': 'run', 'passed': False, 'detail': text.strip()[-300:] or 'no report'}]


def main():
    started = time.monotonic()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--dumps', type=Path, help='chrome_touch dump_ui folder for the map page (default <project>/docs/test)')
    ap.add_argument('--board', choices=['localize', 'remake'])
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    proj = a.project.resolve()
    if not (proj / 'assets').is_dir():
        ap.error('%s is not a Cocos project (no assets folder)' % proj)
    board_file = proj / 'docs' / 'board.txt'
    recorded = board_file.read_text(encoding='utf-8').strip().lower() if board_file.is_file() else ''
    board = a.board or (recorded if recorded in ('localize', 'remake') else None)
    out = (a.out or proj.parent / (proj.name + '-designcheck') / dt.datetime.now().strftime('%Y%m%d-%H%M%S')).resolve()
    if out.is_relative_to(proj):
        ap.error('output must be outside the project')
    if out.exists() and any(out.iterdir()):
        ap.error('output folder exists and is not empty: %s' % out)
    logs = out / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    rows = []
    board_args = ['--board', board] if board else []

    def add(title, ok, detail, log=''):
        rows.append({'check': title, 'status': '通过' if ok is True else ('提示' if ok is None else '需处理'), 'detail': detail, 'log': log})

    def summary(checks, ok_text):
        bad = [c for c in checks if not c['passed']]
        return '；'.join('%s：%s' % (c['id'], str(c['detail'])[:140]) for c in bad[:4]) if bad else ok_text

    dumps = (a.dumps or proj / 'docs' / 'test').resolve()
    code, text = run('audit_level_plan.py', ['--project', proj, '--dumps', dumps, *board_args, '--out', out / 'level_plan.json'], logs)
    checks = report_checks(out / 'level_plan.json', text)
    design = [c for c in checks if c['id'] not in MAP_CHECKS]
    pages = [c for c in checks if c['id'] in MAP_CHECKS and not c['passed']]
    ok = all(c['passed'] for c in design)
    add('关卡板块（LEVEL-01）', False if not ok else (None if pages else True),
        summary(design, '通过') if not ok else ('关卡表通过；地图页还没 dump，美术关 art_check.py 查' if pages else '通过'), 'level_plan.json')

    code, text = run('audit_game_modules.py', ['--project', proj, *board_args, '--out', out / 'game_modules.json'], logs)
    checks = report_checks(out / 'game_modules.json', text)
    add('内置板块（MOD-01）', all(c['passed'] for c in checks), summary(checks, '通过（%d 项）' % len(checks)), 'game_modules.json')

    table = next((proj / t for t in TABLE_PATHS if (proj / t).is_file()), None)
    if table:
        code, text = run('audit_acquisition_progression.py', ['--table', table, '--report', out / 'acquisition.json'], logs)
        try:
            rep = json.loads((out / 'acquisition.json').read_text(encoding='utf-8'))
            errs = rep.get('errors') or []
            ok = rep.get('status') == 'pass' and not errs
        except (OSError, ValueError):
            errs, ok = [text.strip()[-300:]], False
        add('皮肤数值（ECON-01）', ok, '；'.join(map(str, errs[:4]))[:600] if not ok else '通过：%s' % table.relative_to(proj), 'acquisition.json')
    else:
        add('皮肤数值（ECON-01）', None, '没有 unlock_table.json（不要皮肤时由内置板块一行确认）')

    code, text = run('audit_league.py', ['--project', proj, *board_args, '--out', out / 'league.json'], logs)
    checks = report_checks(out / 'league.json', text)
    add('排名扩展（RANK-01）', all(c['passed'] for c in checks), summary(checks, '通过'), 'league.json')

    code, text = run('audit_optional_features.py', ['--project', proj, '--out', out / 'optional_features.json'], logs)
    checks = report_checks(out / 'optional_features.json', text)
    add('可选扩展（FEAT-00）', all(c['passed'] for c in checks), summary(checks, '通过'), 'optional_features.json')

    blocking = [r for r in rows if r['status'] == '需处理']
    report = {'tool': 'design_check', 'schema': 1, 'board': board, 'checked': len(rows), 'failed': len(blocking),
              'passed': not blocking, 'status': 'pass' if not blocking else 'fail', 'rows': rows,
              'gate_ids': ['LEVEL-01', 'MOD-01', 'ECON-01', 'RANK-01', 'FEAT-00'],
              'time': dt.datetime.now().isoformat(timespec='seconds')}
    from check_runner import read_timings
    report['check_timings'] = read_timings(logs)
    report['total_elapsed_seconds'] = round(time.monotonic()-started,6)
    (out / 'design-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    md = ['# 设计关自检', '', '工程：%s　板块：%s　时间：%s' % (proj, {'localize': '英化', 'remake': '重塑'}.get(board, '未记录'), report['time']), '',
          ('**需处理 %d 项：改完重跑本脚本，全部通过再进美术。**' % len(blocking)) if blocking else
          '**设计关全部通过。**最终总检测不再重复这些检查（references/check-stages.md）。',
          '', '| 检查 | 结果 | 说明 |', '| --- | --- | --- |']
    md += ['| %s | %s | %s |' % (r['check'], r['status'], r['detail'].replace('|', '/')) for r in rows]
    (out / 'design-check.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print('\n'.join(md))
    print('\n完整结果：%s' % out)
    return 1 if blocking else 0


if __name__ == '__main__':
    raise SystemExit(main())
