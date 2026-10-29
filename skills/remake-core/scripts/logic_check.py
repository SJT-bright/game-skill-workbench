#!/usr/bin/env python3
"""逻辑检查（remake-test，用户 2026-10-23）：玩法做完就查（重塑第一轮玩法、英化优化做完），也用来验收别人的游戏。

用户给的两份真实报告里的问题，以后玩法做完就要查出来，不等用户验收时发现：
  关卡里退不出去、设置回不了首页、失败页没有 Home、暂停后物理还在动、回首页留着上一局的角色和回调、上一局广告的
  迟到回调落到新一局、镜头只能向右跟、第 85 关配置有空槽、存档异常没处理、主页任务绕过金币购买；
  刷新后关卡进度丢失、分包失败卡在 Loading 没有 Retry、滑动消除和落格两套判定、最后一秒发广告仍判失败、广告超时后
  奖励入口一直锁住、系统取消触摸仍提交消除、Daily Challenge 不是每日、末关后 NEXT 重复最后一关、教学比第一关还难、
  声音设置不保存、平台按钮点了没反应、失败弹窗随机交换按钮位置、命中重叠牌不停止遍历、无上限的同步洗牌循环。

两部分：
  1. 静态扫描 assets/ 下的 .ts/.js（去掉注释后）和关卡 JSON，列出疑点（文件:行）。每条读源码判断：
     真问题就修；误报或有意设计写进 docs/logic/triage.json：{"items": [{"rule": "L-LOOP", "file": "assets/x.ts",
     "verdict": "false_positive" | "by_design", "why": "..."}]}
  2. 实际流程记录 docs/logic/flows.json（--init 生成模板）：F01–F20 每条在浏览器里用真实触摸走过（chrome_touch，
     两种手机比例；不直接调按钮回调、不强制过关），写 status pass / fail / untested / n/a（n/a 要写 why），pass 要有
     evidence（工程里的截图/dump/日志路径）。

  python logic_check.py --project <工程> --init                       # 写 docs/logic/flows.json 模板
  python logic_check.py --project <工程> [--mode build|review] [--binding review.json] [--out <json>]

--mode build（默认，自己做的游戏）：有未判定的"需处理"疑点、或流程缺/失败/未测，就不通过（退出码 1）。
--mode review（验收别人的游戏，只检查不修改）：不拦，报告列出全部疑点和流程结果，写进《优化建议报告》。
结果：<工程>/docs/logic/logic-check.json 和 logic-check.md（tool logic_check，供门禁 LOGIC-01）。
"""
from __future__ import annotations

import argparse
import fnmatch
import json
from pathlib import Path
import re
import sys
import logic_regressions as regressions

