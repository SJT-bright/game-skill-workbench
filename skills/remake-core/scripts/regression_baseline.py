#!/usr/bin/env python3
"""Read-only identities for official ZIPs and explicitly bounded evidence recovery.

A recovery identity is a comparison baseline, never a receipt or an approval of the
old archive. Callers must supply the complete groups returned by their actual runners
and still apply normal dependency, execution-scope and package gates afterwards.
"""
import json
from pathlib import Path, PurePosixPath
import sqlite3
from urllib.parse import quote
import zipfile

import check_ledger as ledger

SCHEMA = 'cocos-regression-baseline-recovery.v1'


def fail(reason):
    raise ledger.NeedsScope('基线恢复：' + reason)


def digest(path):
    return ledger.sha(Path(path).read_bytes())


def package_manifest(files):
    return {name: ledger.sha(data) for name, data in files.items()
            if not set(PurePosixPath(name).parts) & ledger.IGNORED
            and not name.startswith('docs/checks/incremental/')}


def _archive(path):
    from verify_native_zip import safe_name
    if not path.is_file():
        fail('找不到原交付 ZIP，禁止自动切到全量')
    before = digest(path)
    files = {}
    try:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = safe_name(info.filename).as_posix()
                if name in files:
                    fail('原交付 ZIP 存在重复条目')
                files[name] = archive.read(info)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        fail('原交付 ZIP 无法读取：' + str(error))
    if digest(path) != before:
        fail('原交付 ZIP 在读取期间变化')
    return before, files


def _check_app_id(old, current):
    for name in ('project.config.json', 'game.json'):
        try:
            a, b = json.loads(old.get(name, b'{}')), json.loads(current.get(name, b'{}'))
        except (ValueError, UnicodeError):
            fail(name + ' 不是有效 JSON')
        if not isinstance(a, dict) or not isinstance(b, dict):
            fail(name + ' 必须为 JSON 对象')
        for key in ('appId', 'appid', 'app_id'):
            if a.get(key) and b.get(key) and a[key] != b[key]:
                fail('上一交付 ZIP 的 App ID 不匹配')


def _receipt_gap(status, archive_sha, manifest):
    """Missing/mismatched metadata can recover; recorded real refusals cannot."""
    from verify_native_zip import tree_digest
    path = Path(status['receipt'])
    if not path.exists():
        return {'status': 'missing', 'path': str(path), 'sha256': None,
                'entry': status['entry'], 'reason': status.get('entry_reason')}
    if path.is_symlink() or not path.is_file():
        fail('原回执不是可核对的普通文件')
    try:
        receipt = json.loads(path.read_bytes())
    except (OSError, ValueError, UnicodeError):
        fail('原回执不可读，先核对原记录，不能据此绕过失败')
    if not isinstance(receipt, dict):
        fail('原回执格式不正确')
    same_zip = receipt.get('zip_sha256') == archive_sha
    same_tree = receipt.get('native_tree_sha256') == tree_digest(manifest)
    if same_zip or same_tree:
        gate = receipt.get('gate_result')
        finalize = receipt.get('finalize')
        if (isinstance(gate, dict) and (gate.get('passed') is False or gate.get('blocks'))
                or isinstance(finalize, dict) and (finalize.get('blocks') or finalize.get('policy_override'))):
            fail('原回执记录了真实失败、拒绝或测试策略，不能降级恢复')
    if same_zip and same_tree:
        fail('同字节回执存在其他疑点，须修复原疑点，不能作为缺失/失配恢复')
    return {'status': 'mismatched', 'path': str(path), 'sha256': digest(path),
            'entry': status['entry'], 'reason': status.get('entry_reason')}


