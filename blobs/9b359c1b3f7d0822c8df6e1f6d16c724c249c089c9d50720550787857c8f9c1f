"""Synthetic historical receipt files used only by legacy readback tests."""
from pathlib import Path
import datetime as dt
from art_receipt import (STATUSES, SCHEMA, DISPLAY_SCHEMA, _sha, _tool_hashes, _write_json, _keep_record,
                         display_fingerprints, engine, image_fingerprints, images_digest, receipt_path)

def write_fixture(project, status, report=None, report_path=None, note=None):
    """Write the receipt for the CURRENT images of `project`. report = art_check's art-check.json content."""
    if status not in STATUSES:
        raise ValueError('art receipt status must be one of %s' % (STATUSES,))
    project = Path(project).resolve()
    images = image_fingerprints(project)
    report = report or {}
    rpath = Path(report_path).resolve() if report_path else None
    receipt = {
        'kind': 'art-receipt', 'schema': SCHEMA, 'status': status, 'passed': status == 'pass',
        'project': str(project), 'engine': engine(project),
        'art_check': {'report': str(rpath) if rpath else None,
                      'report_sha256': _sha(rpath.read_bytes()) if rpath and rpath.is_file() else None,
                      'status': report.get('status'), 'checked': report.get('checked'), 'failed': report.get('failed'),
                      'time': report.get('time'), 'board': report.get('board')},
        'tools': _tool_hashes(),
        'created': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
        'images_count': len(images), 'images_sha256': images_digest(images),
        'art_check_images_sha256': images_digest(images), 'images': images, 'carried': []}
    display = display_fingerprints(project)            # 生成时预防 R4M2: text, fonts, layout
    receipt.update(display_schema=DISPLAY_SCHEMA, display=display, display_sha256=images_digest(display))
    from art_production import fingerprint as production_fingerprint
    try:
        production = production_fingerprint(project)
        if production is not None:
            receipt['production_binding'] = production
    except ValueError as exc:
        if status == 'pass':
            raise ValueError('cannot write a passing art receipt: ' + str(exc)) from exc
        receipt['production_binding_error'] = str(exc)
    if isinstance(report.get('base_generated'), dict):
        receipt['base_generated'] = report['base_generated']      # v7.8 H8 / H10 summary (art_records.summary)
    if report.get('capture_round', {}).get('ready'):
        receipt['capture_round'] = {k:report['capture_round'][k] for k in ('round','version','dumps','origin_hash')}
        if status == 'pass':
            receipt['capture_round']['artifact_hash'] = report['capture_round']['artifact_hash']
    if isinstance(report.get('value_presentation'), dict):
        receipt['value_presentation'] = report['value_presentation']
    if isinstance(report.get('maintenance_mapping'), dict):
        receipt['maintenance_mapping'] = report['maintenance_mapping']
        # Provenance only: status still follows all blocking rows; no blanket pass or waiver.
    if isinstance(report.get('english_visual_scope'),dict):receipt['english_visual_scope']=report['english_visual_scope']
    # R4Q3 (补查3 第 3 组): which rows still need fixing, the original-style verdict and Saul's keep record
    receipt['blocking_rows'] = [r.get('check') for r in report.get('rows') or [] if isinstance(r, dict)
                                and r.get('status') == '需处理'][:40]
    if isinstance(report.get('original_style'), dict):
        receipt['original_style'] = report['original_style']
    keep = _keep_record(project)
    if keep:
        receipt['keep_original_style'] = keep
    if note:
        receipt['note'] = note
    _write_json(receipt_path(project), receipt)
    return receipt


