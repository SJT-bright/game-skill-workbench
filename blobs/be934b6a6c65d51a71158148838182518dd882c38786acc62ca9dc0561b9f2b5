"""Replay declared ink reservations or containment on captured Cocos UI. All coordinates are normalized."""
import json
import re
from pathlib import Path
from PIL import Image
from ui_region_probe import measure
from math import isfinite

def box(rect):
    if not isinstance(rect,(list,tuple)) or len(rect)!=4 or any(type(v) not in (int,float) or not isfinite(v) for v in rect):
        raise ValueError('invalid screen rectangle')
    x,y,w,h=rect
    if w<=0 or h<=0: raise ValueError('empty capture rectangle')
    return x,y,w,h

def lookup_node(nodes,path):
    if not isinstance(path,str) or not path:raise ValueError('exact node path required')
    if not isinstance(nodes,list) or any(not isinstance(n,dict) for n in nodes):raise ValueError('invalid node collection')
    matches=[n for n in nodes if n.get('path')==path]
    if len(matches)!=1:raise ValueError('absent or ambiguous node: '+path)
    return matches[0]

def lookup(nodes,path):
    node=lookup_node(nodes,path)
    return box(node.get('unclipped_screen',node.get('screen')))

def number(value, name, positive=False):
    if type(value) not in (int,float) or not isfinite(value) or (positive and value<=0):
        raise ValueError('invalid '+name)
    return value

def validate_display_budget(case):
    """Validate an optional, independent design budget; never derive it from live owner size."""
    if 'display_budget' not in case:return None
    budget=case['display_budget']
    if not isinstance(budget,dict) or budget.get('unit')!='css_px':
        raise ValueError('display budget requires css_px unit')
    for key in ('viewport_width','viewport_height'):
        number(case.get(key),key,positive=True)
    entries=budget.get('nodes')
    if not isinstance(entries,list) or not entries:raise ValueError('display budget nodes missing')
    paths=set()
    for entry in entries:
        if not isinstance(entry,dict):raise ValueError('invalid display budget node')
        path=entry.get('path');frame=entry.get('frame');size=entry.get('expected_css')
        if not isinstance(path,str) or not path.strip() or path in paths:
            raise ValueError('display budget requires unique exact node paths')
        paths.add(path)
        if not isinstance(frame,str) or not frame.strip():raise ValueError('display budget frame identity missing')
        if not isinstance(size,(list,tuple)) or len(size)!=2:raise ValueError('display budget needs both CSS axes')
        for value in size:number(value,'expected CSS size',positive=True)
        px=number(entry.get('tolerance_css_px',1),'CSS tolerance')
        ratio=number(entry.get('tolerance_ratio',0),'ratio tolerance')
        if not 0<=px<=2 or not 0<=ratio<1:raise ValueError('display budget tolerance out of bounds')
        if any(max(px,value*ratio)>2 for value in size):
            raise ValueError('effective display tolerance exceeds 2 CSS px')
        if any(max(px,value*ratio)>=value for value in size):
            raise ValueError('display tolerance must be smaller than each expected axis')
    return entries