def _records(project, check_ids):
    """Read the real records table without creating a DB or changing ledger events."""
    path = project / 'docs/checks/incremental/ledger.sqlite3'
    if not path.is_file():
        fail('缺少原始 ledger，不能把全部缺证项登记为新项')
    try:
        db = sqlite3.connect('file:' + quote(str(path)) + '?mode=ro', uri=True)
        try:
            rows = db.execute('SELECT key, check_id, data FROM records ORDER BY rowid DESC').fetchall()
        finally:
            db.close()
    except sqlite3.Error as error:
        fail('原始 ledger 无法读取：' + str(error))
    result = {cid: [] for cid in check_ids}
    for key, cid, raw in rows:
        if cid not in result:
            continue
        try:
            row = json.loads(raw)
            binding = row['binding']
            if (row.get('schema') != ledger.SCHEMA or row.get('check_id') != cid
                    or binding.get('schema') != ledger.SCHEMA or binding.get('check_id') != cid
                    or ledger.sha(binding) != key or not isinstance(row.get('roots'), dict)
                    or not isinstance(binding.get('inputs'), dict)
                    or not isinstance(binding.get('conditions'), dict)
                    or not binding.get('tool_sha256') or not row.get('executed_at')
                    or not isinstance(row.get('files'), list)
                    or row.get('passed') not in (True, False)):
                fail(cid + ' 的原始 ledger 身份或时间不完整')
            for root, values in binding['inputs'].items():
                actual = row['roots'].get(root)
                if (not isinstance(actual, dict) or not isinstance(values, dict)
                        or any(k != '<selectors>' and actual.get(k) != v for k, v in values.items())):
                    fail(cid + ' 的原始 binding 与实际 roots 不一致')
            if row['passed'] and row.get('error'):
                fail(cid + ' 的通过记录同时含原始错误')
        except (ValueError, KeyError, TypeError, AttributeError) as error:
            if isinstance(error, ledger.NeedsScope):
                raise
            fail(cid + ' 的原始 ledger 不能解析：' + str(error))
        result[cid].append((key, row))
    return result


def _raw_files(cid, record, *, allow_missing=False):
    files = record.get('files')
    if not files:
        fail(cid + ' 的原记录缺少真实原始证据文件，不能仅凭 passed 恢复')
    out = []
    for item in files:
        if (not isinstance(item, dict) or not isinstance(item.get('path'), str)
                or not Path(item['path']).is_absolute() or not isinstance(item.get('sha256'), str)):
            fail(cid + ' 的原始证据身份不完整')
        path = Path(item['path'])
        try:
            actual = digest(path) if path.is_file() else None
        except OSError:
            actual = None
        if actual != item['sha256'] and not allow_missing:
            fail(cid + ' 的原始证据缺失或字节变化；先恢复原文件或登记此项补采')
        # Expected hashes are permanent provenance. Missing bytes are explicitly
        # represented, rather than promoted to a successful old observation.
        out.append({'path': str(path), 'sha256': item['sha256'], 'observed_sha256': actual})
    return sorted(out, key=lambda item: (item['path'], item['sha256']))


def _recheck(cid, source_key, source, config):
    request = config.get('evidence_rechecks', {}).get(cid)
    if not isinstance(request, dict) or request.get('prior_key') != source_key:
        return None
    searches = request.get('searched_locations')
    if (not isinstance(request.get('reason'), str) or not request['reason'].strip()
            or not isinstance(searches, list) or not searches
            or not all(isinstance(path, str) and Path(path).is_absolute() for path in searches)):
        fail(cid + ' 的证据补采缺少原因和已查找的绝对路径')
    files = _raw_files(cid, source, allow_missing=True)
    if all(item['sha256'] == item['observed_sha256'] for item in files):
        fail(cid + ' 的原证据仍有效，不能登记为证据丢失补采')
    return request


def _source(cid, key, record, kind, *, recheck=None):
    return {'kind': kind, 'key': key, 'binding': record['binding'],
            'roots_sha256': ledger.sha(record['roots']), 'record_sha256': ledger.sha(record),
            'executed_at': record['executed_at'], 'passed': record['passed'],
            'files': _raw_files(cid, record, allow_missing=recheck is not None),
            'evidence_recheck': recheck}


