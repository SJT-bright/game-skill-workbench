#!/usr/bin/env python3
"""Validate a design starter before production; never execute supplied code.
This proves the explicit data contract, not originality, English prose quality,
solvability or the claimed output of an attached solver.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]/'cocos-game-to-english/scripts'))
from product_contract import limited_levels, skin_counts, reward_errors
from inspect_starter import inspect_input

REQUIRED = ('START_HERE.md', 'GAME_DESIGN.md', 'ART_DIRECTION.md', 'UI_PAGES.md',
            'ECONOMY.json', 'COPY_EN.md', 'AUDIO.md', 'starter.json')
CJK = re.compile(r'[\u3400-\u9fff]')


def read_files(path):
    path = Path(path).resolve()
    if path.is_dir():
        result = {}
        for item in path.rglob('*'):
            if item.is_symlink():raise ValueError('starter may not contain symlinks')
            if item.is_file():
                name = item.relative_to(path).as_posix()
                if item.stat().st_size > 64*1024*1024:raise ValueError('starter member exceeds read budget')
                result[name] = item.read_bytes()
        if sum(map(len, result.values())) > 512*1024*1024:raise ValueError('starter exceeds total read budget')
        return result
    report = inspect_input(path, 64*1024*1024, 512*1024*1024)
    if report['errors']:raise ValueError('unsafe or corrupt starter archive: '+str(report['errors']))
    if report['format'] != 'zip':raise ValueError('semantic validation requires a directory or ZIP')
    import zipfile
    with zipfile.ZipFile(path) as archive:
        return {name:archive.read(name) for name in archive.namelist() if not name.endswith('/')}


def validate(files):
    errors = []
    def need(ok, message):
        if not ok:errors.append(message)
    for name in REQUIRED:need(name in files, 'missing required file: '+name)
    try:level_mode=json.loads(files.get('starter.json',b'{}')).get('mode')!='endless'
    except (ValueError,AttributeError):level_mode=True
    if level_mode:
        for name in ('levels/README.md','levels/level_plan.json','levels/solutions.json'):
            need(name in files,'missing required file: '+name)
    if errors:return {'passed':False, 'errors':errors}
    texts = {}
    for name, raw in files.items():
        if Path(name).suffix in ('.md','.txt','.json','.csv','.tsv'):
            try:texts[name] = raw.decode('utf-8-sig')
            except UnicodeError:errors.append('UTF-8 required: '+name)
    for name, text in texts.items():
        need(not CJK.search(text), 'English-only starter text required: '+name)
        need(not re.search(r'\bTODO\b|\bTBD\b|PLACEHOLDER', text, re.I), 'unfinished field: '+name)
        need(not re.search(r'\b(?:tt|wx)[0-9a-f]{12,}\b|[\"\x27]?(?:appid|app_id|client_secret|secret|adUnitId)[\"\x27]?\s*[:=]\s*[\"\x27]?[A-Za-z0-9_-]{4,}', text, re.I), 'platform ID or credential belongs in project configuration: '+name)
    try:
        spec=json.loads(texts['starter.json']);plan=json.loads(texts.get('levels/level_plan.json','{}'))
        economy=json.loads(texts['ECONOMY.json']);proof=json.loads(texts.get('levels/solutions.json','{}'))
        need(isinstance(spec,dict) and spec.get('schema')=='design_starter.v2','starter schema must be design_starter.v2')
        need(spec.get('language')=='en','starter language must be en')
        need(spec.get('mode') in ('levels','endless'),'starter mode must be levels or endless')
        pages=spec.get('pages')
        need(isinstance(pages,list) and bool(pages),'structured pages required')
        if isinstance(pages,list):
            page_ids=[row.get('id') for row in pages]
            need(not any(str(x).lower() in ('credits','about','production_notes') for x in page_ids),'player-facing production/Credits page is not allowed')
            need(all(isinstance(x,str) and x for x in page_ids) and len(page_ids)==len(set(page_ids)),'page IDs must be nonempty and unique')
            for page in pages:
                for button in page.get('buttons',[]):
                    action=button.get('action','')
                    need(isinstance(action,str) and bool(action),'every button needs an action')
                    need(not re.search(r'league|leaderboard|ranking|share|invite|ad.?skip|cross.?promo', str(action), re.I),'forbidden button route: '+str(action))
        else:pages=[]
        need(isinstance(spec.get('features'),dict), 'starter features object required')
        features=spec.get('features',{})
        for feature in ('ranking','sharing','ad_skip','cross_promotion'):
            need(features.get(feature) is False, 'forbidden feature must be false: '+feature)
        need(features.get('daily_checkin') is False,'ordinary starter daily_checkin must be false; explicit project extensions are separate')
        need(spec.get('plan_ownership')=='import_preserve','starter plan_ownership must be import_preserve')
        need(spec.get('home_layout')=={'middle_left_min':1,'middle_right_min':1,'below_play_max':5,'button_scale':2},'home_layout must match current mobile layout contract')
        need(type(spec.get('energy_enabled')) is bool,'energy_enabled must be a boolean')
        if spec.get('energy_enabled'):need(spec.get('rewarded_energy_amount')==3,'rewarded energy is exactly +3')
        design=texts['GAME_DESIGN.md']
        need(bool(re.search(r'^#{1,6}\s+Built-in modules\s*$', design, re.M|re.I)), 'GAME_DESIGN.md needs a Built-in modules section')
        module_names=spec.get('modules')
        need(isinstance(module_names,list) and {'currency','result_x2','home_gift'}<=set(module_names),'starter modules must declare currency/result_x2/home_gift')
        need(isinstance(economy.get('currency'),str) and bool(economy['currency'].strip()),'ECONOMY.currency required')
        for collection in ('skins','backgrounds'):
            values=economy.get(collection,[])
            need(isinstance(values,list),'ECONOMY.'+collection+' must be an array')
            if isinstance(values,list):
                ids=[row.get('id') for row in values]
                need(all(isinstance(x,str) and x for x in ids) and len(ids)==len(set(ids)),collection+' IDs required and unique')
                for row in values:
                    need(all(isinstance(row.get(k),str) and row[k].strip() for k in ('name','art')),collection+' needs name and art direction')
        if spec.get('mode')=='endless':
            need(not plan and not proof,'endless starter must not supply a fake level plan or solutions')
            need('levels' not in module_names,'endless starter must not enable a level map')
            need(type(economy.get('skin_module')) is bool,'skin_module must be boolean')
            need(type(economy.get('coins_per_level')) is int and economy['coins_per_level']>0,'endless currency reference reward must be positive')
            skins=economy.get('skins',[]);backgrounds=economy.get('backgrounds',[])
            need(isinstance(skins,list) and isinstance(backgrounds,list),'skin/background arrays required')
            wanted=['limited','free']+['common']*7+['rare']*6+['epic']*3+['legendary']*2
            need(([r.get('slot') for r in skins]==wanted) if economy.get('skin_module') else (not skins and not backgrounds),'endless skin count/order mismatch')
            wanted_bg=['free']+['common']*3+['rare']*3+['epic']*2+['legendary']
            need(not backgrounds or [r.get('slot') for r in backgrounds]==wanted_bg,'endless background count/order mismatch')
            return {'passed':not errors,'errors':errors,'scope':'Data contract only; endless gameplay and prose require review.'}
        need('levels' in module_names,'level starter must enable levels module')
        total=plan.get('total_levels');mode=plan.get('limited_skin_mode')
        need(plan.get('schema')=='level_plan.v1' and plan.get('mode')=='levels','ordinary level starter requires level_plan.v1 / levels')
        need(type(total) is int and total>=70,'ordinary level starter requires at least 70 levels')
        need(mode in ('final','every_10'),'limited_skin_mode must be final or every_10')
        if type(total) is not int or total<70 or mode not in ('final','every_10'):
            return {'passed':False,'errors':errors}
        rows=plan.get('levels',[])
        need(isinstance(rows,list) and len(rows)==total,'level rows must equal total_levels')
        if not isinstance(rows,list) or not all(isinstance(row,dict) for row in rows):raise ValueError('level rows must be objects')
        need([row.get('level') for row in rows]==list(range(1,total+1)),'level rows must list 1..total in order exactly once')
        milestones=limited_levels(10,total)
        need([row['level'] for row in rows if row.get('type')=='milestone']==milestones,'milestones must be only multiples of ten; no extra tail milestone')
        from make_level_plan import bonus_places
        need(type(plan.get('seed')) is int,'bonus seed required')
        if type(plan.get('seed')) is int:
            need([row['level'] for row in rows if row.get('type')=='bonus']==bonus_places(plan['seed'],total),'bonus positions differ from saved seed; bonus levels occupy slots within total')
        errors.extend(reward_errors(plan))
        need(type(economy.get('skin_module')) is bool,'ECONOMY.skin_module must be a boolean')
        need(isinstance(economy.get('currency'),str) and economy['currency'].strip() and economy['currency']==plan.get('currency'),'currency required and must match level plan')
        need(type(economy.get('coins_per_level')) is int and economy['coins_per_level']>0 and economy['coins_per_level']==plan.get('coins_per_level'),'coins_per_level must match level reward base')
        skins=economy.get('skins');backgrounds=economy.get('backgrounds')
        need(isinstance(skins,list) and isinstance(backgrounds,list),'skins/backgrounds must be arrays')
        if not isinstance(skins,list) or not isinstance(backgrounds,list):raise ValueError('invalid economy collections')
        if economy['skin_module']:
            counts=skin_counts(total,mode);wanted=['limited']*counts['limited']+['free']+['common']*7+['rare']*6+['epic']*3+['legendary']*2
            need([row.get('slot') for row in skins]==wanted,'skin order/count must be limited + free/7 common/6 rare/3 epic/2 legendary; total '+str(counts['total']))
            need('skins' in module_names,'enabled skin module must appear in modules')
            limited=[row for row in skins if row.get('slot')=='limited']
            need([row.get('level') for row in limited]==(milestones if mode=='every_10' else [milestones[-1]]),'limited skin level mapping mismatch')
        else:need(not skins and not backgrounds,'disabled skin module must have empty skin/background arrays')
        wanted_bg=['free']+['common']*3+['rare']*3+['epic']*2+['legendary']
        need(not backgrounds or [row.get('slot') for row in backgrounds]==wanted_bg,'background order/count must be empty or free/3 common/3 rare/2 epic/1 legendary')
        ids=[row.get('id') for row in skins+backgrounds]
        need(all(isinstance(x,str) and x for x in ids) and len(ids)==len(set(ids)),'skin/background IDs required and unique')
        for row in skins+backgrounds:
            need(all(isinstance(row.get(k),str) and row[k].strip() for k in ('name','art')),'every skin/background needs a name and art direction')
        limited_by_level={row.get('level'):row.get('id') for row in skins if row.get('slot')=='limited'}
        for row in rows:
            n=row['level'];layout=row.get('layout_file')
            need(isinstance(layout,str) and layout in files,'level '+str(n)+' missing actual layout_file')
            if layout in files:need(row.get('layout_sha256')==hashlib.sha256(files[layout]).hexdigest(),'level '+str(n)+' layout SHA mismatch')
            need(type(row.get('difficulty')) in (int,float) and row['difficulty']>0,'level '+str(n)+' needs positive difficulty')
            if n in limited_by_level:need(row.get('reward')=={'type':'skin','id':limited_by_level[n]},'level '+str(n)+' skin reward does not match ECONOMY')
        proofs=proof.get('levels') if isinstance(proof,dict) else None
        need(isinstance(proofs,list) and len(proofs)==total,'solutions must cover every level')
        if isinstance(proofs,list):
            need([r.get('level') for r in proofs]==list(range(1,total+1)),'solutions must list every level exactly once')
            by={r['level']:r for r in rows}
            for row in proofs:
                need(row.get('solvable') is True and isinstance(row.get('actions'),list) and bool(row['actions']),'solution needs a nonempty proposed action sequence')
                need(row.get('layout_sha256')==by.get(row.get('level'),{}).get('layout_sha256'),'solution/layout binding mismatch')
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        errors.append('invalid starter data: '+str(exc))
    return {'passed':not errors, 'errors':errors, 'scope':'Explicit design/data contract only. Independently replay attached solutions and review English/game design before acceptance.'}


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    try:result=validate(read_files(args.input))
    except (OSError,ValueError) as exc:result={'passed':False,'errors':[str(exc)]}
    if args.out.exists():ap.error('output exists; use a new report path')
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False));sys.exit(0 if result['passed'] else 1)
