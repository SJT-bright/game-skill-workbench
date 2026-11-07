"""Resolve actual authoring and compiled Cocos runtime textures for Spine atlases."""
import json
from pathlib import PurePosixPath
import re

from tiktok_finalize_steps.policy import decode_uuid

COMPILED = re.compile(r"(?:export-\d+/)?(?:assets|subpackages)/[^/]+/native/[^/]+/([0-9a-f-]{36})(?:\.[^.]+)?\.atlas$")
IMPORT = re.compile(r"(?:export-\d+/)?(?:assets|subpackages)/[^/]+/import/[^/]+/[^/]+\.json$")
CONFIG = re.compile(r"(?:export-\d+/)?(?:assets|subpackages)/[^/]+/config(?:\.[a-z0-9]+)?\.json$")
TEXTURE_EXT = ('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.pvr', '.pkm', '.astc')

class Unknown(ValueError):
    """A reference cannot be attributed without guessing."""

def need(ok, message):
    if not ok:
        raise Unknown(message)

def only(items, description):
    items = list(items)
    need(len(items) == 1, f"{description}: expected one, got {len(items)}")
    return items[0]

def asset_uuid(value):
    if not isinstance(value, str):
        return None
    base, sep, suffix = value.partition('@')
    uid = decode_uuid(base)
    if uid is None or (sep and not re.fullmatch(r'[a-zA-Z0-9_-]+', suffix)):
        return None
    return uid + sep + suffix


def key_value_pairs(values, numeric=False):
    need(isinstance(values, list) and len(values) % 2 == 0, 'malformed config pairs')
    keys = [int(k) if numeric and isinstance(k, str) and k.isdigit() else k for k in values[::2]]
    result = dict(zip(keys, values[1::2]))
    need(len(result) * 2 == len(values), 'ambiguous duplicate keys in config pairs')
    return result

def config_file(config, group, uid, key, ext):
    directory = config[group + 'Base']
    need(re.fullmatch(r'[a-zA-Z0-9_-]+', directory), 'unsupported asset base')
    version = key_value_pairs(config.get('versions', {}).get(group, []), 'types' in config).get(key)
    need(version is None or re.fullmatch(r'[a-zA-Z0-9_-]+', version), 'invalid asset version')
    file = uid + (f'.{version}' if version else '') + ext
    return str(PurePosixPath(config['config_file']).parent / directory / uid[:2] / file)

def at(rows, index, description):
    need(type(index) is int and 0 <= index < len(rows), 'invalid ' + description)
    return rows[index]

def bundle_uuid(bundle, key):
    return asset_uuid(key if 'types' not in bundle else at(bundle['uuids'], key, 'UUID index'))


def asset_paths(bundle):
    for key, record in bundle['paths'].items():
        if 'types' in bundle:
            yield int(key), record[0], at(bundle['types'], record[1], 'asset type')
        else:
            yield key, record[0], record[1]


def key_for_uuid(bundle, uid):
    return only((i if 'types' in bundle else value for i, value in enumerate(bundle['uuids'])
                 if asset_uuid(value) == uid), f'UUID {uid} in {bundle["name"]}')


def location(bundle, index, bundles):
    seen = set()
    uid = bundle_uuid(bundle, index)
    need(uid is not None, 'invalid asset UUID')
    while True:
        name = bundle['name']
        need(name not in seen, 'bundle redirect cycle')
        seen.add(name)
        redirect = key_value_pairs(bundle['redirect'], 'types' in bundle).get(index)
        if redirect is None:
            return bundle, index, uid
        if isinstance(redirect, str) and redirect.isdigit():
            redirect = int(redirect)
        owner = at(bundle['deps'], redirect, 'redirect index')
        bundle = only((b for b in bundles if b['name'] == owner), 'redirected bundle ' + str(owner))
        index = key_for_uuid(bundle, uid)

def import_record(bundle, index, uid, files):
    packed = [(pack, entries) for pack, entries in bundle['packs'].items()
              if index in entries or ('types' in bundle and str(index) in entries)]
    if not packed:
        path = config_file(bundle, 'import', uid, index, '.json')
        return path, json.loads(files[path]), None
    pack, entries = only(packed, 'import pack membership')
    need(re.fullmatch(r'[a-zA-Z0-9_-]+', pack), 'invalid import pack name')
    path = config_file(bundle, 'import', pack, pack, '.json')
    slot = only((i for i, key in enumerate(entries) if key == index or
                 ('types' in bundle and key == str(index))), 'import pack position')
    return path, json.loads(files[path]), (slot, len(entries))


def compact_asset(payload, packed):
    if packed:
        slot, count = packed
        need(len(payload) == 6 and len(payload[5]) == count, 'unsupported compact import pack')
        payload = payload[:5] + at(payload[5], slot, 'packed asset slot')
    need(isinstance(payload, list) and len(payload) == 11 and payload[0] == 1,
         'unsupported compact import version')
    return payload


