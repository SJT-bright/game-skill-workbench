"""Schema-aware proof for original scalars retained beside owned JSON snapshots.

This supplements STORAGE-01's text-in-place codec. It preserves all base cases,
adds every protected numeric key's SDK/async/cold matrix, and requires separately
registered real Native HOME/input/recovery evidence. No game paths or key names.
"""
import hashlib,json,re,subprocess,shutil
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def same(a,b):return json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False)
def validate(trace,native,binding):
    from maintenance_scope import checked_ref,source_inventory
    from check_known_issues import tree_sha
    from audit_native_storage_contract import BASE_CASES,execution_identity
    from startup_business_contract import validate_business
    import project_qa
    errors=[]
    def need(ok,message):
        if not ok:errors.append('numeric snapshot: '+message)
    try:
        native=Path(native).resolve();project=Path(trace['project']).resolve();base=Path(trace['trace_base'])
        need(trace.get('schema')=='native_storage_trace.v3' and trace.get('binding')==binding,'v3/current binding required')
        need(tree_sha(native)==binding['native_tree_sha256'],'Native identity changed')
        execution_identity(trace)
        command=trace['execution'].get('command',[])
        need(isinstance(command,list) and trace['execution']['runner'] in command and '{bundle}' in command and '{adapter}' in command,'actual runner command/arguments required')
        codec_ref=trace['numeric_snapshot_encoding'];codec=read(checked_ref(codec_ref,base))
        policy=project_qa.lookup(project,'ui_runners',trace['snapshot_runtime']['registered_runner'])
        need(policy['contract_sha256']==codec_ref['sha256'],'encoding differs from reviewed runtime registration')
        need(codec.get('schema')=='numeric_snapshot_encoding.v1','unsupported schema encoding')
        source=native/codec['native_source'];need(source.is_relative_to(native) and source.is_file(),'actual Native numeric facade required')
        text=source.read_text();keys=json.loads(re.search(r'var KEYS=(\[[^\]]+\])',text)[1].replace("'",'"'))
        optional=json.loads(re.search(r'OPTIONAL=(\[[^\]]+\])',text)[1].replace("'",'"'))
        prefix=re.search(r"PREFIX='([^']+)'",text)[1];schema=re.search(r"r\.schema==='([^']+)'",text)[1]
        critical=[k for k in keys if k not in optional]
        need(codec['keys']==keys and codec['critical']==critical and codec['prefix']==prefix and codec['record_schema']==schema,'descriptor does not match actual codec declarations')
        need(codec.get('key_field')=='key' and codec.get('value_field')=='value','unsupported numeric record fields')
        need(len(set(keys))==len(keys) and bool(keys) and bool(critical),'finite numeric scope required')
        entry=(native/'game.js').read_text();need(entry.find('./'+codec['native_source'])>=0 and entry.find('./'+codec['native_source'])<entry.rfind('./main.js'),'facade must be installed before business bootstrap')
        # Derive the protected business domain from syntax, including computed
        # member access. Escaped methods or unknown/dynamic keys remain refused.
        scanner="""const a=require(process.argv[1]),fs=require('fs');const s=fs.readFileSync(0,'utf8'),t=a.parse(s,{ecmaVersion:'latest'}),out=[];function walk(n,p){if(!n||typeof n!=='object')return;if(n.type==='MemberExpression'){let name=n.computed?n.property.value:n.property.name;if(['getlocalStorageNum','setlocalStorageNum'].includes(name)){if(p?.type!=='CallExpression'||p.callee!==n)throw Error('escaped numeric accessor');const k=p.arguments[0];if(k?.type!=='Literal'||typeof k.value!=='string')throw Error('unresolved numeric key');out.push(k.value);}}for(const [k,v]of Object.entries(n))if(k!=='parent'){if(Array.isArray(v))v.forEach(x=>walk(x,n));else if(v&&typeof v==='object')walk(v,n);}}walk(t);process.stdout.write(JSON.stringify(out));"""
        parser=Path(__file__).parent/'vendor/acorn.cjs'
        main=native/'assets/main/index.js';run=subprocess.run([shutil.which('node'),'-e',scanner,str(parser)],input=main.read_text(),text=True,capture_output=True,timeout=30)
        need(run.returncode==0,'numeric caller domain unresolved: '+run.stderr[-300:])
        if run.returncode==0:need(set(json.loads(run.stdout))<=set(keys),'uncovered numeric business key')
        routes=source_inventory(trace['route_inventory'],base,project,binding)['routes']
        loaded={}
        for label in ('current','negative_control','upgrade_negative_control'):
            row=trace[label];bundle=Path(row['bundle']);adapter=Path(row['adapter']);raw=Path(row['raw_report'])
            need(all(p.is_file() for p in (bundle,adapter,raw)),label+' files missing')
            need(all(sha(row[name])==row[name+'_sha256'] for name in ('bundle','adapter')) and sha(raw)==row['raw_sha256'],label+' input/raw bytes changed')
            result=read(raw);loaded[label]=result
            need(result['runner_sha256']==trace['execution']['runner_sha256'] and result['bundle_sha256']==row['bundle_sha256'] and result['adapter_sha256']==row['adapter_sha256'],label+' execution identity mismatch')
            if label=='current':
                need(bundle.resolve()==source.resolve() and adapter.resolve().is_relative_to(native),'current test must execute final Native facade/adapter')
                for name in BASE_CASES:
                    route={'reopen_map':'map','reopen_stage_details':'stage_details'}.get(name)
                    expected='not_applicable' if route and not routes[route]['present'] else 'pass'
                    need(result['cases'].get(name)==expected,'required case failed/missing '+name)
                matrix=result.get('matrix',[])
                need(len(matrix)==len(keys)*4,'per-key boundary/nonbinary/metadata/unreadable matrix incomplete')
                for key in keys:
                    for kind in ('typed_boundary','typed_nonbinary','metadata_unavailable','unrecoverable'):
                        rows=[x for x in matrix if x.get('key')==key and x.get('kind')==kind];need(len(rows)==1,key+' '+kind+' raw observation missing')
                        if len(rows)!=1:continue
                        obs=rows[0];before=obs['before'];after=obs['after'];value=obs['value']
                        need(type(value) is int and abs(value)<=9007199254740991 and (value in (0,1) if kind in ('typed_boundary','metadata_unavailable') else value not in (0,1)),key+' typed fixture invalid')
                        need(any(x.get('key')==key and x.get('type')=='boolean' and type(x.get('value')) is bool for x in obs.get('sync_reads',[])),key+' synchronous Boolean bridge was not hit')
                        need(type(before.get(key)) is int and before.get(key)==value and all(k in after and same(after[k],v) for k,v in before.items()) and obs['removed']==[],key+' original data changed')
                        if kind=='unrecoverable':
                            need(same(before,after) and obs['writes']==[] and obs['locked'] is True and (key not in critical or bool(obs['error'])),key+' unsafe unreadable fallback')
                        else:
                            encoded=after.get(prefix+key);decoded=json.loads(encoded) if isinstance(encoded,str) else encoded
                            need(isinstance(decoded,dict) and type(decoded.get('value')) is int and decoded=={'schema':schema,'key':key,'value':value} and obs['read']==str(value) and obs['cold_read']==str(value) and not obs['error'],key+' recovery/schema/cold value mismatch')
                            need(any(x.get('key')==key and type(x.get('value')) is int and x['value']==value for x in obs['reads']),key+' typed asynchronous original not observed')
                            need(all(k in obs['cold_after'] and same(obs['cold_after'][k],v) for k,v in before.items()),key+' cold restart altered originals')
            else:
                need(row.get('kind')=='controlled_legacy_fixture',label+' precise defect provenance required')
                checked_ref(row['provenance'],base);original=checked_ref(row['base_bundle'],base);patch=row['patch']
                need(original.resolve()==source.resolve() and original.read_text().count(patch['before'])==1 and '\n' not in patch['before'] and '\n' not in patch['after'] and original.read_text().replace(patch['before'],patch['after'],1)==bundle.read_text(),label+' mutation is not the exact documented single-line defect')
                need(row['bundle_sha256']!=trace['current']['bundle_sha256'],label+' negative equals current')
        current=loaded['current'];negative=loaded['negative_control'];upgrade=loaded['upgrade_negative_control']
        for name in ('legacy_numeric_nonbinary_typed','legacy_numeric_boundary_typed','legacy_unreadable_preserved'):
            need(current['cases'].get(name)=='pass','declared cold-upgrade case failed '+name)
        need(current['cases'].get('legacy_upgrade_touch_play')=='external_runtime','real upgrade PLAY must be explicitly delegated to the bound Native runtime')
        need(current['observations']['completed_reward_once']['after']['watchAD']==1,'duplicate ad completion changed reward count')
        need(current['observations']['retry_after_transient_failure']['failed']['balance']==0 and current['observations']['retry_after_transient_failure']['after']['balance']==200 and current['observations']['retry_after_transient_failure']['after']['creates']==1,'retry discarded transaction or requested another ad')
        need(negative['cases'].get('missing_empty_string')=='fail','missing-empty negative did not fail')
        for name in BASE_CASES:
            if name!='missing_empty_string':need(negative['cases'].get(name)==current['cases'].get(name),'empty fixture changed unrelated case '+name)
        key=critical[0];a=next(x for x in current['matrix'] if x['key']==key and x['kind']=='typed_nonbinary');b=next(x for x in upgrade['matrix'] if x['key']==key and x['kind']=='typed_nonbinary')
        need(a['before']==b['before'] and a['read']!=b['read'] and b['read']!=str(b['value']),'same legacy fixture did not reproduce numeric bridge defect')
        runtime_path=checked_ref(trace['snapshot_runtime']['raw'],base);runtime=read(runtime_path)
        need(runtime.get('binding')==binding,'real Native storage runtime binding mismatch')
        rows={x['id']:x for x in runtime['rows']};normal=rows['typed-upgrade']
        need(normal.get('binding')==binding and type(normal['fixture'].get(key)) is int and normal['fixture'][key] not in (0,1),'real Native preboot typed legacy fixture missing')
        need(any(x.get('key')==key and type(x.get('value')) is int and x['value']==normal['fixture'][key] for x in normal['reads']),'real SDK async typed recovery missing')
        errors.extend(validate_business(normal));need(any(t.get('trusted') for t in normal['touches']),'real trusted upgrade PLAY missing')
        need(normal['cold']['coin']==normal['fixture'][key] and all(k in normal['cold']['raw'] and same(normal['cold']['raw'][k],v) for k,v in normal['fixture'].items()),'real cold restart changed original legacy data')
        for k in optional:
            row=rows['isolated-'+k];need(row.get('binding')==binding and row['raw'].get(k) is False and row['afterPlay'].get(k) is False,'unreadable optional value changed '+k);errors.extend(validate_business(row))
        for name in ('critical-'+key,'metadata-unavailable'):
            row=rows[name];retry=row['retry'];need(row.get('binding')==binding and row['retry_visible'] is True and not row['loading_overlay_visible'] and retry['after']>retry['before'] and any(t.get('trusted') for t in retry['touches']),'actual protected Retry/new attempt missing '+name)
            if name.startswith('critical-'):need(row['raw'].get(key) is False and retry['raw'].get(key) is False and row['writes']==[],'critical original was reset or granted')
        need(all(not any(re.search(r'UNCAUGHT|UNHANDLED|HOST_UNCAUGHT',e) for e in row['errors']) for row in rows.values()),'actual storage runtime has unhandled errors')
        # Reuse the common, independently registered actual-renderer contract.
        renderer_path=checked_ref(trace['renderer_report'],base)
        from audit_native_startup_renderer import validate as renderer_validate
        errors.extend(renderer_validate(read(renderer_path),native,binding,project))
    except (ValueError,KeyError,TypeError,OSError,AttributeError,IndexError,StopIteration) as e:
        errors.append('numeric snapshot contract invalid: '+str(e))
    return errors
