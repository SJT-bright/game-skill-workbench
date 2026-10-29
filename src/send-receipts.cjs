const {readJSON,atomicJSON}=require('./core.cjs');const locks=new Map();
function edit(file,fn){const previous=locks.get(file)||Promise.resolve();const current=previous.catch(()=>{}).then(async()=>{const records=await readJSON(file,{}),result=await fn(records);await atomicJSON(file,records);return result;});locks.set(file,current);return current.finally(()=>{if(locks.get(file)===current)locks.delete(file);});}
async function sendWithReceipt({file,key,threadId,skillId,send}){
 const attempt=require('node:crypto').randomUUID();await edit(file,records=>{if(records[key]?.status==='uncertain')throw Error('上次发送待确认，请先查看目标对话，勿重复发送');records[key]={status:'uncertain',detail:'发送已开始，尚未取得回执',threadId,skillId:skillId||null,attempt,createdAt:new Date().toISOString()};});
 let result;try{result=await send();}catch(e){throw Error('发送回执未确认，请先查看目标对话，避免重复发送：'+e.message);}
 await edit(file,records=>{if(records[key]?.attempt===attempt)records[key]={...records[key],...result,finishedAt:new Date().toISOString()};});return result;
}
module.exports={sendWithReceipt};
