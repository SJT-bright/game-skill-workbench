"""Refuse this project's local ad simulator in upload payloads, including renamed copies.

This is a known-tool residue check, not a general proof that arbitrary code contains no mocks.
"""
from pathlib import PurePosixPath

MARKERS = (b'__adSimulator', b'__local_ad_simulator', b'__ad-simulator',
           b'SIM_BUSY_OR_USED')
TOOL_FILES = {'ad-simulator.js', 'ad-simulator.min.js'}


def check_entry(name, data):
    if PurePosixPath(name).name.casefold() in TOOL_FILES:
        raise ValueError('Local ad simulator must not ship in the TikTok upload package: ' + name)
    # Scan bytes regardless of suffix: a renamed script or enabled/disabled branch still must not ship.
    for marker in MARKERS:
        if marker in data:
            raise ValueError('Local ad simulator residue (' + marker.decode() + ') in upload package: ' + name)


def enforce_files(files):
    for name, data in files.items():
        check_entry(name, data)
    return {'local_ad_simulator_absent': True, 'scope': 'known local simulator files and byte markers'}
