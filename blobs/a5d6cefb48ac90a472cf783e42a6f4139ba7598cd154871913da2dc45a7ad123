---
name: cocos-game-to-english
description: "把可运行的中文 Cocos 游戏英化。新中文工程开工先交中文原版手机试玩链接，不等回复继续。保持原玩法、关卡和画风，完成九项固定修改、美工与中文专项后交同版英文试玩及 H5 清单；用户确认后只补缺项并核包交付。也接收已完成源码和测试包，复用输入未变的有效记录。外包游戏完工时，响应口令“出完工交接包”，汇总同版测试 ZIP、源码、回执和两类检查记录。"
---

用户说“出完工交接包”或交付外包完工游戏时，按[完工交接包](../cocos-english-pack/remake-core/references/completion-handoff.md)执行。正式交付 CLI 在成功回执后自动汇总。需要单独补交时，直接使用原回执和本次源码，交接前核对外层清单。


# Cocos 游戏英化

**广告与经济开工时由用户定**：结算 x2、复活、ad-boost 板块、经济与皮肤在开工时问用户并跑 `run_skill.py kickoff record`，Skill 不默认新增；口径只在[英化广告与经济](../cocos-english-pack/cocos-game-to-english/references/english-ad-integration.md)。

先确定唯一来源和工作副本，再按五阶段确定性命令流执行。原工程、原始 ZIP、玩家存档和已有有效证据保留。当前整包版本、补丁与指纹以包根目录 `distribution-manifest.json` 为准；安装后可从各 Skill 的 `PROVENANCE.json` 核对同版来源。历史原因只在[版本历史](../cocos-english-pack/cocos-game-to-english/版本历史.md)追溯。

