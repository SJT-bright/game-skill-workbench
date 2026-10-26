#!/usr/bin/env python3
"""Local screenshot backplate probe; annotated text ROIs required, never whole-screen pass."""
import argparse, json, hashlib
from collections import deque
from pathlib import Path
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
                    bins[(xx,yy)]=(r//16,g//16,b//16)
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


def ui_dump_problems(d, image, nodes, get_text):
    """Adapt real normalized camera boxes; require a distinct UI surface, never a scene backdrop."""
    cx,cy,cw,ch=d.get('canvas_css') or [0,0,d['page']['width'],d['page']['height']]
    sx=image.width/d['page']['width'];sy=image.height/d['page']['height']
    def pixels(n):
        x,y,w,h=n.get('screen') or n['rect']
        return [(cx+x*cw)*sx,(cy+y*ch)*sy,w*cw*sx,h*ch*sy]
    surfaces=[n for n in nodes if {'graphics','sprite'} & set(n.get('comps',{})) and
              0 < (n.get('screen') or n['rect'])[2]*(n.get('screen') or n['rect'])[3] < .2 and n.get('opacity',1)>.85]
    targets=[]
    for n in nodes:
        if not get_text(n):continue
        r=pixels(n);backings=[]
        for surface in surfaces:
            b=pixels(surface)
            ix=max(0,min(r[0]+r[2],b[0]+b[2])-max(r[0],b[0]));iy=max(0,min(r[1]+r[3],b[1]+b[3])-max(r[1],b[1]))
            if ix*iy >= .5*r[2]*r[3]:backings.append(b)
        targets.append({'path':n['path'],'rect':[r[0]-7*sx,r[1]-7*sy,r[2]+14*sx,r[3]+14*sy],'ui_surface_rects':backings})
    unavailable=['checker_unavailable: text_backplate camera screen box missing for '+n['path'] for n in nodes if get_text(n) and not n.get('screen')]
    findings=find_backplates(image,targets)
    return unavailable + ['dark_solid_text_backplate: '+f['target']+' contains a broad dark solid UI fill behind its glyph; remove the fill and strengthen the glyph contour' for f in findings]
