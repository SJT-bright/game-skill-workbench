#!/usr/bin/env python3
"""(Re)build KIT_FINGERPRINTS.json for the package gate K6_kit_module_old (v7.8, 总表 B30 C).

  python3 -B tools/build_kit_fingerprints.py           # write ../KIT_FINGERPRINTS.json
  python3 -B tools/build_kit_fingerprints.py --check   # exit 1 when the file is not what the manifest gives now

Run it after any change to assets/tiktok-platform/*.js in KIT_MANIFEST.json. Keep the text of every previous version
listed in previous_sha256 as tools/kit_versions/<Module>/<sha256>.txt (byte-identical to the old file; .txt so no tool
treats it as a script). A previous hash without its text is listed under previous_without_text and can only be
recognised by "module present, current-only names absent".
"""
import argparse
import json
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT.parent.parent / 'scripts'))
from package_gates import kit_versions  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args(argv)
    manifest = json.loads((KIT / 'KIT_MANIFEST.json').read_text(encoding='utf-8'))
    text = json.dumps(kit_versions.build(manifest), ensure_ascii=False, indent=1, sort_keys=True) + '\n'
    target = KIT / 'KIT_FINGERPRINTS.json'
    if a.check:
        same = target.is_file() and target.read_text(encoding='utf-8') == text
        print('KIT_FINGERPRINTS.json ' + ('is current' if same else 'is stale: run tools/build_kit_fingerprints.py'))
        return 0 if same else 1
    target.write_text(text, encoding='utf-8')
    print('wrote', target)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
