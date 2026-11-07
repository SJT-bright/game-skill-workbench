#!/usr/bin/env python3
"""English entry for the shared preview server. A formal link requires the current pre-trial evidence.

v7.8 (总表 B21 / B30 F): the shared server is remake-core/scripts/serve_preview.py in this pack (it runs the trial-link
smoke before a --keep link is printed). The old target cocos-game-core/scripts/ is not shipped in the English pack,
so this entry used to stop with "Missing modular cocos-game-core preview server".

Chinese check before every English trial link (Saul 2026-11-01, 总表第 28 条). Garden Guardians showed Saul a wave
warning with "高波来袭！" drawn in one slice of a Spine atlas while the old image record said "no Chinese". A server
a person will play -- --open, --keep or --idle-minutes 0 -- now starts only when
  1. it serves a private copy (--snapshot), and
  2. chinese_audit.py check passes on that very export (the same checker as `chinese_audit.py check --export`), and
  3. the current art receipt passed and the source record includes the Sprite ratio check,
  4. the Web export and prepared Native are covered by image-review.json, and
  5. the copy the shared server makes is byte-for-byte the export that was checked.
Every such link is written to <project>/docs/english/chinese-audit/trial-links.json (export, snapshot, check result).
Internal QA servers (none of the three flags, or --raw) start as before.
  --chinese-original  the stage-1 Chinese original: no Chinese check (it is the Chinese game on purpose); with
                      --project the link time is recorded once as `stage_timer.py mark 中文原版链接`
  --draft             Saul asked to see an unfinished English build: the link starts although the check fails; the
                      open problems are printed for the reply, and the link is never called "checked"
  --project <工程>     the English project; not needed when the export is <工程>/build/<platform>
简化.11.9 (用时汇报): every English trial link for a person is also recorded as `stage_timer.py link <N>` and the
previous round's timing it prints is shown for the reply. N counts the different exports handed out (trial-links.json,
export_manifest_sha256): serving the same export again (server stopped, Saul looks once more) is not a new round, and
stage_timer does not record a round number twice, so a manual `T link N` is not doubled. A timing problem is only a
warning; the link starts anyway.
Refused (exit 1, no server): check not passed without --draft, no --snapshot, English project not found, the export
changed between the check and the copy.
"""
from pathlib import Path
import argparse
import runpy
import shutil
import sys

HERE = Path(__file__).resolve().parent
HELP = ('英化入口自己的参数（其余见下面共用服务的参数）：\n'
        '  --chinese-original  第 1 阶段的中文原版链接，不做中文专项检查；带 --project 时记下用时「中文原版链接」\n'
        '  --draft             Saul 要先看没做完的英文版：中文专项检查没过也起，列出没处理的问题，不能叫「检查过」\n'
        '  --project <工程>     英化工程（导出在 <工程>/build/web-mobile 时可以不写）\n'
        '  --native <目录>     试玩前已处理的同版 TikTok Native 构建目录，正式英文试玩必填\n'
        '  --reopen            重开已通过的同版试玩，只核对既有记录\n'
        '正式英文试玩先核对美术回执、Sprite 比例记录、中文专项检查和两个导出的逐图复核记录，必须带 --snapshot。\n'
        '英文试玩链接自动记用时（stage_timer.py link <第几轮>），打印的上一轮用时贴在新链接那条回复最后。\n')


def timing(project, *args):
    """stage_timer.py <args> for this project; a problem is a warning line, never a refusal (用时汇报不挡流程)."""
    try:
        sys.path.insert(0, str(HERE))
        import stage_timer
        return stage_timer.call(project, *args)
    except Exception as exc:  # noqa: BLE001
        return '用时没记上（%s）：%r' % (' '.join(map(str, args)), exc)


def round_number(rows):
    """rows of trial-links.json -> the round of the last row: different exports handed out, in order."""
    n, last = 0, None
    for row in rows:
        sha = row.get('export_manifest_sha256') if isinstance(row, dict) else None
        if sha != last:
            n, last = n + 1, sha
    return n


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


