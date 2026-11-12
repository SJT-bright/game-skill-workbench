"""Read-only R19 name-visibility successor. Historical runs retain historical identity."""
from pathlib import Path
import hashlib,json,re,os,sys
from PIL import Image
import audit_native_startup_renderer as R
import startup_play_successor as S
S_SHA='6100770ed5fb7af24c78bd5671ab1d2e8b17e095473890f27a03e46d81badd14'
OLD_ENV_SHA='f2e636d43d9e28e98ebaa2dbddbbf5deedace40240a94bef433c4adfd788626a'
OLD_CONTRACT_SHA='fbbfc262c73532e00a8f48fa11a32d9222c487c3b86985111e58b7ed1c5b2298'
OLD_TREE='091e65517c99dfe08583c576a36434f9485037843ed19b55e6e25ee4380bf901'
PLAY_D_SHA='0380e4c70d1e8293a2e2e46df6cdf22a8a52be4069233450ba25efa8eb78745c'
SCENE='assets/scenes/Main.scene'
SCHEMA='shellstrike_debrand_loading_successor.v1'
SUCCESSOR_PATH='docs/startup/loading-runtime-r19-successor.json'
DELTA_TOOL=Path(__file__).resolve().parents[2]/'cocos-game-check/package-check/scripts/debrand_delta_guard.py'
NAME_UUIDS={'5b69458c-85d4-4781-9fef-97b5bded02b0','0d11d70a-0c77-4e00-bdd6-2fb72e3a3ce4'}
NAME_TEXT=re.compile(r'shell\s*strike|末日特工队|蛋壳特工队',re.I)
read=S.read;sha=S.sha;checked=S.checked

def need(ok,message):
 if not ok:raise ValueError('Debrand startup: '+message)
def original_helper():
 need(Path(S.__file__).resolve()==Path(__file__).resolve().with_name('startup_play_successor.py')and sha(S.__file__)==S_SHA,'original PLAY checker identity changed')
def capture(project,record,vp,loading=False):
 dfile=checked(project,record['dump']);png=checked(project,record['screenshot']);d=read(dfile)
 need(d.get('origin')=='strict-native-host'and not d.get('errors')and not d.get('truncated')and not d.get('error'),'original dump invalid')
 need((d.get('page',{}).get('width'),d.get('page',{}).get('height'))==vp and Path(d.get('screenshot','')).resolve()==png,'actual capture viewport/pair differs')
 with Image.open(png)as image:need(image.width>=vp[0]and image.height>=vp[1]and abs(image.width/image.height-vp[0]/vp[1])<.01,'actual PNG dimensions differ')
 nodes=d.get('nodes',[]);need(bool(nodes),'rendered node inventory missing')
 for n in nodes:
  c=n.get('comps',{});sp=c.get('sprite',{});lab=c.get('label',{})
  need(not any(u in str(sp.get('frame_uuid',''))or u in str(sp.get('image_uuid',''))for u in NAME_UUIDS)and not NAME_TEXT.search(str(lab.get('string',''))),'actual dump displays game-name image/text')
 if loading:
  need(any(n['path']=='Canvas/LoadingLayer/ui'for n in nodes)and not any(n['path']=='Canvas/LoadingLayer/ui/logo'for n in nodes),'loading inventory missing or disabled logo rendered')
  need('startup_case=request-clock'in d.get('url',''),'loading capture does not come from actual delayed startup')
 else:
  S._capture(project,record,vp,'normal_home')
 return {'dump':str(dfile),'screenshot':str(png),'viewport':list(vp)}