def display_checks(nodes,case,doc):
    entries=validate_display_budget(case)
    if entries is None:return []
    if not isinstance(doc,dict):raise ValueError('display budget needs capture metadata')
    for key in ('viewport','page'):
        meta=doc.get(key)
        if not isinstance(meta,dict):raise ValueError('display budget missing '+key)
        for axis in ('width','height'):
            if number(meta.get(axis),key+' '+axis,positive=True)!=case['viewport_'+axis]:
                raise ValueError('display budget '+key+' differs from declared viewport')
    _,_,cw,ch=box(doc.get('canvas_css'))
    # The dump's normalized node coordinates are relative to canvas, not page or PNG pixels.
    # A clipped visible fragment must not conceal the larger original node.
    rows=[]
    for entry in entries:
        node=lookup_node(nodes,entry['path'])
        comps=node.get('comps')
        sprite=comps.get('sprite') if isinstance(comps,dict) else None
        if not isinstance(sprite,dict) or sprite.get('frame')!=entry['frame']:
            raise ValueError('display budget sprite frame mismatch: '+entry['path'])
        frame_size=sprite.get('frame_size')
        if not isinstance(frame_size,(list,tuple)) or len(frame_size)!=2:
            raise ValueError('display budget loaded frame geometry missing: '+entry['path'])
        for value in frame_size:number(value,'frame dimension',positive=True)
        opacity=number(node.get('opacity'),'effective node opacity',positive=True)
        if opacity>1 or node.get('visible') is False or node.get('active') is False:
            raise ValueError('display budget node not visible: '+entry['path'])
        alpha=number(sprite.get('alpha',255),'sprite alpha',positive=True)
        if alpha>255:raise ValueError('invalid sprite alpha')
        _,_,w,h=lookup(nodes,entry['path'])
        actual=[w*cw,h*ch];expected=entry['expected_css']
        tolerance=[max(entry.get('tolerance_css_px',1),v*entry.get('tolerance_ratio',0)) for v in expected]
        rows.append(dict(id=entry['path'],rule='display_budget',frame=entry['frame'],
                         actual_css=[round(v,6) for v in actual],expected_css=list(expected),
                         tolerance_css=tolerance,
                         passed=all(abs(a-e)<=t+1e-6 for a,e,t in zip(actual,expected,tolerance))))
    return rows

def inspect(im,nodes,case,doc=None):
    x,y,w,h=lookup(nodes,case['owner'])
    if im.width!=case['expected_width'] or im.height!=case['expected_height']:
        raise ValueError('unexpected capture dimensions')
    rows=[]
    if 'inside' in case:
        l,t,r,b=case['inside']
        if not (0<=l<r<=1 and 0<=t<b<=1):raise ValueError('invalid design safe area')
        if not case.get('children'):raise ValueError('no child specified')
        safe=(x+l*w,y+t*h,x+r*w,y+b*h)
        for name in case['children']:
            a,c,d,e=lookup(nodes,name)
            overflow=max((safe[0]-a)*im.width,(safe[1]-c)*im.height,(a+d-safe[2])*im.width,(c+e-safe[3])*im.height)
            rows.append(dict(id=name,overflow_px=round(max(0,overflow),2),passed=overflow<=1))
    if 'horizontal_gap' in case:
        gap = case['horizontal_gap']
        minimum = gap['min_css_px']
        width = case['viewport_width']
        if type(minimum) not in (int, float) or not isfinite(minimum) or minimum <= 0:
            raise ValueError('positive minimum gap in CSS pixels required')
        if type(width) not in (int, float) or not isfinite(width) or width <= 0:
            raise ValueError('positive CSS viewport width required')
        if gap['left'] == gap['right']:
            raise ValueError('two distinct gap nodes required')
        left_x, _, left_width, _ = lookup(nodes, gap['left'])
        right_x, _, _, _ = lookup(nodes, gap['right'])
        distance = (right_x - left_x - left_width) * width
        rows.append(dict(id='horizontal_gap', gap_css_px=round(distance, 3),
                         min_css_px=minimum, passed=distance + 1e-6 >= minimum))

    if 'pixel_regions' in case:
        rows.extend(measure(im,(x*im.width,y*im.height,w*im.width,h*im.height),case['pixel_regions']))
    rows.extend(display_checks(nodes,case,doc))
    if not rows:raise ValueError('empty slot check')
    return rows

def selected_cases(config, case_ids):
    """Resolve explicit first-piece slot IDs, never capture IDs or guessed names."""
    cases = json.loads(Path(config).read_text())['cases']
    if not isinstance(cases, list) or not cases:
        raise ValueError('required cases missing')
    if not isinstance(case_ids, (list, tuple)) or not case_ids or any(
            not isinstance(value, str) or not value or value != value.strip() for value in case_ids):
        raise ValueError('first-piece case IDs must be explicit and nonempty')
    if len(set(case_ids)) != len(case_ids):
        raise ValueError('duplicate first-piece case ID')
    declared = {}
    for case in cases:
        identifier = case.get('id') if isinstance(case, dict) else None
        if not isinstance(identifier, str) or not identifier or identifier != identifier.strip() or identifier in declared:
            raise ValueError('invalid or duplicate declared slot case ID')
        declared[identifier] = case
    unknown = [value for value in case_ids if value not in declared]
    if unknown:
        raise ValueError('unknown first-piece slot case: ' + ', '.join(unknown))
    selected = [declared[value] for value in case_ids]
    for case in selected:
        if not isinstance(case.get('screen'), str) or not case['screen'].strip():
            raise ValueError('first-piece slot requires an exact screen')
        for axis in ('width', 'height'):
            number(case.get('viewport_' + axis), 'first-piece viewport ' + axis, positive=True)
    return selected, [case['id'] for case in cases if case['id'] not in case_ids]


