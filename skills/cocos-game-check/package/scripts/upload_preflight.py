#!/usr/bin/env python3
"""Read-only preflight delegates to the SAME Native/ZIP limits as the formal writer.

v7.7.4 (总表 B17): a ZIP must also carry a matching writer receipt (<zip>.receipt.json from build_checked_zip.py /
make_tiktok_zip.py); without one it is refused, because only the official writers install and prove the platform-kit
standard parts (DriftRacer v2 passed this check with an outdated ad service). --structure-only keeps the old
structure-only answer for diagnosis. A build directory is checked for structure only: it cannot be uploaded."""
from pathlib import Path
import argparse,json,sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent.parent.parent/'remake-core/scripts'))
from make_tiktok_zip import native_problems
from verify_native_zip import verify,TIKTOK_MAIN,TIKTOK_TOTAL,UNOFFICIAL_REFUSAL
from audit_packed_assets import audit

def inspect(path,structure_only=False):
 result={'candidate':str(path.resolve()),'status':'refuse','errors':[]}
 try:
  if path.is_file():
   v=verify(path);sizes={'total':v['uncompressed_total_bytes'],'main':v['main_bytes']};problems=[]
   result.update(entry=v.get('entry'),entry_reason=v.get('entry_reason'))
   if v.get('entry')!='official' and not structure_only:problems.append(UNOFFICIAL_REFUSAL%v.get('entry_reason'))
  elif path.is_dir():
   problems,_,sizes=native_problems(path);asset=audit(path);problems+=asset['errors']
   result['note']='build directory: structure only; the uploadable ZIP must come from build_checked_zip.py or make_tiktok_zip.py'
  else:raise ValueError('candidate does not exist')
  result.update(total_uncompressed_bytes=sizes.get('total'),main_uncompressed_bytes=sizes.get('main'),total_limit_bytes=TIKTOK_TOTAL,main_limit_bytes=TIKTOK_MAIN,errors=problems,status='refuse' if problems else 'pass')
  if structure_only:result['mode']='structure-only (not an upload approval)'
 except Exception as e:result['errors']=[str(e)]
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('candidate',type=Path);p.add_argument('--json',action='store_true');p.add_argument('--structure-only',action='store_true',help='structure diagnosis only; do not require the writer receipt');a=p.parse_args();r=inspect(a.candidate,a.structure_only);print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(r['status']!='pass')
