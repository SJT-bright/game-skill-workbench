'use strict';
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const child = require('child_process');
const api = require('./ad_display_config.cjs');
const kit = path.resolve(__dirname, '../assets/platform-kit');
const work = fs.mkdtempSync(path.join(os.tmpdir(), '广告配置 setup '));
const results = [];
function project(plugin = false, suffix = '') {
  const root = path.join(work, String(results.length) + suffix), dir = path.join(root, 'assets/tiktok-platform');
  fs.mkdirSync(dir, {recursive: true});
  fs.writeFileSync(path.join(root,plugin?'package.json':'project.json'),JSON.stringify(plugin?{creator:{version:'3.8.8'}}:{version:'2.4.15'}));
  for (const name of ['PlatformConfig','AdDisplayPolicy','RewardedService']) {
    const file = name + (plugin ? '.plugin.js' : '.js');
    const source = path.join(kit, plugin ? 'plugins-3x' : 'assets/tiktok-platform', file);
    fs.copyFileSync(source, path.join(dir, file));
    if (plugin) fs.writeFileSync(path.join(dir,file+'.meta'), JSON.stringify({userData:{isPlugin:true,loadPluginInMiniGame:true}}));
  }
  const file = path.join(dir,'PlatformConfig'+(plugin?'.plugin':'')+'.js');
  fs.writeFileSync(file,fs.readFileSync(file,'utf8').replace("gameId: 'change-me'", "gameId: 'portable-game'"));
  return {root,dir,file};
}
async function test(name,run) { try {await run();results.push({name,status:'passed'});} catch(e){results.push({name,status:'failed',error:e.stack});} }
const remote='https://config.example.test/portable.json';
(async()=>{
  await test('empty_remote_is_explicit_package_only_and_require_remote_fails',()=>{
    const p=project(); const local=api.check(p.root,false), required=api.check(p.root,true);
    assert(local.passed);assert.strictEqual(local.status,'package_config_only');assert.strictEqual(local.liveVerified,false);
    assert.strictEqual(required.passed,false);assert(required.problems.some(x=>x.includes('remoteUrl')));
  });
  await test('configure_changes_only_selected_data_and_keeps_identity_rewards_placements',()=>{
    const p=project(), before=fs.readFileSync(p.file,'utf8');
    const result=api.configure(p.root,{remoteUrl:remote});const after=fs.readFileSync(p.file,'utf8');
    assert.strictEqual(after,before.replace("remoteUrl: ''",'remoteUrl: '+JSON.stringify(remote)));
    assert.strictEqual(fs.readFileSync(result.backup,'utf8'),before);assert.strictEqual(result.localEnabled,true);
    assert(api.check(p.root,true).passed);assert.strictEqual(api.check(p.root,true).liveVerified,false);
  });
  await test('same_configuration_is_idempotent',()=>{
    const p=project();api.configure(p.root,{remoteUrl:remote});const b=fs.readFileSync(p.file);
    assert.strictEqual(api.configure(p.root,{remoteUrl:remote}).changed,false);assert(fs.readFileSync(p.file).equals(b));
  });
  await test('dry_run_creates_no_project_files',()=>{
    const p=project(),before=fs.readFileSync(p.file);api.configure(p.root,{remoteUrl:remote,dryRun:true});
    assert(fs.readFileSync(p.file).equals(before));assert(!fs.existsSync(path.join(p.root,'.tiktok-kit')));
  });
  await test('old_config_missing_block_gets_default_ON_without_editing_other_fields',()=>{
    const p=project();let text=fs.readFileSync(p.file,'utf8');const parsed=api.parse(text);
    text=text.slice(0,parsed.map.adDisplay.start)+text.slice(parsed.map.adDisplay.end+1);fs.writeFileSync(p.file,text);
    assert.strictEqual(api.check(p.root,false).passed,false);api.configure(p.root,{remoteUrl:remote});
    assert(api.check(p.root,true).passed);assert.strictEqual(api.parse(fs.readFileSync(p.file,'utf8')).config.adDisplay.enabled,true);
  });
  await test('remote_setup_preserves_existing_explicit_local_OFF',()=>{
    const p=project();api.configure(p.root,{enabled:false});api.configure(p.root,{remoteUrl:remote});
    assert.strictEqual(api.check(p.root,true).localEnabled,false);
  });
  await test('invalid_https_value_fails_before_backup_or_project_write',()=>{
    for(const url of ['http://example.test/x','https://user:pass@example.test/x','https://example.test/x#bad']) {
      const p=project(false,url.length),before=fs.readFileSync(p.file);assert.throws(()=>api.configure(p.root,{remoteUrl:url}));
      assert(fs.readFileSync(p.file).equals(before));assert(!fs.existsSync(path.join(p.root,'.tiktok-kit')));
    }
  });
  await test('project_scripts_are_parsed_without_execution',()=>{
    const p=project();fs.appendFileSync(p.file,'\nthrow new Error("project code must never execute");\n');
    api.configure(p.root,{remoteUrl:remote});assert(api.check(p.root,true).passed);
  });
  await test('missing_or_changed_policy_is_reported',()=>{
    const p=project();fs.appendFileSync(path.join(p.dir,'AdDisplayPolicy.js'),'\n// changed');
    assert.strictEqual(api.check(p.root,false).passed,false);
    fs.unlinkSync(path.join(p.dir,'AdDisplayPolicy.js'));assert.strictEqual(api.check(p.root,false).passed,false);
  });
  await test('Cocos3_setup_uses_generated_plugin_and_requires_plugin_metadata',()=>{
    const p=project(true);api.configure(p.root,{remoteUrl:remote});assert(api.check(p.root,true).passed);
    fs.unlinkSync(path.join(p.dir,'AdDisplayPolicy.plugin.js.meta'));assert.strictEqual(api.check(p.root,true).passed,false);
  });
  await test('Cocos3_missing_editable_PlatformConfig_plugin_metadata_also_fails',()=>{
    const p=project(true);api.configure(p.root,{remoteUrl:remote});assert(api.check(p.root,true).passed);
    fs.unlinkSync(p.file+'.meta');const result=api.check(p.root,true);
    assert.strictEqual(result.passed,false);assert(result.problems.some(x=>x.includes('PlatformConfig')));
  });
  await test('engineering_version_must_match_plain_or_plugin_platform_files',()=>{
    const plain=project(false,'plain'),plugin=project(true,'plugin');
    fs.writeFileSync(path.join(plain.root,'package.json'),JSON.stringify({creator:{version:'3.8.8'}}));
    assert.throws(()=>api.check(plain.root,true),/不匹配/);
    fs.unlinkSync(path.join(plugin.root,'package.json'));
    fs.writeFileSync(path.join(plugin.root,'project.json'),JSON.stringify({version:'2.4.15'}));
    assert.throws(()=>api.check(plugin.root,true),/不匹配/);
  });
  await test('payload_has_exact_project_identity_and_increasing_revision',()=>{
    const p=project(),out=path.join(p.root,'后台响应.json');api.payload(p.root,false,7,out);
    const value=JSON.parse(fs.readFileSync(out));assert.strictEqual(value.gameId,'portable-game');assert.strictEqual(value.ads.enabled,false);
    assert.throws(()=>api.payload(p.root,true,7,out),/revision/);api.payload(p.root,true,8,out);
    assert.strictEqual(JSON.parse(fs.readFileSync(out)).revision,8);
  });
  await test('invalid_payload_and_other_game_output_are_not_overwritten',()=>{
    const p=project(),out=path.join(p.root,'remote.json');assert.throws(()=>api.payload(p.root,'false',1,out));
    assert.throws(()=>api.payload(p.root,false,-1,out));assert.throws(()=>api.payload(p.root,false,Number.MAX_SAFE_INTEGER+1,out));
    fs.writeFileSync(out,JSON.stringify({gameId:'another',appId:'other',channel:'production',revision:1}));
    const b=fs.readFileSync(out);assert.throws(()=>api.payload(p.root,false,2,out));assert(fs.readFileSync(out).equals(b));
  });
  await test('remote_response_OFF_and_newer_ON_pass_real_policy_validation',async()=>{
    const p=project();api.configure(p.root,{remoteUrl:remote});const cfg=api.parse(fs.readFileSync(p.file,'utf8')).config;
    const response=enabled=>({schemaVersion:1,gameId:cfg.gameId,appId:cfg.appId,channel:cfg.adDisplay.channel,revision:enabled?3:2,ads:{enabled}});
    const off=await api.probe(p.root,async()=>response(false)),on=await api.probe(p.root,async()=>response(true));
    assert.strictEqual(off.effectiveEnabled,false);assert.strictEqual(on.effectiveEnabled,true);assert.strictEqual(off.cacheWritten,false);
  });
  await test('mismatched_remote_identity_is_rejected',async()=>{
    const p=project();api.configure(p.root,{remoteUrl:remote});
    await assert.rejects(()=>api.probe(p.root,async()=>({schemaVersion:1,gameId:'wrong',appId:'wrong',channel:'production',revision:1,ads:{enabled:false}})),/拒绝/);
  });
  await test('CLI_runs_from_an_unrelated_working_directory_with_spaces_and_unicode',()=>{
    const p=project(true),r=child.spawnSync(process.execPath,[path.join(__dirname,'ad_display_config.cjs'),'configure','--project',p.root,'--remote-url',remote],{cwd:work,encoding:'utf8'});
    assert.strictEqual(r.status,0,r.stderr);assert.strictEqual(JSON.parse(r.stdout).remoteConfigured,true);
  });
  await test('CLI_rejects_string_boolean_and_unknown_flags',()=>{
    const p=project();for(const arg of [['--enabled','False'],['--bad','x']]){
      const r=child.spawnSync(process.execPath,[path.join(__dirname,'ad_display_config.cjs'),'configure','--project',p.root,...arg],{encoding:'utf8'});
      assert.notStrictEqual(r.status,0);
    }
  });
  await test('remote_probe_has_an_absolute_timeout_without_response',async()=>{
    const https=require('https'),EventEmitter=require('events'),original=https.get;
    let destroyed=false;
    try {
      https.get=()=>{const req=new EventEmitter();req.destroy=error=>{destroyed=true;req.emit('error',error);};return req;};
      await assert.rejects(()=>api.fetchJSON(remote,20),/超时/);assert(destroyed);
    } finally {https.get=original;}
  });
  fs.rmSync(work,{recursive:true,force:true});
  const failed=results.filter(x=>x.status==='failed').length;
  console.log(JSON.stringify({suite:'ad-display-config',passed:results.length-failed,failed,results},null,2));process.exitCode=failed?1:0;
})().catch(error=>{fs.rmSync(work,{recursive:true,force:true});throw error;});
