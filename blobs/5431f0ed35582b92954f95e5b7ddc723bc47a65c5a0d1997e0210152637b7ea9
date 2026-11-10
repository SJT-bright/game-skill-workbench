#!/usr/bin/env python3
"""Final-package checks; shared production verifier, no gameplay CI.

v7.8 (总表 B17): run as a command on a ZIP without a matching writer receipt, the verdict is
"只读预检，不可交付（非官方入口）" (status unofficial_not_deliverable, exit 3); 丛林荡藤 v6 and 剪刀达人 v30 were
called a pass that way. --structure-only keeps the old answer for diagnosis. check() itself is unchanged: both
writers and prepare_delivery import it.

v7.8 (总表 B32 d): check() adds tool_identity (tool_identity.py): the check tools in use compared with the Skill's
release record and the installed copies. Changed or not-installed tools are 「改过的工具」 (result modified_tools and a
warning; never a refusal); this command and build_checked_zip then write a feedback draft into ！Skill更新/
(反馈草稿_改过的工具_<游戏>_<日期>.md, new file only; $COCOS_SKILL_FEEDBACK_DIR moves it, for tests)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ad_regression as ad_regression_gate
import runtime_regression as runtime_regression_gate
import check_guard  # J1 批 / 总表 P19: one not_run shape and the status list (references/check-status.json)
SHARED = Path(__file__).resolve().parents[3] / 'remake-core' / 'scripts'
sys.path.insert(0, str(SHARED))
import verify_native_zip as verifier
from audit_packed_assets import audit as packed_assets


READ_ONLY_VERDICT = '只读预检，不可交付（非官方入口）'
READ_ONLY_DIR = '只读预检，不可交付（Native 目录不是上传包；上传包只能由 build_checked_zip.py 或 make_tiktok_zip.py 写出）'
OFFICIAL_VERDICT = '官方入口写出的包，本地检查通过（不代表平台或真机验收）'
UNOFFICIAL_CLI = (READ_ONLY_VERDICT + ': %s. Only a ZIP written by build_checked_zip.py or make_tiktok_zip.py (with '
                  '<zip>.receipt.json beside it, or a receipt for the same ZIP bytes in that folder) may be delivered; '
                  'add --structure-only for a read-only check that does not judge delivery')
# v7.9 (总表 19 ④): the last part of a refusal whose static reasons made check() skip the browser regressions
BROWSER_SKIPPED_NOTE = ('browser suites not run (rewarded-ad regression, runtime regression): the static reasons above '
                        'already refuse this package; fix them and check the new package '
                        '(浏览器套件没跑：先修上面的问题，出了新包再跑)')


def native_files(root):
    files = {}
    for path in sorted(Path(root).rglob('*')):
        if path.is_symlink():
            raise ValueError('symlink in Native: ' + str(path))
        if not path.is_file():
            continue
        name = path.relative_to(root).as_posix()
        why = verifier.forbidden(name)
        if why == 'Finder/Windows junk file':
            continue
        if why:
            raise ValueError(name + ': ' + why)
        files[name] = path.read_bytes()
    return files


def write_archive(path, files):
    from upload_size_gate import enforce_files
    enforce_files(files)
    from audit_no_ad_simulator import enforce_files as enforce_no_simulator
    enforce_no_simulator(files)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(files.items()):
            archive.writestr(name, content)


def rewarded_ad_gate(files, folder, adapter=None, rework=None):
    """Mandatory rewarded-ad regression on the exact verified bytes staged in folder
    (Basil timeout rule, remake-ads/references/ad-timeout-and-regression.md). Refuses unless
    every case passes; a missing adapter or browser is a refusal, never a skip.
    rework (简化.11.15, rework_scope.plan): a reuse plan against the last passed package -> its pass is kept (only
    pictures, sounds or fonts changed; same code, adapter and tool) instead of running the 10 cases again."""
    if not ad_regression_gate.needs_regression(files):
        return {'id': 'rewarded_ad_regression', 'status': 'not_applicable',
                'reason': 'no createRewardedVideoAd call in package JavaScript'}
    adapter = adapter or os.environ.get(ad_regression_gate.ENV_ADAPTER)
    input_gate('rewarded_ad_regression', adapter)
    from regression_scope_gate import needs_ad_suite
    if not needs_ad_suite(files, adapter, ad_regression_gate, runtime_regression_gate):
        return {'id': 'rewarded_ad_regression', 'status': 'not_applicable',
                'reason': 'configured revive-only probe is covered by the manual playtest'}
    if isinstance(rework, dict) and rework.get('reuse') and rework.get('ad') == 'reuse':
        import rework_scope
        return rework_scope.reused_ad(rework)
    try:
        return ad_regression_gate.run(folder, adapter)
    except ad_regression_gate.RegressionRefused as error:
        raise ValueError(str(error))


def runtime_gate(files, folder, adapter=None, policy=None, board=None, rework=None):
    """Mandatory runtime regression (runtime_regression.py, references/runtime-regression.md) on the same staged
    bytes and the same adapter as the rewarded-ad regression. Every package with game.js runs the suites shipped
    in runtime_regression/suites that apply to it; a missing adapter/field/browser or a failed case refuses.
    policy (v7.8): the package gates' policy ('new' | 'legacy'), so a writer's finalize record decides the runtime
    suites too (dead_shell: FoxDenDash v1's record says new, its bytes say legacy); None = judged from the bytes.
    board (v7.8, 总表 B30): 'remake' | 'localize' picks layout_state's home rules; None = not checked (warning).
    The writers have no trial link, so trial_link never runs here (summary not_run says so).
    rework (简化.11.15, Saul 2026-11-04「出包后的返工修改，就只检查修改涉及的那些部分」): a reuse plan from
    rework_scope.plan -> only the suites that can see the change run again (rework_scope RERUN), the old passes of the
    rest are kept with their receipt named (reused_from); every required suite is in the summary either way."""
    if 'game.js' not in files:
        return {'id': 'runtime_regression', 'status': 'not_applicable', 'reason': 'no game.js at package root'}
    adapter = adapter or os.environ.get(runtime_regression_gate.ENV_ADAPTER)
    input_gate('runtime_regression', adapter)
    board = board if board in runtime_regression_gate.BOARDS else None
    try:
        names = runtime_regression_gate.required_suites(files, adapter)
        if isinstance(rework, dict) and rework.get('reuse'):
            import rework_scope
            rerun = rework_scope.to_rerun(rework, names)
            summary = (runtime_regression_gate.run(folder, adapter, rerun, policy=policy, board=board) if rerun
                       else None)
            return rework_scope.merge_runtime(rework, summary, names)
        return runtime_regression_gate.run(folder, adapter, names, policy=policy, board=board)
    except runtime_regression_gate.RuntimeRefused as error:
        raise ValueError(str(error))


def rework_plan(rework_of, files, adapter=None, policy=None, board=None):
    """Resolve the historical proof without turning an unknown edit into a full browser run."""
    if not rework_of:
        return None
    import rework_scope
    result=rework_scope.plan(rework_of, files, adapter or os.environ.get(ad_regression_gate.ENV_ADAPTER), policy, board)
    if not result.get('reuse'):
        from check_ledger import project_of, Ledger
        current_adapter=adapter or os.environ.get(ad_regression_gate.ENV_ADAPTER)
        project=project_of(adapter=current_adapter)
        ledger=Ledger(project)
        try:
            import runtime_incremental
            rr=runtime_regression_gate;catalog=rr.load_suites();a=rr.load_adapter(current_adapter,catalog)
            engine=rr.detect_engine(files,a);resolved_policy,_=rr.package_policy(files,policy)
            ids=[]
            for name in rr.required_suites(files,a,catalog):
                units=runtime_incremental.unit_ids(name,catalog[name],a,rr.precheck(name,catalog[name],a,engine,resolved_policy) is not None)
                ids.extend('runtime.'+name+'/'+unit for unit in units)
            if ad_regression_gate.needs_regression(files):ids.extend('ads.'+c for c in ad_regression_gate.default_cases(a))
            # Returned visual acceptance is a disposition, not a missing art test.
            # Its independent hidden-startup node is planned by runtime_incremental.
            from returned_art_acceptance import MANIFEST, validate
            if board == 'localize' and (project/MANIFEST).is_file():
                validate(project, native_files=files)
                ids=[cid for cid in ids if not cid.startswith('runtime.layout_state/')]
            missing=[cid for cid in ids if not ledger.previous(cid)]
        finally:ledger.close()
        if missing:
            raise ValueError('返工缺少这些逐项基线，禁止用无关记录触发整套首次运行：'+','.join(missing)+
                             '。先恢复原证据；真实新增项在对应制作节点补做一次。原计划：'+str(result.get('why')))
        return None  # The per-unit ledger, rather than the old extension-wide rule, now decides.
    return result


NO_ADAPTER_HINT = ('write the game\'s adapter JSON (usually <project>/qa/ad-regression.json; fields: '
                   'cocos-game-check/package-check/references/runtime-regression.md and '
                   'remake-ads/references/ad-timeout-and-regression.md) and pass it with --ad-regression or $%s'
                   % ad_regression_gate.ENV_ADAPTER)
ADAPTER_INPUT = 'ad-regression adapter (qa/ad-regression.json)'


class InputNotRun(ValueError):
    """总表 P19 ②: a regression input is absent or empty -> 「未执行」 (status not_run), never a pass or a skip."""

    LABEL = {'rewarded_ad_regression': 'rewarded-ad regression', 'runtime_regression': 'runtime regression'}

    def __init__(self, report):
        ValueError.__init__(self, '%s required: not run (未执行): %s' % (
            self.LABEL.get(report.get('id'), report.get('id')), report['reason']))
        self.summary = report


def input_gate(key, adapter):
    """check_guard.inputs_not_run over what the two regressions need from the caller: an adapter given at all (a path
    that is given is read by the gate's own loader, which names what is wrong with it). The adapter is generated by
    page_registry.py make."""
    report = check_guard.inputs_not_run(key, {ADAPTER_INPUT: str(adapter) if adapter else None},
                                        'remake-core/scripts/page_registry.py make --project <game> writes it from '
                                        'docs/logic/pages.json; ' + NO_ADAPTER_HINT)
    if report:
        raise InputNotRun(dict(report, id=key))


REUSE_SCHEMA = 'writer-regressions.v1'


def regression_context(files, folder, adapter, board, policy, project=None):
    """Use the project and package identity in both planning and actual checks."""
    from check_ledger import project_of
    from feature_policy import board_of
    adapter = adapter or os.environ.get(ad_regression_gate.ENV_ADAPTER) or None
    project = Path(project).resolve() if project else project_of(folder, adapter)
    declared_board = board_of(project)[0]
    if board and declared_board and board != declared_board:
        raise ValueError('scope_required: regression board differs from project board')
    board = board or declared_board
    policy = runtime_regression_gate.package_policy(files, policy)[0]
    return project, adapter, board, policy


def verify_regression_scope(files, folder, adapter, board, policy, prior, *,
                            project=None, expected_scope_sha256=None, operation='check'):
    """Check authorization on these exact bytes before a package check can open Ego."""
    if 'game.js' not in files and not ad_regression_gate.needs_regression(files):
        return None
    from regression_scope_gate import preflight
    project, adapter, board, policy = regression_context(files, folder, adapter, board, policy, project)
    audit = preflight(project, files, adapter, board=board, policy=policy, prior=prior, operation=operation)
    if expected_scope_sha256 is not None and audit.get('plan_sha256') != expected_scope_sha256:
        raise ValueError('scope_required: regression plan changed after writer preflight')
    return audit


def regression_coverage_problem(ad, runtime, files, adapter, policy=None):
    """A diagnostic subset may pass without establishing full delivery coverage."""
    from regression_scope_gate import needs_ad_suite
    adapter = adapter or os.environ.get(ad_regression_gate.ENV_ADAPTER) or None
    if needs_ad_suite(files, adapter, ad_regression_gate, runtime_regression_gate):
        expected = ad_regression_gate.default_cases(ad_regression_gate.load_adapter(adapter))
        rows = ad.get('cases') or []
        actual = [row.get('case') if isinstance(row, dict) else row for row in rows]
        if (not all(isinstance(case, str) for case in actual)
                or sorted(actual) != sorted(expected)):
            return 'rewarded-ad evidence does not cover every required case'
    if 'game.js' in files:
        rr = runtime_regression_gate
        adapter = adapter or os.environ.get(rr.ENV_ADAPTER) or None
        from runtime_incremental import unit_ids
        catalog = rr.load_suites()
        adapter_data = rr.load_adapter(adapter, catalog)
        names = rr.required_suites(files, adapter_data, catalog)
        engine = rr.detect_engine(files, adapter_data)
        judged = rr.package_policy(files, policy)[0]
        required = runtime.get('required') or []
        if (not isinstance(required, list) or not all(isinstance(name, str) for name in required)
                or sorted(required) != sorted(names)):
            return 'runtime evidence does not enumerate the required suites'
        rows = runtime.get('suites') or []
        covered = [row.get('suite') for row in rows if isinstance(row, dict) and (
            row.get('passed') is True or (
                row.get('visual_status') == 'user_accepted' and row.get('functional_passed') is True
                and row.get('accepted_for_delivery') is True))]
        if len(covered) != len(rows) or not all(isinstance(name, str) for name in covered):
            return 'runtime evidence contains an unverified suite'
        if not set(names).issubset(covered) or len(set(covered)) != len(covered):
            return 'runtime evidence does not cover every required suite'
        rows_by_name = {row['suite']: row for row in rows}
        for name in names:
            row = rows_by_name[name]
            meta = catalog[name]
            prechecked = rr.precheck(name, meta, adapter_data, engine, judged) is not None
            expected = set(unit_ids(name, meta, adapter_data, prechecked))
            if row.get('visual_status') == 'user_accepted':
                if (name != 'layout_state' or set(row.get('accepted_visual_units') or []) != expected
                        or 'runtime.layout_state/@startup' not in (row.get('incremental') or {})):
                    return 'runtime visual acceptance does not cover the required units and startup'
                continue
            if expected == {'@suite'}:
                continue
            prefix = 'runtime.' + name + '/'
            actual = {key[len(prefix):] for key in (row.get('incremental') or {}) if key.startswith(prefix)}
            actual.update(case.get('id') for case in row.get('cases') or []
                          if isinstance(case, dict) and case.get('passed') is True)
            if not expected or not expected.issubset(actual):
                return 'runtime evidence is missing required units: ' + name
    for summary in (ad, runtime):
        if summary.get('complete') is False or summary.get('planned_not_run') or summary.get('proof_error'):
            return 'writer regression evidence is incomplete'
    return None


def regression_record(ad, runtime):
    """v7.9 (出包检查提速 S1, 总表 19 ①): what an official writer keeps in its receipt of the two regressions it just
    passed on the bytes it publishes, so prepare_delivery can reuse them instead of running them again on the same ZIP
    (7.5-15 minutes per delivery). None when either did not pass or is incomplete; delivery refuses."""
    def part(summary, runtime_part):
        if not isinstance(summary, dict):
            return None
        if summary.get('complete') is False or summary.get('planned_not_run') or summary.get('proof_error'):
            return None
        # 总表 P19 ③: a status outside references/check-status.json, or one that is not a pass, is nothing to reuse
        if 'status' in summary and summary['status'] not in check_guard.status_values():
            return None
        if summary.get('status') in ('not_run', 'failed', 'environment_incomplete'):
            return None
        if summary.get('status') == 'not_applicable':
            return {'status': 'not_applicable', 'reason': summary.get('reason')}
        if summary.get('passed') is not True or not summary.get('tool_sha256') or not summary.get('adapter_sha256'):
            return None
        keep = {'status': 'passed', 'passed': True, 'tool_sha256': summary['tool_sha256'],
                'adapter_sha256': summary['adapter_sha256'], 'seconds': summary.get('seconds'),
                'warnings': list(summary.get('warnings') or [])}
        # 简化.11.15 (出包后返工): which passes were kept from an earlier package, and from which receipt
        if summary.get('reused_from'):
            keep['reused_from'] = summary['reused_from']
        if isinstance(summary.get('incremental'), dict):
            keep['incremental'] = summary['incremental']
        if isinstance(summary.get('raw_files'), list):
            keep['raw_files'] = summary['raw_files']
        if runtime_part:
            keep.update(required=list(summary.get('required') or []), engine=summary.get('engine'),
                        policy=summary.get('policy'), board=summary.get('board'),
                        suites=[{key:r[key] for key in ('suite','passed','cases','warnings','evidence','raw_files',
                                                       'units','seconds','original_seconds','original_at','reused_from','incremental',
                                                       'functional_passed','accepted_for_delivery','visual_status',
                                                       'visual_checks_executed','visual_acceptance','accepted_visual_units') if key in r}
                                for r in summary.get('suites') or [] if isinstance(r, dict)],
                        startup_measured=summary.get('startup_measured'))
            if isinstance(summary.get('rework'), dict):
                keep['rework'] = summary['rework']
        else:
            keep['cases'] = [c if isinstance(c, str) else c.get('case') for c in summary.get('cases') or []
                             if isinstance(c, (dict, str))]
        return keep
    a, r = part(ad, False), part(runtime, True)
    if a is None or r is None:
        return None
    return {'schema': REUSE_SCHEMA, 'rewarded_ad_regression': a, 'runtime_regression': r}


def reusable_regressions(receipt_file, files, adapter=None, policy=None):
    """v7.9 (出包检查提速 S1, 总表 19 ①): the writer receipt's regression record, when it still holds for these bytes.
    Called only for an official entry (receipt_status already matched the receipt to these ZIP bytes, this Native tree
    and a passed finalize). It holds when each regression passed (or did not apply) as this package needs, the adapter
    file and both check tools are byte-equal to the ones the writer ran, the same runtime suites are required, and the
    writer judged the game at least as strictly. Anything else: delivery stops without a browser fallback.
    -> {reused: True, note, rewarded_ad_regression, runtime_regression} or {reused: False, why}."""
    def no(why):
        return {'reused': False, 'why': why}
    adapter = adapter or os.environ.get(ad_regression_gate.ENV_ADAPTER) or None
    try:
        receipt = json.loads(Path(receipt_file).read_text(encoding='utf-8'))
    except (OSError, TypeError, ValueError) as error:
        return no('writer receipt unreadable: %s' % error)
    record = receipt.get('regressions') if isinstance(receipt, dict) else None
    if not isinstance(record, dict) or record.get('schema') != REUSE_SCHEMA:
        return no('writer receipt has no regression record (written before v7.9, or a regression did not pass there)')
    ad, rt = record.get('rewarded_ad_regression'), record.get('runtime_regression')
    if not isinstance(ad, dict) or not isinstance(rt, dict):
        return no('writer receipt regression record is incomplete')
    adapter_sha = None
    if adapter:
        try:
            adapter_sha = hashlib.sha256(Path(adapter).read_bytes()).hexdigest()
        except OSError as error:
            return no('adapter unreadable: %s' % error)
    # A successor writer can preserve the old rewarded-ad adapter identity only
    # when the recorded, independently replayed exact PLAY-only proof holds.
    adapter_equivalence = False
    tool_equivalence = False
    play_proof = (rt.get('rework') or {}).get('optional_art_delta')
    if isinstance(play_proof, dict):
        try:
            import importlib.util
            gp = Path(__file__).with_name('play_art_delta_guard.py')
            gs = importlib.util.spec_from_file_location('_delivery_play_delta', gp)
            gm = importlib.util.module_from_spec(gs); gs.loader.exec_module(gm)
            checked = gm.validate(play_proof['old_zip']['path'], files, adapter, play_proof['scope']['path'])
            if checked != play_proof:
                return no('PLAY scope proof differs on delivery readback')
            adapter_equivalence = (ad.get('adapter_sha256') == checked['old_adapter']['sha256'])
        except Exception as error:
            return no('PLAY scope proof invalid: %s' % error)
    browser_proof = (rt.get('rework') or {}).get('browser_policy_tool_equivalence')
    if isinstance(browser_proof, dict):
        if not adapter_equivalence:
            return no('browser policy reuse requires the validated exact PLAY source delta')
        try:
            ep = Path(__file__).with_name('browser_policy_tool_equivalence.py')
            es = importlib.util.spec_from_file_location('_delivery_browser_policy', ep)
            em = importlib.util.module_from_spec(es); es.loader.exec_module(em)
            project = json.loads(Path(play_proof['scope']['path']).read_text())['project']
            verified_policy = em.validate(project, browser_proof['original_tool_sha256']['rewarded_ad_regression'], browser_proof['original_tool_sha256']['runtime_regression'])
            if verified_policy != browser_proof:
                return no('browser policy byte/AST equivalence proof changed on readback')
            tool_equivalence = ad.get('tool_sha256') == verified_policy['original_tool_sha256']['rewarded_ad_regression']
        except Exception as error:
            return no('browser policy equivalence refused: %s' % error)
    debrand_proof = (rt.get('rework') or {}).get('debrand_delta')
    if isinstance(debrand_proof, dict):
        try:
            import importlib.util
            file = Path(__file__).with_name('debrand_delta_guard.py')
            spec = importlib.util.spec_from_file_location('_delivery_debrand_delta', file)
            guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
            verified = guard.validate(debrand_proof['old_zip']['path'], files, adapter, debrand_proof['scope']['path'])
            if verified != debrand_proof:
                return no('exact debrand source/scene proof changed on delivery readback')
            inherited = verified['inherited_ad']
            adapter_equivalence = ad.get('adapter_sha256') == inherited['original_adapter_sha256']
            tool_equivalence = ad.get('tool_sha256') == inherited['original_tool_sha256']
        except Exception as error:
            return no('debrand inherited ad identity refused: %s' % error)
    from regression_scope_gate import needs_ad_suite
    if needs_ad_suite(files, adapter, ad_regression_gate, runtime_regression_gate):
        if ad.get('status') != 'passed' or ad.get('passed') is not True:
            return no('the writer did not prove the rewarded-ad regression on a package that needs it')
        if adapter_sha is None or (ad.get('adapter_sha256') != adapter_sha and not adapter_equivalence):
            return no('adapter differs from the one the writer ran (rewarded-ad regression)')
        if ad.get('tool_sha256') != ad_regression_gate.tool_digest() and not tool_equivalence:
            return no('rewarded-ad regression tool differs from the one the writer ran')
    elif ad.get('status') != 'not_applicable':
        return no('rewarded-ad record does not fit this package')
    rr = runtime_regression_gate
    if 'game.js' in files:
        if rt.get('status') != 'passed' or rt.get('passed') is not True:
            return no('the writer did not prove the runtime regression')
        if adapter_sha is None or rt.get('adapter_sha256') != adapter_sha:
            return no('adapter differs from the one the writer ran (runtime regression)')
        try:
            catalog = rr.load_suites()
            judged = rr.package_policy(files, policy)[0]
        except rr.RuntimeRefused as error:
            return no(str(error))
        if rt.get('tool_sha256') != rr.tool_digest(catalog):
            return no('runtime regression tools differ from the ones the writer ran')
        if rt.get('policy') not in ('new', judged):
            return no('the writer ran the runtime suites as a %s game; this check judges it %s'
                      % (rt.get('policy'), judged))
    elif rt.get('status') != 'not_applicable':
        return no('runtime record does not fit this package')
    try:
        coverage_problem = regression_coverage_problem(ad, rt, files, adapter, policy)
    except (ValueError, OSError, TypeError) as error:
        return no('writer regression coverage cannot be verified: %s' % error)
    if coverage_problem:
        return no(coverage_problem)
    source = str(receipt_file)
    return {'reused': True, 'receipt': source,
            'regression_scope': receipt.get('regression_scope'),
            'note': 'reused from the writer receipt %s: same ZIP bytes, adapter and check tools, not run again '
                    '(总表 19 ①)' % Path(source).name,
            'rewarded_ad_regression': dict(ad, reused_from=source),
            'runtime_regression': dict(rt, reused_from=source)}


def writer_regressions(files, folder, adapter=None, policy=None, board=None, rework_of=None, *,
                       project=None, expected_scope_sha256=None):
    """v7.8 (W97, 总表 22.6 D/E): the rewarded-ad and runtime regressions for make_tiktok_zip.py, which does not call
    check(). Same two gates as check() (rewarded_ad_gate, then runtime_gate with the same adapter, policy and board) on
    the staged bytes of the ZIP about to be published. Never raises: -> {blocked, problems, warnings, policy, adapter,
    rewarded_ad_regression, runtime_regression, seconds}. Scope errors and missing evidence refuse publication
    even on the legacy list; the legacy policy still applies to individual suite verdicts and warnings.
    rework_of (简化.11.15): the last passed package (make_tiktok_zip --rework-of); out['rework'] is the plan."""
    import time
    started = time.monotonic()
    out = {'id': 'writer_regressions', 'rewarded_ad_regression': None, 'runtime_regression': None,
           'problems': [], 'warnings': []}
    try:
        project, adapter, board, policy = regression_context(files, folder, adapter, board, policy, project)
        out.update(policy=policy, board=board, adapter=str(adapter) if adapter else None)
        out['regression_scope'] = verify_regression_scope(
            files, folder, adapter, board, policy, rework_of, project=project,
            expected_scope_sha256=expected_scope_sha256, operation='writer')
    except (ValueError, OSError, TypeError) as error:
        out.update(status='scope_required', blocked=True, problems=[str(error)],
                   seconds=round(time.monotonic() - started, 1))
        return out
    legacy = policy == 'legacy'
    reasons = []
    for key, gate in (('rewarded_ad_regression', lambda: rewarded_ad_gate(files, folder, adapter)),
                      ('runtime_regression', lambda: runtime_gate(files, folder, adapter, policy=policy, board=board))):
        try:
            out[key] = gate()
        except Exception as error:  # noqa: BLE001 - fail closed: a crash refuses a new game like a failed case
            text = str(error) if isinstance(error, ValueError) else '%s crashed: %r' % (key, error)
            if not adapter and not any(NO_ADAPTER_HINT in r for r in reasons):
                text += ' - no adapter given: ' + NO_ADAPTER_HINT
            reasons.append(text)
            partial = getattr(error, 'summary', None) or getattr(error.__context__, 'summary', None)   # runtime_gate
            # re-raises RuntimeRefused as ValueError. 总表 P19: an input that was missing keeps 「未执行」 (not_run).
            status = partial.get('status') if isinstance(partial,dict) and partial.get('status') in ('not_run','scope_required') else 'failed'
            out[key] = dict(partial, status=status) if isinstance(partial, dict) else {'id': key, 'status': status,
                                                                                       'error': text[:2000]}
    if isinstance(out['runtime_regression'], dict):
        out['warnings'].extend(out['runtime_regression'].get('warnings') or [])
    if legacy:
        out['warnings'].extend('%s [legacy game: warning]' % r for r in reasons)
        for key in ('rewarded_ad_regression','runtime_regression'):
            part=out.get(key) or {}
            if part.get('proof_error') or part.get('status')=='scope_required':
                out['problems'].append(key+'：检查证据/范围无效，旧游戏也不能降级为通过')
        # This one suite is required when a legacy game is exported again, too.
        # Keep the legacy policy for all the other checks.
        if 'game.js' in files and runtime_regression_gate.predicate('missions', files, {}):
            runtime = out['runtime_regression'] or {}
            if not any(r.get('suite') == 'growth_entry' and r.get('passed') is True and r.get('cases')
                       for r in runtime.get('suites') or []):
                out['problems'].append('growth_entry: the sidebar and shortcut runtime check must pass on this build')
    else:
        out['problems'] = reasons
    if not out['problems']:
        try:
            ad, runtime = out['rewarded_ad_regression'], out['runtime_regression']
            problem = ('writer did not produce complete passing regression evidence'
                       if regression_record(ad, runtime) is None else
                       regression_coverage_problem(ad, runtime, files, adapter, policy))
        except (ValueError, OSError, TypeError) as error:
            problem = str(error)
        if problem:
            out['problems'].append(problem)
    out['blocked'] = bool(out['problems'])
    out['seconds'] = round(time.monotonic() - started, 1)
    return out


def _fallback_entries(archive):
    """Entries of a ZIP the verifier refused, so the remaining checks can still list their reasons.
    Unsafe or forbidden names are left out (they are already the verifier's reason)."""
    out = {}
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            if info.is_dir() or info.flag_bits & 1:
                continue
            try:
                verifier.safe_name(info.filename)
            except ValueError:
                continue
            if verifier.forbidden(info.filename):
                continue
            out[info.filename] = z.read(info)
    return out


def check(archive, app_id=None, tree=None, ad_regression=None, board=None, policy=None, context=None,
          reuse_writer_regressions=False, rework_of=None, *, expected_scope_sha256=None, project=None):
    # 简化.11.15 (出包后返工): rework_of (build_checked_zip --rework-of) is the last passed package; when only pictures,
    # sounds or fonts changed since it, the browser suites that cannot see the change keep its passes (rework_scope).
    # v7.9 (出包检查提速 S1, 总表 19 ①): reuse_writer_regressions (prepare_delivery only) takes an official writer
    # receipt's record of the two regressions for the same bytes, adapter and check tools (reusable_regressions).
    """Read-only final check of the exact bytes. Every reason is collected and the package is refused ONCE with
    all of them (verifier, Credits/no-ad-simulator, startup, packed assets, shared package gates, rewarded-ad
    and runtime regressions) instead of stopping at the first (MusicSlice 0f).
    v7.9 (总表 19 ④): when the static checks (verifier, startup, packed assets, package gates) already refuse, the two
    browser regressions are not run - the package has to be rebuilt anyway and the 7.5-15 minutes would be thrown
    away; the refusal still lists every static reason at once and ends with BROWSER_SKIPPED_NOTE.

    ad_regression: adapter JSON path for the mandatory rewarded-ad regression; falls back to
    $TIKTOK_AD_REGRESSION_ADAPTER. A package that can request a rewarded video is refused
    without a passing regression (no adapter, no browser and a failed case all refuse).
    board: 'remake' | 'localize' | None; the package gates use it only to choose block vs warning.
    policy (v7.7): 'new' | 'legacy' from a writer's finalize record; None (check_package.py given only a ZIP, and
    prepare_delivery.py) = judged from the package bytes (scene / asset uuids against LEGACY_GAMES.json, not listed
    = new). context: writer-only kit_parts attributes (finalize record, project) for K4/K5."""
    import package_gates
    start_sha = hashlib.sha256(Path(archive).read_bytes()).hexdigest()
    reasons = []
    verified_files = {}
    try:
        result = verifier.verify(archive, expected_app_id=app_id, _verified_files=verified_files)
    except ValueError as error:
        reasons.append('verifier: ' + str(error))
        result = None
        verified_files = _fallback_entries(archive)
        from audit_no_ad_simulator import check_entry
        window_hit = False
        for name in sorted(verified_files):
            try:
                check_entry(name, verified_files[name])
            except ValueError as entry_error:
                window_hit = True
                if str(entry_error) not in reasons[0]:
                    reasons.append(str(entry_error))
        # Same boundary as make_tiktok_zip.native_problems: never run the startup audit (Node probes execute
        # package JS) on a package that still carries a player window; the static package gates still run.
        if 'game.js' in verified_files and not window_hit:
            from audit_upload_startup import audit_files
            startup = audit_files(verified_files)
            reasons.extend(e for e in startup['errors'] if e not in reasons[0])
    if tree is not None and result is not None:
        expected = {name: hashlib.sha256(data).hexdigest() for name, data in native_files(Path(tree)).items()}
        if expected != result['file_sha256']:
            reasons.append('final ZIP differs from actual Native input paths/bytes')
        else:
            result['expected_tree_exact'] = True
    project = project or (context or {}).get('project')
    project, ad_regression, board, policy = regression_context(
        verified_files, tree or Path(archive).parent, ad_regression, board, policy, project)
    gates = package_gates.run(verified_files, None, board, policy=policy, context=context)
    reasons.extend(package_gates.messages(gates['blocks']))
    regression = runtime = None
    # v7.9 (出包检查提速 S1, 总表 19 ①): prepare_delivery reuses what the official writer ran on exactly these bytes with
    # this adapter and these check tools (its receipt keeps the record) instead of running it again.
    reuse = None
    if reuse_writer_regressions:
        reuse = (reusable_regressions(result.get('receipt'), verified_files, ad_regression, gates.get('policy'))
                 if result is not None and result.get('entry') == 'official'
                 else {'reused': False, 'why': 'not a ZIP an official writer wrote (no matching receipt)'})
    reused = bool(reuse and reuse.get('reused'))
    if reuse_writer_regressions and not reused:
        reasons.append('scope_required: delivery can only verify matching writer evidence: ' + reuse['why'])
    scope_audit = reuse.get('regression_scope') if reused else None
    browser_skipped = False
    with tempfile.TemporaryDirectory(prefix='TikTok package extract ') as folder:
        # Paths and CRC were validated above; stage those exact bytes, not a second ZIP read.
        for name, data in verified_files.items():
            target = Path(folder) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        assets = packed_assets(folder)
        if not assets['passed']:
            reasons.append('packed resource check: ' + '; '.join(assets['errors']))
        # v7.9 (总表 19 ④): already refused by the static checks above -> the browser suites wait for the new package.
        browser_skipped = bool(reasons) and not reused
        if reused:
            regression, runtime = reuse['rewarded_ad_regression'], reuse['runtime_regression']
        elif not browser_skipped:
            scope_audit = verify_regression_scope(
                verified_files, tree or folder, ad_regression, board, gates.get('policy'), rework_of,
                project=project, expected_scope_sha256=expected_scope_sha256,
                operation='writer' if expected_scope_sha256 is not None else 'check')
            try:
                regression = rewarded_ad_gate(verified_files, folder, ad_regression)
            except ValueError as error:
                reasons.append(str(error))
            try:
                runtime = runtime_gate(verified_files, folder, ad_regression, policy=gates.get('policy'), board=board)
            except ValueError as error:
                reasons.append(str(error))
            if not reasons:
                if regression_record(regression, runtime) is None:
                    reasons.append('writer did not produce complete passing regression evidence')
                else:
                    problem = regression_coverage_problem(regression, runtime, verified_files, ad_regression,
                                                          gates.get('policy'))
                    if problem:
                        reasons.append(problem)
    if hashlib.sha256(Path(archive).read_bytes()).hexdigest() != (result['sha256'] if result else start_sha):
        raise ValueError('ZIP changed during package checks')
    if reasons:
        tail = [BROWSER_SKIPPED_NOTE] if browser_skipped else []
        if len(reasons) == 1:
            raise ValueError(' || '.join(reasons + tail))
        raise ValueError('%d reasons, all listed: ' % len(reasons) + ' || '.join(reasons + tail))
    result['packed_resource_check'] = assets
    result['rewarded_ad_regression'] = regression
    result['runtime_regression'] = runtime
    result['regression_scope'] = scope_audit
    if reuse is not None:
        result['regression_reuse'] = {k: reuse[k] for k in ('reused', 'why', 'note', 'receipt') if k in reuse}
    result['package_gates'] = package_gates.summary(gates)
    from make_tiktok_zip import pre_home
    result['pre_home_bytes'] = pre_home(verified_files, None, board)
    # v7.8 (S8 补): the static estimate above (W8_prehome_bytes, 15 MB warning) next to what the host measured
    # (layout_state startup_size / startup_audio: 10 MiB and no sound, the number that blocks)
    if isinstance(result['pre_home_bytes'], dict) and isinstance(runtime, dict):
        result['pre_home_bytes']['measured'] = runtime.get('startup_measured')
    result['board'] = board
    result['policy'] = gates.get('policy')
    result['policy_reason'] = gates.get('policy_reason')
    # Encoding and decoding are distinct capabilities. Never silently treat
    # a successful static archive check as WebP runtime coverage.
    webp = sorted(name for name in result['file_sha256'] if name.lower().endswith('.webp'))
    result['runtime_requirements'] = []
    if webp:
        result['runtime_requirements'].append({
            'id': 'webp_decode_capability', 'status': 'requires_runtime_evidence',
            'resource_count': len(webp), 'resources': webp,
            'reference': 'cocos-game-check/package-check/references/webp-decode-capability.md',
            'cases': ['png_only_encoder_working_decoder_old_failure',
                      'png_only_encoder_working_decoder_fixed_success',
                      'normal_encoder_control', 'decoder_error_not_enabled',
                      'decoder_timeout_not_enabled', 'zero_dimensions_not_enabled',
                      'duplicate_terminal_once'],
            'boundary': 'Static detection only. Use actual final Native engine/adapter; do not force webp=true or count Canvas encoding as decoding.'})
    result['runtime_execution'] = 'not_executed_by_static_package_checker'
    # v7.8 (总表 B32 d): which check tools judged this package; changed / not installed ones are listed, never a refusal.
    result['tool_identity'] = tools_in_use()
    if result['tool_identity'].get('status') == 'modified':
        result['modified_tools'] = result['tool_identity']['summary']
        result.setdefault('warnings', []).append('改过的工具: ' + '; '.join(result['tool_identity']['summary']))
    return result


def tools_in_use():
    """tool_identity.identity() of the tools in this folder; an error is reported, never raised."""
    try:
        import tool_identity
        return tool_identity.identity(Path(__file__).resolve().parent)
    except Exception as error:  # noqa: BLE001 - reporting only
        return {'status': 'error', 'error': repr(error)[:300], 'modified': [], 'summary': []}


def feedback_draft(identity, game):
    """Write the 改过的工具 feedback draft into ！Skill更新/ (tool_identity.write_draft). -> path or None."""
    if not isinstance(identity, dict) or identity.get('status') != 'modified':
        return None
    try:
        import tool_identity
        path = tool_identity.write_draft(identity, game)
        return str(path) if path else None
    except Exception as error:  # noqa: BLE001 - a draft that cannot be written never changes the verdict
        print('改过的工具：反馈草稿没写成：%r' % (error,), file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--expected-app-id')
    parser.add_argument('--expected-tree', type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--ad-regression', type=Path, help='adapter JSON for the mandatory rewarded-ad and runtime regressions '
                        '(default $%s)' % ad_regression_gate.ENV_ADAPTER)
    parser.add_argument('--board', choices=['remake', 'localize'], help='remake | localize; package gates use it only '
                        'to choose block vs warning (default: unknown)')
    parser.add_argument('--policy', choices=['new', 'legacy'], help='tests and calibration only (design D77 3): '
                        'judge the package as a new or a legacy game. Default: from the package itself (frozen '
                        'legacy list; not listed = new). The writers and prepare_delivery.py never pass it')
    parser.add_argument('--structure-only', action='store_true',
                        help='read-only diagnosis: run every check but do not refuse a ZIP without a matching writer '
                        'receipt (the answer is then not a delivery approval)')
    args = parser.parse_args()
    refused = None
    try:
        if args.report and args.report.exists():
            raise ValueError('refuse to overwrite report')
        if args.input.is_dir():
            with tempfile.TemporaryDirectory(prefix='TikTok Native preflight ') as temp:
                zipped = Path(temp) / 'candidate.zip'
                write_archive(zipped, native_files(args.input))
                result = check(zipped, args.expected_app_id, args.input, args.ad_regression, args.board, args.policy)
                result['input'] = str(args.input.resolve())
                result.pop('archive', None)
            result['verdict'] = READ_ONLY_DIR
        else:
            result = check(args.input, args.expected_app_id, args.expected_tree, args.ad_regression, args.board, args.policy)
            # v7.8 (总表 B17): check() is unchanged (the writers import it); only this command refuses a ZIP that no
            # official writer wrote, as verify_native_zip.py / upload_preflight.py do since v7.7.4.
            if result.get('entry') == 'official':
                result['verdict'] = OFFICIAL_VERDICT
            elif args.structure_only:
                result.update(verdict=READ_ONLY_VERDICT, mode='structure-only (not a delivery approval)')
            else:
                refused = UNOFFICIAL_CLI % result.get('entry_reason')
                result.update(status='unofficial_not_deliverable', verdict=READ_ONLY_VERDICT, refused=refused)
        # v7.8 (总表 B32 d): changed tools get a feedback draft for the Skill session (new file in ！Skill更新/).
        draft = feedback_draft(result.get('tool_identity'), args.input.stem)
        if draft:
            result['tool_feedback_draft'] = draft
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({k:v for k,v in result.items() if k not in ('file_sha256', 'packed_resource_check', 'tool_identity')}, ensure_ascii=False))
        if result.get('modified_tools'):
            print('改过的工具: %s%s' % ('; '.join(result['modified_tools']),
                                     '（反馈草稿：%s）' % draft if draft else ''), file=sys.stderr)
        print('结论: %s' % result['verdict'], file=sys.stderr)
    except (ValueError, OSError, RuntimeError, zipfile.BadZipFile) as error:
        identity = tools_in_use()       # a refusal made with changed tools is reported the same way
        out = {'status': 'refuse', 'error': str(error)}
        if identity.get('status') == 'modified':
            out.update(modified_tools=identity['summary'], tool_feedback_draft=feedback_draft(identity, args.input.stem))
        print(json.dumps(out, ensure_ascii=False))
        return 1
    if refused:
        print('REFUSED: ' + refused, file=sys.stderr)
        return 3
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
