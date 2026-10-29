# 每款游戏制作时间、用量与结案统计

用户2026-10-26明确要求。重塑、英化、美工、维护、成品接手、检查与打包共用；这是生产记录，不增加游戏功能或扩大CI。执行工具为 `scripts/production_accounting.py`，记录存在本游戏 `docs/production/`，不依赖模型记忆、不保存整段聊天或凭据、不混入Native/上传ZIP。没有常驻后台进程；每次执行阶段边界时主动落盘。新聊天实际读取本规则后才生效，不能宣称旧窗口自动同步。

## 必须主动执行的时机

1. **开工先记账**：原件分流/确定项目后，任何实质制作前 `init` 并绑定当前session。已有台账直接沿用；同一游戏多个生产周期保留前次结案，另开版本周期目录，不能覆盖旧账。接手历史项目缺开工/分段记录用 `--historical-start-unknown`，明确只从现在开始记录，按已有确切证据补史，不猜原始起止或将本次记录时刻冒称原项目开工。
2. **每个有意义步骤开始/结束记一次**：按下面实际阶段分工作项，`start/stop`，记录目标、结果、测试内容及证据。不要每次读文件/每条工具调用都写一份报告；同一连续步骤归一项。等待用户前结束执行段，另记wait；用户回复后结束wait再开work。后台构建与主线重叠分别记tool/work，以区间并集统计；中断、崩溃留下open任务，恢复时注明缺失，不把无人值守隔夜全部算工时。
3. **测试命令自动计时**：已有需要执行的脚本/构建可用 `run` 包裹，真实执行并写返回码，失败同样计时，不改变原测试要求或授权。真实浏览器操作用一段work+测试内容/原始证据；图像/视频/广告等非token调用另记工具时长、调用次数与真实回执/费用来源，缺API用量不伪装成token或零成本。缺实测不能改成pass。
4. **阶段提交/通过与返工**：记录“交玩法确认”和“用户玩法通过”、“交美术确认”和“用户美术通过”为独立节点，等待单列；批准时才记approved。玩法后返工、美术后返工、测试修复分别新建任务，原失败记录保留，`note --tag rework` 写原因/影响范围；用户通过不代表技术测试全部通过。
5. **用量收集**：每个大阶段边界、换聊天交接、结案前增量import显式绑定session及实际子Agent/session；发现缺失先标覆盖缺口。交接写台账路径、open步骤、对应session，接续绑定新owner。跨项目切换先stop/unbind旧项目；不能把同一长聊天的所有token都算进当前游戏。不得全盘扫描其他聊天/模型应用或收集登录数据。该工具只接受逐响应token_usage_record，去重response_id、校验owner与本项目绑定时间窗；旧累计token_count单列为不支持，不作为本项目实际用量。其他模型/图片供应商只导入其可验证用量，不按输出字数估成实际token。
6. **用户说“项目完结了/这个游戏做完了/结案/项目结束”**：这是一条统计触发指令。关闭已知工作/等待段，补最新可得用量、留缺失/未闭合事项，执行close，当前聊天主动推送结案摘要和报告链接，并加入本工作区 `production/accounting/projects.jsonl`。不用再问是否统计。此指令不自动上传、发布、对外发消息或标所有技术问题通过。外部飞书/邮件等推送仅沿用户已授权的目的地执行，默认就在当前聊天反馈。不为此新建automation。

## 阶段与粒度

按实际发生项记录；不适用的阶段不创建假工时。

| 主阶段 | 建议分项 |
|---|---|
| intake | 接收/输入身份、环境准备 |
| gameplay | 需求/玩法方案、原型实现、关卡设计、玩法自测、提交确认、用户等待、批准、返工 |
| art | 风格/参考与样板、页面/资产设计、生图/修改、UI集成、合成自检、提交确认、用户等待、批准、返工 |
| implementation | 机制实现、英化、平台/SDK、广告/奖励/存档等实际模块 |
| test | 启动/恢复、触摸/按钮、玩法/关卡、广告/奖励、存档、声音、美术合成、包体/最终产物；每项写实际检查、环境层级、版本、结果、证据 |
| repair | 问题定位、修复、旧负例、定点复验；登记缺陷和重复检查原因 |
| delivery | 构建、包规格、打包、交付、交接 |
| closeout | 最终汇总、缺口、优化分析 |

