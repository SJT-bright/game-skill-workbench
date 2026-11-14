"""Whole-game first-platform-release storage proof for the genuine Creator 1.9 path.

Actual SDK reads all return true / false, async recovery is unavailable, HOME
must not write, and trusted PLAY + drag must change the real game. Existing
released raw-typed migration contracts continue to use the general v3 gate.
"""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

PROFILE = 'creator1_first_platform_release.v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def validate(trace, native, binding, project):
    from cocos1_compat import engine_file
    from audit_native_startup_renderer import tree
    import project_qa
    errors = []
    def need(ok, message):
        if not ok:
            errors.append('STORAGE-01 Creator1: '+message)
    native, project = Path(native).resolve(), Path(project).resolve()
    files = {n: (native/n).read_bytes() for n in tree(native)}
    need(engine_file(files) is not None, 'real supported Creator 1.9.3 engine required')
    need(trace.get('schema') == 'creator1_storage_trace.v1', 'trace schema')
    need(trace.get('binding') == binding and binding.get('native_tree_sha256') == digest(tree(native)), 'actual current Native binding')
    need(trace.get('native_inputs') == tree(native), 'all actual Native files must stay unchanged')
    need(trace.get('project') == str(project) and trace.get('native') == str(native), 'actual project/native path')
    try:
        policy = project_qa.lookup(project, 'runners', trace['execution']['registered_runner'])
        need(policy.get('control_profile') == PROFILE, 'reviewed whole-game storage runner profile')
        need(trace['execution'].get('kind') == 'actual_ego_native_entry', 'actual browser producer required')
        for name, expected in policy.get('trusted_files', {}).items():
            need(sha(name) == expected, 'registered fixture/runner changed')
    except (ValueError, KeyError, OSError, TypeError) as exc:
        errors.append('STORAGE-01 Creator1: trusted runner refused: '+str(exc))
    parsed = subprocess.run([__import__('shutil').which('node') or 'node', str(Path(__file__).with_name('read_cocos1_settings.cjs'))], input=files.get('src/settings.js', b'').decode('utf-8-sig'), text=True, capture_output=True, timeout=10)
    try:
        settings = json.loads(parsed.stdout)
        home_scene = Path(settings['launchScene']).stem
        play_scenes = {Path(r['url']).stem for r in settings['scenes']} - {home_scene}
        need(parsed.returncode == 0 and bool(play_scenes), 'actual launch and playable scene catalog required')
    except (ValueError, KeyError, TypeError):
        home_scene, play_scenes = None, set()
        errors.append('STORAGE-01 Creator1: invalid actual scene catalog')
    rows = trace.get('rows', [])
    need(len(rows) == 2 and {r.get('profile') for r in rows} == {'all_true','all_false'}, 'exactly the two actual whole-game profiles required')
    for row in rows:
        try:
            path = Path(row['raw']['path']).resolve()
            picture = Path(row['screenshot']['path']).resolve()
            need(path.is_relative_to(project) and picture.is_relative_to(project), 'evidence must remain in this project')
            need(sha(path) == row['raw']['sha256'] and sha(picture) == row['screenshot']['sha256'], 'actual raw/screenshot bytes changed')
            need(picture.stat().st_size > 5000 and picture.read_bytes().startswith(b'\x89PNG'), 'actual visible game capture required')
            raw = json.loads(path.read_bytes())
            home, before, after, evidence = (raw[k] for k in ('home','before','after','evidence'))
            observations = evidence['observations']
            need(raw.get('binding') == binding and raw.get('native_inputs') == tree(native), 'raw execution current file binding')
            need(observations.get('profile') == row['profile'], 'raw profile identity')
            reads = observations.get('reads', [])
            expected = row['profile'] == 'all_true'
            need(bool(reads) and all(r.get('type') == 'boolean' and r.get('value') is expected for r in reads), 'actual SDK reads must all receive the injected Boolean')
            need(observations.get('fixture_installed_before_entry') is True and observations.get('async_available') is False and observations.get('metadata_unavailable') is True, 'fixture must precede entry; async recovery and SDK key metadata unavailable')
            need(home.get('scene') == home_scene and home.get('startup') == 'ready' and home.get('writes') == 0, 'actual HOME must be ready with no startup writes')
            need(home.get('viewport') == [390,844] and observations.get('errors') == [], 'actual phone viewport and no startup exceptions')
            need(evidence.get('scene') in play_scenes and evidence.get('startup', {}).get('phase') == 'ready', 'actual PLAY must reach the real game')
            need(type(before.get('player_x')) in (int,float) and type(after.get('player_x')) in (int,float) and before['player_x'] != after['player_x'], 'actual drag must move the real player')
            need(home['at'] < before['at'] < after['at'], 'HOME -> PLAY -> actual gameplay observation order')
            touches = evidence.get('touches', [])
            need(any(t.get('type') == 'touchmove' and t.get('trusted') is True for t in touches)
                 and all(t.get('trusted') is True for t in touches), 'trusted actual SDK touch input required')
        except (KeyError, ValueError, OSError, TypeError) as exc:
            errors.append('STORAGE-01 Creator1: invalid raw execution: '+str(exc))
    return errors


def approve(trace, native, binding):
    project = Path(trace['project']).resolve()
    errors = validate(trace, native, binding, project)
    import project_qa
    policy = project_qa.lookup(project, 'runners', trace['execution']['registered_runner'])
    identity = {'trace_sha256': digest(trace), 'runner': {'path':policy['path'],'sha256':policy['sha256']},
                'dependencies': policy.get('dependencies', {}), 'validator_sha256': sha(__file__)}
    from audit_native_storage_contract import POLICY_VERSION
    return {'tool':'audit_native_storage_contract','profile':PROFILE,'policy_version':POLICY_VERSION,
            'binding':binding,'native':str(Path(native).resolve()),'passed':not errors,'failed':len(errors),
            'checked':2,'status':'passed' if not errors else 'failed','errors':errors,
            'required_cases':['all_true','all_false'],
            'execution_receipt':{'schema':'native_storage_execution_receipt.v1','run_id':str(uuid.uuid4()),
                'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'identity':identity},
            'boundary':'Actual first-platform-release unreadable storage/startup behavior; no released raw-typed save migration or physical device verdict.'}


def consume(report, native, binding, project):
    errors = []
    try:
        path = Path(report['trace'])
        if sha(path) != report['trace_sha256']:
            raise ValueError('original trace changed')
        trace = json.loads(path.read_bytes())
        if report.get('profile') != PROFILE or report.get('passed') is not True or report.get('failed') != 0:
            raise ValueError('passing current storage approval required')
        identity = report['execution_receipt']['identity']
        if identity.get('trace_sha256') != digest(trace) or identity.get('validator_sha256') != sha(__file__):
            raise ValueError('storage rules or original execution identity changed')
        import project_qa
        policy = project_qa.lookup(project,'runners',trace['execution']['registered_runner'])
        if identity['runner'] != {'path':policy['path'],'sha256':policy['sha256']} or identity.get('dependencies') != policy.get('dependencies', {}):
            raise ValueError('registered storage runner/dependencies changed')
        errors.extend(validate(trace,native,binding,project))
    except (ValueError, KeyError, OSError, TypeError) as exc:
        errors.append('STORAGE-01 Creator1: '+str(exc))
    return errors
