---
name: cocos-game-to-english
description: "把可运行的中文 Cocos 游戏英化，保持原玩法、关卡和画风，完成九项固定修改、美工与中文专项后交同版英文试玩及 H5 清单；用户确认后只补缺项并核包交付。也接收已完成源码和测试包，复用输入未变的有效记录。"
---

# Cocos 游戏英化

先确定唯一来源和工作副本，再按五阶段确定性命令流执行。原工程、原始 ZIP、玩家存档和已有有效证据保留。当前整包版本、补丁与指纹以包根目录 `distribution-manifest.json` 为准；安装后可从各 Skill 的 `PROVENANCE.json` 核对同版来源。历史原因只在[版本历史](../cocos-english-pack/cocos-game-to-english/版本历史.md)追溯。

## 零主观判断执行铁律

1. **任何输入第一步固定跑自动驾驶状态机**：拿到任何压缩包、源码目录、交接目录或导出目录，第一条命令必须运行 `python <skills>/cocos-game-to-english/scripts/run_skill.py next "<目标路径>"`（别名 `status` / `autopilot`）。脚本自动判定唯一路由（`source_fresh` / `source_in_progress` / `handoff` / `preview_or_package_only`）、当前阶段（`1`～`5`）、引擎与本机 Creator 路径及钱包策略；**严格执行工具末尾输出的 `[EXACT_NEXT_COMMAND]`，禁止模型自行猜测跳步**。
2. **禁止伪造证据与绕过检查；允许必要的兼容诊断**：不在工程 `docs/`、`qa/` 手写一次性测试或改账本脚本，不手工拼凑 `known-issue-review.json` 指纹；审查包用 `run_skill.py build-review-bundle` 生成。遇到已复现的命令失败、版本识别或构建路径兼容问题，先核日志、实际命令和配置，允许只读查阅相关内部实现；在用户已经授权的范围内对独立候选做最小兼容修补并复验，不因“内部脚本”字样重复索取授权。不得修改验收门槛、伪造完成状态或借诊断绕过检查。用户要求仅交 ZIP 时只改独立副本，不覆盖安装。
3. **现成测试包一键预览**：用户仅需预览现成 TikTok 测试 `.zip` 或仅含 `game.js + game.json` 的导出目录时，直接运行 `python <skills>/cocos-game-to-english/scripts/run_skill.py preview "<路径>" --quick-preview --open`（或 `run_skill.py quick-preview "<路径>" --open`）一键挂载宿主预览，不进建项流程。
4. **批量美工前先确认 Native 能开局。** 新中文工程在第 1 阶段运行 `native-preflight`。先用同一份诊断 Native 核算主包、各分包和总包的未压缩字节与可用空间，再实测首页、首屏资源和真实触摸进入游戏。同版结果沿用。美工批量生产按开工预算安排首批，实际导入后核算图集。第 3 阶段的正式候选先用 `web-mobile` 完成中文专项与美工检查，再从定稿源码导出一次同版 ByteDance。

## 开工与共用规则

- **优化侧栏。** 「优化侧栏」和「整改侧栏」都按[侧栏优化触发范围](../cocos-english-pack/remake-core/references/tiktok-home-growth.md)处理，包含桌面快捷方式和个人主页回访两项入口，首页真实点击直接调用平台。
- 新中文源码可直接运行 `python <skills>/cocos-game-to-english/scripts/run_skill.py start --input "<源码.zip或目录>" --work "<工作副本>" --route source` 一键完成安全解包与开工准备；已有工作副本也可运行 `run_skill.py start --project "<工作副本>"` 先看只读计划，核对后加 `--apply` 执行适用开工节点。工具已完成且输入未变的节点直接沿用；具体见[开工调度](../cocos-english-pack/cocos-game-to-english/references/start-project.md)。找不到 Python 或引擎时先按[环境准备](../cocos-english-pack/cocos-game-to-english/references/portable-environment.md)处理。
- 开工记录 `docs/checks/workflow.json` 的 `route`：中文源码从零制作用 `source`，已完成源码与同版测试 ZIP 用 `handoff`（运行 `run_skill.py start --input "<工程>" --route handoff` 自动核对身份并写出 `docs/handoff-baseline.json`）。后者先核身份和恢复有效记录，不重做中文原版或已完成制作。旧项目是否采用标准件先看 `tiktok_finalize.py decide`，不自动改成新项目。
- [共享执行规则](../cocos-english-pack/remake-core/references/execution-policy.md)管理增量复验、视觉交接、最终 ZIP 和计时；[浏览器规则](../cocos-english-pack/remake-core/references/browser-testing-policy.md)管理 Ego Lite 测试与用户试玩的分工。所有读图由主 Agent 直接查看，OCR 只辅助定位。
- 默认保持原玩法、原关卡、原声音素材与原有数值，不补关、不主动加经济或皮肤系统。广告推荐载体是明确的默认例外，按 [ad-boost 英化模式](../cocos-english-pack/ad-boost/references/localize-mode.md)执行。用户明确要求新增玩法时另立范围，只验证实际新增部分。