SKIP_DIRS = {'node_modules', 'library', 'temp', 'build', 'local', 'profiles', '.git', 'settings', 'packages'}
FLOWS = [
    ('F01', '启动到首页；404/503与旧请求挂起分别验证；Retry产生新底层请求并能进关操作（R03）', 'L-LOAD'),
    ('F02', '首页 → 开始 → 第一关真实通关，奖励数字变化正确、只结算一次', 'L-ROUND'),
    ('F03', '关卡内暂停 → 继续：物理、计时、动画、生成都停住再恢复', 'L-PAUSE'),
    ('F04', '关卡内暂停 → 返回首页 → 再开局：没有上一局的角色、绳索、物件、触摸、延迟回调、计时器残留', 'L-EXIT'),
    ('F05', '失败页 → Home → 首页 → 再选关 → 能正常操作', 'L-EXIT'),
    ('F06', '失败页 → Retry → 新一局：回到起点、扣减一致、触摸有效', 'L-ROUND'),
    ('F07', '胜利页 → Next 进下一关；胜利页 → Home 回首页', 'L-EXIT'),
    ('F08', '最后一关之后：全通关页或明确的循环，Next 不会反复重开最后一关', 'L-LEVELS'),
    ('F09', '设置打开 → 关闭/返回回到原来的页面；关卡里的设置能回首页', 'L-EXIT'),
    ('F10', '刷新保持进度与声音；坏存档可恢复（R02）；实际音频输出0/中/满档、开关及失败重试（R09）', 'L-SAVE'),
    ('F11', '每个广告入口：完成/取消/失败/超时/迟到回调/重复回调——不重复发奖、不串局、超时后安全恢复且不叠广告', 'L-AD'),
    ('F12', '计时/胜负边界：最后一秒发起广告、归零瞬间、最后一步同时胜负，结果唯一', 'L-AD'),
    ('F13', '真实拾取→拖出原节点→合法落点改变业务；区分越界正常松手/系统取消，多指不接管（R07）', 'L-INPUT'),
    ('F14', '购买/装备正确；循环列表反向多圈；消耗工具须有有效消费者（R01/R04/R06）', 'L-ECON'),
    ('F15', '平台按钮（加桌面、回访、排行、更多游戏）：有反馈或已隐藏，没有点了没反应的按钮', 'L-PLATFORM'),
    ('F16', '教程比第一关简单、能完成、能跳过，跳过/完成后去向正确', 'L-LEVELS'),
    ('F17', '两种比例（如 390×844、375×667）下失败页、胜利页、暂停页的按钮都看得到、点得到', 'L-EXIT'),
    ('F18', '每日/签到类：真的按日期（跨日重置、同日不重复领），否则改名', 'L-MODE'),
    ('F19', '切到后台再回来、失去焦点：自动暂停，不崩、不跳过计时', 'L-PAUSE'),
    ('F20', '连续 3 次"返回首页 → 再开局"（两种比例各一遍），每次触摸都有效', 'L-EXIT'),
]
SOUND_FLAG = re.compile(r'\b(canSound|canMusic|soundOn|musicOn|isMute|isMuted|muted|sfxOn|bgmOn|soundEnabled|musicEnabled|'
                        r'enableSound|enableMusic|sound_on|music_on)\b')
DATE_API = re.compile(r'new\s+Date\b|Date\.now\s*\(|getDate\s*\(|toDateString|getDay\s*\(|getUTCDate')
PHYSICS = re.compile(r'PhysicsSystem2D|PhysicsSystem\b|getPhysicsManager|RigidBody')
PHYSICS_OFF = re.compile(r'(PhysicsSystem2D|PhysicsSystem)\.instance\.enabled\s*=\s*false|getPhysicsManager\(\)\.enabled\s*=\s*false|'
                         r'director\.pause\s*\(|\.enabled\s*=\s*!?\s*\w*[Pp]aused|physics\w*\.enabled\s*=\s*false|fixedTimeStep\s*=\s*0|'
                         r'enabledContactListener|timeScale\s*=\s*0')


def strip_comments(code):
    code = re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group(0).count('\n'), code, flags=re.S)
    return re.sub(r'(^|[^:\'"\\])//.*$', r'\1', code, flags=re.M)


def line_of(code, pos):
    return code.count('\n', 0, pos) + 1


def scripts(proj):
    base = proj / 'assets'
    out = []
    if not base.is_dir():
        return out
    for f in sorted(base.rglob('*')):
        rel = f.relative_to(proj).as_posix()
        if f.suffix not in ('.ts', '.js') or not f.is_file() or f.name.endswith(('.min.js', '.d.ts')) or \
                SKIP_DIRS & set(rel.split('/')[:-1]) or f.stat().st_size > 1_500_000:
            continue
        try:
            out.append((rel, strip_comments(f.read_text(encoding='utf-8', errors='ignore'))))
        except OSError:
            pass
    return out


