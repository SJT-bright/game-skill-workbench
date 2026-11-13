"""Source texture triage for named Cocos2 source/export standalone game sprites.
Signals need human comparison; not an art verdict or a full bundle-format verifier.
"""
import argparse,base64,hashlib,json,re,shlex
from collections import deque
from pathlib import Path

def decode(value):
    if not isinstance(value,str):raise ValueError('texture UUID must be a string')
    if len(value)==22:
        raw=value[:2]+base64.b64decode(value[2:],validate=True).hex()
        value='-'.join([raw[:8],raw[8:12],raw[12:16],raw[16:20],raw[20:]])
    if not re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}',value):raise ValueError('unsupported texture UUID')
    return value

def runlen(values):
    best=length=0
    for item in values:length=length+1 if item else 0;best=max(best,length)
    return best

def components(mask,width,height):
    """8-connected parts of a row-major 0/1 mask: [{'area','bbox'}] in the order a raster scan first meets them, the
    same list the old pixel-by-pixel flood fill made. It joins runs of set pixels row by row instead of visiting every
    pixel; the fill took 11 s for the 139 textures of 蛋壳特工队 (美工skill 2026-11-05)."""
    data=bytes(mask);parent=[];runs=[];prev=[]
    def root(a):
        while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
        return a
    for y in range(height):
        row=data[y*width:(y+1)*width];cur=[];x=row.find(1)
        while x!=-1:
            end=row.find(0,x)
            if end==-1:end=width
            cur.append(len(runs));runs.append((y,x,end));parent.append(len(parent));x=row.find(1,end)
        k=0
        for rid in cur:
            b0,b1=runs[rid][1],runs[rid][2]
            while k<len(prev) and runs[prev[k]][2]<b0:k+=1      # ends left of the pixel before b0: not touching
            m=k
            while m<len(prev) and runs[prev[m]][1]<=b1:          # starts at most one pixel right of b1-1: touching
                ra,rb=root(prev[m]),root(rid)
                if ra!=rb:parent[max(ra,rb)]=min(ra,rb)
                m+=1
        prev=cur
    parts={}
    for rid,(y,x0,x1) in enumerate(runs):
        r=root(rid)
        if r not in parts:parts[r]={'area':0,'bbox':[x0,y,x1,y+1]}
        p=parts[r];p['area']+=x1-x0;b=p['bbox']
        b[0]=min(b[0],x0);b[2]=max(b[2],x1);b[3]=max(b[3],y+1)
    return list(parts.values())     # dict order = first run of each part = where the raster scan first met it

def inspect_texture(path):
    from PIL import Image
    with Image.open(path) as source:im=source.convert('RGBA')
    return inspect_image(im)

def inspect_image(im):
    """The same source signals for a verified texture rectangle, without rewriting pixels."""
    im=im.convert('RGBA')
    width,height=im.size;mask=bytearray(im.getchannel('A').point(lambda v:1 if v>8 else 0).tobytes())
    if not any(mask):return {'size':[width,height],'suspects':['empty_alpha'],'edge_runs':{},'components':[]}
    edges={'top':mask[:width],'bottom':mask[-width:],'left':mask[::width],'right':mask[width-1::width]}
    cuts={key:runlen(values) for key,values in edges.items() if runlen(values)>=max(16,len(values)*.15)}
    parts=components(mask,width,height)
    parts.sort(key=lambda x:-x['area']);floor=max(12,parts[0]['area']*.0005)
    fragments=[c for c in parts[1:] if c['area']>=floor]
    margin=max(2,min(width,height)*.005);b=parts[0]['bbox'];touches=min(b[0],b[1],width-b[2],height-b[3])<margin
    signals=(['straight_source_edge'] if cuts else [])+(['extra_alpha_components'] if fragments else [])+(['main_body_lacks_safety_margin'] if touches else [])
    # Entire visible silhouette (including legitimate detached pieces), not just the largest component.
    ink=im.getchannel('A').point(lambda a:255 if a>8 else 0).getbbox()
    if (ink[2]-ink[0])/width < .2 and (ink[3]-ink[1])/height < .2:
        signals.append('tiny_content_in_frame')
    return {'size':[width,height],'suspects':signals,'edge_runs':cuts,'components':fragments,'ink_bbox':ink,'main_component':parts[0],'alpha_threshold':8,'component_floor':floor,'pixel_sha256':hashlib.sha256(im.tobytes()).hexdigest()}

