"""Read-only migration of genuine legacy aggregate observations to precise units.

This module does not execute tests or create ledger records. A derived reuse row
retains the original aggregate binding, time, files and complete source record.
The independently passing observation is the only thing projected to a new ID.
"""
import copy
import hashlib
import json
from pathlib import Path

import check_ledger as CL


FIXTURES = Path(__file__).with_name('fixtures') / 'reviewed-legacy-suites'
OLD_SHA = {
    'ad_outcome': '07ea1ec2e46ff8c5550084d9ea70c35bbd28c49fdce6fbb1a0490063b016d4a1',
    'save_restart': '22876a5015ed801ed369afad6a4b70210b8b0ac31701c0146b360eb07f7fccfc',
}
NEW_SHA = {
    'ad_outcome': 'e76f459d4438b62522ee0dd7474f25fe09c7cffe873617b9aea612d16873716f',
    'save_restart': 'd10ca32a95e4f01b6beac01d2cac4cf6f5ebc27f03b2a41349bcc6c2e12a8262',
}
REVIEW_SHA = '6d469304d0ba3a2dc415e677ce9cb92b807dca862b7476fcced26dc05545d912'


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _reviewed_source(suite, script):
    """Review binds whole old/new files; no arbitrary source/target tool strings."""
    old = (FIXTURES / (suite + '.mjs')).read_bytes()
    new = Path(script).read_bytes()
    review_raw = (FIXTURES / 'unit-rule-review.json').read_bytes()
    if _digest(review_raw) != REVIEW_SHA:
        raise CL.NeedsScope(suite + '：固定的规则审查清单已经变化，先重新审查')
    review = json.loads(review_raw)
    row = review['suites'][suite]
    if (review.get('schema') != 'runtime-unit-rule-review.v1'
            or _digest(old) != OLD_SHA[suite]
            or row.get('old_sha256') != OLD_SHA[suite]
            or row.get('new_sha256') != NEW_SHA[suite]
            or _digest(new) != NEW_SHA[suite]):
        raise CL.NeedsScope(suite + '：独立项判定器与固定的整文件审查对不一致，先核对规则变化')
    # Every edit is explicit and bound to old byte offsets. Reconstructing the
    # whole target detects any unreviewed byte, including changes outside asserts.
    cursor = 0
    rebuilt = bytearray()
    for edit in row['edits']:
        start, end = edit['old_start'], edit['old_end']
        if not cursor <= start <= end <= len(old):
            raise CL.NeedsScope(suite + '：规则审查的字节范围无效')
        if old[start:end].decode() != edit['old']:
            raise CL.NeedsScope(suite + '：规则审查的原文不匹配')
        rebuilt.extend(old[cursor:start])
        rebuilt.extend(edit['new'].encode())
        cursor = end
    rebuilt.extend(old[cursor:])
    if bytes(rebuilt) != new:
        raise CL.NeedsScope(suite + '：存在固定审查之外的判定器改动')
    for assertion in row['unchanged_assertions']:
        if assertion not in old.decode() or assertion not in new.decode():
            raise CL.NeedsScope(suite + '：原始判定断言正文没有逐字保留')
    if not row['unchanged_assertions']:
        raise CL.NeedsScope(suite + '：缺少原始判定断言的完整审查块')
    return old


def _rule_pair(suite, script, conditions):
    import runtime_regression as rr
    import runtime_incremental as incremental
    import runtime_timing as timing

    script = Path(script).resolve()
    old = _reviewed_source(suite, script)
    host = rr.HOST3 if conditions.get('engine') == '3.x' else rr.HOST2
    common = [p for p in rr.TOOL.glob('*.mjs') if p.name != 'frame_rate_compare.mjs']
    paths = [Path(rr.__file__), script, script.with_suffix('.json'), *common, host,
             Path(incremental.__file__), Path(CL.__file__)]
    # Compatibility approval still examines the real scheduler/helper/ledger.
    # Only this fixed, reviewed old suite body is overlaid for the source digest.
    return (timing.rule_fingerprint(CL, paths, source_overrides={script: old}),
            timing.rule_fingerprint(CL, paths))


