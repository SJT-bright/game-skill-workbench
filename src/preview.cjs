const http=require('node:http'),fs=require('node:fs/promises'),path=require('node:path'),crypto=require('node:crypto');
const {LocalWorkbench}=require('./local-workbench.cjs');const root=path.join(__dirname,'../ui'),token=crypto.randomBytes(32).toString('hex'),local=new LocalWorkbench();
const ready=local.init();
const server=http.createServer(async(req,res)=>{res.setHeader('Cache-Control','no-store');try{const name=new URL(req.url,'http://localhost').pathname;
 if(name==='/local-api'){if(req.method!=='POST'||req.headers['x-dock-token']!==token||req.headers.origin!==`http://127.0.0.1:${server.address().port}`){res.writeHead(403);return res.end();}let text='';for await(const chunk of req){text+=chunk;if(text.length>65536)throw Error('请求过大');}await ready;const {method,value}=JSON.parse(text);res.setHeader('Content-Type','application/json; charset=utf-8');return res.end(JSON.stringify({ok:true,value:await local.call(method,value)}));}
 const files={'/':'index.html','/index.html':'index.html','/style.css':'style.css','/glass.css':'glass.css','/workbench.css':'workbench.css','/skill-categories.js':'skill-categories.js','/thread-selection.js':'thread-selection.js','/app.js':'app.js','/demo.cjs.js':'browser-local.js'};
 if(!files[name]){res.writeHead(404);return res.end();}const p=files[name];res.setHeader('Content-Type',p.endsWith('.css')?'text/css':p.endsWith('.js')?'application/javascript':'text/html; charset=utf-8');let data=await fs.readFile(path.join(root,p),'utf8');if(p==='browser-local.js')data=data.replace('__LOCAL_TOKEN__',token);res.end(data);
 }catch(e){res.statusCode=400;res.setHeader('Content-Type','application/json; charset=utf-8');res.end(JSON.stringify({ok:false,error:e.message}));}});
server.listen(Number(process.env.PORT||47830),'127.0.0.1',()=>console.log('Local workbench: http://127.0.0.1:'+server.address().port));
process.on('SIGINT',()=>{require('./codex.cjs').cancelReaders();server.close();process.exit(0);});
