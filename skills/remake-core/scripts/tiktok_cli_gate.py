"""Run the official TikTok CLI on an isolated extraction of a verified ZIP."""
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import zipfile


PACKAGE = '@ttmg/cli'
VERSION = '0.4.7'
REGISTRY = 'https://registry.npmjs.org/'


def run(command, *, cwd, timeout):
    started = time.monotonic()
    completed = subprocess.run(command, cwd=cwd, capture_output=True, encoding='utf-8',
                               errors='replace', timeout=timeout, check=False)
    return completed, round(time.monotonic() - started, 3)


def installed_entry(prefix):
    package = prefix / 'node_modules' / '@ttmg' / 'cli'
    try:
        manifest = json.loads((package / 'package.json').read_text(encoding='utf-8'))
        entry = package / 'dist' / 'index.js'
        if manifest['name'] == PACKAGE and manifest['version'] == VERSION and entry.is_file():
            return entry
    except (OSError, KeyError, ValueError):
        pass
    return None


def setup(work, receipt):
    node = shutil.which('node')
    if not node:
        raise ValueError('Node.js is required for TikTok CLI (20.19.1–20.x or 22+ for the pinned release)')
    version, _ = run([node, '--version'], cwd=work, timeout=15)
    receipt['node_version'] = version.stdout.strip()
    match = re.fullmatch(r'v(\d+)\.(\d+)\.(\d+)', receipt['node_version'])
    if version.returncode or not match:
        raise ValueError('Could not determine the Node.js version for TikTok CLI')
    number = tuple(map(int, match.groups()))
    if not ((20, 19, 1) <= number < (21, 0, 0) or number >= (22, 0, 0)):
        raise ValueError('TikTok CLI needs Node.js 20.19.1–20.x or 22+')

    cache = Path.home() / '.cache' / 'gameskills' / 'ttmg-cli'
    target = cache / VERSION
    entry = installed_entry(target)
    receipt['installation'] = 'cached'
    if not entry:
        npm = shutil.which('npm')
        if not npm:
            raise ValueError('npm is required to install the pinned TikTok CLI from the npm registry')
        receipt['installation'] = 'installing'
        cache.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.install-', dir=cache) as staging:
            pending = Path(staging) / 'cli'
            command = [npm, 'install', '--prefix', str(pending), '--cache', str(Path(staging) / 'npm-cache'),
                       '--registry', REGISTRY, '--engine-strict', '--no-audit', '--no-fund',
                       '--no-save', '--package-lock=false', f'{PACKAGE}@{VERSION}']
            install, seconds = run(command, cwd=work, timeout=240)
            receipt['install_result'] = {'exit_code': install.returncode, 'seconds': seconds}
            if install.returncode or not installed_entry(pending):
                raise ValueError('TikTok CLI installation failed: ' + (install.stderr or install.stdout)[-1800:].strip())
            try:
                pending.rename(target)
            except OSError:
                if not installed_entry(target):
                    raise
            entry = installed_entry(target)
        receipt['installation'] = 'installed'
    actual, _ = run([node, str(entry), '--version'], cwd=work, timeout=20)
    receipt['version'] = actual.stdout.strip()
    if actual.returncode or receipt['version'] != VERSION:
        raise ValueError('Installed TikTok CLI did not report the pinned version')
    return node, str(entry)


def invoke(cli, subcommand, project, work):
    command = [*cli, subcommand, '--dir', str(project), '--format', 'json', '--include-passed']
    completed, seconds = run(command, cwd=work, timeout=180)
    result = {'exit_code': completed.returncode, 'seconds': seconds, 'passed': False}
    try:
        payload = json.loads(completed.stdout)
        if not isinstance(payload, dict) or payload.get('command') != subcommand:
            raise ValueError('unexpected JSON shape')
    except ValueError:
        result['error'] = 'Expected a structured TikTok CLI result'
        result['output_tail'] = (completed.stderr or completed.stdout)[-1800:].strip()
        return result
    result['result'] = payload
    summary = payload.get('summary')
    success_status = {'check': 'passed', 'build': 'succeeded'}[subcommand]
    result['passed'] = (completed.returncode == 0 and payload.get('status') == success_status
                        and isinstance(summary, dict) and summary.get('errors') == 0)
    return result


def cleanup_build(step):
    payload = step.get('result') or {}
    path = (payload.get('artifact') or {}).get('outputDirectory')
    operation = payload.get('operationId')
    if not isinstance(path, str) or not isinstance(operation, str):
        return
    # Remove only the output this invocation created in the CLI's build area.
    output = Path(path)
    expected = Path.home() / '__TTMG__' / 'build' / operation
    if (re.fullmatch(r'build_[0-9a-f-]{36}', operation) and output == expected
            and output.resolve() == expected and output.is_dir()):
        shutil.rmtree(output)


def verify(archive, sha256):
    receipt = {'package': PACKAGE, 'expected_version': VERSION, 'registry': REGISTRY,
               'archive_sha256': sha256, 'passed': False, 'errors': [],
               'boundary': 'Local TikTok CLI check and build; platform upload and device tests are separate.'}
    try:
        data = Path(archive).read_bytes()
        if hashlib.sha256(data).hexdigest() != sha256:
            raise ValueError('ZIP changed after the size and CRC check')
        with tempfile.TemporaryDirectory(prefix='gameskills-ttmg-') as directory:
            work = Path(directory)
            cli = setup(work, receipt)
            project = work / 'native'
            # Only the exact snapshot already validated by upload_size_gate is extracted.
            with zipfile.ZipFile(io.BytesIO(data)) as zipped:
                zipped.extractall(project)
                names = {member.filename for member in zipped.infolist() if not member.is_dir()}
            extracted = {file.relative_to(project).as_posix() for file in project.rglob('*') if file.is_file()}
            if extracted != names:
                raise ValueError('Extraction changed ZIP member paths on this computer')
            receipt['extracted_files'] = len(extracted)
            for subcommand in ('check', 'build'):
                receipt[subcommand] = invoke(cli, subcommand, project, work)
                if not receipt[subcommand]['passed']:
                    receipt['errors'].append(f'ttmg {subcommand} failed; see its command result')
            cleanup_build(receipt['build'])
        if hashlib.sha256(Path(archive).read_bytes()).hexdigest() != sha256:
            raise ValueError('ZIP changed during TikTok CLI verification')
    except (OSError, ValueError, subprocess.SubprocessError, zipfile.BadZipFile) as error:
        receipt['errors'].append(str(error))
    receipt['passed'] = not receipt['errors']
    return receipt
