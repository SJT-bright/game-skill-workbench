#!/usr/bin/env python3
"""Local screenshot backplate probe; annotated text ROIs required, never whole-screen pass."""
import argparse, json, hashlib
from collections import deque
from pathlib import Path
# P20 (问题普查 T20): without Pillow this script ended in a Traceback, even for --help. The shared guard in
# cocos-game-check/package-check/scripts/check_guard.py turns that into a "not_run" line (exit 2) and keeps --help.
if __name__ == '__main__':
    import importlib.util as _ilu
    _cg = Path(__file__).resolve().parents[2] / 'cocos-game-check' / 'package-check' / 'scripts' / 'check_guard.py'
    if _cg.is_file():
        _spec = _ilu.spec_from_file_location('check_guard', _cg)
        _mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        _mod.need_modules('PIL')
from PIL import Image

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def find_backplates(im,targets):
    found=[]
    for t in targets:
        x,y,w,h=t['rect']; x0=max(0,int(x));y0=max(0,int(y));x1=min(im.width,int(x+w+.999));y1=min(im.height,int(y+h+.999))
        if x1<=x0 or y1<=y0: raise ValueError('target outside screenshot: '+t['path'])
        crop=im.crop((x0,y0,x1,y1)); cw,ch=crop.size; pixels=crop.load(); bins={}
        for yy in range(ch):
            for xx in range(cw):
                pixel=pixels[xx,yy];r,g,b=pixel[:3]
                if len(pixel)==4 and pixel[3]<230:continue
                if .2126*r+.7152*g+.0722*b<70:
                    # In an alpha source the dark contour is one silhouette;
                    # quantizing its gradient splits a letter counter/shadow
                    # into apparently rectangular fragments. Screenshot UI
                    # fills still use colour bins to separate nearby surfaces.
                    bins[(xx,yy)]=(0,0,0) if im.mode=='RGBA' else (r//16,g//16,b//16)
        seen=set()
        for start,color in bins.items():
            if start in seen: continue
            q=deque([start]);seen.add(start);pts=[]
            while q:
                a,b=q.popleft();pts.append((a,b))
                for v in ((a-1,b),(a+1,b),(a,b-1),(a,b+1)):
                    if v not in seen and bins.get(v)==color: seen.add(v);q.append(v)
            if len(pts)<45:continue
            xs=[v[0] for v in pts];ys=[v[1] for v in pts];ww=max(xs)-min(xs)+1;hh=max(ys)-min(ys)+1
            occupancy=len(pts)/(ww*hh); ps=set(pts)
            core=sum(all((a+dx,b+dy) in ps for dx in (-1,0,1) for dy in (-1,0,1)) for a,b in pts)
            # Broad flat interior differs from a thin contour. Thresholds stay fixed across old/new/control.
            if ww>=max(8,.18*h) and hh>=max(12,.25*h) and occupancy>=.55 and core/len(pts)>=.25:
                if 'ui_surface_rects' in t:
                    box=[x0+min(xs),y0+min(ys),ww,hh]
                    def covers(b):
                        return max(0,min(box[0]+ww,b[0]+b[2])-max(box[0],b[0]))*max(0,min(box[1]+hh,b[1]+b[3])-max(box[1],b[1]))>=.8*ww*hh
                    if not any(covers(b) for b in t['ui_surface_rects']):continue
                found.append({'target':t['path'],'code':'dark_solid_text_backplate','rect':[x0+min(xs),y0+min(ys),ww,hh],'pixels':len(pts),'occupancy':round(occupancy,3),'core_ratio':round(core/len(pts),3),'color_bin':color})
    return found

def inspect(capture):
    p=Path(capture); d=json.loads(p.read_text()); shot=Path(d['screenshot']); shot=shot if shot.is_absolute() else p.parent/shot; d['screenshot']=str(shot); im=Image.open(shot).convert('RGBA' if d.get('source_kind')=='generated_font_asset' else 'RGB')
    if d.get('screenshot_sha256') != sha(d['screenshot']): raise ValueError('screenshot binding mismatch')
    if not d.get('targets'): raise ValueError('empty target coverage')
    found=find_backplates(im,d['targets'])
    return {'capture':str(p),'screenshot_sha256':sha(d['screenshot']),'binding':d.get('binding'),'targets_checked':len(d['targets']),'passed':not found,'findings':found}
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('captures',nargs='+');a.add_argument('--out',required=True);v=a.parse_args()
    results=[inspect(p) for p in v.captures];Path(v.out).write_text(json.dumps({'passed':all(r['passed'] for r in results),'results':results},ensure_ascii=False,indent=2));print(json.dumps({'passed':all(r['passed'] for r in results),'captures':len(results),'findings':sum(len(r['findings']) for r in results)}));raise SystemExit(0 if all(r['passed'] for r in results) else 1)


def ui_dump_problems(d, image, nodes, get_text, project=None):
    """Adapt real normalized camera boxes; require a distinct UI surface, never a scene backdrop."""
    cx,cy,cw,ch=d.get('canvas_css') or [0,0,d['page']['width'],d['page']['height']]
    sx=image.width/d['page']['width'];sy=image.height/d['page']['height']
    def pixels(n):
        x,y,w,h=n.get('screen') or n['rect']
        return [(cx+x*cw)*sx,(cy+y*ch)*sy,w*cw*sx,h*ch*sy]
    surfaces=[n for n in nodes if {'graphics','sprite'} & set(n.get('comps',{})) and
              0 < (n.get('screen') or n['rect'])[2]*(n.get('screen') or n['rect'])[3] < .2 and n.get('opacity',1)>.85]
    targets=[]
    source_findings=[]
    source_index={}
    original_digests=set()
    if project is not None:
        for p in (Path(project)/'assets').rglob('*.png'):
            source_index.setdefault(p.stem, []).append(p)
        # Preserve explicitly recorded original English art. A broad original
        # panel seen through transparent word art is not the word's own fill.
        board=Path(project)/'docs/board.txt'
        if board.is_file() and board.read_text().strip()=='localize':
            base=Path(project)/'docs/art/base-assets.json'
            try:
                record=json.loads(base.read_text())
                original_digests.update(record.get('images',{}).values())
            except (OSError,ValueError,AttributeError):pass
    for n in nodes:
        if not get_text(n):continue
        r=pixels(n);backings=[]
        # A picture word is itself a surface. Its transparent pixels reveal the
        # parent panel, which must not be mistaken for an opaque fill baked into
        # that word. Inspect every matching source with its actual alpha instead;
        # retain screenshot checks for distinct UI backing surfaces.
        frame=str((n.get('comps',{}).get('sprite') or {}).get('frame',''))
        sources=source_index.get(frame, []) if frame else []
        source_checked=False
        if sources:
            try:
                for source in sources:
                    with Image.open(source) as raw:
                        rgba=raw.convert('RGBA')
                        source_findings.extend(find_backplates(rgba,[{'path':n['path'],'rect':[0,0,*rgba.size]}]))
                source_checked=True
            except (OSError, ValueError):
                source_checked=False  # unreadable evidence keeps the strict screenshot check
        for surface in surfaces:
            if surface is n and source_checked:continue
            sf=str((surface.get('comps',{}).get('sprite') or {}).get('frame',''))
            originals=source_index.get(sf,[])
            if source_checked and originals and all(sha(p) in original_digests for p in originals):continue
            b=pixels(surface)
            ix=max(0,min(r[0]+r[2],b[0]+b[2])-max(r[0],b[0]));iy=max(0,min(r[1]+r[3],b[1]+b[3])-max(r[1],b[1]))
            if ix*iy >= .5*r[2]*r[3]:backings.append(b)
        targets.append({'path':n['path'],'rect':[r[0]-7*sx,r[1]-7*sy,r[2]+14*sx,r[3]+14*sy],'ui_surface_rects':backings})
    unavailable=['checker_unavailable: text_backplate camera screen box missing for '+n['path'] for n in nodes if get_text(n) and not n.get('screen')]
    findings=find_backplates(image,targets)+source_findings
    return unavailable + ['dark_solid_text_backplate: '+f['target']+' contains a broad dark solid UI fill behind its glyph; remove the fill and strengthen the glyph contour' for f in findings]
