"""Replay declared ink reservations or containment on captured Cocos UI. All coordinates are normalized."""
import json
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

def lookup(nodes,path):
    if not isinstance(path,str) or not path:raise ValueError('exact node path required')
    matches=[n for n in nodes if n.get('path')==path]
    if len(matches)!=1:raise ValueError('absent or ambiguous node: '+path)
    node=matches[0]
    return box(node.get('unclipped_screen',node['screen']))

def inspect(im,nodes,case):
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
    if not rows:raise ValueError('empty slot check')
    return rows

def run(config,dump_files,shots):
    cases=json.loads(Path(config).read_text())['cases']
    if not isinstance(cases,list) or not cases:raise ValueError('required cases missing')
    allowed={Path(s).resolve() for s in shots}; docs=[]
    for f in dump_files:
        doc=json.loads(Path(f).read_text())
        if isinstance(doc,dict) and 'nodes' in doc:
            f=Path(f)
            shot=Path(doc.get('screenshot') or f.name.replace('-ui-dump-','-ui-').rsplit('.',1)[0]+'.png')
            doc['_slot_shot']=(shot if shot.is_absolute() else f.parent/shot).resolve()
            docs.append(doc)
    results=[]
    for case in cases:
        row={'id':case['id'],'passed':False}
        try:
            matches=[d for d in docs if d.get('screen')==case['screen'] and d.get('viewport',{}).get('width')==case['viewport_width']]
            if len(matches)!=1:raise ValueError('required state absent or ambiguous')
            doc=matches[0]; path=doc['_slot_shot']
            if path not in allowed or doc.get('truncated') or doc.get('errors'):raise ValueError('incomplete or unpaired capture')
            with Image.open(path) as im:row['checks']=inspect(im,doc['nodes'],case)
            row['passed']=all(r['passed'] for r in row['checks'])
        except (ValueError,TypeError,KeyError,OSError,IndexError) as err:row['error']=str(err)
        results.append(row)
    return dict(passed=all(r['passed'] for r in results),cases=results)
