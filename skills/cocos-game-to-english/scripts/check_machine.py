#!/usr/bin/env python3
"""Does this computer have what the English workflow needs? (English pack 10.2.10, Saul 2026-10-31) Read-only.

The English Skill is used on other people's computers (macOS or Windows). Run this once at the start of stage 1, before
the Chinese original is exported, so a missing tool is found in the first minute and not after hours of work.

  python3 check_machine.py [--project <Cocos project>] [--quick] [--json]      (Windows: python check_machine.py ...)

Checks: Python 3.8+; Pillow (needed to package: image conversion, art checks); numpy and ffmpeg (recommended: some
art checks and the sound loudness check say "not measured" without them, English games only get a warning); Node.js
18+ and a browser the packaging checks can drive (Ego Lite if installed, else Chrome, Edge or Chromium, see
browser_env.py; --quick skips starting the browser once); the Cocos Creator for the project (find_creator.py).
It installs nothing. Every missing item says what it breaks and how to add it, so the AI can ask the user once and fix it.
Exit 0 everything required is there, 1 something required is missing, 2 bad input.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import browser_env  # noqa: E402
import find_creator  # noqa: E402

WIN = sys.platform == 'win32'
PY = 'python' if WIN else 'python3'


def pip_hint(*names):
    return '%s -m pip install --user %s' % ('py -3' if WIN else 'python3', ' '.join(names))


def ffmpeg_path():
    found = shutil.which('ffmpeg')
    if found:
        return found
    for d in ('/opt/homebrew/bin', '/usr/local/bin', '/usr/bin', r'C:\ffmpeg\bin', r'C:\Program Files\ffmpeg\bin'):
        for name in ('ffmpeg', 'ffmpeg.exe'):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
    local = os.environ.get('LOCALAPPDATA')
    if local and os.path.isfile(os.path.join(local, 'Microsoft', 'WinGet', 'Links', 'ffmpeg.exe')):
        return os.path.join(local, 'Microsoft', 'WinGet', 'Links', 'ffmpeg.exe')
    return None


def row(name, ok, required, detail, fix=None, affects=None):
    return {'name': name, 'ok': bool(ok), 'required': required, 'detail': detail, 'fix': None if ok else fix,
            'affects': None if ok else affects}


def collect(project=None, quick=False):
    rows = []
    v = sys.version_info
    rows.append(row('Python', v >= (3, 8), True, '%d.%d.%d（%s）' % (v[0], v[1], v[2], sys.executable),
                    '到 https://www.python.org 装 3.10 或更新的版本，Windows 安装时勾上 Add python.exe to PATH',
                    '所有检查和出包脚本'))
    has = lambda m: importlib.util.find_spec(m) is not None
    rows.append(row('Pillow', has('PIL'), True, '有' if has('PIL') else '没有', pip_hint('pillow'),
                    '出包时换图片格式、压缩图片，和美术检查'))
    rows.append(row('numpy', has('numpy'), False, '有' if has('numpy') else '没有', pip_hint('numpy'),
                    '美术检查里棋盘格背景、按钮底色这几行会写「没法查」'))
    ff = ffmpeg_path()
    rows.append(row('ffmpeg', ff, False, ff or '没有',
                    'macOS：brew install ffmpeg；Windows：winget install Gyan.FFmpeg（装好后新开终端）',
                    '出包时量不了声音响度（英化游戏只警告，不拦包）'))
    chosen = browser_env.plan('auto') if quick else browser_env.check('auto')
    node, major = browser_env.node_path()
    if chosen.get('route') == 'ego':
        rows.append(row('出包检查用的浏览器', True, True, browser_env.say(chosen)))
        if not node:
            rows.append(row('Node.js', False, False, '没有', '到 https://nodejs.org 装 LTS 版',
                            'Ego 用不了时没法改用 Chrome/Edge 跑检查'))
    else:
        rows.append(row('Node.js', node and (major or 0) >= browser_env.MIN_NODE, True,
                        '%s（%s）' % (major, node) if node else '没有', '到 https://nodejs.org 装 LTS 版，装好后新开终端',
                        '广告回归、运行时检查、截图都要它驱动浏览器'))
        ok = chosen.get('route') == 'chrome' and not chosen.get('problem')
        rows.append(row('出包检查用的浏览器', ok, True, browser_env.say(chosen),
                        '装 Google Chrome（https://www.google.com/chrome），Windows 自带的 Edge 也行；装在别处的设 '
                        'CDP_BROWSER=<浏览器程序的完整路径>', '广告回归、运行时检查、截图、出包'))
    if project:
        try:
            r = find_creator.report(project)
        except (OSError, ValueError) as error:
            rows.append(row('Cocos Creator', False, True, str(error), '确认 --project 指的是有 assets/ 的 Cocos 工程那一层'))
        else:
            if r['status'] == 'exact':
                detail = '%s：%s' % (r['version'], r['editor']['exe'])
            elif r['status'] == 'substitute':
                detail = '工程是 %s，没装；先用同一小版本的 %s：%s' % (r['version'], r['editor']['version'], r['editor']['exe'])
            else:
                detail = '工程是 %s，这台电脑没装，同一小版本也没有（装了：%s）' % (
                    r['version'], '、'.join(e['version'] for e in r['installed']) or '一个都没有')
            rows.append(row('Cocos Creator', r['editor'], True, detail,
                            '请用户打开 Cocos Dashboard（https://www.cocos.com/creator-download），在「编辑器」里下载 %s；'
                            '装在别处的设 COCOS_CREATOR=<CocosCreator 程序的完整路径>' % r['version'],
                            '导出中文原版和英文版的试玩链接、出包'))
    else:
        editors = find_creator.installed_editors()
        rows.append(row('Cocos Creator', editors, True, '、'.join(e['version'] for e in editors) or '一个都没找到',
                        '请用户装 Cocos Dashboard，再按工程的版本下载编辑器', '导出试玩链接和出包'))
    return rows


def say(rows):
    lines = []
    for r in rows:
        if r['ok']:
            lines.append('可以  %s：%s' % (r['name'], r['detail']))
        else:
            lines.append('%s  %s：%s。影响：%s。怎么补：%s' % ('缺（必须）' if r['required'] else '缺（建议）', r['name'],
                                                    r['detail'], r['affects'], r['fix']))
    missing = [r['name'] for r in rows if r['required'] and not r['ok']]
    lines.append('结论：' + ('必须的都有，可以开工。' if not missing else '缺 %s。用大白话告诉用户缺什么、影响什么，问一句能不能装；'
                                                          '用户同意后由你来装，装好再跑一次本脚本。缺的东西不影响的步骤先接着做。'
                                                          % '、'.join(missing)))
    return '\n'.join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description='查这台电脑有没有英化流程要用的东西（只读，不装任何东西）')
    ap.add_argument('--project', type=Path, help='这款游戏的 Cocos 工程（有 assets/ 的那一层）')
    ap.add_argument('--quick', action='store_true', help='不启动浏览器试一次（几秒钟就完）')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    if a.project and not a.project.exists():
        print('输入有问题：找不到 %s' % a.project)
        return 2
    rows = collect(a.project, a.quick)
    print(json.dumps(rows, ensure_ascii=False, indent=2) if a.json else say(rows))
    return 1 if any(r['required'] and not r['ok'] for r in rows) else 0


if __name__ == '__main__':
    sys.exit(main())
