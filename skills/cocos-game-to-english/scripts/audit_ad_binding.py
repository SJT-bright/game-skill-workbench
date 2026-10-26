#!/usr/bin/env python3
"""Read-only public ad-config to Native ZIP binding check; not runtime/ownership acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile
from verify_native_zip import verify


def reject_private(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower().replace('_', '').replace('-', '') in {'clientsecret', 'password', 'accesstoken', 'refreshtoken'}:
                raise ValueError('Private credential field is not allowed in public game configuration')
            reject_private(child)
    elif isinstance(value, list):
        for child in value:
            reject_private(child)


def public(value, name):
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError('Missing or malformed public value: ' + name)
    if value.lower() in {'test', 'placeholder', 'your_app_id', 'your_client_key', 'your_ad_unit_id', 'your_placement_id', 'xxx'} or '<' in value:
        raise ValueError('Placeholder public value: ' + name)
    return value


def no_duplicate_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Duplicate JSON key in public configuration')
        value[key] = item
    return value


def audit(config_path, native_zip):
    config_path, native_zip = Path(config_path), Path(native_zip)
    config = json.loads(config_path.read_text(), object_pairs_hook=no_duplicate_keys)
    if not isinstance(config, dict):
        raise ValueError('Public configuration must be a JSON object')
    reject_private(config)
    app = public(config.get('appId'), 'appId')
    key = public(config.get('clientKey'), 'clientKey')
    default = public(config.get('rewardedPlacementId'), 'rewardedPlacementId')
    values = {'appId': app, 'clientKey': key, 'rewardedPlacementId': default}
    for name, value in config.items():
        if name.endswith('PlacementId') and name != 'rewardedPlacementId':
            values[name] = public(value, name)
    slots = config.get('rewardedPlacements', [])
    if not isinstance(slots, list):
        raise ValueError('rewardedPlacements must be an array')
    for i, slot in enumerate(slots):
        if not isinstance(slot, dict):
            raise ValueError('Each rewarded placement must be an object')
        if 'id' in slot and 'placementId' in slot and slot['id'] != slot['placementId']:
            raise ValueError('Conflicting id and placementId in the same slot')
        values['rewardedPlacements[' + str(i) + ']'] = public(slot.get('id', slot.get('placementId')), 'rewardedPlacements[' + str(i) + ']')
    if slots and default not in {values['rewardedPlacements[' + str(i) + ']'] for i in range(len(slots))}:
        raise ValueError('Default rewarded placement is missing from the declared slot list')
    structure = verify(native_zip, expected_app_id=app)
    hits = {}
    with zipfile.ZipFile(native_zip) as z:
        js = {n: z.read(n).decode('utf-8') for n in z.namelist() if n.endswith('.js') and not n.endswith('/')}
        for name, value in values.items():
            literal = re.compile(r"(?P<q>['\"])" + re.escape(value) + r"(?P=q)")
            matches = [n for n, text in js.items() if literal.search(text)]
            if not matches:
                raise ValueError('Public value not found in compiled JavaScript: ' + name)
            hits[name] = matches
    return {
        'status': 'static_ad_config_binding_passed',
        'config': str(config_path.resolve()), 'config_sha256': hashlib.sha256(config_path.read_bytes()).hexdigest(),
        'native_zip': str(native_zip.resolve()), 'native_sha256': structure['sha256'],
        'appId': app, 'placement_count': len(set(value for name, value in values.items() if name not in {'appId', 'clientKey'})),
        'root_app_matches': True, 'compiled_public_occurrences': hits,
        'native_structure_and_crc': True,
        'not_verified': ['Portal/Runtime selected App', 'Client Key and placement ownership/Active',
                         'SDK call reachability and reward business mapping', 'real phone/IAA', 'upload/release'],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--native-zip', type=Path, required=True)
    p.add_argument('--report', type=Path)
    args = p.parse_args()
    try:
        result = audit(args.config, args.native_zip)
    except (ValueError, OSError, UnicodeError, zipfile.BadZipFile, KeyError) as error:
        result = {'status': 'failed', 'reason': str(error)}
    output = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output)
    print(output, end='')
    return 0 if result['status'] == 'static_ad_config_binding_passed' else 2


if __name__ == '__main__':
    sys.exit(main())
