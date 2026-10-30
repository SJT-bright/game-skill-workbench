"""Synthetic schema calibration only; never gameplay evidence."""
from pathlib import Path
import json,tempfile,subprocess,sys
from copy import deepcopy
from PIL import Image
import audit_startup_loading as gate

def fixture(root,binding):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    plan={'declared_at':'2020-01-01T00:00:00+00:00','binding':binding,'viewports':[[390,844],[360,640]],
          'profiles':{'local':{'network':None,'cold':3,'warm':1},'first_network':{'network':{'download_kbps':10000,'upload_kbps':5000,'latency_ms':80},'cold':3,'warm':1},'slow_network':{'network':{'download_kbps':2000,'upload_kbps':1000,'latency_ms':150},'cold':1,'warm':0}}}
    p=root/'plan.json';p.write_text(json.dumps(plan));digest=gate.sha(p);dirs=[]
    specs=[]
    for w,h in plan['viewports']:
        for profile,settings in plan['profiles'].items():
            for cache in ('cold','warm'):
                for n in range(settings[cache]):specs.append((f'{w}-{profile}-{cache}-{n}',w,h,profile,cache,None))
    for fault in gate.FAULTS:specs.append((fault,390,844,'local','cold',fault))
    for name,w,h,profile,cache,fault in specs:
        d=root/name;(d/'frames').mkdir(parents=True,exist_ok=True);dirs.append(d)
        Image.new('RGB',(2,2),'#9fbbaa').save(d/'frames/00001_0ms.jpg')
        r={'binding':binding,'startup_plan_sha256':digest,'status':'completed_pending_business_and_visual_review','profile':profile,'network_applied':plan['profiles'][profile]['network'],'cache_mode':cache,'cache_disabled':cache=='cold','warmup_done':cache=='warm','viewport_requested':{'width':w,'height':h},'marks':{'first_feedback':0,'home_usable':10,'play_touch':20,'level_ready':30,'first_effect':40},'requests':[],'entry_epoch':1700000000,'recording':{'first_frame_epoch':1700000000,'dir':str(d/'frames'),'frame_phases':[]},'fault':fault,'init_js_sha256':'f'*64,'optional_modal_unused':True,'optional_modal_calls':0,'held_requests':[{'synthetic':True}],'steps':[{'action':{'type':'unblock'}}]}
        if fault=='slow_progress':r['marks'].update(home_usable=16001,first_effect=16040)
        if fault=='background_wait':r['background']=[{'from_ms':0,'to_ms':11001,'visibility_while_away':'hidden'}]
        if fault=='stall_retry':r['marks']['retry_shown']=10000
        if fault=='late_callback':r['marks']['old_result_arrived']=100
        if fault=='image_no_callback':r['marks']['retry_shown']=10000
        if fault=='audio_fail':r['requests']=[{'failed':True}]
        (d/'report.json').write_text(json.dumps(r))
    raw,frames=gate.raw_manifest(dirs)
    return dict(tool='audit_startup_loading',policy_version=gate.POLICY_VERSION,plan_file=str(p),plan_sha256=digest,run_directories=[str(d)for d in dirs],raw_reports=raw,raw_frames=frames,binding=binding,checked=len(dirs),failed=0,passed=True,checks=[])

def main():
    binding=dict(source_sha256='a'*64,native_tree_sha256='b'*64,web_tree_sha256='c'*64,build_tag='SYNTHETIC-not-game-proof');rows=[]
    with tempfile.TemporaryDirectory()as td:
        root=Path(td);report=fixture(root,binding)
        def test(name,change,expected):
            d=deepcopy(report);change(d);actual=not gate.validate_report(d,binding);rows.append(dict(id=name,passed=actual==expected))
        test('complete_synthetic_schema',lambda d:None,True)
        test('missing_policy',lambda d:d.pop('policy_version'),False)
        test('stale_binding',lambda d:d.update(binding={}),False)
        test('missing_manifest',lambda d:d.update(raw_reports={}),False)
        test('changed_frame_hash',lambda d:d.update(raw_frames={}),False)
        test('missing_normal_runs',lambda d:d.update(run_directories=d['run_directories'][-8:],checked=8),False)
        test('duplicate_run_directory',lambda d:d.update(run_directories=d['run_directories']+[d['run_directories'][0]],checked=27),False)
        # W3a R5 / D3 problem 4: a v7.5 timing report (has frame_rate) without timing_valid true is not LOAD-03 evidence.
        first=Path(report['run_directories'][0])/'report.json';original=first.read_text()
        for tag,valid,expected in (('invalid_timing_run_rejected',False,False),('valid_timing_run_accepted',True,True)):
            r=json.loads(original);r.update(timing=True,timing_valid=valid,frame_rate={'lowest_fps_in_window':60 if valid else 2,'min_fps':30});first.write_text(json.dumps(r))
            d=deepcopy(report);d['raw_reports'],d['raw_frames']=gate.raw_manifest(d['run_directories'])
            rows.append(dict(id=tag,passed=(not gate.validate_report(d,binding))==expected))
        first.write_text(original)
        binding_file=root/'binding.json';binding_file.write_text(json.dumps({'binding':binding}))
        cli=[sys.executable,str(Path(gate.__file__)), '--plan',report['plan_file'],'--runs',*report['run_directories'],'--binding',str(binding_file)]
        run=subprocess.run(cli+['--out',str(root/'positive-cli.json')],capture_output=True,text=True)
        rows.append(dict(id='real_cli_writes_current_manifest',passed=run.returncode==0 and json.loads((root/'positive-cli.json').read_text()).get('policy_version')==gate.POLICY_VERSION))
        p=Path(report['plan_file']);plan=json.loads(p.read_text());plan['profiles']['local']['cold']=0;p.write_text(json.dumps(plan));changed=deepcopy(report);changed['plan_sha256']=gate.sha(p)
        for raw in changed['raw_reports']:
            f=Path(raw);r=json.loads(f.read_text());r['startup_plan_sha256']=changed['plan_sha256'];f.write_text(json.dumps(r))
        changed['raw_reports'],changed['raw_frames']=gate.raw_manifest(changed['run_directories']);rows.append(dict(id='resigned_plan_cannot_waive_minimum_runs',passed=bool(gate.validate_report(changed,binding))))
        run=subprocess.run(cli+['--out',str(root/'negative-cli.json')],capture_output=True,text=True)
        rows.append(dict(id='real_cli_rejects_waived_coverage',passed=run.returncode==1 and json.loads((root/'negative-cli.json').read_text()).get('passed')is False))
    print(json.dumps(dict(passed=all(r['passed']for r in rows),checked=len(rows),scope='Synthetic gate calibration, not a game pass',cases=rows)));return not all(r['passed']for r in rows)
if __name__=='__main__':raise SystemExit(main())
