#!/usr/bin/env python3
"""Auto execute the known Cocos2 GrowthLedger storage contract, not checklist attestations.
Unsupported matches fail closed. Absence means this specific probe is not applicable,
not that all storage or all rewards passed.
"""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent

def probe(native,web):
 def bundles(root):
  return [p for p in root.rglob('*.js') if 'GrowthLedger:[function' in p.read_text(errors='replace')]
 ns,ws=bundles(native),bundles(web)
 # Web exports can retain old bundles; resolve the active version from settings,
 # never pick the first regex match or an obsolete unversioned file.
 settings=web/'src/settings.js'
 if settings.is_file():
  match=re.search(r'["\']?main["\']?\s*:\s*["\']([^"\']+)["\']',settings.read_text())
  if match:ws=[p for p in ws if p.name=='index.'+match[1]+'.js']
 report={'tool':'run_reward_storage_probe','passed':False,'applicable':bool(ns or ws),'checked_files':{}}
 if not ns and not ws:
  candidates=[]
  for root in [native,web]:
   active=root/'assets/main/index.js'
   if root==web:
    match=re.search(r'["\']?main["\']?\s*:\s*["\']([^"\']+)["\']', (root/'src/settings.js').read_text() if (root/'src/settings.js').is_file() else '')
    if match:active=root/('assets/main/index.'+match[1]+'.js')
   if active.is_file():
    code=active.read_text(errors='replace')
    if 'platformEnergyStateKey=function' in code and ':energy-rewards-v1' in code and 'commitRewardedAdPower=function' in code:candidates.append((root,active))
  if candidates:
   if len(candidates)!=2:return dict(report,status='refused',applicable=True,error='PaperCut energy ledger must be present in both active Native and Web bundles')
   checks=[]
   for root,active in candidates:
    p=subprocess.run(['node',str(HERE/'probe_cocos2_papercut_storage.cjs'),str(root)],capture_output=True,text=True,timeout=45)
    try:result=json.loads(p.stdout)
    except ValueError:result={'passed':False,'error':p.stderr[-1000:]}
    checks.append(result);report['checked_files'][str(active)]=hashlib.sha256(active.read_bytes()).hexdigest()
   return dict(report,applicable=True,passed=all(x.get('passed') is True for x in checks),status='passed' if all(x.get('passed') is True for x in checks) else 'failed',protocol='papercut_energy_storage',execution=checks)
  return dict(report,passed=True,status='not_applicable',reason='No recognized GrowthLedger/PaperCut ledger; other persistence requires its own executable probe/coverage.')
 if len(ns)!=1 or len(ws)!=1:return dict(report,status='refused',error='Recognized ledger must resolve to exactly one actual Native and Web bundle; unsupported layout must not silently pass.')
 adapter=native/'adapter-min.js'
 if not adapter.is_file():return dict(report,status='refused',error='Native adapter missing')
 for p in [ns[0],ws[0],adapter]:report['checked_files'][str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest()
 # Known exported placeholder chain, not a heuristic that all empty handlers
 # are invalid. All three conditions are needed; uncertain layouts remain UI QA.
 empty_rank=[]
 for layer,p in [('native',ns[0]),('web',ws[0])]:
  text=p.read_text()
  if ('getRank=function(){}' in text and 'this.btnRank.on("click",this.onRankClick,this)' in text
      and re.search(r'onRankClick=function\([^)]*\)\{[^}]*toggle\([^}]*ENUM_UI_TYPE\.RANK',text)):
   empty_rank.append(layer)
 report['empty_original_ranking_chain']=empty_rank
 # JS harness uses the actual exported Native module path. Other names/layouts
 # intentionally fail rather than substituting a new ledger implementation.
 if ns[0].relative_to(native).as_posix()!='assets/main/index.js':return dict(report,status='refused',error='Unsupported Native module entry; add a calibrated production loader')
 try:
  p=subprocess.run(['node',str(HERE/'probe_cocos2_reward_storage.cjs'),str(native),str(web),str(ws[0])],capture_output=True,text=True,timeout=45)
  if p.returncode:return dict(report,status='failed',error=p.stderr[-2500:])
  result=json.loads(p.stdout.strip().splitlines()[-1]);report.update(passed=result.get('passed') is True,status='passed',execution=result)
 except (OSError,ValueError,subprocess.TimeoutExpired) as e:report.update(status='refused',error=str(e))
 if empty_rank:report.update(passed=False,status='failed',legacy_entry_error='Reachable ranking handler opens a panel while getRank is empty: '+','.join(empty_rank))
 return report

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--native',required=True,type=Path);a.add_argument('--web',required=True,type=Path);a.add_argument('--out',type=Path);args=a.parse_args()
 r=probe(args.native.resolve(),args.web.resolve())
 if args.out:args.out.write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(r));return 0 if r['passed'] else 1
if __name__=='__main__':sys.exit(main())
