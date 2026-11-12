#!/usr/bin/env python3
"""Open Chrome for a completed English art trial or a verified test ZIP.

The server is already running. This entry only reads existing evidence and the
live phone shell. It does not build, recapture a page, or run a regression.
"""
import argparse
import http.client
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parents[1]
sys.path.insert(0, str(SKILLS / 'remake-core' / 'scripts'))
sys.path.insert(0, str(SKILLS / 'cocos-game-check' / 'package-check' / 'scripts'))

from delivery_continuation import failure
import art_check_record
import audit_native_startup_renderer as startup_renderer
import browser_slots
import chinese_audit
import preview_chrome
import stage_timer
from build_playtest_h5 import object_of, render, required_text, validate_package, validate_plan, write_html
from check_known_issues import tree_sha
from tiktok_finalize import SOURCE_RECORD, check_prepared_native
from verify_delivery_preview import verify_preview
from serve_preview import PLAYTEST_PATH


def read_object(path, label):
    return object_of(json.loads(path.read_text(encoding='utf-8')), label)


def art_trial(project, slot):
    events, bad = stage_timer.load(project)
    timeline = stage_timer.Timeline(events, time.time(), bad)
    route = next((e.get('route') for e in timeline.events if e['ev'] == 'run_start'), None)
    if (route != 'source' or timeline.aborted_at is not None
            or not timeline.stages or timeline.stages[-1]['n'] != 3
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
    from ad_standard_scope import requirement
    if requirement(project, 'new')['required']:
        from ad_nodes_gate import check_project as check_ad_nodes
        ad_result = check_ad_nodes(project, native=native, stage='trial')
        if not ad_result.get('passed'):
            raise ValueError('六标准广告制作/新增UI尚未完成：' + '; '.join(ad_result.get('problems') or ['unknown']))
    native_sha, native_record = check_prepared_native(project, native)
    source_record = project / SOURCE_RECORD
    if (native_sha != trial['native_tree_sha256']
            or chinese_audit.sha_file(native_record) != trial.get('native_preparation_sha256')
            or chinese_audit.sha_file(source_record) != trial.get('source_record_sha256')
            or chinese_audit.sha_file(audit / 'check-result.json') != trial.get('check_result_sha256')
            or chinese_audit.export_manifest(export)['sha256'] != trial['export_manifest_sha256']):
        raise ValueError('候选或已通过的输入已变化。核对受影响项后重新准备当前候选。')
    return tree_sha(export), f"english:{trial['export_manifest_sha256']}:{native_sha}"


def packaged_trial(slot, url, delivery):
    record = read_object(delivery, '测试包交付回执')
    preview = object_of(record.get('preview'), '同版试玩回执')
    web_sha = required_text(preview, 'web_tree_sha256', '同版试玩回执')
    if preview.get('slot_id') != slot['id']:
        raise ValueError('当前试玩服务与最终交付回执不一致。')
    archive = Path(required_text(record, 'archive', '测试包交付回执')).resolve()
    package = validate_package(record, archive, {'preview_url': url, 'web_tree_sha256': web_sha})
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
    return web_sha, package


def serve_checklist(slot, url, html):
    path = browser_slots.playtest_html_path(slot['id'])
    previous = path.read_text(encoding='utf-8') if path.is_file() else None
    write_html(path, html)
    try:
        parts = urlsplit(url)
        connection = http.client.HTTPConnection(parts.hostname, parts.port, timeout=5)
        try:
            connection.request('GET', PLAYTEST_PATH)
            response = connection.getresponse()
            if response.status != 200 or response.read() != html.encode('utf-8'):
                raise ValueError('同页清单尚不可用。用当前 Skill 重开已核准的同版服务，再交接。')
        finally:
            connection.close()
    except (OSError, ValueError, http.client.HTTPException):
        if previous is None:
            path.unlink(missing_ok=True)
        else:
            write_html(path, previous)
        raise
    return url.rstrip('/') + PLAYTEST_PATH


def finish_stage(project, kind, trial_identity):
    if kind == 'art':
        report = stage_timer.call(project, 'done', '--stage', '3', '--summary',
            '核对本轮美工、中文专项、同版候选和试玩清单。有效检查沿用。',
            '--next', '用户按 H5 试玩。AI 继续处理反馈和适用回归。')
        stage_timer.call(project, 'publish', trial_identity)
    else:
        stage_timer.call(project, 'mark', '交付', '--once')
        report = stage_timer.call(project, 'done', '--stage', '5', '--summary',
            '核对本次实际 ZIP、分包体积、适用回归证据及同版试玩清单。',
            '--next', '用户收包，可在同页选择本轮改动快查。')
    return report


def handoff(project, url, kind, plan, delivery=None, *, no_browser=False):
    project = project.resolve()
    matches = [s for s in browser_slots.slots() if s.get('kind') == 'preview'
               and s.get('url') == url and s.get('project') == str(project)
               and s.get('keep') and s.get('dir')]
    if len(matches) != 1:
        raise ValueError('找不到本工程唯一的保留快照。先在内部准备同版预览。')
    slot = matches[0]
    plan = validate_plan(plan)
    if plan['preview_url'] != url or plan['mode'] not in ('trial', 'package'):
        raise ValueError('需要本次同版入口的试玩计划。')
    phase = 3 if kind == 'art' else 5
    events, bad = stage_timer.load(project)
    timeline = stage_timer.Timeline(events, time.time(), bad)
    if (timeline.cur and timeline.cur['n'] == phase
            and any(s['end'] is None and s['entry'] == timeline.entry() for s in timeline.steps)):
        raise ValueError(f'第 {phase} 阶段还有开放步骤。等实际检查结束后再交接。')
    package = None
    trial_identity = None
    if kind == 'art':
        if plan['mode'] != 'trial':
            raise ValueError('美工试玩的计划使用 trial 模式。')
        web_sha, trial_identity = art_trial(project, slot)
        label = '英文美工试玩'
    else:
        if delivery is None:
            raise ValueError('最终交付需要 prepare_delivery.py 对本次实际 ZIP 生成的交付回执。')
        web_sha, package = packaged_trial(slot, url, delivery)
        plan['mode'] = 'package'
        label = '测试包同版试玩'
    if plan['web_tree_sha256'] != web_sha:
        raise ValueError('试玩清单与当前候选不是同一 Web 构建。')
    preview = verify_preview(url, web_sha, require_ad_simulator=plan['require_ad_simulator'])
    if preview['slot_id'] != slot['id']:
        raise ValueError('试玩服务在核对过程中被替换。')
    observation = None
    if timeline.cur and timeline.cur['n'] == phase:
        try:
            observation = stage_timer.begin_observation(project, '同页试玩清单与入口核对',
                                                        node_id='preview/combined-handoff')
        except (OSError, ValueError):
            pass
    ready = False
    try:
        html = render(plan, package, ad_simulator=preview['ad_simulator'])
        checklist = serve_checklist(slot, url, html)
        ready = True
    finally:
        if observation:
            try:
                stage_timer.finish_observation(observation, state='completed' if ready else 'failed',
                                               exit_code=0 if ready else 1)
            except (OSError, ValueError):
                pass
    try:
        stage_report = finish_stage(project, kind, trial_identity)
        total_report = stage_timer.call(project, 'report', '--all')
    except Exception as error:
        stage_report = f'阶段用时未记录完整。{error}'
        total_report = ''
    browser = preview_chrome.browser_request(checklist, explicit_open=True, no_browser=no_browser,
                                             window_size=(1180, 900))
    return {'status': 'handoff_ready', 'kind': kind, 'label': label, 'playtest_url': checklist,
            'markdown_link': f'[{label}与清单]({checklist})', 'web_tree_sha256': web_sha,
            'stage_report': stage_report, 'timing_report': total_report, 'browser': browser}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--preview-url', required=True, help='current retained local candidate')
    parser.add_argument('--kind', choices=('art', 'package'), required=True)
    parser.add_argument('--plan', type=Path, required=True, help='current playtest checklist plan JSON')
    parser.add_argument('--delivery-record', type=Path, help='required for package handoff')
    parser.add_argument('--no-browser', action='store_true', help='reuse a verified checklist window without requesting another Chrome window')
    args = parser.parse_args(argv)
    if (args.kind == 'package') != (args.delivery_record is not None):
        parser.error('只有最终测试包交接使用且必须提供 --delivery-record。')
    try:
        plan = read_object(args.plan, '试玩计划')
        result = handoff(args.project, args.preview_url, args.kind, plan, args.delivery_record,
                         no_browser=args.no_browser)
    except (OSError, KeyError, TypeError, ValueError, http.client.HTTPException) as error:
        print(json.dumps(failure(error, stage='preview'), ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
