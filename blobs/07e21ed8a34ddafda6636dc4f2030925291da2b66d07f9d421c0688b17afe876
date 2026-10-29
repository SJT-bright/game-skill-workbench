#!/usr/bin/env python3
"""Read-only preflight delegates to the SAME Native/ZIP limits as the formal writer."""
from pathlib import Path
import argparse,json,sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent.parent.parent/'remake-core/scripts'))
from make_tiktok_zip import native_problems
from verify_native_zip import verify,TIKTOK_MAIN,TIKTOK_TOTAL
from audit_packed_assets import audit

def inspect(path):
 result={'candidate':str(path.resolve()),'status':'refuse','errors':[]}
 try:
  if path.is_file():
   v=verify(path);sizes={'total':v['uncompressed_total_bytes'],'main':v['main_bytes']};problems=[]
  elif path.is_dir():
   problems,_,sizes=native_problems(path);asset=audit(path);problems+=asset['errors']
  else:raise ValueError('candidate does not exist')
  result.update(total_uncompressed_bytes=sizes.get('total'),main_uncompressed_bytes=sizes.get('main'),total_limit_bytes=TIKTOK_TOTAL,main_limit_bytes=TIKTOK_MAIN,errors=problems,status='refuse' if problems else 'pass')
 except Exception as e:result['errors']=[str(e)]
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('candidate',type=Path);p.add_argument('--json',action='store_true');a=p.parse_args();r=inspect(a.candidate);print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(r['status']!='pass')
