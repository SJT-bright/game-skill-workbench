#!/usr/bin/env python3
"""Generate the resource table assets/scripts/generated/ResKeys.js (2.4) or ResKeys.ts (3.x) from the project (生成时预防 P12).

Why: 96 loading problems in 63 games came from paths and types written by hand ('ui/' + name for a file that is not
there, cc.JsonAsset for a .txt, a picture imported only as a texture). With this table the game code never writes a
path or a type: it picks a constant and hands it to the platform part ResLoader (Res.request(ResKeys.ui_gift_box)), which
throws on anything that is not a table entry. Run it when work starts and again after every resource is added, moved or
deleted (bind_art.py / the art step may call it); it is static and finishes in about a second.

  python3 -B make_res_keys.py --project <cocos project>            # write the table, list dangling references
  python3 -B make_res_keys.py --project <cocos project> --check    # write nothing; exit 1 when the table is stale
  options: --engine 2|3 (default: read project.json / package.json), --out <file>, --strict, --json

What goes in: every file inside a bundle (assets/resources, and every folder whose .meta says isBundle). One frozen entry
per file: {__resKey: 1, id, path, type, bundle}. The type comes from the file and its .meta:
  picture: 2.4 meta type 'sprite' (default) -> SpriteFrame, 'raw'/'texture' -> Texture2D;
           3.x userData.type 'sprite-frame' -> SpriteFrame (path + '/spriteFrame'), 'texture' -> Texture2D (path + '/texture')
  .json JsonAsset (Spine skeleton json skipped) · .txt/.csv/.xml TextAsset · .mp3/.ogg/.wav/.m4a/.aac AudioClip ·
  .prefab Prefab · .plist SpriteAtlas · .ttf/.otf TTFFont · .fnt BitmapFont · .anim AnimationClip · .mp4 VideoClip
Scenes, scripts, materials, effects, auto-atlas and Spine/DragonBones files are not loaded by path through ResLoader:
they are listed under "skipped" with the reason. Ids: resources/<path> -> path, other bundles -> <bundle>_<path>, lower
case, non-letters to '_'; a clash gets the type appended and is listed under "warnings".

After writing, the game scripts (assets/**/*.js|ts, not generated/ or tiktok-platform/) are read for ResKeys.<id> and
ResKeys['<id>']; an id that is no longer in the table (the file was deleted or renamed) is listed with file:line and the
exit code is 1. Direct engine loads (cc.resources.load, assetManager.loadBundle, bundle.load, cc.loader.loadRes) are
listed under "raw_loads": information for an English game (the original code stays), a failure with --strict (new games).
When docs/startup/first-screen.json exists (first_screen.py, P04), every entry gets its group from it and the table
also has ResKeys.HOME (ids the home page needs: preload these first) and ResKeys.DEFERRED (load after the home page
shows); without that file the table is exactly as before.
No machine paths, no platform-specific commands: runs the same on Windows.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA = 'res_keys.v1'
IMAGE = {'.png', '.jpg', '.jpeg', '.webp'}
BY_EXT = {
    '.json': 'JsonAsset', '.txt': 'TextAsset', '.csv': 'TextAsset', '.xml': 'TextAsset',
    '.mp3': 'AudioClip', '.ogg': 'AudioClip', '.wav': 'AudioClip', '.m4a': 'AudioClip', '.aac': 'AudioClip',
    '.prefab': 'Prefab', '.plist': 'SpriteAtlas', '.ttf': 'TTFFont', '.otf': 'TTFFont', '.fnt': 'BitmapFont',
    '.anim': 'AnimationClip', '.mp4': 'VideoClip',
}
SKIP_EXT = {
    '.fire': 'scene: cc.director.loadScene', '.scene': 'scene: director.loadScene', '.ts': 'script', '.js': 'script',
    '.mtl': 'material (referenced by components)', '.effect': 'effect (referenced by materials)', '.pac': 'auto-atlas',
    '.atlas': 'Spine/DragonBones atlas (load the skeleton through its own component)',
    '.skel': 'Spine binary skeleton', '.dbbin': 'DragonBones binary', '.md': 'document', '.DS_Store': 'system file',
}
OUT_DIR = ('assets', 'scripts', 'generated')
REF = re.compile(r"\bResKeys\s*(?:\.\s*([A-Za-z_$][\w$]*)|\[\s*(['\"])([^'\"]+)\2\s*\])")
RAW = re.compile(r"\b(?:cc\.resources\.load|resources\.load|assetManager\.loadBundle|cc\.loader\.loadRes(?:Dir|Array)?|"
                 r"loader\.loadRes|bundle\.load|\.loadRemote|Res\.load)\s*\(")  # F2: Res.load is read as an unlisted load
TABLE_PROPS = {'BUNDLES', 'SCHEMA', 'HOME', 'DEFERRED'}
FIRST_SCREEN = ('docs', 'startup', 'first-screen.json')
SKIP_SCRIPT_DIRS = ('generated', 'tiktok-platform', 'platform-kit')


def read_meta(path):
    meta = path.with_name(path.name + '.meta')
    if not meta.is_file():
        return None
    try:
        return json.loads(meta.read_text(encoding='utf-8'))
    except (ValueError, OSError):
        return {}


def detect_engine(project):
    pj = project / 'project.json'
    if pj.is_file():
        try:
            v = str(json.loads(pj.read_text(encoding='utf-8')).get('version', ''))
            if v.startswith('2'):
                return 2
        except ValueError:
            pass
    pk = project / 'package.json'
    if pk.is_file():
        try:
            v = str((json.loads(pk.read_text(encoding='utf-8')).get('creator') or {}).get('version', ''))
            if v.startswith('3'):
                return 3
        except ValueError:
            pass
    return 3 if (project / 'settings' / 'v2').is_dir() else 2


def bundle_roots(assets):
    roots = {}
    res = assets / 'resources'
    if res.is_dir():
        roots[res] = 'resources'
    for meta in sorted(assets.rglob('*.meta')):
        folder = meta.with_name(meta.name[:-5])
        if not folder.is_dir():
            continue
        try:
            data = json.loads(meta.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            continue
        user = data.get('userData') if isinstance(data.get('userData'), dict) else {}
        if data.get('isBundle') is True or user.get('isBundle') is True:
            name = data.get('bundleName') or user.get('bundleName') or folder.name
            roots[folder] = 'resources' if folder == res else name
    return roots


def owner_bundle(path, roots):
    best = None
    for root in roots:
        try:
            path.relative_to(root)
        except ValueError:
            continue
        if best is None or len(root.parts) > len(best.parts):
            best = root
    return best


def classify(path, engine):
    """Return (type, path suffix, None) or (None, None, skip reason)."""
    ext = path.suffix.lower()
    meta = read_meta(path)
    if ext in IMAGE:
        if engine == 2:
            kind = (meta or {}).get('type', 'sprite')
            return ('Texture2D', '', None) if kind in ('raw', 'texture') else ('SpriteFrame', '', None)
        kind = ((meta or {}).get('userData') or {}).get('type', 'sprite-frame')
        if kind == 'texture':
            return 'Texture2D', '/texture', None
        if kind == 'sprite-frame':
            return 'SpriteFrame', '/spriteFrame', None
        return None, None, 'picture imported as ' + str(kind)
    if ext == '.json' and meta:
        if 'textures' in meta and ('scale' in meta or 'atlas' in str(meta)) or meta.get('importer') in ('spine-data', 'dragonbones'):
            return None, None, 'Spine/DragonBones skeleton json (load it through its own component)'
    if ext in BY_EXT:
        return BY_EXT[ext], '', None
    if path.name in SKIP_EXT or ext in SKIP_EXT:
        return None, None, SKIP_EXT.get(path.name) or SKIP_EXT[ext]
    return None, None, 'unknown file type ' + (ext or path.name)


def make_id(bundle, rel):
    base = rel if bundle == 'resources' else bundle + '_' + rel
    ident = re.sub(r'[^a-z0-9]+', '_', base.lower()).strip('_') or 'res'
    return 'r_' + ident if ident[0].isdigit() else ident


def build(project, engine):
    assets = project / 'assets'
    if not assets.is_dir():
        raise SystemExit('make_res_keys: no assets/ folder in ' + str(project))
    roots = bundle_roots(assets)
    entries, skipped, warnings, used = [], [], [], {}
    for path in sorted(p for p in assets.rglob('*') if p.is_file() and not p.name.endswith('.meta')):
        root = owner_bundle(path, roots)
        if root is None:
            continue
        rel_file = path.relative_to(assets).as_posix()
        if path.parts[len(assets.parts):len(assets.parts) + 3] == OUT_DIR:
            continue
        rtype, suffix, reason = classify(path, engine)
        if rtype is None:
            skipped.append({'file': rel_file, 'reason': reason})
            continue
        bundle = roots[root]
        rel = path.relative_to(root).with_suffix('').as_posix()
        ident = make_id(bundle, rel)
        if ident in used or ident.upper() in TABLE_PROPS:
            new = ident + '_' + rtype.lower()
            n = 2
            while new in used:
                new = '%s_%s%d' % (ident, rtype.lower(), n)
                n += 1
            warnings.append('id %s already used by %s; %s gets %s' % (ident, used.get(ident, ident), rel_file, new))
            ident = new
        used[ident] = rel_file
        entries.append({'id': ident, 'path': rel + suffix, 'type': rtype, 'bundle': bundle, 'file': rel_file})
    bundles = sorted({e['bundle'] for e in entries} | set(roots.values()))
    table = {'schema': SCHEMA, 'engine': engine, 'entries': entries, 'bundles': bundles, 'skipped': skipped, 'warnings': warnings}
    fs = project.joinpath(*FIRST_SCREEN)
    if fs.is_file():                       # P04: home group / deferred group from first_screen.py
        try:
            data = json.loads(fs.read_text(encoding='utf-8'))
            home = {r['file'] for r in (data.get('home_needs') or {}).get('files', [])}
        except (ValueError, OSError, TypeError, KeyError):
            home = None
            warnings.append('docs/startup/first-screen.json unreadable: groups left out (re-run first_screen.py)')
        if home is not None:
            for e in entries:
                e['group'] = 'home' if 'assets/' + e['file'] in home else 'deferred'
            table['groups'] = True
    return table


HEADER = ('// GENERATED by remake-core/scripts/make_res_keys.py (%s) -- do not edit by hand.\n'
          '// Re-run it after adding, moving or deleting a resource. Load only through ResLoader: Res.request(ResKeys.<id>).\n')


def render(table):
    # F2 (发版自检 C4): every load is written here with literal bundle, path and type, one function per entry, so the
    # package resource check (audit_runtime_resources) lists every path from the game's own table. ResLoader and
    # AudioService only call key.request(cb) and have no load call of their own.
    lines, loaders, types = [], [], set()
    ts = table['engine'] == 3
    for e in table['entries']:
        lines.append('  %s: k(%s, %s, %s, %s),  // %s' % (e['id'], json.dumps(e['id']), json.dumps(e['path'], ensure_ascii=False),
                                                     json.dumps(e['type']), json.dumps(e['bundle'], ensure_ascii=False),
                                                     e['file']))
        types.add(e['type'])
        call = '%sgetBundle(%s).load(%s, %s%s, cb)' % ('assetManager.' if ts else 'cc.assetManager.',
                                                        json.dumps(e['bundle'], ensure_ascii=False),
                                                        json.dumps(e['path'], ensure_ascii=False), '' if ts else 'cc.', e['type'])
        loaders.append('  %s: function (cb%s) { %s; },' % (e['id'], ': any' if ts else '', call))
    body = '\n'.join(lines)
    loader_body = '\n'.join(loaders)
    bundles = json.dumps(table['bundles'], ensure_ascii=False)
    groups = ''
    if table.get('groups'):
        home = json.dumps([e['id'] for e in table['entries'] if e.get('group') == 'home'])
        later = json.dumps([e['id'] for e in table['entries'] if e.get('group') != 'home'])
        groups = ('  HOME: Object.freeze(%s),\n  DEFERRED: Object.freeze(%s),\n' % (home, later) if table['engine'] == 3 else
                  '  ResKeys.HOME = Object.freeze(%s);\n  ResKeys.DEFERRED = Object.freeze(%s);\n' % (home, later))
    if table['engine'] == 3:
        imports = ', '.join(['assetManager'] + sorted(types))
        return (HEADER % SCHEMA +
                'import { %s } from \'cc\';\n' % imports +
                'const L: { [id: string]: (cb: any) => void } = {\n' + loader_body + ('\n' if loader_body else '') + '};\n'
                'function k(id: string, path: string, type: string, bundle: string) {\n'
                '  return Object.freeze({ __resKey: 1 as const, id, path, type, bundle, request: L[id] });\n}\n'
                'export const ResKeys = Object.freeze({\n' + body + ('\n' if body else '') +
                '  BUNDLES: Object.freeze(' + bundles + '),\n' + groups + '});\n'
                '(globalThis as any).ResKeys = ResKeys;\nexport default ResKeys;\n')
    return (HEADER % SCHEMA +
            '(function (root) {\n  \'use strict\';\n'
            '  var L = {\n' + loader_body + ('\n' if loader_body else '') + '  };\n'
            '  function k(id, path, type, bundle) { return Object.freeze({ __resKey: 1, id: id, path: path, type: type, bundle: bundle, request: L[id] }); }\n'
            '  var ResKeys = {\n' + body + ('\n' if body else '') + '  };\n'
            '  ResKeys.BUNDLES = Object.freeze(' + bundles + ');\n' + groups +
            '  Object.freeze(ResKeys);\n'
            "  if (typeof module === 'object' && module && module.exports) module.exports = ResKeys;\n"
            '  if (root) root.ResKeys = ResKeys;\n'
            "})(typeof globalThis !== 'undefined' ? globalThis : (typeof window !== 'undefined' ? window : this));\n")


def game_scripts(assets, out):
    for p in sorted(assets.rglob('*')):
        if p.suffix not in ('.js', '.ts') or not p.is_file() or p.name.endswith('.d.ts') or p == out:
            continue
        rel = p.relative_to(assets).parts
        if any(part in SKIP_SCRIPT_DIRS for part in rel[:-1]) or p.name in ('ResLoader.js', 'ResKeys.js', 'ResKeys.ts'):
            continue
        yield p


def scan_code(project, out, ids):
    assets = project / 'assets'
    dangling, raw = [], []
    for p in game_scripts(assets, out):
        try:
            text = p.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        text_nc = re.sub(r'/\*[\s\S]*?\*/', lambda m: '\n' * m.group(0).count('\n'), text)
        for n, line in enumerate(text_nc.splitlines(), 1):
            code = line.split('//', 1)[0]
            for m in REF.finditer(code):
                ident = m.group(1) or m.group(3)
                if ident not in ids and ident not in TABLE_PROPS:
                    dangling.append({'file': p.relative_to(project).as_posix(), 'line': n, 'id': ident})
            if RAW.search(code):
                raw.append({'file': p.relative_to(project).as_posix(), 'line': n, 'code': code.strip()[:160]})
    return dangling, raw


def main(argv=None):
    ap = argparse.ArgumentParser(description='Generate ResKeys from the Cocos project resources (P12).')
    ap.add_argument('--project', required=True)
    ap.add_argument('--engine', type=int, choices=(2, 3))
    ap.add_argument('--out')
    ap.add_argument('--check', action='store_true', help='write nothing; exit 1 when the table on disk is stale')
    ap.add_argument('--strict', action='store_true', help='direct engine loads in game code fail (new games)')
    ap.add_argument('--json', action='store_true', help='print the report as JSON')
    a = ap.parse_args(argv)
    project = Path(a.project).resolve()
    engine = a.engine or detect_engine(project)
    out = Path(a.out).resolve() if a.out else project.joinpath(*OUT_DIR, 'ResKeys.ts' if engine == 3 else 'ResKeys.js')
    table = build(project, engine)
    text = render(table)
    current = out.read_text(encoding='utf-8') if out.is_file() else None
    stale = current != text
    if not a.check and stale:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(text.encode('utf-8'))
    ids = {e['id'] for e in table['entries']}
    dangling, raw = scan_code(project, out, ids)
    failed = bool(dangling) or (a.check and stale) or (a.strict and bool(raw))
    try:
        out_name = out.relative_to(project).as_posix()
    except ValueError:
        out_name = str(out)
    report = {'schema': SCHEMA, 'engine': engine, 'out': out_name,
              'keys': len(table['entries']), 'bundles': table['bundles'], 'stale': stale,
              'home_keys': sum(1 for e in table['entries'] if e.get('group') == 'home') if table.get('groups') else None,
              'written': (not a.check) and stale, 'dangling': dangling, 'raw_loads': raw,
              'skipped': table['skipped'], 'warnings': table['warnings'], 'ok': not failed}
    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        print('ResKeys: %d keys in %s (%s)' % (report['keys'], report['out'],
              ('stale, run without --check' if a.check else 'written') if stale else 'up to date'))
        for d in dangling:
            print('  DANGLING %s:%d ResKeys.%s is not in the table (file deleted or renamed?)' % (d['file'], d['line'], d['id']))
        for r in raw:
            print('  %s %s:%d direct engine load, use Res.request(ResKeys.<id>): %s' % ('RAW-LOAD' if a.strict else 'info raw-load', r['file'], r['line'], r['code']))
        for w in table['warnings']:
            print('  warning ' + w)
        if table['skipped']:
            print('  skipped %d files (scenes, scripts, Spine, ...); --json lists them' % len(table['skipped']))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
