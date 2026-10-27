const {test}=require('node:test');const assert=require('node:assert/strict');const {isMaintenanceTitle,isGameThread}=require('../src/codex.cjs');
const id='11111111-1111-4111-8111-111111111111';const cwd='/work/游戏出海项目制作';
test('Numbered and emoji-prefixed Skill process maintenance does not become a game merely because cwd is a game workspace',()=>{
 for(const title of ['3️⃣优化 Skill 审查流程','1️⃣成品检测 Skill','③ Skill 更新与融合','[2] 优化SKILL审查流程','（4）检测成品Skill','🛠️ 游戏 Skill 安装','cocos-game-to-english Skill 更新']){assert.equal(isMaintenanceTitle(title),true,title);assert.equal(isGameThread({id,name:title,cwd},[cwd]),false,title);}
});
test('Specific game identities retain Skill notes and game-scoped Skill update requests',()=>{
 for(const title of ['香吉士-两人行双人跳（待把问题沉淀进skill）','香吉士-两人行双人跳（Skill更新）','松果邮局 Skill 更新后复验','优化 Maya Temple Trek 的 Skill 检查问题','Maya’s Temple Trek','韩吴越-Ingrids（自制）']){assert.equal(isMaintenanceTitle(title),false,title);assert.equal(isGameThread({id,name:title,cwd},[cwd]),true,title);}
});
test('Existing tool maintenance stays excluded without treating every occurrence of Skill as maintenance',()=>{
 assert.equal(isMaintenanceTitle('游戏工作台软件开发'),true);assert.equal(isMaintenanceTitle('审查启动包工坊流程'),true);assert.equal(isMaintenanceTitle('松果邮局（把当前问题补充到Skill中）'),false);assert.equal(isMaintenanceTitle(''),false);
});

test('Scheduled Skill maintenance is excluded while scheduled game identities retain Skill notes',()=>{
 for(const title of ['每小时游戏Skill更新审查','每小时游戏 Skill 更新审查','每天优化 Skill 审查流程','定时成品检测 Skill','③ 每天：更新 Skill','每2小时 游戏Skill更新审查']){assert.equal(isMaintenanceTitle(title),true,title);assert.equal(isGameThread({id,name:title,cwd},[cwd]),false,title);}
 for(const title of ['每天松果邮局 Skill 更新后复验','每小时香吉士-两人行双人跳（待把问题沉淀进skill）'])assert.equal(isMaintenanceTitle(title),false,title);
});
