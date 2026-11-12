"""Reuse proven preview behavior after the server's fresh byte-for-byte entry readback.

Port numbers are transport addresses, not game versions. HTTP entry readback always
runs in serve_preview; cached visual/interaction evidence belongs to the content and
viewport, keeps its original capture time, and never claims a new screenshot.
"""
from pathlib import Path
import json
import check_ledger as C

def rule_files(kind,conditions=None):
    assets=Path(__file__).resolve().parent.parent/'assets'
    # These are the actual response-injected scripts. Their bytes can fix an
    # input failure or invalidate an old pass without changing the game export.
    files=[Path(__file__).with_name('serve_preview.py'),Path(__file__),
           assets/'preview-touch-bridge.js']
    if kind=='home':
        files.append(Path(__file__).with_name('preview_audio_startup.py'))
    if (conditions or {}).get('ad_simulator') is True:
        files.append(assets/'ad-simulator.js')
    if kind=='ad-response':
        scripts=Path(__file__).resolve().parents[2]/'cocos-game-check/package-check/scripts'
        runtime=scripts/'runtime_regression'
        # trial_link's real Python judge, transport and explicit JS imports.
        files.extend([scripts/'runtime_regression.py',scripts/'ego_test_page.mjs',
                      runtime/'suites/trial_link.mjs',runtime/'suites/trial_link.json',
                      runtime/'lib.mjs',runtime/'layout_rules.mjs',runtime/'engine_adapter.mjs',runtime/'session.mjs'])
    if any(not p.is_file() for p in files):raise C.NeedsScope('试玩判定器或其依赖缺失，不能沿用旧记录')
    return files

def run(project,kind,export,conditions,fn,adapter=None):
    if not project:raise C.NeedsScope('用户试玩须给 --project，检查记录不能写进游戏导出目录')
    ledger=C.Ledger(project)
    root=lambda:{'preview':C.manifest(export),'adapter':C.json_manifest(json.loads(Path(adapter).read_text()) if adapter else {})}
    roots=root()
    try:
        p=ledger.prepare('preview.'+kind,roots,conditions,C.tool_fingerprint(rule_files(kind,conditions)),label='试玩入口 / '+kind,domain='startup' if kind=='home' else 'platform')
        def execute():
            value=list(fn())
            if kind=='ad-response' and value[0]=='pass':
                info=value[2] if len(value)>2 and isinstance(value[2],dict) else {}
                if info.get('not_applicable') is not True:
                    raw=info.get('raw_files') or []
                    summary=info.get('summary') or {}
                    if (summary.get('passed') is not True or not raw
                            or any(not Path(p).is_file() for p in raw)):
                        raise C.NeedsScope('广告试玩缺少本次真实结果原件，不能缓存为通过')
            return {'passed':value[0]=='pass','value':value}
        result,proof=ledger.execute(p,execute,lambda r:r['passed'],
            verify_inputs=lambda:C.select_inputs(root(),p['scope']))
        value=result['value']
        if proof['reused']:
            value=list(value);value[1]='沿用原试玩检查（%s）；本次只读回服务和同版文件，未重拍或重测：%s'%(proof['original_at'],value[1])
            if len(value)>2 and isinstance(value[2],dict):value[2]=dict(value[2],reused_from=proof['source_key'],original_at=proof['original_at'])
        return tuple(value)
    finally:ledger.close()
