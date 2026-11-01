#!/usr/bin/env python3
"""English entry for the shared preview server; an English trial link must pass the Chinese check first.

v7.8 (总表 B21 / B30 F): the shared server is remake-core/scripts/serve_preview.py in this pack (it runs the trial-link
smoke before a --keep link is printed). The old target cocos-game-core/scripts/ is not shipped in the English pack,
so this entry used to stop with "Missing modular cocos-game-core preview server".

Chinese check before every English trial link (Saul 2026-11-01, 总表第 28 条). Garden Guardians showed Saul a wave
warning with "高波来袭！" drawn in one slice of a Spine atlas while the old image record said "no Chinese". A server
a person will play -- --open, --keep or --idle-minutes 0 -- now starts only when
  1. it serves a private copy (--snapshot), and
  2. chinese_audit.py check passes on that very export (the same checker as `chinese_audit.py check --export`), and
  3. the copy the shared server makes is byte-for-byte the export that was checked (a build still running fails here).
Every such link is written to <project>/docs/english/chinese-audit/trial-links.json (export, snapshot, check result).
Internal QA servers (none of the three flags, or --raw) start as before.
  --chinese-original  the stage-1 Chinese original: no Chinese check (it is the Chinese game on purpose)
  --draft             Saul asked to see an unfinished English build: the link starts although the check fails; the
                      open problems are printed for the reply, and the link is never called "checked"
  --project <工程>     the English project; not needed when the export is <工程>/build/<platform>
Refused (exit 1, no server): check not passed without --draft, no --snapshot, English project not found, the export
changed between the check and the copy.
"""
from pathlib import Path
import runpy
import shutil
import sys

HERE = Path(__file__).resolve().parent
WRAPPER_ONLY = ('--chinese-original', '--draft')
HELP = ('英化入口自己的参数（其余见下面共用服务的参数）：\n'
        '  --chinese-original  第 1 阶段的中文原版链接，不做中文专项检查\n'
        '  --draft             Saul 要先看没做完的英文版：中文专项检查没过也起，列出没处理的问题，不能叫「检查过」\n'
        '  --project <工程>     英化工程（导出在 <工程>/build/web-mobile 时可以不写）\n'
        '给人试玩的链接（--open、--keep 或 --idle-minutes 0）必须带 --snapshot，并先过 chinese_audit.py check。\n')


def option(argv, name):
    for i, a in enumerate(argv):
        if a == name:
            return argv[i + 1] if i + 1 < len(argv) else None
        if a.startswith(name + '='):
            return a.split('=', 1)[1]
    return None


def for_a_person(argv):
    """A link someone will open: a window is requested, it is kept, or it never stops by itself."""
    if '--raw' in argv:
        return False
    idle = option(argv, '--idle-minutes')
    try:
        forever = idle is not None and float(idle) == 0
    except ValueError:
        forever = False
    return '--open' in argv or '--keep' in argv or forever


def find_project(directory, given):
    if given:
        p = Path(given).expanduser().resolve()
        return p if (p / 'assets').is_dir() else None
    d = Path(directory).expanduser().resolve()
    for p in [d] + list(d.parents)[:3]:
        if (p / 'assets').is_dir() and (p / 'docs' / 'english').is_dir():
            return p
    return None


def refuse(message):
    print('不起英文试玩服务：' + message, file=sys.stderr, flush=True)
    raise SystemExit(1)


def gate(argv, say=print):
    """Return (arguments for the shared server, snapshot check or None); exit 1 when the link is refused."""
    draft, original = '--draft' in argv, '--chinese-original' in argv
    argv = [a for a in argv if a not in WRAPPER_ONLY]
    if original:
        say('中文原版链接：不做中文专项检查（这是中文原版，不是英化结果）。')
        return argv, None
    if not for_a_person(argv):
        return argv, None
    directory = option(argv, '--directory')
    if not directory or not Path(directory).expanduser().is_dir():
        return argv, None                                   # the shared server reports a bad --directory
    if '--snapshot' not in argv:
        refuse('英文试玩链接要带 --snapshot：交给人试玩的必须是查过的那一份，构建再跑也改不了它')
    export = Path(directory).expanduser().resolve()
    project = find_project(export, option(argv, '--project'))
    if project is None:
        refuse('找不到英化工程：加 --project <英化工程>（导出在 <工程>/build/web-mobile 时可以不写）。'
               '第 1 阶段的中文原版链接加 --chinese-original')
    sys.path.insert(0, str(HERE))
    import chinese_audit as CA
    out = CA.resolve_out(project, None)
    try:
        CA.guard_out(out, project, export)
        result = CA.evaluate(project, out, export, None)
    except (CA.Usage, CA.Refused) as exc:
        refuse('中文专项检查跑不了：%s' % exc)
    CA.write_json(out / 'check-result.json', result)
    problems = result['problems']
    if problems:
        say('中文专项检查没通过，%d 条问题（全部在 %s）：' % (len(problems), out / 'check-result.json'))
        for row in problems[:20]:
            say('  [%s] %s → %s' % (row['code'], row['message'], row['fix']))
        if len(problems) > 20:
            say('  ……还有 %d 条' % (len(problems) - 20))
        if not draft:
            refuse('先处理上面的问题：scan --project <工程> --export <这份导出>，用 sheet 看清要复核的几项、逐个 review，'
                   '再 check；通过了再起链接（%s）' % (HERE / 'chinese_audit.py'))
        say('--draft：Saul 要先看没做完的英文版。回复里写明这一版没过中文专项检查、上面这些还没处理，不能说「检查过」。')
    else:
        say('中文专项检查：通过（%s）。' % (out / 'check-result.json'))
    expected = (result.get('export') or {}).get('manifest_sha256')
    checked = CA.sha_file(out / 'check-result.json')
    name = option(argv, '--name') or ''

    def verify(snapshot_dir):
        got = CA.export_manifest(snapshot_dir)['sha256']
        if got != expected:
            shutil.rmtree(str(snapshot_dir), ignore_errors=True)
            refuse('试玩快照和刚查过的导出不一样（查完以后导出又变了，可能构建还在跑）。等构建完，'
                   '重新 scan --export、check，再起链接')
        log = out / 'trial-links.json'
        rows = CA.read_json(log, [])
        rows = rows if isinstance(rows, list) else []
        rows.append({'time': CA.now(), 'name': name, 'export': str(export), 'export_manifest_sha256': expected,
                     'snapshot': str(snapshot_dir), 'snapshot_manifest_sha256': got, 'check_result_sha256': checked,
                     'passed': not problems, 'draft': bool(problems), 'open_problems': len(problems)})
        CA.write_json(log, rows)
        say('试玩快照和查过的导出一字不差，记在 %s。' % log)
    return argv, verify


def main(argv):
    root = HERE.parents[1]
    target = next((p for p in (root / 'remake-core/scripts/serve_preview.py', root / 'cocos-game-core/scripts/serve_preview.py')
                   if p.is_file()), None)
    if target is None:
        raise SystemExit('Missing shared preview server remake-core/scripts/serve_preview.py')
    sys.path.insert(0, str(target.parent))
    if '-h' in argv or '--help' in argv:
        print(HELP, flush=True)
    argv, verify = gate(argv)
    if verify is not None:
        import browser_slots                                # the shared server imports this same module object
        make_copy = browser_slots.snapshot

        def checked_snapshot(source):
            dest = make_copy(source)
            verify(dest)
            return dest
        browser_slots.snapshot = checked_snapshot
    sys.argv = [str(target)] + argv
    runpy.run_path(str(target), run_name='__main__')


if __name__ == '__main__':
    main(sys.argv[1:])
