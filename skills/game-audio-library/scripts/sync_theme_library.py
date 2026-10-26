#!/usr/bin/env python3
"""Download versioned, themed audio from original sources. Never modifies game projects.
Run --list, or --theme all / puzzle / scifi etc. Existing verified packs are reused.
"""
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess, sys, tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse
import requests
from common import LIB, RAW, AUDIO_EXT, record_credit, credits_by_file, safe_name, classify_license
from fetch_page import safe_extract
MANIFEST = Path(__file__).resolve().parent.parent / 'templates/theme-packs.json'
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()
def ensure_credits(pack, dest, names):
    credits = credits_by_file()
    count = 0
    for name in names:
        target = dest / name
        if target.suffix.lower() not in AUDIO_EXT or str(target) in credits:
            continue
        asset = pack.get('assets', {}).get(Path(name).as_posix(), {})
        record_credit(target, pack['source'], asset.get('title', target.stem),
                      pack['author'], pack['license'], pack['license_url'], asset.get('page', pack['page']))
        count += 1
    return count


def sync(pack, cache_dir=None, offline=False):
    allowed, _, why = classify_license(pack.get('license', ''))
    if not allowed: raise ValueError('License rejected: ' + why)
    for field in ('key', 'source'):
        if pack[field] != safe_name(pack[field]) or pack[field] in ('.', '..'):
            raise ValueError('Unsafe pack path: ' + field)
    dest=RAW/pack['source']/pack['key']
    receipt=LIB/'downloads'/(pack['key']+'.json')
    identity=hashlib.sha256(json.dumps(pack,sort_keys=True).encode()).hexdigest()
    old=json.loads(receipt.read_text()) if receipt.exists() else {}
    if old.get('identity')==identity and old.get('files') and all((dest/n).is_file() and digest(dest/n)==h for n,h in old['files'].items()):
        repaired = ensure_credits(pack, dest, old['files'])
        return dict(key=pack['key'],status='reused',files=len(old['files']),credits_repaired=repaired)
    # Stage a complete pack before changing the live library. Network failure leaves old files intact.
    with tempfile.TemporaryDirectory(prefix='audio-theme-') as td:
        stage=Path(td)/'unpacked'; stage.mkdir(); source_hashes={}
        for entry in pack['files']:
            url=entry['url']; name=safe_name(entry.get('name') or Path(unquote(urlparse(url).path)).name, 120)
            p=Path(td)/name
            cached = None
            if cache_dir and entry.get('sha256'):
                suffix = Path(unquote(urlparse(url).path)).suffix
                candidate = Path(cache_dir) / (hashlib.sha256(url.encode()).hexdigest()[:20] + suffix)
                if candidate.is_file() and digest(candidate) == entry['sha256']:
                    cached = candidate
            if cached:
                shutil.copy2(cached, p)
            elif offline:
                raise ValueError('Verified source cache missing: ' + url)
            else:
                with requests.get(url,stream=True,timeout=(20,120),headers={'User-Agent':'GameAudioSkill/2.0'}) as r:
                    r.raise_for_status()
                    with p.open('wb') as out:
                        for chunk in r.iter_content(65536): out.write(chunk)
            source_hashes[url]=digest(p)
            if entry.get('sha256') and digest(p)!=entry['sha256']: raise ValueError('Source checksum changed: '+url)
            if p.suffix.lower()=='.zip': safe_extract(p,stage)
            elif p.suffix.lower() in AUDIO_EXT: shutil.copy2(p,stage/name)
            else: raise ValueError('Unsupported source: '+url)
        audio=[p for p in stage.rglob('*') if p.suffix.lower() in AUDIO_EXT and p.is_file()]
        if not audio: raise ValueError('No audio in '+pack['key'])
        for p in audio:
            q=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(p)],capture_output=True,text=True)
            if q.returncode or float(q.stdout.strip() or 0)<=0: raise ValueError('Invalid audio '+str(p))
        hashes={}
        staged=[p for p in stage.rglob('*') if p.is_file()]
        for p in staged:
            target=dest/p.relative_to(stage)
            if target.exists() and digest(target)!=digest(p): raise ValueError('Local modification preserved: '+str(target))
        for p in staged:
            rel=p.relative_to(stage); target=dest/rel; target.parent.mkdir(parents=True,exist_ok=True)
            h=digest(p)
            if target.exists() and digest(target)!=h: raise ValueError('Local modification preserved: '+str(target))
            if not target.exists(): shutil.copy2(p,target)
            hashes[str(rel)]=h
        ensure_credits(pack, dest, hashes)
        receipt.parent.mkdir(parents=True,exist_ok=True)
        tmp=receipt.with_suffix('.tmp'); tmp.write_text(json.dumps(dict(identity=identity,files=hashes,sources=source_hashes),indent=2));tmp.replace(receipt)
        return dict(key=pack['key'],status='downloaded',audio=len(audio))
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--theme',default='all');ap.add_argument('--list',action='store_true');ap.add_argument('--no-index',action='store_true');ap.add_argument('--cache-dir');ap.add_argument('--offline',action='store_true');a=ap.parse_args()
    packs=json.loads(MANIFEST.read_text())['packs']
    if a.list:
        print(json.dumps(packs,ensure_ascii=False,indent=2));return
    selected=[p for p in packs if a.theme=='all' or a.theme in set(p.get('themes', [])) | {t for asset in p.get('assets', {}).values() for t in asset.get('themes', [])}]
    if not selected: ap.error('Unknown theme. Use --list.')
    results=[];failed=False
    for pack in selected:
        try: result=sync(pack,a.cache_dir,a.offline)
        except Exception as e: result=dict(key=pack['key'],status='failed',error=str(e));failed=True
        results.append(result);print(json.dumps(result,ensure_ascii=False),flush=True)
    if not a.no_index:
        r=subprocess.run([sys.executable,str(Path(__file__).with_name('build_index.py'))]);failed=failed or r.returncode!=0
    print(json.dumps(dict(library=str(LIB),results=results,success=not failed),ensure_ascii=False))
    raise SystemExit(1 if failed else 0)
if __name__=='__main__':main()