def matches_case(case, doc, exact_viewport=False):
    selector = case.get('capture_case')
    if selector is not None:
        # Several real captures may share one page/viewport (initial Home and
        # Home after earned rewards). Bind a declared case to the producer's
        # exact dump + paired screenshot, without changing screen identity.
        if (not isinstance(selector,str) or not re.fullmatch(r'[A-Za-z0-9_-]+',selector)
                or Path(doc.get('_file','')).name != 'capture-ui-dump-'+selector+'.json'
                or doc.get('screenshot') != selector+'.png'):
            return False
        paired=Path(doc['_file']).resolve().parent/(selector+'.png')
        if '_slot_shot' in doc and Path(doc['_slot_shot']).resolve()!=paired:
            return False
    return (doc.get('screen') == case['screen'] and
            doc.get('viewport', {}).get('width') == case['viewport_width'] and
            (not (exact_viewport or 'display_budget' in case) or
             doc.get('viewport', {}).get('height') == case['viewport_height']))


def first_piece_documents(config, documents, case_ids):
    """Select whole original pages; each requested slot must have exactly one capture."""
    selected, remaining = selected_cases(config, case_ids)
    chosen = {}
    for case in selected:
        matches = [doc for doc in documents if matches_case(case, doc, exact_viewport=True)]
        if len(matches) != 1:
            raise ValueError('required first-piece state absent or ambiguous: ' + case['id'])
        doc = matches[0]
        if doc.get('truncated') or doc.get('errors') or doc.get('error'):
            raise ValueError('incomplete first-piece capture: ' + case['id'])
        chosen[str(Path(doc['_file']).resolve())] = doc
    return list(chosen.values()), [case['id'] for case in selected], remaining


def run(config,dump_files,shots,case_ids=None):
    cases=json.loads(Path(config).read_text())['cases']
    if not isinstance(cases,list) or not cases:raise ValueError('required cases missing')
    remaining = None
    if case_ids is not None:
        cases, remaining = selected_cases(config, case_ids)
    allowed={Path(s).resolve() for s in shots}; docs=[]
    for f in dump_files:
        doc=json.loads(Path(f).read_text())
        if isinstance(doc,dict) and 'nodes' in doc:
            f=Path(f)
            doc['_file']=str(f.resolve())
            shot=Path(doc.get('screenshot') or f.name.replace('-ui-dump-','-ui-').rsplit('.',1)[0]+'.png')
            doc['_slot_shot']=(shot if shot.is_absolute() else f.parent/shot).resolve()
            docs.append(doc)
    results=[]
    for case in cases:
        row={'id':case['id'],'passed':False}
        try:
            validate_display_budget(case)
            matches=[d for d in docs if matches_case(case, d, exact_viewport=case_ids is not None)]
            if len(matches)!=1:raise ValueError('required state absent or ambiguous')
            doc=matches[0]; path=doc['_slot_shot']
            if path not in allowed or doc.get('truncated') or doc.get('errors'):raise ValueError('incomplete or unpaired capture')
            with Image.open(path) as im:row['checks']=inspect(im,doc['nodes'],case,doc)
            row['passed']=all(r['passed'] for r in row['checks'])
        except (ValueError,TypeError,KeyError,OSError,IndexError) as err:row['error']=str(err)
        results.append(row)
    result = dict(passed=all(r['passed'] for r in results),cases=results)
    if case_ids is not None:
        result.update(selected_cases=[case['id'] for case in cases], remaining_cases=remaining,
                      full_art_passed=None)
    return result
