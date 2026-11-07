#!/usr/bin/env python3
"""Chinese audit before an English trial link (English pack, Saul 2026-11-01).

Garden Guardians: "高波来袭！" sat in the `wave` slice of the Spine atlas page highwave.png while the old
image-review.json said "chinese: no, slices_reviewed: true". No script string had those characters, and nothing
checked that anyone had looked at the slice. This tool builds the evidence from the files themselves and a checker
that recomputes everything, so a hand-written "done / no / true" can never pass.

  chinese_audit.py scan   --project <P> [--export <web export>] [--out <dir>] [--ocr auto|vision|tesseract|windows|none|fake]
  chinese_audit.py review --project <P> [--out <dir>] (--id <id> [--id ...] | --file <glob> [--field <regex>])
                          --verdict <chinese|false_positive|no_text|
                          english_only|not_displayed|fixed> --by "<who>" [--evidence <file> ...]
                          [--evidence-kind <ocr|slice_view|isolated_render|natural_play|text_context>]
                          [--reason "<why>"] [--supersedes <review id>]
  chinese_audit.py sheet  --project <P> [--out <dir>] [--pending | --id ...]
  chinese_audit.py check  --project <P> [--export <export>] [--snapshot <served snapshot>] [--out <dir>] [--json]

Default <dir> is <P>/docs/english/chinese-audit/ (audit.json, slices/, ocr/, reviews.json, evidence/, sheets/,
check-result.json). Nothing is written under assets/ or the export.
scan: exit 0 when the scan ran (findings included), 2 on bad input. review: 0 recorded, 1 refused, 2 bad input.
sheet: 0 written, 1 nothing to show, 2 bad input. check: 0 passed, 1 not passed, 2 bad input.
Only check computes `passed`; a `passed` field anywhere else is ignored.
What it cannot prove: that a person's verdict on a picture is right. It proves the verdict exists, is about the
current pixels, carries real evidence files, and that nothing changed since.
"""
import argparse
import bisect
import datetime
import fnmatch
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
SCANNER_VERSION = 'chinese_audit 1.0.0 (2026-11-01)'
RULES_VERSION = 'chinese-rules 2026-11-01.3'      # .3: @property tooltip/displayName strings are editor-only
SCHEMA = 'chinese_audit.v1'
DEFAULT_OUT = Path('docs') / 'english' / 'chinese-audit'

IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'}
SCRIPT_SUFFIXES = {'.js', '.ts', '.mjs', '.cjs'}
SERIAL_SUFFIXES = {'.fire', '.prefab', '.scene', '.json', '.anim'}
TEXT_SUFFIXES = {'.txt', '.csv', '.tsv', '.xml', '.html', '.htm', '.css', '.md', '.yaml', '.yml', '.ini',
                 '.properties', '.effect', '.mtl', '.chunk', '.glsl', '.lua', '.text', '.svg', '.pac'}
AUDIO_SUFFIXES = {'.mp3', '.ogg', '.wav', '.m4a', '.aac', '.flac'}
FONT_SUFFIXES = {'.ttf', '.otf', '.woff', '.woff2'}
SKIP_NAMES = {'.DS_Store', 'Thumbs.db', 'desktop.ini'}
SKIP_DIRS = {'.git', '__pycache__', '__MACOSX', '.svn'}     # caches only; assets/temp etc. are real content
VERDICTS = ('chinese', 'false_positive', 'no_text', 'english_only', 'not_displayed', 'fixed')
CLEARING = set(VERDICTS) - {'chinese'}
EVIDENCE_KINDS = ('ocr', 'slice_view', 'isolated_render', 'natural_play', 'text_context')
LOW_CONFIDENCE = 0.5          # Vision reports 0.3 / 0.5 / 1.0; below 0.5 counts as low
MIN_OCR_SIDE = 64             # short side below this is enlarged before recognition
MAX_OCR_SIDE = 8192
ENV_FAKE = 'CHINESE_AUDIT_FAKE_OCR'

HAN = ('\u3007\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002ffff\U00030000-\U000323af')
CJK_PUNCT = '\u3000-\u303f\uff01-\uff0f\uff1a-\uff20\uff3b-\uff40\uff5b-\uff65\uffe0-\uffef'
CHINESE = re.compile('[%s%s]' % (HAN, CJK_PUNCT))
CHINESE_RUN = re.compile('[%s%s]+' % (HAN, CJK_PUNCT))
ESCAPE = re.compile(r'\\u\{([0-9a-fA-F]{1,6})\}|\\u([0-9a-fA-F]{4})')
SURROGATE = re.compile(r'\\u([dD][89aAbB][0-9a-fA-F]{2})\\u([dD][cCdDeEfF][0-9a-fA-F]{2})')
HAN_ONLY = re.compile('[%s]' % HAN)
ASCII_LETTERS = re.compile('[A-Za-z]')
MAYBE_ESCAPED = re.compile(r'\\u(\{[0-9a-fA-F]+\}|[0-9a-fA-F]{4})')
LATIN = re.compile(r'^[\u0000-\u024f\u1e00-\u1eff\u2000-\u206f\u20a0-\u20cf\u2100-\u214f]*$')
LOG_CALL = re.compile(r'^(console\.\w+|cc\.(log|warn|error|info|debug|logID|warnID|errorID|assert))$')
EDITOR_LABEL = re.compile(r'\b(tooltip|displayName)\s*:\s*$')
HEX64 = re.compile(r'^[0-9a-f]{64}$')


class Usage(Exception):
    """Bad input or environment: exit 2."""


class Refused(Exception):
    """A request that is refused on its merits: exit 1."""


# ---------------------------------------------------------------- small helpers

def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def sha_json(obj):
    return sha_bytes(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))


def short_id(prefix, *parts):
    return '%s-%s' % (prefix, sha_bytes('\0'.join(parts).encode('utf-8'))[:10])


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return default


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', errors='backslashreplace')
    os.replace(str(tmp), str(path))


def decode_escapes(text):
    if '\\' not in text:
        return text
    text = SURROGATE.sub(lambda m: chr(0x10000 + ((int(m.group(1), 16) - 0xD800) << 10) + int(m.group(2), 16) - 0xDC00),
                         text)

    def one(m):
        value = int(m.group(1) or m.group(2), 16)
        return chr(value) if value <= 0x10FFFF and not 0xD800 <= value <= 0xDFFF else m.group(0)
    return ESCAPE.sub(one, text)


def has_chinese(text):
    return bool(text) and bool(CHINESE.search(text))


def chinese_runs(text):
    return ''.join(CHINESE_RUN.findall(text or ''))


def clip(text, n=160):
    text = text if isinstance(text, str) else str(text)
    return text if len(text) <= n else text[:n] + '…'


def inside(child, parent):
    try:
        Path(child).resolve().relative_to(Path(parent).resolve())
        return True
    except ValueError:
        return False


def kind_of(path):
    s = path.suffix.lower()
    if s in IMAGE_SUFFIXES:
        return 'image'
    if s == '.meta':
        return 'meta'
    if s in SCRIPT_SUFFIXES:
        return 'script'
    if s in SERIAL_SUFFIXES:
        return 'serialized'
    if s == '.atlas':
        return 'spine_atlas'
    if s == '.plist':
        return 'plist'
    if s == '.fnt':
        return 'bmfont'
    if s in TEXT_SUFFIXES:
        return 'text'
    if s in AUDIO_SUFFIXES:
        return 'audio'
    if s in FONT_SUFFIXES:
        return 'font'
    return 'binary'


def walk_files(root):
    root = Path(root)
    for p in sorted(root.rglob('*')):
        rel = p.relative_to(root)
        if p.name in SKIP_NAMES or SKIP_DIRS & set(rel.parts[:-1]):
            continue
        if p.is_file():
            yield p


def source_files(project):
    """{rel posix path: Path}: every file under assets/ plus text files under build-templates/."""
    project = Path(project)
    out = {}
    for p in walk_files(project / 'assets'):
        out[p.relative_to(project).as_posix()] = p
    bt = project / 'build-templates'
    if bt.is_dir():
        for p in walk_files(bt):
            if kind_of(p) in ('script', 'serialized', 'text', 'plist', 'meta'):
                out[p.relative_to(project).as_posix()] = p
    return out


def manifest_of(files):
    rows = {rel: {'sha256': sha_file(p), 'kind': kind_of(p), 'size': p.stat().st_size} for rel, p in files.items()}
    return {'files': rows, 'sha256': sha_json({k: v['sha256'] for k, v in rows.items()})}


def export_manifest(export):
    export = Path(export)
    rows = {p.relative_to(export).as_posix(): sha_file(p) for p in walk_files_all(export)}
    return {'files': rows, 'sha256': sha_json(rows)}


def walk_files_all(root):
    """Every file except .DS_Store-like litter (exports keep no editor caches)."""
    for p in sorted(Path(root).rglob('*')):
        if p.is_file() and p.name not in SKIP_NAMES:
            yield p


# ---------------------------------------------------------------- text findings
# Each finding: file, where (line N or JSON field path), text, decoded text, category, displayed yes/maybe/no,
# reason, scan = needs_review (a person must conclude) or auto_pass (kept in the record with the reason).

AUTO = {
    'script_comment': '代码注释，玩家看不到',
    'console_log': '开发日志（console.* / cc.log/warn/error 的参数），玩家看不到',
    'node_name': '节点名或资源名（_name / name），玩家看不到',
    'spine_editor_path': 'Spine 导出时记下的编辑器路径（skeleton/images、skeleton/audio），游戏不显示',
    'spine_internal': 'Spine/龙骨骨架里的内部名字（骨骼、插槽、附件、动画名），游戏不显示',
    'meta': '.meta 是编辑器导入设置，不进游戏画面',
    'atlas_name': '图集描述里的切片名/纹理页名，游戏不显示',
    'path_name': '文件路径里的汉字，游戏不显示（被脚本按路径加载时，脚本字符串会另列一条）',
    'serial_internal': '序列化内部字段（__type__、uuid 等），游戏不显示',
    'script_regex': '正则表达式里的汉字（用来匹配文字），本身不显示',
    'editor_label': '编辑器属性面板里的说明（@property / properties 的 tooltip、displayName），游戏不显示',
}
NEEDS = {
    'label': ('yes', 'Label/RichText/EditBox 的文字，会显示'),
    'serial_field': ('maybe', '组件属性里的文字，可能显示'),
    'script_string': ('maybe', '脚本字符串，可能显示'),
    'script_code': ('maybe', '脚本里不在字符串和注释里的汉字（比如中文变量名），要确认'),
    'config_value': ('maybe', '配置里的值，可能显示'),
    'config_key': ('maybe', '配置里的键名，可能被当成文字显示'),
    'text_line': ('maybe', '文本文件里的文字，可能显示'),
    'bmfont_glyph': ('yes', '位图字体里有汉字字形，说明游戏会用它显示中文'),
    'unreadable': ('maybe', '文件读不了（编码不对或解析失败），没法确认里面有没有中文'),
}
LABEL_FIELDS = {'_string', '_N$string', 'string', '_N$placeholder', '_placeholder', 'placeholder', '_N$text',
                '_text', 'text', '_N$textLabel'}
NAME_FIELDS = {'_name', 'name', '_N$name'}
SERIAL_INTERNAL = {'__type__', '__id__', '__uuid__', '_id', '__expectedType__', '_rawFiles', '_native'}
SPINE_INTERNAL_FIELDS = {'name', 'bone', 'parent', 'slot', 'attachment', 'skin', 'path', 'target', 'bones', 'ik',
                         'transform'}


def _finding(rel, file_sha, category, text, where, line=None, field=None, decoded=None):
    if category in AUTO:
        scan, displayed, reason = 'auto_pass', 'no', AUTO[category]
    else:
        displayed, reason = NEEDS[category]
        scan = 'needs_review'
    value = decoded if decoded is not None else text
    return {'kind': 'text', 'file': rel, 'file_sha256': file_sha, 'category': category, 'where': where,
            'line': line, 'field': field, 'text': clip(text, 200), 'decoded': clip(value, 200),
            'chinese': clip(chinese_runs(value), 80), 'decoded_escapes': decoded is not None and decoded != text,
            'displayed': displayed, 'reason': reason, 'scan': scan}


def _number_findings(rows):
    """Stable ids: file + category + text + n-th occurrence (line moves do not break a review)."""
    seen = {}
    for r in rows:
        key = (r['file'], r['category'], r['decoded'])
        n = seen.get(key, 0)
        seen[key] = n + 1
        r['identity_sha256'] = sha_bytes('\0'.join([r['file'], r['category'], r['decoded'], str(n)]).encode('utf-8'))
        r['id'] = 'tx-' + r['identity_sha256'][:10]
    return rows


