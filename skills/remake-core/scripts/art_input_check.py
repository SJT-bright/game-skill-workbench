"""Read-only Web capture preflight. No pixels analysed and no ART receipt written."""
from collections import Counter
import json
from pathlib import Path
import time


def verify_capture(project, dumps, build, board, inventory, capture_build=None, require_web=False):
    """Web dumps keep their Web identity even when asset checks use a Native build."""
    from art_round_check import run as capture_check
    web_records = any(d.get('tool') == 'ui_dump' and
                      d.get('producer') in {'chrome_touch.dump_ui', 'ego_page.dump_ui'}
                      for d in inventory['records'])
    required = board == 'localize' and (
        require_web or web_records or capture_build or
        build and (build / 'index.html').is_file() or
        (project / 'docs/art/capture-plan.json').is_file() or
        (project / '.tiktok-kit/art-rounds/current.json').is_file())
    if not required:
        return None
    web = capture_build or (build if build and (build / 'index.html').is_file() else None)
    if not web or not (web / 'index.html').is_file():
        return {'ready': False, 'error': 'Web 截图缺本轮导出：请给 --capture-build WEB_EXPORT；'
                '--build 为 Web 导出时可直接使用。Native 资源目录不能证明 Web 截图版本。'}
    return capture_check('verify', project, web, dumps)


def inspect(project, dumps, build, board, capture_build=None):
    # Reuse the full check's inventory and provenance rules; never make a second
    # relaxed definition of a complete/current screenshot set.
    from art_check import capture_inventory
    inventory = capture_inventory(project, dumps)
    errors = list(inventory['errors'])
    groups = Counter(str(p.parent.relative_to(dumps)) for p in inventory['dump_files'])
    unmatched = sorted(str(p.relative_to(dumps)) for p in dumps.rglob('*ui-dump.json'))
    if unmatched:
        errors.append('采集命名未被正式入口识别：' + ', '.join(unmatched[:12]))
    provenance = verify_capture(project, dumps, build, board, inventory, capture_build, require_web=True)
    if provenance is not None and (not provenance.get('ready') or 'error' in provenance):
        errors.append('截图版本未核准：' + provenance.get('error', '状态或视口需重拍'))
    return {
        'ready': not errors, 'errors': errors,
        'dump_count': len(inventory['dump_files']), 'screenshot_count': len(inventory['shots']),
        'capture_directories': dict(sorted(groups.items())),
        'observed': inventory['observed'], 'listed': inventory['listed'],
        'viewports': inventory['viewports'], 'capture_round': provenance,
        'version_verified': bool(provenance and provenance.get('ready') and 'error' not in provenance),
        'notes': ['目录数量只帮助核对采集范围，不据此判断版本；历史沿用由 capture_round 的原始依赖证据决定。']
    }


def run(project, dumps, build, out, board=None, capture_build=None):
    import feature_policy
    started = time.monotonic()
    project, dumps, out = Path(project).resolve(), Path(dumps).resolve(), Path(out).resolve()
    build = Path(build).resolve() if build else None
    capture_build = Path(capture_build).resolve() if capture_build else None
    if not (project / 'assets').is_dir():
        raise ValueError('not a Cocos project')
    if out.is_relative_to(project) or out.exists() and any(out.iterdir()):
        raise ValueError('use a fresh output directory outside project')
    board, board_source = feature_policy.board_of(project, board)
    result = inspect(project, dumps, build, board or 'remake', capture_build)
    result.update(tool='art_input_preflight', scope='capture-inputs-only',
                  board=board or 'remake', board_source=board_source,
                  resource_build=str(build) if build else None,
                  capture_build=str(capture_build) if capture_build else
                      (str(build) if build and (build / 'index.html').is_file() else None),
                  visual_checks_run=0, visual_passed=None, receipt_written=False,
                  elapsed_seconds=round(time.monotonic() - started, 6))
    out.mkdir(parents=True, exist_ok=True)
    (out / 'input-preflight.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['ready'] else 1
