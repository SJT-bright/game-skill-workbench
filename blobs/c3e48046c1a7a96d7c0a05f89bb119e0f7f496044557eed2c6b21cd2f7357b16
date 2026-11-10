#!/usr/bin/env python3
"""Open Chrome for a completed English art trial or a verified test ZIP.

The server is already running. This entry only reads existing evidence and the
live phone shell. It does not build, recapture a page, or run a regression.
"""
import argparse
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parents[1]
sys.path.insert(0, str(SKILLS / 'remake-core' / 'scripts'))
sys.path.insert(0, str(SKILLS / 'cocos-game-check' / 'package-check' / 'scripts'))

import art_check_record
import audit_native_startup_renderer as startup_renderer
import browser_slots
import chinese_audit
import preview_chrome
import stage_timer
from build_playtest_h5 import object_of, required_text, validate_package
from check_known_issues import tree_sha
from tiktok_finalize import SOURCE_RECORD, check_prepared_native
from verify_delivery_preview import verify_preview


def read_object(path, label):
    return object_of(json.loads(path.read_text(encoding='utf-8')), label)


def art_trial(project, slot):
    events, bad = stage_timer.load(project)
    timeline = stage_timer.Timeline(events, time.time(), bad)
    route = next((e.get('route') for e in timeline.events if e['ev'] == 'run_start'), None)
    if (route != 'source' or timeline.cur or timeline.aborted_at is not None
            or not timeline.stages or timeline.stages[-1]['n'] != 3
            or timeline.stages[-1]['end'] is None
            or any(s['n'] >= 4 for s in timeline.stages)):
        raise ValueError('美工试玩只在本轮第 3 阶段完成时交接。回归和写包途中继续用内部检测入口。')

    audit = chinese_audit.resolve_out(project, None)
    rows = chinese_audit.read_json(audit / 'trial-links.json', [])
    if not isinstance(rows, list):
        raise ValueError('没有可核对的同版美工试玩记录。')
    trial = next((r for r in reversed(rows) if isinstance(r, dict)
                  and r.get('snapshot') == slot['dir']
                  and r.get('timing_run_id') == timeline.run_id
                  and r.get('passed') is True and r.get('draft') is False
                  and r.get('open_problems') == 0), None)
    if trial is None:
        raise ValueError('当前快照尚无本轮美工试玩的通过记录。')
    art = art_check_record.check(project)
    if art['level'] != 'ok':
        raise ValueError(art['message'])
    native = Path(required_text(trial, 'native', '美工试玩记录'))
    export = Path(required_text(trial, 'export', '美工试玩记录'))
    native_sha, native_record = check_prepared_native(project, native)
    source_record = project / SOURCE_RECORD
    if (native_sha != trial['native_tree_sha256']
            or chinese_audit.sha_file(native_record) != trial.get('native_preparation_sha256')
            or chinese_audit.sha_file(source_record) != trial.get('source_record_sha256')
            or chinese_audit.sha_file(audit / 'check-result.json') != trial.get('check_result_sha256')
            or chinese_audit.export_manifest(export)['sha256'] != trial['export_manifest_sha256']):
        raise ValueError('候选或已通过的输入已变化。核对受影响项后重新准备当前候选。')
    return tree_sha(export)


def packaged_trial(slot, url, delivery):
    record = read_object(delivery, '测试包交付回执')
    preview = object_of(record.get('preview'), '同版试玩回执')
    web_sha = required_text(preview, 'web_tree_sha256', '同版试玩回执')
    if preview.get('slot_id') != slot['id']:
        raise ValueError('当前试玩服务与最终交付回执不一致。')
    archive = Path(required_text(record, 'archive', '测试包交付回执')).resolve()
    validate_package(record, archive, {'preview_url': url, 'web_tree_sha256': web_sha})
    size = record['fresh_size_check']
    checked = read_object(Path(required_text(size, 'report', '本次 ZIP 体积回执')), 'ZIP 检查结果')
    if (checked.get('passed') is not True or checked.get('sha256') != size['sha256']
            or checked.get('run_id') != size['run_id'] or checked.get('archive') != str(archive)):
        raise ValueError('缺少与实际 ZIP 一致的本次分包体积检查结果。')
    startup = object_of(record.get('final_startup_runtime'), '最终 Native 启动回执')
    native = Path(required_text(record, 'native', '测试包交付回执'))
    if (startup.get('passed') is not True or not native.is_dir()
            or startup.get('native_tree_sha256') != startup_renderer.digest(startup_renderer.tree(native))):
        raise ValueError('最终 Native 的有效启动记录缺失或候选已变化。')
    return web_sha


def handoff(project, url, kind, delivery=None, *, no_browser=False):
    project = project.resolve()
    matches = [s for s in browser_slots.slots() if s.get('kind') == 'preview'
               and s.get('url') == url and s.get('project') == str(project)
               and s.get('keep') and s.get('dir')]
    if len(matches) != 1:
        raise ValueError('找不到本工程唯一的保留快照。先在内部准备同版预览。')
    slot = matches[0]
    if kind == 'art':
        web_sha = art_trial(project, slot)
        label = '英文美工试玩'
    else:
        if delivery is None:
            raise ValueError('最终交付需要 prepare_delivery.py 对本次实际 ZIP 生成的交付回执。')
        web_sha = packaged_trial(slot, url, delivery)
        label = '测试包同版试玩'
    preview = verify_preview(url, web_sha)
    if preview['slot_id'] != slot['id']:
        raise ValueError('试玩服务在核对过程中被替换。')
    size = slot.get('phone_size') or (390, 844)
    browser = preview_chrome.browser_request(url, explicit_open=True, no_browser=no_browser, phone_size=size)
    return {'status': 'handoff_ready', 'kind': kind, 'label': label, 'preview': preview, 'browser': browser}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--preview-url', required=True, help='current retained local candidate')
    parser.add_argument('--kind', choices=('art', 'package'), required=True)
    parser.add_argument('--delivery-record', type=Path, help='required for package handoff')
    parser.add_argument('--no-browser', action='store_true', help='only verify the handoff when no window is requested')
    args = parser.parse_args(argv)
    if (args.kind == 'package') != (args.delivery_record is not None):
        parser.error('只有最终测试包交接使用且必须提供 --delivery-record。')
    try:
        result = handoff(args.project, args.preview_url, args.kind, args.delivery_record, no_browser=args.no_browser)
    except (OSError, KeyError, TypeError, ValueError) as error:
        print(json.dumps({'status': 'refuse', 'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
