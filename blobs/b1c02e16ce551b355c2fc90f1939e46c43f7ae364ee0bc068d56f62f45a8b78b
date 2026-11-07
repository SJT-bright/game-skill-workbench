"""Exact R18 -> R19 loading-logo visibility change; read-only, fail closed.
validate(old_zip, new_files, adapter, scope=None) -> proof; no browser or build.
"""
import copy,hashlib,importlib.util,json,os,zipfile
from pathlib import Path
SCHEMA='debrand-logo-visibility.v1'
ZIP_SHA='c0e2ce0023422fe60d5b8fdbb82b294491f5e619782f247029f50ea7e5351d3a'
RECEIPT_SHA='360d86654131f7bce165010bdae548785afda5e9b1a8c59f38ec6ead358d01a4'
DECODER_SHA='0380e4c70d1e8293a2e2e46df6cdf22a8a52be4069233450ba25efa8eb78745c'
SCENE='assets/scenes/Main.scene'
PACK='assets/main/import/04/046fe66ac.json'
NODE='Main/Canvas/LoadingLayer/ui/logo'
def sha(b):return hashlib.sha256(b).hexdigest()
def need(ok,why):
 if not ok:raise ValueError('debrand exact delta: '+why)
def ref(p):return {'path':str(Path(p).resolve()),'sha256':sha(Path(p).read_bytes())}
def read(p):return json.loads(Path(p).read_text())
def module(p,name):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def tree(files):
 h=hashlib.sha256()
 for k in sorted(files):h.update(k.encode()+b'\0'+sha(files[k]).encode()+b'\n')
 return h.hexdigest()
def nodepath(node,objects=None):
 out=[];seen=set()
 while isinstance(node,dict):
  need(id(node)not in seen,'parent cycle');seen.add(id(node));out.append(node.get('_name',''))
  parent=node.get('_parent');node=(objects[parent['__id__']]if objects is not None and parent else parent)
 return '/'.join(reversed(out))
