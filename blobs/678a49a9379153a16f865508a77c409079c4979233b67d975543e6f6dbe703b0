"""Cocos 3 SystemJS evidence adapter; preserves the generic business/real-Canvas gate."""
from pathlib import Path
import hashlib,json
PROFILE='cocos3_systemjs_native_v1'
def validate(report,native,data,need,ref):
    required={'game.js','application.js','web-adapter.js','engine-adapter.js','src/settings.json','cocos-js/cc.js'}
    inputs={r.get('relative_path') for r in report.get('inputs',[])}
    need(required<=inputs,'Cocos3 actual entry, both adapters, settings and engine identities required')
    engines=[p for p in native.glob('cocos-js/_virtual_cc-*.js') if p.is_file()]
    # Creator can emit a monolithic System.register cc.js or a cc.js facade plus one virtual engine.
    # Both retain the same exact Function#toString/source identity requirement below.
    if not engines:
        main = native/'cocos-js/cc.js'
        if main.is_file() and b'System.register' in main.read_bytes() and main.stat().st_size > 100000:
            engines = [main]
    need(len(engines)==1 and engines[0].relative_to(native).as_posix() in inputs,'Cocos3 exact bundled engine required')
    if engines:
        source=engines[0].read_bytes()
        for name in ('game_run','renderer'):
            text=data.get('engine_identity',{}).get('functions',{}).get(name,'')
            need(isinstance(text,str) and len(text)>30 and text.encode() in source,'Cocos3 '+name+' observed function must match actual engine source')
    need(data.get('phase_order')==['entry','adapter','renderer','scene'],'Cocos3 actual entry/adapter/WebGL/scene order required')
    controls=report.get('controls',{})
    for name in ('known_bad','reintroduced_defect','parser_type_mismatch'):
        p=ref(controls.get(name,{}),name+' Cocos3 execution')
        if not p:continue
        raw=json.loads(p.read_text());need(raw.get('passed') is False,name+' must be an observed failure')
        trace=raw.get('trace',{});trace_path=ref(raw.get('raw_trace',{}),name+' original trace');need(trace_path is not None and json.loads(trace_path.read_text())==trace,name+' trace must equal immutable raw execution');need(bool(trace.get('raw',{}).get('errors')) or trace.get('error'),name+' must retain the actual error/failed recovery')
        need(raw.get('base_native_tree_sha256')==report.get('native_tree_sha256'),name+' current-base binding missing')
        need(bool(raw.get('native_tree_sha256')) and raw.get('native_tree_sha256')!=report.get('native_tree_sha256'),name+' distinct control tree required')
        need(raw.get('runner_sha256')==report.get('runner',{}).get('sha256'),name+' same reviewed runner required')
        if name=='known_bad':
            need(raw.get('provenance',{}).get('kind')=='preserved_original_export' and bool(raw.get('provenance',{}).get('sha256')),'Cocos3 preserved original control identity required')
        else:need(bool(raw.get('mutation')),name+' actual current-tree mutation required')
        if name=='parser_type_mismatch':
            need(any(c.get('sharedScreen') and c.get('returned') and str(c.get('type')).startswith('webgl') for c in trace.get('raw',{}).get('contexts',[])),'Cocos3 parser negative must reach actual WebGL')
            need('unpack' in json.dumps(trace).lower() or 'deserialize' in json.dumps(trace).lower(),'Cocos3 parser negative must retain actual parse failure')