def read_text(path):
    data = Path(path).read_bytes()
    if data.startswith((b'\xff\xfe', b'\xfe\xff')):
        return data.decode('utf-16')
    return data.decode('utf-8-sig')


REGEX_BEFORE = set('(,=:[!&|?{};+-*%<>~^')
REGEX_WORDS = {'return', 'typeof', 'case', 'do', 'else', 'in', 'of', 'new', 'delete', 'void', 'throw', 'instanceof',
               'yield', 'await'}


def js_pieces(src):
    """Yield (kind, start, end, inner text, in_log_call) for strings, templates and comments of JS/TS source."""
    i, n = 0, len(src)
    stack = []                   # callee name for each open '('
    last = ''                    # last significant char
    word = ''                    # last identifier
    while i < n:
        c = src[i]
        if c in ' \t\r\n':
            i += 1
            continue
        if c == '/' and i + 1 < n and src[i + 1] == '/':
            j = src.find('\n', i)
            j = n if j < 0 else j
            yield 'comment', i, j, src[i + 2:j], False
            i = j
            continue
        if c == '/' and i + 1 < n and src[i + 1] == '*':
            j = src.find('*/', i + 2)
            j = n if j < 0 else j + 2
            yield 'comment', i, j, src[i + 2:j - 2], False
            i = j
            continue
        if c in '"\'':
            j = i + 1
            while j < n and src[j] != c and src[j] != '\n':
                j += 2 if src[j] == '\\' else 1
            yield 'string', i, j + 1, src[i + 1:j], any(LOG_CALL.match(s or '') for s in stack)
            i, last, word = j + 1, '"', ''
            continue
        if c == '`':
            j, depth = i + 1, 0
            while j < n:
                ch = src[j]
                if ch == '\\':
                    j += 2
                    continue
                if depth == 0 and ch == '`':
                    break
                if ch == '$' and j + 1 < n and src[j + 1] == '{':
                    depth += 1
                    j += 2
                    continue
                if depth and ch == '{':
                    depth += 1
                elif depth and ch == '}':
                    depth -= 1
                j += 1
            yield 'string', i, j + 1, src[i + 1:j], any(LOG_CALL.match(s or '') for s in stack)
            i, last, word = j + 1, '"', ''
            continue
        if c == '/' and (last == '' or last in REGEX_BEFORE or (last == 'w' and word in REGEX_WORDS)):
            j, in_class = i + 1, False
            while j < n and src[j] != '\n':
                ch = src[j]
                if ch == '\\':
                    j += 2
                    continue
                if ch == '[':
                    in_class = True
                elif ch == ']':
                    in_class = False
                elif ch == '/' and not in_class:
                    break
                j += 1
            yield 'regex', i, j + 1, src[i + 1:j], False
            i, last, word = j + 1, ')', ''
            continue
        if c.isalnum() or c in '_$' or ord(c) > 127:
            j = i
            while j < n and (src[j].isalnum() or src[j] in '_$' or ord(src[j]) > 127):
                j += 1
            word = src[i:j]
            if has_chinese(word):
                yield 'code', i, j, word, False
            i, last = j, 'w'
            continue
        if c == '(':
            k = i - 1
            while k >= 0 and src[k] in ' \t':
                k -= 1
            e = k + 1
            while k >= 0 and (src[k].isalnum() or src[k] in '_$.'):
                k -= 1
            stack.append(src[k + 1:e])
        elif c == ')' and stack:
            stack.pop()
        last = c
        i += 1


def scan_script(rel, path, file_sha):
    src = read_text(path)
    if not (CHINESE.search(src) or MAYBE_ESCAPED.search(src)):
        return []
    starts = [0] + [m.end() for m in re.finditer('\n', src)]
    rows = []
    for kind, a, _b, inner, in_log in js_pieces(src):
        value = decode_escapes(inner) if kind in ('string', 'regex') else inner
        if not has_chinese(value):
            continue
        line = bisect.bisect_right(starts, a)
        category = {'comment': 'script_comment', 'code': 'script_code', 'regex': 'script_regex'}.get(kind)
        if category is None:
            category = 'console_log' if in_log else 'script_string'
            if category == 'script_string' and EDITOR_LABEL.search(src[max(0, a - 48):a]):
                category = 'editor_label'       # @property({tooltip: '摇杆背景节点'}): only the editor shows it
        rows.append(_finding(rel, file_sha, category, inner.strip(), 'line %d' % line, line=line,
                             decoded=value.strip() if value != inner else None))
    return rows


def _is_serialized(doc):
    if isinstance(doc, dict):
        return '__type__' in doc
    return isinstance(doc, list) and bool(doc) and all(isinstance(x, dict) and '__type__' in x for x in doc[:5])


def _is_spine(doc):
    return isinstance(doc, dict) and isinstance(doc.get('skeleton'), dict) and ('bones' in doc or 'slots' in doc)


def _is_dragonbones(doc):
    return isinstance(doc, dict) and ('armature' in doc or 'SubTexture' in doc) and (
        'frameRate' in doc or 'SubTexture' in doc or 'version' in doc)


def _walk_json(node, path=''):
    if isinstance(node, dict):
        for k, v in node.items():
            p = '%s/%s' % (path, k) if path else str(k)
            yield 'key', p, str(k)
            for row in _walk_json(v, p):
                yield row
    elif isinstance(node, list):
        for i, v in enumerate(node):
            for row in _walk_json(v, '%s[%d]' % (path, i)):
                yield row
    elif isinstance(node, str):
        yield 'value', path, node


def _leaf(path):
    leaf = re.sub(r'\[\d+\]$', '', path).rsplit('/', 1)[-1]
    return re.sub(r'\[\d+\]', '', leaf)


def scan_json(rel, path, file_sha):
    raw = read_text(path)
    if not (CHINESE.search(raw) or MAYBE_ESCAPED.search(raw)):
        return []
    try:
        doc = json.loads(raw)
    except ValueError:
        return scan_lines(rel, raw, file_sha)
    serial, spine, dragon = _is_serialized(doc), _is_spine(doc), _is_dragonbones(doc)
    rows = []
    for what, fpath, value in _walk_json(doc):
        if not has_chinese(value):
            continue
        leaf = _leaf(fpath)
        if spine and fpath in ('skeleton/images', 'skeleton/audio'):
            cat = 'spine_editor_path'
        elif (spine or dragon) and (what == 'key' or leaf in SPINE_INTERNAL_FIELDS or leaf.endswith('Name')):
            cat = 'spine_internal'
        elif serial and leaf in SERIAL_INTERNAL:
            cat = 'serial_internal'
        elif serial and what == 'value' and leaf in LABEL_FIELDS:
            cat = 'label'
        elif serial and leaf in NAME_FIELDS:
            cat = 'node_name'
        elif serial:
            cat = 'serial_field'
        else:
            cat = 'config_key' if what == 'key' else 'config_value'
        rows.append(_finding(rel, file_sha, cat, value, fpath, field=fpath))
    return rows


def scan_lines(rel, text, file_sha, category='text_line'):
    rows = []
    for no, line in enumerate(text.splitlines(), 1):
        value = decode_escapes(line)
        if has_chinese(value):
            rows.append(_finding(rel, file_sha, category, line.strip(), 'line %d' % no, line=no,
                                 decoded=value.strip() if value != line else None))
    return rows


def text_findings(rel, path, kind, file_sha):
    rows = []
    if has_chinese(rel):
        rows.append(_finding(rel, file_sha, 'path_name', rel, 'path'))
    if kind in ('image', 'audio', 'font', 'binary', 'plist'):
        return rows      # plist names are handled with the atlas; binary files have no text to read here
    try:
        if kind == 'meta':
            text = read_text(path)
            rows += [dict(r) for r in scan_lines(rel, text, file_sha, 'meta')]
        elif kind == 'script':
            rows += scan_script(rel, path, file_sha)
        elif kind == 'serialized':
            rows += scan_json(rel, path, file_sha)
        elif kind == 'spine_atlas':
            rows += scan_lines(rel, read_text(path), file_sha, 'atlas_name')
        elif kind == 'bmfont':
            pass     # glyphs are listed by the atlas reader
        else:
            rows += scan_lines(rel, read_text(path), file_sha)
    except (UnicodeError, OSError) as exc:
        rows.append(_finding(rel, file_sha, 'unreadable', '读不了：%s' % exc, 'file'))
    return rows


# ---------------------------------------------------------------- atlas readers
# A region: {'name', 'page' (file name as written), 'x','y','w','h' (unrotated size), 'rotate' (0/90/180/270),
#            'orig': [w,h] or None, 'offset': [x,y] or None, 'index'}; area in the page is w×h, or h×w when rotated 90/270.

def _ints(value):
    return [int(round(float(v))) for v in re.split(r'[,\s]+', value.strip()) if v != '']


def parse_spine_atlas(text):
    """Spine / libGDX .atlas, old (xy/size/orig/offset, rotate true|false|90) and 4.x (bounds/offsets, rotate: 90)
    layouts, any number of pages. Returns (pages, regions)."""
    pages, regions = [], []
    page, region = None, None
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    for raw in lines:
        line = raw.strip()
        if not line:
            page, region = None, None
            continue
        if page is None:
            page = {'file': line, 'size': None}
            pages.append(page)
            continue
        if ':' in line:
            key, value = [x.strip() for x in line.split(':', 1)]
            target = region if region is not None else page
            if target is page:
                if key == 'size':
                    page['size'] = _ints(value)[:2]
                else:
                    page[key] = value
                continue
            if key == 'rotate':
                v = value.lower()
                region['rotate'] = 90 if v == 'true' else 0 if v == 'false' else int(float(v)) % 360
            elif key == 'xy':
                region['x'], region['y'] = _ints(value)[:2]
            elif key == 'size':
                region['w'], region['h'] = _ints(value)[:2]
            elif key == 'bounds':
                region['x'], region['y'], region['w'], region['h'] = _ints(value)[:4]
            elif key == 'orig':
                region['orig'] = _ints(value)[:2]
            elif key == 'offset':
                region['offset'] = _ints(value)[:2]
            elif key == 'offsets':
                v = _ints(value)
                region['offset'], region['orig'] = v[:2], v[2:4]
            elif key == 'index':
                region['index'] = int(float(value))
            else:
                region.setdefault('extra', {})[key] = value
            continue
        region = {'name': line, 'page': page['file'], 'rotate': 0, 'orig': None, 'offset': None, 'index': -1}
        regions.append(region)
    boxes = {}
    for r in regions:
        if not all(k in r for k in ('x', 'y', 'w', 'h')):
            raise ValueError('切片 %s 缺坐标或尺寸' % r['name'])
        if r['rotate'] not in (0, 90, 180, 270):
            raise ValueError('unsupported Spine rotation for %s: %s' % (r['name'], r['rotate']))
        w, h = (r['h'], r['w']) if r['rotate'] in (90, 270) else (r['w'], r['h'])
        x, y = r['x'], r['y']
        boxes.setdefault(r['page'], {})[(x, y, x + w, y + h)] = r['name']
    for page, page_boxes in boxes.items():
        active = []
        for (x, y, right, bottom), name in sorted(page_boxes.items()):
            active = [row for row in active if row[0] > x]
            for _, top, end, other in active:
                if y < end and top < bottom:
                    raise ValueError('Spine page %s has partially overlapping slices: %s and %s' % (page, other, name))
            active.append((right, y, bottom, name))
    return pages, regions


def _pts(value):
    """'{{1,2},{3,4}}' / '{1,2}' -> flat int list."""
    return [int(round(float(v))) for v in re.findall(r'-?\d+(?:\.\d+)?', str(value))]


