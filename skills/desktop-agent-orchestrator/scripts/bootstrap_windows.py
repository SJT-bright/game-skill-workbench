#!/usr/bin/env python3
"""Inspect a portable Skill bundle and prepare missing Windows software. Never dispatches AI tasks."""
import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import platform
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
import uuid
import zipfile

sys.dont_write_bytecode = True
APPS = {'workbuddy', 'astudio', 'workbuddy_ai', 'qoder_cn', 'qoder', 'opencode', 'grok'}


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def checked_url(url, hosts):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in hosts or parsed.username or parsed.password:
        raise ValueError('URL is outside this product official sources: ' + url)
    return url


def request(url, hosts):
    checked_url(url, hosts)
    response = urllib.request.urlopen(urllib.request.Request(
        url, headers={'User-Agent': 'GameSkillMigration/2'}), timeout=30)
    try:
        checked_url(response.url, hosts)
    except Exception:
        response.close()
        raise
    return response


def read_web(url, hosts):
    with request(url, hosts) as response:
        data = response.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
        raise ValueError('Metadata response exceeds limit')
    return data.decode('utf-8')


class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script' and attrs.get('src'):
            self.sources.append(attrs['src'])


def resolve_download(item, arch):
    hosts = item['allowed_hosts']
    resolver = item['resolver']
    if arch not in item.get('architectures', ['x64']):
        raise ValueError('No verified installer for architecture ' + arch)
    if resolver == 'direct':
        url = item['urls'].get(arch) or item['urls'].get('any')
        return {'url': checked_url(url, hosts)}
    if resolver == 'workbuddy_update':
        value = json.loads(read_web(item['metadata_url'], hosts))
        return {'url': checked_url(value['url'], hosts), 'sha256': value.get('sha256hash') or None,
                'version': value.get('version')}
    if resolver == 'astudio_releases':
        value = json.loads(read_web(item['metadata_url'], hosts))
        candidates = [x for x in value['data'] if x.get('platform') == 'win' and x.get('arch') == arch]
        if len(candidates) != 1:
            raise ValueError('Windows release could not be uniquely identified')
        release = candidates[0]
        return {'url': checked_url(release['downloadUrl'], hosts), 'sha512': release.get('sha512'),
                'bytes': release.get('size'), 'version': release.get('version')}
    if resolver == 'page_scripts':
        page = read_web(item['official_page'], hosts)
        parser = Scripts()
        parser.feed(page)
        texts = [page]
        sources = [urllib.parse.urljoin(item['official_page'], x) for x in parser.sources]
        for source in sources[:30]:
            try:
                texts.append(read_web(source, hosts))
            except (OSError, ValueError):
                continue
        urls = set()
        for text in texts:
            for url in re.findall(r'https://[^\s<>"\x27\\`]+', text):
                if re.search(item['filename_pattern'], urllib.parse.urlsplit(url).path):
                    checked_url(url, hosts)
                    urls.add(url)
        if len(urls) != 1:
            raise ValueError('Resolve the exact desktop product on its official download page')
        return {'url': urls.pop()}
    raise ValueError('Use official page to select exact product/version: ' + item['official_page'])