## 九项固定修改

逐项判断适用性，不适用须有具体原因。实施细节见[固定修改与范围](../cocos-english-pack/cocos-game-to-english/references/scope-and-fixed-work.md)、[固定入口](../cocos-english-pack/cocos-game-to-english/references/fixed-entries.md)。

| 项 | 工作与结果 |
|---|---|
| 1 | 中文字符串、Label、图片字改自然英文；首轮照原画风重做按钮和图片字。句子用英文字体；LEVEL、SCORE、货币等固定词、动态数字与符号按同套画风整组制作。不留游戏名、版本号或 Credits。 |
| 2 | 首页加个人主页回访和添加桌面，原按钮不挪。对应按钮直接调用平台入口；对应冷启动核资格、存档成功后自动发奖，不重复发奖，普通切回前台不提示。奖励与无钱包替代按货币规则。 |
| 3 | SFX、BGM 分开调音量，立即生效，重启后保留。 |
| 4 | 删除分享、更多游戏、联网排行榜；核心分享奖励改激励视频，局内本地名次按固定入口的例外保留。 |
| 5 | 修复真实的点击、触摸和操作缺陷，保持玩法。 |
| 6 | 结算有 Retry、最显眼的 Watch Ad x2，以及它下方一行可点的 Claim；奖励、取消和防重复按广告规则。 |
| 7 | 接入看广告复活，覆盖实际失败状态；没有失败状态时按固定入口的对应方案，不自行变更玩法。 |
| 8 | ad-boost 按诊断推荐默认加入适用载体，不出选择题；无空位或缺确定数值时换下一适用推荐。先完成本轮计划的美工与接入，再发英文试玩。 |
| 9 | 每个模式关内有暂停/设置入口，暂停窗含 Continue、Restart、Home；开窗时计时、物理和生成暂停。复用平台页面与原版暂停函数。 |

## 五阶段

中途问检查进度走 `run_skill.py status <工程>`，逐项给标题、原结果与待处理项，再沿当前执行继续。首轮总审只建立一次实际覆盖，失败后接续已有记录，按真实依赖补对应项。每次给正式试玩时同时写明首轮美工的结果或未覆盖范围，链接生成速度不作为通过依据。

| 阶段 | 现在做什么 | 细节 |
|---|---|---|
| 1 盘点 | 跑 `run_skill.py next` 锁定路由，核来源、解包和引擎。新项目批量美工前在内部 Native 核实首页、点击开始和实际进关。列中文素材、实际页面、平台/存档/声音与奖励待办。 | [盘点与原版试玩](../cocos-english-pack/cocos-game-to-english/references/workflow-stage-1.md) |
| 2 修改 | 完成九项固定修改。先定英文内框、字符集、显示槽和共享用途，首件接真实页面确认后再批量生成；改完跑 `run_skill.py stage2` 单写者静态排雷与接图闭环。 | [制作与接入](../cocos-english-pack/cocos-game-to-english/references/workflow-stage-2.md) |
| 3 英文试玩 | 先构建 `web-mobile`，合并完成本轮美工并通过中文专项、完整美工总审与真实页面复核，再单次构建同版 Native；核实启动、输入和候选身份后交第一个正式同版试玩＋H5 清单。 | [候选与试玩](../cocos-english-pack/cocos-game-to-english/references/workflow-stage-3.md) |
| 4 反馈 | 同批反馈一次改完，按单端 Web 复验后再补同版 Native；只补变化影响的页面与检查。新链接绑定新候选；同事交接或已交付局部返工按增量基线处理。 | [反馈与返工](../cocos-english-pack/cocos-game-to-english/references/workflow-stage-4.md) |
| 5 核包交付 | 用户确认后只读核功能、平台、中文与包体覆盖，跑 `prepack` 与 `build-review-bundle`，只补这些范围的缺项并复用有效记录；不执行美工或静态视觉布局检查。最终写包与重新读回 ZIP 查体积和分包，同条回复交 ZIP、可用试玩与本版 H5。 | [补缺与交付](../cocos-english-pack/cocos-game-to-english/references/workflow-stage-5.md) |

