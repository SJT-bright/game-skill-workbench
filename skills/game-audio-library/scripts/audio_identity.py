"""Portable source identities used for audio selection and per-machine history.

Explicit decoded-audio/family IDs come from the verified library index. This
module does not infer acoustic similarity from filenames or modify audio files.
"""
from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

from common import LIB


def relative_asset_path(path, library=LIB) -> str:
    """Return a library-relative POSIX key, refusing outside/escaping paths."""
    value = str(path).replace('\\', '/')
    root = Path(library).expanduser().resolve()
    candidate = Path(value).expanduser()
    if re.match(r'^[A-Za-z]:/', value) and not candidate.is_absolute():
        raise ValueError('Foreign absolute audio path needs import rebasing: ' + value)
    if not candidate.is_absolute():
        if '..' in PurePosixPath(value).parts:
            raise ValueError('Audio path escapes the library')
        candidate = root / candidate
    try:
        relative = candidate.resolve().relative_to(root)
    except ValueError:
        raise ValueError('Audio path is outside the current library: ' + value)
    if not relative.parts:
        raise ValueError('An audio asset path is required')
    return relative.as_posix()



def identity(row: dict) -> str:
    if row.get('audio_id'):
        return str(row['audio_id'])
    if row.get('file_sha256'):
        return 'file-sha256:' + str(row['file_sha256'])
    if row.get('asset_id'):
        return str(row['asset_id'])
    return 'path:' + relative_asset_path(row['path'])


def normalized_stem(row: dict) -> str:
    value = unquote(str(row.get('name') or PurePosixPath(str(row.get('path', '')).replace('\\', '/')).stem)).casefold()
    # Keep track numbers. Only recognized presentation/format suffixes are removed.
    value = re.sub(r'\.(?:wav|ogg|mp3|flac|m4a|aiff?|opus)$', '', value)
    value = re.sub(r'(?:[\s_\-]*\((?:wav|ogg|mp3|flac|loop(?:ing|ed)?|seamless)\)|[\s_\-]+(?:wav|ogg|mp3|flac|loop(?:ing|ed)?|seamless)(?:[\s_\-]*\d+)?)$', '', value)
    if row.get('kind') in {'bgm', 'jingle'}:
        value = re.sub(r'[\s_\-]+no[\s_\-]+vocals?$', '', value)
    if row.get('kind') == 'sfx':
        value = re.sub(r'[\s_\-]+(?:var(?:iant)?[\s_\-]*)?\d{1,3}$', '', value)
    return re.sub(r'[^\w]+', '-', value).strip('-')


def family(row: dict) -> str:
    if row.get('family_id'):
        value = str(row['family_id'])
        if value.startswith('family:') and row.get('kind') in {'bgm', 'jingle'}:
            value = re.sub(r'[-_ ]+no[-_ ]+vocals?$', '', value, flags=re.I)
        return value
    source, pack = str(row.get('source', '')), str(row.get('pack', ''))
    parents = ()
    if row.get('path'):
        try:
            parts = PurePosixPath(relative_asset_path(row['path'])).parts
        except ValueError:
            # Lookup of a migrated index can precede path rebasing. Keep only the
            # portable RAW suffix; never put another computer's home in an ID.
            suffix = str(row['path']).replace('\\', '/').split('/raw/', 1)
            parts = PurePosixPath('raw/' + suffix[1]).parts if len(suffix) == 2 else ()
        prefix = ('raw', source, *PurePosixPath(pack).parts)
        parents = parts[len(prefix):-1] if parts[:len(prefix)] == prefix else parts[:-1]
    return 'family:' + '/'.join((source, pack, *parents, normalized_stem(row)))
