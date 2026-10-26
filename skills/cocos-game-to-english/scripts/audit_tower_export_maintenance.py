"""Fail-closed review for the Tower Heroes existing Native export maintenance path.

The input is the original export, not a reconstructed Cocos source project.
This branch verifies the exact rebuild, negative storage control, startup Retry,
recorded GUI observations, and TikTok CLI structure before the shared ZIP writer.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile

import audit_native_storage_contract as storage_contract

REQUIRED_UI = {'reopen_home','reopen_map','reopen_stage_details','profile_revisit',
               'home_shortcut','phone_360x800','phone_393x852',
               'startup_failure_retry','startup_retry_recovered','startup_retry_interactive'}
REQUIRED_CHECKS = {'baseline','business','ui','rebuild','persistence',
                   'startup_retry','platform_structure'}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def tree(root):
    return {f.relative_to(root).as_posix():sha(f) for f in sorted(root.rglob('*')) if f.is_file()}

def hash_json(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def audit(args):
    root=args.project.resolve();native=args.native.resolve();web=args.web.resolve()
    review=json.loads(args.review.read_text());errors=[]
    def require(ok,message):
        if not ok:errors.append(message)
    require(review.get('schema')=='export_maintenance_review.v1' and review.get('game_id')=='tower-heroes','Wrong review kind')
    require(review.get('authorization')=='maintain_only_available_export' and review.get('input_kind')=='existing_native_export','Export-only authorization missing')
    require(review.get('build_tag')==args.build_tag,'Build tag changed')
    actual_native,actual_web=tree(native),tree(web)
    require(actual_native==review.get('native_files'),'Final Native fingerprint changed')
    require(actual_web==review.get('web_files'),'Final Web fingerprint changed')
    original=root/review.get('original_zip','missing')
    require(original.is_file() and sha(original)==review.get('original_sha256'),'Original ZIP fingerprint changed')
    if original.is_file():
        try:
            with zipfile.ZipFile(original) as z:
                baseline={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if not n.endswith('/')}
            changed=sorted(n for n,h in baseline.items() if actual_native.get(n)!=h)
            added=sorted(set(actual_native)-set(baseline))
            old_font='subpackages/resources/native/08/08719077-fbe3-4990-80c2-39585f4726ca/艺黑.ttf'
            new_font='subpackages/resources/native/08/08719077-fbe3-4990-80c2-39585f4726ca/YiHei.ttf'
            font_meta='subpackages/resources/import/08/08719077-fbe3-4990-80c2-39585f4726ca.json'
            require(changed==sorted(['adapter-min.js','assets/main/index.js','game.js',old_font,font_meta]),'Unexpected Native patch footprint')
            require(added==[new_font],'Unexpected added Native file')
            require(changed==review.get('changed_baseline_files') and added==review.get('added_files'),'Baseline patch list stale')
            with zipfile.ZipFile(original) as z:
                require((native/new_font).read_bytes()==z.read(old_font),'Font bytes changed during ASCII rename')
                require((native/font_meta).read_text()==z.read(font_meta).decode().replace('艺黑.ttf','YiHei.ttf'),'Font UUID reference not updated exactly')
        except (OSError,zipfile.BadZipFile) as exc:errors.append('Original ZIP unreadable: '+str(exc))
    maintenance=review.get('maintenance_inputs',{})
    require(bool(maintenance),'Maintenance source inputs missing')
    for rel,digest in maintenance.items():
        candidate=root/rel
        require(candidate.is_file() and sha(candidate)==digest,'Maintenance input changed: '+rel)
    binding={'source_sha256':hash_json(maintenance),'native_tree_sha256':hash_json(actual_native),
             'web_tree_sha256':hash_json(actual_web),'build_tag':args.build_tag}
    require(review.get('binding')==binding,'Source/Native/Web binding changed')
    require(set(review.get('checks',{}))==REQUIRED_CHECKS and all(x.get('status')=='pass' for x in review.get('checks',{}).values()),'Review checklist incomplete')
    with tempfile.TemporaryDirectory(prefix='tower-export-rebuild ') as temporary:
        tmp=Path(temporary)
        for name in ['src','tools','inputs']:
            shutil.copytree(root/name,tmp/name)
        result=subprocess.run([sys.executable,str(tmp/'tools/assemble.py')],capture_output=True,text=True,timeout=90)
        require(result.returncode==0,'Independent Native rebuild failed: '+result.stderr[-400:])
        if result.returncode==0:
            require(tree(tmp/'build/native')==actual_native,'Independent Native rebuild differs')
            require(tree(tmp/'build/web')==actual_web,'Independent Web rebuild differs')
    for file in list(native.rglob('*.js'))+list(web.rglob('*.js')):
        result=subprocess.run(['node','--check',str(file)],capture_output=True,text=True)
        require(result.returncode==0,'JavaScript syntax: '+str(file))
    trace=root/review.get('storage_trace','missing')
    if trace.is_file():
        try:
            stored=json.loads(trace.read_text())
            errors+=storage_contract.validate(stored,native,binding)
            if not errors:errors+=storage_contract.replay(stored)
        except (ValueError,OSError,KeyError) as exc:errors.append('Storage trace invalid: '+str(exc))
    else:errors.append('Storage trace missing')
    bundle_text=(native/'assets/main/index.js').read_text()
    inventory={}
    for name in ('AdRewardReceipt','HomeGrowthWallet','DLocal','UIGuild'):
        start=bundle_text.find(name+':[function')
        end=bundle_text.find('cc._RF.pop()}',start)
        if start<0 or end<0:
            errors.append('Storage module missing: '+name)
            continue
        module=bundle_text[start:end]
        inventory[name]={call:module.count(call+'(') for call in ('getItem','setItem','removeItem')}
    require(inventory==review.get('storage_inventory'),'All storage owners must be inventoried against current Native bytes')
    ui=review.get('runtime_ui',{})
    require(set(ui)==REQUIRED_UI,'Runtime UI evidence inventory incomplete')
    for name in REQUIRED_UI:
        row=ui.get(name,{})
        item=row.get('evidence',{})
        file=root/item.get('path','missing')
        require(row.get('status')=='pass' and len(row.get('observed',''))>50,name+' observation missing')
        require(file.is_file() and sha(file)==item.get('sha256'),name+' evidence changed')
        if file.is_file():
            data=file.read_bytes()
            require(len(data)>5000 and (data.startswith(b'\xff\xd8\xff') or data.startswith(b'\x89PNG\r\n\x1a\n')),name+' image invalid')
    cli=root.parent/'ttmg-cli/node_modules/.bin/ttmg'
    require(cli.is_file(),'TikTok CLI missing')
    if cli.is_file():
        result=subprocess.run([str(cli),'check','--dir',str(native),'--format','json','--include-passed'],capture_output=True,text=True,timeout=90)
        try:
            report=json.loads(result.stdout)
            require(result.returncode==0 and report.get('status')=='passed' and report.get('summary',{}).get('errors')==0,'TikTok CLI structure check failed')
        except ValueError:errors.append('TikTok CLI output invalid')
    return {'tool':'audit_tower_export_maintenance','status':'blocked' if errors else 'passed',
            'passed':not errors,'errors':errors,'scope':'Existing Tower Heroes Native export maintenance; physical-device, real ad and platform acceptance remain unverified'}