def _bound_raw(source):
    files = source.get('files')
    result = source.get('result')
    if not isinstance(files, list) or not files or not isinstance(result, dict):
        raise CL.NeedsScope('原 aggregate 缺少已冻结且带 SHA 的原始证据')
    bound = {}
    for item in files:
        path = Path(item['path']).resolve()
        if not path.is_file() or _digest(path.read_bytes()) != item.get('sha256'):
            raise CL.NeedsScope('原 aggregate 证据丢失或 SHA 已变化：' + str(path))
        bound[str(path)] = item['sha256']
    raw_files = result.get('raw_files')
    if not isinstance(raw_files, list) or not raw_files:
        raise CL.NeedsScope('原 aggregate 没有原始运行文件清单')
    if any(str(Path(path).resolve()) not in bound for path in raw_files):
        raise CL.NeedsScope('原 aggregate 原始文件没有全部绑定冻结 SHA')
    evidence = result.get('evidence')
    report_path = evidence.get('report') if isinstance(evidence, dict) else None
    if not report_path or str(Path(report_path).resolve()) not in bound:
        raise CL.NeedsScope('原 aggregate 缺少绑定 SHA 的 suite 原始 report')
    report = json.loads(Path(report_path).read_text())
    raw_results = []
    for path in raw_files:
        if Path(path).suffix != '.json':
            continue
        try:
            value = json.loads(Path(path).read_text())
        except (OSError, UnicodeError, ValueError):
            continue
        if isinstance(value, dict) and value.get('suite') == result.get('suite') and 'passed' in value:
            raw_results.append(value)
    if len(raw_results) != 1:
        raise CL.NeedsScope('原 aggregate 缺少唯一的原始 suite 判定结果文件')
    raw_result = raw_results[0]
    # Stored normalized cases may omit fields; verdict IDs, status and detail
    # must still be identical to the independently frozen original result.
    normalize = lambda rows: [{key: row.get(key) for key in ('id', 'passed', 'detail')}
                              for row in rows if isinstance(row, dict)]
    if normalize(raw_result.get('cases') or []) != normalize(result.get('cases') or []):
        raise CL.NeedsScope('原 aggregate 的归档 case 与原始结果不一致')
    if source.get('error') or raw_result.get('fatal') or result.get('fatal') \
            or result.get('batch_problems') or result.get('proof_error'):
        raise CL.NeedsScope('原 aggregate 存在全局运行/判定错误，不能拆出通过项')
    if raw_result.get('passed') is not source.get('passed'):
        raise CL.NeedsScope('原 aggregate 总判定与原始结果不一致')
    return report, result


def _one(rows, predicate):
    matches = [row for row in rows if isinstance(row, dict) and predicate(row)]
    return matches[0] if len(matches) == 1 else None


def _ad_cases(report, result, unit, source_passed):
    entries, observations = report.get('entries'), report.get('cases')
    if not isinstance(entries, list) or not isinstance(observations, list):
        return None
    if unit == '@discovered':
        if source_passed is not True:
            return None
        ids = [entry.get('id') for entry in entries if entry.get('from') == 'button_sweep']
        if len(ids) != len(set(ids)):
            return None
        cases = []
        for check_id in ids:
            part = _ad_cases(report, result, check_id, source_passed)
            if part is None:
                return None
            cases.extend(part)
        # The fixed aggregate source completed the discovery catalogue even if
        # no discovered entry needed an ad journey.
        return cases or [{'id': '@discovered', 'passed': True,
                          'detail': 'Original complete aggregate observed no additional discovered entries'}]
    entry = _one(entries, lambda item: item.get('id') == unit)
    observation = _one(observations, lambda item: item.get('id') == unit)
    if not entry or not observation or any(observation.get(kind + '_result') != 'pass'
                                           for kind in ('cancel', 'complete')):
        return None
    cases = []
    for kind in ('cancel', 'complete'):
        case = _one(result.get('cases') or [], lambda item: item.get('id') == unit + '/' + kind)
        if not case or case.get('passed') is not True:
            return None
        cases.append(case)
    return cases


