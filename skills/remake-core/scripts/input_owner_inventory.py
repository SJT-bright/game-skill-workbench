"""Shared explicit-input inventory; no execution or gameplay verdict.

Pure source classification is cached in-process by source/tool fingerprints.
Unknown input syntax cannot be used to attest non-applicability.
"""
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from collections import OrderedDict

HERE = Path(__file__).resolve().parent
_CACHE = OrderedDict()
_WORDS = re.compile(r'\b(?:getID|touchId|pointerId|TOUCH_START|touchstart|pointerdown|onTouchStart|onPointerDown|eval|Function)\b')


def inspect_sources(paths):
    """Batch uncached candidates; consumers still bind current file hashes."""
    results = [None] * len(paths)
    pending = []
    for index, value in enumerate(paths):
        path = Path(value)
        raw = path.read_bytes()
        try:
            source = raw.decode('utf-8-sig')
        except UnicodeError:
            results[index] = {'status': 'unresolved', 'reason': 'input source is not valid UTF-8'}
            continue
        if not _WORDS.search(source) and '\\u' not in source and '\\x' not in source:
            results[index] = {'status': 'none', 'reason': 'no explicit input-ownership vocabulary'}
            continue
        pending.append((index, path.suffix, raw, source))
    if not pending:
        return results
    scanner = HERE / 'scan_input_ownership.cjs'
    parser = HERE / 'vendor/acorn.cjs'
    node = shutil.which('node')
    if not node:
        for index, *_ in pending:
            results[index] = {'status': 'unresolved', 'reason': 'Node.js required to distinguish executable input from source text'}
        return results
    tool = hashlib.sha256(scanner.read_bytes() + parser.read_bytes() + Path(__file__).read_bytes()).hexdigest()
    work = {}
    for index, suffix, raw, source in pending:
        key = (node, suffix, hashlib.sha256(raw).hexdigest(), tool)
        if key in _CACHE:
            _CACHE.move_to_end(key)
            results[index] = copy.deepcopy(_CACHE[key])
        else:
            work.setdefault(key, {'indexes': [], 'source': source, 'extension': suffix})['indexes'].append(index)
    if not work:
        return results
    try:
        run = subprocess.run([node, str(scanner)], input=json.dumps({'sources': [
            {'source': row['source'], 'extension': row['extension']} for row in work.values()]}),
                             capture_output=True, text=True, timeout=20)
        data = json.loads(run.stdout)
        if run.returncode or not isinstance(data, list) or len(data) != len(work) or any(
                row.get('schema') != 'input_ownership_inventory.v1' or row.get('status') not in {'none', 'owner', 'unresolved'}
                for row in data):
            raise ValueError('invalid source inventory result')
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        for row in work.values():
            for index in row['indexes']:
                results[index] = {'status': 'unresolved', 'reason': 'input inventory unavailable: ' + str(error)}
        return results
    # Cache source analysis, never a button/lifecycle/business pass.
    for (key, row), result in zip(work.items(), data):
        if result['status'] != 'unresolved':
            _CACHE[key] = copy.deepcopy(result)
        for index in row['indexes']:
            results[index] = copy.deepcopy(result)
    while len(_CACHE) > 128:
        _CACHE.popitem(last=False)
    return results


def inspect_source(path):
    return inspect_sources([path])[0]