def _current_source(cid, row, records, all_records=None):
    claimed = row.get('record')
    if not isinstance(claimed, dict):
        fail(cid + ' 的沿用项没有原始 record')
    if claimed.get('observation_kind') == 'derived_legacy_unit':
        from runtime_unit_reuse import verify_derived_source
        derived = verify_derived_source(all_records or {}, row)
        if derived is None:
            fail(cid + ' 的派生观察没有可核对的真实 aggregate 来源')
        source = _source(cid, derived['source_key'], derived, 'derived_legacy_unit_observation')
        source.update(source_check_id=derived['source_record']['check_id'],
                      source_record_sha256=ledger.sha(derived['source_record']),
                      source_passed=derived['source_passed'], unit=derived['source_unit'])
        return source
    key = ledger.sha(claimed.get('binding'))
    record = next((record for stored_key, record in records if stored_key == key), None)
    if record is None or record != claimed or record.get('passed') is not True:
        fail(cid + ' 的沿用 record 不在真实 ledger 中或没有通过')
    old = record['binding']
    current = row['binding']
    try:
        covered = ledger.select_inputs(record['roots'], row.get('scope'))
    except ledger.NeedsScope:
        fail(cid + ' 的原观察不覆盖当前依赖')
    if (covered != current['inputs'] or old['conditions'] != current['conditions']
            or old['tool_sha256'] != current['tool_sha256']):
        fail(cid + ' 的原观察不覆盖当前输入、条件或判定器')
    return _source(cid, key, record, 'current_observation')


def _new_check_repair(cid, row, history, declaration, recovery, archive_sha, project):
    """Continue a genuinely new failed check only after a provable input correction."""
    request = recovery.get('check_repairs', {}).get(cid)
    if not isinstance(request, dict) or not str(request.get('correction_basis') or '').strip():
        fail(cid + ' 有真实旧记录或失败，不能改名为新增项绕过')
    reference = request.get('prior_plan') or {}
    path = Path(reference.get('path') or '')
    if not path.is_absolute() or not path.is_file() or digest(path) != reference.get('sha256'):
        fail(cid + ' 修复缺少原核准计划字节')
    plan = json.loads(path.read_bytes())
    baseline = plan.get('baseline') or {}
    origin = (baseline.get('sources') or {}).get(cid) or {}
    actions = [group[cid] for group in (plan.get('actions') or {}).values() if cid in group]
    origin_valid = False
    seen = set()
    for _ in range(16):
        if origin.get('declaration') != declaration: break
        if origin.get('kind') == 'new_check':
            origin_valid = True; break
        if origin.get('kind') not in ('new_check_repair','new_check_environment_retry'): break
        parent = origin.get('prior_plan') or {}
        parent_path = Path(parent.get('path') or '')
        if (not parent_path.is_absolute() or str(parent_path) in seen or not parent_path.is_file()
                or digest(parent_path) != parent.get('sha256')): break
        seen.add(str(parent_path)); ancestor = json.loads(parent_path.read_bytes())
        if (ancestor.get('schema') != 'cocos-regression-scope.v1' or ancestor.get('project') != str(project)
                or (ancestor.get('baseline') or {}).get('sha256') != archive_sha): break
        origin = ((ancestor.get('baseline') or {}).get('sources') or {}).get(cid) or {}
    if (plan.get('schema') != 'cocos-regression-scope.v1' or plan.get('project') != str(project)
            or baseline.get('sha256') != archive_sha or not origin_valid
            or origin.get('declaration') != declaration or len(actions) != 1):
        fail(cid + ' 原计划不能证明是本工程本基线的真实新增检查')
    prior_key = request.get('source_key') or request.get('failed_key')
    failed = next((r for key, r in history if key == prior_key), None)
    if (failed is None or type(failed.get('passed')) is not bool or actions[0].get('key') != prior_key
            or actions[0].get('action') != 'run'):
        fail(cid + ' 修复缺少原计划对应的真实失败记录')
    # A checked session may have stopped before any game case was executed.
    # Preserve that real error and retry it as an environment failure, never as
    # a game pass or a cleared product failure. The actual observer still runs.
    environment = request.get('environment_retry')
    if environment and failed.get('passed') is False:
        ref = environment.get('raw_report') or {}
        raw = Path(ref.get('path') or '')
        if (not str(environment.get('resolved_reason') or '').strip() or not raw.is_absolute()
                or not raw.is_file() or digest(raw) != ref.get('sha256')):
            fail(cid + ' 环境恢复缺少真实原始错误或解决原因')
        observed = json.loads(raw.read_bytes())
        message = 'Ego session stopped; resolve the recorded error/control state before continuing'
        if (observed.get('cases') != [] or not str(observed.get('fatal') or '').startswith('Error: ' + message)
                or message not in str(failed.get('error') or (failed.get('result') or {}).get('fatal') or '')
                or (failed.get('result') or {}).get('cases') not in (None, [])):
            fail(cid + ' 此失败不是已核对的零用例环境中断')
        return {'kind': 'new_check_environment_retry', 'current_key': row['key'],
                'declaration': declaration, 'old_pass_claimed': False, 'prior_plan': reference,
                'prior_record_sha256': ledger.sha(failed), 'prior_error': failed.get('error') or (failed.get('result') or {}).get('fatal'),
                'prior_binding': failed['binding'], 'environment_retry': environment}
    if ledger.select_inputs(failed['roots'], row.get('scope')) == row['binding']['inputs']:
        fail(cid + ' 实际依赖没有修正，不能将同输入失败重置为新增检查')
    if failed.get('passed') is False and not failed.get('files'):
        if not isinstance(failed.get('error'), str) or not failed['error']:
            fail(cid + ' 原失败缺少执行错误，不能恢复来源')
        previous = {'kind':'new_check_failed_execution', 'key':prior_key,
                    'record_sha256':ledger.sha(failed), 'binding':failed['binding'],
                    'executed_at':failed['executed_at'], 'passed':False, 'error':failed['error'],
                    'files':[], 'boundary':'Failed execution provenance only; no passing observation reused.'}
    else:
        previous = _source(cid, prior_key, failed, 'new_check_observed_failure' if failed['passed'] is False else 'new_check_observed_pass')
    return {'kind': 'new_check_repair', 'current_key': row['key'], 'declaration': declaration,
            'old_pass_claimed': False, 'prior_plan': reference, 'correction_basis': request['correction_basis'],
            'prior_observation': previous}