def _save_cases(report, result, unit, source_passed):
    if source_passed is not True or report.get('result') != 'pass':
        return None
    restart = _one(result.get('cases') or [], lambda item: item.get('id') == 'restart')
    if not restart or restart.get('passed') is not True:
        return None
    if unit == '@kinds':
        kinds = report.get('kinds')
        if not isinstance(kinds, dict) or kinds.get('missing') != []:
            return None
        return [{'id': '@kinds', 'passed': True, 'detail': copy.deepcopy(kinds)}]
    if not unit.startswith('step/'):
        return None
    step = _one(report.get('steps') or [], lambda item: item.get('name') == unit[5:])
    if (not step or step.get('stuck') or any(key not in step for key in ('before', 'after', 'after_restart'))
            or CL.canonical(step['before']) == CL.canonical(step['after'])
            or CL.canonical(step['after']) != CL.canonical(step['after_restart'])
            or any(isinstance(step[key], dict) and step[key].get('adapterError')
                   for key in ('before', 'after', 'after_restart'))):
        return None
    return [{'id': unit, 'passed': True, 'detail': copy.deepcopy(step)}]


def reuse_unit(store, plan, suite, unit, script):
    """Return a derived reuse plan, or the unchanged scoped run plan.

    Existing precise-ID history always wins. Missing/corrupt aggregate evidence
    or unreviewed rule changes require diagnosis instead of scheduling every new
    ID. A changed relevant input or a genuinely unproven unit remains ``run`` and
    must still pass the caller's original per-ID authorization gate.
    """
    cid = 'runtime.' + suite + '/' + unit
    if (suite not in OLD_SHA or unit == '@suite' or plan.get('action') != 'run'
            or plan.get('check_id') != cid or store.previous(cid)):
        return plan
    sources = store.previous('runtime.' + suite + '/@suite')
    if not sources:
        return plan
    scope = plan.get('scope')
    if not scope or not scope.get('inputs') or not scope.get('basis'):
        raise CL.NeedsScope(cid + '：先登记实际精确依赖，再关联旧 aggregate 观察')
    try:
        old_tool, current_tool = _rule_pair(suite, script, plan['binding']['conditions'])
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise CL.NeedsScope(cid + '：无法核准新旧判定器的精确等价：' + str(error)) from error
    if plan['binding'].get('tool_sha256') != current_tool:
        raise CL.NeedsScope(cid + '：当前计划未绑定实际独立项判定器')
    for source in sources:
        binding = source.get('binding') or {}
        if binding.get('conditions') != plan['binding']['conditions']:
            continue
        if binding.get('tool_sha256') != old_tool:
            raise CL.NeedsScope(cid + '：旧 aggregate 工具版本无法由固定审查对重建，先核对具体规则变化')
        if CL.select_inputs(source.get('roots') or {}, scope) != plan['binding']['inputs']:
            continue
        if (source.get('schema') != CL.SCHEMA or binding.get('schema') != CL.SCHEMA
                or source.get('check_id') != 'runtime.' + suite + '/@suite'
                or binding.get('check_id') != source.get('check_id')):
            raise CL.NeedsScope(cid + '：旧 aggregate 原记录身份不完整')
        report, result = _bound_raw(source)
        if report.get('suite') != suite or result.get('suite') != suite \
                or report.get('policy') != binding['conditions'].get('policy'):
            raise CL.NeedsScope(cid + '：旧 report 对应的 suite 或执行条件不一致')
        cases = (_ad_cases(report, result, unit, source.get('passed')) if suite == 'ad_outcome'
                 else _save_cases(report, result, unit, source.get('passed')))
        if cases is None:
            return plan
        observation = dict(suite=suite, unit=unit, passed=True, cases=copy.deepcopy(cases),
                           problems=[], proof_error=False, warnings=result.get('warnings') or [],
                           evidence=copy.deepcopy(result.get('evidence')), raw_files=copy.deepcopy(result['raw_files']),
                           seconds=source['seconds'], browser=result.get('browser', True),
                           source_passed=source.get('passed'), source_problems=copy.deepcopy(result.get('problems') or []))
        derived = copy.deepcopy(source)
        derived.update(passed=True, result=observation, observation_kind='derived_legacy_unit',
                       source_passed=source.get('passed'), source_record=copy.deepcopy(source),
                       source_key=CL.sha(binding), source_unit=unit)
        reused = copy.deepcopy(plan)
        reused.update(action='reuse', record=derived,
                      why='原 aggregate 的真实独立观察、原条件、精确依赖与固定判定器审查对一致；未启动新测试')
        return reused
    return plan


