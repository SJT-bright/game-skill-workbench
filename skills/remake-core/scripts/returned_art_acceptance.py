#!/usr/bin/env python3
"""Exact-byte user acceptance for visual rework after delivery; never an AI art pass.

The agent records the user's existing returned-work instruction once. There is no
new approval question, no image analysis, and no modification to old art reports.
This record controls visual acceptance only; source, runtime, ZIP and upload checks
keep their separate results. Run record after the requested edit and final build.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import tempfile
import os
import zipfile

HERE = Path(__file__).resolve().parent
MANIFEST = Path('.tiktok-kit/returned-art-acceptance.json')
SCHEMA = 'returned-art-acceptance.v1'
KINDS = {'image', 'crop', 'font', 'text', 'layout'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as out:
        json.dump(value, out, ensure_ascii=False, indent=2); out.write('\n'); name = out.name
    os.replace(name, path)


def source_hash(project):
    from tiktok_finalize import source_sha256
    root = Path(project)
    identities = {p: sha(root/p) for p in ('project.json', 'package.json') if (root/p).is_file()}
    identities['production_source'] = source_sha256(root)
    return hashlib.sha256(json.dumps(identities, sort_keys=True).encode()).hexdigest()


def web_hash(web):
    path = HERE.parents[1]/'cocos-game-to-english/scripts'
    if str(path) not in sys.path: sys.path.insert(0, str(path))
    from chinese_audit import export_manifest
    return export_manifest(Path(web))['sha256']


def native_hash(native):
    from verify_native_zip import native_directory_digest
    return native_directory_digest(Path(native))


def available_native_origin(project, native):
    """Use an existing source-to-Native seal without requiring new art evidence."""
    import tiktok_finalize as F
    digest = native_hash(native)
    proof = Path(project)/F.PREPARED_NATIVE/(digest+'.json')
    if not proof.is_file():
        return {'status': 'unrecorded', 'basis': 'actual bytes bound; build origin must be established by the production/build record'}
    F.check_prepared_native(project, native)
    if (F.read_source_record(project) or {}).get('source_sha256') != F.source_sha256(project):
        raise ValueError('existing Native preparation points to stale source; update only build identity')
    return {'status': 'verified_existing_preparation', 'record_sha256': sha(proof)}


def previous_identity(archive=None, delivery=None):
    if bool(archive) == bool(delivery):
        raise ValueError('identify the previous delivered ZIP or its existing delivery record')
    if archive:
        path = Path(archive).resolve()
        with zipfile.ZipFile(path) as z:
            if z.testzip() is not None: raise ValueError('previous ZIP CRC failed')
            entries = z.namelist()
            if not any(n.endswith('game.json') for n in entries):
                raise ValueError('previous delivered game ZIP lacks game.json')
        return {'archive': str(path), 'sha256': sha(path), 'basis': 'actual_previous_zip'}
    path = Path(delivery).resolve(); data = read(path)
    if not isinstance(data, dict): raise ValueError('previous delivery record must be a JSON object')
    digest = data.get('sha256') or data.get('zip_sha256')
    archive = data.get('archive') or data.get('zip') or data.get('path')
    if not isinstance(archive, str) or not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('previous delivery record needs archive/zip/path and SHA-256')
    file = Path(archive)
    if file.is_file() and sha(file) != digest: raise ValueError('previous delivery ZIP differs from its recorded bytes')
    return {'archive': archive, 'sha256': digest, 'basis': 'existing_delivery_record',
            'record': str(path), 'record_sha256': sha(path)}


def scope_rows(project, scope):
    root = Path(project).resolve()
    if not isinstance(scope, list) or not scope: raise ValueError('list the requested visual changes')
    rows = []
    for item in scope:
        if not isinstance(item, dict) or item.get('kind') not in KINDS or not str(item.get('request', '')).strip():
            raise ValueError('each visual change needs kind and the requested change; functional checks cannot be waived')
        rel = item.get('path', '')
        if not isinstance(rel, str) or not rel or PurePosixPath(rel).is_absolute() or '..' in PurePosixPath(rel).parts:
            raise ValueError('visual scope needs an exact project-relative file')
        p = root/rel
        if not p.resolve().is_relative_to(root): raise ValueError('visual scope escapes project')
        if p.is_dir(): raise ValueError('visual scope must name files, not whole folders')
        rows.append({'path': rel, 'kind': item['kind'], 'request': item['request'], 'sha256': sha(p) if p.is_file() else None})
    return rows


def record(project, web, native, instruction, scope, previous_zip=None, previous_delivery=None):
    project = Path(project).resolve(); web = Path(web).resolve(); native = Path(native).resolve()
    if not (project/'assets').is_dir() or not (web/'index.html').is_file() or not (native/'game.json').is_file():
        raise ValueError('current source assets, playable Web index.html and processed Native game.json are required')
    if not isinstance(instruction, str) or not instruction.strip(): raise ValueError('retain the exact existing user request')
    document = {'schema': SCHEMA, 'status': 'user_accepted', 'ai_art_rechecked': False,
        'authority': 'user_requested_visual_rework_and_test_package',
        'scope_domain': 'art_only', 'functional_acceptance': False,
        'recorded_at': datetime.now(timezone.utc).isoformat(), 'user_instruction': instruction,
        'previous_delivery': previous_identity(previous_zip, previous_delivery),
        'scope': scope_rows(project, scope), 'source_sha256': source_hash(project),
        'web': {'path': str(web), 'sha256': web_hash(web)},
        'native': {'path': str(native), 'sha256': native_hash(native)},
        'native_origin': available_native_origin(project, native),
        'note': '用户已授权返工后交测试包；美术按本次授权接受，未重复 AI 美术验收。功能、分包体积和同版交付核对保持独立。'}
    write(project/MANIFEST, document)
    return document


def validate(project, web=None, native=None, native_files=None):
    project = Path(project).resolve(); path = project/MANIFEST; doc = read(path)
    if not isinstance(doc, dict): raise ValueError('returned acceptance must be a JSON object')
    if (doc.get('schema') != SCHEMA or doc.get('status') != 'user_accepted' or
        doc.get('ai_art_rechecked') is not False or doc.get('functional_acceptance') is not False or
        doc.get('scope_domain') != 'art_only' or doc.get('authority') != 'user_requested_visual_rework_and_test_package' or
        not isinstance(doc.get('user_instruction'), str) or not doc['user_instruction'].strip()):
        raise ValueError('not a returned visual acceptance record')
    previous = doc.get('previous_delivery')
    if not isinstance(previous, dict): raise ValueError('previous delivery identity must be a JSON object')
    digest = previous.get('sha256')
    if (not isinstance(previous.get('archive'), str) or not previous['archive'] or
        not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest)):
        raise ValueError('previous delivery identity missing')
    if scope_rows(project, doc.get('scope')) != doc['scope'] or source_hash(project) != doc.get('source_sha256'):
        raise ValueError('requested artwork/source changed after acceptance; bind the completed requested edit, do not rerun all art')
    if not all(isinstance(doc.get(key), dict) and isinstance(doc[key].get('path'), str) for key in ('web', 'native')):
        raise ValueError('current Web and Native identities must be JSON objects with paths')
    wb = Path(web or doc['web']['path']); nt = Path(native or doc['native']['path'])
    if not wb.is_dir() or web_hash(wb) != doc['web']['sha256']:
        raise ValueError('current Web differs from the accepted returned candidate')
    if not nt.is_dir() or native_hash(nt) != doc['native']['sha256']:
        raise ValueError('current Native differs from the accepted returned candidate')
    origin = available_native_origin(project, nt)
    if not isinstance(doc.get('native_origin', {}), dict): raise ValueError('Native origin must be a JSON object')
    if doc.get('native_origin', {}).get('status') == 'verified_existing_preparation' and origin != doc['native_origin']:
        raise ValueError('existing Native source binding changed; update only build identity')
    if native_files is not None:
        from verify_native_zip import tree_digest
        if tree_digest({k: hashlib.sha256(v).hexdigest() for k, v in native_files.items()}) != doc['native']['sha256']:
            raise ValueError('actual writer Native differs from accepted returned candidate')
    return {'state': 'user_accepted_returned_art', 'status': 'user_accepted', 'ai_art_rechecked': False,
            'functional_acceptance': False, 'manifest': str(path), 'manifest_sha256': sha(path),
            'source_sha256': doc['source_sha256'], 'web': doc['web'], 'native': doc['native'],
            'scope': doc['scope'], 'previous_delivery': previous, 'recorded_at': doc['recorded_at'],
            'native_origin': doc.get('native_origin', {'status': 'unrecorded'})}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--project', required=True, type=Path)
    sub = p.add_subparsers(dest='command', required=True)
    r = sub.add_parser('record'); r.add_argument('--web', required=True, type=Path); r.add_argument('--native', required=True, type=Path)
    prior = r.add_mutually_exclusive_group(required=True); prior.add_argument('--previous-zip', type=Path); prior.add_argument('--previous-delivery', type=Path)
    r.add_argument('--instruction-file', required=True, type=Path); r.add_argument('--scope-file', required=True, type=Path)
    sub.add_parser('check'); a = p.parse_args(argv)
    try:
        result = (record(a.project, a.web, a.native, a.instruction_file.read_text(encoding='utf-8'), read(a.scope_file), a.previous_zip, a.previous_delivery)
                  if a.command == 'record' else validate(a.project))
    except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile) as error:
        p.exit(1, str(error)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