def skeleton_dependency(payload, packed, page_names):
    data = compact_asset(payload, packed)
    instances = data[5]
    root = instances[-1]
    root = (~root if root < 0 else root) if type(root) is int else 0
    obj = at(instances, root, 'asset root')
    mask = at(data[4], obj[0], 'object mask')
    cls = at(data[3], mask[0], 'object class')
    need(isinstance(cls, list) and cls[0] == 'sp.SkeletonData', 'import is not Spine SkeletonData')
    need(len(mask) == len(obj) + 1, 'unexpected Spine mask layout')
    keys = [at(cls[1], prop, 'property index') for prop in mask[1:-1]]
    props = dict(zip(keys, obj[1:]))
    names, textures = props['textureNames'], props['textures']
    need(isinstance(names, list) and isinstance(textures, list) and len(names) == len(textures),
         'invalid Spine texture slots')
    need(len(set(names)) == len(names) and set(names) == set(page_names), 'Spine pages do not match texture slots')
    pos = keys.index('textures') + 1
    need(pos >= mask[-1] and at(cls, mask[pos] + cls[2], 'texture property type') == 3,
         'unsupported Spine asset reference representation')
    uuids = {}
    for name, ref in zip(names, textures):
        key = at(data[9], ref, 'Spine dependency key')
        need(type(key) is int and key < 0 and ~key == len(uuids), 'unexpected Spine dependency assignment')
        target = at(data[10], ref, 'Spine dependency UUID')
        if type(target) is int:
            target = at(data[1], target, 'shared UUID')
        need(asset_uuid(target) is not None, 'invalid Spine texture UUID')
        uuids[name] = target
    return props['_atlasText'], uuids

def custom_asset(payload, packed, kind):
    data = compact_asset(payload, packed)
    instances, custom_types = data[5:7]
    need(len(instances) == 2 and instances[-1] == -1 and isinstance(custom_types, list)
         and len(custom_types) == 1 and at(data[3], custom_types[0], 'custom asset class') == kind,
         'unsupported compact ' + kind)
    return instances[0]


def packed_row(imported, packed, kind):
    if not (packed and isinstance(imported, dict) and imported.get('type') == kind):
        return None
    slot, count = packed
    rows = imported['data']
    if isinstance(rows, str) and kind == 'cc.Texture2D':
        rows = rows.split('|')
    need(isinstance(rows, list) and len(rows) == count, 'invalid ' + kind + ' pack length')
    return rows[slot]


def image_asset_format(bundle, index, uid, files):
    _, imported, packed = import_record(bundle, index, uid, files)
    row = packed_row(imported, packed, 'cc.ImageAsset')
    if row is not None:
        imported, packed = row, None
    image = custom_asset(imported, packed, 'cc.ImageAsset')
    need(isinstance(image, dict), 'unsupported ImageAsset data')
    return image.get('fmt')


def texture_path(bundle, index, uid, files, bundles):
    _, imported, packed = import_record(bundle, index, uid, files)
    settings = packed_row(imported, packed, 'cc.Texture2D')
    if settings is None:
        settings = custom_asset(imported, packed, 'cc.Texture2D')
    if isinstance(settings, str):
        fmt = settings.split(',', 1)[0]
    else:
        # Cocos 3 Texture2D stores sampler settings and ImageAsset mipmap UUIDs.
        if isinstance(settings, dict):
            mipmaps = settings.get('mipmaps')
        else:
            need(isinstance(settings, list) and len(settings) == 2, 'unsupported Texture2D data')
            mipmaps = settings[1]
        need(isinstance(mipmaps, list) and len(mipmaps) == 1, 'unsupported Spine texture mipmap layout')
        image_uid = asset_uuid(mipmaps[0])
        need(image_uid is not None, 'invalid ImageAsset UUID')
        bundle, index, uid = location(bundle, key_for_uuid(bundle, image_uid), bundles)
        fmt = image_asset_format(bundle, index, uid, files)
    need(isinstance(fmt, str) and fmt.isdigit(), 'unsupported texture variant or extension')
    ext = at(TEXTURE_EXT, int(fmt), 'texture extension')
    need(ext in ('.png', '.jpg', '.jpeg', '.webp'), 'texture uses an unreviewable format')
    path = config_file(bundle, 'native', uid, index, ext)
    need(path in files, 'missing runtime texture ' + path)
    return path, uid


def _namespace(path):
    return path.split('/', 1)[0] if path.startswith('export-') else ''


def _bundle_configs(files, namespace):
    for path in files:
        if CONFIG.fullmatch(path) and _namespace(path) == namespace:
            cfg = json.loads(files[path])
            if isinstance(cfg, dict) and all(field in cfg for field in
                                              ('name', 'uuids', 'paths', 'packs', 'redirect', 'deps')) and (
                    'types' in cfg or cfg.get('debug') is True):
                yield dict(cfg, config_file=path)


