const path=require('node:path');const os=require('node:os');const fs=require('node:fs/promises');const {HubStore,startHub,readJSON,atomicJSON}=require('./core.cjs');
(async()=>{
 const root=process.env.SKILL_HUB_DATA||path.join(os.homedir(),'.skill-dock-hub');await fs.mkdir(root,{recursive:true});
 const store=new HubStore(root);const settings=await readJSON(path.join(root,'server.json'),{});
 const hub=await startHub(store,{host:process.env.HOST||'127.0.0.1',port:Number(process.env.PORT||47831),token:process.env.SKILL_HUB_TOKEN||settings.token});await atomicJSON(path.join(root,'server.json'),{token:hub.token});
 console.log('Skill Hub listening on port '+hub.port+'; subscription token is in server.json (not logged).');
 let running=false;const tick=async()=>{if(running)return;running=true;try{const sources=await readJSON(path.join(root,'sources.json'),[]);for(const s of sources){const r=await store.publish(s.path,s.name,s.note||'');if(r.changed){hub.notify();console.log('Published '+r.release.name+' '+r.release.version);}}}catch(e){console.error(e.message);}finally{running=false;}};
 await tick();const timer=setInterval(tick,20000);async function stop(){clearInterval(timer);await hub.close();process.exit(0);}process.on('SIGTERM',stop);process.on('SIGINT',stop);
})().catch(e=>{console.error(e.message);process.exit(1);});