def validate_current_debrand_report(project,native,report_ref):
 original_helper();project=Path(project).resolve();native=Path(native).resolve();file=checked(project,report_ref);d=read(file);binding=d.get('binding',{})
 need(d.get('schema')=='shellstrike_no_game_name.v1'and d.get('expected_viewports')==[[393,852],[375,667]],'current report schema/phone set differs')
 need(native.is_relative_to(project)and Path(d.get('native_root','')).resolve()==native and R.digest(R.tree(native))==binding.get('native_tree_sha256'),'current full Native identity differs')
 rows=d.get('normal',[]);need(len(rows)==2 and {tuple(r.get('viewport',[]))for r in rows}==S.VPS,'two distinct actual normal executions required')
 normals=[]
 for row in rows:
  _,raw=S.validate_renderer_reference(project,native,binding,row['renderer_report']);vp=tuple(row['viewport']);need(tuple(raw['viewport'])==vp,'normal raw viewport differs')
  c=raw.get('home',{}).get('capture',{});pair={'dump':{'path':c['file'],'sha256':c['dump_sha256']},'screenshot':{'path':c['png'],'sha256':c['screenshot_sha256']}}
  normals.append({'viewport':list(vp),'renderer_report':row['renderer_report'],'home_capture':capture(project,pair,vp)})
 loadingfile=checked(project,d['loading_report']);loading=read(loadingfile);executions=loading.get('executions',[])
 need(loading.get('schema')=='shellstrike_no_name_loading.v1'and loading.get('binding')==binding and Path(loading.get('native_root','')).resolve()==native and loading.get('passed')is True and not loading.get('errors')and loading.get('run_id'),'actual current loading collector identity/result differs')
 need(len(executions)==2 and {tuple(r.get('viewport',[]))for r in executions}==S.VPS,'two distinct actual loading phone executions required')
 captures=[]
 for row in executions:
  logo=row.get('logo',{});need(logo.get('path')=='Canvas/LoadingLayer/ui/logo'and logo.get('exists')is True and logo.get('active')is False and logo.get('active_in_hierarchy')is False and logo.get('sprite_uuid')=='5b69458c-85d4-4781-9fef-97b5bded02b0@f9941','actual original logo is not observed disabled')
  need(row.get('loading_active')is True and row.get('after_draw_observed')is True and row.get('name_sprites')==[]and row.get('name_labels')==[]and not row.get('first_exception'),'actual loading visibility/error observation failed')
  need(any(r.get('targeted')and r.get('status')=='delayed'for r in row.get('requests',[]))and not any(len(e)>1 and e[1]in('console.error','window.error')for e in row.get('phase_events',[])),'actual loading delay missing or runtime error present')
  captures.append(capture(project,row['capture'],tuple(row['viewport']),True))
 return {'schema':'shellstrike_no_game_name.checked.v1','report':str(file),'report_sha256':sha(file),'binding':binding,'native_root':str(native),'normal_executions':2,'loading_logo_disabled_executions':2,'normal':normals,'loading':captures,'scope':'Current normal trusted PLAY and actual disabled loading-name node only; historical fault executions keep their old identities.'}

class HistoricalSourcePath:
 """Read-only R18 source reconstruction: only Main.scene is supplied by its retained
 original bytes. The new exact delta guard must run first and prove this substitution.
 No file writes, path rebinding, current observations, or arbitrary overlay is allowed.
 """
 def __init__(self,path,project,original):self.path=Path(path);self.project=Path(project);self.original=Path(original)
 def __truediv__(self,value):return HistoricalSourcePath(self.path/value,self.project,self.original)
 def __fspath__(self):return os.fspath(self.path)
 def __str__(self):return str(self.path)
 def relative_to(self,other):return self.path.relative_to(Path(os.fspath(other)))
 def read_bytes(self):return(self.original if self.path==self.project/SCENE else self.path).read_bytes()
 def read_text(self):return self.read_bytes().decode()
 def is_file(self):return self.path.is_file()
 @property
 def suffix(self):return self.path.suffix
 def rglob(self,pattern):return(HistoricalSourcePath(p,self.project,self.original)for p in self.path.rglob(pattern))