def inventory(entries):
    records = []
    if os.name == 'nt':
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for key in (r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
                        r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'):
                try:
                    with winreg.OpenKey(hive, key) as parent:
                        for i in range(winreg.QueryInfoKey(parent)[0]):
                            try:
                                with winreg.OpenKey(parent, winreg.EnumKey(parent, i)) as sub:
                                    def value(name):
                                        try:
                                            return winreg.QueryValueEx(sub, name)[0]
                                        except OSError:
                                            return ''
                                    records.append({'name': value('DisplayName'), 'version': value('DisplayVersion'),
                                                    'publisher': value('Publisher'), 'location': value('InstallLocation')})
                            except OSError:
                                continue
                except OSError:
                    continue
    result = {}
    for item in entries:
        matches = [x for x in records if str(x['name']).casefold() in
                   {name.casefold() for name in item.get('registry_names', [])}]
        commands = [shutil.which(x) for x in item.get('commands', [])]
        commands = [x for x in commands if x]
        if item['id'] == 'grok':
            fallback = Path.home() / '.grok/bin' / ('grok.exe' if os.name == 'nt' else 'grok')
            if fallback.is_file():
                commands.append(str(fallback))
        if item['id'] == 'python':
            commands.append(sys.executable)
        result[item['id']] = {'installed_candidate': bool(matches or commands), 'registry_matches': matches,
                              'commands': list(dict.fromkeys(commands)), 'channel_ready': False,
                              'reason': 'Installation candidates only; actual window, login and tool probe required.'}
    return result


def input_inventory(path):
    if path is None:
        return {'status': 'not_supplied', 'next': 'Ask for the actual game source or planning package when making a game.'}
    path = path.expanduser().resolve(strict=True)
    entries, texts, versions = [], {}, []

    def consider(name, size, read):
        entries.append({'path': name, 'bytes': size})
        if size <= 512 * 1024 and (name.endswith('.md') or Path(name).name == 'package.json'):
            text = read().decode('utf-8-sig', errors='replace')
            texts[name] = text
            if Path(name).name == 'package.json':
                try:
                    package = json.loads(text)
                    creator = package.get('creator', {})
                    version = creator.get('version') if isinstance(creator, dict) else None
                    version = version or (package.get('version') if package.get('engine') == 'cocos-creator-js' else None)
                    if version:
                        versions.append(str(version))
                except (ValueError, AttributeError):
                    pass

    if path.is_dir():
        for child in path.rglob('*'):
            relative = child.relative_to(path)
            if child.is_symlink() or any(x in relative.parts for x in ['node_modules', '.git', 'library', 'temp', 'build']):
                continue
            if child.is_file():
                consider(relative.as_posix(), child.stat().st_size, child.read_bytes)
                if len(entries) > 12000:
                    raise ValueError('Input exceeds inventory limit; select the exact source package')
        fingerprint = None
    elif zipfile.is_zipfile(path):
        fingerprint = sha(path)
        with zipfile.ZipFile(path) as archive:
            if len(archive.infolist()) > 12000 or sum(x.file_size for x in archive.infolist()) > 2 * 1024**3:
                raise ValueError('Archive exceeds read-only inventory limits')
            seen = set()
            for member in archive.infolist():
                name = member.filename
                relative = PurePosixPath(name.replace('\\', '/'))
                normalized = relative.as_posix().casefold()
                if (relative.is_absolute() or '..' in relative.parts or PureWindowsPath(name).drive
                        or normalized in seen or (member.external_attr >> 16) & 0o170000 == 0o120000):
                    raise ValueError('Unsafe, linked or colliding archive entry: ' + name)
                seen.add(normalized)
                if not member.is_dir():
                    consider(name, member.file_size, lambda name=name: archive.read(name))
            if archive.testzip() is not None:
                raise ValueError('Archive CRC mismatch')
    else:
        raise ValueError('Select a source folder or ZIP; other archives need an available verified extractor')
    names = [x['path'].lower() for x in entries]
    source = any('/assets/' in '/' + n and n.endswith(('.ts', '.js', '.scene', '.fire')) for n in names)
    return {'status': 'inventoried', 'input': str(path), 'sha256': fingerprint, 'files': entries,
            'readable_small_documents': texts, 'creator_versions': sorted(set(versions)),
            'route': 'cocos-game-to-english' if source else 'cocos-game-from-starter',
            'boundary': 'Read-only intake only; main must read all relevant materials and decide actual source completeness.'}


def download(item, resolved, folder):
    url = resolved['url']
    suffix = '.ps1' if item['id'] == 'grok' else '.exe'
    target = folder / (item['id'] + suffix)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ValueError('Refuse overwriting installer: ' + str(target))
    partial = target.with_suffix(target.suffix + '.part')
    try:
        with request(url, item['allowed_hosts']) as response, partial.open('xb') as output:
            if suffix == '.exe' and 'text/html' in response.headers.get('Content-Type', '').lower():
                raise ValueError('Official download returned HTML instead of an installer')
            total = 0
            for block in iter(lambda: response.read(1024 * 1024), b''):
                total += len(block)
                if total > 1024**3:
                    raise ValueError('Installer exceeds download size limit')
                output.write(block)
        with partial.open('rb') as stream:
            header = stream.read(2)
        if total == 0 or (suffix == '.exe' and header != b'MZ'):
            raise ValueError('Empty or invalid executable download')
        if resolved.get('bytes') is not None and total != resolved['bytes']:
            raise ValueError('Official byte length mismatch')
        for algorithm in ('sha256', 'sha512'):
            expected = resolved.get(algorithm)
            if expected:
                h = hashlib.new(algorithm)
                with partial.open('rb') as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b''):
                        h.update(block)
                if h.hexdigest().lower() != expected.lower():
                    raise ValueError('Official digest mismatch: ' + algorithm)
        partial.rename(target)
        return {'status': 'downloaded_pending_install', 'path': str(target), 'bytes': total,
                'sha256': sha(target), 'source': url, 'installed': False, 'channel_ready': False}
    finally:
        if partial.exists():
            partial.unlink()


