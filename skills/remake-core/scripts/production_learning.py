"""Portable, nonblocking game-evidence collection and explicit Skill maintenance.

Game hooks call collect_nonblocking(); they never run Skill CI or execute repairs.
Maintenance CLI import/plan/audit/apply operates only on an explicit workspace.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import tempfile

HERE = Path(__file__).resolve().parent
POLICY = HERE.parent / 'assets/production-learning-policy.json'
BUNDLE_SCHEMA = 'production_learning_bundle.v1'
DEFAULT_RECORDS = ('docs/timing/stage-timing.jsonl', 'docs/timing/timing-summary.json',
                   'docs/test/package-issues.jsonl',
                   'docs/production/accounting.jsonl', 'docs/production/summary.json',
                   'docs/checks/known-issues.json', 'docs/checks/delivery-continuation.json',
                   'docs/production-learning/proposals.json')
MAX_RECORDS, MAX_BYTES, MAX_TOTAL_BYTES = 32, 4 * 1024 * 1024, 8 * 1024 * 1024
IDENTIFIER = re.compile(r'[A-Za-z][A-Za-z0-9_.:-]{0,159}\Z')


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def digest(value):
    return hashlib.sha256(value).hexdigest()


def sha(path):
    return digest(Path(path).read_bytes())


def now():
    return datetime.now(timezone.utc).isoformat()


def policy():
    data = json.loads(POLICY.read_text(encoding='utf-8'))
    if data.get('schema') != 'production_learning_policy.v1':
        raise ValueError('unknown learning catalog schema')
    return data


def relative(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise ValueError('a portable relative path is required')
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in ('', '.', '..') for x in p.parts) or value != p.as_posix():
        raise ValueError('unsafe relative path: ' + value)
    return p.as_posix()


def local(root, value, *, exists=True):
    root = Path(root).resolve()
    text = str(value)
    p = Path(text) if Path(text).is_absolute() else root / relative(text)
    if any(x.is_symlink() for x in (p, *p.parents)):
        raise ValueError('symlink paths are not accepted')
    p = p.resolve()
    if p == root or not p.is_relative_to(root) or exists and not p.is_file():
        raise ValueError('record must be an existing project-local file')
    return p


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.learning-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(encoded(value) + b'\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def normalize(value, project):
    """Keep facts private inside evidence; paths are data, never executable commands."""
    if isinstance(value, dict):
        return {str(k): normalize(v, project) for k, v in value.items()
                if str(k).lower() not in {'api_key', 'access_token', 'refresh_token', 'password', 'authorization'}}
    if isinstance(value, list):
        return [normalize(v, project) for v in value]
    if isinstance(value, str):
        # Preserve source record facts, but do not distribute machine-specific roots.
        value = value.replace(str(project), '<project>')
        if value.startswith(('/', '~/')) or re.match(r'^[A-Za-z]:[\\/]', value):
            return '<external>/' + value.replace('\\', '/').rstrip('/').split('/')[-1]
        return value
    return value


def observations(value, record_id):
    rows = []
    def visit(item, pointer=''):
        if isinstance(item, dict):
            status = item.get('status', item.get('repair_status', item.get('result')))
            cause = item.get('cause_key')
            explicit_cause = cause if isinstance(cause, str) and IDENTIFIER.fullmatch(cause) else None
            fix = item.get('fix', item.get('repair_result', item.get('repair')))
            changes = item.get('changes', item.get('changed_files', []))
            delta = isinstance(changes, list) and any(isinstance(x, dict) and x.get('before_sha256') and
                x.get('after_sha256') and x['before_sha256'] != x['after_sha256'] for x in changes)
            outcomes = item.get('outcomes', [])
            witnessed = isinstance(outcomes, list) and {'failure', 'fixed'} <= set(x for x in outcomes if isinstance(x, str))
            confirmed = status in ('fixed', 'resolved', 'resumed') and bool(explicit_cause and fix and delta and witnessed)
            relevant = explicit_cause or fix or item.get('tag') == 'rework' or 'original_failure' in item
            if relevant:
                rows.append(dict(record_id=record_id, pointer=pointer or '/', cause_key=explicit_cause,
                    recorded_status=status if isinstance(status, (str, bool, int, float)) else None,
                    classification='recorded_confirmed_fix' if confirmed else 'candidate_needs_cause_or_validation',
                    prevention_stage=item.get('prevention_stage') if isinstance(item.get('prevention_stage'), str) else None,
                    evidence_only=True, generalized=False))
            for key, child in item.items():
                visit(child, pointer + '/' + str(key).replace('~', '~0').replace('/', '~1'))
        elif isinstance(item, list):
            for index, child in enumerate(item): visit(child, pointer + '/' + str(index))
    visit(value)
    return rows


def bundle_body(bundle):
    return {k: v for k, v in bundle.items() if k not in ('id', 'created_at')}


def validate_bundle(bundle):
    if not isinstance(bundle, dict) or bundle.get('schema') != BUNDLE_SCHEMA:
        raise ValueError('unknown experience bundle schema')
    if bundle.get('id') != digest(encoded(bundle_body(bundle))):
        raise ValueError('bundle content identity differs')
    records = bundle.get('records')
    if not isinstance(records, list) or len(records) > MAX_RECORDS:
        raise ValueError('invalid evidence record inventory')
    ids = set()
    for record in records:
        relative(record['source'])
        if record['id'] in ids or record['id'] != digest(encoded(record['payload'])):
            raise ValueError('duplicate or changed portable evidence')
        if not re.fullmatch(r'[0-9a-f]{64}', record.get('raw_sha256', '')):
            raise ValueError('original evidence digest missing')
        ids.add(record['id'])
    if not isinstance(bundle.get('proposals'), list) or not isinstance(bundle.get('observations'), list):
        raise ValueError('proposals and observations must be arrays')
    return bundle


def safe_workspace(value):
    path = Path(value)
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('workspace symlink refused')
    path = path.resolve()
    for rel in ('.codex/skills', '.agents/skills', '.claude/skills', '.cursor/skills', '.kiro/crew/skills'):
        installed = (Path.home()/rel).resolve()
        if path == installed or path.is_relative_to(installed):
            raise ValueError('learning workspace must not be an installed Skill directory')
    return path


@contextmanager
def database(workspace, *, timeout=1.0):
    workspace = safe_workspace(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    path = workspace / 'learning.sqlite3'
    if path.is_symlink(): raise ValueError('queue database cannot be a symlink')
    db = sqlite3.connect(path, timeout=timeout, isolation_level=None)
    try:
        db.execute('BEGIN IMMEDIATE')
        db.execute('CREATE TABLE IF NOT EXISTS bundles (id TEXT PRIMARY KEY, payload TEXT NOT NULL, imported_at TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS applied (plan_sha TEXT PRIMARY KEY, candidate TEXT NOT NULL, identity TEXT NOT NULL)')
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def import_bundle(workspace, bundle, *, timeout=1.0):
    if not isinstance(bundle, dict): bundle = json.loads(Path(bundle).read_text(encoding='utf-8'))
    validate_bundle(bundle)
    with database(workspace, timeout=timeout) as db:
        existing = db.execute('SELECT payload FROM bundles WHERE id=?', (bundle['id'],)).fetchone()
        if existing:
            if bundle_body(json.loads(existing[0])) != bundle_body(bundle):
                raise ValueError('concurrent bundle ID collision')
            return dict(status='unchanged', bundle_id=bundle['id'])
        db.execute('INSERT INTO bundles VALUES (?,?,?)', (bundle['id'], encoded(bundle).decode(), now()))
    return dict(status='imported', bundle_id=bundle['id'])


def collect_nonblocking(project, record_paths=None, queue_dir=None, trigger='delivery', context=None):
    """Best effort only: every normal failure returns delivery_blocking=False.

    Pass already produced records. This does not discover chats, run checks,
    collect video, change a delivery receipt, or install/modify Skill files.
    """
    result = dict(schema='production_learning_collection.v1', delivery_blocking=False,
                  status='error', trigger=str(trigger), diagnostics=[])
    try:
        project = Path(project).resolve()
        if not (project/'assets').is_dir(): raise ValueError('Cocos project assets folder missing')
        context = dict(context or {})
        if (set(context) - {'delivery_ready','final_zip_sha256','build_tag'} or
                'delivery_ready' in context and type(context['delivery_ready']) is not bool or
                'final_zip_sha256' in context and not re.fullmatch(r'[a-f0-9]{64}',context['final_zip_sha256']) or
                'build_tag' in context and (not isinstance(context['build_tag'],str) or len(context['build_tag'])>160 or '/' in context['build_tag'] or '\\' in context['build_tag'])):
            raise ValueError('delivery context accepts readiness, exact ZIP digest and a path-free build tag only')
        catalog = policy()
        if record_paths is not None and not isinstance(record_paths,(list,tuple)):raise ValueError('record_paths must be a bounded list or tuple')
        requested = record_paths if record_paths is not None else [x for x in DEFAULT_RECORDS if (project/x).is_file()]
        deferred = []
        if len(requested)>MAX_RECORDS:
            deferred.extend(dict(source=str(x).replace(str(project),'<project>'),reason='record_count_budget') for x in requested[MAX_RECORDS:MAX_RECORDS*2])
            requested=requested[:MAX_RECORDS]
        records, proposals, found = [], [], []
        read_bytes = 0
        seen = set()
        for name in requested:
            try:
                path = local(project, name)
                if path.suffix not in ('.json','.jsonl'): raise ValueError('only existing lightweight JSON/JSONL records are collected')
                budget=min(MAX_BYTES,max(0,MAX_TOTAL_BYTES-read_bytes))
                if path.stat().st_size>budget: raise ValueError('record exceeds per-file or total collection byte budget')
                with path.open('rb') as stream: raw=stream.read(budget+1)
                read_bytes+=len(raw)
                if len(raw)>budget: raise ValueError('record grew beyond collection byte budget')
                payload = ([json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]
                           if path.suffix == '.jsonl' else json.loads(raw))
                payload = normalize(payload, project)
                rid = digest(encoded(payload))
                if rid in seen: continue
                seen.add(rid)
                records.append(dict(id=rid, source=path.relative_to(project).as_posix(), raw_sha256=digest(raw), payload=payload,
                                    classification='private_project_evidence_not_a_shared_rule'))
                found.extend(observations(payload, rid))
                if isinstance(payload, dict) and payload.get('schema') == 'production_learning_proposals.v1':
                    for proposal in payload.get('rules', []):
                        if not isinstance(proposal, dict): raise ValueError('rule proposal must be an object')
                        proposals.append(proposal)
            except Exception as error:
                result['diagnostics'].append(dict(record=str(name).replace(str(project), '<project>'), error=str(error)))
                deferred.append(dict(source=str(name).replace(str(project),'<project>'),reason=str(error)))
        body = dict(schema=BUNDLE_SCHEMA, delivery_context=context,collector_sha256=sha(__file__),catalog_sha256=sha(POLICY), catalog_version=catalog['catalog_version'],
                    formal_base_archive_sha256=catalog['formal_base_archive_sha256'],
                    records=sorted(records, key=lambda x: x['id']), proposals=proposals,deferred_records=deferred,
                    observations=sorted(found, key=lambda x: (x['record_id'], x['pointer'])),
                    boundary='Private evidence and unapproved candidates only; never executable game instructions.')
        bundle = dict(body, id=digest(encoded(body)), created_at=now())
        validate_bundle(bundle)
        out = local(project, 'docs/production-learning/outbox/'+bundle['id']+'.json', exists=False)
        already = out.is_file()
        if already:
            validate_bundle(json.loads(out.read_text(encoding='utf-8')))
        else:
            atomic_json(out, bundle)
        result.update(status='unchanged' if already else 'collected', bundle_id=bundle['id'],
                      bundle=out.relative_to(project).as_posix(), records=len(records), observations=len(found),read_bytes=read_bytes,deferred_records=len(deferred))
        if deferred:result['status']='deferred'
        if queue_dir is not None:
            try: result['queue'] = import_bundle(queue_dir, bundle, timeout=0.0)
            except Exception as error:
                result.update(status='deferred')
                result['diagnostics'].append(dict(queue='unavailable; portable outbox retained', error=str(error)))
    except Exception as error:
        result['diagnostics'].append(dict(error=str(error)))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    collect = sub.add_parser('collect'); collect.add_argument('--project', required=True); collect.add_argument('--record', action='append'); collect.add_argument('--queue'); collect.add_argument('--trigger', default='delivery')
    imp = sub.add_parser('import'); imp.add_argument('--workspace', required=True); imp.add_argument('--bundle', required=True)
    for name in ('plan', 'audit', 'apply'):
        command = sub.add_parser(name); command.add_argument('--workspace', required=True); command.add_argument('--base', required=True)
        command.add_argument('--out')
        if name != 'plan': command.add_argument('--plan', required=True)
        if name == 'apply': command.add_argument('--review', required=True); command.add_argument('--candidate', required=True)
    args = parser.parse_args(argv)
    if args.command == 'collect':
        print(json.dumps(collect_nonblocking(args.project, args.record, args.queue, args.trigger), ensure_ascii=False))
        return 0  # Collection failure is deliberately never a game-delivery gate.
    try:
        if args.command == 'import': result = import_bundle(args.workspace, args.bundle)
        else:
            import production_rule_governance as governance
            if args.command == 'plan': result = governance.plan(args.workspace, args.base)
            elif args.command == 'audit': result = governance.audit(args.workspace, args.base, args.plan)
            else: result = governance.apply(args.workspace, args.base, args.plan, args.review, args.candidate)
        if getattr(args, 'out', None): atomic_json(args.out, result)
        print(json.dumps(result, ensure_ascii=False))
        return 2 if result.get('blocked') else 0
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as error:
        print(json.dumps(dict(status='maintenance_candidate_refused', blocked=True, error=str(error), delivery_blocking=False), ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
