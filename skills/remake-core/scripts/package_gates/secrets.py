"""Source hygiene in the upload package (简化.11.6, Saul 2026-11-04: 91 SLS11's .git held an account and password;
「同类问题要让它直接出不了包」). Every package entry runs it through package_gates.run (make_tiktok_zip.py,
build_checked_zip.py, check_package.py), on the bytes that go into the ZIP. Same rules as source_hygiene.py:

    H1_vcs_ide_in_package   a .git / .svn / .hg / .bzr / CVS or .idea / .vscode / .vs / .history / .fleet folder
                            (or __MACOSX) is in the package.
    H2_credentials_in_package   app_desc.txt, .env, a signing key / certificate, or a text file with a credential line
                            (密码 / 账号 / password / appSecret ... = value).
Both block for new and legacy games and for both boards: nobody may ship them.
"""
from . import finding

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import source_hygiene as H  # noqa: E402


def check(view):
    found = H.scan_items((name, data) for name, data in view.files.items())
    out = []
    if found['vcs_ide']:
        out.append(finding('H1_vcs_ide_in_package', 'block', 'version control / IDE data in the package (%s): build from a '
                           'clean copy (cocos-game-to-english/scripts/unpack_source.py) and write the package again'
                           % ', '.join(v['path'] for v in found['vcs_ide'][:5]), found['vcs_ide']))
    if found['secrets']:
        out.append(finding('H2_credentials_in_package', 'block', 'credentials in the package (%s): remove the files or '
                           'blank the values in the project, rebuild and write the package again'
                           % '; '.join('%s %s' % (s['path'], s['why']) for s in found['secrets'][:5]), found['secrets']))
    return out
