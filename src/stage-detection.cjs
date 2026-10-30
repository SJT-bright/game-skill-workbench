const VERSION=2;
function cleanText(value){
 let text=String(value||'');
 if(/^\s*#\s*AGENTS\.md\b/i.test(text)||/^\s*<(?:environment_context|permissions|collaboration_mode)\b/i.test(text))return '';
 return text.replace(/```[\s\S]*?(?:```|$)/g,'').replace(/<(?:environment_context|in-app-browser-context|external_codex_apps_open_page)[^>]*>[\s\S]*?<\/(?:environment_context|in-app-browser-context|external_codex_apps_open_page)>/g,'').replace(/^\s*>.*$/gm,'').slice(-16000);
}
function inferStage(messages,{previous}={}){
 let reopened=false;
 for(let n=messages.length-1;n>=0;n--){
  const message=messages[n],role=message.role,text=cleanText(message.text);if(!text)continue;
  const lines=text.split(/[\n。！!？?；;]/).map(s=>s.trim()).filter(Boolean);let best=null;
  for(let j=0;j<lines.length;j++){
   if(/玩法.*(?:美工|美术).*(?:测试|检查)/.test(lines[j])&&!/进入|开始|现在|正在|完成/.test(lines[j]))continue;const clauses=lines[j].split(/[，,]/);for(let k=0;k<clauses.length;k++){
    let line=clauses[k].trim();if(!line||line.length>1400)continue;
    if(/^(?:本次更新说明|完整组件|Skill 目录|Skill 路径|文件树 SHA|完整压缩包|Skill：|项目目录：|当前游戏：)/i.test(line))continue;
    if(/使用(?:这个)?新版\s*Skill.*继续|沿用.*当前进度|玩法.*美工.*测试|玩法.*美工.*检查/.test(line))continue;
    if(/(?:之前|此前|历史|上次|原先|曾经|比如|例如|举例|不能称|不代表)/.test(line))continue;
    if((k>0&&/^(?:再|然后)/.test(line))||/^(?:之后|后续|以后|随后)/.test(line))continue;
    if(/(?:尚未|还未|还没|没有|未)(?:开始|进入|进行)|(?:美工|美术|玩法)(?:制作|阶段)?未开始/.test(line))continue;
    if(/^(?:完成|做完|美工完成|玩法完成).*(?:后|之后)(?:再|才|将)/.test(line)||/后再|后再去|之后再/.test(line))continue;
    if(/明天|下周|下个月|以后|未来|有空|计划/.test(line)&&!/现在|马上|立即/.test(line))continue;
    const future=/(?:下一步|下一阶段|接下来|后续|计划|准备|将会|稍后|随后)/.test(line);
    if(future&&role!=='user'&&!/(?:现在|正在|已经|已开始|我会先|我现在)/.test(line))continue;
    if(/(?:不要|暂不|先不|无需|不需要|别)(?:再|进行|做|进入|开始|使用|调用|执行|去|先|\s)*(?:美工|美术|测试|检查|试玩|玩法|重塑|换皮)/.test(line))continue;
    const candidates=[];const add=(stage,score)=>candidates.push({stage,score});
    const notDone=/(?:未|没|尚未|还未|还没|没有).{0,4}(?:完成|结束|通过)|不通过|未达标/.test(line);
    if(!notDone&&/(?:游戏|项目|本游戏|制作)(?:已全部完成|已完成交付|全部完成|已完结)|正式完成|最终验收(?:已)?通过|项目完结了/.test(line))add('已完成',120);
    if(/(?:当前|目前|正在|现在).{0,8}(?:处于|进行|做|进入|是)?.{0,3}(?:玩法|美工|美术|测试|检查)(?:制作|阶段)/.test(line)||/(?:进入|开始|切换到|转入).{0,5}(?:玩法|美工|美术|测试|检查|试玩)/.test(line)){
     if(/美工|美术/.test(line))add('美工制作',110);else if(/测试|检查|试玩/.test(line))add('检查',110);else add('玩法制作',110);
    }
    if(!notDone&&/美工(?:制作|阶段)?(?:已|已经)?(?:完成|结束|通过)|美术(?:制作|阶段)?(?:已|已经)?(?:完成|结束|通过)/.test(line))add('待试玩',105);
    if(!notDone&&/玩法(?:制作|阶段)?(?:已|已经)?(?:完成|结束|通过)|玩法确认(?:已)?(?:完成|通过)/.test(line))add('玩法结束',95);
    if(/待试玩|(?:等待|待|请你|交给你|给你)(?:进行)?(?:本地)?试玩|(?:已提供|已交付|给你).{0,12}(?:试玩|预览)链接/.test(line))add('待试玩',100);
    if(/正在(?:本地)?试玩|进入(?:本地)?(?:游玩|试玩)阶段|游玩阶段|开始(?:本地)?试玩|已(?:打开|启动).{0,8}(?:试玩|预览)/.test(line))add('游玩',100);
    if(/独立解压|逐文件校验|(?:ZIP|压缩包).{0,12}(?:完整性|CRC)|(?:最终|最新)?源码包.{0,12}(?:完整性检查|已打好|已生成)|构建.{0,10}测试.{0,8}通过|(?:检查|核对).{0,12}(?:测试包|导出包).{0,8}(?:一致|通过)|源码.{0,12}(?:交付|打包完成)/i.test(line))add('检查',90);
    if(/(?:试玩|预览)窗口(?:已|已经)?打开|打开同版本试玩/.test(line))add('游玩',100);
    if(/(?:测试|检查|验收)阶段|检测成品|(?:开始|正在|执行|进行|继续).{0,8}(?:检查|测试|验收)(?:游戏|成品|一遍|一下|阶段|$)|(?:开始|正在|执行|进行|继续|跑|做).{0,8}(?:整体验收|验收|回归测试|触屏测试|真机测试|游戏测试|成品检查)|(?:生成|打成|打包|交付|导出).{0,14}(?:测试包|TikTok|Native)|试玩.{0,8}(?:白屏|报错|发现|失败|卡住)|测试(?:不通过|未通过|失败)/i.test(line))add('检查',90);
    if(role==='user'&&/^(?:试玩|预览).{0,70}$|(?:给|打开|启动|提供).{0,6}(?:试玩|预览)/.test(line))add('游玩',90);
    if(role==='user'&&/(?:测试|检查|试玩|验收)(?:一下|下|这个|这款|游戏|成品|一遍|一轮)|(?:这个|这款|游戏).{0,10}(?:测试|检查|试玩)|本地(?:预览|试玩)|给我.{0,6}(?:预览|试玩)|^(?:测试|试玩|检查|验收)$/.test(line))add(/试玩|预览/.test(line)?'游玩':'检查',90);
    if(role==='user'&&(/^(?:先|现在|马上|立即)?(?:做|进行)?(?:美工|美术)|(?:美工|美术|UI|界面|背景|贴图).{0,12}(?:重做|调整|修改|替换|优化)|这页太丑|页面太丑/.test(line)))add('美工制作',85);
    if(/美工(?:制作|阶段)|美术(?:制作|阶段)|(?:开始|进入|用|使用|调用).{0,6}(?:美工|美术)|(?:修改|修复|调整|重做|替换|设计|生成|制作|改成|换).{0,14}(?:美工|美术|界面|UI|按钮样式|按钮贴图|贴图|背景|角色形象|素材|音效)|美术与声音|换皮/i.test(line))add('美工制作',80);
    if(/玩法(?:制作|阶段)|制作玩法|开始(?:制作|重塑)|(?:新增|修复|调整|修改|设计|制作|优化).{0,12}(?:玩法|关卡|机制|游戏逻辑|操作逻辑)|(?:开始|继续|进行|用|使用).{0,8}(?:英化|重塑)|^英化.{0,60}$|^重塑.{0,60}$/.test(line))add('玩法制作',75);
    if(/(?:使用|调用|用|按).{0,80}(?:remake-art|cocos-game-art-redo)\b/i.test(line)||role==='user'&&/^\$?(?:remake-art|cocos-game-art-redo)\b/.test(line))add('美工制作',85);
    if(/(?:使用|调用|用|按).{0,80}(?:cocos-game-check|cocos-game-finished-product-check|cocos-tiktok-package-check|cocos-game-tiktok-package)\b/i.test(line)||role==='user'&&/^\$?(?:cocos-game-check|cocos-game-finished-product-check)\b/.test(line))add('检查',85);
    if(/(?:使用|调用|用|按).{0,80}(?:cocos-game-from-starter|remake-game|cocos-game-to-english)\b/i.test(line))add('玩法制作',70);
    for(const candidate of candidates)if(!best||candidate.score>=best.score)best={...candidate,evidence:line.slice(0,200)};
   }
  }
  if(best&&!(reopened&&best.stage==='已完成'))return {stage:best.stage,evidence:best.evidence,role,certainty:best.score>=100?'explicit':'context',at:message.at||message.timestamp||null,messageId:message.id||null,algorithmVersion:VERSION};
  if(role==='user'&&/(?:继续|修改|修复|重做|开始)/.test(text))reopened=true;
 }
 if(previous?.stage&&!(reopened&&previous.stage==='已完成'))return {...previous,continued:true,algorithmVersion:VERSION};
 return {stage:null,evidence:'',certainty:'unknown',algorithmVersion:VERSION};
}
function messageOf(record){
 const p=record.payload||{};let item=p.type==='item_completed'?p.item:p;const type=String(item?.type||'').toLowerCase();
 let role=item?.role;if(['usermessage','user_message'].includes(type))role='user';else if(['agentmessage','agent_message'].includes(type))role='assistant';
 if(!['user','assistant'].includes(role)||type==='reasoning')return null;
 const text=typeof item.text==='string'?item.text:typeof item.message==='string'?item.message:typeof item.content==='string'?item.content:Array.isArray(item.content)?item.content.filter(c=>['text','input_text','output_text'].includes(c.type)).map(c=>c.text||'').join('\n'):'';
 return text?{role,text,id:item.id||null,at:record.timestamp||item.timestamp||null}:null;
}
module.exports={VERSION,inferStage,cleanText,messageOf};
