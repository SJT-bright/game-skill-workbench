#!/usr/bin/env python3
"""Portable team handoff and read-only intake. Neither operation certifies current runtime.

Keep the upload ZIP untouched. Receipt absence means evidence unavailable, not a failed game.
Received scripts/commands are data; this tool never executes them or imports a ledger.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

from upload_size_gate import inspect_zip
from verify_native_zip import receipt_status, safe_name

SCHEMA = 'game-handoff.v1'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(data):
    def pairs(rows):
        out = {}
        for k, v in rows:
            if k in out:
                raise ValueError('duplicate JSON field: ' + k)
            out[k] = v
        return out
    return json.loads(data, object_pairs_hook=pairs)


def package(archive, feedback=None):
    files = {}
    result = inspect_zip(archive, 'tiktok', feedback, _verified_files=files)
    hashes = {n: sha(b) for n, b in files.items()}
    return result, hashes


def short_writer(result):
    return {k: result[k] for k in ('entry', 'entry_reason', 'receipt_tool', 'receipt_policy') if k in result}


def export(archive, source, delivery, output, project=None):
    archive, source, delivery, output = [Path(p).resolve() for p in (archive, source, delivery, output)]
    if output.exists() or output.suffix.lower() != '.zip' or output in (archive, source):
        raise ValueError('handoff output must be a new evidence ZIP, distinct from game and source')
    if not source.is_file() or source.suffix.lower() != '.zip':
        raise ValueError('handoff needs the actual delivered source ZIP')
    checked, hashes = package(archive)
    if not checked['passed']:
        raise ValueError('handoff package file check failed: ' + '; '.join(checked['errors']))
    writer = receipt_status(archive, checked['sha256'], hashes)
    if writer.get('entry') != 'official':
        raise ValueError('export needs original same-byte writer evidence; use receive for external legacy ZIPs')
    delivered_bytes = delivery.read_bytes(); delivered = read_json(delivered_bytes)
    if delivered.get('delivery_ready') is not True or delivered.get('sha256') != checked['sha256']:
        raise ValueError('handoff needs a successful delivery record for exactly this ZIP')
    from source_hygiene import audit
    hygiene = audit(source)
    if not hygiene['passed']:
        raise ValueError('delivered source hygiene failed: ' + '; '.join(hygiene['problems'][:5]))
    source_hash = sha(source.read_bytes())
    contents = {'writer.receipt.json': Path(writer['receipt']).read_bytes(),
                'delivery.json': delivered_bytes, 'receiving-file-check.json': json.dumps(checked, ensure_ascii=False).encode()}
    fresh = delivered.get('fresh_size_check', {})
    original_size = Path(fresh.get('report', ''))
    if original_size.is_file():
        data = original_size.read_bytes()
        if read_json(data).get('sha256') != checked['sha256']:
            raise ValueError('author size evidence belongs to another ZIP')
        contents['author-size.json'] = data
    ledger_meta = {'state': 'missing', 'records': 0, 'current_approval': False}
    if project:
        project = Path(project).resolve()
        database = project/'docs/checks/incremental/ledger.sqlite3'
        if database.is_file():
            from check_ledger import Ledger
            with tempfile.TemporaryDirectory(prefix='game-handoff-records-') as tmp:
                ledger = Ledger(project)
                try:
                    meta = ledger.export(Path(tmp)/'checks')
                finally:
                    ledger.close()
                for p in (Path(tmp)/'checks').rglob('*'):
                    if p.is_file():
                        contents['checks/'+p.relative_to(Path(tmp)/'checks').as_posix()] = p.read_bytes()
                ledger_meta = {'state': 'exported' if meta['records'] else 'empty',
                               'records': meta['records'], 'current_approval': False}
        for rel in ('docs/checks/workflow.json', 'docs/checks/check-inputs.json'):
            p = project/rel
            if p.is_file():
                contents['project/'+rel] = p.read_bytes()
    preview = delivered.get('preview') or {}
    manifest = {'schema': SCHEMA, 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'test_zip': {'name': archive.name, 'sha256': checked['sha256']},
                'source_zip': {'name': source.name, 'sha256': source_hash},
                'writer_receipt': 'writer.receipt.json', 'delivery_record': 'delivery.json',
                'ledger': ledger_meta, 'author_preview': preview,
                'receiver_preview': 'Recreate and verify the same Native on the receiving computer; loopback author URLs are not portable.',
                'files': {n: sha(b) for n, b in contents.items()},
                'boundary': 'Byte-bound author evidence, no new execution or current-machine/device approval. Source pairing is declared at export; rejudge source/build bindings separately.'}
    if sha(archive.read_bytes()) != checked['sha256'] or sha(source.read_bytes()) != source_hash or delivery.read_bytes() != delivered_bytes:
        raise ValueError('handoff inputs changed while exporting')
    output.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with output.open('xb') as stream, zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as z:
            created = True
            for n, b in contents.items():
                z.writestr(n, b)
            z.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    except Exception:
        # Remove only the file created by this export; existing outputs were refused.
        if created and output.is_file():
            output.unlink()
        raise
    return {'status': 'handoff_exported', 'evidence_zip': str(output), 'sha256': sha(output.read_bytes()),
            'writer_evidence': 'verified', 'ledger': ledger_meta, 'delivery_ready': False,
            'reply_artifacts': [str(archive), str(source), str(output)],
            'boundary': manifest['boundary']}


def receive(archive, source=None, evidence=None, feedback=None):
    archive = Path(archive).resolve(); checked, hashes = package(archive, feedback)
    writer = receipt_status(archive, checked['sha256'], hashes) if checked['passed'] else {}
    writer_state = 'verified' if writer.get('entry') == 'official' else 'unavailable'
    gaps = []; problems = []; imported = None; source_identity = None
    if source:
        try:
            source = Path(source).resolve()
            with zipfile.ZipFile(source) as z:
                for n in z.namelist():
                    safe_name(n)
                if z.testzip() is not None:
                    raise ValueError('source ZIP CRC failed')
            source_identity = {'path': str(source), 'sha256': sha(source.read_bytes()),
                               'paired_to_test_zip': False}
        except (ValueError, OSError, zipfile.BadZipFile) as exc:
            problems.append('source ZIP: ' + str(exc))
    if evidence:
        try:
            with zipfile.ZipFile(evidence) as z:
                names = z.namelist()
                if len(names) != len(set(names)):
                    raise ValueError('duplicate handoff member')
                for n in names:
                    safe_name(n)
                manifest = read_json(z.read('manifest.json'))
                if manifest.get('schema') != SCHEMA or manifest.get('test_zip', {}).get('sha256') != checked['sha256']:
                    raise ValueError('handoff is not for these test ZIP bytes')
                listed = manifest.get('files')
                if not isinstance(listed, dict) or set(names) != {'manifest.json', *listed}:
                    raise ValueError('handoff member inventory mismatch')
                for n, digest in listed.items():
                    if sha(z.read(n)) != digest:
                        raise ValueError('handoff evidence hash mismatch: ' + n)
                member = manifest.get('writer_receipt')
                if member not in listed:
                    raise ValueError('handoff writer receipt missing')
                with tempfile.TemporaryDirectory(prefix='game-handoff-verify-') as tmp:
                    p = Path(tmp)/'test.zip'
                    Path(str(p)+'.receipt.json').write_bytes(z.read(member))
                    portable_writer = receipt_status(p, checked['sha256'], hashes)
                if portable_writer.get('entry') != 'official':
                    raise ValueError('portable writer receipt invalid: ' + portable_writer.get('entry_reason', 'unknown'))
                writer = portable_writer; writer_state = 'verified'
                if source:
                    if not source_identity or source_identity['sha256'] != manifest.get('source_zip', {}).get('sha256'):
                        raise ValueError('source ZIP does not match the handoff manifest')
                    source_identity['paired_to_test_zip'] = True
                else:
                    gaps.append('source ZIP not supplied; declared source identity has not been checked')
                original = read_json(z.read(manifest['delivery_record']))
                if original.get('sha256') != checked['sha256'] or original.get('delivery_ready') is not True:
                    raise ValueError('author delivery record does not match this package')
                imported = {'evidence_zip': str(Path(evidence).resolve()), 'sha256': sha(Path(evidence).read_bytes()),
                            'ledger': manifest.get('ledger'), 'current_approval': False, 'executed_received_code': False}
                if manifest.get('ledger', {}).get('state') != 'exported':
                    gaps.append('per-check author records unavailable; locate missing nodes, do not run a full matrix by default')
        except (ValueError, KeyError, TypeError, AttributeError, OSError, zipfile.BadZipFile) as exc:
            problems.append(str(exc))
    if writer_state != 'verified':
        gaps.append('original writer receipt unavailable here; prior writer failure is not established')
    if source is None:
        gaps.append('source ZIP not supplied')
    if not evidence:
        gaps.append('portable per-check records not supplied')
    good = checked['passed'] and not problems
    return {'schema': 'external-package-intake.v1', 'mode': 'receive_external_package',
            'origin': 'external_declared', 'status': 'received' if good else 'intake_problem',
            'intake_passed': good, 'delivery_ready': False, 'current_runtime_approval': False,
            'file_check': checked, 'writer_evidence': {'state': writer_state, **short_writer(writer)},
            'source_identity': source_identity,
            'portable_evidence': imported, 'evidence_gaps': gaps, 'problems': problems,
            'next': 'Create same-build local preview; if modifying/reissuing, import original per-check records with trusted tools, re-plan current dependencies and supplement only missing/affected nodes.',
            'boundary': 'Reception and byte/evidence checks only; no runtime, new formal writer, device or platform verdict.'}


def main():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='mode', required=True)
    e = sub.add_parser('export'); e.add_argument('--zip', required=True, type=Path); e.add_argument('--source', required=True, type=Path)
    e.add_argument('--delivery-record', required=True, type=Path); e.add_argument('--out', required=True, type=Path); e.add_argument('--project', type=Path)
    r = sub.add_parser('receive'); r.add_argument('--zip', required=True, type=Path); r.add_argument('--source', type=Path)
    r.add_argument('--evidence', type=Path); r.add_argument('--platform-feedback', type=Path); r.add_argument('--report', required=True, type=Path)
    a = p.parse_args()
    try:
        if a.mode == 'export':
            result = export(a.zip, a.source, a.delivery_record, a.out, a.project)
        else:
            if a.report.exists() or a.report.resolve() in {q.resolve() for q in (a.zip, a.source, a.evidence) if q}:
                raise ValueError('intake report must be a new file distinct from inputs')
            result = receive(a.zip, a.source, a.evidence, a.platform_feedback)
            a.report.parent.mkdir(parents=True, exist_ok=True)
            with a.report.open('x') as f:
                json.dump(result, f, ensure_ascii=False, indent=2); f.write('\n')
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get('intake_passed', result.get('status') == 'handoff_exported') else 1
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        print(json.dumps({'status': 'handoff_error', 'delivery_ready': False, 'error': str(exc)}, ensure_ascii=False)); return 1


if __name__ == '__main__':
    raise SystemExit(main())
