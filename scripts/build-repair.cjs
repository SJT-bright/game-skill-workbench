const fs=require('node:fs/promises'),path=require('node:path'),crypto=require('node:crypto');
async function build(){
 const root=path.resolve(__dirname,'..'),version=require('../package.json').version,out=path.join(root,'release',`GameDesk-${version}-Windows-Repair`),payload=path.join(out,'payload');
 await fs.rm(out,{recursive:true,force:true});await fs.mkdir(payload,{recursive:true});
 for(const name of ['src','ui'])await fs.cp(path.join(root,name),path.join(payload,name),{recursive:true});
 await fs.writeFile(path.join(payload,'ui/demo.cjs.js'),'// Desktop client: real files.\n');
 await fs.cp(path.join(root,'skills'),path.join(payload,'bundled-skills'),{recursive:true});
 for(const name of ['package.json','distribution.json','LICENSE','THIRD_PARTY_NOTICES.md'])await fs.copyFile(path.join(root,name),path.join(payload,name));
 const files=[];async function walk(dir,prefix=''){for(const e of await fs.readdir(dir,{withFileTypes:true})){const relative=prefix+e.name,p=path.join(dir,e.name);if(e.isDirectory())await walk(p,relative+'/');else{const b=await fs.readFile(p);files.push({path:relative,bytes:b.length,sha256:crypto.createHash('sha256').update(b).digest('hex')});}}}await walk(payload);
 await fs.writeFile(path.join(out,'repair-manifest.json'),JSON.stringify({schema:1,version,files},null,2));
 const installer=await fs.readFile(path.join(root,'scripts/Repair-Windows.ps1'),'utf8');await fs.writeFile(path.join(out,'Repair.ps1'),'\uFEFF'+installer);
 await fs.writeFile(path.join(out,'Update.cmd'),'@echo off\r\ncd /d "%~dp0"\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Repair.ps1"\r\n');
 await fs.writeFile(path.join(out,'使用说明.txt'),'Windows 已安装用户修复升级包\r\n\r\n1. 在旧工作台的 设置 中点击 退出（只收起浮窗不够）。\r\n2. 将本压缩包完整解压到独立目录，不要直接覆盖原安装目录。\r\n3. 双击 Update.cmd，选择原来包含 GameDeskSkill.exe 的安装文件夹。\r\n4. 完成后会自动启动 '+version+'。\r\n\r\n无需重复下载运行时。游戏、Codex对话、Skill同步目录与个人设置保持原样。\r\n原程序文件备份位置记录在原安装目录 repair-receipt.json。\r\n如果还未安装过工作台，请下载完整 Windows 包。\r\n');
 console.log(out);
}
if(require.main===module)build().catch(e=>{console.error(e.message);process.exitCode=1;});module.exports={build};
