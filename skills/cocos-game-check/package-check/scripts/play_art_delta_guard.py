#!/usr/bin/env python3
"""Strict, read-only exception for the R17 PLAY optional-art dependency repair.

validate(old_zip, new_files, adapter, scope=None) returns a proof or raises ValueError.
new_files is {Native relative path: bytes}; no old execution is re-dated/rebound.
scope is a JSON path (or PLAY_ART_DELTA_SCOPE), with project, original_dir.
The R17 source inventory and official ZIP identity are independently pinned here.
"""
import copy, hashlib, json, os, re, struct, subprocess, zipfile
from pathlib import Path

SCHEMA = 'play-art-decoupling.v1'
OLD_ZIP_SHA = '1d36efac779d14885799a8f19cb1f875a254818bc2b4568724fc65977cecdbf1'
OLD_RECEIPT_SHA = '2bfc696b34dee3125bcca90a8d350b4b77f29d3445ff4f6ba295ea546d1208a8'
SOURCE_DIFF_SHA = 'fc724a6fc89cb98652ae9a2bc00278c7c9e53f4cdf7b692df84af04134829576'
PREFAB = 'assets/res/layer/MainLayer.prefab'
SCRIPT = 'assets/scripts/english/EnglishUI.ts'
HOME = 'assets/scripts/game/compoment/layer/HomeLayer.ts'
INSERT = "        const fallback = node.getChildByName('ArtLoadFallback');\n        if (fallback) fallback.active = false;\n"
ASYNC_INSERT = "    const fallback = node.getChildByName('ArtLoadFallback');\n    if (fallback) bundle.load('btnres/ui_yellow/spriteFrame', SpriteFrame, (error, frame) => {\n        if (error || !fallback.isValid) return;\n        fallback.getComponent(Sprite).spriteFrame = frame;\n    });\n"
BLANK = '8e0aad79-556b-4a79-bed9-81abd32bb286@f9941'
TERSER = '/Applications/Cocos/Creator/3.8.8/CocosCreator.app/Contents/Resources/resources/3d/engine/node_modules/terser'
def sha(b): return hashlib.sha256(b).hexdigest()
def tree_sha(files):
    h=hashlib.sha256()
    for k in sorted(files):h.update(k.encode()+b'\0'+sha(files[k]).encode()+b'\n')
    return h.hexdigest()
def need(ok, why):
    if not ok: raise ValueError('PLAY delta: ' + why)
def ref(p): return {'path': str(Path(p).resolve()), 'sha256': sha(Path(p).read_bytes())}

