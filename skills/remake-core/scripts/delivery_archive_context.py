"""One delivery's freshly inspected ZIP payload; never a cross-delivery pass cache.

Only inspect_delivery_archive creates the private context. The existing canonical
verifier still runs all its rules once, over the CRC-checked immutable payload and
unchanged central-directory metadata. Later consumers recheck archive and original
writer-receipt bytes, then consume that same result. Standalone checks stay fresh.
"""
import copy
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
import zipfile

_TOKEN = object()


def _sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


class _PayloadReader:
    def __init__(self, token, infos, payload):
        if token is not _TOKEN:
            raise ValueError('trusted delivery payload required')
        self._infos, self._payload = infos, payload

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        return False

    def infolist(self):
        # Keep all directory attributes and duplicate-entry metadata. A dict of
        # filenames alone must never replace the verifier's structure checks.
        return [copy.copy(info) for info in self._infos]

    def read(self, name):
        key = name.filename if isinstance(name, zipfile.ZipInfo) else name
        if key not in self._payload:
            raise ValueError('fresh delivery payload member missing: ' + str(key))
        return self._payload[key]


class _DeliveryArchive:
    __slots__ = ('_token', '_archive', '_sha', '_payload', '_infos', '_receipt',
                 '_receipt_bytes', '_receipt_sha', '_result', '_verifying', '_closed')

    def __init__(self, token, archive, inspection, payload, infos, receipt):
        if token is not _TOKEN:
            raise ValueError('fresh inspection factory required')
        if (inspection.get('passed') is not True or inspection.get('platform') != 'tiktok'
                or inspection.get('writer_receipt', {}).get('entry') != 'official'
                or inspection.get('crc_verified') is not True
                or inspection.get('tiktok_cli', {}).get('passed') is not True
                or not receipt.get('data') or not payload):
            raise ValueError('complete fresh delivery inspection required')
        self._token = token
        self._archive = Path(archive).resolve()
        self._sha = inspection['sha256']
        self._payload = MappingProxyType(dict(payload))
        self._infos = tuple(copy.copy(info) for info in infos)
        self._receipt = Path(receipt['path']).resolve()
        self._receipt_bytes = receipt['data']
        self._receipt_sha = receipt['sha256']
        self._result, self._verifying, self._closed = None, False, False
        self._check_active_path(archive)
        self._check_receipt()

    def _check_active_path(self, archive):
        if self._token is not _TOKEN or self._closed:
            raise ValueError('delivery archive context is not active')
        if Path(archive).resolve() != self._archive:
            raise ValueError('delivery archive context belongs to another path')

    def _check_receipt(self):
        if self._receipt.is_symlink() or not self._receipt.is_file():
            raise ValueError('original writer receipt is missing or linked')
        try:
            data = self._receipt.read_bytes()
        except OSError as error:
            raise ValueError('original writer receipt is missing') from error
        if data != self._receipt_bytes or hashlib.sha256(data).hexdigest() != self._receipt_sha:
            raise ValueError('original writer receipt changed during delivery')

    def check_current(self, archive):
        self._check_active_path(archive)
        if _sha_file(self._archive) != self._sha:
            raise ValueError('ZIP changed after the fresh delivery inspection')
        self._check_receipt()
        return self._sha

    def verified(self, archive, app_id=None, *, files=None):
        self._check_active_path(archive)
        self._check_receipt()
        if self._result is None:
            import verify_native_zip as verifier
            self._verifying = True
            try:
                result = verifier.verify(archive, expected_app_id=app_id, _archive_context=self)
            finally:
                self._verifying = False
            if (result.get('entry') != 'official' or result.get('sha256') != self._sha
                    or Path(result['receipt']).resolve() != self._receipt):
                raise ValueError('fresh canonical writer evidence does not match delivery context')
            expected = {name: hashlib.sha256(data).hexdigest() for name, data in self._payload.items()}
            if result['file_sha256'] != expected:
                raise ValueError('canonical verification differs from fresh ZIP member bytes')
            self._check_receipt()
            self._result = copy.deepcopy(result)
        else:
            self.check_current(archive)
        result = copy.deepcopy(self._result)
        if app_id is not None and result.get('appId') != app_id:
            raise ValueError('Root App ID does not match the requested target')
        if files is not None:
            actual = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
            if actual != result['file_sha256']:
                raise ValueError('final ZIP differs from actual Native input paths/bytes')
        return result

    def close(self):
        self._closed = True
        self._result = None


def _require_context(context):
    if type(context) is not _DeliveryArchive or context._token is not _TOKEN:
        raise ValueError('trusted fresh delivery archive context required')
    return context


def _payload_reader(context, archive, archive_sha256):
    context = _require_context(context)
    context._check_active_path(archive)
    context._check_receipt()
    if archive_sha256 != context._sha:
        raise ValueError('ZIP changed before canonical delivery verification')
    if not context._verifying:
        raise ValueError('delivery payload is only for its canonical verification')
    return _PayloadReader(_TOKEN, context._infos, context._payload)


def consume_delivery_archive(context, archive, app_id=None, *, files=None):
    """Internal consumer; dictionaries/flags cannot create a verified context."""
    return _require_context(context).verified(archive, app_id, files=files)


def delivery_payload(context, archive):
    context = _require_context(context)
    context._check_active_path(archive)
    if context._result is None:
        raise ValueError('canonical delivery verification has not completed')
    return dict(context._payload)


def delivery_receipt(context, archive):
    context = _require_context(context)
    context._check_active_path(archive)
    context._check_receipt()
    if context._result is None:
        raise ValueError('canonical delivery verification has not completed')
    return json.loads(context._receipt_bytes.decode('utf-8'))


def check_delivery_archive_current(context, archive):
    return _require_context(context).check_current(archive)


def inspect_delivery_archive(archive, feedback=None):
    """Fresh final file/size/CLI/receipt gate on every new delivery invocation."""
    from upload_size_gate import inspect_final_zip
    payload, receipt = {}, {}
    inspection = inspect_final_zip(archive, 'tiktok', feedback,
                                   _verified_files=payload, _verified_receipt=receipt)
    if not inspection['passed']:
        return inspection, None
    # No member bytes are read again here. Preserve the real complete ZIP
    # metadata so the canonical verifier retains its directory/attribute rules.
    before = _sha_file(archive)
    if before != inspection['sha256']:
        raise ValueError('ZIP changed before delivery context metadata capture')
    with zipfile.ZipFile(archive) as source:
        infos = source.infolist()
    if _sha_file(archive) != before:
        raise ValueError('ZIP changed during delivery context metadata capture')
    return inspection, _DeliveryArchive(_TOKEN, archive, inspection, payload, infos, receipt)