def parse_plist_atlas(data):
    """TexturePacker cocos2d plist, formats 0..3. Returns (pages, regions) or None when it is not a sprite atlas."""
    doc = plistlib.loads(data)
    if not isinstance(doc, dict) or not isinstance(doc.get('frames'), dict):
        return None
    meta = doc.get('metadata') or {}
    fmt = int(meta.get('format', 0) or 0)
    tex = meta.get('realTextureFileName') or meta.get('textureFileName')
    pages = [{'file': tex, 'size': _pts(meta.get('size'))[:2] if meta.get('size') else None}]
    regions = []
    for name, f in sorted(doc['frames'].items()):
        if not isinstance(f, dict):
            continue
        r = {'name': name, 'page': tex, 'rotate': 0, 'orig': None, 'offset': None, 'index': -1, 'format': fmt}
        if fmt == 0 or ('x' in f and 'width' in f):
            r['x'], r['y'], r['w'], r['h'] = int(f['x']), int(f['y']), int(f['width']), int(f['height'])
            r['offset'] = [int(round(float(f.get('offsetX', 0)))), int(round(float(f.get('offsetY', 0))))]
            if 'originalWidth' in f:
                r['orig'] = [abs(int(f['originalWidth'])), abs(int(f.get('originalHeight', 0)))]
        else:
            rect = _pts(f.get('textureRect') or f.get('frame'))
            if len(rect) < 4:
                raise ValueError('切片 %s 没有 frame/textureRect' % name)
            r['x'], r['y'], r['w'], r['h'] = rect[:4]
            if f.get('textureRotated') or f.get('rotated'):
                r['rotate'] = 270   # TexturePacker turns the picture 90° clockwise; both directions are read anyway
            off = f.get('spriteOffset') or f.get('offset')
            r['offset'] = _pts(off)[:2] if off else None
            src = f.get('spriteSourceSize') or f.get('sourceSize')
            r['orig'] = _pts(src)[:2] if src else None
            if f.get('sourceColorRect'):
                r['source_color_rect'] = _pts(f['sourceColorRect'])[:4]
        regions.append(r)
    return pages, regions


def parse_dragonbones_tex(doc):
    if not (isinstance(doc, dict) and isinstance(doc.get('SubTexture'), list)):
        return None
    tex = doc.get('imagePath') or (doc.get('name', '') + '.png')
    pages = [{'file': tex, 'size': [doc['width'], doc['height']] if 'width' in doc and 'height' in doc else None}]
    regions = []
    for s in doc['SubTexture']:
        r = {'name': s.get('name', ''), 'page': tex, 'x': int(s.get('x', 0)), 'y': int(s.get('y', 0)),
             'w': int(s.get('width', 0)), 'h': int(s.get('height', 0)), 'index': -1,
             'rotate': 90 if s.get('rotated') else 0,
             'orig': [int(s['frameWidth']), int(s['frameHeight'])] if 'frameWidth' in s else None,
             'offset': [int(s.get('frameX', 0)), int(s.get('frameY', 0))] if 'frameX' in s else None}
        if r['rotate']:
            r['w'], r['h'] = r['h'], r['w']     # DragonBones lists the area as stored; keep w/h unrotated
        regions.append(r)
    return pages, regions


def parse_bmfont(text):
    """BMFont .fnt, text or XML. Returns (pages, glyph ids)."""
    pages, glyphs = [], []
    if text.lstrip().startswith('<'):
        root = ET.fromstring(text)
        for p in root.iter('page'):
            pages.append({'file': p.get('file'), 'id': p.get('id')})
        glyphs = [int(c.get('id')) for c in root.iter('char') if c.get('id') is not None]
        return pages, glyphs
    for line in text.splitlines():
        tag = line.split(' ', 1)[0]
        attrs = dict(re.findall(r'(\w+)=("[^"]*"|\S+)', line))
        if tag == 'page':
            pages.append({'file': attrs.get('file', '').strip('"'), 'id': attrs.get('id')})
        elif tag == 'char' and 'id' in attrs:
            glyphs.append(int(attrs['id']))
    return pages, glyphs


def read_atlas(rel, path):
    """(format, pages, regions) for an atlas description file, or None when the file is not one."""
    kind = kind_of(path)
    if kind == 'spine_atlas':
        pages, regions = parse_spine_atlas(read_text(path))
        return 'spine_atlas', pages, regions
    if kind == 'plist':
        got = parse_plist_atlas(Path(path).read_bytes())
        return ('cocos_plist',) + got if got else None
    if kind == 'serialized' and path.name.endswith(('_tex.json', 'tex.json')):
        got = parse_dragonbones_tex(json.loads(read_text(path)))
        return ('dragonbones_tex',) + got if got else None
    return None


# ---------------------------------------------------------------- pixels and slices

def _pil():
    try:
        from PIL import Image
    except ImportError:
        raise Usage('缺少 Pillow（Python 图片库）。先装：python3 -m pip install Pillow')
    return Image


def _transpose(img, name):
    Image = _pil()
    enum = getattr(Image, 'Transpose', Image)
    return img.transpose(getattr(enum, name))


def pixels_sha256(img):
    """SHA-256 of the RGBA bytes plus the size: the identity of what was looked at."""
    img = img if img.mode == 'RGBA' else img.convert('RGBA')
    return sha_bytes(('RGBA %dx%d\n' % img.size).encode('ascii') + img.tobytes())


def open_rgba(path):
    Image = _pil()
    with Image.open(path) as im:
        im.load()
        return im.convert('RGBA')


def cut_region(page, r):
    """Cut a region from a page image and turn it back upright. Raises ValueError when it does not fit."""
    rot = r.get('rotate', 0) % 360
    aw, ah = (r['h'], r['w']) if rot in (90, 270) else (r['w'], r['h'])
    x, y = r['x'], r['y']
    if aw <= 0 or ah <= 0:
        raise ValueError('切片 %s 尺寸是 0' % r['name'])
    if x < 0 or y < 0 or x + aw > page.size[0] or y + ah > page.size[1]:
        raise ValueError('切片 %s 的范围 (%d,%d %dx%d) 超出纹理页 %dx%d' % (r['name'], x, y, aw, ah, page.size[0], page.size[1]))
    img = page.crop((x, y, x + aw, y + ah))
    if rot == 90:        # libGDX/Spine store the picture turned 90° counter-clockwise
        img = _transpose(img, 'ROTATE_270')
    elif rot == 270:     # TexturePacker cocos2d turns it 90° clockwise
        img = _transpose(img, 'ROTATE_90')
    elif rot == 180:
        img = _transpose(img, 'ROTATE_180')
    return img


def _resolve_page(atlas_path, page_file, project):
    if not page_file:
        return None
    cand = (atlas_path.parent / page_file)
    if cand.is_file():
        return cand
    alt = atlas_path.parent / Path(page_file).name
    if alt.is_file():
        return alt
    stem = atlas_path.with_suffix('.png')
    return stem if stem.is_file() and Path(page_file).suffix == '' else None


def current_state(project, export=None, slice_dir=None, on_pixels=None, spine_pages=None):
    """Recompute everything that can be computed without a recognizer: manifests, text findings, atlases, every
    picture and slice with its pixel SHA. on_pixels(item, image) is called for every picture/slice/unmatched export
    picture so scan can prepare recognizer input without holding all pictures in memory."""
    project = Path(project)
    if not (project / 'assets').is_dir():
        raise Usage('不是 Cocos 工程（没有 assets/）：%s' % project)
    core_scripts = HERE.parents[1] / 'remake-core' / 'scripts'
    if str(core_scripts) not in sys.path:
        sys.path.insert(0, str(core_scripts))
    import spine_atlas_binding as spine

    files = source_files(project)
    manifest = manifest_of(files)
    texts, items, atlases = [], [], []
    for rel, p in files.items():
        texts.extend(text_findings(rel, p, kind_of(p), manifest['files'][rel]['sha256']))

    # whole pictures
    for rel, p in files.items():
        if kind_of(p) != 'image':
            continue
        item = {'id': short_id('img', rel), 'kind': 'image', 'file': rel, 'file_sha256': manifest['files'][rel]['sha256'],
                'rotate': 0}
        try:
            img = open_rgba(p)
            item['size'] = list(img.size)
            item['pixels_sha256'] = pixels_sha256(img)
            if on_pixels:
                on_pixels(item, img)
            del img
        except Exception as exc:      # noqa: BLE001 - any decoder error is a finding, not a crash
            item['error'] = '图片打不开：%s' % clip(str(exc), 200)
        items.append(item)

    # atlases: Spine/libGDX .atlas, cocos .plist, DragonBones *_tex.json, BMFont .fnt
    for rel, p in files.items():
        kind = kind_of(p)
        if kind == 'bmfont':
            _bmfont(rel, p, manifest, files, project, texts, atlases)
            continue
        if kind not in ('spine_atlas', 'plist', 'serialized'):
            continue
        entry = {'file': rel, 'sha256': manifest['files'][rel]['sha256'], 'format': None, 'pages': [], 'regions': 0}
        try:
            got = read_atlas(rel, p)
        except Exception as exc:      # noqa: BLE001
            if kind == 'serialized':
                continue
            entry['error'] = '图集描述读不了：%s' % clip(str(exc), 200)
            atlases.append(entry)
            items.append({'id': short_id('atl', rel), 'kind': 'atlas_error', 'file': rel, 'error': entry['error'],
                          'binding_error': kind == 'spine_atlas'})
            continue
        if got is None:
            if kind == 'plist':
                texts.extend(scan_lines(rel, read_text_safe(p), entry['sha256']))
            continue
        fmt, pages, regions = got
        entry['format'], entry['regions'] = fmt, len(regions)
        bound_pages = None
        if fmt == 'spine_atlas':
            try:
                if spine_pages is None:
                    bound_pages = spine.resolve_source(files, rel, [page['file'] for page in pages])
                else:
                    bound_pages = spine_pages[rel]
                if {page['file'] for page in pages} != {region['page'] for region in regions} or not regions:
                    raise ValueError('Spine atlas has a page with no slices')
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                entry['error'] = 'Spine texture binding unresolved: %s' % clip(str(exc), 300)
                atlases.append(entry)
                items.append({'id': short_id('atl', rel), 'kind': 'atlas_error', 'file': rel,
                              'binding_error': True, 'error': entry['error']})
                continue
        page_imgs = {}
        for pg in pages:
            name = pg.get('file')
            pp = files.get(bound_pages.get(name)) if bound_pages is not None else _resolve_page(p, name, project)
            row = {'name': pg.get('file'), 'file': None, 'sha256': None}
            if pp is not None and inside(pp, project):
                row['file'] = pp.relative_to(project).as_posix()
                row['sha256'] = sha_file(pp)
                try:
                    page_imgs[pg.get('file')] = (pp, open_rgba(pp))
                except Exception as exc:      # noqa: BLE001
                    row['error'] = '纹理页打不开：%s' % clip(str(exc), 200)
            else:
                row['error'] = '找不到纹理页 %s' % pg.get('file')
            entry['pages'].append(row)
        page_rows = {r['name']: r for r in entry['pages']}
        for r in regions:
            if fmt != 'spine_atlas' and has_chinese(r['name']):    # .atlas lines are read as text already
                texts.append(_finding(rel, entry['sha256'], 'atlas_name', r['name'], 'region %s' % r['name']))
        counts = {}
        for r in regions:
            ident = (r['page'], r['name'], r.get('index', -1))
            counts[ident] = counts.get(ident, 0) + 1
            sid = short_id('sl', rel, str(r['page']), r['name'], str(r.get('index', -1)), str(counts[ident]))
            pg = page_rows.get(r['page'], {})
            item = {'id': sid, 'kind': 'slice', 'file': pg.get('file'), 'file_sha256': pg.get('sha256'),
                    'atlas_file': rel, 'atlas_sha256': entry['sha256'], 'atlas_format': fmt, 'slice': r['name'],
                    'region': {k: r.get(k) for k in ('x', 'y', 'w', 'h', 'rotate', 'orig', 'offset', 'index')},
                    'rotate': r.get('rotate', 0) % 360}
            if r['page'] not in page_imgs:
                item['error'] = pg.get('error') or '找不到纹理页 %s' % r['page']
                if fmt == 'spine_atlas':
                    item['binding_error'] = True
                items.append(item)
                continue
            try:
                img = cut_region(page_imgs[r['page']][1], r)
            except ValueError as exc:
                item['error'] = str(exc)
                if fmt == 'spine_atlas':
                    item['binding_error'] = True
                items.append(item)
                continue
            item['size'] = list(img.size)
            item['pixels_sha256'] = pixels_sha256(img)
            if slice_dir is not None:
                target = Path(slice_dir) / (item['pixels_sha256'] + '.png')
                if not target.is_file():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    img.save(str(target), format='PNG')
                item['slice_file'] = 'slices/%s.png' % item['pixels_sha256']
            if on_pixels:
                on_pixels(item, img)
            items.append(item)
        page_imgs.clear()
        atlases.append(entry)

    _number_findings(texts)
    for t in texts:
        items.append(t)
    ids = [i['id'] for i in items]
    if len(ids) != len(set(ids)):
        dup = sorted({x for x in ids if ids.count(x) > 1})
        raise Usage('编号重复（%s），把这款工程报给 Skill 维护者' % ', '.join(dup[:5]))
    state = {'manifest': manifest, 'atlases': atlases, 'items': items, 'export': None}
    if export is not None:
        state['export'] = export_state(project, export, items, on_pixels)
        items.extend(state['export'].pop('items'))
    return state