def launch_signed_installer(path):
    if os.name != 'nt' or path.suffix.lower() != '.exe':
        return {'status': 'manual_step', 'reason': 'Official scripts require source review; no automatic script execution.'}
    code = '$s=Get-AuthenticodeSignature -LiteralPath $env:GAME_SKILL_INSTALLER; @{status=[string]$s.Status; subject=[string]$s.SignerCertificate.Subject}|ConvertTo-Json -Compress'
    signature = subprocess.run(['powershell.exe', '-NoProfile', '-Command', code],
                               env={**os.environ, 'GAME_SKILL_INSTALLER': str(path)},
                               capture_output=True, text=True, check=True)
    details = json.loads(signature.stdout.lstrip('\ufeff'))
    if details['status'] != 'Valid':
        return {'status': 'signature_review_required', 'signature': details}
    child = subprocess.Popen([str(path)])
    return {'status': 'wizard_opened', 'pid': child.pid, 'signature': details,
            'boundary': 'User completes legal terms and installation; launch is not installation acceptance.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle-dir', type=Path, required=True)
    parser.add_argument('--mode', choices=['single', 'multi'])
    parser.add_argument('--project-input', type=Path)
    parser.add_argument('--state-dir', type=Path)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--launch-installers', action='store_true')
    parser.add_argument('--inspect-only', action='store_true')
    args = parser.parse_args()
    if os.name != 'nt' and not args.inspect_only:
        parser.error('Windows preparation runs on Windows; --inspect-only is available on other hosts.')
    bundle = args.bundle_dir.resolve(strict=True)
    spec = importlib.util.spec_from_file_location('bundle_installer', bundle / 'install_skills.py')
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    installer.verify(bundle)
    mode = args.mode
    if mode is None:
        answer = input('本次是否启用桌面多 Agent？[1] 启用 [2] 本次单Agent [0] 退出：').strip()
        if answer not in {'1', '2'}:
            return 0
        mode = 'multi' if answer == '1' else 'single'
    run_id = str(uuid.uuid4())
    state = args.state_dir or Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'GameSkillMigration' / run_id
    state = state.expanduser().absolute()
    if state.is_relative_to(bundle) or state.exists():
        raise ValueError('Use a fresh state directory outside the verified bundle')
    state.mkdir(parents=True)
    catalog = json.loads((Path(__file__).resolve().parents[1] / 'assets/windows-software.json').read_text(encoding='utf-8'))
    if {x['id'] for x in catalog['apps']} != APPS or len(catalog['apps']) != len(APPS):
        raise ValueError('Software catalog must contain the exact seven applications')
    entries = (catalog['apps'] if mode == 'multi' else []) + catalog['runtimes']
    observed = inventory(entries)
    report = {'run_id': run_id, 'mode': mode, 'platform': platform.platform(), 'inspection_only': args.inspect_only,
              'authorization_source': 'Current bootstrap selection; agents must still verify the current human request.',
              'started_at': datetime.now(timezone.utc).isoformat(), 'inventory': observed,
              'input': input_inventory(args.project_input), 'software': {}, 'status': 'prepared_not_channel_accepted'}
    save(state / 'environment.json', report)
    if not args.inspect_only:
        configured = os.environ.get('CODEX_HOME')
        target = (Path(configured).expanduser() if configured else Path.home() / '.codex') / 'skills'
        report['skill_installation'] = installer.install(bundle, target.absolute())
    arch = 'arm64' if 'arm' in platform.machine().lower() else 'x64'
    for item in entries:
        if observed[item['id']]['installed_candidate']:
            report['software'][item['id']] = {'status': 'existing_preserved_pending_channel_probe'}
        elif args.download and not args.inspect_only:
            try:
                resolved = resolve_download(item, arch)
                result = download(item, resolved, state / 'downloads')
                if args.launch_installers:
                    result['installer'] = launch_signed_installer(Path(result['path']))
                report['software'][item['id']] = result
            except Exception as exc:
                report['software'][item['id']] = {'status': 'needs_resolution', 'official_page': item['official_page'],
                                                'reason': str(exc)}
        else:
            report['software'][item['id']] = {'status': 'missing', 'official_page': item['official_page']}
        save(state / 'environment.json', report)
    if not args.inspect_only:
        helper = bundle / 'support-skills/chrome-mobile-testing/scripts/prepare_chrome.py'
        try:
            command = [sys.executable, str(helper)]
            if args.download:
                command.append('--install-runtime')
            completed = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=300)
            report['chrome_runtime'] = json.loads(completed.stdout)
        except Exception as exc:
            report['chrome_runtime'] = {'status': 'needs_resolution', 'reason': str(exc)}
        save(state / 'environment.json', report)
    next_steps = ('读取 environment.json 和当前已安装Skill。先由本轮人类选择是否启用桌面多Agent，' 
                  '本轮已明确选择则不重复。检查新机Computer Use与image_gen是否实际可用。单Agent则独立制作；' 
                  '多Agent仅在七应用池核身份/登录/工具/占用，逐任务实际发送、回收和独立验收。' 
                  'needs_resolution按对应官方下载页继续浏览器下载；不要以环境报告或原机证据宣称可用。' 
                  '安装向导、账号登录、协议与验证码按当前要求由本人完成。' 
                  '读取input.route及原始材料，纯策划先启动包做游戏，完整源进入游戏换英文。')
    (state / '下一步给Codex.txt').write_text(next_steps, encoding='utf-8')
    print(json.dumps({'status': report['status'], 'mode': mode, 'report': str(state / 'environment.json'),
                      'next_steps': str(state / '下一步给Codex.txt')}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'status': 'failed', 'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
