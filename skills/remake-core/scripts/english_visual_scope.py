"""Explicit, per-capture preservation of an English game's original art templates.

This is a visual scope only. It never supplies a gameplay/economy maintenance
receipt, changes a threshold, or suppresses text, contrast, overlap or clipping.
"""
import hashlib
import json
from pathlib import Path

RULES = {
    'home_original_composition': {'home'},
    'result_original_button_layout': {'result_win', 'result_fail'},
    'result_original_density': {'result_win', 'result_fail'},
    'original_popup_illustration': {'result_win', 'result_fail'},
    'original_background_pattern': None,
    'original_loading_spinner': {'loading'},
    'original_popup_extent': None,
}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def ref(value, base):
    if not isinstance(value, dict) or not value.get('path') or not value.get('sha256'):
        raise ValueError('visual scope needs path and SHA-256 for every reference')
    p=Path(value['path']); p=(p if p.is_absolute() else base/p).resolve()
    if not p.is_file() or sha(p)!=value['sha256']:
        raise ValueError('visual scope evidence changed or missing: '+str(p))
    return p

def node_names(paths):
    names=set()
    def walk(x):
        if isinstance(x, dict):
            if x.get('__type__')=='cc.Node': names.add(x.get('_name'))
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    for p in paths: walk(read(p))
    return names