def bundle_configs(files):
    return {name: list(_bundle_configs(files, name))
            for name in sorted({_namespace(path) for path in files if CONFIG.fullmatch(path)})}


def missing_runtime_atlases(files, configs):
    """A bundle can still contain the inline atlas after the standalone sidecar is deleted."""
    for bundles in configs.values():
        for bundle in bundles:
            paths = list(asset_paths(bundle))
            skeleton_paths = {path for _, path, kind in paths if kind == 'sp.SkeletonData'}
            for key, logical, kind in paths:
                if logical not in skeleton_paths or kind != 'cc.Asset':
                    continue
                owner, index, uid = location(bundle, key, bundles)
                path = config_file(owner, 'native', uid, index, '.atlas')
                if path not in files:
                    yield path


def resolve_source(files, atlas, page_names):
    """Use the author page path and verify imported Spine UUIDs when Creator 2 records them."""
    import posixpath
    page_paths = {}
    need(bool(page_names) and len(set(page_names)) == len(page_names), 'missing or repeated Spine page names')
    meta_path = str(PurePosixPath(atlas).with_suffix('.json.meta'))
    meta = json.loads(files[meta_path].read_bytes()) if meta_path in files else {}
    textures = meta.get('textures') if meta.get('importer') == 'spine' else None
    parent = posixpath.dirname(atlas)
    for page_name in page_names:
        page = page_name.replace('\\', '/')
        path = posixpath.normpath(posixpath.join(parent, page))
        need(not page.startswith('/') and not re.match(r'^[a-zA-Z]:', page) and path.startswith('assets/'),
             'invalid author texture path ' + page)
        if path not in files and textures is not None:
            # Creator 2.4 also accepts a basename alias. Only use it when the importer UUID verifies it.
            path = posixpath.join(parent, posixpath.basename(page))
        need(path in files, 'missing author texture ' + path)
        page_paths[page_name] = path
    if textures is not None:
        actual = []
        for path in page_paths.values():
            meta_file = files.get(path + '.meta')
            need(meta_file is not None, 'missing author texture meta ' + path)
            actual.append(decode_uuid(json.loads(meta_file.read_bytes()).get('uuid')))
        expected = [decode_uuid(value) for value in textures] if isinstance(textures, list) else []
        need(None not in actual and actual == expected,
             'Spine importer texture UUIDs do not match atlas pages: ' + atlas)
    return page_paths


def resolve(files, atlas, page_names, configs=None):
    """Resolve exact runtime bindings in one Cocos build. Unattributed inputs raise Unknown."""
    try:
        if configs is None:
            configs = bundle_configs(files)
        bundles = configs.get(_namespace(atlas), [])
        need(bool(bundles), 'no supported Cocos bundle config')
        stem = COMPILED.fullmatch(atlas)
        need(stem is not None, 'unsupported compiled Spine atlas path')
        stem = stem.group(1)
        owning_bundle, logical = only(
            ((bundle, logical) for bundle in bundles for key, logical, kind in asset_paths(bundle)
             if kind == 'cc.Asset' and bundle_uuid(bundle, key) == stem
             and config_file(bundle, 'native', stem, key, '.atlas') == atlas),
            'atlas owner and logical path')
        skeleton_index = only(
            (key for key, path, kind in asset_paths(owning_bundle)
             if path == logical and kind == 'sp.SkeletonData'), 'SkeletonData matching atlas logical path')
        owner, index, uid = location(owning_bundle, skeleton_index, bundles)
        packed_file, packed, pack_slot = import_record(owner, index, uid, files)
        inline_atlas, pages = skeleton_dependency(packed, pack_slot, page_names)
        need(inline_atlas.encode('utf-8') == files[atlas], 'runtime Spine atlas text differs from the standalone atlas')
        result = {}
        for page, target in pages.items():
            texture_uid = asset_uuid(target)
            texture_index = only(
                (key for key, _, kind in asset_paths(owning_bundle)
                 if kind == 'cc.Texture2D' and bundle_uuid(owning_bundle, key) == texture_uid),
                'declared Texture2D UUID matching Spine dependency')
            tex_owner, tex_idx, tex_uid = location(owning_bundle, texture_index, bundles)
            png, image_uid = texture_path(tex_owner, tex_idx, tex_uid, files, bundles)
            result[page] = {'texture': png, 'texture_uuid': tex_uid, 'image_uuid': image_uid}
        return result
    except (ValueError, TypeError, AttributeError, KeyError, IndexError) as error:
        if isinstance(error, Unknown):
            raise
        raise Unknown(f'malformed Cocos reference: {error}') from error
