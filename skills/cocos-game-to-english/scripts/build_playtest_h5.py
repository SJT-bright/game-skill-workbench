#!/usr/bin/env python3
"""Build a standalone, version-bound playtest route from a reviewed game inventory."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile


HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / 'assets' / 'playtest-checklist.html'
MARKER = '/* CHECKLIST_DATA */'
CORE_TOOLS = HERE.parents[1] / 'remake-core' / 'scripts'
CHECK_TOOLS = HERE.parents[1] / 'cocos-game-check' / 'package-check' / 'scripts'
SCHEMA = 'english-playtest-plan.v1'


def object_of(value, label):
    if not isinstance(value, dict):
        raise ValueError(f'{label} 应为对象')
    return value


def required_text(row, key, label):
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} 缺少 {key}')
    return value.strip()


def nonempty_rows(value, label):
    if not isinstance(value, list) or not value:
        raise ValueError(f'{label} 不能为空')
    return value


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def validate_plan(plan):
    plan = object_of(plan, '试玩计划')
    if plan.get('schema') != SCHEMA:
        raise ValueError(f'试玩计划应使用 {SCHEMA}')
    mode = plan.get('mode')
    if mode not in ('trial', 'package', 'share'):
        raise ValueError('mode 应为 trial、package 或 share')
    web_sha = required_text(plan, 'web_tree_sha256', '试玩计划')
    if not re.fullmatch(r'[a-f0-9]{64}', web_sha):
        raise ValueError('缺本版 Web 构建指纹')
    require_ad_simulator = plan.get('require_ad_simulator', False)
    if type(require_ad_simulator) is not bool:
        raise ValueError('require_ad_simulator 应为布尔值')

    inventory = {}
    for entry in nonempty_rows(plan.get('inventory'), '页面与操作盘点'):
        entry = object_of(entry, '盘点项')
        identifier = required_text(entry, 'id', '盘点项')
        if identifier in inventory:
            raise ValueError(f'盘点项 ID 重复：{identifier}')
        inventory[identifier] = {
            key: required_text(entry, key, identifier)
            for key in ('page', 'state', 'control', 'evidence')
        }

    steps, step_ids, coverage = [], set(), set()
    for step in nonempty_rows(plan.get('steps'), '试玩路线'):
        step = object_of(step, '路线步骤')
        identifier = required_text(step, 'id', '路线步骤')
        if identifier in step_ids:
            raise ValueError(f'步骤 ID 重复：{identifier}')
        step_ids.add(identifier)
        page = required_text(step, 'page', identifier)
        enter = required_text(step, 'enter', identifier)
        checks = []
        for check in nonempty_rows(step.get('checks'), f'{page} 的测试点'):
            check = object_of(check, page)
            covers = nonempty_rows(check.get('covers'), f'{page} 的覆盖 ID')
            for item_id in covers:
                if not isinstance(item_id, str) or item_id not in inventory:
                    raise ValueError(f'{page} 引用了盘点中不存在的入口：{item_id}')
                if item_id in coverage:
                    raise ValueError(f'路线重复测试同一项：{item_id}')
                coverage.add(item_id)
            basis = check.get('basis')
            if basis not in ('verified_fix', 'verified_behavior', 'strict_requirement'):
                raise ValueError(f'{page} 的检测点须标明已复验修复、已实测或严格要求')
            item = {'action': required_text(check, 'action', page),
                    'expected': required_text(check, 'expected', page)}
            if basis == 'verified_fix':
                item['problem'] = required_text(check, 'problem', page)
                required_text(check, 'problem_evidence', page)
            elif 'problem' in check or 'problem_evidence' in check:
                raise ValueError(f'{page} 只可为有复现记录的已复验修复展示旧现象')
            checks.append(item)
        steps.append({'id': identifier, 'page': page, 'enter': enter, 'checks': checks})
    if missing := sorted(inventory.keys() - coverage):
        raise ValueError('试玩路线缺少盘点项：' + ', '.join(missing))
    return {
        'game': required_text(plan, 'game', '试玩计划'),
        'version': required_text(plan, 'version', '试玩计划'),
        'mode': mode,
        'preview_url': '' if mode == 'share' else required_text(plan, 'preview_url', '试玩计划'),
        'web_tree_sha256': web_sha,
        'require_ad_simulator': require_ad_simulator,
        'steps': steps,
    }


def validate_package(record, archive, plan):
    record = object_of(record, '测试包交付回执')
    if (record.get('status') != 'delivery_file_verified' or record.get('entry') != 'official'
            or record.get('expected_tree_exact') is not True):
        raise ValueError('需要正式交付入口产生的本次 ZIP 回执')
    if not archive.is_file() or archive.suffix.lower() != '.zip':
        raise ValueError('需要实际交付的 ZIP 文件')
    if Path(required_text(record, 'archive', '测试包回执')).resolve() != archive:
        raise ValueError('回执中的 ZIP 路径与本次交付文件不同')
    digest = sha256_file(archive)
    size = object_of(record.get('fresh_size_check'), '本次 ZIP 体积回执')
    if (digest != record.get('sha256') or digest != size.get('sha256') or size.get('reused') is not False
            or not size.get('run_id')):
        raise ValueError('ZIP 已变化或缺本次体积复核')
    preview = object_of(record.get('preview'), '同版试玩回执')
    if (preview.get('url'), preview.get('web_tree_sha256')) != (plan['preview_url'], plan['web_tree_sha256']):
        raise ValueError('H5 的试玩入口与 ZIP 交付回执不同')
    return {'name': archive.name, 'sha256': digest}


def validate_acceptance(report, delivery, plan):
    report = object_of(report, '最终验收报告')
    if (report.get('status') != 'passed' or report.get('board') != 'localize'
            or report.get('stage') != 'device' or report.get('errors') != []
            or type(report.get('catalog_checks')) is not int or report['catalog_checks'] < 1):
        raise ValueError('正式双栏需要本版英化 device 阶段通过报告。已有局部验收可用单栏试玩。')
    accepted = object_of(report.get('binding'), '最终验收构建绑定')
    startup = object_of(delivery.get('final_startup_runtime'), '正式交付 Native 启动回执')
    native_sha = required_text(startup, 'native_tree_sha256', '正式交付 Native 启动回执')
    if (startup.get('passed') is not True or not re.fullmatch(r'[a-f0-9]{64}', native_sha)
            or accepted.get('native_tree_sha256') != native_sha
            or accepted.get('web_tree_sha256') != plan['web_tree_sha256']):
        raise ValueError('最终验收的 Native 或 Web 与这次正式交付不同')


def render(plan, package=None, *, split_preview=False, ad_simulator=False):
    data = dict(plan, package=package, ad_simulator=ad_simulator)
    stable = {k: plan[k] for k in ('game', 'version', 'web_tree_sha256', 'steps', 'require_ad_simulator')}
    data['progress_key'] = 'cocos-playtest-' + hashlib.sha256(
        json.dumps(stable, ensure_ascii=False, sort_keys=True).encode('utf-8')
    ).hexdigest()
    if split_preview:
        data['split_preview'] = True
    # Keep game labels as data even when they contain HTML-looking characters.
    encoded = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    template = TEMPLATE.read_text(encoding='utf-8')
    if template.count(MARKER) != 1:
        raise ValueError('H5 模板数据槽不正确')
    return template.replace(MARKER, encoded, 1)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--zip', type=Path)
    parser.add_argument('--delivery-record', type=Path)
    parser.add_argument('--acceptance-report', type=Path, help='passed device-stage report for the delivered build')
    parser.add_argument('--demo-split', action='store_true', help='render a clearly marked split trial sample')
    args = parser.parse_args(argv)
    try:
        if args.out.suffix.lower() != '.html':
            raise ValueError('输出应为 .html')
        destination = args.out.resolve()
        if any(p and destination == p.resolve() for p in (args.plan, args.zip, args.delivery_record, args.acceptance_report)):
            raise ValueError('H5 输出须与输入文件分开')
        plan = validate_plan(json.loads(args.plan.read_text(encoding='utf-8')))
        package = None
        native = None
        if bool(args.zip) != bool(args.delivery_record):
            raise ValueError('标注测试包时须同时提供实际 ZIP 与本次交付回执')
        if plan['mode'] == 'package' and (args.demo_split or not (args.zip and args.acceptance_report)):
            raise ValueError('正式双栏交付需要实际 ZIP、本次交付回执和本版最终验收通过报告')
        if plan['mode'] == 'trial' and args.acceptance_report:
            raise ValueError('绑定最终验收报告时请选择 package 模式')
        if plan['mode'] == 'share' and (args.zip or args.acceptance_report or args.demo_split):
            raise ValueError('转发清单只用本版盘点和构建指纹')
        if args.zip:
            record = json.loads(args.delivery_record.read_text(encoding='utf-8'))
            package = validate_package(record, args.zip.resolve(), plan)
            if args.acceptance_report:
                acceptance = json.loads(args.acceptance_report.read_text(encoding='utf-8'))
                validate_acceptance(acceptance, record, plan)
            native = Path(required_text(record, 'native', '测试包回执')).resolve()
            if destination.is_relative_to(native):
                raise ValueError('H5 须单独交付，请放在 Native 目录外')
        ad_simulator = False
        if plan['mode'] != 'share':
            sys.path[:0] = [str(CHECK_TOOLS), str(CORE_TOOLS)]
            from browser_slots import slots
            from verify_delivery_preview import verify_preview
            preview = verify_preview(plan['preview_url'], plan['web_tree_sha256'],
                                     require_ad_simulator=plan['require_ad_simulator'])
            slot = next((row for row in slots() if row.get('id') == preview['slot_id']), None)
            if not slot or not slot.get('dir'):
                raise ValueError('试玩快照已关闭或被替代')
            if destination.is_relative_to(Path(slot['dir']).resolve()):
                raise ValueError('H5 须单独交付，请放在试玩快照外')
            ad_simulator = preview['ad_simulator']
        html = render(plan, package, split_preview=args.demo_split, ad_simulator=ad_simulator)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', prefix='.playtest-', dir=destination.parent,
                                         delete=False) as stream:
            temp = Path(stream.name)
            try:
                stream.write(html)
                stream.close()
                os.replace(temp, destination)
            finally:
                temp.unlink(missing_ok=True)
        print(json.dumps({'html': str(destination), 'pages': len(plan['steps']),
                          'web_tree_sha256': plan['web_tree_sha256'], 'package': package}, ensure_ascii=False))
    except (OSError, ValueError) as error:
        print(f'试玩 H5 未生成：{error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
