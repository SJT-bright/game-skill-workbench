"""Refuse known test-ad tools and production Credits/About windows in upload bytes.
This finite signature gate does not prove arbitrary code or image-only UI is clean.
"""
from pathlib import PurePosixPath
import re
import json

MARKERS = (b'__adSimulator', b'__local_ad_simulator', b'__ad-simulator', b'SIM_BUSY_OR_USED',
           b'Local test ad', b'Complete test ad', b'merge-preview-ad', b'installMergePreviewAds')
TOOL_FILES = {'ad-simulator.js', 'ad-simulator.min.js', 'preview-ads.js', 'preview-ads.min.js'}
# Exact UI labels/routes, not currency credits, comments, licenses or art filenames.
WINDOW_LABEL = re.compile(r'''(["'`])(?:credits(?:\s*/\s*about)?|制作人员|制作说明|鸣谢)\1''', re.I)
WINDOW_ROUTE = re.compile(r'\b(?:openCredits|showCredits|creditsPanel|creditsDialog|creditsWindow)\b', re.I)
PRODUCTION_NOTES = ('Original game art and sounds', 'English edition ·', 'Made with ChatGPT')


def check_entry(name, data):
    filename = PurePosixPath(name).name.casefold()
    if filename in TOOL_FILES:
        raise ValueError('Local ad simulator must not ship in the TikTok upload package: ' + name)
    for marker in MARKERS:
        if marker.lower() in data.lower():
            raise ValueError('Local ad simulator residue (' + marker.decode() + ') in upload package: ' + name)
    # Scan code and serialized UI, including disabled/unreachable routes and escaped labels.
    # LICENSE/NOTICE documents and unused texture filenames are not player windows.
    if PurePosixPath(name).suffix.lower() in ('.js', '.json', '.html', '.htm', '.prefab', '.fire', '.scene'):
        text = data.decode('utf-8', errors='replace')
        text = re.sub(r'\\u([0-9a-fA-F]{4})|\\x([0-9a-fA-F]{2})',
                      lambda m: chr(int(m.group(1) or m.group(2), 16)), text)
        for marker in MARKERS:
            if marker.decode().casefold() in text.casefold():
                raise ValueError('Local ad simulator escaped residue in upload package: ' + name)
        if filename.endswith('.js'):
            text = re.sub(r"""("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)|(//[^\n]*|/\*[\s\S]*?\*/)""",
                          lambda m: m.group(1) or '', text)
        # Cocos 2.4 standalone SpriteFrame import metadata names an art asset,
        # not a serialized player node/label. Ignore only that typed name field;
        # simulator markers above and all other fields still remain scanned.
        if filename.endswith('.json'):
            try:
                value = json.loads(text)
                if (isinstance(value, list) and len(value) == 11
                        and value[3] == ['cc.SpriteFrame']
                        and isinstance(value[5], list) and len(value[5]) == 1
                        and isinstance(value[5][0], dict)
                        and set(value[5][0]) <= {'name', 'rect', 'offset', 'originalSize', 'capInsets'}
                        and all(key in value[5][0] for key in ('name', 'rect', 'originalSize'))):
                    value[5][0]['name'] = ''
                    text = json.dumps(value, ensure_ascii=False)
            except (ValueError, TypeError):
                pass
        match = WINDOW_LABEL.search(text) or WINDOW_ROUTE.search(text)
        note = next((s for s in PRODUCTION_NOTES if s in text), None)
        html_label = re.search(r'>\s*(?:Credits(?:\s*/\s*About)?|制作人员|鸣谢)\s*<', text, re.I) if filename.endswith(('.html', '.htm')) else None
        if match or note or html_label:
            found = match.group(0) if match else note or html_label.group(0)
            raise ValueError('Forbidden Credits/About player window (' + found + ') in upload package: ' + name)


def enforce_files(files):
    for name, data in files.items():
        check_entry(name, data)
    return {'local_ad_simulator_absent': True, 'forbidden_player_windows_absent': True,
            'scope': 'known simulator bytes/files and code/serialized Credits/About UI signatures; no image-only or arbitrary-program proof'}
