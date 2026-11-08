"""Reuse verified observations and applicability decisions without running a game."""
from datetime import datetime
from pathlib import Path
import sqlite3

import check_ledger as C


class _ReadOnlyLedger(C.Ledger):
    """Use the shared planner without creating tables, evidence or execution rows."""
    def __init__(self, project):
        self.project = Path(project).resolve()
        self.home = self.project / 'docs/checks/incremental'
        database = self.home / 'ledger.sqlite3'
        if not database.is_file():
            raise C.NeedsScope('缺少本工程的原检查记录；门禁只复核，不能从旧报告新登记通过')
        self.db = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
        self._file_checks = {}


def evidence_files(project, evidence, *, required):
    """Validate every supplied raw file and return unique paths and SHA values."""
    if not isinstance(evidence, list) or (required and not evidence):
        raise C.NeedsScope('pass 必须有非空原始证据文件及 SHA-256')
    paths, refs = {}, set()
    for ref in evidence:
        if not isinstance(ref, dict) or not isinstance(ref.get('path'), str) or not ref['path'].strip():
            raise C.NeedsScope('无效原始证据引用')
        path = (Path(project) / ref['path']).resolve()
        if not path.is_file() or path.stat().st_size == 0:
            raise C.NeedsScope('原始证据必须是非空文件：' + str(path))
        digest = C.sha(path.read_bytes())
        if digest != ref.get('sha256'):
            raise C.NeedsScope('原始证据 SHA-256 不符：' + str(path))
        paths[str(path)] = digest
        refs.add(digest)
    return paths, refs


class CaseRecords:
    def __init__(self, project, *, read_only=False):
        self.project = Path(project).resolve()
        if not (self.project / 'assets').is_dir():
            raise C.NeedsScope('逻辑检查需要真实工程根目录，不能使用报告目录：' + str(self.project))
        self.read_only = read_only
        # A report containing only missing/untested rows has no observation to
        # register. Keep that audit read-only even when --out is elsewhere.
        self._ledger = _ReadOnlyLedger(self.project) if read_only else None
        self.roots = {'source': C.manifest(self.project / 'assets')}
        self.rules = C.tool_fingerprint([
            Path(__file__), Path(__file__).with_name('logic_regressions.py'),
            Path(__file__).with_name('logic_check.py'),
        ])

    @property
    def ledger(self):
        if self._ledger is None:
            self._ledger = C.Ledger(self.project)
        return self._ledger

    def close(self):
        if self._ledger is not None:
            self._ledger.close()

    def resolve(self, ident, rec, current_binding, errors, *, current_digest=None):
        if errors:
            return None
        status = rec.get('status')
        if status not in ('pass', 'n/a'):
            raise C.NeedsScope(ident + '：只能登记已验证观察或有依据的不适用判定')
        paths, refs = evidence_files(self.project, rec.get('evidence', []), required=status == 'pass')
        # Report formatting and binding claims are not observations. Normalize
        # paths and repeated references so copying a reference cannot be new proof.
        observation = {k: v for k, v in rec.items() if k not in (
            'source_binding', 'incremental', 'problem', 'title', 'rule', 'button_check_root')}
        observation['evidence'] = [{'path': path, 'sha256': digest} for path, digest in sorted(paths.items())]

        def relative(value):
            if isinstance(value, dict):
                return {k: relative(v) for k, v in value.items()}
            if isinstance(value, list):
                return [relative(v) for v in value]
            if isinstance(value, str) and value.startswith(str(self.project) + '/'):
                return value[len(str(self.project)) + 1:]
            return value

        observation = relative(observation)
        cid = 'logic.' + ident
        plan = self.ledger.prepare(cid, self.roots, {'observation_sha256': C.sha(observation)},
                                   self.rules, label=ident, domain='audio' if ident == 'R09' else 'gameplay')
        if plan['action'] == 'reuse':
            row = plan['record']
            return {'action': 'reuse', 'original_validation_at': row['executed_at'],
                    'original_observed_at': row['result'].get('observed_at'), 'source_key': C.sha(row['binding'])}
        if self.read_only:
            raise C.NeedsScope(ident + '：原记录不可沿用（' + plan['why'] + '）；门禁不会登记或执行新检查')
        if plan['action'] != 'run':
            raise C.NeedsScope(ident + '：' + plan['why'])
        if not current_binding:
            purpose = '适用性' if status == 'n/a' else '依赖/证据'
            raise C.NeedsScope(ident + '：' + plan['why'] + '；只复核此项' + purpose + '，不重测其他已通过项')
        old = self.ledger.previous(cid)
        if old:
            previous = old[0]
            changed = C.select_inputs(previous.get('roots', {}), plan['scope']) != C.select_inputs(self.roots, plan['scope'])
            if changed and status == 'pass':
                # Rotating an older capture back into the row is still old proof.
                old_refs = {digest for row in old for digest in row.get('result', {}).get('evidence_sha256', [])}
                if not refs - old_refs:
                    raise C.NeedsScope(ident + '：相关输入已变但没有新的原始观察证据；不能只更新 source_binding、复制或删减旧引用')
            if status == 'n/a' and (changed or previous.get('result', {}).get('status') != 'n/a'):
                review = rec.get('applicability_review')
                previous_review = previous.get('result', {}).get('applicability_review') or {}
                observed_at = review.get('observed_at') if isinstance(review, dict) else None
                try:
                    valid_time = isinstance(observed_at, str) and datetime.fromisoformat(observed_at.replace('Z', '+00:00')).tzinfo is not None
                except ValueError:
                    valid_time = False
                if (not isinstance(review, dict) or not current_digest or review.get('source_sha256') != current_digest
                        or not str(review.get('reason') or '').strip() or not valid_time
                        or observed_at == previous_review.get('observed_at', previous.get('result', {}).get('observed_at'))):
                    raise C.NeedsScope(ident + '：相关输入已变，只复核此项适用性；填写新的 applicability_review {source_sha256, observed_at, reason}，不能沿用旧 n/a 或只刷新全局 SHA')
        observed_at = ((rec.get('applicability_review') or {}).get('observed_at')
                       if status == 'n/a' and isinstance(rec.get('applicability_review'), dict) else rec.get('observed_at'))
        result = {'passed': True, 'status': status, 'observed_at': observed_at,
                  'evidence': list(paths), 'evidence_sha256': sorted(refs),
                  'applicability_review': rec.get('applicability_review'),
                  'boundary': 'validation of existing observations/applicability, not a new browser execution'}
        _, proof = self.ledger.execute(plan, lambda: result, lambda r: r['passed'])
        return {'action': 'registered_applicability' if status == 'n/a' else 'registered_observation',
                'original_observed_at': observed_at, 'source_key': proof['key'], 'browser_executed': False}
