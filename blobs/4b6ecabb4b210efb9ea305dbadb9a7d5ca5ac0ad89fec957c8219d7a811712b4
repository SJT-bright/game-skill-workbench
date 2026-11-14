"""Recognize the real Creator 1.9 export format; never infer it from a filename alone."""
import re
import hashlib
import json
from pathlib import Path


def engine_file(files):
    manifest = json.loads(Path(__file__).with_name('official_engine_sources.json').read_bytes())
    known = {(r['sha256'], r['bytes']) for r in manifest.get('artifacts', [])
             if r.get('engine_version') == '1.9.3' and r.get('export_target') == 'wechatgame'}
    for name in ('cocos2d-js-min.js', 'cocos2d-js.js'):
        code = files.get(name, b'')
        if isinstance(code, str):
            code = code.encode()
        if ((hashlib.sha256(code).hexdigest(), len(code)) in known
                and re.search(rb'cc\.ENGINE_VERSION\s*=\s*[\"\']1\.9\.3[\"\']', code)
                and b'getTouchesByEvent:function' in code
                and b'cc.game' in code and b'cc.loader' in code):
            return name
    return None
