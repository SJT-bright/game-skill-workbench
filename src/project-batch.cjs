const path=require('node:path'),{importProject}=require('./project-import.cjs');
async function importProjects({sources,root,onItem=async()=>{},onProgress=async()=>{},shouldStop=()=>false}){
 if(!Array.isArray(sources)||!sources.length||sources.length>200||sources.some(s=>typeof s!=='string'||!path.isAbsolute(s)))throw Error('每次请选择 1 至 200 个游戏文件夹');
 const unique=[...new Map(sources.map(s=>[process.platform==='win32'?path.resolve(s).toLowerCase():path.resolve(s),s])).values()],results=[];
 for(let i=0;i<unique.length;i++){
  if(shouldStop())break;const source=unique[i],name=path.basename(source);
  try{await onProgress({current:i+1,total:unique.length,name,files:0,totalFiles:null,bytes:0,totalBytes:null});const project=await importProject({source,root,onProgress:p=>onProgress({current:i+1,total:unique.length,name,...p})});const game=await onItem(project);results.push({source,name:project.name,path:project.path,status:'imported',gameId:game?.id});}
  catch(e){results.push({source,name,status:'failed',error:e.message});}
 }
 return {results,total:unique.length,imported:results.filter(r=>r.status==='imported').length,failed:results.filter(r=>r.status==='failed').length,remaining:unique.length-results.length,remainingSources:unique.slice(results.length)};
}
module.exports={importProjects};