def read_text_safe(p):
    try:
        return read_text(p)
    except (UnicodeError, OSError):
        return ''


def _bmfont(rel, p, manifest, files, project, texts, atlases):
    sha = manifest['files'][rel]['sha256']
    entry = {'file': rel, 'sha256': sha, 'format': 'bmfont', 'pages': [], 'regions': 0}
    try:
        pages, glyphs = parse_bmfont(read_text(p))
    except Exception as exc:      # noqa: BLE001
        texts.append(_finding(rel, sha, 'unreadable', '位图字体读不了：%s' % exc, 'file'))
        atlases.append(dict(entry, error=str(exc)))
        return
    entry['regions'] = len(glyphs)
    for pg in pages:
        pp = _resolve_page(p, pg.get('file'), project)
        entry['pages'].append({'name': pg.get('file'), 'file': pp.relative_to(project).as_posix() if pp and inside(pp, project) else None})
    han = ''.join(chr(g) for g in glyphs if 0 < g <= 0x10FFFF and has_chinese(chr(g)))
    if han:
        texts.append(_finding(rel, sha, 'bmfont_glyph', han, 'chars'))
    atlases.append(entry)


def export_state(project, export, items, on_pixels):
    export = Path(export)
    if not export.is_dir():
        raise Usage('找不到导出目录：%s' % export)
    man = export_manifest(export)
    by_file_sha = {}
    for it in items:
        if it['kind'] == 'image':
            by_file_sha.setdefault(it['file_sha256'], []).append(it['id'])
    out_items, matched, own = [], 0, 0
    for rel, digest in man['files'].items():
        if Path(rel).suffix.lower() not in IMAGE_SUFFIXES:
            continue
        item = {'id': short_id('ex', rel), 'kind': 'export_image', 'file': rel, 'file_sha256': digest, 'rotate': 0}
        if digest in by_file_sha:
            item['same_as'] = by_file_sha[digest]
            matched += 1
        else:
            own += 1
            try:
                img = open_rgba(export / rel)
                item['size'] = list(img.size)
                item['pixels_sha256'] = pixels_sha256(img)
                if on_pixels:
                    on_pixels(item, img)
                del img
            except Exception as exc:      # noqa: BLE001
                item['error'] = '导出图打不开：%s' % clip(str(exc), 200)
        out_items.append(item)
    return {'dir': str(export.resolve()), 'manifest': man, 'images': matched + own, 'matched_source': matched,
            'own_scan': own, 'items': out_items}


EXPORT_SKEW_S = 2.0   # file-system timestamp slack


def source_newer_than_export(project, export):
    """11.17 R4Q7: assets/ files (not .meta) changed after the newest file of the export, i.e. the export was built from
    an older source (奔跑吧巨人: homePanel.prefab and EnglishPlatform.ts edited for build 8, checked with export 7).
    Fingerprint = modification time: a Cocos export does not record which source it came from."""
    try:
        built = max(p.stat().st_mtime for p in walk_files_all(Path(export)))
    except ValueError:
        return []
    assets = Path(project) / 'assets'
    if not assets.is_dir():
        return []
    out = []
    for p in walk_files_all(assets):
        if p.suffix.lower() == '.meta':
            continue
        if p.stat().st_mtime > built + EXPORT_SKEW_S:
            out.append(p.relative_to(project).as_posix())
    return sorted(out)


# ---------------------------------------------------------------- recognizers

def cache_dir():
    if sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Caches'
    elif os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / 'AppData' / 'Local'))
    else:
        base = Path(os.environ.get('XDG_CACHE_HOME') or (Path.home() / '.cache'))
    return Path(base) / 'cocos-english-skill'