def validate(path, project, binding, dumps):
    p=Path(path).resolve(); base=p.parent; project=Path(project).resolve(); doc=read(p)
    if doc.get('schema')!='english_original_visual_scope.v1': raise ValueError('English original visual scope schema required')
    if not isinstance(binding,dict) or any(not binding.get(k) for k in ('source_sha256','native_tree_sha256','web_tree_sha256','build_tag')) or doc.get('binding')!=binding:
        raise ValueError('visual scope must match the current complete binding')
    if Path(doc.get('project','')).resolve()!=project: raise ValueError('visual scope project mismatch')
    if (project/'docs/board.txt').read_text().strip()!='localize' or (project/'docs/art-style.txt').read_text().strip()!='original':
        raise ValueError('visual scope only applies to localize with original art')
    from audit_mobile_input import snapshot
    if snapshot(project)[2]!=binding['source_sha256']: raise ValueError('visual scope source is stale')
    from check_known_issues import tree_sha
    if tree_sha(project/'build/bytedance')!=binding['native_tree_sha256'] or tree_sha(project/'build/web-mobile')!=binding['web_tree_sha256']:
        raise ValueError('visual scope compiled artifacts are stale')
    auth=doc.get('authorization',[])
    if not isinstance(auth,list) or not auth: raise ValueError('specific user authorization is required')
    for item in auth:
        a=ref(item,base); excerpt=item.get('excerpt','')
        if not isinstance(excerpt,str) or len(excerpt.strip())<8 or excerpt not in a.read_text(encoding='utf-8'):
            raise ValueError('authorization excerpt must appear verbatim in its record')
    original=Path(doc.get('original_project','')).resolve()
    if original==project or not (original/'assets').is_dir(): raise ValueError('distinct original source project required')
    rows=doc.get('pages'); seen=set(); validated=[]
    if not isinstance(rows,list) or not rows: raise ValueError('explicit page mappings required')
    available={Path(d['_file']).resolve():d for d in dumps}
    for row in rows:
        screen=row.get('screen'); rules=row.get('rules',[])
        if not screen or screen in seen: raise ValueError('unique explicit screen mapping required')
        seen.add(screen)
        if not rules or len(rules)!=len(set(rules)) or not set(rules)<=set(RULES): raise ValueError('unknown or duplicate visual rule')
        if len(str(row.get('reason','')).strip())<20: raise ValueError('specific original preservation rationale required')
        originals=[ref(x,base) for x in row.get('original_refs',[])]
        if not originals or any(not x.is_relative_to(original/'assets') or x.suffix not in {'.prefab','.fire','.scene'} for x in originals):
            raise ValueError('original serialized prefab/scene evidence required')
        anchors=row.get('anchors',[])
        if not anchors or not set(anchors)<=node_names(originals): raise ValueError('anchors not found in original UI')
        pairs=row.get('dumps',[]); sizes=set(); pages=[]
        if len(pairs)<2: raise ValueError('both real portrait captures required')
        for pair in pairs:
            f=ref(pair,base); raw=read(f); d=available.get(f)
            if d is None or d.get('nodes')!=raw.get('nodes'): raise ValueError('mapped capture not in unchanged audit input')
            if raw.get('tool')!='ui_dump' or raw.get('schema')!=1 or raw.get('producer')!='ego_page.dump_ui' or raw.get('truncated') or raw.get('errors'):
                raise ValueError('complete official ui_dump required')
            if raw.get('screen')!=screen: raise ValueError('mapped screen mismatch')
            for rule in rules:
                if RULES[rule] is not None and raw.get('purpose') not in RULES[rule]: raise ValueError('rule purpose mismatch: '+rule)
            if not set(anchors)<={n.get('name') for n in raw['nodes']}: raise ValueError('original UI anchor missing from current capture')
            size=(raw.get('page',{}).get('width'),raw.get('page',{}).get('height'))
            if not all(type(v) in (int,float) and v>0 for v in size) or size[1]<=size[0] or size in sizes: raise ValueError('two distinct portrait ratios required')
            sizes.add(size)
            shot=ref(pair.get('screenshot'),base); actual=Path(raw.get('screenshot','')); actual=(actual if actual.is_absolute() else f.parent/actual).resolve()
            if shot!=actual: raise ValueError('screenshot must belong to this same capture')
            pages.append({'path':str(f),'sha256':sha(f),'screenshot':str(shot),'screenshot_sha256':sha(shot),'viewport':list(size)})
        frames=row.get('original_frames',[])
        if 'original_background_pattern' in rules and not frames: raise ValueError('original background pattern needs exact source image identity')
        for frame in frames:
            current=ref(frame.get('current'),base); old=ref(frame.get('original'),base)
            if not current.is_relative_to(project/'assets') or not old.is_relative_to(original/'assets') or current.suffix.lower()!='.png' or old.suffix.lower()!='.png' or sha(current)!=sha(old):
                raise ValueError('retained original PNG identity mismatch')
            if not frame.get('frame') or current.stem!=frame['frame']: raise ValueError('explicit original frame name required')
        if 'original_popup_extent' in rules:
            baselines=row.get('extent_baseline',[])
            if len(baselines)!=len(pairs):raise ValueError('popup extent needs a prior unchanged panel capture at each ratio')
            covered=set()
            for baseline in baselines:
                current=Path(baseline.get('current_dump','')).resolve()
                if current not in {Path(x['path']) for x in pages} or current in covered:raise ValueError('extent baseline current capture mismatch')
                covered.add(current)
                old=read(ref(baseline.get('baseline_dump'),base));now=read(current);key=baseline.get('panel_path')
                old_nodes=[n for n in old.get('nodes',[]) if n.get('path')==key];new_nodes=[n for n in now.get('nodes',[]) if n.get('path')==key]
                if old.get('tool')!='ui_dump' or old.get('errors') or old.get('truncated') or len(old_nodes)!=1 or len(new_nodes)!=1 or old_nodes[0].get('screen')!=new_nodes[0].get('screen') or old.get('page')!=now.get('page'):
                    raise ValueError('popup extent changed from the actual retained baseline')
        validated.append({'screen':screen,'rules':rules,'captures':pages,'anchors':anchors,'original_refs':row['original_refs'],'original_frames':frames,'reason':row['reason']})
    return {'schema':doc['schema'],'path':str(p),'sha256':sha(p),'pages':validated,
            'boundary':'Only named original template/art-style demands on the listed exact captures. Actual English text, contrast, glyph overlap, clipping, visibility, controls and gameplay/economy gates remain active.'}

def rules_for(mapping,d):
    if not mapping:return set()
    path=str(Path(d['_file']).resolve())
    return {rule for row in mapping['pages'] if row['screen']==d.get('screen') and any(x['path']==path for x in row['captures']) for rule in row['rules']}
