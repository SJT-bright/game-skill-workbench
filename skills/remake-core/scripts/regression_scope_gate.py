#!/usr/bin/env python3
"""Authorize scoped regressions and return recoverable gaps to the repair workflow."""
import argparse
from contextvars import ContextVar
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
import zipfile

import check_ledger as ledger

ENV_PLAN = 'ENGLISH_CHECK_REGRESSION_PLAN'
SCHEMA = 'cocos-regression-scope.v1'
STARTUP = 'startup.native.renderer'
# These current runners contain distinct feature journeys. A prose note cannot split them.
MIXED_SUITES = {'ad_outcome', 'save_restart', 'button_sweep'}
ADAPTER_ENV = 'TIKTOK_AD_REGRESSION_ADAPTER'
_active_plan = ContextVar('active_regression_scope', default=None)


class ScopeRepairRequired(ledger.NeedsScope):
    """The attempted operation needs repair while the authorized task continues."""

    def __init__(self, message):
        self.reason = message
        super().__init__('scope_required: ' + message + '；继续修复此缺口，再回原节点续跑')


def fail(message):
    raise ScopeRepairRequired(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    return sha(path.read_bytes())


def scope_path(project):
    return project / 'docs/checks/check-inputs.json'


def package_manifest(files):
    return {name: sha(data) for name, data in files.items()
            if not set(PurePosixPath(name).parts) & ledger.IGNORED
            and not name.startswith('docs/checks/incremental/')}


def adapter_file(adapter):
    adapter = adapter or os.environ.get(ADAPTER_ENV)
    if not adapter or not Path(adapter).is_file():
        fail('缺少当前游戏的回归适配文件')
    return Path(adapter).resolve()


def scope_digest(project):
    path = scope_path(project)
    return digest(path) if path.is_file() else None


def whole_package(pattern):
    # fnmatch '*' also crosses path separators. Repeated stars are equivalent.
    return pattern and all(ch == '*' for ch in pattern)


def baseline_identity(archive, candidate):
    from verify_native_zip import receipt_status, safe_name

    path = Path(archive).resolve()
    if not path.is_file():
        fail('找不到原交付 ZIP，禁止自动切到全量')
    archive_sha = digest(path)
    with zipfile.ZipFile(path) as z:
        files = {}
        for item in z.infolist():
            if item.is_dir():
                continue
            name = safe_name(item.filename).as_posix()
            if name in files:
                fail('原交付 ZIP 存在重复条目')
            files[name] = z.read(item)
    if digest(path) != archive_sha:
        fail('原交付 ZIP 在读取期间变化')
    status = receipt_status(path, archive_sha, package_manifest(files))
    if status.get('entry') != 'official':
        fail('原交付 ZIP 缺少同字节的正式回执')
    receipt = Path(status['receipt'])
    for config in ('project.config.json', 'game.json'):
        old = json.loads(files.get(config, b'{}'))
        new = json.loads(candidate.get(config, b'{}'))
        for key in ('appId', 'appid', 'app_id'):
            if old.get(key) and new.get(key) and old[key] != new[key]:
                fail('上一交付 ZIP 的 App ID 不匹配')
    return {'path': str(path), 'sha256': archive_sha,
            'receipt': str(receipt), 'receipt_sha256': digest(receipt)}


def _load_plan(project):
    path = os.environ.get(ENV_PLAN)
    if not path:
        fail('缺少已核对的执行计划。先运行 regression_scope_gate.py plan；不会自动打开浏览器')
    try:
        raw = Path(path).read_bytes()
        plan = json.loads(raw)
    except (OSError, ValueError) as error:
        fail('执行计划无法读取：' + str(error))
    if not isinstance(plan, dict) or plan.get('schema') != SCHEMA or plan.get('project') != str(project):
        fail('执行计划不属于此工程')
    if plan.get('scope_sha256') != scope_digest(project):
        fail('检查依赖声明已变化，请重新生成计划')
    if plan.get('mode') not in ('scoped', 'reuse-only', 'full'):
        fail('无效执行模式')
    if plan['mode'] == 'full' and not str(plan.get('authorization') or '').strip():
        fail('全量模式缺少用户本轮明确指令')
    if not isinstance(plan.get('actions'), dict):
        fail('执行计划没有用例清单')
    plan_sha = sha(raw)
    active = _active_plan.get()
    if active is not None and active != plan_sha:
        fail('执行过程中不能更换已绑定的计划')
    return plan, plan_sha


def _authorize(roots, plans, plan, operation):
    if ledger.sha(roots['package']) != plan.get('native_tree'):
        fail('计划与正在检查的 Native 构建不一致')
    if 'adapter' in roots and ledger.sha(roots['adapter']) != plan.get('adapter_tree'):
        fail('计划与正在使用的适配内容不一致')
    expected = plan['actions'].get(operation)
    if not isinstance(expected, dict):
        fail('计划缺少 ' + operation + ' 用例清单')
    actual = {row['check_id']: row for row in plans}
    if not actual.keys() <= expected.keys():
        fail('计划外检查：' + ', '.join(sorted(actual.keys() - expected.keys())))
    for cid, row in actual.items():
        item = expected[cid]
        action = row['action']
        if item.get('key') != row['key'] or action not in ('reuse', 'run'):
            fail(cid + ' 的输入、工具、历史证据或执行条件发生变化')
        if action == 'run':
            if plan['mode'] == 'reuse-only':
                fail(cid + ' 没有可沿用证据，纯沿用计划禁止启动浏览器')
            if item.get('action') != 'run':
                fail(cid + ' 未获本次重跑许可')
            if plan['mode'] == 'scoped':
                _specific_run(cid, row)
    return actual


def authorize_batch(project, roots, plans, *, operation, expected_sha256=None, native=None, adapter=None):
    project = Path(project).resolve()
    plan, plan_sha = _load_plan(project)
    if expected_sha256 is not None and plan_sha != expected_sha256:
        fail('执行计划在浏览器启动前发生变化')
    if _active_plan.get() is None:
        if native is None or adapter is None:
            fail('回归执行必须先核准完整计划')
        preflight(project, directory_files(Path(native)), adapter, board=plan.get('board'),
                  policy=plan.get('policy'), operation='direct')
        if _active_plan.get() != plan_sha:
            fail('执行计划在前置核对期间变化')
    _authorize(roots, plans, plan, operation)
    return plan_sha


def needs_ad_suite(files, adapter, ad_runner, runtime_runner):
    if not ad_runner.needs_regression(files):
        return False
    # Some installed older packs explicitly keep a revive-only manual probe.
    manual = getattr(runtime_runner, 'manual_revive_request', None)
    if manual and adapter:
        value = runtime_runner.load_adapter(adapter)
        if manual(value) and not value.get('double_claim'):
            return False
    return True


def _observe(project, files, adapter, board, policy):
    """Ask the same runners for their actual schedule without executing it."""
    scripts = Path(__file__).resolve().parents[2] / 'cocos-game-check/package-check/scripts'
    sys.path.insert(0, str(scripts))
    import ad_regression
    import ad_incremental
    import runtime_regression
    import runtime_incremental
    from verify_native_zip import safe_name

    if ledger.project_of(adapter=adapter) != project:
        fail('回归适配文件或环境指向了另一个工程')
    with tempfile.TemporaryDirectory(prefix='regression-plan-') as folder:
        stage = Path(folder)
        for name, data in files.items():
            target = stage / safe_name(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        groups = {'ads': [], 'runtime': []}
        if needs_ad_suite(files, adapter, ad_regression, runtime_regression):
            groups['ads'] = ad_incremental.run(ad_regression, stage, adapter, plan_only=True)
        if 'game.js' in files:
            groups['runtime'] = runtime_incremental.run(
                runtime_regression, stage, adapter, board=board, policy=policy, plan_only=True)
    return groups


def _specific_run(cid, row):
    scope = row.get('scope') or {}
    patterns = scope.get('inputs', {}).get('package', [])
    selected = set(row.get('binding', {}).get('inputs', {}).get('package', {})) - {'<selectors>'}
    actual = set(row.get('roots', {}).get('package', {}))
    if (not patterns or any(whole_package(pattern) for pattern in patterns)
            or (bool(actual) and selected == actual)):
        fail(cid + ' 用整包或空范围解释重跑。先登记实际代码、资源和页面依赖')
    if cid.removeprefix('runtime.').split('/')[0] in MIXED_SUITES and cid.endswith('/@suite'):
        fail(cid + ' 当前会执行多个功能流程。先拆分到具体用例，不能用整组替代')
    atomic = scope.get('atomic')
    if cid.endswith('/@suite') and not (isinstance(atomic, str) and atomic.strip()):
        fail(cid + ' 是整组检查，尚无不可拆分且全组受影响的依据')


def _only_bundle_changed(before, current):
    """A combined script's bytes alone do not identify the affected feature."""
    if {k: v for k, v in before.items() if k != 'package'} != {
            k: v for k, v in current.items() if k != 'package'}:
        return False
    a, b = before.get('package', {}), current.get('package', {})
    changed = {path for path in a.keys() | b.keys() if a.get(path) != b.get(path)}
    bundle = re.compile(r'^(?:(?:assets|subpackages)/[^/]+/index|src/chunks/bundle)(?:\.[^/]+)?\.js$')
    return bool(changed) and all(bundle.fullmatch(path) for path in changed)


def _check_impact(project, groups, proposed, mode, baseline, files):
    eligible = {row['check_id']: row for rows in groups.values() for row in rows}
    pending = {cid for cid, row in eligible.items() if row['action'] == 'run'}
    blocked = [cid + ' ' + row['why'] for cid, row in eligible.items() if row['action'] not in ('run', 'reuse')]
    if mode in ('full', 'reuse-only'):
        if blocked:
            fail('先处理逐项缺口：' + '；'.join(blocked))
        if mode == 'reuse-only' and (pending or proposed):
            fail('纯沿用计划不能补跑：' + ', '.join(sorted(pending | proposed.keys())))
        return
    if not baseline:
        fail('局部返工需要原交付 ZIP 和回执')
    for cid, row in sorted(eligible.items()):
        if row['action'] != 'reuse':
            _specific_run(cid, row)
    if blocked:
        fail('先处理逐项缺口：' + '；'.join(blocked))
    store = ledger.Ledger(project)
    try:
        for cid in sorted(pending):
            row = eligible[cid]
            passed = [old for old in store.previous(cid) if old.get('passed')]
            if not passed:
                continue  # Explicitly proposed new case with a declared dependency.
            before = ledger.select_inputs(passed[0].get('roots', {}), row['scope'])
            current = row['binding']['inputs']
            recovery = row.get('evidence_recheck')
            recollect = (recovery and recovery.get('prior_key') == ledger.sha(passed[0]['binding'])
                         and not store._evidence_valid(passed[0]))
            if before == current and passed[0]['binding']['conditions'] == row['binding']['conditions'] and not recollect:
                fail(cid + ' 的实际输入未变。先核对旧证据或判定器变化，不能以工具版本解释重跑')
            if _only_bundle_changed(before, current):
                fail(cid + ' 只匹配到合并脚本字节变化，先核对受影响的真实模块')
    finally:
        store.close()
    if pending - proposed.keys():
        fail('执行范围之外仍有待跑项：' + ', '.join(sorted(pending - proposed.keys())))
    if proposed.keys() - pending - {STARTUP}:
        fail('申请了当前无需重跑或未知的检查：' + ', '.join(sorted(proposed.keys() - pending - {STARTUP})))
    old_path = Path(baseline['path'])
    with zipfile.ZipFile(old_path) as archive:
        old = package_manifest({i.filename: archive.read(i) for i in archive.infolist() if not i.is_dir()})
    if digest(old_path) != baseline['sha256']:
        fail('原交付 ZIP 已变化')
    current = package_manifest(files)
    changed = {name for name in old.keys() | current.keys() if old.get(name) != current.get(name)}
    owners = []
    for cid, row in eligible.items():
        scope = row.get('scope') or {}
        inputs = scope.get('inputs', {})
        patterns = inputs.get('package', [])
        broad = not patterns or any(whole_package(p) for p in patterns)
        if not broad:
            owners.extend(patterns)
    from fnmatch import fnmatchcase
    unmapped = sorted(path for path in changed if not any(fnmatchcase(path, p) for p in owners))
    if unmapped:
        fail('这些产物变化缺少精确归属：' + ', '.join(unmapped[:15]))
    # A non-empty explanation is required in addition to the ledger's concrete binding.
    if any(not isinstance(reason, str) or not reason.strip() for reason in proposed.values()):
        fail('每个重跑项需要实际变更及其依赖理由')


def create_plan(project, files, adapter, *, board, policy, prior, mode, proposed, authorization=None):
    project = Path(project).resolve()
    adapter = adapter_file(adapter)
    if not isinstance(proposed, dict):
        fail('重跑项必须是「检查 ID → 实际变更理由」的对象')
    if mode == 'full' and not (isinstance(authorization, str) and authorization.strip()):
        fail('全量执行需要记录用户本轮明确原话')
    baseline = baseline_identity(prior, files) if prior else None
    groups = _observe(project, files, adapter, board, policy)
    _check_impact(project, groups, proposed, mode, baseline, files)
    actions = {group: {p['check_id']: {'action': p['action'], 'key': p['key'],
                                       'reason': proposed.get(p['check_id'], p['why'])}
                       for p in plans} for group, plans in groups.items()}
    return {'schema': SCHEMA, 'mode': mode, 'project': str(project), 'board': board, 'policy': policy,
            'scope_sha256': scope_digest(project), 'baseline': baseline, 'authorization': authorization,
            'native_tree': ledger.sha(package_manifest(files)), 'adapter_sha256': digest(adapter),
            'adapter_tree': ledger.sha(ledger.json_manifest(json.loads(adapter.read_text()))),
            'startup_run': mode == 'full' or STARTUP in proposed, 'actions': actions}


def preflight(project, files, adapter, *, board=None, policy=None, prior=None, operation='writer'):
    project = Path(project or ledger.project_of(adapter=adapter)).resolve()
    plan, plan_sha = _load_plan(project)
    adapter = adapter_file(adapter)
    roots = {'package': package_manifest(files), 'adapter': ledger.json_manifest(json.loads(adapter.read_text()))}
    if plan.get('adapter_sha256') != digest(adapter):
        fail('适配文件已经变化')
    if plan.get('board') != board or plan.get('policy') != policy:
        fail('计划和执行的制作入口或平台策略不同')
    baseline = plan.get('baseline')
    if plan['mode'] == 'scoped' and not baseline:
        fail('缺少原交付基线')
    if operation == 'writer' and plan['mode'] == 'scoped' and not prior:
        fail('写包器未核准原交付基线，不会按首次运行处理')
    if baseline and baseline != baseline_identity(prior or baseline['path'], files):
        fail('原交付基线或回执已经变化')
    if ledger.sha(roots['package']) != plan.get('native_tree'):
        fail('计划和即将写包的实际 Native 文件不一致')
    groups = _observe(project, files, adapter, board, policy)
    for group, rows in groups.items():
        if {row['check_id'] for row in rows} != plan['actions'].get(group, {}).keys():
            fail(group + ' 的覆盖清单已经变化')
        _authorize(roots, rows, plan, group)
    # Recheck dependencies before allowing the first browser. Refuse forged/shallow plan entries.
    if plan['mode'] == 'scoped':
        proposed = {cid: item['reason'] for group in plan['actions'].values() for cid, item in group.items()
                    if item['action'] == 'run' and any(r['check_id'] == cid and r['action'] == 'run'
                                                       for rows in groups.values() for r in rows)}
        if plan.get('startup_run'):
            proposed[STARTUP] = '本版真实 Native 启动及触控'
        _check_impact(project, groups, proposed, plan['mode'], baseline, files)
    if _load_plan(project)[1] != plan_sha:
        fail('计划在核对过程中变化')
    _active_plan.set(plan_sha)
    return {'schema': SCHEMA, 'plan_sha256': plan_sha, 'mode': plan['mode'],
            'baseline': baseline, 'allowed': sorted(cid for g in plan['actions'].values()
                                                     for cid, item in g.items() if item['action'] == 'run'),
            'startup_run': bool(plan.get('startup_run'))}


def startup_replay(proof, native, binding, project, *, reuse_only, plan_project):
    """Verify existing startup evidence or execute only the explicitly planned item."""
    import audit_native_startup_renderer as renderer
    import native_startup_ledger as startup

    native, project = Path(native).resolve(), Path(project).resolve()
    if renderer.digest(renderer.tree(native)) != binding.get('native_tree_sha256'):
        fail('Native 启动证据对应其他构建')
    conditions, tools = startup.identity(proof, native, project)
    conditions['native_tree_sha256'] = binding['native_tree_sha256']
    store = ledger.Ledger(project)
    try:
        row = store.prepare(STARTUP, {}, conditions, tools,
                            label='真实 Native 启动 / 首次触控', domain='startup')
        if row['action'] == 'reuse':
            def unexpected_execution():
                fail('交付期间启动证据失效，需回到核准节点')
            result, detail = store.execute(row, unexpected_execution, lambda _: False)
            if not result.get('raw_evidence'):
                fail('启动证据缺少真实回放')
            return dict(detail, id=STARTUP, action='reused',
                        reason='正式启动输入和原始回放证据一致',
                        evidence=result['raw_evidence'], observed_at=result['observed_at'],
                        original_binding=result['original_binding'],
                        original_build_tag=result['original_binding']['build_tag'],
                        native_tree_sha256=binding['native_tree_sha256'])
        if reuse_only:
            fail('正式交付只能回读启动证据。缺项回到已核准的启动节点补验')
        if row['action'] != 'run':
            fail(STARTUP + '：' + row['why'])
        if _active_plan.get() is None:
            fail('写包前未核准启动和回归范围')
        plan, _ = _load_plan(Path(plan_project).resolve())
        if (plan['mode'] == 'reuse-only' or not plan.get('startup_run')
                or ledger.sha(ledger.manifest(native)) != plan.get('native_tree')):
            fail('计划未核准此 Native 构建的启动重跑')
    finally:
        store.close()
    return startup.replay(proof, native, binding, project)


def directory_files(native):
    return {p.relative_to(native).as_posix(): p.read_bytes()
            for p in native.rglob('*') if p.is_file()}


def repair_report(project, files, adapter, *, board, policy, prior, mode, proposed, authorization=None):
    """Collect actionable gaps offline. Only a fully validated plan can resume execution."""
    project = Path(project).resolve()
    issues = []
    preserved = []
    try:
        groups = _observe(project, files, adapter_file(adapter), board, policy)
    except (ValueError, OSError, zipfile.BadZipFile) as error:
        groups = {}
        issues.append({'id': 'inspection', 'kind': 'input_repair', 'reason': str(error),
                       'remedy': '修复具体路径、依赖声明或适配器格式，再重新读取实际计划。'})
    for rows in groups.values():
        for row in rows:
            cid = row['check_id']
            if row['action'] == 'reuse':
                preserved.append(cid)
                continue
            if row['action'] != 'run':
                remedy = {
                    'evidence_missing': '从原证据目录、交接记录或备份恢复并验证原始字节；无法恢复时只为该独立项补验。',
                    'needs_scope': '读取实际消费者和调用关系，补齐依赖与新增删除归属，再重新规划。',
                    'blocked_failed': '核对失败原始输出，修复产品、操作路径或已确认的运行环境，再只重试该项。',
                }.get(row['action'], '读取此项原始结果并修复具体缺口，再重新规划。')
                issues.append({'id': cid, 'kind': row['action'], 'reason': row['why'], 'remedy': remedy})
            if mode == 'scoped':
                try:
                    _specific_run(cid, row)
                except ledger.NeedsScope as error:
                    issues.append({'id': cid, 'kind': 'dependency_or_execution_unit', 'reason': str(error),
                                   'remedy': '补准实际依赖。包含多个功能的执行器拆成可独立核验的单元，按原报告恢复未受影响项。'})
    plan = None
    try:
        plan = create_plan(project, files, adapter, board=board, policy=policy, prior=prior,
                           mode=mode, proposed=proposed, authorization=authorization)
    except (ValueError, OSError, zipfile.BadZipFile) as error:
        issues.append({'id': 'plan', 'kind': 'plan_repair', 'reason': str(error),
                       'remedy': '修复所列计划、基线或归属问题，保留原执行证据，再调用 repair 生成核准计划。'})
    return {
        'schema': 'cocos-regression-repair.v1',
        'status': 'plan_ready' if plan is not None else 'repair_required',
        'task_terminal': False, 'browser_launches': 0,
        'project': str(project), 'native_tree': ledger.sha(package_manifest(files)),
        'scope_sha256': scope_digest(project), 'preserved': sorted(preserved),
        'issues': issues if plan is None else [],
        'continuation': {
            'action': 'resume_authorized_step' if plan is not None else 'repair_and_replan',
            'owner': 'current_agent',
            'instruction': '在现有授权内持续修复并续跑。仅有真实外部文件、权限、决定缺失或用户明确暂停时才交回用户。',
        },
    }, plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('inspect', 'plan', 'repair'))
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--native', required=True, type=Path, help='Already prepared actual Native files')
    parser.add_argument('--adapter', required=True, type=Path)
    parser.add_argument('--board', required=True, choices=('localize', 'remake'))
    parser.add_argument('--policy', required=True, choices=('new', 'legacy'))
    parser.add_argument('--prior', type=Path)
    parser.add_argument('--mode', choices=('scoped', 'reuse-only', 'full'), default='scoped')
    parser.add_argument('--proposed', type=Path, help='JSON object of case IDs to reasons')
    parser.add_argument('--authorization', help='Explicit current user instruction to run the full matrix')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--plan-out', type=Path, help='For repair, write a validated executable plan if ready')
    args = parser.parse_args()
    try:
        if args.command == 'plan' and not args.out:
            fail('plan 需要 --out；inspect 可以只打印')
        if any(path and path.resolve().is_relative_to(args.native.resolve())
               for path in (args.out, args.plan_out)):
            fail('计划必须写在 Native 目录之外')
        files = directory_files(args.native)
        if 'game.js' not in files:
            fail('指定目录不是最终准备过的小游戏 Native 构建')
        if args.command == 'inspect':
            groups = _observe(args.project.resolve(), files, adapter_file(args.adapter), args.board, args.policy)
            result = {'status': 'inspection_only', 'browser_launches': 0, 'groups': {}}
            for operation, rows in groups.items():
                result['groups'][operation] = [
                    {'id': row['check_id'], 'action': row['action'], 'reason': row['why'],
                     'declared_package_inputs': (row.get('scope') or {}).get('inputs', {}).get('package', [])}
                    for row in rows]
            report = json.dumps(result, ensure_ascii=False, indent=2)
            if args.out:
                with args.out.open('x', encoding='utf-8') as stream:
                    stream.write(report + '\n')
            else:
                print(report)
            return
        proposed = json.loads(args.proposed.read_text()) if args.proposed else {}
        if args.command == 'repair':
            if not args.out or not args.plan_out:
                fail('repair 需要 --out 和 --plan-out，分别保存修复记录与核准计划')
            if args.out.resolve() == args.plan_out.resolve():
                fail('修复记录与执行计划需要不同文件')
            if args.out.exists() or args.plan_out.exists():
                fail('保留既有修复记录和计划，请为本次修复使用新路径')
            report, plan = repair_report(args.project, files, args.adapter, board=args.board,
                                         policy=args.policy, prior=args.prior, mode=args.mode,
                                         proposed=proposed, authorization=args.authorization)
            if plan is not None:
                with args.plan_out.open('x', encoding='utf-8') as stream:
                    json.dump(plan, stream, ensure_ascii=False, indent=2)
                    stream.write('\n')
                report['plan_path'] = str(args.plan_out.resolve())
            args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            print(json.dumps({'status': report['status'], 'task_terminal': False,
                              'report': str(args.out.resolve()), 'browser_launches': 0,
                              'issues': len(report['issues']), 'preserved': len(report['preserved']),
                              'next_action': report['continuation']['action']}, ensure_ascii=False))
            return
        plan = create_plan(args.project, files, args.adapter, board=args.board, policy=args.policy,
                           prior=args.prior, mode=args.mode, proposed=proposed, authorization=args.authorization)
        with args.out.open('x', encoding='utf-8') as stream:
            json.dump(plan, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        print(json.dumps({'status': 'plan_ready', 'path': str(args.out.resolve()),
                          'browser_launches': 0, 'mode': plan['mode']}, ensure_ascii=False))
    except ScopeRepairRequired as error:
        parser.exit(2, json.dumps({'status': 'repair_required', 'task_terminal': False,
                                  'reason': error.reason, 'next_action': 'repair_and_replan',
                                  'owner': 'current_agent'}, ensure_ascii=False) + '\n')
    except (ValueError, OSError, zipfile.BadZipFile) as error:
        parser.exit(2, json.dumps({'status': 'repair_required', 'task_terminal': False,
                                  'reason': str(error), 'next_action': 'diagnose_and_repair_input',
                                  'owner': 'current_agent'}, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