def validate(old_zip,new_files,adapter,scope=None):
 import ad_regression as A,runtime_regression as R
 scope=Path(scope or os.environ.get('DEBRAND_DELTA_SCOPE',''));need(scope.is_file(),'DEBRAND_DELTA_SCOPE missing');s=read(scope);need(s.get('schema')==SCHEMA,'scope schema differs')
 project=Path(s['project']).resolve();old_zip=Path(old_zip).resolve()
 need(old_zip==project/'qa/rework-baseline/R18/ShellStrike_R18_TikTok.zip'and s.get('old_zip')==ref(old_zip)and sha(old_zip.read_bytes())==ZIP_SHA,'not the stable actual R18 ZIP')
 receipt=Path(str(old_zip)+'.receipt.json');need(s.get('old_receipt')==ref(receipt)and sha(receipt.read_bytes())==RECEIPT_SHA,'original R18 receipt differs');record=read(receipt)
 need(record.get('tool')=='build_checked_zip'and record.get('zip_sha256')==ZIP_SHA,'R18 was not the matching official writer result')
 regressions=record['regressions'];ad=regressions['rewarded_ad_regression'];rt=regressions['runtime_regression']
 need(ad.get('passed')is True and rt.get('passed')is True,'original R18 regressions did not pass')
 prior=rt['rework']['optional_art_delta'];invref=prior['source']['inventory'];inventoryfile=Path(invref['path']);need(ref(inventoryfile)==invref,'original R17 raw source inventory changed')
 before=read(inventoryfile)['current_assets'].copy();before.update(prior['source']['after'])
 actual={p.relative_to(project).as_posix():sha(p.read_bytes())for p in(project/'assets').rglob('*')if p.is_file()}
 changed=sorted(k for k in set(before)|set(actual)if before.get(k)!=actual.get(k))
 need([k for k in changed if k!='assets/.DS_Store']==[SCENE],'production source differs beyond single scene visibility change: '+repr(changed))
 old_scene=Path(s['original_scene']['path']);need(ref(old_scene)==s['original_scene']and sha(old_scene.read_bytes())==before[SCENE],'original R18 scene bytes differ from authenticated inventory')
 a=read(old_scene);b=read(project/SCENE);ids=[i for i,o in enumerate(a)if o.get('__type__')=='cc.Node'and nodepath(o,a)==NODE]
 need(len(ids)==1,'exact original loading logo missing/ambiguous');i=ids[0];need(a[i].get('_active')is True,'original target was not active')
 expected=copy.deepcopy(a);expected[i]['_active']=False;need(expected==b,'scene changed beyond exact loading logo _active true -> false')
 need(sha(Path(adapter).read_bytes())==rt.get('adapter_sha256')==prior['adapter']['sha256'],'adapter must remain byte-identical to current R18 adapter')
 decoder=Path(__file__).with_name('play_art_delta_guard.py');need(sha(decoder.read_bytes())==DECODER_SHA,'reviewed pure compiled-graph decoder changed');D=module(decoder,'_debrand_compiled_decoder')
 with zipfile.ZipFile(old_zip)as z:
  need(z.testzip()is None,'R18 ZIP CRC failure');old={n:z.read(n)for n in z.namelist()if not n.endswith('/')}
 need(set(old)==set(new_files),'Native membership changed');native_changed=sorted(k for k in old if old[k]!=new_files[k]);need(native_changed==[PACK],'Native changed beyond exact scene pack: '+repr(native_changed))
 aa=D.decode_pack(old[PACK]);bb=D.decode_pack(new_files[PACK]);need(len(aa)==len(bb)==6,'scene packed membership changed')
 oldnodes=[n for n in D.find_nodes(aa,'logo')if nodepath(n)==NODE];newnodes=[n for n in D.find_nodes(bb,'logo')if nodepath(n)==NODE]
 need(len(oldnodes)==len(newnodes)==1,'compiled logo missing/ambiguous');on,nn=oldnodes[0],newnodes[0]
 need(on.get('_active',True)is True and nn.get('_active')is False,'compiled target is not exact active true -> false')
 if '_active'in on:nn['_active']=on['_active']
 else:del nn['_active']
 need(D.canonical(aa)==D.canonical(bb),'other compiled scene or packed asset fields/references changed')
 # R18 inherited ad execution intentionally keeps its original adapter/tool
 # identity. Authenticate that exact prior chain, without calling PLAY.source
 # against this newly changed scene.
 policy=rt['rework']['browser_policy_tool_equivalence'];policypath=Path(policy['tool']['path']);need(ref(policypath)==policy['tool'],'R18 browser-policy equivalence validator changed')
 P=module(policypath,'_debrand_prior_policy');verified=P.validate(project,policy['original_tool_sha256']['rewarded_ad_regression'],policy['original_tool_sha256']['runtime_regression'])
 need(verified==policy,'R18 inherited tool/body equivalence no longer holds')
 need(ad.get('tool_sha256')==policy['original_tool_sha256']['rewarded_ad_regression']and ad.get('adapter_sha256')==prior['old_adapter']['sha256'],'R18 inherited ad execution identity differs')
 need(rt.get('tool_sha256')==R.tool_digest(R.load_suites())and A.tool_digest()==policy['current_tool_sha256']['rewarded_ad_regression'],'current functional check tools differ from R18')
 return {'schema':SCHEMA,'guard':ref(__file__),'decoder':ref(decoder),'scope':ref(scope),'old_zip':ref(old_zip),'old_receipt':ref(receipt),'adapter':ref(adapter),'source':{'inventory':invref,'original_scene':ref(old_scene),'semantic_changed':[SCENE],'changed':changed,'before':before[SCENE],'after':actual[SCENE],'nonrendering_metadata':{k:{'before':before.get(k),'after':actual.get(k)}for k in changed if k=='assets/.DS_Store'},'target_node':NODE,'original_active':True,'current_active':False},'native':{'old_native_tree_sha256':tree(old),'native_tree_sha256':tree(new_files),'changed':native_changed,'files':{PACK:{'before':sha(old[PACK]),'after':sha(new_files[PACK])}},'comparison':'entire six-section compiled graph identical after reversing exactly logo._active'},'inherited_ad':{'original_adapter_sha256':ad['adapter_sha256'],'original_tool_sha256':ad['tool_sha256'],'current_adapter_sha256':rt['adapter_sha256'],'current_tool_sha256':A.tool_digest(),'source_receipt':ref(receipt),'original_reused_from':ad.get('reused_from'),'browser_policy_equivalence':policy},'rerun':['layout_state','startup3x'],'reuse_semantics':'Only loading logo visibility changed. Original functional/ad/image-hold executions retain their R18/R17 identities; no new execution is asserted.'}
if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--old',required=True);ap.add_argument('--native',required=True);ap.add_argument('--adapter',required=True);ap.add_argument('--scope',required=True);ap.add_argument('--out');args=ap.parse_args()
 root=Path(args.native);files={p.relative_to(root).as_posix():p.read_bytes()for p in root.rglob('*')if p.is_file()};d=validate(args.old,files,args.adapter,args.scope);text=json.dumps(d,ensure_ascii=False,indent=2)+'\n'
 if args.out:Path(args.out).write_text(text)
 print(text)