def legacy_unit(check_id):
    """Return a supported (suite, unit) without treating a rename as a new test."""
    for suite in OLD_SHA:
        prefix = 'runtime.' + suite + '/'
        if isinstance(check_id, str) and check_id.startswith(prefix) and check_id[len(prefix):] != '@suite':
            return suite, check_id[len(prefix):]
    return None


def _legacy_probe(records, plan, source, *, compare_archive=False, script=None):
    suite, unit = legacy_unit(plan['check_id'])
    source_id = 'runtime.' + suite + '/@suite'

    class OriginalRecordView:
        def previous(self, check_id):
            return [source] if check_id == source_id else []

    probe = copy.deepcopy(plan)
    probe.update(action='run', record=None)
    if compare_archive:
        probe['roots'] = copy.deepcopy(source['roots'])
        probe['binding']['inputs'] = CL.select_inputs(source['roots'], probe.get('scope'))
        probe['key'] = CL.sha(probe['binding'])
    script = script or (Path(__file__).resolve().parents[2]
                        / 'cocos-game-check/package-check/scripts/runtime_regression/suites' / (suite + '.mjs'))
    result = reuse_unit(OriginalRecordView(), probe, suite, unit, script)
    return result['record'] if result['action'] == 'reuse' else None


def verify_derived_source(records, plan, *, script=None):
    """Rebuild a claimed derived row from the actual read-only DB record view.

    ``records`` maps check IDs to the validated ``(key, record)`` pairs read by
    regression_baseline. The claimed embedded source is never trusted by itself.
    """
    identity = legacy_unit(plan.get('check_id'))
    claimed = plan.get('record')
    if not identity or not isinstance(claimed, dict) or claimed.get('observation_kind') != 'derived_legacy_unit':
        return None
    source_id = 'runtime.' + identity[0] + '/@suite'
    actual = next((source for key, source in records.get(source_id, [])
                   if key == claimed.get('source_key') and source == claimed.get('source_record')), None)
    if actual is None:
        raise CL.NeedsScope(plan['check_id'] + '：派生观察的原 aggregate 不在真实 ledger 中')
    derived = _legacy_probe(records, plan, actual, script=script)
    if derived is None or derived != claimed:
        raise CL.NeedsScope(plan['check_id'] + '：派生观察与真实 aggregate、原始文件或当前精确依赖不一致')
    return derived


def legacy_comparison_source(records, plan, archive_manifest, *, script=None):
    """Recover a real old-archive unit observation even when this unit must run.

    It projects the *old* roots through the current precise scope, while retaining
    all original conditions, assertions and raw evidence checks. Its identity is
    independent of whether the new unit is pending or has since completed.
    """
    identity = legacy_unit(plan.get('check_id'))
    if not identity:
        return None
    source_id = 'runtime.' + identity[0] + '/@suite'
    for key, source in records.get(source_id, []):
        if source.get('roots', {}).get('package') != archive_manifest:
            continue
        derived = _legacy_probe(records, plan, source, compare_archive=True, script=script)
        # Do not bypass a newer contradictory observation with an older pass.
        return derived
    return None


def legacy_observation_exists(records, plan, archive_manifest):
    """A previously observed failure cannot be renamed as a brand-new check."""
    identity = legacy_unit(plan.get('check_id'))
    if not identity:
        return False
    suite, unit = identity
    for _, source in records.get('runtime.' + suite + '/@suite', []):
        if source.get('roots', {}).get('package') != archive_manifest:
            continue
        report, result = _bound_raw(source)
        if report.get('suite') != suite:
            raise CL.NeedsScope(plan['check_id'] + '：旧 aggregate 的 suite 报告身份不一致')
        if suite == 'ad_outcome':
            if unit == '@discovered':
                return isinstance(report.get('entries'), list)
            return any(item.get('id') == unit for item in report.get('entries') or [] if isinstance(item, dict))
        if unit == '@kinds':
            return isinstance(report.get('kinds'), dict)
        return unit.startswith('step/') and any(item.get('name') == unit[5:]
                                                for item in report.get('steps') or [] if isinstance(item, dict))
    return False