**“最后全量测试”只指第 5 阶段的完整功能、平台与包体验证，不回跑前置美工。** 第一个正式试玩前完成本轮计划内美工与合并检查；已交正式试玩或有效交接后，旧美工记录缺失或后来误跑的美工失败不能把最终任务倒送回第 3 阶段。保留这些历史记录，不改写为通过。用户明确提出的新视觉修改，按受影响页面在更新试玩前完成；真实按钮点不动、奖励不生效、资源缺失等仍按功能故障修复，不借此扩大为原界面审美返工。

试玩、广告接入、反馈 `stage2` 和预检共用[同一阶段规则](../cocos-english-pack/remake-core/references/check-stages.md)。原画风适用标签不代表用户新增了视觉返工范围；过期的历史说明不再生成当前执行步骤。

## 按需读取

- 第一轮美工：[美工入口](../cocos-english-pack/remake-art/SKILL.md)、[Codex 多进程并发美工流水线](../cocos-english-pack/remake-art/references/codex-concurrent-art-pipeline.md)（统一用 `codex exec` 多子进程并发 + 母版合成 + `raw_image_gate.py` 秒检）、[英文界面重建](../cocos-english-pack/cocos-game-to-english/references/english-ui-rebuild.md)、[分数与奖励行](../cocos-english-pack/cocos-game-to-english/references/score-reward-production.md)。采集先按[少返工的制作与采集](../cocos-english-pack/remake-art/references/art-iteration-workflow.md)合并路线并判定旧图能否沿用；首件不代替其他真实状态。
- 广告：[固定广告接入](../cocos-english-pack/cocos-game-to-english/references/english-ad-integration.md)、[ad-boost 英化模式](../cocos-english-pack/ad-boost/references/localize-mode.md)，以及实际选中板块 README。新 TK 包按[广告展示开关](../cocos-english-pack/remake-ads/references/ad-display-switch.md)接线，默认开启，关闭/恢复保留已赚取权益与免费路径；使用同包配置工具核实真实远端源和全部现存广告路径，没有真实配置源不报告后台控制已完成。
- SDK 回退：[固定顺序](../cocos-english-pack/cocos-game-check/references/tiktok-fixed-adaptation.md#tiktok-sdk-fallback)在开工、适配及实际 Native 交付时必检，适用于全部新旧游戏。
- 平台：按 [TikTok 固定适配](../cocos-english-pack/cocos-game-check/references/tiktok-fixed-adaptation.md)读取当前阶段涉及的小节，标准件由脚本安装；检查报到哪项再读对应细节，不在开工重读全部手册。
- 用户试玩交接：[真实鼠标检查](../cocos-english-pack/remake-core/references/real-mouse-preview.md)。中文原版、英文试玩、重开和最终交接都保留真实鼠标开局及代表操作门禁；由试玩入口执行本次观察，不另外手动重复跑一遍鼠标门禁。
- 反馈与交付：[返工交付](../cocos-english-pack/remake-core/references/returned-art-delivery.md)、[人工画面清单](../cocos-english-pack/remake-core/references/manual-visual-review.md)、[同页 H5](../cocos-english-pack/cocos-game-to-english/references/playtest-h5.md)。
- 计时与协作：[阶段与节点计时](../cocos-english-pack/cocos-game-to-english/references/phase-timing.md)、[并行分工](../cocos-english-pack/cocos-game-to-english/references/parallel-production.md)、[源工程排雷与单通道极速流水线](../cocos-english-pack/cocos-game-to-english/references/raw-game-conflict-shield.md)。美工工厂与广告生图共用同一整机锁，默认和上限为 15；主线程统一构建和交接，任务少时不用子 Agent。
- 用户明确要求重设计时才读[美工首轮与重设计](../cocos-english-pack/cocos-game-to-english/references/art-first-round.md)。未用板块、历史事故和维护测试不作为每个游戏的必读材料。
