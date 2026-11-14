"""Exact formal34 default-storage observation compatibility after Creator1 branch additions.

This preserves original keys/time/raw evidence and never runs a game/runner. Current
validators still rejudge every obligation. The helper and both caller bodies are
sealed in a non-circular chain; unknown changes cannot borrow a predecessor.
"""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CURRENT_CALLER_BODIES = {'audit_native_storage_contract.py': 'f500209c736459ebc80797b1de64e9b1485e9f24df1cf59713bbe3177368094d', 'storage_scoped_reuse.py': 'f8910b838d3ada560545ef3099eed8ce1970bfb442b5b08122ca342287bb7e16'}
FORMAL34_TOOLS = {'storage_scoped_reuse.py': '8336095512bb86c98b24934485fe7ab59a4fb3538233392e220b3d36e5e62dcd', 'audit_native_storage_contract.py': '96eb89de2c4ce38c705d87f0b5f500d31199962a3511e6fc25ba6bed506d830d', 'maintenance_scope.py': '8068266f64616022dd4a47489c5aacd7aee847ad0cf265748f804867960e908a', 'startup_storage_consumers.py': '3c832d4be8447f87e177cf27102d6374bf2b28ec684f389ca4ac68608d454ed8', 'scan_storage_consumers.cjs': 'b31e37f94db9c47d0646fbfcf5f9a394e99e27b3a28ec8b1d5c9b995ea9f4805', 'startup_business_contract.py': 'c8600b73ea380b841e5d7d9065b4053a35c76a7dff8bf1ac8f6b9d42173ee007', 'numeric_snapshot_contract.py': '8b94ca6a0fc899c0e7401a1cb6df413d561d1f295436aff9c36dda0d6951fabe', 'vendor/acorn.cjs': 'fdb08546776ec6228b03e8d02b40d4ab3255bae5f401adba7ff5dad927ac5c9c'}
CONTRACT = ('audit_native_storage_contract.py', 'maintenance_scope.py',
            'startup_business_contract.py', 'startup_storage_consumers.py',
            'scan_storage_consumers.cjs', 'vendor/acorn.cjs')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _line(raw, name):
    prefix = (name + ' = ').encode()
    lines = [line for line in raw.splitlines(keepends=True) if line.startswith(prefix)]
    if len(lines) != 1:
        raise ValueError('storage compatibility: ambiguous seal slot')
    return lines[0]


def _read(path, observed):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('storage compatibility: missing or linked dependency: '+str(path))
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    if path.is_symlink() or tuple(getattr(before, k) for k in fields) != tuple(getattr(after, k) for k in fields):
        raise ValueError('storage compatibility: dependency changed during read: '+str(path))
    identity = _sha(raw)
    if path in observed and observed[path] != identity:
        raise ValueError('storage compatibility: dependency changed while reading: '+str(path))
    observed[path] = identity
    return raw


def _unchanged(observed):
    for path, identity in observed.items():
        if _sha(_read(path, dict(observed))) != identity:
            raise ValueError('storage compatibility: dependency changed before decision: '+str(path))


def guard(expected_sha, expected_body):
    observed = {}
    raw = _read(Path(__file__), observed)
    metadata = _line(raw, 'CURRENT_CALLER_BODIES')
    if metadata != ('CURRENT_CALLER_BODIES = ' + repr(CURRENT_CALLER_BODIES) + '\n').encode():
        raise ValueError('storage compatibility: malformed caller anchors')
    body = _sha(raw.replace(metadata, b'CURRENT_CALLER_BODIES = {}\n', 1))
    if _sha(raw) != expected_sha or body != expected_body:
        raise ValueError('storage compatibility: unknown helper body or seal')
    actual = {}
    for name, anchor in CURRENT_CALLER_BODIES.items():
        source = _read(HERE / name, observed)
        seal = _line(source, 'STORAGE_OVERLAY_COMPAT_SHA256')
        body_slot = _line(source, 'STORAGE_OVERLAY_COMPAT_BODY_SHA256')
        if (seal != ("STORAGE_OVERLAY_COMPAT_SHA256 = '"+expected_sha+"'\n").encode()
                or body_slot != ("STORAGE_OVERLAY_COMPAT_BODY_SHA256 = '"+expected_body+"'\n").encode()
                or _sha(source.replace(seal, b"STORAGE_OVERLAY_COMPAT_SHA256 = '"+b'0'*64+b"'\n", 1)) != anchor):
            raise ValueError('storage compatibility: unknown current default caller')
        actual[name] = _sha(source)
    if set(actual) != {'storage_scoped_reuse.py', 'audit_native_storage_contract.py'}:
        raise ValueError('storage compatibility: incomplete caller anchors')
    for name, identity in FORMAL34_TOOLS.items():
        if name in actual:
            continue
        path = HERE / name
        if _sha(_read(path, observed)) != identity:
            raise ValueError('storage compatibility: unchanged dependency changed: '+name)
        actual[name] = identity
    _unchanged(observed)
    return actual


def _current():
    source = (HERE / 'audit_native_storage_contract.py').read_bytes()
    values = [ast.literal_eval(_line(source, name).split(b' = ', 1)[1].decode('ascii')) for name in
              ('STORAGE_OVERLAY_COMPAT_SHA256', 'STORAGE_OVERLAY_COMPAT_BODY_SHA256')]
    return guard(*values)


def _default(report, trace, native=None):
    if (not isinstance(report, dict) or not isinstance(trace, dict) or report.get('profile') is not None
            or trace.get('schema') not in ('native_storage_trace.v1', 'native_storage_trace.v2', 'native_storage_trace.v3')):
        return False
    # A genuine Creator1 export cannot borrow an old default-backend receipt,
    # even if somebody manually gives it a non-Creator profile label.
    root = Path(native or report.get('native', ''))
    observed, missing = {}, []
    for name in ('cocos2d-js-min.js', 'cocos2d-js.js'):
        path = root / name
        if path.is_symlink():
            return False
        if not path.exists():
            missing.append(path)
            continue
        if not path.is_file():
            return False
        raw = _read(path, observed)
        if len(raw) == 1579751 and _sha(raw) == '12b92d9871b3376e50fe09f1291f8ca949b4a50ca936a5681fb226b50ec3dee4':
            return False
    _unchanged(observed)
    if any(path.exists() or path.is_symlink() for path in missing):
        raise ValueError('storage compatibility: engine context changed while deciding')
    return True


def formal34_tools(report, trace, native):
    _current()
    result = dict(FORMAL34_TOOLS) if _default(report, trace, native) else None
    _current()
    return result


def scope_tools(previous, current, report, trace, native):
    actual = _current()
    result = (_default(report, trace, native) and previous == FORMAL34_TOOLS
              and current == actual)
    _current()
    return result


def execution_receipt(report, trace, expected):
    actual = _current()
    if not _default(report, trace):
        return False
    previous = report.get('execution_receipt', {}).get('identity')
    if not isinstance(previous, dict):
        return False
    names = CONTRACT + (('numeric_snapshot_contract.py',) if trace.get('numeric_snapshot_encoding') else ())
    old = {name: FORMAL34_TOOLS[name] for name in names}
    new = {name: actual[name] for name in names}
    result = (previous.get('contract_files') == old and expected.get('contract_files') == new
            and {k:v for k,v in previous.items() if k != 'contract_files'} ==
                {k:v for k,v in expected.items() if k != 'contract_files'})

    _current()
    return result