def check(root,names,role='single_body'):
    root=Path(root).resolve();names=list(dict.fromkeys(names));errors=[];matches={name:[] for name in names}
    if not root.is_dir() or not names or any(not isinstance(n,str) or not n for n in names):
        return {'input':str(root),'status':'incomplete','passed':False,'checked':0,'missing':names,'errors':['Cocos source/export root and nonempty frame targets required'],'rows':[],'art_verdict':'not_assessed'}
    if role not in ('single_body','background','tile','multi_body'):raise ValueError('unsupported role')
    if role!='single_body':
        return {'input':str(root),'status':'not_applicable','passed':None,'checked':0,'missing':[],'errors':[],'rows':[],'role':role,'art_verdict':'not_assessed'}
    source_mode=(root/'project.json').is_file()
    package=root/'package.json'
    creator3=False
    if package.is_file():
        try:
            creator3=str(json.loads(package.read_text()).get('creator',{}).get('version','')).startswith('3.')
        except (OSError,ValueError,AttributeError):
            pass
    source_mode=source_mode or creator3
    if source_mode:
        images = (p for p in (root/'assets').rglob('*.meta')
                  if Path(p.stem).suffix.lower() in {'.png', '.jpg', '.jpeg'})
        for p in images:
            try:
                doc=json.loads(p.read_text())
                metas=doc.get('subMetas',{})
                frame_names=({m.get('displayName') for m in metas.values() if isinstance(m,dict) and m.get('importer')=='sprite-frame'}
                             if creator3 else set(metas))
                for name in frame_names.intersection(names):
                    tex=Path(str(p)[:-5]).resolve()
                    if not tex.is_relative_to(root) or not tex.is_file():raise ValueError('missing source texture')
                    matches[name].append(tex)
            except (OSError,ValueError,TypeError) as exc:errors.append({'path':str(p.relative_to(root)),'error':str(exc)})
    # Limited profile: standalone import/*.json + sibling native directory.
    # Scan both main assets and ordinary subpackages; unknown layouts remain incomplete.
    folders=[] if source_mode else sorted(set(root.glob('assets/*/import'))|set(root.glob('subpackages/*/import')))
    for folder in folders:
        for p in folder.rglob('*.json'):
            try:
                doc=json.loads(p.read_text())
                if not isinstance(doc,list) or len(doc)<6 or not isinstance(doc[5],list) or not doc[5] or not isinstance(doc[5][0],dict):continue
                name=doc[5][0].get('name')
                if name not in matches:continue
                uuid=decode(doc[1][0]);native=folder.parent/'native'
                textures=sorted(native.rglob(uuid+'.png'))
                if not textures:raise ValueError('missing standalone PNG')
                for texture in textures:
                    path=texture.resolve()
                    if not path.is_relative_to(root):
                        errors.append({'path':str(p.relative_to(root)),'texture':str(texture.relative_to(root)),'error':'texture outside Native root'})
                        continue
                    matches[name].append(path)
            except (OSError,ValueError,TypeError,IndexError,KeyError) as exc:
                errors.append({'path':str(p.relative_to(root)),'error':str(exc)})
    rows=[];cache={};candidate_counts={}
    for name,paths in matches.items():
        # Inspect every distinct candidate. Name collisions do not identify which
        # bundle the runtime used, but must not hide a candidate's source signals.
        paths=sorted(set(paths));candidate_counts[name]=len(paths)
        for path in paths:
            try:
                if path not in cache:cache[path]=dict(inspect_texture(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                row=dict(cache[path],name=name,texture=str(path.relative_to(root)),candidate_count=len(paths));rows.append(row)
            except (OSError,ValueError,ImportError) as exc:errors.append({'frame':name,'texture':str(path.relative_to(root)),'error':str(exc)})
    missing=sorted(set(names)-{row['name'] for row in rows});review=any(row['suspects'] for row in rows)
    status='incomplete' if missing or errors or not rows else 'needs_review' if review else 'no_signals'
    return {'input':str(root),'status':status,'passed':status=='no_signals','checked':len(rows),'missing':missing,'errors':errors,'rows':rows,'candidate_counts':candidate_counts,'runtime_binding':'not_assessed','art_verdict':'not_assessed','coverage':'all discovered distinct PNG/JPEG source textures or standalone Cocos2 export PNGs for each named frame; name collisions are exhaustively inspected, not resolved to runtime bindings; actual frame rect and whole-page composition need project observation'}

def observed_dump_files(dumps, project=None):
    """Mixed evidence uses only verified originals; ordinary scans keep attachments."""
    folder = Path(dumps)
    if (folder/'capture-inheritance.json').is_file():
        import sys
        core = Path(__file__).resolve().parents[2]/'remake-core/scripts'
        if str(core) not in sys.path:
            sys.path.insert(0, str(core))
        from art_capture_history import resolve_input_files
        return resolve_input_files(folder, project)
    return folder.rglob('*.json')


def captured_inventory(dumps):
    names=set();pages=set()
    if dumps:
        for path in observed_dump_files(dumps):
            try:doc=json.loads(path.read_text())
            except (OSError,ValueError):continue
            if not isinstance(doc,dict):continue
            nodes=doc.get('nodes',[])
            if not isinstance(nodes,list):continue
            for node in nodes:
                if not isinstance(node,dict):continue
                sprite=node.get('comps',{}).get('sprite',{});frame=sprite.get('frame')
                if isinstance(frame,str) and frame:names.add(frame)
            if nodes:pages.add(str(doc.get('page',path.name)))
    excluded=[{'frame':n,'reason':'background texture: separate composition/tiling review'} for n in sorted(names) if n.startswith('background_')]
    return {'pages':sorted(pages),'observed_frames':sorted(names),'selected_frames':sorted(n for n in names if not n.startswith('background_')),'excluded_frames':excluded}

def captured_frames(dumps):
    return captured_inventory(dumps)['selected_frames']

def bitmap_font_routes(root, names, observations):
    """Resolve fontFrames glyph sprites from real FNT page geometry and pixels.

    Names alone never approve a glyph: every observed frame must have the exact
    declared rectangle size, the page dimensions/rect must be valid, and all
    otherwise indistinguishable source candidates must contain identical pixels.
    The original texture triage still runs on each rectangle and retains signals.
    """
    from PIL import Image
    aliases={'percent':'%','slash':'/','plus':'+','minus':'-','colon':':','dot':'.','x':'x'}
    wanted={}
    for name in names:
        m=re.fullmatch(r'digit_([0-9])',name)
        char=m.group(1) if m else aliases.get(name[7:]) if name.startswith('symbol_') else None
        if char:wanted[name]=ord(char)
    candidates={name:[] for name in wanted}
    if not (root/'assets').is_dir() or not wanted:return {},[]
    for font in sorted((root/'assets').rglob('*.fnt')):
        try:
            if not font.resolve().is_relative_to(root/'assets'):continue
            pages={};glyphs={};common={}
            for line in font.read_text(encoding='utf-8-sig').splitlines():
                fields=shlex.split(line)
                if not fields:continue
                values=dict(value.split('=',1) for value in fields[1:] if '=' in value)
                if fields[0]=='page':pages[int(values['id'])]=values['file']
                elif fields[0]=='char':glyphs[int(values['id'])]=values
                elif fields[0]=='common':common=values
            for name,code in wanted.items():
                value=glyphs.get(code);samples=observations.get(name,[])
                if not value or not samples:continue
                x,y,w,h=(int(value[key]) for key in ('x','y','width','height'))
                if min(x,y)<0 or min(w,h)<=0 or any(s.get('frame_size')!=[w,h] for s in samples):continue
                texture=(font.parent/pages[int(value.get('page',0))]).resolve()
                if not texture.is_relative_to(root/'assets') or not texture.is_file():continue
                with Image.open(texture) as source:im=source.convert('RGBA')
                if im.size!=(int(common['scaleW']),int(common['scaleH'])) or x+w>im.width or y+h>im.height:continue
                crop=im.crop((x,y,x+w,y+h));info=inspect_image(crop)
                binding={'manifest':str(font.relative_to(root)), 'manifest_sha256':hashlib.sha256(font.read_bytes()).hexdigest(),
                         'texture':str(texture.relative_to(root)), 'texture_sha256':hashlib.sha256(texture.read_bytes()).hexdigest(),
                         'char_id':code,'rect':[x,y,w,h]}
                binding_sha=hashlib.sha256(json.dumps(binding,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                candidates[name].append(dict(info,name=name,resource_kind='bitmap_font_glyph',sha256=binding_sha,**binding))
        except (OSError,ValueError,KeyError,TypeError,UnicodeError):
            # Unknown/broken FNTs cannot supply a route. The requested frame remains
            # missing unless another complete, unambiguous actual source resolves it.
            continue
    routes={};rows=[]
    for name,values in candidates.items():
        if not values or len({(tuple(v['size']),v['pixel_sha256']) for v in values})!=1:continue
        for value in values:value['candidate_count']=len(values)
        rows.extend(values)
        routes[name]={'type':'bitmap_font_glyph','sources':[{k:v[k] for k in ('manifest','manifest_sha256','texture','texture_sha256','char_id','rect','pixel_sha256')} for v in values],
                      'status':'exact_geometry_and_pixels_resolved; source signals retained in rows'}
    return routes,rows

def route_other_sources(result, dumps, atlas_report):
    """Route observed frames that are outside the standalone texture profile."""
    if not dumps or not result['missing']:
        return result
    root = Path(result['input'])
    atlas = json.loads(atlas_report.read_text()) if atlas_report and atlas_report.is_file() else {}
    candidates = {}
    for sheet in atlas.get('atlases', []):
        checked = {row['frame'] for row in sheet['frames'] if not row['problems']}
        skipped = {row['frame']: row['reason'] for row in sheet['skipped']}
        for frame in checked | skipped.keys():
            for name in sheet['frame_names'].get(frame, [frame]):
                candidates.setdefault(name, []).append({
                    'type': 'atlas', 'manifest': sheet['manifest'],
                    'manifest_sha256': sheet['manifest_sha256'], 'slice': frame,
                    'status': skipped.get(frame, 'checked'),
                    'sizes': sheet['runtime_sizes'].get(frame, [])
                })
    observations = {}
    for path in observed_dump_files(dumps):
        try:
            doc = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if not isinstance(doc, dict):
            continue
        for node in doc.get('nodes', []):
            sprite = node.get('comps', {}).get('sprite', {})
            name = sprite.get('frame')
            if name in result['missing']:
                observations.setdefault(name, []).append(sprite)
    glyph_routes,glyph_rows=bitmap_font_routes(root,result['missing'],observations)
    result['rows'].extend(glyph_rows)
    result['checked']+=len(glyph_rows)
    result.setdefault('candidate_counts',{}).update({name:len(route['sources']) for name,route in glyph_routes.items()})
    engine = root / 'project.json'
    engine_version = json.loads(engine.read_text()).get('version') if engine.is_file() else None
    builtin = Path('/Applications/Cocos/Creator/2.4.15/CocosCreator.app/Contents/Resources/static/default-assets/image')
    routes = dict(glyph_routes)
    for name in result['missing']:
        if name in routes:continue
        samples = observations.get(name, [])
        matched = [row for row in candidates.get(name, [])
                   if samples and all(sample.get('frame_size') in row['sizes'] for sample in samples)]
        if len(matched) == 1:
            routes[name] = matched[0]
            continue
        if candidates.get(name) or engine_version != '2.4.15' or name not in (
                'default_scrollbar_vertical', 'default_scrollbar_vertical_bg'):
            continue
        texture = builtin / (name + '.png')
        meta = texture.with_suffix('.png.meta')
        if not (texture.is_file() and meta.is_file()):
            continue
        frame = json.loads(meta.read_text())['subMetas'][name]
        size = [frame['rawWidth'], frame['rawHeight']]
        if samples and all(sample.get('sliced') is True and sample.get('frame_size') == size
                           for sample in samples):
            routes[name] = {'type': 'creator_default_sliced_control', 'texture': str(texture),
                            'sha256': hashlib.sha256(texture.read_bytes()).hexdigest(),
                            'meta_sha256': hashlib.sha256(meta.read_bytes()).hexdigest(),
                            'frame_uuid': frame['uuid'], 'size': size}
    result['routed_frames'] = routes
    result['missing'] = sorted(set(result['missing']) - routes.keys())
    if not result['missing'] and not result['errors'] and result['rows']:
        result['status'] = 'needs_review' if any(row['suspects'] for row in result['rows']) else 'no_signals'
        result['passed'] = result['status'] == 'no_signals'
    return result

def apply_review(result):
    path=Path(result['input'])/'docs/art/sprite-source-review.json'
    if not path.is_file() or result['status']=='incomplete':return result
    try:entries=json.loads(path.read_text()).get('reviews',[])
    except (OSError,ValueError,TypeError):result['errors'].append('invalid sprite-source-review.json');result['status']='incomplete';result['passed']=False;return result
    if not isinstance(entries,list) or any(not isinstance(x,dict) or not isinstance(x.get('why',''),str) or not isinstance(x.get('normal_signals',[]),list) for x in entries):
        result['errors'].append('invalid source review entries');result['status']='incomplete';result['passed']=False;return result
    for row in result['rows']:
        for entry in entries:
            if entry.get('frame')!=row['name'] or entry.get('sha256')!=row['sha256'] or not entry.get('why','').strip():continue
            accepted=set(entry.get('normal_signals',[]))&{'straight_source_edge','main_body_lacks_safety_margin','extra_alpha_components','tiny_content_in_frame'}
            row['observed_suspects']=row['suspects'][:];row['suspects']=[x for x in row['suspects'] if x not in accepted];row['human_review']=entry
    result['status']='needs_review' if any(r['suspects'] for r in result['rows']) else 'no_signals';result['passed']=result['status']=='no_signals'
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('native_root',type=Path,metavar='ROOT');parser.add_argument('frames',nargs='*');parser.add_argument('--dumps',type=Path);parser.add_argument('--out',type=Path);parser.add_argument('--atlas-report',type=Path);parser.add_argument('--role',choices=['single_body','background','tile','multi_body'],default='single_body');args=parser.parse_args()
    names=args.frames or captured_frames(args.dumps)
    result=apply_review(route_other_sources(check(args.native_root,names,args.role),args.dumps,args.atlas_report))
    if args.dumps:result['capture_inventory']=captured_inventory(args.dumps)
    if args.out:args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 2 if result['status']=='incomplete' else 1 if result['status']=='needs_review' else 0
if __name__=='__main__':raise SystemExit(main())