遇到当前授权范围内的故障，执行 Agent 按[自动返修](../cocos-english-pack/remake-core/references/execution-policy.md#当前任务中的自动返修)当轮修复、复验，继续原任务。失败输出中的重试命令在原因修正后执行。

## 零主观判断执行铁律

1. **任何输入第一步固定跑自动驾驶状态机**：拿到任何压缩包、源码目录、交接目录或导出目录，第一条命令必须运行 `python <skills>/cocos-game-to-english/scripts/run_skill.py next "<目标路径>"`（别名 `status` / `autopilot`）。脚本自动判定唯一路由（`source_fresh` / `source_in_progress` / `handoff` / `preview_or_package_only`）、当前阶段（`1`～`5`）、引擎与本机 Creator 路径及钱包策略；**严格执行工具末尾输出的 `[EXACT_NEXT_COMMAND]`，禁止模型自行猜测跳步**。
2. **禁止伪造证据与绕过检查；允许必要的兼容诊断**：不在工程 `docs/`、`qa/` 手写一次性测试或改账本脚本，不手工拼凑 `known-issue-review.json` 指纹；审查包用 `run_skill.py build-review-bundle` 生成。遇到已复现的命令失败、版本识别或构建路径兼容问题，先核日志、实际命令和配置，允许只读查阅相关内部实现；在用户已经授权的范围内对独立候选做最小兼容修补并复验，不因“内部脚本”字样重复索取授权。不得修改验收门槛、伪造完成状态或借诊断绕过检查。用户要求仅交 ZIP 时只改独立副本，不覆盖安装。
3. **现成测试包一键预览**：用户仅需预览现成 TikTok 测试 `.zip` 或仅含 `game.js + game.json` 的导出目录时，直接运行 `python <skills>/cocos-game-to-english/scripts/run_skill.py preview "<路径>" --quick-preview --open`（或 `run_skill.py quick-preview "<路径>" --open`）一键挂载宿主预览，不进建项流程。
4. **批量美工前先确认 Native 能开局。** 新中文工程在第 1 阶段运行 `native-preflight`。先用同一份诊断 Native 核算主包、各分包和总包的未压缩字节与可用空间，再实测首页、首屏资源和真实触摸进入游戏。同版结果沿用。美工批量生产按开工预算安排首批，实际导入后核算图集。第 3 阶段的正式候选先用 `web-mobile` 完成中文专项与美工检查，再从定稿源码导出一次同版 ByteDance。

## 开工与共用规则

首页制作先按[双入口接线](../cocos-english-pack/remake-core/references/tiktok-home-growth.md#首页设计时接好两个平台入口)接通 PROFILE 和 SHORTCUT。首个集成 Native 包实点验证任务 SDK 晚到后的两条路径。发现零请求、错调或重复，直接修工作副本、重建、复测。

- **优化侧栏。** 「优化侧栏」和「整改侧栏」都按[侧栏优化触发范围](../cocos-english-pack/remake-core/references/tiktok-home-growth.md)执行。两份引导在美工前定稿，首页分别打开引导，确认才调用 TikTok。只从匹配来源核验资格，资格通过不加奖，真实点领取并确认存档提交后才到账。侧栏返工以用户实际测包和同版可编辑源码为基线；无法绑定后台版本或 SHA-256 时明确记录，不把本地模拟称为平台验收。
- 新中文源码可直接运行 `python <skills>/cocos-game-to-english/scripts/run_skill.py start --input "<源码.zip或目录>" --work "<工作副本>" --route source` 先安全解包，按输出交中文原版试玩后接着做开工准备；已有工作副本也可运行 `run_skill.py start --project "<工作副本>"` 先看只读计划，核对后加 `--apply` 执行适用开工节点。工具已完成且输入未变的节点直接沿用；具体见[开工调度](../cocos-english-pack/cocos-game-to-english/references/start-project.md)。找不到 Python 或引擎时先按[环境准备](../cocos-english-pack/cocos-game-to-english/references/portable-environment.md)处理。
- 开工记录 `docs/checks/workflow.json` 的 `route`：中文源码从零制作用 `source`，已完成源码与同版测试 ZIP 用 `handoff`（运行 `run_skill.py start --input "<工程>" --route handoff` 自动核对身份并写出 `docs/handoff-baseline.json`）。后者先核身份和恢复有效记录，不重做中文原版或已完成制作。旧项目是否采用标准件先看 `tiktok_finalize.py decide`，不自动改成新项目。
- [共享执行规则](../cocos-english-pack/remake-core/references/execution-policy.md)管理增量复验、视觉交接、最终 ZIP 和计时；[浏览器规则](../cocos-english-pack/remake-core/references/browser-testing-policy.md)管理 Ego Lite 测试与用户试玩的分工。所有读图由主 Agent 直接查看，OCR 只辅助定位。
- 默认保持原玩法、原关卡、原声音和数值，不补关；用户明确要求新增玩法时另立范围，只验证实际新增部分。

## 九项固定修改

逐项判断适用性，不适用须有具体原因。实施细节见[固定修改与范围](../cocos-english-pack/cocos-game-to-english/references/scope-and-fixed-work.md)、[固定入口](../cocos-english-pack/cocos-game-to-english/references/fixed-entries.md)。

| 项 | 工作与结果 |
|---|---|
| 1 | 中文字符串、Label、图片字改自然英文；首轮照原画风重做按钮和图片字。句子用英文字体；LEVEL、SCORE、货币等固定词、动态数字与符号按同套画风整组制作。不留游戏名、版本号或 Credits。 |
| 2 | 首页加个人主页回访和添加桌面，原按钮不挪。各自先开引导，确认才调用平台入口；对应入口回来核资格，点击领取且保存成功才到账，不重复发奖，普通切回前台不提示。奖励与无钱包替代按货币规则。 |
| 3 | SFX、BGM 独立开关、十格与实时百分比，立即生效并持久保存；按固定入口的 AUDIO-01 核实际输出。 |
| 4 | 删除分享、更多游戏、联网排行榜；核心分享奖励改激励视频，局内本地名次按固定入口的例外保留。 |
| 5 | 修复真实的点击、触摸和操作缺陷，保持玩法。 |
| 6 | 按开工决定：加了 Watch Ad x2 时它是结算主按钮，下方一行可点的 Claim 免费结算（胜利进下一关，无尽或失败执行 Retry），没有可领奖励的失败页直接显示 Retry；不加则结算页保留原样。见[固定入口](../cocos-english-pack/cocos-game-to-english/references/fixed-entries.md)。 |
| 7 | 按开工决定接入看广告复活，覆盖实际失败状态；原有复活保留并改接平台包。 |
| 8 | 按开工决定：`none` 不加板块；点名的板块走[父子级选择](../cocos-english-pack/ad-boost/references/hierarchical-choices.md)按 choice_plan 实施。 |
| 9 | 每个模式关内有暂停/设置入口，暂停窗含 Continue、Restart、Home；开窗时计时、物理和生成暂停。复用平台页面与原版暂停函数。 |

## 五阶段

中途问检查进度走 `run_skill.py status <工程>`，逐项给标题、原结果与待处理项，再沿当前执行继续。启动或运行时复测按[原账本的逐项计划](../cocos-english-pack/remake-core/references/incremental-checks.md#浏览器与制作写包使用相同计划)，修正 `scope_required` 指出的实际依赖后再续跑。首轮总审只建立一次实际覆盖，失败后接续已有记录，按真实依赖补对应项。每次给正式试玩时同时写明首轮美工的结果或未覆盖范围，链接生成速度不作为通过依据。

| 阶段 | 现在做什么 | 细节 |
|---|---|---|
| 1 盘点 | 跑 `run_skill.py next` 锁定路由并安全接收原版。新中文工程先构建或沿用原始 Web，实际开局后发中文原版手机试玩链接（同条附上开工决定几题），发完立即继续做开工准备和内部 Native 首页与进关验证。列中文素材、实际页面、平台、存档、声音与奖励待办。 | [盘点与原版试玩](../cocos-english-pack/cocos-game-to-english/references/workflow-stage-1.md) |
| 2 修改 | 完成九项固定修改。先定英文内框、字符集、显示槽和共享用途，首件接真实页面确认后再批量生成；改完跑 `run_skill.py stage2` 单写者静态排雷与接图闭环。 | [制作与接入](../cocos-english-pack/cocos-game-to-english/references/workflow-stage-2.md) |
| 3 英文试玩 | 先构建 `web-mobile`，合并完成本轮美工并通过中文专项、完整美工总审与真实页面复核，再单次构建同版 Native；核实启动、输入和候选身份后交第一个正式同版试玩＋H5 清单。 | [候选与试玩](../cocos-english-pack/cocos-game-to-english/references/workflow-stage-3.md) |
| 4 反馈 | 同批反馈一次改完，按单端 Web 复验后再补同版 Native；只补变化影响的页面与检查。新链接绑定新候选；同事交接或已交付局部返工按增量基线处理。 | [反馈与返工](../cocos-english-pack/cocos-game-to-english/references/workflow-stage-4.md) |
| 5 核包交付 | 用户确认后只读核功能、平台、中文与包体覆盖，跑 `prepack` 与 `build-review-bundle`，只补这些范围的缺项并复用有效记录；不执行美工或静态视觉布局检查。最终写包与重新读回 ZIP 查体积和分包，同条回复交 ZIP、可用试玩与本版 H5。 | [补缺与交付](../cocos-english-pack/cocos-game-to-english/references/workflow-stage-5.md) |

**“最后全量测试”只指第 5 阶段的完整功能、平台与包体验证，不回跑前置美工。** 第一个正式试玩前完成本轮计划内美工与合并检查；已交正式试玩或有效交接后，旧美工记录缺失或后来误跑的美工失败不能把最终任务倒送回第 3 阶段。保留这些历史记录，不改写为通过。用户明确提出的新视觉修改，按受影响页面在更新试玩前完成；真实按钮点不动、奖励不生效、资源缺失等仍按功能故障修复，不借此扩大为原界面审美返工。

试玩、广告接入、反馈 `stage2` 和预检共用[同一阶段规则](../cocos-english-pack/remake-core/references/check-stages.md)。原画风适用标签不代表用户新增了视觉返工范围；过期的历史说明不再生成当前执行步骤。

## 每轮制作回收问题

按 [RSI 迭代流程](../cocos-english-pack/cocos-game-to-english/references/rsi-workflow.md) 记录本轮 Skill 和候选身份，随制作留复现证据，并按已变输入选择主风险及适用的历史盲区。先以触发机制判断项目、版本或平台分支、共享检查三个层级。通用修复进入下一版隔离候选，用不同输入和健康对照核实适用范围，再从已有责任节点生效。制作与交付沿用现有检查账本。

## 按需读取

- 第一轮美工：[美工入口](../cocos-english-pack/remake-art/SKILL.md)、[Codex 多进程并发美工流水线](../cocos-english-pack/remake-art/references/codex-concurrent-art-pipeline.md)（统一用 `codex exec` 多子进程并发 + 母版合成 + `raw_image_gate.py` 秒检）、[英文界面重建](../cocos-english-pack/cocos-game-to-english/references/english-ui-rebuild.md)、[分数与奖励行](../cocos-english-pack/cocos-game-to-english/references/score-reward-production.md)。采集先按[少返工的制作与采集](../cocos-english-pack/remake-art/references/art-iteration-workflow.md)合并路线并判定旧图能否沿用；首件不代替其他真实状态。
- 广告：[固定广告接入](../cocos-english-pack/cocos-game-to-english/references/english-ad-integration.md)、[ad-boost 英化模式](../cocos-english-pack/ad-boost/references/localize-mode.md)，以及实际选中板块 README。新 TK 包按[广告展示开关](../cocos-english-pack/remake-ads/references/ad-display-switch.md)接线，默认开启，关闭/恢复保留已赚取权益与免费路径；使用同包配置工具核实真实远端源和全部现存广告路径，没有真实配置源不报告后台控制已完成。
- SDK 回退：[固定顺序](../cocos-english-pack/cocos-game-check/references/tiktok-fixed-adaptation.md#tiktok-sdk-fallback)在开工、适配及实际 Native 交付时必检，适用于全部新旧游戏。
- 手机布局兼容：涉及胶囊、安全区、窄屏或触摸的新增界面与局部修复，按[五视口布局与触摸复验](../cocos-english-pack/remake-core/references/tiktok-mobile-layout-compatibility.md)记录同版基础、失败对照及浏览器/真机证据；不扩大已授权范围。
- 平台：按 [TikTok 固定适配](../cocos-english-pack/cocos-game-check/references/tiktok-fixed-adaptation.md)读取当前阶段涉及的小节，标准件由脚本安装；检查报到哪项再读对应细节，不在开工重读全部手册。
- 用户试玩交接：[真实鼠标检查](../cocos-english-pack/remake-core/references/real-mouse-preview.md)。中文原版、英文试玩、重开和最终交接都保留真实鼠标开局及代表操作门禁；由试玩入口执行本次观察，不另外手动重复跑一遍鼠标门禁。
- 反馈与交付：[返工交付](../cocos-english-pack/remake-core/references/returned-art-delivery.md)、[人工画面清单](../cocos-english-pack/remake-core/references/manual-visual-review.md)、[同页 H5](../cocos-english-pack/cocos-game-to-english/references/playtest-h5.md)。
- 计时与协作：[阶段与节点计时](../cocos-english-pack/cocos-game-to-english/references/phase-timing.md)、[并行分工](../cocos-english-pack/cocos-game-to-english/references/parallel-production.md)、[源工程排雷与单通道极速流水线](../cocos-english-pack/cocos-game-to-english/references/raw-game-conflict-shield.md)。美工工厂与广告生图共用同一整机锁，默认和上限为 15；主线程统一构建和交接，任务少时不用子 Agent。
- 用户明确要求重设计时才读[美工首轮与重设计](../cocos-english-pack/cocos-game-to-english/references/art-first-round.md)。未用板块、历史事故和维护测试不作为每个游戏的必读材料。