使用如 `gameplay.design`、`art.sample`、`test.ads` 的phase；task写具体步骤。每段包含开始/结束、work/tool/wait、owner、实际结果；脚本生成阶段聚合及全部步骤明细。批准事件可用极短单独段；不将所有制作塞进一个“大测试”阶段。

## 计算口径必须明确

- **总历时**＝确切开工到用户完结；历史开工未知时只能给本次记录区间，原项目总历时未知。阶段“设计到用户通过”的历时含等待，另列执行/工具/等待的区间并集。并行分项可能重叠，不能将各行相加冒充项目工时；记录区间并集也不等于纯推理时长或人类工时。未覆盖区间单列，不能悄悄当休息或工作。
- **实际token**按响应去重，input+output为total；cached属于input，reasoning属于output；另列uncached。源没有cache/reasoning字段时记未知。缺会话/供应商/本轮尚未落盘用量须给覆盖范围；零条记录输出unknown，不说零消耗。阶段按调用完成时间归属，跨边界调用可能近似，重叠阶段/无对应工作段归未分摊；不能宣称逐步骤达到账单级精确。
- **额度**是全账户共享窗口，可在开工/大阶段结束/结案读取可用的usage_limits，保留窗口ID、usedPercent、reset；仅作账户快照。跨重置、其他项目并发、缺快照时无法归因到项目，不将token换成额度百分比或把账户差值称项目独占消耗。
- **金额**有真实账单则保留原来源；只有价格表时用带日期、来源、币种的表估算：未缓存输入×输入价+缓存输入×缓存价+输出×输出价。缺模型/缓存/费率的调用不计入完整总价，明确未计价，订阅成本不套API单价。脚本report/close可接 `--pricing`，输出只是估算、actual_billed保持未知。图片/视频、软件订阅、广告实测费用另列证据，不漏进“总成本已齐全”结论。

## 最短命令

`TOOL` 指本Skill的 `scripts/production_accounting.py`；`PROJECT`为准确游戏目录，`OWNER`为当前真实session ID。

```sh
python3 "$TOOL" --project "$PROJECT" init --name "游戏名/本次制作周期"
python3 "$TOOL" --project "$PROJECT" bind --owner "$OWNER"
python3 "$TOOL" --project "$PROJECT" start --id gameplay-design-1 --phase gameplay.design --task "首轮玩法设计" --owner "$OWNER"
python3 "$TOOL" --project "$PROJECT" stop --id gameplay-design-1 --result done --evidence docs/gameplay.md
python3 "$TOOL" --project "$PROJECT" run --phase test.input --task "底部按钮取消与恢复" --owner "$OWNER" --tested "取消不提交，恢复后新触点恰执行一次" -- node scripts/test_input.cjs
python3 "$TOOL" --project "$PROJECT" import-usage --file /absolute/current-owned-rollout.jsonl --owner "$OWNER"
python3 "$TOOL" --project "$PROJECT" report
python3 "$TOOL" --project "$PROJECT" close --registry /absolute/workspace/production/accounting/projects.jsonl
```

`stop --tested`可多次传；证据须为本游戏内真实文件并保存SHA。phase可用任何明确分项，不为凑模板创建不存在流程。`note --phase repair.ads --tag rework --text "具体原因与证据位置"`用于保留返工/优化依据。`quota --file`仅接受提取后的 `{at,windows:[{id,used_percent,resets_at}]}`，禁止把完整账户响应/余额/账户ID落盘。价格表为 `{as_of,source,currency,models:{模型:{input_per_million,cached_input_per_million,output_per_million}}}`；工具不会自行查价。

读回 `docs/production/summary.json` / `summary.md` 核覆盖与open项。结案同命令可复用，不重复累计close；生成最终回答这一轮用量可能尚未落盘，先给截至快照并标明尾部缺口，下一次恢复时核实当次调用归属，来源能明确归属才补录；当前导入器不越过close时间窗，尾部不能归属就保持未知，不能伪称已含最终回答。临时测试文件用临时目录自动回收。

## 完结时主动推送的内容

总历时与覆盖边界；玩法/美工/实现/测试/修复/打包每段的时间和token；各阶段子步骤与实际测试内容/结果；缓存比例、未缓存输入、输出和可得额度快照；有依据的估算/实际成本及未知项；最多数条有证据的优化建议（重复加载、返工原因、重复测试、工具失败、等待、已可复用证据）。按耗时/用量排序不等于判定浪费，不牺牲必要验证，也不虚报节省比例。摘要直接发当前聊天，详细记录给链接，数据留本地便于跨项目比较。