def pretrial_records(project, export, native):
    """Verify prepared evidence only. Source scans, PNG conversion and OCR run before this entry."""
    import audit_image_review_record as images
    import tiktok_finalize as finalize
    from tiktok_finalize_steps import png

    problems = finalize.check_trial_source(project, 'localize')
    if problems:
        refuse('\n'.join(row['message'] for row in problems))
    if native is None:
        refuse('正式英文试玩需要 --native <同版已处理的 TikTok 构建目录>，以核对实际包内图片的复核记录。')
    native = native.expanduser().resolve()
    if not all((native / name).is_file() for name in ('game.js', 'game.json', 'project.config.json')):
        refuse('找不到实际 TikTok Native 构建目录：%s' % native)
    try:
        native_sha, native_record = finalize.check_prepared_native(project, native)
    except (OSError, ValueError) as error:
        refuse(str(error))
    prepared = png.check_prepared({'root': native, 'project': project})
    if prepared['blocks']:
        refuse('\n'.join(row['message'] for row in prepared['blocks']))
    record = project / 'docs/english/image-review.json'
    try:
        review = images.check(images.directory_items([export, native]), record)
    except (OSError, ValueError) as error:
        refuse('读取待试玩图片失败：%s' % error)
    if not review['passed']:
        refuse('逐图复核未通过，请在试玩前用 audit_image_review_record.py write --directory <Web> '
               '--directory <已处理的 Native> 生成记录。\n' + '\n'.join(review['problems'][:10]))
    return native, native_sha, native_record, record, project / finalize.SOURCE_RECORD, review['distinct_images']