def ocr_jobs():
    try:
        return max(1, int(os.environ.get('CHINESE_AUDIT_OCR_JOBS', '0'))) if os.environ.get('CHINESE_AUDIT_OCR_JOBS') \
            else max(1, min(4, (os.cpu_count() or 2) // 2))
    except ValueError:
        return 1


def prepare_ocr_input(img, both_ways):
    """Recognizer input: upright (and, for slices stored turned, also upside down), enlarged when the short side is
    under 64 px, and pictures with transparency shown on black AND on white (white text vanishes on white)."""
    Image = _pil()
    variants = [('upright', img)]
    if both_ways:
        variants.append(('turned_180', _transpose(img, 'ROTATE_180')))
    w, h = img.size
    scale = 1
    if min(w, h) < MIN_OCR_SIDE:
        scale = int(math.ceil(MIN_OCR_SIDE / float(max(1, min(w, h)))))
        scale = max(1, min(scale, MAX_OCR_SIDE // max(1, max(w, h))))
    resample = getattr(getattr(Image, 'Resampling', Image), 'LANCZOS')
    alpha = img.getextrema()[3][0] < 255 if img.mode == 'RGBA' else False
    backgrounds = [(0, 0, 0), (255, 255, 255)] if alpha else [None]
    panels = []
    for _name, v in variants:
        if scale > 1:
            v = v.resize((v.size[0] * scale, v.size[1] * scale), resample)
        for bg in backgrounds:
            if bg is None:
                panels.append(v.convert('RGB'))
            else:
                base = Image.new('RGBA', v.size, bg + (255,))
                base.alpha_composite(v)
                panels.append(base.convert('RGB'))
    gap = 8
    width = max(p.size[0] for p in panels)
    height = sum(p.size[1] for p in panels) + gap * (len(panels) - 1)
    sheet = Image.new('RGB', (width, height), (128, 128, 128))
    y = 0
    for p in panels:
        sheet.paste(p, (0, y))
        y += p.size[1] + gap
    info = {'variants': [n for n, _ in variants], 'backgrounds': ['black', 'white'] if alpha else ['as_is'],
            'scale': scale, 'size': [width, height]}
    return sheet, info


class Recognizer(object):
    name = 'none'
    languages = []
    version = 'none'
    note = ''

    def available(self):
        return True

    def run(self, tasks):
        """tasks: [{'key', 'path', 'pixels_sha256'}] -> {key: {'ok', 'error', 'items': [{text, confidence, box}], 'raw'}}"""
        raise NotImplementedError


class NoRecognizer(Recognizer):
    name, version = 'none', 'none'
    note = '没有用识别器：每张图、每个切片都要人工复核'


class FakeRecognizer(Recognizer):
    """Tests only. CHINESE_AUDIT_FAKE_OCR = JSON {pixels_sha256: "text" | "fail" | ["t1", ...] | [{"text","confidence"}]}
    (or @<file>). Unlisted pictures read as no text."""
    name, version, languages = 'fake', 'fake-1', ['zh-Hans', 'en-US']
    note = '测试用假识别器'

    def __init__(self):
        raw = os.environ.get(ENV_FAKE, '{}')
        if raw.startswith('@'):
            raw = Path(raw[1:]).read_text(encoding='utf-8')
        self.table = json.loads(raw or '{}')
        self.calls = 0

    def run(self, tasks):
        out = {}
        for t in tasks:
            self.calls += 1
            v = self.table.get(t['pixels_sha256'])
            if v == 'fail':
                out[t['key']] = {'ok': False, 'error': 'fake failure', 'items': [], 'raw': 'fail'}
                continue
            if v is None:
                v = []
            if isinstance(v, str):
                v = [v]
            items = [x if isinstance(x, dict) else {'text': x, 'confidence': 1.0} for x in v]
            out[t['key']] = {'ok': True, 'error': None, 'items': items, 'raw': v}
        return out


def _chunks(seq, n):
    return [seq[i:i + n] for i in range(0, len(seq), n)]


def _run_parallel(func, chunks):
    from concurrent.futures import ThreadPoolExecutor
    out = {}
    with ThreadPoolExecutor(max_workers=ocr_jobs()) as pool:
        for part in pool.map(func, chunks):
            out.update(part)
    return out


class VisionRecognizer(Recognizer):
    name, languages = 'vision', ['zh-Hans', 'zh-Hant', 'en-US']
    script = HERE / 'ocr_vision.swift'

    def __init__(self):
        self.script_sha = sha_file(self.script) if self.script.is_file() else 'missing'
        self.version = 'macOS %s; ocr_vision.swift %s' % (platform.mac_ver()[0] or '?', self.script_sha[:12])
        self.command, self.note = None, ''

    def available(self):
        if sys.platform != 'darwin':
            self.note = '不是 macOS'
            return False
        if not self.script.is_file():
            self.note = '找不到 ocr_vision.swift'
            return False
        binary = cache_dir() / ('ocr_vision-%s' % self.script_sha[:16])
        if binary.is_file() and os.access(str(binary), os.X_OK):
            self.command = [str(binary)]
            return True
        swiftc = shutil.which('swiftc')
        if swiftc:
            try:
                binary.parent.mkdir(parents=True, exist_ok=True)
                tmp = binary.with_name(binary.name + '.%d.tmp' % os.getpid())
                r = subprocess.run([swiftc, '-O', str(self.script), '-o', str(tmp)], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, timeout=600)
                if r.returncode == 0 and tmp.is_file():
                    os.replace(str(tmp), str(binary))
                    self.command = [str(binary)]
                    return True
                self.note = 'swiftc 编译失败，改用 swift 直接跑：%s' % clip(r.stderr.decode('utf-8', 'replace'), 200)
            except (OSError, subprocess.SubprocessError) as exc:
                self.note = 'swiftc 编译失败，改用 swift 直接跑：%s' % exc
        swift = shutil.which('swift')
        if swift:
            self.command = [swift, str(self.script)]
            return True
        self.note = (self.note + '；' if self.note else '') + '没有 swift/swiftc（装 Xcode 命令行工具：xcode-select --install）'
        return False

    def _one(self, chunk):
        with tempfile.TemporaryDirectory(prefix='chinese-audit-vision-') as td:
            lst, out = Path(td) / 'list.json', Path(td) / 'out.json'
            lst.write_text(json.dumps([{'id': t['key'], 'path': t['path']} for t in chunk]), encoding='utf-8')
            try:
                r = subprocess.run(self.command + [str(lst), str(out)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   timeout=180 + 10 * len(chunk))
                err = r.stderr.decode('utf-8', 'replace')
                doc = json.loads(out.read_text(encoding='utf-8')) if out.is_file() else None
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                doc, err = None, str(exc)
        res = {}
        rows = {row.get('id'): row for row in (doc or {}).get('results', [])}
        for t in chunk:
            row = rows.get(t['key'])
            if row is None:
                res[t['key']] = {'ok': False, 'error': 'Vision 没有返回结果：%s' % clip(err, 300), 'items': [], 'raw': None}
            else:
                res[t['key']] = {'ok': bool(row.get('ok')), 'error': row.get('error'), 'raw': row,
                                 'items': [{'text': i.get('text', ''), 'confidence': i.get('confidence'),
                                            'box': i.get('box')} for i in row.get('items', [])]}
        return res

    def run(self, tasks):
        return _run_parallel(self._one, _chunks(tasks, 40))


class TesseractRecognizer(Recognizer):
    name = 'tesseract'

    def __init__(self):
        self.exe = shutil.which('tesseract')
        self.version, self.note, self.languages = 'unknown', '', []

    def available(self):
        if not self.exe:
            self.note = '没有装 tesseract'
            return False
        try:
            langs = subprocess.run([self.exe, '--list-langs'], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   timeout=60).stdout.decode('utf-8', 'replace').split()
            ver = subprocess.run([self.exe, '--version'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 timeout=60).stdout.decode('utf-8', 'replace').splitlines()
        except (OSError, subprocess.SubprocessError) as exc:
            self.note = 'tesseract 跑不起来：%s' % exc
            return False
        self.version = ver[0].strip() if ver else 'unknown'
        zh = [x for x in ('chi_sim', 'chi_tra') if x in langs]
        if not zh:
            self.note = 'tesseract 没有中文语言包（chi_sim/chi_tra），认不出汉字，不能用'
            return False
        self.languages = zh + (['eng'] if 'eng' in langs else [])
        self.version += '; langs ' + '+'.join(self.languages)
        return True

    def _one(self, chunk):
        res = {}
        for t in chunk:
            try:
                r = subprocess.run([self.exe, t['path'], 'stdout', '-l', '+'.join(self.languages), '--psm', '11', 'tsv'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
                if r.returncode != 0:
                    raise OSError(r.stderr.decode('utf-8', 'replace')[:300])
                lines, items = r.stdout.decode('utf-8', 'replace').splitlines(), []
                for row in lines[1:]:
                    cols = row.split('\t')
                    if len(cols) >= 12 and cols[0] == '5' and cols[11].strip():
                        conf = float(cols[10]) / 100.0 if cols[10] not in ('', '-1') else None
                        items.append({'text': cols[11].strip(), 'confidence': conf,
                                      'box': [int(cols[6]), int(cols[7]), int(cols[8]), int(cols[9])]})
                res[t['key']] = {'ok': True, 'error': None, 'items': items, 'raw': lines[:400]}
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                res[t['key']] = {'ok': False, 'error': str(exc), 'items': [], 'raw': None}
        return res

    def run(self, tasks):
        return _run_parallel(self._one, _chunks(tasks, 10))


class WindowsRecognizer(Recognizer):
    """Windows.Media.Ocr through ocr_windows.ps1. NOT tried on a Windows machine yet (written on macOS)."""
    name = 'windows'
    script = HERE / 'ocr_windows.ps1'

    def __init__(self):
        self.exe = shutil.which('powershell') or shutil.which('powershell.exe') or shutil.which('pwsh')
        self.script_sha = sha_file(self.script) if self.script.is_file() else 'missing'
        self.version, self.note, self.languages = 'unknown', '', []

    def available(self):
        if os.name != 'nt' or not self.exe or not self.script.is_file():
            self.note = '不是 Windows，或没有 PowerShell / ocr_windows.ps1'
            return False
        try:
            r = subprocess.run([self.exe, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(self.script), '-Probe'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
            doc = json.loads(r.stdout.decode('utf-8-sig', 'replace') or '{}')
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            self.note = 'Windows OCR 跑不起来：%s' % exc
            return False
        langs = doc.get('languages') or []
        zh = [x for x in langs if str(x).lower().startswith('zh')]
        if not zh:
            self.note = 'Windows 没装中文 OCR 语言（设置 → 时间和语言 → 添加中文，含“光学字符识别”）'
            return False
        self.languages = langs
        self.version = 'Windows %s; ocr_windows.ps1 %s' % (doc.get('os') or platform.version(), self.script_sha[:12])
        return True

    def _one(self, chunk):
        with tempfile.TemporaryDirectory(prefix='chinese-audit-win-') as td:
            lst, out = Path(td) / 'list.json', Path(td) / 'out.json'
            lst.write_text(json.dumps([{'id': t['key'], 'path': t['path']} for t in chunk], ensure_ascii=False),
                           encoding='utf-8')
            try:
                r = subprocess.run([self.exe, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(self.script),
                                    '-List', str(lst), '-Out', str(out)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   timeout=180 + 10 * len(chunk))
                err = r.stderr.decode('utf-8', 'replace')
                doc = json.loads(out.read_text(encoding='utf-8-sig')) if out.is_file() else None
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                doc, err = None, str(exc)
        rows = {row.get('id'): row for row in (doc or {}).get('results', [])}
        res = {}
        for t in chunk:
            row = rows.get(t['key'])
            if row is None:
                res[t['key']] = {'ok': False, 'error': 'Windows OCR 没有返回结果：%s' % clip(err, 300), 'items': [],
                                 'raw': None}
            else:
                res[t['key']] = {'ok': bool(row.get('ok')), 'error': row.get('error'), 'raw': row,
                                 'items': [{'text': i.get('text', ''), 'confidence': i.get('confidence'),
                                            'box': i.get('box')} for i in row.get('items', [])]}
        return res

    def run(self, tasks):
        return _run_parallel(self._one, _chunks(tasks, 40))


def pick_recognizer(choice):
    notes = []
    if choice == 'fake':
        return FakeRecognizer(), notes
    if choice == 'none':
        return NoRecognizer(), notes
    order = {'vision': [VisionRecognizer], 'tesseract': [TesseractRecognizer], 'windows': [WindowsRecognizer]}.get(choice)
    if order is None:     # auto
        order = [WindowsRecognizer, TesseractRecognizer] if os.name == 'nt' else [VisionRecognizer, TesseractRecognizer]
    for cls in order:
        r = cls()
        if r.available():
            if r.note:
                notes.append('%s：%s' % (r.name, r.note))
            return r, notes
        notes.append('%s 不可用：%s' % (cls.name, r.note))
    if choice != 'auto':
        raise Usage('识别器 %s 不可用：%s' % (choice, '；'.join(notes)))
    r = NoRecognizer()
    r.note = '没有能认汉字的识别器（%s），每张图、每个切片都要人工复核' % '；'.join(notes)
    return r, notes


def receipt_key(pixels_sha, both_ways, recognizer, version):
    return sha_json([pixels_sha, bool(both_ways), recognizer, version, RULES_VERSION])[:32]


def classify(receipt):
    """(scan state, reasons, chinese hits) from a receipt; the receipt, not audit.json, is the evidence."""
    if receipt is None:
        return 'needs_review', ['没有识字回执'], []
    if receipt.get('status') != 'ok':
        return 'needs_review', ['识字失败：%s' % clip(receipt.get('error') or '?', 120)], []
    hits, low, folded = [], [], []
    for r in receipt.get('results') or []:
        text = r.get('text') or ''
        conf = r.get('confidence')
        if has_chinese(text) and not HAN_ONLY.search(text) and len(ASCII_LETTERS.findall(text)) >= 2 \
                and not has_chinese(unicodedata.normalize('NFKC', text)):
            # a Chinese-first recognizer writes "INCOMING!" as "INCOMING！"; full-width punctuation inside an
            # English word with no Han is read as the ASCII mark (Garden Guardians wave slice, 2026-11-01)
            folded.append(text)
            continue
        if has_chinese(text):
            hits.append(text)
        elif text.strip() and isinstance(conf, (int, float)) and conf < LOW_CONFIDENCE and not LATIN.match(text):
            low.append(text)
    if hits:
        return 'needs_review', ['识别出汉字或中文标点：%s' % clip('、'.join(hits), 80)], hits
    if low:
        return 'needs_review', ['低置信度、又不是英文字母：%s' % clip('、'.join(low), 80)], []
    words = [r.get('text') for r in receipt.get('results') or [] if (r.get('text') or '').strip()]
    reasons = ['只有英文：%s' % clip(' '.join(words), 80) if words else '没有识别到文字']
    if folded:
        reasons.append('英文里的全角标点按半角算：%s' % clip('、'.join(folded), 60))
    return 'auto_covered', reasons, []


# ---------------------------------------------------------------- scan

PICTURE_KINDS = ('image', 'slice', 'export_image')


def bind_sha(item):
    """What a receipt or a review is about: pixels for pictures/slices, the finding identity for text, the file for
    things that could not be read."""
    if item.get('kind') == 'text':
        return item.get('identity_sha256')
    return item.get('pixels_sha256') or item.get('file_sha256') or item.get('atlas_sha256') or sha_bytes(
        (item.get('error') or '').encode('utf-8'))


def resolve_out(project, out):
    return Path(out).resolve() if out else (Path(project) / DEFAULT_OUT).resolve()


def guard_out(out, project, *roots):
    for root in [Path(project) / 'assets'] + [r for r in roots if r]:
        if inside(out, root) or inside(root, out):
            raise Usage('结果目录 %s 不能放在 %s 里面（也不能把它包在里面），换一个 --out' % (out, root))


def _audit_paths(out):
    return {'audit': out / 'audit.json', 'reviews': out / 'reviews.json', 'ocr': out / 'ocr', 'slices': out / 'slices',
            'evidence': out / 'evidence', 'sheets': out / 'sheets', 'check': out / 'check-result.json'}


def cmd_scan(a):
    project = Path(a.project).resolve()
    if not (project / 'assets').is_dir():
        raise Usage('不是 Cocos 工程（没有 assets/）：%s' % project)
    export = Path(a.export).resolve() if a.export else None
    out = resolve_out(project, a.out)
    guard_out(out, project, export)
    paths = _audit_paths(out)
    rec, notes = pick_recognizer(a.ocr)
    use_ocr = not isinstance(rec, NoRecognizer)
    tasks, tmp = {}, tempfile.mkdtemp(prefix='chinese-audit-')
    t_start = time.time()

    def on_pixels(item, img):
        if not use_ocr:
            return
        both = item.get('rotate', 0) in (90, 270)
        key = receipt_key(item['pixels_sha256'], both, rec.name, rec.version)
        item['ocr_key'] = key
        if key in tasks:
            return
        old = read_json(paths['ocr'] / (key + '.json'))
        if (isinstance(old, dict) and old.get('status') == 'ok' and old.get('input_pixels_sha256') == item['pixels_sha256']
                and old.get('recognizer') == rec.name and old.get('recognizer_version') == rec.version
                and old.get('rules_version') == RULES_VERSION):
            tasks[key] = {'reuse': True}
            return
        prep, info = prepare_ocr_input(img, both)
        p = Path(tmp) / (key + '.png')
        prep.save(str(p), format='PNG')
        info['sha256'] = pixels_sha256(prep.convert('RGBA'))
        tasks[key] = {'key': key, 'path': str(p), 'pixels_sha256': item['pixels_sha256'], 'size': list(img.size),
                      'both': both, 'prepared': info}

    try:
        state = current_state(project, export, paths['slices'], on_pixels)
        t_inv = time.time() - t_start
        todo = [t for t in tasks.values() if not t.get('reuse')]
        t0 = time.time()
        results = rec.run(todo) if todo else {}
        t_ocr = time.time() - t0
        for t in todo:
            r = results.get(t['key']) or {'ok': False, 'error': '识别器没有返回这张图', 'items': [], 'raw': None}
            write_json(paths['ocr'] / (t['key'] + '.json'), {
                'schema': 'chinese_audit.ocr.v1', 'key': t['key'], 'recognizer': rec.name,
                'recognizer_version': rec.version, 'languages': rec.languages, 'rules_version': RULES_VERSION,
                'input_pixels_sha256': t['pixels_sha256'], 'input_size': t['size'], 'both_ways': t['both'],
                'prepared': t['prepared'], 'status': 'ok' if r.get('ok') else 'failed', 'error': r.get('error'),
                'results': r.get('items') or [], 'raw': r.get('raw'), 'created': now()})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    pending = []
    for item in state['items']:
        k = item['kind']
        if k == 'text':
            pass
        elif k == 'atlas_error' or item.get('error'):
            item['scan'], item['reasons'] = 'error', [item.get('error') or '读不了']
        elif k == 'export_image' and item.get('same_as'):
            item['scan'], item['reasons'] = 'same_as_source', ['和工程里的图字节相同，沿用源图的结果']
        elif not use_ocr:
            item['scan'], item['reasons'] = 'not_scanned', ['没有用识别器，要人工复核']
        else:
            rp = paths['ocr'] / (item['ocr_key'] + '.json')
            receipt = read_json(rp)
            item['ocr_receipt'] = 'ocr/%s.json' % item['ocr_key']
            item['ocr_receipt_sha256'] = sha_file(rp) if rp.is_file() else None
            item['scan'], item['reasons'], hits = classify(receipt)
            item['ocr_text'] = [r.get('text') for r in (receipt or {}).get('results') or []][:20]
        item['bind_sha256'] = bind_sha(item)
        if item.get('scan') in ('needs_review', 'not_scanned', 'error'):
            pending.append(item)

    pictures = [i for i in state['items'] if i['kind'] in PICTURE_KINDS]
    texts = [i for i in state['items'] if i['kind'] == 'text']
    stats = {'images': sum(1 for i in pictures if i['kind'] == 'image'),
             'slices': sum(1 for i in pictures if i['kind'] == 'slice'),
             'export_images': sum(1 for i in pictures if i['kind'] == 'export_image'),
             'atlases': len(state['atlases']), 'atlas_errors': sum(1 for x in state['atlases'] if x.get('error')),
             'ocr_calls': len(todo), 'ocr_reused': sum(1 for t in tasks.values() if t.get('reuse')),
             'ocr_unique_inputs': len(tasks), 'ocr_seconds': round(t_ocr, 2), 'inventory_seconds': round(t_inv, 2),
             'text_findings': len(texts), 'text_needs_review': sum(1 for t in texts if t['scan'] == 'needs_review'),
             'text_auto_pass': sum(1 for t in texts if t['scan'] == 'auto_pass'),
             'auto_covered': sum(1 for i in pictures if i.get('scan') == 'auto_covered'),
             'pending': len(pending)}
    audit = {'schema': SCHEMA, 'scanner_version': SCANNER_VERSION, 'rules_version': RULES_VERSION, 'created': now(),
             'project': str(project), 'out': str(out),
             'recognizer': {'name': rec.name, 'version': rec.version, 'languages': rec.languages, 'note': rec.note,
                            'notes': notes},
             'source_manifest': state['manifest'], 'source_manifest_sha256': state['manifest']['sha256'],
             'atlases': state['atlases'], 'export': state['export'],
             'export_manifest_sha256': state['export']['manifest']['sha256'] if state['export'] else None,
             'items': state['items'], 'stats': stats,
             'note': '本文件只是扫描记录。能不能给英文试玩链接只看 check 的结果（check-result.json），这里写的 passed 不算数。'}
    write_json(paths['audit'], audit)
    _print_scan(audit, pending, out)
    return 0


def _label(item):
    if item['kind'] == 'slice':
        return '%s 的切片 %s（%s）' % (item.get('file') or item.get('atlas_file'), item.get('slice'), item.get('atlas_file'))
    if item['kind'] == 'text':
        return '%s %s「%s」' % (item['file'], item.get('where'), clip(item.get('decoded') or '', 40))
    if item['kind'] == 'export_image':
        return '导出 %s' % item['file']
    return item.get('file') or '?'


def _print_scan(audit, pending, out):
    s, rec = audit['stats'], audit['recognizer']
    print('中文专项扫描完成（这一步不判通过；通过只看 check）。')
    print('图片 %d 张，图集 %d 个（读不了 %d 个），切片 %d 个；导出图 %d 张。' % (
        s['images'], s['atlases'], s['atlas_errors'], s['slices'], s['export_images']))
    if audit.get('export'):
        e = audit['export']
        print('导出：%d 张图里 %d 张和工程里的图字节相同（沿用源图结果），%d 张单独识字。' % (e['images'], e['matched_source'], e['own_scan']))
    print('文字：%d 处有汉字，要结论 %d 处，自动放过 %d 处（注释、日志、节点名等，理由写在 audit.json）。' % (
        s['text_findings'], s['text_needs_review'], s['text_auto_pass']))
    print('识别器：%s（%s）。%s' % (rec['name'], rec['version'], rec.get('note') or ''))
    for n in rec.get('notes') or []:
        print('  ' + n)
    print('本次识字 %d 张（用时 %.1f 秒），沿用旧回执 %d 张；自动扫描覆盖（没字或只有英文）%d 项。' % (
        s['ocr_calls'], s['ocr_seconds'], s['ocr_reused'], s['auto_covered']))
    print('要复核的：%d 项。' % len(pending))
    for item in pending[:25]:
        print('  %s  %s：%s' % (item['id'], _label(item), '；'.join(item.get('reasons') or [item.get('reason') or ''])))
    if len(pending) > 25:
        print('  ……还有 %d 项，全部在 %s' % (len(pending) - 25, out / 'audit.json'))
    print('记录：%s' % (out / 'audit.json'))
    if pending:
        print('下一步：sheet --pending 生成复核图，看清以后用 review 写结论（带证据），再跑 check。')
    else:
        print('下一步：跑 check。')


# ---------------------------------------------------------------- reviews

def load_reviews(out):
    doc = read_json(out / 'reviews.json')
    if doc is None:
        return [] if not (out / 'reviews.json').exists() else None
    if not isinstance(doc, dict) or not isinstance(doc.get('reviews'), list):
        return None
    return [r for r in doc['reviews'] if isinstance(r, dict)]


def _image_pixels(p):
    if Path(p).suffix.lower() not in IMAGE_SUFFIXES:
        return None
    try:
        return pixels_sha256(open_rgba(p))
    except Exception:      # noqa: BLE001
        return None


def evidence_problems(out, review, old_shas=()):
    """Why a review's evidence does not hold now (empty list = holds). old_shas: earlier versions of the same item;
    a picture of one of them is evidence about the old picture, not this one."""
    bad = []
    ev = review.get('evidence') or []
    if review.get('item_kind') in PICTURE_KINDS + ('atlas_error',) and not ev:
        bad.append('没有证据文件')
    if review.get('item_kind') == 'text' and not ev and not (review.get('reason') or '').strip():
        bad.append('没有证据也没有理由')
    for e in ev:
        rel = e.get('path') if isinstance(e, dict) else None
        if not rel:
            bad.append('证据记录坏了')
            continue
        p = (out / rel).resolve()
        if not inside(p, out):
            bad.append('证据 %s 不在结果目录里' % rel)
        elif not p.is_file():
            bad.append('证据文件 %s 不在了' % rel)
        elif sha_file(p) != e.get('sha256'):
            bad.append('证据文件 %s 和记下的 sha 对不上（被改过）' % rel)
        m = re.match(r'^slices/([0-9a-f]{64})\.png$', rel)
        if m and review.get('item_kind') == 'slice' and m.group(1) != review.get('item_sha'):
            bad.append('证据 %s 是另一版的切片，不是现在这张' % rel)
        elif old_shas and p.is_file() and _image_pixels(p) in set(old_shas) - {review.get('item_sha')}:
            bad.append('证据 %s 是这一项改之前的旧图' % rel)
    return bad


def _new_review_id(reviews):
    n = 0
    for r in reviews:
        m = re.match(r'^R(\d+)$', str(r.get('review_id', '')))
        if m:
            n = max(n, int(m.group(1)))
    return 'R%04d' % (n + 1)


def _item_still_current(project, audit, item):
    """Cheap re-check before a review is written: are the bytes this item was cut from unchanged?"""
    k = item['kind']
    if k == 'export_image':
        base = Path((audit.get('export') or {}).get('dir') or '')
        p = base / item['file']
        return p.is_file() and sha_file(p) == item.get('file_sha256')
    if k == 'slice':
        a = project / item['atlas_file']
        ok = a.is_file() and sha_file(a) == item.get('atlas_sha256')
        if item.get('file'):
            p = project / item['file']
            ok = ok and p.is_file() and sha_file(p) == item.get('file_sha256')
        return ok
    if k == 'atlas_error':
        p = project / item['file']
        return p.is_file()
    p = project / item['file']
    return p.is_file() and sha_file(p) == item.get('file_sha256')


def cmd_review(a):
    project = Path(a.project).resolve()
    out = resolve_out(project, a.out)
    audit = read_json(out / 'audit.json')
    if not isinstance(audit, dict) or audit.get('schema') != SCHEMA:
        raise Refused('还没有扫描记录（%s）。先跑 scan。' % (out / 'audit.json'))
    if audit.get('scanner_version') != SCANNER_VERSION or audit.get('rules_version') != RULES_VERSION:
        raise Refused('扫描器或规则版本变了，旧扫描不能再用。先重新 scan，再写复核。')
    items = {i['id']: i for i in audit.get('items', [])}
    if a.field and not a.file:
        raise Usage('--field 要和 --file 一起用')
    if a.file:
        # 简化.11 real export (SausageRun English v1): 857 level-config "name" values needed one conclusion each; one
        # reviewed reason may cover a batch of text items, each still recorded and checked on its own
        try:
            field_rx = re.compile(a.field) if a.field else None
        except re.error as exc:
            raise Usage('--field 不是正确的正则：%s' % exc)
        picked = [i['id'] for i in audit.get('items', []) if i.get('kind') == 'text' and i.get('scan') == 'needs_review'
                  and fnmatch.fnmatchcase(i.get('file') or '', a.file)
                  and (field_rx is None or field_rx.search(i.get('field') or i.get('where') or ''))]
        if not picked:
            raise Refused('--file %s%s 一项要结论的文字都没选中' % (a.file, ' --field %s' % a.field if a.field else ''))
        print('按 --file%s 选中 %d 项文字' % ('/--field' if a.field else '', len(picked)))
        a.id = list(a.id) + [p for p in picked if p not in a.id]
    if not a.id:
        raise Usage('要给 --id，或者用 --file（加 --field）选一批文字项')
    unknown = [i for i in a.id if i not in items]
    if unknown:
        raise Usage('audit.json 里没有这些编号：%s' % ', '.join(unknown))
    reviews = load_reviews(out)
    if reviews is None:
        raise Refused('reviews.json 坏了，读不了：%s' % (out / 'reviews.json'))
    by_id = {r.get('review_id'): r for r in reviews}
    sup = a.supersedes
    if sup and sup not in by_id:
        raise Refused('要纠正的复核 %s 不存在' % sup)
    if sup and by_id[sup].get('item_id') not in a.id:
        raise Refused('复核 %s 说的是 %s，不在这次的 --id 里' % (sup, by_id[sup].get('item_id')))
    for iid in a.id:
        it = items[iid]
        if not _item_still_current(project, audit, it):
            raise Refused('%s（%s）在扫描以后改过了，先重新 scan，再按新的编号复核。' % (iid, _label(it)))
        if it['kind'] == 'text' and it.get('scan') == 'auto_pass':
            pass    # allowed: a person may still record a conclusion on an auto-passed line
    # evidence: bind every file by sha; files outside the result folder are copied in
    ev_rows = []
    for raw in a.evidence or []:
        cand = [Path(raw), out / raw, project / raw]
        p = next((c.resolve() for c in cand if c.is_file()), None)
        if p is None:
            raise Refused('证据文件不在：%s' % raw)
        digest = sha_file(p)
        if inside(p, out):
            rel = p.relative_to(out).as_posix()
        else:
            target = out / 'evidence' / ('%s-%s' % (digest[:12], p.name))
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.is_file():
                shutil.copyfile(str(p), str(target))
            rel = target.relative_to(out).as_posix()
        ev_rows.append({'path': rel, 'sha256': digest, 'source': str(p)})
    new = []
    for iid in a.id:
        it = items[iid]
        kind = a.evidence_kind or ('text_context' if it['kind'] == 'text' else 'slice_view')
        row = {'review_id': None, 'item_id': iid, 'item_kind': it['kind'], 'item_sha': it.get('bind_sha256') or bind_sha(it),
               'item_file': it.get('file'), 'item_file_sha256': it.get('file_sha256'), 'slice': it.get('slice'),
               'verdict': a.verdict, 'by': a.by.strip(), 'evidence': [dict(e) for e in ev_rows], 'evidence_kind': kind,
               'reason': (a.reason or '').strip(), 'supersedes': sup if sup and by_id[sup].get('item_id') == iid else None,
               'created': now(), 'scanner_version': SCANNER_VERSION}
        bad = evidence_problems(out, row, {r.get('item_sha') for r in reviews if r.get('item_id') == iid})
        if bad:
            raise Refused('%s：%s。复核要带看得到的证据（切片图、复核图、渲染截图）或写清理由。' % (iid, '；'.join(bad)))
        new.append(row)
    if not a.by.strip():
        raise Usage('--by 不能是空的')
    for row in new:
        row['review_id'] = _new_review_id(reviews)
        reviews.append(row)
    write_json(out / 'reviews.json', {'schema': 'chinese_audit.reviews.v1', 'reviews': reviews})
    for row in new:
        print('已记下 %s：%s → %s（%s，证据 %d 个，类型 %s）%s' % (
            row['review_id'], row['item_id'], row['verdict'], row['by'], len(row['evidence']), row['evidence_kind'],
            '，纠正 %s' % row['supersedes'] if row['supersedes'] else ''))
    print('记录：%s。写完复核后跑 check。' % (out / 'reviews.json'))
    return 0


# ---------------------------------------------------------------- check (the only place `passed` is computed)

OK_STATES = ('auto_covered', 'auto_pass', 'reviewed')


def pre_english_chinese(project):
    """SHA-256 of pre-English pictures that the list marks as having Chinese ({"chinese": "yes"/true} next to a sha)."""
    doc = read_json(Path(project) / 'docs' / 'english' / 'pre-english-images.json')
    marked = set()

    def yes(v):
        return v is True or str(v).strip().lower() in ('yes', 'true', '1', 'chinese', '有', '是')

    def walk(x, key_sha=None):
        if isinstance(x, dict):
            sha = x.get('sha256') or key_sha
            flag = next((x[k] for k in ('chinese', 'has_chinese', 'hasChinese') if k in x), None)
            if isinstance(sha, str) and HEX64.match(sha.lower()) and flag is not None and yes(flag):
                marked.add(sha.lower())
            for k, v in x.items():
                walk(v, k.lower() if isinstance(k, str) and HEX64.match(k.lower()) else None)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    if doc is not None:
        walk(doc)
        for k in ('chinese', 'chinese_images'):
            if isinstance(doc, dict) and isinstance(doc.get(k), list):
                marked.update(s.lower() for s in doc[k] if isinstance(s, str) and HEX64.match(s.lower()))
    return marked


def _diff(old, new):
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(k for k in set(old) & set(new) if old[k] != new[k])
    return added, removed, changed


def _show(names, n=8):
    return '、'.join(names[:n]) + ('……共 %d 个' % len(names) if len(names) > n else '')


def evaluate(project, out, export=None, snapshot=None):
    project = Path(project).resolve()
    problems, warnings = [], []

    def problem(code, message, fix, item=None, **kw):
        row = {'code': code, 'message': message, 'fix': fix}
        if item is not None:
            row.update({'id': item.get('id'), 'kind': item.get('kind'), 'file': item.get('file')})
            if item.get('slice') is not None:
                row['slice'] = item['slice']
                row['atlas_file'] = item.get('atlas_file')
        row.update(kw)
        problems.append(row)

    audit = read_json(out / 'audit.json')
    if not isinstance(audit, dict) or audit.get('schema') != SCHEMA:
        old = project / 'docs' / 'english' / 'image-review.json'
        problem('no_audit', '没有中文专项扫描记录（%s）%s' % (out / 'audit.json', '；docs/english/image-review.json 里手写的 '
                'done / chinese:no / slices_reviewed:true 不是证据，不算' if old.is_file() else ''),
                '跑 chinese_audit.py scan，再按提示复核')
        audit = None
    else:
        if audit.get('scanner_version') != SCANNER_VERSION:
            problem('scanner_changed', '扫描器版本变了（记录是 %s，现在是 %s），旧证据作废' % (audit.get('scanner_version'), SCANNER_VERSION),
                    '重新 scan')
        if audit.get('rules_version') != RULES_VERSION:
            problem('rules_changed', '规则版本变了（记录是 %s，现在是 %s），旧证据作废' % (audit.get('rules_version'), RULES_VERSION),
                    '重新 scan')
    if export is None and audit and audit.get('export'):
        warnings.append('这次 check 没给 --export：只核对了源资源，扫过的导出（%s）这次没有核对' % audit['export'].get('dir'))
    state = current_state(project, export)
    rec = (audit or {}).get('recognizer') or {'name': 'none', 'version': 'none'}

    # 1. the inventory must be the one that was scanned
    if audit:
        old = {k: v.get('sha256') for k, v in (audit.get('source_manifest') or {}).get('files', {}).items()}
        new = {k: v['sha256'] for k, v in state['manifest']['files'].items()}
        added, removed, changed = _diff(old, new)
        for code, names, what in (('files_added', added, '新加的'), ('files_changed', changed, '改过的'),
                                  ('files_removed', removed, '删掉的')):
            if names:
                problem(code, '扫描以后有%s文件 %d 个：%s' % (what, len(names), _show(names)), '重新 scan', files=names[:200])
    audit_items = {i.get('id'): i for i in (audit or {}).get('items', []) if isinstance(i, dict)}

    reviews = load_reviews(out)
    if reviews is None:
        problem('reviews_broken', 'reviews.json 读不了：%s' % (out / 'reviews.json'), '修好或删掉它，再重新复核')
        reviews = []
    by_rid = {}
    for r in reviews:
        if r.get('review_id') in by_rid:
            problem('review_duplicate_id', '复核编号 %s 出现两次' % r.get('review_id'), '删掉重复的那条，重新 review')
        by_rid[r.get('review_id')] = r
    superseded = set()
    for r in reviews:
        s = r.get('supersedes')
        if s:
            if s not in by_rid:
                problem('supersedes_unknown', '复核 %s 说要纠正 %s，但没有这一条' % (r.get('review_id'), s), '重新 review，--supersedes 写对编号')
            elif by_rid[s].get('item_id') != r.get('item_id'):
                problem('supersedes_other_item', '复核 %s 纠正的 %s 说的不是同一项' % (r.get('review_id'), s), '重新 review')
            else:
                superseded.add(s)
    old_by_item = {}
    for r in reviews:
        old_by_item.setdefault(r.get('item_id'), set()).add(r.get('item_sha'))
    valid = {}
    for r in reviews:
        bad = evidence_problems(out, r, old_by_item.get(r.get('item_id'), ()))
        if r.get('verdict') not in VERDICTS:
            bad.append('结论 %s 不认识' % r.get('verdict'))
        if not str(r.get('by') or '').strip():
            bad.append('没写是谁复核的')
        if bad:
            problem('review_evidence_bad', '复核 %s（%s）不能用：%s' % (r.get('review_id'), r.get('item_id'), '；'.join(bad)),
                    '重新 review，带上现在这张图的证据文件', review_id=r.get('review_id'))
        else:
            valid[r.get('review_id')] = r
    chinese_shas = {r['item_sha'] for r in valid.values() if r['verdict'] == 'chinese' and r['review_id'] not in superseded}
    chinese_files = {r.get('item_file_sha256') for r in valid.values()
                     if r['verdict'] == 'chinese' and r['review_id'] not in superseded and r.get('item_kind') in ('image', 'export_image')}
    chinese_files.discard(None)

    status, rows = {}, []
    evidence_kinds = {k: [] for k in EVIDENCE_KINDS}
    for item in state['items']:
        iid, k = item['id'], item['kind']
        b = bind_sha(item)
        row = {'id': iid, 'kind': k, 'file': item.get('file'), 'slice': item.get('slice')}
        st, why = None, []
        old = audit_items.get(iid)
        if item.get('binding_error'):
            problem('spine_binding_unresolved', '%s：%s' % (_label(item), item['error']),
                    '修正 Spine 图集、切片范围或贴图绑定，再重新 scan', item)
            st, why = 'invalid_spine_input', [item['error']]
        elif audit and (old is None or (old.get('bind_sha256') or bind_sha(old)) != b):
            problem('not_scanned_now', '%s：扫描记录里没有现在这一版' % _label(item), '重新 scan', item)
            st = 'stale'
        elif k == 'text':
            st = 'auto_pass' if item['scan'] == 'auto_pass' else 'needs_review'
            why = [item['reason']]
        elif k == 'export_image' and item.get('same_as'):
            src = [status.get(s) for s in item['same_as']]
            st = 'same_as_source' if any(s in OK_STATES for s in src) else 'source_not_ok'
        elif item.get('error') or k == 'atlas_error':
            st, why = 'needs_review', [item.get('error') or '读不了']
        elif rec.get('name') in (None, 'none'):
            st, why = 'needs_review', ['没有识字回执（扫描时没用识别器）']
        else:
            key = receipt_key(item['pixels_sha256'], item.get('rotate', 0) in (90, 270), rec['name'], rec['version'])
            rp = out / 'ocr' / (key + '.json')
            receipt = read_json(rp) if rp.is_file() else None
            if receipt is None:
                problem('receipt_missing', '%s：识字回执不在（ocr/%s.json）' % (_label(item), key), '重新 scan', item)
                st = 'needs_review'
            elif old is not None and old.get('ocr_receipt_sha256') != sha_file(rp):
                problem('receipt_changed', '%s：识字回执和扫描时记下的 sha 对不上（被改过）' % _label(item), '重新 scan', item)
                st = 'needs_review'
            elif receipt.get('input_pixels_sha256') != item['pixels_sha256'] or receipt.get('rules_version') != RULES_VERSION:
                problem('receipt_wrong_input', '%s：回执识的不是现在这张图/这个切片' % _label(item), '重新 scan', item)
                st = 'needs_review'
            else:
                st, why, _hits = classify(receipt)
                row['ocr_text'] = [x.get('text') for x in receipt.get('results') or []][:10]
                if old is not None and old.get('scan') == 'auto_covered' and st != 'auto_covered':
                    problem('audit_disagrees', '%s：audit.json 记成没字/只有英文，回执却是「%s」' % (_label(item), '；'.join(why)),
                            '重新 scan，再按回执复核', item)
        if st == 'needs_review' or (st == 'source_not_ok'):
            st, why = _apply_reviews(item, b, st, why, reviews, valid, superseded, problem, evidence_kinds, row)
        if st in ('auto_covered', 'reviewed', 'auto_pass') and b in chinese_shas and k != 'text':
            problem('chinese_still_here', '%s：这张图/切片之前被确认有中文（同样的像素），现在还在' % _label(item),
                    '换成英文版，重新 scan', item)
        status[iid] = st
        row['status'], row['why'] = st, why
        if st not in ('auto_covered', 'auto_pass', 'same_as_source'):
            rows.append(row)

    # 2. pictures confirmed or marked Chinese must not be in the project or the export
    marked = pre_english_chinese(project) | chinese_files
    for it in state['items']:
        if it['kind'] in ('image', 'export_image') and it.get('file_sha256') in marked:
            problem('pre_english_chinese_here', '%s：和标成有中文的原图字节相同' % _label(it), '换成英文版，重新构建、重新 scan', it)

    # 3. export and served snapshot must be the ones that were scanned
    exp_now = state['export']
    if export is not None:
        rec_exp = (audit or {}).get('export')
        if not rec_exp:
            problem('export_not_scanned', '这份导出没有扫过：%s' % export, '跑 scan --export <这份导出>')
        else:
            a_, r_, c_ = _diff(rec_exp['manifest']['files'], exp_now['manifest']['files'])
            if a_ or r_ or c_:
                problem('export_changed', '导出和扫过的那份不一样：多了 %d、少了 %d、改了 %d 个文件（%s）' % (
                    len(a_), len(r_), len(c_), _show(a_ + r_ + c_)), '重新 scan --export')
        newer = source_newer_than_export(project, export)
        if newer:   # 11.17 R4Q7 (奔跑吧巨人 source8 + export7 passed): the export was built before these source edits
            problem('export_not_this_source', '导出不是这版源码：导出构建以后，源码又改了 %d 个文件（%s）' % (
                len(newer), _show(newer)), '用现在的源码重新构建导出，再 scan --export、check', files=newer[:200])
        try:
            sys.path.insert(0, str(HERE))
            import check_export_images as CEI
            r = CEI.check(project, export)
            for row in r.get('old', []):
                problem('export_old_image', '导出里有旧图 %s（工程里是 %s）：%s' % (row['export'], row['project'], row['why']),
                        '删掉导出目录重新构建，再 scan --export')
        except Exception as exc:      # noqa: BLE001
            problem('export_check_failed', 'check_export_images 没跑成：%s' % exc, '看报错，修好再查')
    snap_info = None
    if snapshot is not None:
        ref = exp_now['manifest'] if exp_now else ((audit or {}).get('export') or {}).get('manifest')
        if not Path(snapshot).is_dir():
            raise Usage('找不到快照目录：%s' % snapshot)
        snap = export_manifest(snapshot)
        snap_info = {'dir': str(Path(snapshot).resolve()), 'sha256': snap['sha256'], 'files': len(snap['files'])}
        if not ref:
            problem('snapshot_without_export', '给了试玩快照，但没有扫过的导出可以对', '先 scan --export <导出>，check 也带上 --export')
        else:
            a_, r_, c_ = _diff(ref['files'], snap['files'])
            if a_ or r_ or c_:
                problem('snapshot_mismatch', '试玩快照和查过的导出不一样：快照多了 %d、少了 %d、改了 %d 个文件（%s）' % (
                    len(a_), len(r_), len(c_), _show(a_ + r_ + c_)), '用查过的这份导出重新起试玩服务，或对新导出重新 scan + check')

    counts = {}
    for st in status.values():
        counts[st] = counts.get(st, 0) + 1
    kinds = {}
    for it in state['items']:
        kinds[it['kind']] = kinds.get(it['kind'], 0) + 1
    result = {
        'schema': 'chinese_audit.check.v1', 'scanner_version': SCANNER_VERSION, 'rules_version': RULES_VERSION,
        'checked_at': now(), 'project': str(project), 'out': str(out),
        'export': {'dir': str(Path(export).resolve()), 'manifest_sha256': exp_now['manifest']['sha256'],
                   'images': exp_now['images']} if exp_now else None,
        'snapshot': snap_info, 'recognizer': rec, 'source_manifest_sha256': state['manifest']['sha256'],
        'audit_source_manifest_sha256': (audit or {}).get('source_manifest_sha256'),
        'items_by_kind': kinds, 'status_counts': counts,
        'evidence_kinds': evidence_kinds,
        'evidence_kind_note': 'isolated_render 是隔离渲染截图：只证明资源能正确显示，不是自然游玩到达，也不是真机；natural_play 才是自然游玩。',
        'problems': problems, 'warnings': warnings, 'items': rows,
        'limits': ['校验的是证据存在、绑定到现在的像素和文件、覆盖完整；人对图的判断本身对不对，程序证明不了。',
                   '导出里的自动合图只按整张图识字，不拆切片。'],
    }
    result['passed'] = not problems
    return result


def _apply_reviews(item, b, st, why, reviews, valid, superseded, problem, evidence_kinds, row):
    iid = item['id']
    mine = [r for r in reviews if r.get('item_id') == iid]
    current = [r for r in mine if r.get('item_sha') == b]
    active = [r for r in current if r.get('review_id') in valid and r.get('review_id') not in superseded]
    if st == 'source_not_ok':
        if not active:
            problem('export_source_not_ok', '%s：和源图字节相同，但源图还没过（见源图那一条）' % _label(item),
                    '先把源图那一条处理好', item)
            return 'needs_review', ['源图没过']
    if not active:
        if mine and not current:
            problem('review_for_old_version', '%s：复核（%s）对的是旧版本，现在的像素/内容不一样了' % (
                _label(item), ', '.join(r.get('review_id') for r in mine)), '看现在这张，重新 review', item)
        else:
            problem('needs_review', '%s：%s，还没有带证据的复核结论' % (_label(item), '；'.join(why) or '要复核'),
                    '用 sheet 看清以后 review --id %s --verdict ... --evidence ...' % iid, item, reasons=why)
        return 'needs_review', why
    verdicts = {r['verdict'] for r in active}
    if 'chinese' in verdicts and verdicts & CLEARING:
        problem('review_conflict', '%s：复核结论相反（%s），又没写 --supersedes' % (
            _label(item), '、'.join('%s=%s' % (r['review_id'], r['verdict']) for r in active)),
                '确认哪个对，用 review --supersedes <错的那条> 重新写', item)
        return 'conflict', why
    if verdicts == {'chinese'}:
        problem('confirmed_chinese', '%s：确认有中文（%s）' % (_label(item), ', '.join(r['review_id'] for r in active)),
                '改成英文，重新 scan', item)
        return 'confirmed_chinese', why
    for r in active:
        evidence_kinds.setdefault(r.get('evidence_kind') or 'slice_view', []).append(
            {'review_id': r['review_id'], 'item_id': iid, 'verdict': r['verdict'], 'by': r.get('by')})
    row['reviews'] = [r['review_id'] for r in active]
    row['verdict'] = sorted(verdicts)
    row['evidence_kind'] = sorted({r.get('evidence_kind') for r in active})
    return 'reviewed', why


def cmd_check(a):
    project = Path(a.project).resolve()
    if not (project / 'assets').is_dir():
        raise Usage('不是 Cocos 工程（没有 assets/）：%s' % project)
    export = Path(a.export).resolve() if a.export else None
    snapshot = Path(a.snapshot).resolve() if a.snapshot else None
    out = resolve_out(project, a.out)
    guard_out(out, project, export, snapshot)
    if export is not None and not export.is_dir():
        raise Usage('找不到导出目录：%s' % export)
    result = evaluate(project, out, export, snapshot)
    write_json(out / 'check-result.json', result)
    if a.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 0 if result['passed'] else 1
    p = result['problems']
    if result['passed']:
        print('中文专项检查：通过。')
    else:
        print('中文专项检查：不通过，%d 条问题。不能把这一版当成英文试玩交出去。' % len(p))
    c = result['status_counts']
    print('自动扫描覆盖 %d，自动放过的文字 %d，有复核结论 %d，和源图相同的导出图 %d；待处理 %d。' % (
        c.get('auto_covered', 0), c.get('auto_pass', 0), c.get('reviewed', 0), c.get('same_as_source', 0),
        sum(v for k, v in c.items() if k not in OK_STATES + ('same_as_source',))))
    iso = result['evidence_kinds'].get('isolated_render') or []
    if iso:
        print('其中 %d 条复核的证据是隔离渲染截图（不算自然游玩、不算真机）。' % len(iso))
    for w in result['warnings']:
        print('注意：' + w)
    for row in p[:30]:
        print('  [%s] %s → %s' % (row['code'], row['message'], row['fix']))
    if len(p) > 30:
        print('  ……还有 %d 条，全部在 check-result.json' % (len(p) - 30))
    print('结果：%s' % (out / 'check-result.json'))
    return 0 if result['passed'] else 1


# ---------------------------------------------------------------- sheet

def _font(size):
    from PIL import ImageFont
    cands = ['/System/Library/Fonts/Hiragino Sans GB.ttc', '/System/Library/Fonts/PingFang.ttc',
             '/System/Library/Fonts/STHeiti Medium.ttc', '/System/Library/Fonts/STHeiti Light.ttc']
    windir = os.environ.get('WINDIR')
    if windir:
        cands += [str(Path(windir) / 'Fonts' / n) for n in ('msyh.ttc', 'msyh.ttf', 'simhei.ttf', 'simsun.ttc')]
    cands += ['/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc']
    for c in cands:
        if Path(c).is_file():
            try:
                return ImageFont.truetype(c, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _picture_for(item, project, out, audit):
    k = item['kind']
    if k == 'slice':
        p = out / (item.get('slice_file') or ('slices/%s.png' % item.get('pixels_sha256')))
    elif k == 'export_image':
        p = Path((audit.get('export') or {}).get('dir') or '') / item['file']
    elif k == 'image':
        p = project / item['file']
    else:
        return None
    return p if p.is_file() else None


def cmd_sheet(a):
    project = Path(a.project).resolve()
    out = resolve_out(project, a.out)
    audit = read_json(out / 'audit.json')
    if not isinstance(audit, dict) or audit.get('schema') != SCHEMA:
        raise Refused('还没有扫描记录（%s）。先跑 scan。' % (out / 'audit.json'))
    items = {i['id']: i for i in audit.get('items', [])}
    if a.id:
        unknown = [i for i in a.id if i not in items]
        if unknown:
            raise Usage('audit.json 里没有这些编号：%s' % ', '.join(unknown))
        ids = list(a.id)
    else:
        exp = (audit.get('export') or {}).get('dir')
        result = evaluate(project, out, Path(exp) if exp and Path(exp).is_dir() else None)
        ids = [r['id'] for r in result['items'] if r['status'] not in OK_STATES]
    Image = _pil()
    from PIL import ImageDraw
    font, small = _font(22), _font(16)
    cells, texts_only = [], []
    for iid in ids:
        it = items.get(iid)
        if it is None:
            continue
        pic = _picture_for(it, project, out, audit)
        if pic is None:
            texts_only.append(it)
            continue
        img = open_rgba(pic)
        w, h = img.size
        f = max(1.0, 96.0 / max(1, h))
        if w * f > 1600 and h * (1600.0 / w) >= 96:
            f = 1600.0 / w
        size = (max(1, int(round(w * f))), max(96, int(round(h * f))))
        resample = getattr(getattr(Image, 'Resampling', Image), 'NEAREST' if f >= 2 else 'LANCZOS')
        img = img.resize(size, resample)
        panels = []
        for bg in ((32, 32, 32), (235, 235, 235)):
            base = Image.new('RGBA', size, bg + (255,))
            base.alpha_composite(img)
            panels.append(base.convert('RGB'))
        side = size[0] * 2 + 16 <= 1800
        pw = size[0] * 2 + 16 if side else size[0]
        ph = size[1] if side else size[1] * 2 + 16
        label = '%s  %s' % (iid, _label(it))
        sub = '识字：%s   %s' % (clip(' | '.join(x for x in (it.get('ocr_text') or []) if x) or '（无）', 120),
                                  '；'.join(it.get('reasons') or []))
        tw = max(int(getattr(font, 'getlength', lambda s: 12 * len(s))(clip(label, 110))),
                 int(getattr(small, 'getlength', lambda s: 9 * len(s))(clip(sub, 140))))
        cw = max(pw, tw, 600) + 24
        cell = Image.new('RGB', (cw, ph + 70), (255, 255, 255))
        d = ImageDraw.Draw(cell)
        d.text((12, 6), clip(label, 110), fill=(0, 0, 0), font=font)
        d.text((12, 36), clip(sub, 140), fill=(90, 90, 90), font=small)
        cell.paste(panels[0], (12, 62))
        cell.paste(panels[1], (12 + size[0] + 16, 62) if side else (12, 62 + size[1] + 16))
        cells.append((iid, cell))
    if not cells and not texts_only:
        print('没有要复核的图。')
        return 1
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    sheets = out / 'sheets'
    sheets.mkdir(parents=True, exist_ok=True)
    pages, cur, cur_h = [], [], 0
    for iid, cell in cells:
        if cur and cur_h + cell.size[1] > 6000:
            pages.append(cur)
            cur, cur_h = [], 0
        cur.append((iid, cell))
        cur_h += cell.size[1] + 8
    if cur:
        pages.append(cur)
    written = []
    for n, page in enumerate(pages, 1):
        width = max(c.size[0] for _i, c in page)
        height = sum(c.size[1] + 8 for _i, c in page)
        sheet = Image.new('RGB', (width, height), (200, 200, 200))
        y = 0
        for _i, c in page:
            sheet.paste(c, (0, y))
            y += c.size[1] + 8
        p = sheets / ('sheet-%s-%02d.png' % (stamp, n))
        sheet.save(str(p), format='PNG')
        write_json(p.with_suffix('.json'), {'sheet': p.name, 'sha256': sha_file(p), 'ids': [i for i, _c in page]})
        written.append(p)
        print('%s（%d 项：%s）' % (p, len(page), ', '.join(i for i, _c in page[:12]) + ('…' if len(page) > 12 else '')))
    for it in texts_only[:40]:
        print('文字/其它（不画图）：%s  %s：%s' % (it['id'], _label(it), it.get('reason') or '；'.join(it.get('reasons') or [])))
    if len(texts_only) > 40:
        print('……文字类还有 %d 项，见 audit.json' % (len(texts_only) - 40))
    return 0


# ---------------------------------------------------------------- command line

def build_parser():
    ap = argparse.ArgumentParser(description='英化试玩前的中文专项检查（扫描、复核、复核图、校验）')
    sub = ap.add_subparsers(dest='cmd')
    s = sub.add_parser('scan', help='扫描工程（和这轮导出），写 audit.json')
    s.add_argument('--project', required=True)
    s.add_argument('--export')
    s.add_argument('--out')
    s.add_argument('--ocr', default='auto', choices=['auto', 'vision', 'tesseract', 'windows', 'none', 'fake'])
    r = sub.add_parser('review', help='写复核结论（证据按 sha 绑定）')
    r.add_argument('--project', required=True)
    r.add_argument('--out')
    r.add_argument('--id', action='append', default=[])
    r.add_argument('--file', help='文字项一次选一批：文件路径通配（如 "assets/resources/configs/*.json"），只选还要结论的文字项')
    r.add_argument('--field', help='和 --file 一起用：字段路径或行号要匹配的正则（如 "/name$"）')
    r.add_argument('--verdict', required=True, choices=list(VERDICTS))
    r.add_argument('--by', required=True)
    r.add_argument('--evidence', action='append')
    r.add_argument('--evidence-kind', choices=list(EVIDENCE_KINDS))
    r.add_argument('--reason')
    r.add_argument('--supersedes')
    h = sub.add_parser('sheet', help='把要复核的图拼成看得清的复核图')
    h.add_argument('--project', required=True)
    h.add_argument('--out')
    g = h.add_mutually_exclusive_group()
    g.add_argument('--pending', action='store_true')
    g.add_argument('--id', action='append')
    c = sub.add_parser('check', help='全部重算，只有通过才退出 0')
    c.add_argument('--project', required=True)
    c.add_argument('--export')
    c.add_argument('--snapshot')
    c.add_argument('--out')
    c.add_argument('--json', action='store_true')
    return ap


def main(argv=None):
    ap = build_parser()
    try:
        a = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    if not a.cmd:
        ap.print_help()
        return 2
    try:
        return {'scan': cmd_scan, 'review': cmd_review, 'sheet': cmd_sheet, 'check': cmd_check}[a.cmd](a)
    except Usage as exc:
        print('用法或环境有问题：%s' % exc)
        return 2
    except Refused as exc:
        print('不行：%s' % exc)
        return 1
    except OSError as exc:
        print('读写文件出错：%s' % exc)
        return 2


if __name__ == '__main__':
    sys.exit(main())