def validate_loading_successor(data,binding,project):
 import zipfile
 original_helper();project=Path(project).resolve();native=Path(data.get('native_root','')).resolve()
 need(data.get('schema')==SCHEMA and data.get('profile')=='shellstrike_native_startup_v1'and data.get('binding')==binding,'successor schema/profile/binding differs')
 need(native.is_relative_to(project)and R.digest(R.tree(native))==binding.get('native_tree_sha256'),'successor full Native identity differs')
 prior=data['predecessor'];envfile=checked(project,prior['loading_envelope']);contractfile=checked(project,prior['startup_contract']);need(sha(envfile)==OLD_ENV_SHA and sha(contractfile)==OLD_CONTRACT_SHA,'original R18 official envelope/contract changed')
 old=read(envfile);oldbinding=old['binding'];oldnative=Path(old['native_root']);need(oldbinding['native_tree_sha256']==OLD_TREE and R.digest(R.tree(oldnative))==OLD_TREE,'original executed R18 Native changed/rebound')
 contract=read(contractfile);need(contract.get('passed')is True and contract.get('tool')=='audit_startup_contract'and contract.get('binding')==oldbinding,'original R18 official startup contract failed/rebound')
 semantic=data['semantic_delta'];need(Path(semantic['tool_record']['path']).resolve()==DELTA_TOOL and sha(DELTA_TOOL)==semantic['tool_record']['sha256'],'canonical debrand guard changed')
 D=S._fixed_module(DELTA_TOOL,'shellstrike_debrand_guard');files={p.relative_to(native).as_posix():p.read_bytes()for p in native.rglob('*')if p.is_file()}
 old_sys_path=list(sys.path)
 try:
  sys.path.insert(0,str(DELTA_TOOL.parent))
  delta=D.validate(checked(project,prior['zip']),files,checked(project,semantic['adapter']),checked(project,semantic['scope']))
 finally:sys.path[:]=old_sys_path
 need(delta==read(checked(project,semantic['proof'])),'actual debrand delta differs from recorded proof')
 # Run unchanged original R17 strict assertions under the original R17 binding.
 first=old['predecessor'];need(first['binding']==S.OLD_BINDING,'original R17 binding changed')
 index=checked(project,first['loading_index']);controls=checked(project,first['controls']);need(sha(index)==S.OLD_INDEX_SHA and sha(controls)==S.OLD_CONTROLS_SHA,'original matrix/control bytes changed')
 legacy=project/'qa/startup-contract-r17-locked.py';need(sha(legacy)==S.OLD_VALIDATOR_SHA,'original strict validator changed');L=S._fixed_module(legacy,'shellstrike_r17_strict_debrand')
 errors=L.validate_loading(read(index),S.OLD_BINDING,index.parent);need(not errors,'original 26-case assertions failed: '+repr(errors))
 old17=Path(first['native_root']);need(R.digest(R.tree(old17))==S.OLD_TREE,'original R17 Native changed')
 oldreport=read(checked(project,first['renderer_report']));oldraw=read(checked(project,oldreport['raw']));assertions=[]
 L.validate(oldreport,old17,S.OLD_BINDING,project,oldraw,lambda ok,msg:None if ok else assertions.append(msg),lambda r,label:checked(project,r));need(not assertions,'original controls/renderer assertions failed: '+repr(assertions))
 # Re-run original PLAY delta predicates on the original bytes, explicitly
 # reconstructed source. All current-to-original differences were proved above.
 play=old['semantic_delta'];need(sha(S.DELTA_TOOL)==PLAY_D_SHA and play['tool_record']['sha256']==PLAY_D_SHA,'original PLAY guard identity changed');PD=S._fixed_module(S.DELTA_TOOL,'shellstrike_original_play_guard')
 playproof=read(checked(project,play['proof']));scope=read(checked(project,play['scope']));original=project/'docs/test/no-game-name-r19/Main.scene.r18-original'
 need(original.is_file(),'retained original scene missing')
 a=json.loads(original.read_bytes());b=read(project/SCENE);need(a[27]['_active']is True and b[27]['_active']is False,'original/current logo source state differs');b[27]['_active']=True;need(a==b,'source exceeds one logo active property')
 source=PD.source_delta(HistoricalSourcePath(project,project,original),Path(scope['original_dir']));need(source==playproof['source'],'historical original PLAY source assertions differ')
 with zipfile.ZipFile(checked(project,first['zip']))as z:old17files={n:z.read(n)for n in z.namelist()if not n.endswith('/')}
 old18files={p.relative_to(oldnative).as_posix():p.read_bytes()for p in oldnative.rglob('*')if p.is_file()};need(PD.native_delta(old17files,old18files)==playproof['native'],'historical original PLAY Native assertions differ')
 historical=S.validate_current_play_report(project,oldnative,old['current_play_proof']);need(historical['binding']==oldbinding,'historical PLAY proof rebound')
 current=validate_current_debrand_report(project,native,data['current_debrand_proof']);need(current['binding']==binding,'new observations bind another current build')
 return {'schema':'shellstrike_debrand_loading_successor.checked.v1','current_binding':binding,'current_native_root':str(native),'predecessor_binding':oldbinding,'predecessor_cases_checked':26,'historical_play':historical,'exact_delta':delta,'current_affected_state':current,'reuse_semantics':'Original R17 fault cases and original R18 PLAY cases retain original Native identity. Only R19 normal/name-visibility observations are new.'}