def scan(proj):
    """Static suspects. severity fail = must be fixed or judged in triage.json; hint = look at it in the flows."""
    found = []
    files = scripts(proj)
    allcode = '\n'.join(c for _, c in files)

    def add(rule, sev, rel, line, msg):
        found.append({'rule': rule, 'severity': sev, 'file': rel, 'line': line, 'message': msg})

    set_keys, get_keys = {}, set()
    for rel, code in files:
        for m in re.finditer(r'setItem\s*\(\s*([\'"`])([^\'"`]+)\1', code):
            set_keys.setdefault(m.group(2), (rel, line_of(code, m.start())))
        for m in re.finditer(r'getItem\s*\(\s*([\'"`])([^\'"`]+)\1', code):
            get_keys.add(m.group(2))
        # touch cancel committed like a normal release (Mahjong 2026-10-23: 16 -> 14 tiles after touchcancel)
        ends = {m.group(2) for m in re.finditer(r'(TOUCH_END|[\'"]touchend[\'"])\s*,\s*(?:this\.)?(\w+)', code)}
        for m in re.finditer(r'(TOUCH_CANCEL|[\'"]touchcancel[\'"])\s*,\s*(?:this\.)?(\w+)', code):
            if m.group(2) in ends:
                add('L-INPUT-CANCEL', 'fail', rel, line_of(code, m.start()),
                    'touch cancel uses the same handler as touch end (%s): a cancelled gesture must restore the drag start, clear the '
                    'selection and commit nothing' % m.group(2))
        if re.search(r'TOUCH_MOVE|[\'"]touchmove[\'"]', code) and not re.search(r'TOUCH_CANCEL|[\'"]touchcancel[\'"]', code):
            add('L-INPUT-CANCEL', 'hint', rel, 1, 'drag (touch move) without any touch-cancel handling: check F13')
        for m in re.finditer(r'while\s*\(\s*(true|1|!0)\s*\)|for\s*\(\s*;\s*;\s*\)', code):
            add('L-LOOP', 'fail', rel, line_of(code, m.start()),
                'unbounded synchronous loop: give it a try limit, yield, and a guaranteed fallback (Mahjong auto-shuffle while(true))')
        for m in re.finditer(r'(loadBundle|loadRes|loadDir|load|preload|loadScene|preloadScene)\s*\(', code):
            seg = code[m.end():m.end() + 900]
            e = re.search(r'if\s*\(\s*(err|error|e)\s*\)\s*\{([^{}]*)\}', seg)
            if e and re.fullmatch(r'\s*((console\.\w+|cc\.(log|warn|error)|log|warn|error)\s*\([^;]*\)\s*;?\s*)*', e.group(2)):
                add('L-LOAD', 'fail', rel, line_of(code, m.end() + e.start()),
                    'load error branch only logs (%s): the player is stuck on Loading; show a visible error with Retry that sends a '
                    'new request and ignores the old one' % m.group(1))
        for m in re.finditer(r'Math\.random\s*\(\s*\)', code):
            around = code[max(0, m.start() - 250):m.end() + 250]
            if re.search(r'(btn|button|Btn|Button)\w*', around) and re.search(r'setPosition|\.position\s*=|\.x\s*=|swap', around):
                add('L-BUTTON-FIXED', 'fail', rel, line_of(code, m.start()),
                    'buttons placed by Math.random (Mahjong: retry/continue/close swap places 12-15%%): fixed positions, same meaning '
                    'every time')
        for m in re.finditer(r'Math\.min\s*\([^;]{0,120}(level|Level|lv|stage|Stage)[^;]{0,80}length\s*-\s*1', code):
            add('L-LEVELS', 'hint', rel, line_of(code, m.start()),
                'level index clamped to the last level: after the last level NEXT must not replay it forever (F08)')
        if re.search(r'setItem\s*\(', code) and not re.search(r'\btry\s*\{', code):
            add('L-SAVE', 'hint', rel, 1, 'saves without try/catch: a failed write must show an error and keep the old data (F10)')
        for m in re.finditer(r'\[[^\[\]\n]*,\s*,[^\[\]\n]*\]', code):
            if re.search(r'level|Level|stage|LEVEL', code[max(0, m.start() - 300):m.start()]):
                add('L-CONFIG', 'fail', rel, line_of(code, m.start()), 'level data array with an empty slot ", ,": remove the hole or fill it')
    for key, (rel, line) in set_keys.items():
        if key not in get_keys:
            add('L-SAVE', 'fail', rel, line, 'saved key "%s" is never read back: progress/settings written but not restored after a '
                'refresh (Mahjong: highest level saved, game restarts at level 1)' % key)
    flags = [(rel, line_of(code, m.start()), m.group(1)) for rel, code in files for m in re.finditer(SOUND_FLAG, code)]
    saved_sound = any(re.search(r'setItem\s*\([^)]*(sound|music|mute|sfx|bgm|audio|volume)', c, re.I) for _, c in files) or \
        re.search(r'(sound|music|mute|sfx|bgm|audio|volume)\w*\s*:', ' '.join(k for k in set_keys), re.I)
    if flags and not saved_sound and not any(re.search(r'sound|music|mute|sfx|bgm|audio|volume', k, re.I) for k in set_keys):
        rel, line, name = flags[0]
        whole_state = any(re.search(r'JSON\.stringify\s*\(', c) and re.search(r'setItem\s*\(', c) for _, c in files)
        add('L-SAVE', 'hint' if whole_state else 'fail', rel, line,
            'sound setting "%s" persistence is not proven by key-name scanning%s; inspect the actual serialized state, reload and '
            'verify late audio applies saved settings (F10); do not label it memory-only without tracing the writer' %
            (name, ' (a JSON state writer exists)' if whole_state else ''))
    names = ' '.join(rel for rel, _ in files) + ' ' + ' '.join(p.name for p in (proj / 'assets').rglob('*') if p.is_file()) \
        if (proj / 'assets').is_dir() else ''
    if re.search(r'daily', allcode + ' ' + names, re.I) and not DATE_API.search(allcode):
        rel = next((r for r, c in files if re.search(r'daily', c, re.I)), 'assets')
        add('L-MODE', 'fail', rel, 1, '"Daily" appears but no script reads the date: a daily mode needs a date seed, a per-day save and '
            'a day reset, otherwise rename it (Mahjong "Daily Challenge" was a normal level)')
    if PHYSICS.search(allcode) and re.search(r'\bpause', allcode, re.I) and not PHYSICS_OFF.search(allcode):
        rel = next((r for r, c in files if PHYSICS.search(c)), 'assets')
        add('L-PAUSE', 'fail', rel, 1, 'physics is used and the game pauses, but nothing stops the physics step: pause must stop physics, '
            'timers and spawning and resume them on continue/restart (Double Jump: pause only changed a flag)')
    if (re.search(r'setTimeout\s*\(|scheduleOnce\s*\(', allcode) and
            not re.search(r'clearTimeout|unscheduleAllCallbacks|unschedule\s*\(|Tween\.stopAll|stopAllByTarget', allcode)):
        add('L-ASYNC', 'hint', 'assets', 1, 'delayed callbacks are never cleared: leaving a round must cancel them or check a round token')
    if files and not re.search(r'EVENT_HIDE|visibilitychange|onHide|game\.on\(\s*[\'"]hide|Game\.EVENT_HIDE', allcode):
        add('L-PAUSE', 'hint', 'assets', 1, 'no hide/visibility handling: switching to the background should pause the round (F19)')
    for f in sorted((proj / 'assets').rglob('*.json')) if (proj / 'assets').is_dir() else []:
        rel = f.relative_to(proj).as_posix()
        if SKIP_DIRS & set(rel.split('/')[:-1]) or not re.search(r'level|stage|chapter', rel, re.I) or f.stat().st_size > 5_000_000:
            continue
        try:
            data = json.loads(f.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError):
            continue
        holes = []

        def walk(x, path):
            if isinstance(x, list):
                for i, v in enumerate(x):
                    if v is None or v == {} or v == []:
                        holes.append('%s[%d]' % (path, i))
                    else:
                        walk(v, '%s[%d]' % (path, i))
            elif isinstance(x, dict):
                for k, v in x.items():
                    walk(v, path + '.' + str(k))
        walk(data, '$')
        if holes:
            add('L-CONFIG', 'fail', rel, 1, 'level config has empty entries %s: remove the holes (Double Jump level 85 had an empty slot) '
                'and check every level loads' % ', '.join(holes[:4]))
    found.extend(regressions.static_suspects(files))
    return found, len(files)