def source_delta(project, originals):
    invpath = project/'docs/art/user-approved-lock-r17/source-diff.json'
    raw = invpath.read_bytes()
    need(SOURCE_DIFF_SHA and sha(raw) == SOURCE_DIFF_SHA, 'R17 source inventory identity differs')
    inventory = json.loads(raw)['current_assets']
    actual = {str(p.relative_to(project)): sha(p.read_bytes()) for p in (project/'assets').rglob('*') if p.is_file()}
    changed = sorted(k for k in set(inventory)|set(actual) if inventory.get(k) != actual.get(k))
    need(sorted(k for k in changed if k != 'assets/.DS_Store') == sorted([PREFAB, SCRIPT, HOME]), 'source changes exceed exact MainLayer prefab + EnglishUI repair: '+repr(changed))
    before = {}
    for key,name in ((PREFAB,'MainLayer.prefab.r17-original'),(SCRIPT,'EnglishUI.ts.r17-original'),(HOME,'HomeLayer.ts.r17-original')):
        p = originals/name; b = p.read_bytes(); need(sha(b)==inventory[key], 'before source not R17: '+key); before[key] = b
    oldhome=before[HOME].decode();newhome=(project/HOME).read_text()
    oldguard='if (!this.node.isValid || version !== this.pageVersion) return;'
    newguard='if (!this.node || !this.node.isValid || version !== this.pageVersion) return;'
    need(oldhome.count(oldguard)==1 and newhome.count(newguard)==1 and newhome.replace(newguard,oldguard,1)==oldhome,'HomeLayer differs beyond exact late-callback null guard')
    oldts = before[SCRIPT].decode(); newts = (project/SCRIPT).read_text()
    need(newts.count(INSERT)==1 and newts.count(ASYNC_INSERT)==1 and newts.replace(INSERT,'',1).replace(ASYNC_INSERT,'',1)==oldts, 'EnglishUI differs beyond exact asynchronous original fallback load and successful-load hide')
    need(ASYNC_INSERT+"    const path = 'english/' + key + '/spriteFrame';" in newts,'fallback original plate load must precede existing optional action image lookup')
    need('sprite.spriteFrame = frame;\n'+INSERT in newts, 'fallback hide must follow successful frame assignment')
    # Name must not acquire another consumer or producer anywhere in production.
    hits=[]
    for p in (project/'assets').rglob('*'):
        if p.is_file() and p.suffix in ('.ts','.js','.prefab','.scene','.json') and b'ArtLoadFallback' in p.read_bytes(): hits.append(str(p.relative_to(project)))
    need(sorted(hits)==sorted([PREFAB,SCRIPT]), 'fallback name is not unique to this repair')
    a=json.loads(before[PREFAB]); b=json.loads((project/PREFAB).read_bytes())
    need(len(b)==len(a)+6, 'exactly two Nodes, two UITransforms, Sprite and Label must be appended')
    ids=[i for i,o in enumerate(a) if o.get('__type__')=='cc.Node' and o.get('_name')=='btnGo']
    need(len(ids)==1,'ambiguous btnGo'); ni=ids[0]; node=a[ni]
    comps=[(x['__id__'],a[x['__id__']])for x in node['_components']]
    si=next(i for i,o in comps if o['__type__']=='cc.Sprite'); bi=next(i for i,o in comps if o['__type__']=='cc.Button');button=a[bi]
    plate=button['_normalSprite'];need(plate['__uuid__']==BLANK,'button original plate differs')
    expected=copy.deepcopy(a);expected[si]['_spriteFrame']=None;expected[si]['_enabled']=False;expected[bi]['_normalSprite']=None
    expected[ni]['_children'].append({'__id__':len(a)})
    n,t,sp,caption,ct,l=copy.deepcopy(b[-6:]);base=len(a)
    def node_expected(name,parent,children,components):
        return {'__type__':'cc.Node','_name':name,'_objFlags':0,'_parent':{'__id__':parent},'_children':[{'__id__':i}for i in children],'_active':True,'_components':[{'__id__':i}for i in components],'_prefab':None,'_lpos':{'__type__':'cc.Vec3','x':0,'y':0,'z':0},'_lrot':{'__type__':'cc.Quat','x':0,'y':0,'z':0,'w':1},'_lscale':{'__type__':'cc.Vec3','x':1,'y':1,'z':1},'_layer':node['_layer'],'_euler':{'__type__':'cc.Vec3','x':0,'y':0,'z':0},'_id':''}
    need(n==node_expected('ArtLoadFallback',ni,[base+3],[base+1,base+2]),'fallback Node has additional behavior or transform')
    need(caption==node_expected('Caption',base,[],[base+4,base+5]),'caption Node has additional behavior or transform')
    rootui=next(o for i,o in comps if o['__type__']=='cc.UITransform');size=rootui['_contentSize']
    image=(project/'assets/res/common/english/play.png').read_bytes()
    need(image[:8]==b'\x89PNG\r\n\x1a\n','PLAY source is not a PNG')
    iw,ih=struct.unpack('>II',image[16:24]);need((iw,ih)==(813,216),'approved PLAY source dimensions differ')
    width=size['width'];height=width*ih/iw
    def ui_expected(owner,w,h):
        return {'__type__':'cc.UITransform','_name':'','_objFlags':0,'node':{'__id__':owner},'_enabled':True,'__prefab':None,'_contentSize':{'__type__':'cc.Size','width':w,'height':h},'_anchorPoint':{'__type__':'cc.Vec2','x':0.5,'y':0.5},'_id':''}
    need(t==ui_expected(base,width,height),'fallback plate must equal original PLAY visible image ratio')
    need(ct==ui_expected(base+3,width-40,height-12),'caption must remain inside fallback plate')
    expected_sprite=copy.deepcopy(a[si]);expected_sprite.update(node={'__id__':base},_enabled=True,__prefab=None,_spriteFrame=None,_id='')
    need(sp==expected_sprite,'fallback Sprite differs from original same blank plate')
    # Exact reviewed text-only component: no assets, click listeners or custom material.
    expected_label={'__type__':'cc.Label','_name':'','_objFlags':0,'node':{'__id__':base+3},'_enabled':True,'__prefab':None,'_customMaterial':None,'_srcBlendFactor':2,'_dstBlendFactor':4,'_color':{'__type__':'cc.Color','r':255,'g':255,'b':255,'a':255},'_string':'PLAY','_horizontalAlign':1,'_verticalAlign':1,'_actualFontSize':42,'_fontSize':42,'_fontFamily':'Arial','_lineHeight':48,'_overflow':2,'_enableWrapText':False,'_font':None,'_isSystemFontUsed':True,'_spacingX':0,'_isItalic':True,'_isBold':True,'_isUnderline':False,'_underlineHeight':2,'_cacheMode':0,'_id':'','_enableOutline':True,'_outlineWidth':3,'_outlineColor':{'__type__':'cc.Color','r':0,'g':0,'b':0,'a':255}}
    need(l==expected_label,'fallback Label differs from reviewed readable system text')
    expected += [n,t,sp,caption,ct,l];need(expected==b,'prefab changed outside exact dependency + fallback subtree')
    return {'fallback_visible_size':{'width':width,'height':height,'derived_from_play_png':[iw,ih]},'inventory':ref(invpath),'changed':changed,'semantic_changed':sorted([PREFAB,SCRIPT,HOME]),'nonrendering_metadata':{k:{'before':inventory.get(k),'after':actual.get(k)}for k in changed if k=='assets/.DS_Store'},'before':{k:sha(v)for k,v in before.items()},'after':{k:actual[k]for k in changed}}

