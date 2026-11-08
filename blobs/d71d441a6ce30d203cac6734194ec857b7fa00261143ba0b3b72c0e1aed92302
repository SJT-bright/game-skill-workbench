"""Mandatory byte-size gate shared by upload writers; no gameplay CI.

CLI: re-read the final ZIP on EVERY delivery, including unchanged/renamed/imported
packages. A fresh size receipt is deliberately separate from gameplay/startup checks.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import stat
import uuid
import zipfile
from verify_native_zip import TIKTOK_MAIN, TIKTOK_TOTAL, TIKTOK_INDEPENDENT, safe_name

SOURCES = {
    'tiktok': 'https://developers.tiktok.com/docs/en/mini-games-technical-overview',
    'douyin': 'https://developer.open-douyin.com/docs/resource/zh-CN/mini-game/develop/framework/subpackages/basic',
}


def enforce(sizes, game, platform='tiktok'):
    if platform not in SOURCES:
        raise ValueError('Unknown target platform; choose tiktok or douyin explicitly')
    total = sum(sizes.values())
    if total > TIKTOK_TOTAL:
        raise ValueError(f'Uncompressed total package {total} bytes exceeds the limit {TIKTOK_TOTAL} bytes')
    key = 'subpackages' if platform == 'tiktok' else 'subPackages'
    if not isinstance(game, dict):
        raise ValueError('game.json must be a JSON object')
    wrong_keys = [k for k in game if k.casefold() == 'subpackages' and k != key]
    if wrong_keys:
        raise ValueError(f'{platform} requires game.json {key}; wrong/ambiguous key(s): {wrong_keys}')
    if not isinstance(game.get(key, []), list):
        raise ValueError(f'game.json {key} must be an array')
    roots=[];normal={};independent={};names=set()
    for sub in game.get(key, []):
        if not isinstance(sub, dict) or not isinstance(sub.get('root'), str):
            raise ValueError('Each subpackage needs a relative root')
        name=sub.get('name')
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_.-]+',name):
            raise ValueError('Each subpackage needs a nonempty ASCII name (letters/digits/_/./-)')
        if name.casefold() in names:
            raise ValueError('Duplicate subpackage name: '+name)
        names.add(name.casefold())
        raw=sub['root']
        safe_name(raw)
        if not re.fullmatch(r'[A-Za-z0-9_./-]+',raw):
            raise ValueError('Non-portable subpackage root: '+repr(raw))
        # A trailing separator is valid directory syntax. Validate the original
        # path first, then use the same directory prefix for either spelling.
        # This normalizes accounting only; never rewrite the inspected ZIP.
        root=raw.rstrip('/')+'/'
        if any(root.casefold().startswith(r.casefold()) or r.casefold().startswith(root.casefold()) for r in roots):
            raise ValueError('Overlapping/duplicate subpackage roots: '+root)
        if not any(p.startswith(root) for p in sizes):
            raise ValueError('Declared subpackage has no files (including exact path case): '+root)
        if any(n.startswith(root) for n in ('game.js','game.json','project.config.json')):
            raise ValueError('A subpackage cannot contain the main entry/configuration')
        if 'independent' in sub and type(sub['independent']) is not bool:
            raise ValueError('independent must be a boolean: '+name)
        roots.append(root)
        count=sum(n for p,n in sizes.items() if p.startswith(root))
        (independent if sub.get('independent') is True else normal)[root]=count
        if sub.get('independent') is True and count>TIKTOK_INDEPENDENT:
            raise ValueError(f'Independent subpackage {root} {count} bytes exceeds {TIKTOK_INDEPENDENT}')
    main=sum(n for p,n in sizes.items() if not any(p.startswith(root) for root in roots))
    if main>TIKTOK_MAIN:
        raise ValueError(f'Uncompressed main package {main} bytes exceeds the limit {TIKTOK_MAIN} bytes')
    # Douyin's documented non-payment total is lower; never borrow TikTok's 30MB allowance.
    if platform=='douyin' and total>20_000_000:
        raise ValueError(f'Uncompressed Douyin total {total} bytes exceeds conservative 20000000 limit')
    return {'total_bytes':total,'main_bytes':main,'normal_subpackages':normal,'independent_subpackages':independent}

def enforce_files(files):
    # Reject total before parsing config or opening an output file.
    total=sum(len(data) for data in files.values())
    if total>TIKTOK_TOTAL:
        raise ValueError(f'Uncompressed total package {total} bytes exceeds the limit {TIKTOK_TOTAL} bytes')
    return enforce({p:len(data) for p,data in files.items()},json.loads(files['game.json'].decode('utf-8-sig')))


def json_object(data):
    """Duplicate configuration keys can be interpreted differently by the uploader."""
    def pairs(rows):
        out={}
        for key,value in rows:
            if key in out:
                raise ValueError('Duplicate JSON configuration key: '+key)
            out[key]=value
        return out
    return json.loads(data.decode('utf-8-sig'),object_pairs_hook=pairs)


def inspect_files(files, platform='tiktok'):
    for name in ('game.js','game.json','project.config.json'):
        if not files.get(name):
            raise ValueError('Missing/empty root entry: '+name+' (do not upload an outer folder)')
    game=json_object(files['game.json'])
    result=enforce({p:len(b) for p,b in files.items()},game,platform)
    key='subpackages' if platform=='tiktok' else 'subPackages'
    subs=game.get(key,[])
    roots=[s['root'].rstrip('/')+'/' for s in subs]
    warnings=[]
    for sub,root in zip(subs,roots):
        if not files.get(root+'game.js'):
            raise ValueError('Missing/empty subpackage game.js entry: '+root)
        if sub['root'].endswith('/'):
            warnings.append('Trailing slash accepted; directory prefix normalized for checks only: '+sub['root'])
    orphans=[n for n in files if n.startswith('subpackages/') and not any(n.startswith(r) for r in roots)]
    if orphans:
        raise ValueError('Unregistered subpackage files are counted in main: '+', '.join(orphans[:5]))
    # Cocos 3 runtime's names must agree with game.json and actual bundle manifests.
    engine_names=None
    if 'src/settings.json' in files:
        settings=json_object(files['src/settings.json'])
        if not isinstance(settings,dict):
            raise ValueError('Cocos src/settings.json must be a JSON object')
        engine_names=settings.get('subpackages',[])
        if not isinstance(engine_names,list) or not all(isinstance(n,str) for n in engine_names):
            raise ValueError('Cocos src/settings.json subpackages must be an array of names')
        if len(set(engine_names))!=len(engine_names) or not set(engine_names).issubset(s['name'] for s in subs):
            raise ValueError('Cocos engine subpackages do not match game.json declarations')
        versions=settings.get('bundleVers',{})
        if not isinstance(versions,dict):
            raise ValueError('Cocos bundleVers must be an object')
        for sub,root in zip(subs,roots):
            if sub['name'] not in engine_names:
                continue  # application-owned code subpackage, not an engine asset bundle
            version=versions.get(sub['name'])
            config_path=root+('config.'+str(version)+'.json' if version else 'config.json')
            if not files.get(config_path):
                raise ValueError('Missing Cocos subpackage bundle config selected by bundleVers: '+config_path)
            config=json_object(files[config_path])
            if not isinstance(config,dict) or config.get('name')!=sub['name']:
                raise ValueError('Cocos bundle config name differs from subpackage name: '+root)
    main_files={n:len(b) for n,b in files.items() if not any(n.startswith(r) for r in roots)}
    result.update(platform=platform,configuration_key=key,engine_subpackages=engine_names,
                  limits={'main_bytes':TIKTOK_MAIN,'total_bytes':TIKTOK_TOTAL if platform=='tiktok' else 20_000_000,
                          'independent_bytes':TIKTOK_INDEPENDENT},
                  subpackages=[{'name':s['name'],'root':s['root'],'independent':s.get('independent',False),
                                'bytes':sum(len(b) for n,b in files.items() if n.startswith(r))}
                               for s,r in zip(subs,roots)],
                  largest_main_files=sorted(main_files.items(),key=lambda x:-x[1])[:10],warnings=warnings,
                  if_subpackages_not_recognized_bytes=result['total_bytes'])
    return result


def inspect_zip(archive, platform='tiktok', feedback=None):
    """No cached verdict, receipt reuse or game execution. Every payload is CRC-read."""
    archive=Path(archive).resolve()
    before=hashlib.sha256(archive.read_bytes()).hexdigest()
    result={'schema':'upload_size_receipt.v1','tool':'upload_size_gate',
            'run_id':str(uuid.uuid4()),'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'archive':str(archive),'sha256':before,'zip_bytes':archive.stat().st_size,
            'platform':platform,'source':SOURCES[platform],
            'tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'passed':False,'errors':[],
            'boundary':'Fresh local partition/configuration/byte/CRC check only; no platform upload or gameplay verdict.'}
    files={};seen=set()
    try:
        with zipfile.ZipFile(archive) as z:
            if sum(i.file_size for i in z.infolist())>TIKTOK_TOTAL:
                raise ValueError('Uncompressed total exceeds 30000000 bytes')
            for info in z.infolist():
                safe_name(info.filename)
                canonical=info.filename.rstrip('/').casefold()
                if canonical in seen:
                    raise ValueError('Duplicate/case-colliding ZIP entry: '+info.filename)
                seen.add(canonical)
                if info.flag_bits&1 or stat.S_ISLNK(info.external_attr>>16):
                    raise ValueError('Encrypted/symlink ZIP entry: '+info.filename)
                if not info.is_dir():
                    files[info.filename]=z.read(info)
            result['explicit_directory_entries']=sum(i.is_dir() for i in z.infolist())
        lower={n.casefold() for n in files}
        for name in files:
            if any(p.as_posix().casefold() in lower for p in Path(name).parents if p.as_posix()!='.'):
                raise ValueError('ZIP file/directory collision: '+name)
        result.update(inspect_files(files,platform))
        result['files']=len(files)
        result['crc_verified']=True
        if feedback:
            evidence=Path(feedback).resolve()
            data=json_object(evidence.read_bytes())
            if (not isinstance(data,dict) or data.get('platform')!=platform or
                    not isinstance(data.get('rejected_sha256'),str) or
                    not re.fullmatch(r'[a-fA-F0-9]{64}',data['rejected_sha256'])):
                raise ValueError('Platform feedback needs matching platform and rejected_sha256')
            rejected=data['rejected_sha256'].lower()
            result['platform_feedback']={'path':str(evidence),'sha256':hashlib.sha256(evidence.read_bytes()).hexdigest(),
                                         'same_rejected_archive':before==rejected}
            if before==rejected:
                raise ValueError('This exact ZIP was rejected by the platform; local arithmetic cannot clear the rejection')
            result['warnings'].append('A prior platform rejection exists; this changed ZIP still requires platform recheck')
        result['passed']=True
    except (ValueError,KeyError,TypeError,zipfile.BadZipFile,RuntimeError) as error:
        result['errors'].append(str(error))
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=before:
        result['passed']=False
        result['errors'].append('ZIP changed during checking; no valid delivery receipt')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip',type=Path,required=True)
    parser.add_argument('--platform',choices=tuple(SOURCES),required=True)
    parser.add_argument('--report',type=Path,required=True,help='new receipt path; never overwrite/reuse an old check')
    parser.add_argument('--platform-feedback',type=Path,help='project-local record of a known platform rejection')
    args=parser.parse_args()
    if args.report.exists() or args.report.is_symlink() or args.report.resolve()==args.zip.resolve():
        parser.error('report must be a new file distinct from ZIP; rerun with a fresh report path')
    try:
        result=inspect_zip(args.zip,args.platform,args.platform_feedback)
        args.report.parent.mkdir(parents=True,exist_ok=True)
        with args.report.open('x',encoding='utf-8') as out:
            json.dump(result,out,ensure_ascii=False,indent=2);out.write('\n')
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0 if result['passed'] else 1
    except (OSError,ValueError,zipfile.BadZipFile) as error:
        print('REFUSED: '+str(error))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
