#!/usr/bin/env python3
"""Portable team handoff and read-only intake. Neither operation certifies current runtime.

Keep the upload ZIP untouched. Receipt absence means evidence unavailable, not a failed game.
Received scripts/commands are data; this tool never executes them or imports a ledger.

  deliver   (2026-11-12) what the maker of a finished game hands over by default: after prepare_delivery succeeded it
            makes the source ZIP when none exists and exports the evidence ZIP next to the test ZIP. The English final
            hand-off (handoff_preview.py --kind package) calls it, so nobody has to remember the export step.
  export    the evidence ZIP for a given test ZIP + source ZIP + delivery record (what deliver uses)
  receive   read-only intake of a package somebody else made
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import time
from pathlib import Path
import tempfile
import zipfile

from upload_size_gate import inspect_zip
from verify_native_zip import receipt_status, safe_name

SCHEMA = 'game-handoff.v1'
SOURCE_TAIL = '_源码'
EVIDENCE_TAIL = '_交接证据'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    """Bounded-memory identity of the actual file, never an acceptance shortcut."""
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _expected_source_sha(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
        raise ValueError('expected source SHA-256 must be a lowercase content digest')
    return value


def _unchanged_inputs(archive, test_sha, source, source_sha, delivery, delivery_bytes):
    # Source is checked last, after every other callback/IO in this guard.
    if file_sha(archive) != test_sha or delivery.read_bytes() != delivery_bytes or file_sha(source) != source_sha:
        raise ValueError('handoff inputs changed while exporting; no completed handoff')


def _discard_owned(path, expected, *, identity=None):
    """Remove only this invocation's unchanged output; preserve concurrent bytes."""
    path = Path(path)
    try:
        if path.is_symlink() or not path.is_file():
            return
        before = path.stat()
        if identity is not None and (before.st_dev, before.st_ino) != identity:
            return
        signature = lambda st: (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
        if file_sha(path) == expected and signature(path.stat()) == signature(before):
            path.unlink()
    except OSError:
        pass


def _timings(started, packaging):
    total = time.perf_counter() - started
    return {'schema': 'handoff-timing.v1', 'total_seconds': total,
            'packaging_seconds': packaging, 'verification_seconds': max(0.0, total - packaging),
            'game_execution_seconds': 0.0,
            'boundary': 'Wall time of this call. Verification includes record preparation and file checks; packaging includes source/evidence ZIP creation. Parent and child totals overlap.'}


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


def export(archive, source, delivery, output, project=None, *, expected_source_sha256=None):
    started, packaging_seconds = time.perf_counter(), 0.0
    archive, source, delivery, output = [Path(p).resolve() for p in (archive, source, delivery, output)]
    if output.exists() or output.suffix.lower() != '.zip' or output in (archive, source):
        raise ValueError('handoff output must be a new evidence ZIP, distinct from game and source')
    if not source.is_file() or source.suffix.lower() != '.zip':
        raise ValueError('handoff needs the actual delivered source ZIP')
    # A caller's digest is only a stricter expectation; the final actual file
    # is always hashed and compared. Public standalone export owns its baseline.
    source_hash = (_expected_source_sha(expected_source_sha256) if expected_source_sha256 is not None
                   else file_sha(source))
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
    # Prepare a private ZIP, then verify original bytes before publication.
    # The final published path is never a partially written successful bundle.
    output.parent.mkdir(parents=True, exist_ok=True)
    publication_identity, output_sha = None, None
    try:
        with tempfile.TemporaryDirectory(prefix='.handoff-', dir=output.parent) as tmp:
            staged = Path(tmp) / output.name
            tick = time.perf_counter()
            with staged.open('xb') as stream, zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as z:
                for n, b in contents.items():
                    z.writestr(n, b)
                z.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
            packaging_seconds += time.perf_counter() - tick
            output_sha = file_sha(staged)
            _unchanged_inputs(archive, checked['sha256'], source, source_hash, delivery, delivered_bytes)
            stat = staged.stat(); publication_identity = (stat.st_dev, stat.st_ino)
            os.link(staged, output)  # exclusive atomic publication; never replace an existing path
            if file_sha(output) != output_sha:
                raise ValueError('handoff output changed during publication')
            _unchanged_inputs(archive, checked['sha256'], source, source_hash, delivery, delivered_bytes)
    except BaseException:
        if publication_identity is not None:
            _discard_owned(output, output_sha, identity=publication_identity)
        raise
    return {'status': 'handoff_exported', 'evidence_zip': str(output), 'sha256': output_sha,
            'source_sha256': source_hash, 'writer_evidence': 'verified', 'ledger': ledger_meta, 'delivery_ready': False,
            'timings': _timings(started, packaging_seconds),
            'reply_artifacts': [str(archive), str(source), str(output)],
            'boundary': manifest['boundary']}


def source_identity(source):
    """Scripts and configs under assets/ of a project folder or of a source ZIP (the rule of logic_regressions.source_digest
    and prepare_delivery.source_sha256): the same value for a project and a source ZIP made from it. Folder names are
    judged inside the project only, so a project kept under a folder called build or temp is read like any other."""
    from pathlib import PurePosixPath
    skip = {'node_modules', 'library', 'temp', 'build', '.git'}
    source = Path(source)
    if source.is_dir():
        digest = hashlib.sha256()
        for path in sorted((source / 'assets').rglob('*')):
            rel = path.relative_to(source)
            if not path.is_file() or path.suffix not in {'.js', '.ts', '.json'} or skip & set(rel.parts):
                continue
            digest.update(rel.as_posix().encode('utf-8') + b'\0' + hashlib.sha256(path.read_bytes()).digest())
        return digest.hexdigest()
    with zipfile.ZipFile(source) as z:
        names = [i.filename for i in z.infolist() if not i.is_dir()]
        bases = set()
        for n in names:
            parts = PurePosixPath(n).parts
            if 'assets' in parts[:-1]:
                i = parts.index('assets')
                if not skip & set(parts[:i]) and '__MACOSX' not in parts[:i]:
                    bases.add('/'.join(parts[:i]))
        if not bases:
            raise ValueError('source ZIP has no assets/ folder')
        base = sorted(bases, key=lambda b: (b.count('/') if b else -1, b))[0]
        prefix = base + '/' if base else ''
        rows = []
        for n in names:
            if not n.startswith(prefix + 'assets/'):
                continue
            rel = PurePosixPath(n[len(prefix):])
            if rel.suffix not in {'.js', '.ts', '.json'} or skip & set(rel.parts):
                continue
            rows.append((rel.parts, rel.as_posix(), n))
        digest = hashlib.sha256()
        for _, rel, n in sorted(rows):
            digest.update(rel.encode('utf-8') + b'\0' + hashlib.sha256(z.read(n)).digest())
    return digest.hexdigest()


def _free(folder, stem, tail):
    """<stem><tail>.zip, or the first free "<stem><tail> (2).zip" ...: nothing existing is overwritten."""
    for n in range(1, 100):
        path = folder / ('%s%s%s.zip' % (stem, tail, '' if n == 1 else ' (%d)' % n))
        if not path.exists():
            return path
    raise ValueError('too many earlier files named like %s%s.zip' % (stem, tail))


def _earlier(folder, stem, tail):
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == '.zip' and p.name.startswith(stem + tail))