def identity(archive, candidate, project=None, groups=None):
    """Return the compatible official identity or a fully bound recovery identity.

    ``candidate`` is the actual {ZIP member: bytes} map. ``groups`` must be the
    complete runner output, not a user-selected subset. For a genuinely new check,
    check-inputs.json may declare ``baseline_recovery.new_checks[check_id]`` with
    non-empty ``reason`` and ``basis``; old failures never become new checks.
    """
    from verify_native_zip import receipt_status
    path = Path(archive).resolve()
    archive_sha, old_files = _archive(path)
    old_manifest, current_manifest = package_manifest(old_files), package_manifest(candidate)
    _check_app_id(old_files, candidate)
    status = receipt_status(path, archive_sha, old_manifest)
    if status.get('entry') == 'official':
        receipt = Path(status['receipt'])
        return {'path': str(path), 'sha256': archive_sha,
                'receipt': str(receipt), 'receipt_sha256': digest(receipt)}
    gap = _receipt_gap(status, archive_sha, old_manifest)
    if project is None or not isinstance(groups, dict):
        fail('原 ZIP 缺少匹配正式回执，恢复需要工程及完整逐项观察计划')
    project = Path(project).resolve()
    rows = {}
    coverage = {}
    for group, entries in groups.items():
        if not isinstance(entries, list):
            fail('逐项观察计划格式不正确')
        coverage[group] = []
        for row in entries:
            cid = row.get('check_id') if isinstance(row, dict) else None
            if not isinstance(cid, str) or not cid or cid in rows:
                fail('逐项观察 ID 缺失或重复')
            if row.get('action') not in ('run', 'reuse'):
                fail(cid + ' 存在未解决失败或疑点：' + str(row.get('why', row.get('action'))))
            binding = row.get('binding')
            if (not isinstance(binding, dict) or ledger.sha(binding) != row.get('key')
                    or binding.get('check_id') != cid
                    or row.get('roots', {}).get('package') != current_manifest
                    or ledger.select_inputs(row['roots'], row.get('scope')) != binding.get('inputs')):
                fail(cid + ' 的当前观察计划与实际候选输入不一致')
            coverage[group].append(cid)
            rows[cid] = row
    if not rows or not any(row['action'] == 'reuse' for row in rows.values()):
        fail('没有任何真实可沿用项；不能把全部缺证项当成新项扩大执行')
    from runtime_unit_reuse import legacy_unit, legacy_comparison_source, legacy_observation_exists
    legacy_ids = {'runtime.' + item[0] + '/@suite' for cid in rows
                  if (item := legacy_unit(cid)) is not None}
    records = _records(project, set(rows) | legacy_ids)
    scope_path = project / 'docs/checks/check-inputs.json'
    try:
        scope_raw = scope_path.read_bytes()
        config = json.loads(scope_raw)
    except (OSError, ValueError, UnicodeError):
        fail('恢复需要可读的逐项依赖登记 check-inputs.json')
    if not isinstance(config, dict) or config.get('schema') != ledger.SCOPE_SCHEMA:
        fail('恢复依赖登记格式不正确')
    recovery = config.get('baseline_recovery', {})
    new_checks = recovery.get('new_checks', {}) if isinstance(recovery, dict) else {}
    if not isinstance(new_checks, dict) or not isinstance(config.get('evidence_rechecks', {}), dict):
        fail('恢复登记格式不正确')
    sources = {}
    for cid, row in sorted(rows.items()):
        history = records[cid]
        archived = [(key, record) for key, record in history
                    if record['roots'].get('package') == old_manifest]
        current_source = _current_source(cid, row, history, records) if row['action'] == 'reuse' else None
        if archived:
            key, record = archived[0]
            if record.get('passed') is not True:
                fail(cid + ' 的原 ZIP 最新真实观察失败，先修复，不能退回更旧通过项')
            request = config.get('evidence_rechecks', {}).get(cid)
            if (isinstance(request, dict)
                    and record['binding'].get('evidence_recheck') == ledger.sha(request)):
                # The completed replacement observation has the same ZIP bytes.
                # Keep the original missing record as comparison provenance so
                # completing the approved node does not replace the plan baseline.
                original = next(((k, r) for k, r in archived if k == request.get('prior_key')), None)
                if original is None or original[1].get('passed') is not True:
                    fail(cid + ' 的补采缺少原通过记录')
                key, record = original
            recollect = _recheck(cid, key, record, config)
            source = _source(cid, key, record, 'archive_observation', recheck=recollect)
            # A changed item remains tied to its old observation after its precise
            # recheck completes. Therefore run -> reuse does not change identity.
            source['current_key'] = row['key']
            sources[cid] = source
        elif (derived := legacy_comparison_source(records, row, old_manifest)) is not None:
            source = _source(cid, derived['source_key'], derived, 'legacy_unit_archive_observation')
            source.update(current_key=row['key'], source_check_id=derived['source_record']['check_id'],
                          source_record_sha256=ledger.sha(derived['source_record']),
                          source_passed=derived['source_passed'], unit=derived['source_unit'])
            sources[cid] = source
        elif cid in new_checks:
            if legacy_observation_exists(records,row,old_manifest):
                fail(cid + ' 已有真实 aggregate 观察，不能把原失败或缺口改名为新增检查')
            declaration = new_checks[cid]
            if (not isinstance(declaration, dict)
                    or any(not isinstance(declaration.get(k), str) or not declaration[k].strip()
                           for k in ('reason', 'basis'))):
                fail(cid + ' 新增项需要明确 reason 和实际依赖 basis')
            if any(key != row['key'] or record.get('passed') is not True for key, record in history):
                sources[cid] = _new_check_repair(cid, row, history, declaration, recovery, archive_sha, project)
            else:
                sources[cid] = {'kind': 'new_check', 'current_key': row['key'],
                                'declaration': declaration, 'old_pass_claimed': False}
        elif current_source:
            sources[cid] = dict(current_source, current_key=row['key'], old_pass_claimed=False)
        else:
            fail(cid + ' 待跑项缺少对应原 ZIP 的真实旧输入来源；先恢复原记录或明确登记实际新增项')
    # Reading sources cannot race a moving candidate archive or dependency record.
    if digest(path) != archive_sha or scope_path.read_bytes() != scope_raw:
        fail('恢复核对期间原 ZIP 或依赖登记发生变化')
    return {'type': 'evidence_recovery', 'schema': SCHEMA, 'path': str(path), 'sha256': archive_sha,
            'project': str(project), 'archive_manifest': old_manifest,
            'archive_manifest_sha256': ledger.sha(old_manifest),
            'current_manifest_sha256': ledger.sha(current_manifest),
            'scope_sha256': ledger.sha(scope_raw), 'receipt_status': gap,
            'coverage': {name: sorted(ids) for name, ids in sorted(coverage.items())},
            'sources': sources, 'old_official_pass_claimed': False,
            'boundary': 'Evidence comparison baseline only; the old ZIP is not declared official or passed.'}