def canonical(root):
    """Identity-preserving sorted traversal, handles cyclic Cocos instance graphs."""
    seen={};objects=[]
    def visit(x):
        if not isinstance(x,(dict,list)):return x
        ident=id(x)
        if ident in seen:return {'$ref':seen[ident]}
        i=len(objects);seen[ident]=i;objects.append(None)
        objects[i]=({k:visit(x[k])for k in sorted(x)} if isinstance(x,dict) else [visit(v)for v in x])
        return {'$ref':i}
    r=visit(root);return {'root':r,'objects':objects}

def decode_pack(raw):
    """Symbolic interpreter of Creator 3.8.8 deserialize.ts DataTypeID 0..12.
    Retains every serialized field, object identity, dependency and unknown custom
    payload. No game engine, constructors, business code or browser is executed.
    """
    d=json.loads(raw);need(isinstance(d,list)and len(d)==6 and d[0]==1,'unsupported compiled pack')
    uuids,strings,classes,masks=d[1:5];result=[]
    for sec in d[5]:
        need(len(sec)==6,'unsupported section');ins,types,refs,depo,depk,depu=copy.deepcopy(sec)
        types=[]if types==0 else types; refs=[]if refs==0 else refs
        slots=[{}for _ in ins]; rev={}; depowners={}
        rootidx=0;count=len(ins)-len(types)
        if isinstance(ins[-1],int):rootidx=ins[-1]if ins[-1]>=0 else ~ins[-1];count-=1
        def setv(owner,key,val):owner[key]=val
        def assign(owner,key,value,typ):
            if typ==0:setv(owner,key,value)
            elif typ==1:
                if value>=0:setv(owner,key,slots[value])
                else:rev[~value]=(owner,key)
            elif typ in (2,3,9):
                arr=[None]*len(value);setv(owner,key,arr)
                for j,v in enumerate(value):assign(arr,j,v,{2:1,3:6,9:4}[typ])
            elif typ==4:setv(owner,key,clazz(value))
            elif typ in (5,7,8):setv(owner,key,{'$valueType':typ,'data':value})
            elif typ==6:depowners[value]=(owner,key)
            elif typ==10:setv(owner,key,{'$customType':classes[value[0]],'data':value[1]})
            elif typ==11:
                obj=value[0];setv(owner,key,obj)
                for j in range(1,len(value),3):assign(obj,value[j],value[j+2],value[j+1])
            elif typ==12:
                arr=value[0];setv(owner,key,arr)
                for j in range(len(arr)):assign(arr,j,arr[j],value[j+1])
            else:raise ValueError('unsupported compiled assignment '+str(typ))
        def clazz(value):
            mask=masks[value[0]];c=classes[mask[0]];obj={'__type__':c[0]};keys=c[1]
            for j,v in enumerate(value[1:],1):assign(obj,keys[mask[j]],v,0 if j<mask[-1] else c[mask[j]+c[2]])
            return obj
        for i in range(count):slots[i].update(clazz(ins[i]))
        for j,typ in enumerate(types):
            i=count+j
            if typ>=0:slots[i].update({'$customType':classes[typ],'data':ins[i]})
            else:
                box={};assign(box,'v',ins[i],~typ);need(isinstance(box['v'],dict),'unsupported nonobject instance');slots[i].update(box['v'])
        if refs:
            split=refs[-1]*3
            for j in range(0,len(refs)-1,3):
                ownerkey=rev[j//3]if j<split else (slots[refs[j]],strings[refs[j+1]]if refs[j+1]>=0 else ~refs[j+1])
                ownerkey[0][ownerkey[1]]=slots[refs[j+2]]
        for j,oi in enumerate(depo):
            owner,key=depowners[j]if j in depowners else (slots[oi], strings[depk[j]]if isinstance(depk[j],int)and depk[j]>=0 else (~depk[j]if isinstance(depk[j],int)else depk[j]))
            uid=uuids[depu[j]]if isinstance(depu[j],int)else depu[j];owner[key]={'$asset':uid}
        reachable=set()
        def walk(x):
            if not isinstance(x,(dict,list))or id(x)in reachable:return
            reachable.add(id(x))
            for v in (x.values()if isinstance(x,dict)else x):walk(v)
        walk(slots[rootidx])
        need(all(id(slots[i])in reachable for i in range(count+len(types))), 'compiled pack has unreachable instances')
        result.append(slots[rootidx])
    return result

def find_nodes(root,name):
    seen=set();found=[]
    def go(x):
        if not isinstance(x,(dict,list))or id(x)in seen:return
        seen.add(id(x))
        if isinstance(x,dict)and x.get('__type__')=='cc.Node'and x.get('_name')==name:found.append(x)
        for v in (x.values()if isinstance(x,dict)else x):go(v)
    go(root);return found

def config_semantics(raw,ignored_uuid=None):
    d=json.loads(raw);u=d.pop('uuids');need(len(set(u))==len(u),'duplicate bundle UUID')
    def uid(i):return u[i]if isinstance(i,int)else i
    d['uuid_set']=sorted(x for x in u if x not in (ignored_uuid or set()))
    d['paths']={uid(int(i)):v for i,v in d['paths'].items()}
    d['packs']={k:[uid(i)for i in v]for k,v in d['packs'].items()}
    d['scenes']={k:uid(v)for k,v in d['scenes'].items()}
    r=d['redirect'];d['redirect']=sorted([[uid(r[i]),r[i+1]]for i in range(0,len(r),2)if uid(r[i])not in (ignored_uuid or set())])
    d['extensionMap']={k:sorted(uid(i)for i in v)for k,v in d['extensionMap'].items()}
    for typ,arr in d['versions'].items():need(not arr,'versioned bundle unsupported by this narrow guard')
    need(not d.get('dependencyRelationships'),'dependencyRelationships unsupported')
    return d

def javascript_delta(old,new):
    marker='System.register("chunks:///_virtual/EnglishUI.ts"'
    def split(b):
        s=b.decode();need(s.count(marker)==1,'EnglishUI module ambiguous');a=s.index(marker);n=s.find('\n\nSystem.register',a);need(n>=0,'EnglishUI module boundary absent');return s[:a],s[a:n],s[n:]
    ap,ac,az=split(old);bp,bc,bz=split(new)
    home_marker='System.register("chunks:///_virtual/HomeLayer.ts"'
    def home_split(s):
        need(s.count(home_marker)==1,'HomeLayer module ambiguous');a=s.index(home_marker);n=s.find('\n\nSystem.register',a);need(n>=0,'HomeLayer module boundary absent');return s[:a],s[a:n],s[n:]
    # HomeLayer sorts after EnglishUI in this bundle, so compare the untouched
    # prefix/suffix after replacing the two specifically reviewed modules.
    ahp,ah,ahz=home_split(az);bhp,bh,bhz=home_split(bz)
    need(ap==bp and ahp==bhp and ahz==bhz,'another compiled JS module changed')
    hpattern=r'([A-Za-z_$][\w$]*)\.node&&\1\.node\.isValid&&([A-Za-z_$][\w$]*)===\1\.pageVersion'
    matches=list(re.finditer(hpattern,bh));need(len(matches)==1,'compiled HomeLayer must add only the exact late-callback node existence test')
    h=matches[0];old_condition=h.group(1)+'.node.isValid&&'+h.group(2)+'==='+h.group(1)+'.pageVersion'
    reverted_home=bh[:h.start()]+old_condition+bh[h.end():]
    helper=Path(__file__).with_name('play-art-js-equivalence.cjs')
    home_result=subprocess.run(['node',str(helper),TERSER,'home'],input=json.dumps([ah,reverted_home]),capture_output=True,text=True)
    need(home_result.returncode==0 and json.loads(home_result.stdout).get('equal')is True,'HomeLayer compiled remainder changed beyond exact null guard')
    # Remove only the exact minifier form of the reviewed two source statements.
    pattern=r'var ([A-Za-z_$][\w$]*)=([A-Za-z_$][\w$]*)\.getChildByName\("ArtLoadFallback"\);if\(\1&&\(\1\.active=!1\),'
    hits=list(re.finditer(pattern,bc));need(len(hits)==1,'compiled fallback hide differs from exact var + guarded active=false')
    hit=hits[0];need(hit.group(2)=='e','fallback receiver is not applyArt node')
    stripped=bc[:hit.start()]+'if('+bc[hit.end():]
    # Precise emitted form of the only new optional yellow-plate load branch.
    load_pattern=(r'var ([A-Za-z_$][\w$]*)=e\.getChildByName\("ArtLoadFallback"\);'
                  r'\1&&([A-Za-z_$][\w$]*)\.load\("btnres/ui_yellow/spriteFrame",([A-Za-z_$][\w$]*),'
                  r'\(function\(([A-Za-z_$][\w$]*),([A-Za-z_$][\w$]*)\)\{!\4&&\1\.isValid&&'
                  r'\(\1\.getComponent\(([A-Za-z_$][\w$]*)\)\.spriteFrame=\5\)\}\)\);')
    loads=list(re.finditer(load_pattern,stripped));need(len(loads)==1,'compiled asynchronous original plate branch differs from exact guarded load')
    load=loads[0]
    need(load.group(2)=='s'and load.group(3)=='i'and load.group(6)=='a','compiled plate load does not use original bundle/SpriteFrame/Sprite aliases')
    stripped=stripped[:load.start()]+stripped[load.end():]
    helper=Path(__file__).with_name('play-art-js-equivalence.cjs')
    result=subprocess.run(['node',str(helper),TERSER],input=json.dumps([ac,stripped]),capture_output=True,text=True)
    need(result.returncode==0,'compiled EnglishUI remainder is not equivalent: '+result.stderr[-1200:])
    detail=json.loads(result.stdout);need(detail.get('equal')is True,'compiled EnglishUI changed beyond exact asynchronous fallback/hide statements')
    detail['home_layer']=json.loads(home_result.stdout)
    return detail

def native_delta(old,new):
    need(set(old)==set(new),'Native membership changed')
    changed=sorted(k for k in old if old[k]!=new[k])
    expected=['assets/main/index.js','subpackages/layer/config.json','subpackages/layer/import/0d/0daa66ce2.json']
    need(changed==expected,'Native changed outside exact compiled module / MainLayer pack / layer config: '+repr(changed))
    js=javascript_delta(old[expected[0]],new[expected[0]])
    a=decode_pack(old[expected[2]]);b=decode_pack(new[expected[2]])
    need(len(a)==len(b)==2,'MainLayer pack membership changed')
    nodes=find_nodes(b,'ArtLoadFallback');need(len(nodes)==1,'compiled fallback not unique');fallback=nodes[0]
    btns=find_nodes(b,'btnGo');need(len(btns)==1,'compiled btnGo ambiguous');btn=btns[0]
    need(fallback.get('_parent')is btn,'compiled fallback parent differs')
    need({k:v for k,v in fallback.items()if k not in ('_parent','_components','_children')}=={'__type__':'cc.Node','_name':'ArtLoadFallback','_layer':btn['_layer']},'compiled fallback Node fields differ')
    captions=fallback.get('_children',[]);need(len(captions)==1,'compiled fallback must have exactly one caption child');caption=captions[0]
    need(caption.get('_parent')is fallback,'compiled caption parent differs')
    need({k:v for k,v in caption.items()if k not in ('_parent','_components')}=={'__type__':'cc.Node','_name':'Caption','_layer':btn['_layer']},'compiled caption Node fields differ')
    components=fallback.get('_components',[]);need(len(components)==2 and [v['__type__']for v in components]==['cc.UITransform','cc.Sprite'],'compiled fallback component types/order differ')
    ccomps=caption.get('_components',[]);need(len(ccomps)==2 and [v['__type__']for v in ccomps]==['cc.UITransform','cc.Label'],'compiled caption component types/order differ')
    ui,sp=components;ct,label=ccomps
    need(ui.get('node')is fallback and sp.get('node')is fallback and ct.get('node')is caption and label.get('node')is caption,'compiled fallback component owner differs')
    height=277*216/813
    need({k:v for k,v in ui.items()if k!='node'}=={'__type__':'cc.UITransform','_contentSize':{'$valueType':5,'data':[5,277,height]}},'compiled fallback plate dimensions differ from PLAY image')
    need({k:v for k,v in ct.items()if k!='node'}=={'__type__':'cc.UITransform','_contentSize':{'$valueType':5,'data':[5,237,height-12]}},'compiled caption dimensions differ')
    need({k:v for k,v in label.items()if k!='node'}=={'__type__':'cc.Label','_string':'PLAY','_actualFontSize':42,'_fontSize':42,'_lineHeight':48,'_overflow':2,'_enableWrapText':False,'_isItalic':True,'_isBold':True,'_enableOutline':True,'_outlineWidth':3},'compiled fallback Label differs')
    need({k:v for k,v in sp.items()if k not in ('node','_spriteFrame')}=={'__type__':'cc.Sprite','_sizeMode':0},'compiled fallback Sprite behavior differs')
    child=btn.get('_children',[]);need(sum(x is fallback for x in child)==1,'compiled fallback child linkage differs');child.remove(fallback)
    oldbtn=find_nodes(a,'btnGo')[0]
    sprite=next(c for c in btn['_components']if c['__type__']=='cc.Sprite');oldsprite=next(c for c in oldbtn['_components']if c['__type__']=='cc.Sprite')
    button=next(c for c in btn['_components']if c['__type__']=='cc.Button')
    need(sprite.get('_spriteFrame')is None and button.get('_normalSprite')is None and sp.get('_spriteFrame')is None,'static fallback/PLAY image dependency was not removed from all three fields')
    need(sprite.get('_enabled')is False,'compiled legacy root Sprite must be disabled')
    del sprite['_enabled']
    oldbutton=next(c for c in oldbtn['_components']if c['__type__']=='cc.Button')
    removed=oldsprite['_spriteFrame']['$asset'];oldplate=oldbutton['_normalSprite']['$asset']
    sprite['_spriteFrame']=copy.deepcopy(oldsprite['_spriteFrame']);button['_normalSprite']=copy.deepcopy(oldbutton['_normalSprite'])
    need(canonical(a)==canonical(b),'other compiled prefab fields or packed prefab changed')
    ou=set(json.loads(old[expected[1]])['uuids']);nu=set(json.loads(new[expected[1]])['uuids']);removed_uuids=ou-nu
    need(not nu-ou and removed in removed_uuids and removed_uuids<={removed,oldplate},'bundle UUID changes exceed removed static PLAY/plate references')
    need(config_semantics(old[expected[1]],removed_uuids)==config_semantics(new[expected[1]],removed_uuids),'bundle configuration changed beyond exactly removed optional image references and index relocation')
    return {'old_native_tree_sha256':tree_sha(old),'native_tree_sha256':tree_sha(new),'changed':changed,'files':{k:{'before':sha(old[k]),'after':sha(new[k])}for k in changed},'javascript':js,'compiled_prefab':'identity-preserving graph equality after exact repair reversal','config':'UUID-resolved equality minus removed PLAY dependency'}

def validate(old_zip,new_files,adapter,scope=None):
    scope=scope or os.environ.get('PLAY_ART_DELTA_SCOPE');need(scope,'PLAY_ART_DELTA_SCOPE absent')
    scopepath=Path(scope);s=json.loads(scopepath.read_text());need(s.get('schema')==SCHEMA,'scope schema differs')
    project=Path(s['project']).resolve();originals=Path(s['original_dir']).resolve();old_zip=Path(old_zip).resolve()
    need(s.get('old_zip')==ref(old_zip) and old_zip==project/'qa/rework-baseline/R17/ShellStrike_R17_TikTok.zip','old ZIP must be the exact stable predecessor copy pinned in scope')
    need(sha(old_zip.read_bytes())==OLD_ZIP_SHA,'not the actual passed R17 ZIP')
    receipt=Path(str(old_zip)+'.receipt.json');need(s.get('old_receipt')==ref(receipt),'stable predecessor receipt differs from scope');need(sha(receipt.read_bytes())==OLD_RECEIPT_SHA,'old receipt bytes differ from reviewed R17 receipt');r=json.loads(receipt.read_text());need(r.get('zip_sha256')==OLD_ZIP_SHA and r.get('tool')=='build_checked_zip','old official receipt mismatch')
    for name in ('rewarded_ad_regression','runtime_regression'):need(r['regressions'][name].get('passed')is True,'old regression did not pass '+name)
    baseline=originals/'ad-regression.json.r17-original';oldadapter=baseline.read_bytes()
    for name in ('rewarded_ad_regression','runtime_regression'):need(r['regressions'][name].get('adapter_sha256')==sha(oldadapter),'original adapter identity differs from R17 '+name)
    ad=json.loads(Path(adapter).read_bytes());before=json.loads(oldadapter);expected=copy.deepcopy(before);need(expected['image_stall'].get('play')in (None,False),'original already had play enabled');expected['image_stall']['play']=True
    note=ad.get('image_stall',{}).get('note')
    need(isinstance(note,str)and bool(note.strip()),'image_stall.note must remain a nonempty description')
    expected['image_stall']['note']=note
    need(ad==expected,'adapter differs beyond image_stall.play=true and its non-executable explanatory note')
    need(not any('.DS_Store' in Path(k).parts for k in new_files), 'Finder metadata must not enter Native')
    source=source_delta(project,originals)
    with zipfile.ZipFile(old_zip)as z:
        need(z.testzip()is None,'old ZIP CRC failure');old={n:z.read(n)for n in z.namelist()if not n.endswith('/')}
    native=native_delta(old,new_files)
    return {'schema':SCHEMA,'scope':ref(scopepath),'old_zip':ref(old_zip),'old_receipt':ref(receipt),'guard':ref(__file__),'javascript_guard':ref(Path(__file__).with_name('play-art-js-equivalence.cjs')),'old_adapter':ref(baseline),'adapter':ref(adapter),'adapter_delta':{'execution':'image_stall.play=true','description_only':{'field':'image_stall.note','before':before['image_stall'].get('note'),'after':note}},'source':source,'native':native,'rerun':['layout_state','button_sweep','image_stall','startup','startup3x','network'],'reuse_semantics':'Only unaffected old suite executions retain original receipt identity; no old observations are current captures.'}

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--old',required=True);ap.add_argument('--native',required=True);ap.add_argument('--adapter',required=True);ap.add_argument('--scope',required=True);ap.add_argument('--out');args=ap.parse_args()
    try:
        root=Path(args.native);files={str(p.relative_to(root)):p.read_bytes()for p in root.rglob('*')if p.is_file()};proof=validate(args.old,files,args.adapter,args.scope);text=json.dumps(proof,ensure_ascii=False,indent=2)+'\n'
        if args.out:Path(args.out).write_text(text)
        print(text)
    except Exception as error:
        print(str(error));raise SystemExit(1)
