"""Mandatory byte-size gate shared by upload writers; no gameplay CI."""
import json
from verify_native_zip import TIKTOK_MAIN, TIKTOK_TOTAL, TIKTOK_INDEPENDENT, safe_name

def enforce(sizes, game):
    total = sum(sizes.values())
    if total > TIKTOK_TOTAL:
        raise ValueError(f'Uncompressed total package {total} bytes exceeds the limit {TIKTOK_TOTAL} bytes')
    if not isinstance(game, dict) or not isinstance(game.get('subpackages', []), list):
        raise ValueError('game.json subpackages must be an array')
    roots=[];normal={};independent={}
    for sub in game.get('subpackages', []):
        root=safe_name(sub['root']).as_posix().rstrip('/')+'/'
        roots.append(root)
        count=sum(n for p,n in sizes.items() if p.startswith(root))
        (independent if sub.get('independent') is True else normal)[root]=count
        if sub.get('independent') is True and count>TIKTOK_INDEPENDENT:
            raise ValueError(f'Independent subpackage {root} {count} bytes exceeds {TIKTOK_INDEPENDENT}')
    main=sum(n for p,n in sizes.items() if not any(p.startswith(root) for root in roots))
    if main>TIKTOK_MAIN:
        raise ValueError(f'Uncompressed main package {main} bytes exceeds the limit {TIKTOK_MAIN} bytes')
    return {'total_bytes':total,'main_bytes':main,'normal_subpackages':normal,'independent_subpackages':independent}

def enforce_files(files):
    # Reject total before parsing config or opening an output file.
    total=sum(len(data) for data in files.values())
    if total>TIKTOK_TOTAL:
        raise ValueError(f'Uncompressed total package {total} bytes exceeds the limit {TIKTOK_TOTAL} bytes')
    return enforce({p:len(data) for p,data in files.items()},json.loads(files['game.json'].decode('utf-8-sig')))
