"""GROW-01: genuine SDK objects survive alias changes; Node boundary tests, not device proof."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
KIT = HERE.parent / 'assets/platform-kit'
NODE = r"""
const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert/strict');
const K=process.argv[1],rows=[],negative=[];
const flush=()=>new Promise(r=>setImmediate(r));
async function exercise(flavor,mode,entry,mutant){
 const calls=[],listeners=new Set(),storage=new Map();
 const primary={canIUse(){return false;},getSystemInfoSync(){return {SDKVersion:'1.0.0'};}};
 const task={canIUse(){assert.equal(this,task);return undefined;},getSystemInfoSync(){return {SDKVersion:'1.0.0'};},
  getLaunchOptionsSync(){return {scene:entry};},getEnterOptionsSync(){return {scene:entry};},
  onShow(fn){assert.equal(this,task);listeners.add(fn);},offShow(fn){assert.equal(this,task);listeners.delete(fn);}};
 for(const name of ['addShortcut','startEntranceMission','getShortcutMissionReward','getEntranceMissionReward'])task[name]=function(o){assert.equal(this,task);calls.push(name);o.success({canReceiveReward:true});};
 const g={console,module:{exports:{}},setInterval,clearInterval,setTimeout,clearTimeout,Promise};
 if(mode==='single_ttminis')g.TTMinis={game:task};
 if(mode==='single_tt')g.tt=task;
 if(mode==='single_wx'||mode==='direct_wx')g.wx=task;
 if(mode==='split_tt'){g.TTMinis={game:primary};g.tt=task;}
 if(mode==='split_wx'){g.TTMinis={game:primary};g.wx=task;}
 if(mode==='first_false'||mode==='first_throw'){
  g.TTMinis={game:{canIUse(){if(mode==='first_throw')throw Error('unsupported candidate');return false;},startEntranceMission(){throw Error('wrong SDK');},getEntranceMissionReward(){throw Error('wrong SDK');}}};g.tt=task;
 }
 const c=vm.createContext(g),cache={};
 function source(rel){return fs.readFileSync(path.join(K,rel),'utf8');}
 function load(name){
  if(cache[name])return cache[name].exports;
  const module={exports:{}};cache[name]=module;
  let text=source('assets/tiktok-platform/'+name+'.js');
  if(name==='TikTokMissionService'&&mutant==='drop_wx'){
   const line="  try { add(typeof wx !== 'undefined' && wx); } catch (_) {}";assert(text.includes(line));text=text.replace(line,'');
  }
  if(name==='TikTokMissionService'&&mutant==='first_object'){
   const start=text.indexOf('function sdk(method) {'),end=text.indexOf('\nfunction isCurrent',start);assert(start>=0&&end>start);text=text.slice(0,start)+'function sdk(method) { return sdkCandidates()[0] || null; }\n'+text.slice(end);
  }
  const factory=vm.runInContext('(function(module,exports,require){'+text+'\n})',c);
  factory(module,module.exports,id=>load(id.replace(/^.*\//,'').replace(/\.js$/,'')));return module.exports;
 }
 let shim=source('parts/host-shim.js');
 if(mutant==='no_capture'){
  const line='var providers = captureSDKProviders(sdk, root, opts.alsoGlobals !== false);';assert(shim.includes(line));shim=shim.replace(line,'var providers = [];');
 }
 const mod={exports:{}};vm.runInContext('(function(module,exports){'+shim+'\n})',c)(mod,mod.exports);
 if(mode!=='direct_wx'&&mode!=='no_sdk')mod.exports.install(g.TTMinis?.game||g.tt||g.wx);
 // This is the adapter's real failure boundary: aliases may be changed before game modules load.
 if(mode==='split_tt'||mode==='split_wx'){g.tt=primary;g.wx=primary;}
 let Mission,Flow,Store;
 if(flavor==='plugin'&&!mutant){
  for(const name of ['PlatformConfig','TikTokMissionService','SaveStore','MissionFlow'])vm.runInContext(source('plugins-3x/'+name+'.plugin.js'),c);
  Mission=g.TikTokKit.TikTokMissionService;Flow=g.TikTokKit.MissionFlow;Store=g.TikTokKit.SaveStore;
 }else{Mission=load('TikTokMissionService');Flow=load('MissionFlow');Store=load('SaveStore');}
 const store=new Store({coins:0},{schema:false,login:false,storage:{getItem:k=>storage.get(k)||null,setItem(k,v){storage.set(k,String(v));}}});assert(store.load().ok);
 const flow=new Flow({store,render(){},reward(kind,d){d.coins+=50;},missionTimeoutMs:100});
 await flow.startEntryTracking();await flush();
 if(entry==='scan_qrcode'&&mode!=='no_sdk'){
  await flow.open('profile',{navigate:true});assert.equal(calls[0],'startEntranceMission');for(const fn of [...listeners])fn({scene:'center'});await flush();
 }
 if(mode==='no_sdk'){assert.equal(calls.length,0);assert.equal(store.get().coins,0);flow.dispose();return;}
 const wanted=entry==='desktop_shortcut'?'getShortcutMissionReward':'getEntranceMissionReward';
 assert(calls.includes(wanted),'missing '+wanted+' after namespace adaptation');assert.equal(store.get().coins,50);assert(store.isClaimed(entry==='desktop_shortcut'?'shortcut':'profile'));
 const count=calls.length;for(const fn of [...listeners])fn({scene:entry==='desktop_shortcut'?entry:'center'});await flush();assert.equal(store.get().coins,50);assert.equal(calls.length,count);
 // Returned candidate arrays cannot change the retained registry or mint APIs.
 const candidates=Mission.sdkCandidates();candidates.length=0;assert(Mission.sdkCandidates().length>0);
 flow.dispose();assert.equal(listeners.size,0);
}
(async()=>{
 for(const flavor of ['commonjs','plugin']){
  for(const mode of ['single_ttminis','single_tt','single_wx','split_tt','split_wx','direct_wx','first_false','first_throw']){
   for(const entry of ['scan_qrcode','center','desktop_shortcut']){await exercise(flavor,mode,entry);rows.push({flavor,mode,entry,passed:true});}
  }
  await exercise(flavor,'no_sdk','scan_qrcode');rows.push({flavor,mode:'no_sdk',passed:true});
 }
 for(const [name,mode]of [['no_capture','split_tt'],['drop_wx','direct_wx'],['first_object','split_wx']]){
  let detected=false;try{await exercise('commonjs',mode,'scan_qrcode',name);}catch(e){if(e.code==='ERR_ASSERTION')detected=true;else throw e;}
  assert(detected,'negative control '+name+' must fail the same behavioral check');negative.push({name,detected:true});
 }
 console.log(JSON.stringify({schema:'known_issue_negative_control.v1',issue_id:'GROW-01',scope:'Node genuine-object boundary fixtures; no TikTok device or review claim',current_cases:rows.length,current_passed:rows.every(r=>r.passed),negative_controls:negative,rows}));
})().catch(e=>{console.error(e);process.exitCode=1;});
"""

class SDKProviderRetention(unittest.TestCase):
    def command(self, argv):
        result = subprocess.run(argv, capture_output=True, text=True, timeout=90, cwd=KIT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_same_sdk_boundary_and_negative_controls(self):
        raw = self.command(['node', '-e', NODE, str(KIT)])
        data = json.loads(raw.strip().splitlines()[-1])
        self.assertTrue(data['current_passed'])
        self.assertEqual(len(data['negative_controls']), 3)
        print('GROW01_SDK_PROVIDERS ' + json.dumps(data, separators=(',', ':')))

    def test_existing_host_contracts(self):
        self.command(['node', str(KIT / 'tests/host-shim.test.js')])

    def test_existing_entry_tracking(self):
        self.command(['node', str(KIT / 'tests/entry-tracking.test.js')])

    def test_generated_plugins_and_startup_wiring(self):
        self.command([sys.executable, '-B', str(KIT / 'tools/make_plugin_scripts.py'), '--check'])
        self.command([sys.executable, '-B', str(HERE / 'test_finalize_hostshim_boot.py')])

if __name__ == '__main__':
    unittest.main()
