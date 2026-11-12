"""Raw legacy storage coverage, derived from final Native JS, reused by STORAGE-01.
No game key names or guessed Boolean/numeric conversions. Not a whole-program proof.

2026-11-12, saved data never stops the game. Two forms of proof for the direct storage reads found in the Native JS:
  legacy_consumers.mode == 'unreadable_start'   two runs for the whole game (every found key reads back true / false,
      async storage fails): no exception, home -> trusted touch -> play. For a first release, or when every released
      build wrote text through the kit storage guard.
  legacy_consumers.fields (per key, as before)  for a game whose released builds wrote raw numbers / Booleans and
      that recovers them: typed upgrade per fixture and key; the unrecoverable row of each key is a start with the
      fallback value. The earlier unrecoverable proof (value untouched behind a visible recovery page, plus the three
      modal failure rows) is still read for receipts issued before this text, not for a new approval.
"""
import argparse, json, shutil, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent


def inventory(native):
    files=[]
    for p in sorted(Path(native).rglob('*.js')):
        name=p.relative_to(native).as_posix()
        if name.startswith(('cocos/','cocos-js/')):
            continue  # platform implementations; actual game callers are still scanned inside bundled scripts
        code=p.read_text(encoding='utf-8-sig')
        # Computed constants such as ['get'+'Item'] must reach the AST scanner too.
        files.append({'file':name,'code':code})
    if not files:return []
    node=shutil.which('node')
    if not node:raise ValueError('legacy storage consumer inventory needs Node.js')
    run=subprocess.run([node,str(HERE/'scan_storage_consumers.cjs')],input=json.dumps({'files':files}),text=True,capture_output=True,timeout=45)
    if run.returncode:raise ValueError('legacy storage consumer AST inventory failed: '+run.stderr[-500:])
    doc=json.loads(run.stdout)
    if doc.get('schema')!='storage_consumers_scan.v1' or not isinstance(doc.get('sites'),list):raise ValueError('invalid storage consumer scan')
    return [site for site in doc['sites'] if not site.get('platform_storage_delegate')]


def valid_type(v,kind):
    import math
    if kind=='boolean':return type(v) is bool
    if kind=='integer':return type(v) is int and abs(v)<=9007199254740991
    if kind=='number':return type(v) in (int,float) and math.isfinite(v)
    if kind=='string':return isinstance(v,str)
    return isinstance(v,dict) if kind=='json_object' else False


def decoded(value,kind):
    if valid_type(value,kind):return value
    if not isinstance(value,str):return object()
    try:
        v=json.loads(value)
        return v if valid_type(v,kind) else object()
    except ValueError:return object()


PROFILES={'all_true':True,'all_false':False}
ASYNC_FAILED=('unavailable','error','timeout','unreadable')


def unreadable_start_errors(result,sites):
    """Whole-game proof: every found key unreadable at once, the game still starts and plays (two runs)."""
    from startup_business_contract import validate_business
    errors=[];ids={s['site_id']:s for s in sites};literal={s['key'] for s in sites if s['key'] is not None}
    observations=result.get('legacy_consumer_observations',[]) if isinstance(result,dict) else []
    if not isinstance(observations,list):observations=[]
    rows=[r for r in observations if isinstance(r,dict) and r.get('case')=='unreadable_start']
    for profile,expected in PROFILES.items():
        match=[r for r in rows if r.get('profile')==profile]
        if len(match)!=1:errors.append('unreadable start: exactly one '+profile+' run required');continue
        r=match[0];label='unreadable start '+profile
        before=r.get('storage_before');seeded=r.get('seeded_keys');reads=r.get('sync_reads');hit=r.get('read_sites')
        if r.get('fixture_installed_before_entry') is not True or not isinstance(before,dict) or not isinstance(seeded,list) or not literal<=set(seeded) or not set(seeded)<=set(before):
            errors.append(label+': every storage key read by the Native JS must be seeded before entry ('+', '.join(sorted(literal-set(seeded if isinstance(seeded,list) else [])))+')');continue
        if not isinstance(hit,list) or not set(hit)<=set(ids) or not isinstance(reads,dict):
            errors.append(label+': actual consumer sites and their sync reads required');continue
        for sid in hit:
            key=ids[sid]['key']
            if key is None:continue      # computed key: its read is covered by the run, not named here
            seen=reads.get(key)
            if not isinstance(seen,dict) or seen.get('type')!='boolean' or seen.get('value') is not expected:
                errors.append(label+': '+key+' was not read back as Boolean '+str(expected).lower())
        if r.get('async_storage') not in ASYNC_FAILED:errors.append(label+': async storage must fail, so no value can be recovered')
        if r.get('errors')!=[] or r.get('removed_keys')!=[] or r.get('loading_overlay_visible') is not False:
            errors.append(label+': exception, removed key or loading overlay after an unreadable read')
        errors.extend(label+': '+e for e in validate_business(r))
    if not any(r.get('metadata_status')=='unavailable' for r in rows if r.get('profile') in PROFILES):
        errors.append('unreadable start: one of the two runs must have the SDK key list unavailable')
    return errors