def _evidence_for(path, test_sha, source_sha, delivery_sha):
    """Manifest of an evidence ZIP written earlier for exactly these files and this delivery record, else None."""
    try:
        with zipfile.ZipFile(path) as z:
            manifest = read_json(z.read('manifest.json')); listed = manifest.get('files')
            if (manifest.get('schema') == SCHEMA and manifest.get('test_zip', {}).get('sha256') == test_sha and
                    manifest.get('source_zip', {}).get('sha256') == source_sha and isinstance(listed, dict) and
                    set(z.namelist()) == {'manifest.json', *listed} and listed.get('delivery.json') == delivery_sha and
                    all(sha(z.read(n)) == d for n, d in listed.items())):
                return manifest
    except (ValueError, KeyError, TypeError, AttributeError, OSError, zipfile.BadZipFile):
        pass
    return None


def deliver(delivery, project, source=None, out_dir=None):
    """The default hand-over of a finished game (user 2026-11-12): test ZIP, editable source ZIP and evidence ZIP
    together; the play link comes from the preview hand-off that calls this.

    Run right after prepare_delivery succeeded. The source ZIP is: --source when given; else the source ZIP the
    delivery record already checked; else an earlier "<test zip name>_源码.zip" that still equals the project; else a
    new one written by make_source_zip.py. The evidence ZIP "<test zip name>_交接证据.zip" is exported next to the test
    ZIP (next to the project folder when the test ZIP sits inside the project: a source ZIP is never written into the
    project it packs). A second run with unchanged inputs returns the same two files. The upload ZIP is never touched and nothing
    existing is overwritten. No runtime, device or platform verdict is added here.
    """
    started, packaging_seconds = time.perf_counter(), 0.0
    delivery = Path(delivery).resolve(); project = Path(project).resolve()
    delivered_bytes = delivery.read_bytes(); record = read_json(delivered_bytes)
    if record.get('delivery_ready') is not True:
        raise ValueError('四样交付需要 prepare_delivery.py 的成功交付记录（delivery_ready 为 true）；先完成最终交付复核')
    archive = Path(str(record.get('archive') or '')).resolve()
    if not archive.is_file() or file_sha(archive) != record.get('sha256'):
        raise ValueError('测试包与交付记录不是同一份文件：' + str(archive))
    if not (project / 'assets').is_dir():
        raise ValueError('不是 Cocos 工程（没有 assets 文件夹）：' + str(project))
    folder = Path(out_dir).resolve() if out_dir else archive.parent
    if folder == project or folder.is_relative_to(project):
        if out_dir:
            raise ValueError('源码包不能写进工程文件夹里，换一个工程外的文件夹：' + str(folder))
        folder = project.parent          # the test ZIP sits inside the project: the two ZIPs go next to the project folder
    folder.mkdir(parents=True, exist_ok=True)
    current = source_identity(project)
    made = {'source_zip': False, 'evidence_zip': False}
    if source is not None:
        source = Path(source).resolve()
    else:
        named = (record.get('source_hygiene') or {}).get('source') if isinstance(record.get('source_hygiene'), dict) else None
        named = Path(named).resolve() if isinstance(named, str) and named else None
        if named and named.is_file() and named.suffix.lower() == '.zip':
            source = named
        else:
            for earlier in _earlier(folder, archive.stem, SOURCE_TAIL):
                try:
                    if source_identity(earlier) == current:
                        source = earlier; break
                except (ValueError, OSError, zipfile.BadZipFile):
                    continue
        if source is None:
            from make_source_zip import build
            tick = time.perf_counter()
            written = build(project, _free(folder, archive.stem, SOURCE_TAIL))
            packaging_seconds += time.perf_counter() - tick
            if not written.get('written'):
                raise ValueError('源码包没有写出：工程里有账号、密码或密钥，先删掉文件或把值清空再交付。' +
                                 '；'.join(written.get('problems', [])[:8]))
            source = Path(written['zip']); made['source_zip'] = True
    if not source.is_file() or source.suffix.lower() != '.zip':
        raise ValueError('源码包必须是一个 ZIP 文件：' + str(source))
    # Freeze raw source bytes before the final logical identity/hygiene checks.
    # Candidate-search identities above only select an old file; they are not proof.
    source_sha = file_sha(source)
    identity = source_identity(source)
    if identity != current:
        raise ValueError('源码包和当前工程不是同一份源码（assets 下的脚本或配置不同）：' + str(source))
    bound = (record.get('logic_source_binding') or {}).get('current_source_sha256') if isinstance(record.get('logic_source_binding'), dict) else None
    if bound and bound != identity:
        raise ValueError('源码包和交付复核时核对的源码不是同一份；交付复核之后工程又改过，先重新出包和复核')
    test_sha, delivery_sha = record['sha256'], sha(delivered_bytes)
    evidence = manifest = None
    for earlier in _earlier(folder, archive.stem, EVIDENCE_TAIL):
        manifest = _evidence_for(earlier, test_sha, source_sha, delivery_sha)
        if manifest:
            evidence = earlier; break
    created_evidence, evidence_sha = False, None
    try:
        if evidence is None:
            evidence = _free(folder, archive.stem, EVIDENCE_TAIL)
            exported = export(archive, source, delivery, evidence, project, expected_source_sha256=source_sha)
            evidence_sha = exported['sha256']; created_evidence = True
            packaging_seconds += exported['timings']['packaging_seconds']
            if exported.get('source_sha256') != source_sha:
                raise ValueError('handoff exported a different source identity')
            ledger = exported['ledger']; made['evidence_zip'] = True
        else:
            ledger = manifest.get('ledger')
            evidence_sha = file_sha(evidence)
        # Keep source identity stable through both new export and old evidence reuse.
        if source_identity(project) != current:
            raise ValueError('source project changed during handoff')
        if file_sha(evidence) != evidence_sha:
            raise ValueError('handoff evidence changed before returning')
        _unchanged_inputs(archive, test_sha, source, source_sha, delivery, delivered_bytes)
        lines = ['测试包：' + str(archive), '源码包：' + str(source), '交接证据包：' + str(evidence)]
        if not isinstance(ledger, dict) or ledger.get('state') != 'exported':
            lines.append('证据包里没有逐项检查账本（工程里没有账本或账本是空的），接收方按缺项处理，不是全量通过的证明。')
        return {'status': 'team_handoff_ready', 'test_zip': str(archive), 'source_zip': str(source), 'evidence_zip': str(evidence),
                'sha256': {'test_zip': test_sha, 'source_zip': source_sha, 'evidence_zip': evidence_sha},
                'made': made, 'ledger': ledger, 'reply_lines': lines, 'timings': _timings(started, packaging_seconds),
                'boundary': 'Files for the hand-over only. The evidence ZIP carries the author records as they are; '
                            'it does not approve a receiver environment, real device or platform upload.'}
    except BaseException:
        if created_evidence:
            _discard_owned(evidence, evidence_sha)
        raise


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
    d = sub.add_parser('deliver', help='after prepare_delivery: make the source ZIP if needed and export the evidence ZIP')
    d.add_argument('--delivery-record', required=True, type=Path); d.add_argument('--project', required=True, type=Path)
    d.add_argument('--source', type=Path, help='an existing source ZIP made with make_source_zip.py (default: made here)')
    d.add_argument('--out-dir', type=Path, help='where the two ZIPs go (default: the folder of the test ZIP)')
    r = sub.add_parser('receive'); r.add_argument('--zip', required=True, type=Path); r.add_argument('--source', type=Path)
    r.add_argument('--evidence', type=Path); r.add_argument('--platform-feedback', type=Path); r.add_argument('--report', required=True, type=Path)
    a = p.parse_args()
    try:
        if a.mode == 'export':
            result = export(a.zip, a.source, a.delivery_record, a.out, a.project)
        elif a.mode == 'deliver':
            result = deliver(a.delivery_record, a.project, a.source, a.out_dir)
        else:
            if a.report.exists() or a.report.resolve() in {q.resolve() for q in (a.zip, a.source, a.evidence) if q}:
                raise ValueError('intake report must be a new file distinct from inputs')
            result = receive(a.zip, a.source, a.evidence, a.platform_feedback)
            a.report.parent.mkdir(parents=True, exist_ok=True)
            with a.report.open('x') as f:
                json.dump(result, f, ensure_ascii=False, indent=2); f.write('\n')
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get('intake_passed', result.get('status') in ('handoff_exported', 'team_handoff_ready')) else 1
    except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile) as exc:
        print(json.dumps({'status': 'handoff_error', 'delivery_ready': False, 'error': str(exc)}, ensure_ascii=False)); return 1


if __name__ == '__main__':
    raise SystemExit(main())
