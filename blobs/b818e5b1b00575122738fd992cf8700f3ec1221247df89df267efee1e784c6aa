"""Authenticate the sole Ego-only browser selector change; never runs a browser.

Old aggregated tool identities remain old. Current executions use current tool
identities. No assertion, test case, host, suite or other function may change.
"""
import ast,hashlib,json
from pathlib import Path
OLD_AD='5cf740c48a6b10c08a52429be0431690fa0ca0147e856d73accded60c3781dfa'
OLD_RT='c35d539eca7c9ccdb790cc348b92d808d79fe931a348a7167f85a6d5bf54dfd5'
WRAPPER_SHA='fb806eacecb06ac5d785283b086ef66bf915b82070085601d34d07b1549e0645'
OLD_CASES_SHA='0cfc836970d9bf6f9b18c605bf7bc2088a8ee2d25d2a29fe58c05f5257a4363f'
OLD_LIB_SHA='1659eb4e4e579a41274e291cfbfb388b06ca8198fe7e29ed586263ce9722d2b8'
PIN={
 'ad_regression.py':('cce89b866e64f75fe3995a0179c793e246c0ec53dedfee58d1ec5495ed7cb7b6','caffc9a8a8aae4afbc313fe4b49717b82dd161517db38f59b49e8a94279e233d'),
 'runtime_regression.py':('9bc8196ea8cb0c4f06d1ffc2b8461e8661d25c320eb93192336549765621227f','941e6b7e1298377e4ed41db6abef1b9df7b612176a03aa15de8b9def8e5de19c')}
def sha(b):return hashlib.sha256(b).hexdigest()
def need(ok,why):
 if not ok:raise ValueError('browser selector equivalence: '+why)
def ref(p):return {'path':str(Path(p).resolve()),'sha256':sha(Path(p).read_bytes())}
def split(raw):
 s=raw.decode();nodes=[n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)and n.name=='find_browser'];need(len(nodes)==1,'unique selector function required');n=nodes[0];lines=s.splitlines(True)
 return ''.join(lines[n.lineno-1:n.end_lineno]),''.join(lines[:n.lineno-1]+lines[n.end_lineno:])
def validate(project,old_ad,old_rt):
 import ad_regression as A,runtime_regression as R
 need(old_ad==OLD_AD and old_rt==OLD_RT,'not the authenticated R17 tool pair')
 root=Path(project).resolve()/'qa/rework-baseline/R17/tools';sources={};files={}
 for name,(oldsha,newfuncsha)in PIN.items():
  old=root/name;new=A.HERE/name;ob=old.read_bytes();nb=new.read_bytes();need(sha(ob)==oldsha,'preserved prior source differs: '+name)
  of,oremainder=split(ob);nf,nremainder=split(nb)
  need(sha(nf.encode())==newfuncsha,'current selector is not the precise Ego-only function: '+name)
  need(oremainder==nremainder,'code outside browser selection changed: '+name)
  need(ast.dump(ast.parse(oremainder),include_attributes=False)==ast.dump(ast.parse(nremainder),include_attributes=False),'assertion AST differs')
  sources[name]={'original_source':ref(old),'current_source':ref(new),'old_browser_function_sha256':sha(of.encode()),'new_browser_function_sha256':sha(nf.encode()),'unchanged_remainder_sha256':sha(oremainder.encode())};files[name]=ob
 oldcases=root/'ad_regression.cases.mjs';oldlib=root/'runtime_regression.lib.mjs';wrapper=A.HERE/'ego_test_page.mjs'
 need(sha(oldcases.read_bytes())==OLD_CASES_SHA and sha(oldlib.read_bytes())==OLD_LIB_SHA,'preserved original transport caller changed')
 need(sha(wrapper.read_bytes())==WRAPPER_SHA,'current Ego viewport/screenshot wrapper differs from exact reviewed transport')
 imp="import {wrapEgoPage} from '../ego_test_page.mjs';\n"
 transport=[]
 for original,current,call,revert in ((oldcases,A.TOOL/'cases.mjs',"  page = wrapEgoPage(task.page('p1'));","  page = task.page('p1');"),(oldlib,R.TOOL/'lib.mjs',"  const page = wrapEgoPage(task.page(name || 'p1'));","  const page = task.page(name || 'p1');")):
  text=current.read_text();need(text.count(imp)==1 and text.count(call)==1,'exact wrapper import/page factory shape differs')
  reversed_text=text.replace(imp,'',1).replace(call,revert,1)
  need(reversed_text.encode()==original.read_bytes(),'test assertions/body changed beyond wrapper import and page factory')
  transport.append({'original_source':ref(original),'current_source':ref(current),'reversed_body_sha256':sha(reversed_text.encode())})
 h=hashlib.sha256()
 for name in ('host.js','play.html','server.py','cases.mjs'):h.update(name.encode()+b'\0'+(oldcases.read_bytes()if name=='cases.mjs'else(A.TOOL/name).read_bytes()))
 h.update(b'watched_run.py\0'+(A.HERE/'watched_run.py').read_bytes());h.update(files['ad_regression.py']);need(h.hexdigest()==OLD_AD,'old ad aggregate does not authenticate all unchanged cases/host inputs')
 h=hashlib.sha256()
 for p in sorted(list(R.HOST2.glob('*.js'))+list(R.HOST2.glob('*.py'))+list(R.HOST2.glob('*.html'))+list(R.TOOL.glob('*.mjs'))+list(R.HOST3.glob('*'))):
  if p.is_file():h.update(p.name.encode()+b'\0'+(oldlib.read_bytes()if p==R.TOOL/'lib.mjs'else p.read_bytes()))
 catalog=R.load_suites()
 for name in sorted(catalog):h.update(name.encode()+b'\0'+catalog[name]['script'].read_bytes())
 h.update(b'watched_run.py\0'+(R.HERE/'watched_run.py').read_bytes());h.update(files['runtime_regression.py']);need(h.hexdigest()==OLD_RT,'old runtime aggregate does not authenticate all unchanged suites/host inputs')
 return {'schema':'browser_selector_equivalence.v1','tool':ref(__file__),'original_tool_sha256':{'rewarded_ad_regression':OLD_AD,'runtime_regression':OLD_RT},'current_tool_sha256':{'rewarded_ad_regression':A.tool_digest(),'runtime_regression':R.tool_digest(catalog)},'sources':sources,'transport_callers':transport,'ego_viewport_screenshot_wrapper':ref(wrapper),'source_origin':ref(root/'source-origin.json'),'scope':'Only exact Ego-only find_browser plus exact Page transport wrapper import/factory changed. Wrapper re-applies requested metrics and captures actual CDP PNG bytes; it never computes a test verdict, reward or business result. All other source bytes, assertion AST, hosts and suite bodies authenticated by original receipt aggregate hashes. Prior executions retain prior tool identity.'}
