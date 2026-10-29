const fs=require('node:fs/promises'),path=require('node:path');
function projectName(value){const name=String(value||'').normalize('NFC').trim();if(!name||name.length>100||/[\\/\x00-\x1f<>:"|?*]/.test(name)||/[. ]$/.test(name)||/^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(name)||name==='.'||name==='..')throw Error('项目名称不能包含路径或特殊字符');return name;}
async function importProject({source,root,name}){
 if(!path.isAbsolute(root||'')||!path.isAbsolute(source||''))throw Error('请选择收到的文件夹和保存位置');
 const original=await fs.realpath(source),base=await fs.realpath(root);if(!(await fs.stat(base)).isDirectory()||!(await fs.lstat(original)).isDirectory())throw Error('请选择文件夹');
 if(base===original||base.startsWith(original+path.sep))throw Error('保存位置不能放在导入文件夹内部');
 const title=projectName(name||path.basename(original));
 // Collect before creating the destination. Never follow external directory links.
 const files=[];async function walk(dir,rel=''){for(const item of await fs.readdir(dir,{withFileTypes:true})){const relative=path.join(rel,item.name),from=path.join(dir,item.name);if(item.isSymbolicLink())throw Error('文件夹包含符号链接，请先整理为普通文件：'+relative);if(item.isDirectory())await walk(from,relative);else if(!item.isFile())throw Error('不支持的项目文件：'+relative);files.push({relative,directory:item.isDirectory()});}}await walk(original);
 let dest;for(let n=1;n<10000;n++){const next=path.join(base,title+(n===1?'':' ('+n+')'));try{await fs.mkdir(next);dest=next;break;}catch(e){if(e.code!=='EEXIST')throw e;}}if(!dest)throw Error('同名项目过多');
 try{for(const file of files){const to=path.join(dest,file.relative);if(file.directory)await fs.mkdir(to,{recursive:true});else{await fs.mkdir(path.dirname(to),{recursive:true});await fs.copyFile(path.join(original,file.relative),to,require('node:fs').constants.COPYFILE_EXCL);}}return {name:path.basename(dest),path:dest,files:files.filter(f=>!f.directory).length};}catch(e){await fs.rm(dest,{recursive:true,force:true});throw e;}
}
module.exports={projectName,importProject};