def triaged(f, triage):
    for t in triage:
        if t.get('rule') == f['rule'] and (fnmatch.fnmatch(f['file'], t.get('file', '')) or f['file'] == t.get('file')) and \
                t.get('verdict') in ('false_positive', 'by_design') and str(t.get('why', '')).strip():
            if t.get('line') in (None, f['line']):
                return t
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--mode', choices=('build', 'review'), default='build')
    ap.add_argument('--init', action='store_true', help='write the docs/logic/flows.json template and stop')
    ap.add_argument('--binding', type=Path)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    proj = a.project.resolve()
    if not (proj / 'assets').is_dir():
        ap.error('%s is not a Cocos project (no assets folder)' % proj)
    logic = proj / 'docs' / 'logic'
    flows_file = logic / 'flows.json'
    digest = regressions.source_digest(proj)
    if a.init:
        logic.mkdir(parents=True, exist_ok=True)
        if flows_file.exists():
            try:
                doc = json.loads(flows_file.read_text(encoding='utf-8-sig'))
                if not isinstance(doc, dict) or not isinstance(doc.get('regressions', []), list):
                    raise ValueError('expected an object and a regressions array')
            except (OSError, ValueError) as exc:
                ap.error('existing flows not overwritten: %s' % exc)
        else:
            doc = {'schema': 'logic_flows.v1', 'flows': [
                {'id': i, 'title': t, 'status': 'untested', 'evidence': '', 'note': ''} for i, t, _ in FLOWS]}
        records = doc.setdefault('regressions', [])
        ids = {r.get('id') for r in records if isinstance(r, dict)}
        added = [r for r in regressions.templates() if r['id'] not in ids]
        records.extend(added)
        # An init rerun never refreshes a stale binding or resets completed rows.
        doc.setdefault('regression_binding', {'source_sha256': digest})
        data = json.dumps(doc, ensure_ascii=False, indent=2) + '\n'
        if not flows_file.exists() or flows_file.read_text(encoding='utf-8-sig') != data:
            flows_file.write_text(data, encoding='utf-8')
        print(json.dumps({'status': 'initialized', 'regressions_added': len(added), 'path': str(flows_file)}, ensure_ascii=False))
        return 0
    findings, n_files = scan(proj)
    try:
        triage = json.loads((logic / 'triage.json').read_text(encoding='utf-8-sig')).get('items', [])
        triage = [t for t in triage if isinstance(t, dict)]
    except (OSError, ValueError, AttributeError):
        triage = []
    for f in findings:
        t = triaged(f, triage)
        if t:
            f['verdict'], f['why'] = t['verdict'], t['why']
    open_fails = [f for f in findings if f['severity'] == 'fail' and not f.get('verdict')]
    try:
        document = json.loads(flows_file.read_text(encoding='utf-8-sig'))
        rec = {x.get('id'): x for x in document.get('flows', []) if isinstance(x, dict)}
    except (OSError, ValueError, AttributeError):
        rec = None
        document = {}
    flows, flow_problems = [], []
    for fid, title, rule in FLOWS:
        x = (rec or {}).get(fid, {})
        st = x.get('status', 'missing') if rec is not None else 'missing'
        ev = str(x.get('evidence') or '')
        row = {'id': fid, 'title': title, 'rule': rule, 'status': st, 'evidence': ev, 'note': x.get('note', '')}
        if st == 'pass' and not (ev and any((proj / e.strip()).exists() for e in re.split(r'[;,]', ev) if e.strip())):
            row['problem'] = 'pass without an evidence file in the project (screenshot / dump / log)'
        elif st == 'n/a' and not str(x.get('why') or x.get('note') or '').strip():
            row['problem'] = 'n/a needs a why'
        elif st not in ('pass', 'n/a'):
            row['problem'] = {'fail': 'flow fails: fix it and walk it again', 'untested': 'not walked yet',
                              'missing': 'not recorded in docs/logic/flows.json (run --init)'}.get(st, 'unknown status ' + str(st))
        if row.get('problem'):
            flow_problems.append(row)
        flows.append(row)
    regression_rows, regression_problems = regressions.validate(document, proj, digest)
    # Self-contained reports let the main gate recheck evidence hashes later.
    for row in regression_rows:
        if row.get('id') == 'R06' and isinstance(row.get('button_check'), dict):
            row['button_check'] = dict(row['button_check'], path=str((proj / row['button_check']['path']).resolve()))
            row['button_check_root'] = str(proj.resolve())
        if isinstance(row.get('evidence'), list):
            row['evidence'] = [dict(ref, path=str((proj / ref['path']).resolve()))
                               if isinstance(ref, dict) and isinstance(ref.get('path'), str) else ref
                               for ref in row['evidence']]
    blocking = (len(open_fails) + len(flow_problems) + len(regression_problems)) if a.mode == 'build' else 0
    report = {'tool': 'logic_check', 'schema': 1, 'mode': a.mode, 'checked': n_files + len(FLOWS) + len(regressions.CASES), 'scripts': n_files,
              'failed': blocking, 'passed': blocking == 0 and n_files > 0, 'status': 'pass' if blocking == 0 and n_files > 0 else 'fail',
              'open_findings': len(open_fails), 'flow_problems': len(flow_problems), 'findings': findings, 'flows': flows,
              'regression_version': 1, 'regressions': regression_rows, 'regression_problems': len(regression_problems),
              'current_source_sha256': digest,
              'regression_binding': document.get('regression_binding'),
              'boundary': 'Static suspects need a source read; flows are recorded by the tester from real touch runs; untested is never pass.'}
    if a.mode == 'review':
        report['status'] = 'review'
        report['passed'] = False  # a review report never passes the build gate (LOGIC-01 needs --mode build)
    if a.binding:
        try:
            b = json.loads(a.binding.read_text(encoding='utf-8')).get('binding')
        except (OSError, ValueError) as exc:
            ap.error('binding: %s' % exc)
        if not isinstance(b, dict):
            ap.error('no binding object in %s' % a.binding)
        report['binding'] = b
    out = a.out or logic / 'logic-check.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    md = ['# 逻辑检查（%s）' % ('自己的游戏：要全部处理' if a.mode == 'build' else '验收评审：只列出，不修改'), '',
          '结论：%s；脚本 %d 个；待处理疑点 %d；流程问题 %d' % (report['status'], n_files, len(open_fails), len(flow_problems)), '',
          '## 静态疑点（每条读源码判断：真问题就修，误报/有意设计写进 docs/logic/triage.json）', '']
    for f in findings:
        md.append('- [%s] %s %s:%s %s%s' % ('需处理' if f['severity'] == 'fail' else '提示', f['rule'], f['file'], f['line'], f['message'],
                                           ('（已判定 %s：%s）' % (f['verdict'], f['why'])) if f.get('verdict') else ''))
    md += ['', '## 实际流程（真实触摸、两种比例；没走到的写 untested，不能算通过）', '']
    for r in flows:
        md.append('- %s %s：%s%s%s' % (r['id'], r['title'], r['status'], ('，证据 ' + r['evidence']) if r['evidence'] else '',
                                      ('　← ' + r['problem']) if r.get('problem') else ''))
    md += ['', '## 实例沉淀回归 R01–R09（缺证据、旧源码绑定、未测均不通过）', '']
    for r in regression_rows:
        md.append('- %s %s：%s%s' % (r['id'], r['title'], r['status'], (' ← ' + r['problem']) if r.get('problem') else ''))
    out.with_suffix('.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'open_findings': len(open_fails), 'flow_problems': len(flow_problems),
                      'regression_problems': len(regression_problems),
                      'top': [('%s %s:%s' % (f['rule'], f['file'], f['line'])) for f in open_fails[:6]], 'report': str(out)},
                     ensure_ascii=False))
    return 0 if a.mode == 'review' or report['passed'] else 1  # review: exit 0, only reports


if __name__ == '__main__':
    sys.exit(main())