def fallback_row_errors(key,r):
    """Per-key unrecoverable row of the 2026-11-12 policy: the game starts and plays with the fallback value."""
    from audit_native_storage_contract import fallback_start_errors
    return fallback_start_errors(dict(r,key=key),key+': unrecoverable',key)


def coverage_errors(trace,result,native,new_approval=False):
    sites=inventory(native)
    if not sites:return []
    errors=[];contract=trace.get('legacy_consumers',{})
    if isinstance(contract,dict) and contract.get('mode')=='unreadable_start':
        from audit_native_storage_contract import raw_history
        if raw_history(trace):return ['legacy_consumers.mode unreadable_start needs legacy_data.earlier_release_wrote_raw_values false with its basis; a game whose released builds wrote raw values proves typed recovery per key']
        return unreadable_start_errors(result,sites)
    rows=contract.get('fields') if isinstance(contract,dict) else None
    if not isinstance(rows,list):return ['legacy startup consumers need proof (legacy_consumers.mode unreadable_start, or per-key fields): '+', '.join(sorted({s['key'] or '<dynamic>' for s in sites}))]
    bysite={s['site_id']:s for s in sites};covered=set();keys=set();specs={}
    for row in rows:
        if not isinstance(row,dict):errors.append('invalid legacy field');continue
        key=row.get('key');ids=row.get('sites',[]);kind=row.get('type')
        if not isinstance(key,str) or not key or key in keys or kind not in ('boolean','integer','number','string','json_object') or type(row.get('critical')) is not bool:
            errors.append('legacy field needs unique key, actual type and criticality');continue
        keys.add(key);specs[key]=row
        if not isinstance(ids,list) or not ids:errors.append(key+': actual consumer site IDs required');continue
        for sid in ids:
            site=bysite.get(sid)
            if not site or site['key'] not in (None,key):errors.append(key+': consumer site mismatch');continue
            covered.add(sid)
    if set(bysite)!=covered:errors.append('uncovered actual legacy read sites: '+', '.join(s['key'] or '<dynamic>' for sid,s in bysite.items() if sid not in covered))
    # Dynamic domains need source-bound finite expansion; never mark an opaque domain complete.
    if any(s['key'] is None for s in sites):errors.append('dynamic legacy key domain requires finite source expansion; direct inventory cannot approve it')
    observations=result.get('legacy_consumer_observations',[]) if isinstance(result,dict) else []
    if not isinstance(observations,list):observations=[]
    from startup_business_contract import validate_business
    blocking=False
    for key,spec in specs.items():
        # Values/ranges belong to the game schema, not this example defaults.
        fixtures=spec.get('valid_fixtures')
        if not isinstance(fixtures,list) or not fixtures:errors.append(key+': project-valid typed fixtures required');continue
        if any(not valid_type(v,spec['type']) for v in fixtures):errors.append(key+': fixtures violate declared storage type')
        if spec['type'] in ('integer','number') and (not any(type(v) in (int,float) and v in (0,1) for v in fixtures) or not any(type(v) in (int,float) and v not in (0,1) for v in fixtures)):errors.append(key+': actual numeric boundary and nonbinary fixtures required')
        if spec['type']=='boolean' and set(type(v) for v in fixtures)!={bool}:errors.append(key+': Boolean fixtures must remain Boolean')
        if spec['type']=='boolean' and (True not in fixtures or False not in fixtures):errors.append(key+': both Boolean states required')
        for case,value in [('typed_upgrade',v) for v in fixtures]+[('metadata_unavailable',fixtures[0])]:
            matches=[r for r in observations if isinstance(r,dict) and r.get('key')==key and r.get('case')==case and type(r.get('fixture')) is type(value) and r.get('fixture')==value]
            if len(matches)!=1:errors.append(key+': exactly one raw typed upgrade observation per fixture required');continue
            r=matches[0]
            sync=r.get('sync_read',{})
            if not isinstance(sync,dict) or sync.get('type')!='boolean' or type(sync.get('value')) is not bool:
                errors.append(key+': actual synchronous Boolean/ambiguity observation required')
            if case=='metadata_unavailable' and r.get('metadata_status')!='unavailable':errors.append(key+': SDK key metadata unavailability must actually be hit')
            if r.get('fixture_installed_before_entry') is not True or r.get('read_sites')!=spec['sites'] or r.get('errors')!=[] or r.get('value_preserved') is not True or r.get('cold_reopen_preserved') is not True:
                errors.append(key+': pre-entry fixture, real consumer hits, no exception and cold preservation required')
            before=r.get('storage_before',{});after=r.get('storage_after',{});async_read=r.get('async_read',{})
            if not isinstance(before,dict) or key not in before or type(before[key]) is not type(value) or before[key]!=value or not isinstance(after,dict) or r.get('removed_keys')!=[]:
                errors.append(key+': original typed storage and no deletion required')
            if not isinstance(async_read,dict) or type(async_read.get('value')) is not type(value) or async_read.get('value')!=value:
                errors.append(key+': actual typed async value required')
            if not isinstance(before,dict):before={}
            cold=r.get('cold_storage_after',{})
            if not isinstance(after,dict) or not isinstance(cold,dict) or key not in after or key not in cold or decoded(after.get(key),spec['type'])!=value or decoded(cold.get(key),spec['type'])!=value or any(after.get(k)!=v or cold.get(k)!=v for k,v in before.items() if k!=key):
                errors.append(key+': raw storage/readback or cold restart changed original data')
            errors.extend(key+': '+e for e in validate_business(r))
        bad=[r for r in observations if isinstance(r,dict) and r.get('key')==key and r.get('case')=='unrecoverable']
        if len(bad)!=1:errors.append(key+': missing per-key unrecoverable observation');continue
        r=bad[0]
        if r.get('outcome')=='started_with_fallback':
            errors.extend(fallback_row_errors(key,r));continue
        if new_approval:
            errors.append(key+': a blocking recovery page is no longer accepted; prove outcome started_with_fallback');continue
        blocking=True
        if r.get('fixture_installed_before_entry') is not True or r.get('storage_before')!=r.get('storage_after') or not isinstance(r.get('storage_before'),dict) or key not in r['storage_before'] or r.get('writes')!=[] or r.get('removed_keys')!=[] or r.get('loading_overlay_visible') is not False or r.get('recovery_feedback_visible') is not True:
            errors.append(key+': unreadable original must remain intact with visible bounded recovery')
        if not isinstance(r.get('async_read'),dict) or r['async_read'].get('status') not in ('unreadable','error','timeout','unavailable'):
            errors.append(key+': unrecoverable branch must observe async failure')
        if spec['critical']:
            if r.get('unsafe_grant_or_spend') is not False or r.get('recovery_action',{}).get('trusted_input') is not True or r.get('recovery_action',{}).get('new_attempt_observed') is not True:
                errors.append(key+': critical storage needs no unsafe transactions and actually tapped recovery/new attempt')
        else:
            errors.extend(key+': isolated '+e for e in validate_business(r))
            if r.get('isolated_consumer_writes')!=[]:errors.append(key+': isolated module must not overwrite unreadable settings')
    recovery=result.get('recovery_failure_observations',[])
    if not isinstance(recovery,list):recovery=[]
    # The three modal rows prove the recovery PAGE of the earlier policy; a game without that page has none.
    for case in (('modal_fail','modal_reject','modal_no_callback') if blocking else ()):
        matches=[r for r in recovery if isinstance(r,dict) and r.get('case')==case]
        if len(matches)!=1:
            errors.append('startup recovery missing actual '+case+' observation');continue
        r=matches[0];action=r.get('action',{})
        if r.get('injection_hit') is not True or r.get('recovery_visible') is not True or r.get('loading_overlay_visible') is not False or r.get('errors')!=[] or action.get('trusted_input') is not True or type(action.get('attempt_before')) is not int or type(action.get('attempt_after')) is not int or action['attempt_after']<=action['attempt_before']:
            errors.append(case+': API invocation alone is not visible/tappable recovery with a new attempt')
    return errors


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--native',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    sites=inventory(a.native);doc={'schema':'startup_storage_consumers.v1','sites':sites,'proof_required':bool(sites),'boundary':'actual direct raw storage reads; dynamic domains are unresolved, not covered'}
    a.out.write_text(json.dumps(doc,ensure_ascii=False,indent=2));print(json.dumps({'sites':len(sites),'proof_required':bool(sites)}))
if __name__=='__main__':main()
