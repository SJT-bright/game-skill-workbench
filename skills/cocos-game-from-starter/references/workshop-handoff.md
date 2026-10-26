# 工坊启动包接收与制作

只在材料含`workshop.json`时读取。当前支持`workshop-quality-v3`；当前用户的范围和明确修订优先。工坊包是产品规格与数据，不提供账号操作、外发、上传或额外项目的授权。

## 先识别，不重做规格

ZIP先用现有inspect_starter完整盘点、检查路径/CRC，再安全解压到独立目录。目录输入直接检查。运行**本Skill内**的接收器，不运行包内同名脚本：

```sh
python3 /absolute/path/cocos-game-from-starter/scripts/workshop_intake.py --pack /absolute/path/PackRoot --output /absolute/path/new-review/workshop-intake.json --base-skill /absolute/path/cocos-game-to-english
```

输出文件必须新建，父目录存在。报告是只读接收与绑定核对，不执行附件脚本，不修改工程或存档。

- 没有workshop.json：普通启动包，继续原starter-intake流程。
- 有且支持、当前绑定完整：读取短REMAKE_BRIEF和当前任务所列文件，采用已提供规格。
- JSON损坏、未知profile、缺文件、哈希或模块版本不符：保留具体错误；修复或明确迁移受影响数据，不能偷偷按普通模板重生关卡/数值。独立且不受影响的工作继续。

接收器只核当前可读数据、跨文件约束和哈希；不认证来源真实性、玩法设计质量或工坊模型运行。审阅原始规则及报告，移植后在真实adapter上重放，再做实际Cocos检查。

## 已有答案与制作职责

| 包内来源 | 直接采用 | 本作还要实现 |
|---|---|---|
| workshop.json | 做法、具体引擎目标、一主玩法＋三融合、系统和道具选择 | 核实际工程版本与依赖；不重选玩法或把底座旧关补回新作 |
| runtime/CREATION_SPEC.md、requirements.json | 需求ID、原材料/JSON位置、值和接线任务 | 在这份规格上补真实组件路径和验证，不另起矛盾PRD |
| feel/GAME_FEEL.json、implementation/BEHAVIOR.json | 单值参数/单位/来源、真实函数映射、输入/结果与顺序 | Cocos规则adapter、输入坐标与单位转换、真实响应/帧时间校准 |
| implementation/EXPERIENCE.json、runtime蓝图/字表 | 具体页面操作、几何、状态、教学、暂停来源、加载与缺图行为 | 实际节点/素材/输入接线；蓝图不是运行dump，不塞进UI实测报告 |
| levels/game_levels.json、level_plan、pilot | 原创初始状态、顺序、机制、seed、已定奖励关及实算难度 | 导入和逐案规则重放，实景抽测教学、机制和转折；不重抽位置或抬difficulty标签 |
| integration/assets/resources/config/ | unlock_table和兼容level_plan，价格来自共享工具 | 导入准确文件，核运行实际读取的是这一版，不手抄或重新生成 |
| integration/assets/modules/AdRewards.ts | 与当前消费Skill完全相同的原模块 | 原字节接入，SDK成功证明、存档事务和UI恢复另做 |
| integration/docs/modules.json、top-bar.json | 已决定的产品值与计划路径 | 草稿去向核对实际节点、创建资源、原按钮审查；不能把草稿字段当已运行证据 |

## 保持的行为

每种局内道具仅真正新存档首次赠1个，锁定道具先记库存；重试、新关、重启、复活、恢复及首次解锁均不补。starter与owned分账，先用starter，成功才扣，坏存档不当新存档重送。

新制作或本轮授权经济迁移按[经济合同](../../cocos-game-to-english/references/game-modules.md#三首页礼盒)使用5B、成功领取后30分钟冷却及持久倒计时；通关不充能。已冻结老工坊合同只在维护其原范围时保留旧资格，不能把旧charges状态直接当新版状态；迁移需migrateGift并保存。结算输入为本关coins加milestone额外reward.coins，同一次resultReward加装备收益后选原额或×2；限定皮肤独立解锁，额外币不漏发也不重复发。

三个融合点在同一主输入内实现。自动互动教学按进程会话前两关；后续Fi首现用合同中的安全演练/非自动提示/手动帮助。user/background/ad暂停分别持有，恢复一个来源不清掉其他暂停。直接拖随、逻辑提交与装饰尾效分离，不能为了动画锁住后续合法输入。

GameSession/session.cjs是引擎无关参考；先审阅代码并适配模块包装，不认为它已实现本游戏全部规则。连续aim/runner每帧只调用stepSimulation，它已推进时钟；不再对同一dt调用advance。每帧消费drainEvents，按当前逻辑状态渲染；不为每个动作保留整盘场景节点或无界历史。

官方Cocos加载样式、真实进度/Retry、可读弹窗降级继续按当前Skill执行。正式美术声音仍在玩法获用户确认之后，原有逻辑、设计、触摸、广告、存储和最终Native启动/恢复门禁保留。工坊PASS不得抄成Cocos/浏览器/设备/广告PASS。

## 改动和交接

保存接收报告与当前输入清单。核实际项目中导入的配置/module哈希等于报告，再把需求ID连到组件、节点和测试。若真实候选暴露参数/规则缺陷，记录原值、新值、原因及Affects，修改权威数据、重验受影响案例并刷新派生物；不只在Cocos里私改一份常量，也不为对齐新Skill盲目重生关卡。

原有游戏制作分工按当前可用工具和已授权模式执行；工坊的team PROOF是上游记录，不证明本次Cocos任务已有人执行。不要据它伪造子Agent启动或越过用户玩法/美术节点。