def gate(argv, say=print):
    """Return (arguments for the shared server, snapshot check or None); exit 1 when the link is refused."""
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument('--draft', action='store_true')
    parser.add_argument('--chinese-original', action='store_true')
    parser.add_argument('--reopen', action='store_true')
    parser.add_argument('--native', type=Path)
    opts, argv = parser.parse_known_args(argv)
    if opts.reopen and (opts.draft or opts.chinese_original or not for_a_person(argv)):
        parser.error('--reopen 只能用于重开已通过的正式英文试玩')
    if opts.chinese_original:
        say('中文原版链接：不做中文专项检查（这是中文原版，不是英化结果）。')
        given = option(argv, '--project')
        if given and for_a_person(argv):
            project = Path(given).expanduser().resolve()
            if project.is_dir():
                say(timing(project, 'mark', '中文原版链接', '--once'))
            else:
                say('用时没记上：--project 不是文件夹（%s），中文原版链接照样起。' % project)
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
    sys.path.insert(0, str(HERE.parents[1] / 'remake-core/scripts'))
    import art_receipt
    sys.path.insert(0, str(HERE))
    import chinese_audit as CA
    export_sha = CA.export_manifest(export)['sha256']
    art = art_receipt.check(project, board='localize', capture_build=export)
    if art['level'] != 'ok' or art.get('status') != 'pass':
        refuse('需要当前正式美术通过回执。' + art['message'])
    art_path = art_receipt.receipt_path(project)
    out = CA.resolve_out(project, None)
    try:
        CA.guard_out(out, project, export)
        result = None if opts.reopen else CA.evaluate(project, out, export, None)
    except (CA.Usage, CA.Refused) as exc:
        refuse('中文专项检查跑不了：%s' % exc)
    check_path = out / 'check-result.json'
    log = out / 'trial-links.json'
    if result is not None:
        if (result.get('export') or {}).get('manifest_sha256') != export_sha:
            refuse('Web 导出在验收核对期间发生变化，请等构建结束后重新核对。')
        previous = CA.read_json(check_path)
        same_pass = (result.get('passed') is True and isinstance(previous, dict) and previous.get('passed') is True
                     and CA.sha_json({k: v for k, v in previous.items() if k != 'checked_at'})
                     == CA.sha_json({k: v for k, v in result.items() if k != 'checked_at'}))
        if not same_pass:
            CA.write_json(check_path, result)
    elif not check_path.is_file():
        refuse('缺同版已通过的中文专项检查记录。')
    problems = result['problems'] if result is not None else []
    if problems:
        say('中文专项检查没通过，%d 条问题（全部在 %s）：' % (len(problems), out / 'check-result.json'))
        for row in problems[:20]:
            say('  [%s] %s → %s' % (row['code'], row['message'], row['fix']))
        if len(problems) > 20:
            say('  ……还有 %d 条' % (len(problems) - 20))
        if not opts.draft:
            refuse('先处理上面的问题：scan --project <工程> --export <这份导出>，用 sheet 看清要复核的几项、逐个 review，'
                   '再 check；通过了再起链接（%s）' % (HERE / 'chinese_audit.py'))
        say('--draft：Saul 要先看没做完的英文版。回复里写明这一版没过中文专项检查、上面这些还没处理，不能说「检查过」。')
    elif result is not None:
        say('中文专项检查：通过（%s）。' % check_path)
    bindings = {'art_receipt_sha256': art_path, 'check_result_sha256': check_path}
    native = native_sha = None
    if not opts.draft:
        native, native_sha, native_record, record, source_record, distinct_images = pretrial_records(
            project, export, opts.native)
        bindings.update(image_review_sha256=record, source_record_sha256=source_record,
                        native_preparation_sha256=native_record)
        from verify_native_zip import native_directory_digest
    evidence = {key: CA.sha_file(path) for key, path in bindings.items()}
    if opts.reopen:
        rows = CA.read_json(log, [])
        if not isinstance(rows, list) or not any(
            isinstance(row, dict) and row.get('passed') is True and row.get('draft') is False
            and row.get('export_manifest_sha256') == row.get('snapshot_manifest_sha256') == export_sha
            and row.get('native_tree_sha256') == native_sha
            and all(row.get(key) == digest for key, digest in evidence.items())
            for row in rows
        ):
            refuse('找不到与当前导出和回执一致的已通过试玩记录。请回到试玩前阶段核对变更。')
        say('同版试玩已通过的记录核对一致。')
    elif not opts.draft:
        say('试玩前检查通过：当前美术回执、Sprite 比例记录和 %d 张不同图片的复核记录。' % distinct_images)
    name = option(argv, '--name') or ''
    if not option(argv, '--project'):
        argv += ['--project', str(project)]

    def verify(snapshot_dir):
        got = CA.export_manifest(snapshot_dir)['sha256']
        if got != export_sha:
            shutil.rmtree(str(snapshot_dir), ignore_errors=True)
            refuse('试玩快照和刚查过的导出不一样（查完以后导出又变了，可能构建还在跑）。等构建完，'
                   '重新 scan --export、check，再起链接')

        def record_ready_trial():
            if any(not path.is_file() or CA.sha_file(path) != evidence[key] for key, path in bindings.items()):
                refuse('试玩服务准备期间验收记录已变，请重新核对后再起链接。')
            if native is not None and native_directory_digest(native) != native_sha:
                refuse('试玩服务准备期间 Native 已变，请回到试玩前核对候选。')
            rows = CA.read_json(log, [])
            rows = rows if isinstance(rows, list) else []
            same_export = bool(rows) and isinstance(rows[-1], dict) and rows[-1].get('export_manifest_sha256') == export_sha
            rows.append({'time': CA.now(), 'name': name, 'export': str(export), 'export_manifest_sha256': export_sha,
                         'snapshot': str(snapshot_dir), 'snapshot_manifest_sha256': got, 'native': str(native) if native else None,
                         'native_tree_sha256': native_sha,
                         'passed': not problems and not opts.draft, 'draft': opts.draft,
                         'open_problems': len(problems), **evidence})
            CA.write_json(log, rows)
            say('试玩快照和查过的导出一字不差，记在 %s。' % log)
            if same_export:
                say('（和上一个链接是同一份导出，不算新一轮试玩，用时不另记）')
            else:
                say(timing(project, 'link', round_number(rows)))

        return record_ready_trial
    return argv, verify


def main(argv):
    root = HERE.parents[1]
    target = root / 'remake-core/scripts/serve_preview.py'
    if not target.is_file():
        raise SystemExit('Missing shared preview server remake-core/scripts/serve_preview.py')
    sys.path.insert(0, str(target.parent))
    if '-h' in argv or '--help' in argv:
        print(HELP, flush=True)
    original = '--chinese-original' in argv
    argv, verify = gate(argv)
    shared = runpy.run_path(str(target))
    shared['main'](argv, verify_snapshot=verify, chinese_original=original)


if __name__ == '__main__':
    main(sys.argv[1:])
