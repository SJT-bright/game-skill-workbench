#!/usr/bin/env python3
"""Verify a live local phone preview against the Web hash of the delivered build."""
import argparse
from datetime import datetime, timezone
import http.client
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'remake-core' / 'scripts'))
from browser_slots import process_identity, slots
from check_known_issues import tree_sha
from serve_preview import AD_SIMULATOR_PATH, entry_readback


def verify_preview(url, web_sha256, *, require_ad_simulator=False):
    if not url:
        raise ValueError('缺同版试玩链接：只有 ZIP，交付未完成。先启动手机试玩并传入 --preview-url。')
    parts = urlsplit(url)
    if (parts.scheme != 'http' or parts.hostname != '127.0.0.1' or not parts.port
            or url != f'http://127.0.0.1:{parts.port}/'):
        raise ValueError('试玩链接须为 serve_preview.py 提供的本地手机入口。')
    if not isinstance(web_sha256, str) or not re.fullmatch(r'[a-f0-9]{64}', web_sha256):
        raise ValueError('缺同版 Web 构建指纹。')
    slot = next((s for s in slots() if s.get('kind') == 'preview' and s.get('url') == url
                 and s.get('keep') and s.get('dir') and s.get('pid') and s.get('process_identity')
                 and s['process_identity'] == process_identity(s['pid'])), None)
    if slot is None:
        raise ValueError('试玩链接未绑定有效的保留快照。用 --snapshot 启动或恢复同版试玩。')
    snapshot = Path(slot['dir'])
    if tree_sha(snapshot) != web_sha256:
        raise ValueError('试玩快照和测试包绑定的 Web 构建不同。')

    def fetch(target):
        request = urlsplit(target)
        if request.scheme != parts.scheme or request.netloc != parts.netloc:
            raise ValueError('试玩入口跳出了本地服务。')
        path = request.path or '/'
        if request.query:
            path += '?' + request.query
        connection = http.client.HTTPConnection(parts.hostname, parts.port, timeout=5)
        try:
            connection.request('GET', path, headers={'Cache-Control': 'no-cache'})
            with connection.getresponse() as response:
                if response.status != 200:
                    raise ValueError(f'试玩入口 HTTP {response.status}。')
                body = response.read()
        finally:
            connection.close()
        if target == url and b'content="fixed-phone-v1"' not in body:
            raise ValueError('链接未打开固定手机试玩入口。')
        return body

    ok, files, problem = entry_readback(url, snapshot, html_injected=None, fetch=fetch)
    if not ok:
        raise ValueError(problem)
    simulated = any(row['file'] == AD_SIMULATOR_PATH and row['same'] for row in files)
    if require_ad_simulator and not simulated:
        raise ValueError('本轮检查需要模拟广告。用当前候选开启模拟广告后核对同版试玩。')
    return {'url': url, 'web_tree_sha256': web_sha256, 'slot_id': slot['id'],
            'checked_at': datetime.now(timezone.utc).isoformat(), 'entry_files': files,
            'ad_simulator': simulated,
            'markdown_link': f'[同版手机试玩（模拟广告）]({url})' if simulated else f'[同版手机试玩]({url})'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview-url', required=True)
    parser.add_argument('--web-sha256', required=True, help='Web tree SHA-256 from the matching build evidence')
    parser.add_argument('--require-ad-simulator', action='store_true', help='require the local manual reward simulator')
    args = parser.parse_args()
    try:
        print(json.dumps(verify_preview(args.preview_url, args.web_sha256,
                                        require_ad_simulator=args.require_ad_simulator), ensure_ascii=False))
    except (ValueError, OSError) as error:
        print(json.dumps({'status': 'refuse', 'error': str(error)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
