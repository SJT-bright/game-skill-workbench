---
name: cocos-game-from-starter
description: "开始前移除分享与全部排行榜（好友排行、Ranking、Leaderboard），不得保留。重塑：用户拖入启动包（START_HERE.md、GAME_DESIGN.md、levels/、UI_PAGES.md、ECONOMY.json、COPY_EN.md等设计文件，一般是英文写的；有时同时附原游戏源码），或只给主题/策划，说重塑、用启动包做游戏、做新游戏时使用。按启动包重新做一个国际TikTok Cocos游戏（按内置板块加货币、结算×2、礼盒、皮肤和关卡板块；默认不做排名、签到、更多游戏、分享）：先做玩法（占位图），用户说玩法通过后才按启动包美术提示做全部美术和声音，再试玩验收、浏览器测试，用户说打包才出包。只要有启动包就走这里，不管有没有源码；只有中文源码、没有启动包时改用cocos-game-to-english（英化）。"
---

**每次制作的时间、token与结案统计（用户2026-10-26）**：按[制作记录与完结汇总](../cocos-game-to-english/references/production-accounting.md)，确定项目后即启用本游戏追加台账；各玩法/美工/实现/实际测试/返工/交付步骤主动记录起止、工作/工具/等待、结果与证据，阶段边界增量收集绑定会话用量。用户说“项目完结了”时主动在当前聊天推送分阶段及总历时、可核实token/额度/成本、测试明细和优化分析，并本地归档；缺数据标未知，缓存/推理不重复相加，共用账户额度不冒称项目独占。记录不扩大制作/CI范围，不建常驻进程或额外定时任务。


**回访与快捷方式共用模板（2026-10-26）**：两项任务沿用用户确认的[共用展示与任务流程](../cocos-game-to-english/references/tiktok-home-growth.md#共用展示与任务流程模板用户确认2026-10-26)：图标入口、插图奖励弹窗、Open跳转、返回查询、单次持久领奖及Claimed；按游戏配置奖励与美术，展示和入账共用同值。


**不展示 Credits 界面（用户 2026-10-26）**：玩家端不新增或保留 Credits、制作人员、鸣谢页面、弹窗、标签及入口，也不以 About 页面承载相同制作说明。已有入口连同对应路由/弹窗移除，不能仅改名；不向玩家展示 AI/GPT 分工、英化/改编过程或原素材保留说明。游戏名和版本号可在设置页底部小字展示；“皮肤仅改变外观”放皮肤页。素材来源、作者、许可证和制作记录保留在项目交接文档；优先选择无需游戏内署名的素材，现有许可证确有强制展示要求时先说明并采用符合许可且不新增 Credits 界面的方式，必要时更换素材，不能直接删掉许可义务。制作/修改检查受影响设置入口与弹窗；出包只核本次相关入口和实际产物，不重跑无关CI。


**用户可操作的广告模拟（用户2026-10-26）**：可玩候选有广告入口时，交用户试玩前按[广告模拟与实际奖励核对](../cocos-game-to-english/references/manual-ad-simulation.md)提供本地手动模拟看完、取消、失败和暂无广告；点击原广告按钮，经过原适配器和原奖励/保存流程，显示实际状态差异，先核当前候选基本路径。共用`serve_preview.py --ad-simulator`仅注入本地响应，不进入Native/ZIP，不直接改余额；原逐入口自动矩阵保留。仅出现失败提示不算已交付可操作模拟。


<!-- WORKSHOP_RECEIVER:BEGIN -->
**工坊启动包接收（2026-10-26）**：输入含`workshop.json`时，先按[工坊交接](references/workshop-handoff.md)运行本Skill的只读接收器。确认v3及当前文件绑定后，直接采用包内CREATION_SPEC、EXPERIENCE、手感/行为合同、关卡和integration配置；下面普通模板的生成/补设计步骤改为导入及Cocos接线。缺件、版本或哈希不符明确处理，不降级成普通包重造数据。无workshop.json保留原流程。模型/配置通过不代替实际玩法、逻辑、触摸、美术或Native门禁。
<!-- WORKSHOP_RECEIVER:END -->

**已报告问题登记与定点复验（2026-10-26.package-gate-v2）**：收到本作确定故障反馈时，先按[固定问题历史与定点复验](../cocos-tiktok-package-check/references/resource-and-reported-issues.md)保存原始描述并登记。只有源码时先保留原报告，Native及对应运行器可用后、首次出包前必须导入未闭合项；不能初始化空历史绕过既有反馈。修复只跑该问题的case和关联依赖，出包入口自动拒绝未复验/失败/旧指纹问题，不重开无关全量CI。

**每次新测试包必查启动与卡加载（用户 2026-10-26）**：按[最终Native启动与恢复门禁](../cocos-game-to-english/references/final-package-startup-gate.md)执行。成品直接出包也必须核当前Native的真实入口/adapter/引擎、HOME可操作→真实触摸→玩法变化及失败→Retry新请求→恢复；缺同版证据、旧绑定或失败拒包。仅限启动链，不重跑无关CI或已批准美工；本地通过不得写成手机扫码通过。


**统一 Cocos 加载界面（用户 2026-10-26）**：按[官方默认加载与重试样式](../cocos-game-to-english/references/cocos-loading-screen.md)执行。所有开发者可控加载页使用匹配 Creator 版本的 Cocos 官方加载画面与进度动画，不出现游戏标题、角色、场景或游戏专属加载文案；保留真实进度、失败重试及首页就绪判据。构建模板和 post-build 等后处理不得重新注入游戏主题加载页；交试玩前在全部后处理执行完的实际产物中观察加载动画，不能仅凭配置或静态 Logo 判通过。



**重复关卡与难度（2026-10-26）**：设计/扩关或收到重复反馈时，按[重复关卡与真实难度](../cocos-game-to-english/references/top-bar-and-level-map.md#重复关卡与真实难度2026-10-26)查运行表的重复、同构及解法后缀拆关，以实际解题参数递进，旧表须先命中反例；不因普通首次试玩扩大验收。


**弹窗底图失败仍须可用（2026-10-25）**：试玩前按[弹窗完整显示与缺图降级](../cocos-game-to-english/references/art-before-trial.md#弹窗完整显示与缺图降级2026-10-25)核受影响共享弹窗正常与缺图状态，底板/遮罩/正文/关闭/操作必须同时可见可用；包体检查不替代实际合成画面。


**列表预览灰格与首尾压框（2026-10-25）**：皮肤/道具/主题选择页美术检查执行[选项预览与面板内区短检](../cocos-game-art-redo/references/collection-preview-review.md)：逐项核实际内容与装备对应，按实绘内框查首尾行；历史保留不豁免缺陷，同一方法检出旧版并通过修复版/正常对照后再结案。


**移动引导与无响应按钮防复发（2026-10-25）**：涉及拖动/摇杆引导、相机卡住、暂停恢复或广告按钮无响应时，读取[引导输入、暂停恢复与反馈](../cocos-game-to-english/references/tutorial-input-and-pause-recovery.md)。实际拖动须产生玩家与镜头变化；开局过渡中暂停也须恢复到可玩；暂停层去重，广告不可用明确反馈且不发奖。局部修复限对应链路，完整制作在交试玩前验证这些实际存在的机制。


**任何用户本地预览/试玩链接的前置条件（用户2026-10-25）**：生成、恢复或随包附带链接之前，先按[固定手机尺寸试玩](../cocos-game-to-english/references/user-phone-preview.md)实施并验证。共享 `serve_preview.py` 默认内部390×844手机框，桌面不放大全屏，小窗口只等比缩小；原始导出/Native/ZIP和用户存档不改。只交试玩时仅核外壳尺寸、真实首页及一次开始，不启动全量CI。不得先发裸全屏地址再让用户自行缩窗口。


**持续执行与进度汇报（2026-10-25纠错）**：已授权工作按[持续修复与交付](../cocos-game-to-english/references/check-fix-package-loop.md)推进，进度用commentary，不以固定时间/修复数或“整体未完成”要求用户发继续。只在授权终点、必需人工节点、用户/工具停止或确需外部输入且独立工作已尽时结束；新聊天按既有接续授权。


**场景资源路径故障复盘（2026-10-25）**：发生`scene-load-failed`、分包迁移或上传后卡启动时，先读[Native场景路径检测与修复](../cocos-game-to-english/references/native-startup-path-casebook.md)。准确旧包、同一外部故障边界、修复后完整操作链对照；主包与普通分包配置都扫描。错误UI或场景active不等于进入游戏，不得复制历史通过或以维护候选绕过已失败的正式检查。


**加载页假通过防复发（2026-10-25）**：启动故障/加载维护或所属最终功能轮，按[启动业务完成与工具反例校准](../cocos-game-to-english/references/loading-scene-false-positive.md)核HOME可操作→真实输入→玩法变化。scene active、满进度、桩或ZIP闭包不替代实际业务；先查首错，不隐藏Loading。普通换图不扩CI，已有故障定点闭合。 正式启动检查缺当前真实业务观测仍拒绝。


**玩法通过后自动换聊天（用户 2026-10-25）**：按[自动新建聊天接续](../cocos-game-to-english/references/auto-art-stage-chat.md)执行。用户说“玩法通过”后，保存交接，Agent用受支持工具在准确同游戏目录创建新聊天并发送“继续这个游戏”及工程/交接信息，确认接任；不再让用户手动新开。此条覆盖下面玩法节点的旧手动换新要求，其他阶段范围不自动扩大。


**本地验证的已知前提与汇报（用户 2026-10-25）**：内部保留实际证据层级，用户已知本地与上传验证的区别；日常不重复该前提或免责声明。仅在询问、具体混淆或需要处理的失败时说明，不把本地结果称为真机/真实广告通过。


**美术检查前移（用户 2026-10-25）**：按[美术验收前移与试玩后锁定](../cocos-game-to-english/references/art-before-trial.md)执行：所有美术测试在交用户试玩前完成；用户确认后到测试包交付之间不再美工测试、不重新评判已批准画面。最终画面字段只查运行故障，不夹带美术标准。

**所有测试包的最终文件检测（2026-10-24）**：凡已授权产出TikTok测试包/上传包/扫码包/平台ZIP，最终交付前使用 [TikTok测试包最终检测](../cocos-tiktok-package-check/SKILL.md)。共享verifier现强制检查game.js可达依赖、引擎、分包入口、Cocos场景/数据pack；成品直接出包也执行该文件级检查，沿用本轮授权范围，不因此重跑完整游戏CI。检查失败继续定点修复和出包，完整证据留内部，默认只交最终ZIP。

**动态主页美工（用户 2026-10-25）**：新设计或本轮重做主页时，按[主角、标题待机动画与按钮分区](../cocos-game-to-english/references/mobile-button-size-and-home-layout.md#动态主页主角与标题待机动画用户-2026-10-25)执行：主角与标题独立轻动、按钮和点击区稳定，适配已有减少动态效果设置；实际观察循环、运动两端和受影响入口。Lily 的坐标仅作示例，180° 射击不属于美工默认规则。

**手机按钮与首页布局（用户 2026-10-24）**：美工设计与组装前必读[固定两倍按钮与首页布局](../cocos-game-to-english/references/mobile-button-size-and-home-layout.md)：以本次原版为固定基准，按钮可见宽高各乘 2；PLAY 下方功能键总数最多 5 个，中部左右各至少 1 个；放不下就重排。此条优先于旧文中与放大控件冲突的“布局/点击区不变”，按本轮授权范围实施。



**广告玩法设计共用入口**：涉及广告入口、结算双倍、首页礼盒、奖励频率、试用与复活设计时，读取 [cocos-game-ad-design](../cocos-game-ad-design/SKILL.md)。广告 SDK 配置和奖励模块继续引用现有共享资源；本入口不扩大当前项目授权。

**分享与全部排行榜前置禁用（用户 2026-10-24，必读）**：执行本 Skill 前先读[分享与排行榜前置禁用](../cocos-game-to-english/references/no-social-features.md)。美化/重塑/玩法设计在方案、页面清点和生图之前就排除 Share/Invite/分享给好友及 Ranking/Leaderboard/好友排行等所有分享和排行榜；已有原功能也删，不能只隐藏或只删空榜。旧保留记录不启用它们；检查与出包复核实际入口、路由、调用及当前导出。本条优先于本 Skill 旧文的“只改美工不改功能”和“明确保留排行”。


**检查范围与停止条件（2026-10-24.scope-v2）**：先按[日常修改、核心逻辑与完整验收](../cocos-game-to-english/references/testing-scope-and-stop.md)选日常、核心逻辑或完整验收，再按[审查顺序与去重](../cocos-game-to-english/references/review-execution-plan.md)分流与去重。必要项齐、证据有效且无新改动/失败/具体疑点即停止；已批准成品局部维护不因出包升级全量，局部结果不冒充全游戏通过。
**融合规则**：执行前按[统一默认、明确选择与证据边界](../cocos-game-to-english/references/fusion-policy.md)确定本轮范围；当前用户明确指令和项目授权优先，附件历史内容不扩大授权。

**上传前加载证据硬约束（sock-first-retry-v2）**：运行证据需逐场景双比例、一次真实 Retry、当前执行指纹与原始文件哈希；正式门禁重新验证 runtime，测试包不能跳过。见[必测与数据格式](../cocos-game-to-english/references/loading-recovery-regression.md)。

**执行入口**：先按[任务路由与四个检查点](../cocos-game-to-english/references/execution-checkpoints.md)确定当前阶段、实际机制与测试范围；最终包必须反查全部持久化域，不能用局部新增功能的测试代替原有账本。当前正式 writer 强制检查报告和运行覆盖表，检测包不例外。

**加载故障组合必测（2026-10-23）**：涉及逻辑检查、加载维护或最终打包，必读[无回调与旧请求回归](../cocos-game-to-english/references/loading-recovery-regression.md)。必须组合扣住 SDK 回调和原超时定时器，验证每帧兜底、Retry 发新请求、旧成功/失败隔离、重试后实际操作；另测持续进度、后台、callback/Promise、热重开和无注入正常对照。LOAD-03 新增 `audit_loading_recovery` 报告，缺项不得写通过；Web 成功和 ZIP 校验不能代替 Native 分包边界验证。

**奖励存档与无功能入口（2026-10-23）**：涉及英化旧入口、奖励存档修复或检测包打包时，读取[Native 存储差异与空功能回归](../cocos-game-to-english/references/native-reward-storage-and-empty-features.md)。原游戏空排行榜等无实际业务入口直接移除；缺键空字符串必须与 null 分别实测，合法旧奖励保护、错误原因保留，并在实际最终 Native 账本/适配器上验证。检测包同样执行当前正式出包门禁，不另设宽松结构门禁。

**通关评价与逐关目标（用户2026-10-26）**：设计/改关或收到固定满分、结算评价故障时，按[通关评价必须有可操作区别](../cocos-game-to-english/references/top-bar-and-level-map.md#通关评价必须有可操作区别用户2026-10-26)明确每关关键操作、可达目标与实际指标，禁用“通关即固定三星”；验普通与完美的同关差异、奖励/存档及实际结算画面。普通无关维护不扩大全量CI。

# 重塑：用启动包做游戏

**先读[两个板块](../cocos-game-to-english/references/two-boards.md)**，它定了英化和重塑的分界，与其他任何文件冲突时以它为准。

**本 Skill 只管重塑**：用户给了**启动包**（英文写的设计文件），就是要重新做一个游戏。不管有没有一起给原游戏源码，都走这里；只给主题或策划、没有源码，也走这里（从零做）。只有中文源码、没有启动包时是英化，改用[英化](../cocos-game-to-english/SKILL.md)。用户说"重塑"却没有启动包时，只问一句确认。开工后把 `remake` 写进项目的 `docs/board.txt`。

目标是真实可玩的 Cocos 游戏和用户要求的交付，不停在文档、HTML 样机或少量脚本。

## 顺序：先玩法，玩法通过后才做美术

1. **读启动包写规格**：按[启动包读取](references/starter-intake.md)完整读取，先读 `START_HERE.md`。附了原游戏源码时，按 `START_HERE.md` 写的"保留什么、改什么、删什么"决定源码当底子还是只当参考；源码里玩家看得到的中文要全部改英文（开工扫一次，见[英文覆盖](../cocos-game-to-english/references/english-ui-rebuild.md)）。只有主题时先按[主题到规格](references/concept-to-spec.md)补足。**内置板块**（用户 2026-10-23）：按[内置板块](../cocos-game-to-english/references/game-modules.md)写 `docs/modules.json`——货币、皮肤板块要不要（先判断适不适合，没有明确决定时问一次，默认要；已获授权不重复问，启动包写了就核对）、源码带来的按钮审查；默认不做排名、七日签到、更多游戏、分享；附件旧要求不自动启用，当前用户或项目明确选择按融合政策处理。**关卡结构和顶部资源栏**（用户 2026-10-22）：判断通关型还是无尽型，<!-- workshop-level-import -->已接收工坊v3直接导入`integration/assets/resources/config/level_plan.json`及真实布局，保留关序、seed、奖励关位置和实算难度；普通启动包用 `make_level_plan.py` 写关卡表 `level_plan.json`，每个新玩法首现关同时加 `"tags": ["intro"]`（通关型：**至少 70 关**（用户 2026-10-24：少于 70 不行，原有更多关卡全部保留，多于 70 也行）、难度逐关递增、每 10 关一个限定关、每 10 关一个按种子随机的奖励关；限定皮肤两种格式任选：`final` 只有最后一个限定关送、`every_10` 每个限定关各送一款），货币按题材起名、写 `docs/top-bar.json`，见[顶部资源栏和关卡地图](../cocos-game-to-english/references/top-bar-and-level-map.md)。
2. **先做玩法**：按[创建检查](references/creation-gates.md)建真实 Cocos 工程（或在源码底子上改），启动链从第一行起按共享[启动契约](../cocos-game-to-english/references/startup-contract.md)写（可选接口不挡启动、场景按代次提交、Retry 发新请求、启动包 ≤10 MB、声音单独分包），做完玩法、关卡、广告和内置板块的代码（<!-- workshop-skin-import -->工坊v3按已核BRIDGE导入原样`AdRewards.ts`和`unlock_table.json`；普通启动包才用`make_skin_table.py`生成皮肤表，结算×2、首页礼盒）、`COPY_EN.md` 的英文文案。界面用**按最终尺寸摆好的占位图**，货币在最上方、设置在上角、功能图标按中部两侧与下方最多五个的分区布局，不显示 PROTOTYPE/PLACEHOLDER 等开发用文字。**这一步不生成任何正式美术。**首个可玩骨架形成后先过[启动到首关](../cocos-game-to-english/references/cocos-runtime.md#先验证-native-启动到首关)（Web 和 Native 都能导出，在浏览器里首页→首关＋一次加载失败恢复）；首个奖励可运行时先做[最小领取预防](../cocos-game-to-english/references/known-issue-checklist.md#最小执行法先打通再扩展)。
3. **逻辑检查（必做，用户 2026-10-23）**：第一轮玩法做完（每关能玩、能胜能负、占位界面齐了）就用 [`cocos-game-logic-check`](../cocos-game-logic-check/SKILL.md) 的 build 模式查一遍：`logic_check.py --init` → 盘点按钮去向表 → 静态扫描＋读源码 → 真实触摸走 F01–F20 和故障测试 → 查出来就修、加回归测试 → `logic_check.py --mode build` 通过（门禁 LOGIC-01）；同时执行[实际缺陷回归 R01–R09](../cocos-game-logic-check/references/learned-regressions.md)，`--init` 保留旧结果补新项，未测/失效证据不放行。没通过不发玩法确认。**设计关**（用户 2026-10-24）：关卡表、皮肤表、`docs/modules.json` 写好后跑 `design_check.py --board remake`（LEVEL-01、MOD-01、ECON-01、RANK-01、FEAT-00），全部通过才发玩法确认；见[检查分阶段](../cocos-game-to-english/references/check-stages.md)。
4. **玩法确认（节点 1）**：逻辑检查和设计关已通过（附 `docs/logic/逻辑检查报告.md`、`design-check.md` 结论），再交给用户占位版试玩入口和玩法清单（[试玩清单](../cocos-game-to-english/assets/user-playtest-checklist-template.md)的第一到四节、第六节）。用户把问题一起提，改好后说"**玩法通过**"。只有用户自己说"直接做完"时才跳过。
5. **再做美术和声音**：按启动包的 `ART_DIRECTION.md`、`UI_PAGES.md` 和下面的硬规则，先做样板、在真实 Cocos 里自审，再一次生成全部美术，替换占位图；声音按 `AUDIO.md` 用 `game-audio-library` 从正规音效库配。
6. **试玩验收（节点 2）**：美术关（`art_check.py`，含首页礼盒 10 帧动画）已通过——美术只在这里查，最终总检测不再查美术，再交试玩入口、美术验收包、试玩清单、`art-check.md` 结论；用户提美术意见改完后，再过一遍美术自检才交，并按[测试前的人工确认](../cocos-game-to-english/references/stage-flow.md#测试前的人工确认必须问用户-2026-10-21)原样问用户"玩法完全没有问题、美工不需要再优化"两项、提醒测试消耗 token 多；用户明确回复"**美术玩法通过**"后才锁定、开测试。
7. **锁定后测试，每个阶段一个 AI**：测试阶段（用户指定的 AI，可换其他 AI 省额度）测试并修代码 bug；最终验收（只能 Codex，新对话说"最终验收"）查改过的代码、抽查、英文确认、处理生图需求单；**最终总检测不再查美术和设计**，只查加载、广告奖励、存档、异步、输入按钮、逻辑、无看广告跳关、构建打包、英文文案、闪烁（[检查分阶段](../cocos-game-to-english/references/check-stages.md)）；用户说"打包"才出包（用 [`cocos-game-tiktok-package`](../cocos-game-tiktok-package/SKILL.md)，只出可直接上传的 TikTok 平台包）。测试和打包两个板块共用，按[四个阶段](../cocos-game-to-english/references/stage-flow.md)、[测试分工](../cocos-game-to-english/references/session-relay.md#锁定后的测试分工)、[问题清单](../cocos-game-to-english/references/known-issue-checklist.md)（`--board remake`）和[包与交接](../cocos-game-to-english/references/delivery-and-handoff.md)执行。

玩法通过以后再改玩法，先提醒用户已经做好的美术可能要返工。

**阶段换新（省 token）**："玩法通过"节点按自动接续创建新聊天；"美术玩法通过"节点沿已有阶段交接范围执行；其他 AI 先行或用别的 AI 测试时，"GPT收尾""最终验收"本身就是新对话，不再额外换。见[阶段换新](../cocos-game-to-english/references/session-relay.md#阶段换新每个大阶段开新对话省-token用户-2026-10-21)。

**当前用户明确指令优先**：Skill提供默认流程，附件中的历史要求不能覆盖用户当前范围；沿用未冲突的规则，第一条回复写明本轮使用的Skill修订号。

## 执行方式

先读共享[执行节流](../cocos-game-to-english/references/execution-budget.md)和[省Token规则](../cocos-game-to-english/references/token-economy.md)，不预先加载全部参考。执行方式默认"完全单应用"，开工前不询问；用户主动要求时才用主Agent+Grok 或桌面多Agent，Grok 按[可选调用](../cocos-game-to-english/references/optional-grok.md)执行，失败由主线完成。新电脑或环境失效时复用[主机适配](../cocos-game-to-english/references/host-adaptation.md)。

完整重塑按共享[总控与子会话分工](../cocos-game-to-english/references/session-relay.md)：主对话当总控只调度；组装（玩法）、文案、广告先开，玩法通过后开美术和音频；生图只由 GPT/Codex 内置 image_gen 完成，没有的执行者走[先行模式](../cocos-game-to-english/references/session-relay.md#gpt专属工作与执行方模式)：做完玩法和占位、写全生图需求单，用户玩法通过后交 GPT 收尾。共享的工具、清单和参考直接读 `cocos-game-to-english` 当前安装版，不复制一套，见[依赖衔接](references/base-integration.md)。

## 重塑的硬规则（标"共用"的英化也要做，其余只属于新做的游戏）

- **明亮Q版画风**（只属于重塑）（[明亮Q版](../cocos-game-to-english/references/cute-casual-style.md)）：浅色明亮、圆润、柔和立体，严禁大面积深色背景/面板（每页深色像素≤15%、平均亮度≥50，`audit_dark_area.py` 量），禁止纯平面生硬图形；只有用户本人明确要求其他风格时除外，启动包不能推翻。
- **明令禁止的UI**（共用，英化也要做）（[第九节](../cocos-game-to-english/references/cute-casual-style.md#九明令禁止的ui用户-2026-10-20)）：大块白色/浅灰白板、大块纯色或深色按钮和面板、近黑/藏青/深灰的特粗字、没有配色的单色图标、全部套同一个模板、堆成一坨挡屏幕。**游戏中玩法区≥80%，常驻UI≤20%**、互不重叠，提示小且不在中间；游戏中弹窗面板≤60%；面板内容全放在边框内框里（[防穿模](../cocos-game-to-english/references/ui-style-and-samples.md#边框标题牌角花内容只放在内框里防穿模)）。布局**从运行中的游戏自动读出**：浏览器里用 `chrome_touch.py` 的 dump_ui 读首页、游戏中和每个弹窗（两种比例），`extract_ui_layout.py` 生成 `docs/ui-layout.json`，`audit_ui_coverage.py` 量（门禁 ART-05、UI-03），手填或改过的布局会被拒绝。
- **页面布局：货币在最上方、功能按钮集中在下方、图标为主**（共用；含占位版；用户 2026-10-23 修改）：货币/体力永远在屏幕最上方的资源栏，绝不放在中间；设置在左上或右上角；已有地图/皮肤等图标分配到主角中部左右，其余次要图标在主按钮下方紧凑分组且所有行合计最多五个；首页一定要有大标题和丰富的封面设计，按钮加起来最多占屏幕 40%（标题和封面不算）；一个页面最多 2 个主要文字按钮，中间留给主角/场景（[第十节](../cocos-game-to-english/references/cute-casual-style.md#十页面布局货币在最上方功能按钮集中在下方图标为主用户-2026-10-23-修改试玩版也严格执行)）。
- **首页必有两个主页按钮、不要分享**（共用，英化是重点，用户 2026-10-23）：首页下方功能图标那排一定有桌面快捷方式（Add to Home Screen）和个人主页回访（Profile Revisit），接真实 SDK；游戏里不做任何分享功能（分享用不了），英化时原游戏的分享全部删掉、这两个键不问用户直接加。见[首页必加两个主页按钮](../cocos-game-to-english/references/tiktok-home-growth.md#英化首页必加两个主页按钮去掉分享不问用户用户-2026-10-23)。
- **每个页面都有生成的背景**（生成背景只属于重塑；不能纯色共用）：**包括游戏中**（天空不能是一整块浅蓝，至少渐变加云朵/远景）；过关/失败/结算/暂停弹窗后面是半透明遮罩下的游戏场景或生成的全屏背景，禁止纯黑/纯色底。一种纯色不能超过屏幕 40%，`audit_page_richness.py` 量每张 dump_ui 截图。
- **全 UI 生图**：按[主题规范与样板](../cocos-game-to-english/references/ui-style-and-samples.md)先样板后整套，按[全UI生图重构](../cocos-game-to-english/references/english-ui-rebuild.md#重塑全-ui-生图重构)做完整按钮和图片标题（固定英文和底图一体生成，动态数值实时显示）。美术清晰度是硬门槛：原图≥显示尺寸 2 倍、禁止放大使用、禁止低分辨率/像素风/粗糙边缘（[清晰度硬规则](../cocos-game-to-english/references/artwork-and-feedback.md#清晰度硬规则禁止低分辨率像素风和粗糙边缘)）。
- **声音从正规音效库下载**（声音文件只属于重塑；两类声音开关和十格音量共用）：用 `game-audio-library`，禁止代码合成或 AI 生成；两类声音开关、十格/10%音量，见[共通首页与声音](../cocos-game-to-english/references/common-game-components.md)（门禁 AUDIO-01、AUDIO-02）。
- **内置板块**（共用，MOD-01/02、FEAT-01、ECON-01/02，用户 2026-10-23）一律按[内置板块](../cocos-game-to-english/references/game-modules.md)：每款游戏有货币；每关结束（无尽每局结束）看广告×2；首页 10 帧动画礼盒（看广告领货币，随通关数和下一款皮肤价格变大）；皮肤板块默认要：<!-- workshop-module-import -->工坊v3使用已核生成表，其他包由`make_skin_table.py`生成20款主角＋10款背景，只用货币买、价格台阶 2R 起每款加 1R/4R/10R/20R、加成随稀有度上升、限定皮肤排第一且画得最精致；没有完美通关送皮肤；下一关前弹"看广告试用"（前 2 关不弹，[收集与皮肤系统设计](../cocos-game-to-english/references/rarity-unlock-design.md)）；广告奖励全用 `AdRewards.ts`，每个广告按钮连点只发一次、广告前后不卡顿。`audit_game_modules.py` 查。
- **默认不做排名、七日签到、更多游戏、分享**（用户 2026-10-23，多做多错）：按[融合政策](../cocos-game-to-english/references/fusion-policy.md)判定默认范围与明确选择；`audit_game_modules.py`、`audit_page_richness.py`、`audit_ui_coverage.py`、`audit_platform_markers.py` 会拦。
- **同一组按钮同一种风格**（共用，用户 2026-10-23，永久禁止混用）：一组功能键的字都与按钮一次生成成整张图，同组底板材质与字形一致，整组一次生成；`art_check.py`"同组按钮同一种风格"必须通过。见[同一组按钮同一种风格](../cocos-game-to-english/references/page-richness.md#同一组按钮同一种风格按钮和下面的字做法底板颜色都一样用户-2026-10-23两个板块所有美术)。
- **文字也要设计**（共用，用户 2026-10-22，明令禁止直接调用字体打固定的字）：固定的字（标题、按钮、栏目名、物品名、任务名、COINS/Price）一律用 GPT 和底图一起生成图片字（`txt_<字>`，跟画风走，常用花体/装饰字），深绿/深青色的字、细字禁止；**深色粗字永久禁止（用户 2026-10-23，不分颜色，游戏中 HUD、图片字、面板说明都算；字的填充色只用亮色，深色只在描边和阴影里；状态字"HOME SCREEN OPEN""MISSIONS 2/3 RESOLVED"删掉）**，见[永久禁止深色粗字](../cocos-game-to-english/references/page-richness.md#永久禁止深色粗字用户-2026-10-23两个板块所有页面游戏中-hud-也算)；按钮（含左右箭头）全部来自同一套（`docs/art/button-set.json`）；会变的数字用按画风生成的数字位图字，大段说明文字放在底板上；不用系统细字体、对比度够，`art_check.py` 量。见[文字也要设计](../cocos-game-to-english/references/page-richness.md#六文字也要设计两个板块用户-2026-10-22)。
- **所有字都是生成的图片字、和画面一体（共用，用户 2026-10-23，重点强调）**：首页的字、金币数、体力数、PLAY 按钮上的字、说明文字全部是生成的图片字；**每个按钮连同上面的风格化文字一次生成成一整张图**（`btn_<字>`，不能"生成底板＋字体字/另一张字图"）；**游戏大标题是一张按画风一次生成的风格化 logo**，绝不打字；**数字用按画风生成的数字图做成位图字体**（BitmapFont/LabelAtlas）；只有公告、玩法说明这类大段文字可以用细一点的字体。正例 THE COLLECTION 收藏页，反例 Scissors Master 首页。`audit_page_richness.py` 的 `spliced_button`/`typed_title`/`font_number` 拦，`art_check.py` 单独一行，见[所有字都是生成的图片字](../cocos-game-to-english/references/page-richness.md#所有字都是生成的图片字和画面一体按钮连字一张图标题是-logo用户-2026-10-23两个板块重点强调)。
- **字不压扁拉伸、字色有变化、只改美工也全套（用户 2026-10-23，两个板块）**：每个字/按钮图单独裁到可见边缘做成自己的 SpriteFrame，按 `min(w/W, h/H)` 等比缩放（SizeMode TRIMMED/RAW，不用 CUSTOM 硬设成按钮尺寸），放不下就改按钮或重新生成，绝不压扁（反例：DETAILS 压扁 2.89 倍）；不用 Canvas `fillText` 画字；一页上标题、按钮字、数字、标签颜色不能全一样（反例：Hazel's Shelf Scramble 全青色首页、全橙黄 Your Progress 弹窗），按钮字用花体风格字；所有能点开的页面和弹窗列进 `docs/art/screens.json` 一起改一起测。用户只说"重做美工、重新设计按钮/图案/logo/图标、改美术"时走 [`cocos-game-art-redo`](../cocos-game-art-redo/SKILL.md)，带上全部美术规则和 `art_check.py`。见[图片字不能压扁拉伸](../cocos-game-to-english/references/page-richness.md#图片字不能压扁拉伸字色要有变化只改美工也全套检查用户-2026-10-23两个板块)。
- **数字不叠印、卡片里的图不伸出、没有假透明格子（用户 2026-10-23，两个板块）**：固定数字（每日奖励、价格、关卡奖励）和金币图标/底板**一起生成成一张图**；会变的数字用**一个**位图字体 Label（.fnt 每个字的 xadvance ≥ 字宽，三位数和最大值都放大看过），不手摆一个个数字图、不再叠第二个 Label、字距不为负；卡片里的奖励图在卡片内、不被拉长；生成图用真透明（alpha），不能带灰白/绿色棋盘格。`audit_page_richness.py` 的 `glyph_overlap`/`double_number`/`negative_spacing`/`font_advance`/`clip_out`/`checker_fill` 每轮美术自检就拦（反例：Daily Rewards 弹窗 100/150/200/300 像"10"叠在"100"上，第 7 天的车伸出卡片，卡片里是绿色棋盘格；见[数字不叠印](../cocos-game-to-english/references/page-richness.md#数字和字不能叠在一起固定数字和底图一起生成用户-2026-10-23两个板块)）。
- **位置穿模审查、主功能字在按钮上（用户 2026-10-23，两个板块）**：道具数量、体力、金币、关卡的胶囊/边框、按钮、收集功能键都是生成的图，会变的数字单独生成数字图做位图字体；字不压图标（反例：体力"20"压在闪电上）、图不伸出按钮/胶囊（反例：WATCH AD 左边金币伸出去）、按钮不重叠；WATCH AD、PLAY 这类主要功能字在生成的按钮上，按钮下的小字只做解释。每次把图拼到一起就 dump＋`art_check.py`（"位置穿模"一行）并看 `overlap/` 穿模审查图，美术做完就审，不等用户发现。见[位置穿模审查](../cocos-game-to-english/references/page-richness.md#位置穿模审查每次把图拼到一起都要查用户-2026-10-23两个板块)。
- **标准按钮功能和一局状态（逻辑检查，共用，用户 2026-10-23）**：关卡内能暂停并回首页；设置能返回；失败页有 Home 和 Retry，复活广告单独一个放在下面；胜利页有 Home 和 Next；按钮位置固定、不随机交换；暂停停住物理、计时和生成；离开一局清干净（节点、触摸、定时器、Tween、相机）；广告和加载回调带局次，迟到的忽略，超时安全恢复且不能连点叠奖励；加载失败有 Retry；刷新后进度和声音设置都在、坏存档不崩；触摸取消不提交；命中取最上层；同一动作一套判定；关卡配置没空槽、末关后不重复最后一关、教程比第一关简单；Daily 真的按日期；循环有上限；奖励不绕过购买规则；平台按钮有反馈；镜头各方向都跟、背景铺满。第一轮玩法做完和以后大改玩法都用 [`cocos-game-logic-check`](../cocos-game-logic-check/SKILL.md) 查（门禁 LOGIC-01），规则见[逻辑规则](../cocos-game-logic-check/references/logic-rules.md)。
- **美术只在美术关查、最终总检测不查美术（共用，用户 2026-10-23 定、2026-10-24 改）**：清晰度（运行时的图≥节点 2 倍、背景≥1.5 倍，代码里动态设置的图也算）、首页礼盒 10 帧动画等全部美术项都在 `art_check.py` 里，第一轮美术起每轮都跑、通过才交节点 2（反例 RobotSpaDay：用户确认美术后才查出 22 张不到 2 倍）；最终总检测不再跑美术，锁定后改了图只对改动页面重跑。见[美术只在美术关查](../cocos-game-to-english/references/page-richness.md#美术只在美术关查最终总检测不查美术用户-2026-10-24两个板块)。
- **美术是重中之重**（共用，用户 2026-10-23）：美术阶段花最多的精力和 token，每个页面/弹窗/HUD/按钮/图标/图片字都单独写设计要求；先样板后整套，至少两整轮自审（第二轮零"需处理"、看图清单逐条写结论）才交用户；美术问题在交用户前一票否决（美术关没通过不交节点 2）。见[美术是重中之重](../cocos-game-to-english/references/page-richness.md#美术是重中之重用户-2026-10-23两个板块)。
- **弹窗不能单调、尽量用生成图**（共用，用户 2026-10-23）：每个弹窗都要有生成的面板和标题牌、图片字标题、一张生成的插图（礼物/宝箱、角色、带游戏图标的手机、奖励物品＋货币图标）和整套按钮，不能是浅色平板上只有字和几个扁平按钮（反例："Home screen reward"弹窗）；能用生成图的地方都用生成图，`plain_popup` 会拦（[尽量生成图](../cocos-game-to-english/references/page-richness.md#尽量生成图尽量替换游戏里的图用户-2026-10-23两个板块)）。
- **顶部资源栏、关卡地图、奖励关和限定关**（共用，HUD-01、LEVEL-01/02，用户 2026-10-22）：
  - **顶部资源栏**：货币（按题材起名和画图标，海底→珍珠）、体力（闪电）、关卡进度（无尽是最高分），放在画面最上方的浅色胶囊里，数字当场变化。
  - **关数和难度**：通关型**至少 70 关**（用户 2026-10-24：不足按已选玩法补到 ≥70；原有超过 70 关全部保留，不裁剪；多于 70 也行），难度逐关递增，没有突然变难的关；限定关在第 10、20、30…关（总关数以内每个 10 的倍数）。`audit_level_plan.py` 查 `levels_at_least_70`，在设计关跑。
  - **地图**：通关型一定有地图，显示总关数；无尽型不要地图。
  - **限定关**：每 10 关一个（第 10、20、30…关），难度照常，地图节点是华丽边框；第一次打过送大量货币（至少前 5 关货币总和）并解锁下一章；限定皮肤两种格式任选（用户 2026-10-24）：`final` 只有最后一个限定关送一款，`every_10` 每个限定关各送一款（只能在限定关拿到；`make_level_plan.py --limited-skin-mode` 和 `make_skin_table.py --limited-mode` 写同一个）。
  - **奖励关**：每 10 关一个，<!-- workshop-bonus-import -->工坊v3保留已核导入位置，普通包位置由 `make_level_plan.py --seed` 定，很简单，3 倍货币、看广告 6 倍，地图节点画成货币图标。
  - **检查**：`audit_top_bar.py`、`audit_level_plan.py`，浏览器实测 LEVEL-02。见[顶部资源栏和关卡地图](../cocos-game-to-english/references/top-bar-and-level-map.md)。
- **不能有单调页面**（共用，PAGE-01）：结算页、首页、选关、弹窗、设置、皮肤页按[页面不能单调](../cocos-game-to-english/references/page-richness.md)做足，不能只有一个按钮、纯色底、只有字的按钮、系统默认字体、空白面板、开发用文字；dump_ui 时写 `purpose`，`audit_page_richness.py` 量。**美术自检在美术阶段做（ART-06）**：每轮美术做完（第一版、每次按用户意见修改后）立刻 dump_ui 读全部页面（含游戏中）、跑 `art_check.py`、Codex 看总览图，改到全部通过才交；按意见修改也整页复查。不能出现空白卡片、占位方块、深色粗字、字超出按钮、大片空白、选关一屏少于 6 关。最后的测试只查玩法和功能。见[美术自检](../cocos-game-to-english/references/page-richness.md#五美术自检每轮美术做完立刻做两个板块art-06page-01)。
- **设置页两个标签**（共用）：功能页（How to Play、震动、底部游戏名与版本号）和声音页（音乐、音效分别开关和十格音量），见[设置页通用设计](../cocos-game-to-english/references/common-game-components.md#设置页通用设计两个标签页功能和声音用户-2026-10-21两个板块都用)。
- **首关互动教程**（共用）：按[首关教程](../cocos-game-to-english/references/first-level-onboarding.md)做真实互动步骤，仅每次重启后的前两关自动出现。
- **英文不能像机翻（COPY-01）**：`COPY_EN.md` 的文字接进游戏后，用 dump_ui 读出玩家实际看到的字，跑 `audit_copy_quality.py`，GPT 审语感，见[英文文案质量](../cocos-game-to-english/references/english-ui-rebuild.md#英文文案质量两个板块都要)。
- **关卡要能过**：按[创建检查](references/creation-gates.md)生成和求解，用真实规则重放到胜利；有限预算没找到解不能称无解。

## 两个板块共用的硬规则

- **严格不做看广告跳关**，`audit_no_ad_skip.py` 必须为 0（门禁 NOSKIP-01）。
- **广告**：取消/出错/超时不奖；严格完整播放才奖、只奖一次；按钮等结果时有"检查中"状态，每种非成功结果都有看得见的提示，能重试或关闭；平台任务回到前台作废旧查询（门禁 AD、CLAIM、GROW-01）。
- **等待一定要能结束（ASYNC-01，Monkey Dash 2026-10-21）**：广告和平台任务的结果可能从回调来，也可能从 Promise 来，每条路都接进同一个单次结算；等待有自己的截止时间。测试把 SDK 结果和原超时回调同时扣住，画面仍能结束等待、重试成功；替身能分别用每种方式返回；同一个检查先在故意改坏的版本上失败过。见[返回方式和等待出口](../cocos-game-to-english/references/tiktok-home-growth.md#返回方式和等待出口写了超时--能结束等待monkey-dash-2026-10-21)。
- **打包脚本自己调用门禁**，并用 `test_writer_refusal.py` 证明缺证据时真的出不了包（BUILD-03）。
- **只有一种包（BUILD-04，用户 2026-10-23）**：用户说打包、出包、上传测试包、检测包、压缩包、TikTok 平台包，都用 [`cocos-game-tiktok-package`](../cocos-game-tiktok-package/SKILL.md) 出**可直接上传的 TikTok 平台包**：Native 小游戏构建、ZIP 根目录直接是 game.js/game.json/project.config.json、`assets/resources` 进 Cocos 小游戏普通分包（启动时带进度加载、有 Retry）、未压缩主包≤4,000,000 字节、总包≤30,000,000、独立分包各≤4,000,000；用 `make_tiktok_zip.py` 出包（先跑门禁，不合格不写 ZIP）。严禁外层文件夹、Web 包冒充 Native、源码包、ZIP 套 ZIP、__MACOSX/.DS_Store、测试跳关、旧 App ID（反例：SquareRush 旧包 resources 留在主包，主包 8,754,975 字节被 TikTok 拒绝）。
- **测试必须全部测完**（共用，用户 2026-10-22）：分 9 段测、每段当段修、不停下等用户，`--executor-exit` 返回 `test_stage_complete` 才结束，见[测试阶段必须全部测完](../cocos-game-to-english/references/stage-flow.md#测试阶段必须全部测完分段测当段修不停下一次汇报用户-2026-10-22)。
- **测试在浏览器里做**，严格用 Ego Lite，改用 Chrome 前先问用户；Ego 和 Chrome 内核相同，只在一个浏览器里测一次；手机用 iPhone 预设（默认 iPhone 15，短屏 iPhone SE），**每个按钮都点一遍**（按钮清单从游戏里读出，`audit_button_coverage.py`，INPUT-05）；不依赖、不询问 TikTok 开发者工具；不做上传 TikTok 后的测试。
- **最终检查一项不漏，加载是重点**（共用，用户 2026-10-23）：加载**不写死结束时间**（大游戏做不到，用户 2026-10-23），改判不卡住、不白等（按这款游戏真正加载的量算允许时间）、下完就进（不许假的最短加载时间），见[不写死结束时间](../cocos-game-to-english/references/startup-loading-timing.md#不写死结束时间用户-2026-10-23)，每条进关路线（PLAY、地图选关、Next、Retry、复活后继续、切后台回来、关掉重开）都真实进到能玩，最终构建上加载整套重测；按[最终检查总表](../cocos-game-to-english/references/stage-flow.md#最终检查一项不漏加载是重点用户-2026-10-23)逐行写结果和证据。
- **游戏必须进得去**（启动契约，LOAD-01）、**动态画面**（VIS-01）、**启动加载计时**（LOAD-03）、[加载与广告提前预防](../cocos-game-to-english/references/loading-and-ad-prevention.md)、[重开与触摸输入](../cocos-game-to-english/references/replay-and-input-checks.md)、进入测试前先跑 `preflight.py --board remake`。
- **被占就开新的，绝不等待（用户 2026-10-23，最高优先）**：出现"被占用/排队/资源锁/还没轮到"时立刻在 Ego 里新开独立窗口（或本会话自己的新 TaskSpace、新端口的 `serve_preview.py --snapshot`），不等、不轮询、不抢别人的；每次新开前 `browser_slots.py sweep --close` 关掉空了的旧窗口，别人还在用的不动。只有这个游戏自己的构建、音频流水线用 `heavy_lock.py --project <工程>` 排队（放后台，测试不等它）；子会话数按内存定，见[被占就开新的](../cocos-game-to-english/references/machine-load.md#一遇到被占用要排队立刻新开一个绝不等待用户-2026-10-23最高优先)。
- **测试用完就自己关浏览器（用户 2026-10-23，所有环节）**：不管哪个环节（英化/重塑的接入测试、按钮点测、加载测试、录屏、批量跑关、截图审美术、打包前手机审查、最终验收），**一次测试用完，马上自己关掉这次测试在 Ego 里开的窗口、TaskSpace 和预览服务**，不留给以后的清理、不等用户来关：`chrome_touch.py` 跑完自动关；手动开的用 `browser_slots.py close --name "<线名>"`（真的结束 Ego 空间、停掉预览，不只是注销；退出码 2 时照着输出的 `ego-browser` 代码再跑一次）；汇报"测试完成"或写交接前 `browser_slots.py check --name "<线名>"` 必须通过。Ego 窗口没有例外（用户试玩不在 Ego）；别的会话还在跑的测试窗口不动。见[用完就关](../cocos-game-to-english/references/machine-load.md#测试用完就自己关浏览器用户-2026-10-23所有环节)。
- **Ego 只给 AI 自己测试用，用户试玩一律在 Codex 本地预览（用户 2026-10-23，两个板块、所有环节）**：只有 AI 调用 Ego 做自己的测试才算使用 Ego，Ego 里开的每个窗口、TaskSpace 都只用于 AI Agent 自己测试。**禁止一切让用户在 Ego 里试玩的做法**：不开"给用户试玩"的 Ego 窗口，不把试玩页在 Ego 里置前或 `handOff()` 给用户，不登记 `--keep` 的 Ego 空间（脚本会拒绝），不说"试玩页已在 Ego Lite 中打开并交给你"。交给用户试玩时，用 `../cocos-game-to-english/scripts/serve_preview.py --directory <最新 Web 导出> --keep --name "<线名> 用户试玩"` 起本地服务，**在 Codex 回复里给本地预览链接**（并写清横/竖屏和操作），用户在 Codex 里打开预览试玩。历史 Ego 空间只列候选；核当前归属、已完成/取消/被新版替代且不再使用后，由当前拥有者正常结束，再以 `ego-finish --space-id <ID>` 核消失。标签不能单独作为关闭依据。见[Ego 只给 AI 测试](../cocos-game-to-english/references/machine-load.md#ego-只给-ai-自己测试用户试玩一律在-codex-本地预览用户-2026-10-23)。
- **新建测试空间不问用户（共用，用户 2026-10-23，已长期授权）**：每次测试都自己新建一个 TaskSpace，不问、不等确认；空间不存在/失活/被占/连不上就直接新建接着测（汇报一句话带过），禁止问"是否允许新建独立测试空间"；只有 Ego 卡到没法准确测试才问用户是否改用 Chrome。测完自己关；每一轮、每个新对话开头先 `browser_slots.py tidy` 收拾上一轮，不留闲置空间。见[新开测试空间不用问](../cocos-game-to-english/references/machine-load.md#一遇到被占用要排队立刻新开一个绝不等待用户-2026-10-23最高优先)。
- **画面判定只由 GPT 做**；**不自动打包**；不清用户存档；不把脚本、Mock 或截图当真实通过；Secret 不入代码、包或截图。

启动包历史要求与默认模板冲突时，先按融合政策核对当前明确选择与项目范围；没有明确选择的部分按统一模块处理，并说明必要差异。兼容购买方式中的最多 8 次广告约束仅在对应模式适用，不覆盖默认货币购买模板。

历史完整创建说明按需查[创建细则](references/workflow-detail.md)，不默认通读。

**页面就绪与取消重进（2026-10-23，共用必测）**：涉及导航/分包/最终验收时，按[页面就绪与取消重进](../cocos-game-to-english/references/page-readiness-and-cancel.md)执行。LOAD-01新增audit_page_readiness最终runtime报告；普通/热缓存页面直达，独占大包不得绑全部按钮；慢下载三次取消重进、关闭后资源完成、缓存断网和普通控件独立性均实测，不用静态通过替代。

**加载故障复盘入口（v20完整复检）**：加载维护、完整逻辑检查或打包前，按[加载与重试案例及验证方法](../cocos-game-to-english/references/loading-recovery-casebook.md)识别本项目实际加载层，读取对应复现与修复步骤；字体/图片/原生分包、请求独立计时、取消重进、真实HTTP新请求、最终产物绑定均不可由入口替身检查代替。案例中的历史游戏结果不代表当前项目通过。

**明确选择的兼容模式**：用户当前或项目权威规格明确要求旧版 League、签到或其他购买方式时，按[兼容玩法](references/explicit-legacy-features.md)启用相应实现与验收，不因默认模板删除已有业务或存档。

第一轮美工检验同时执行[留白与功能键实际大小约束](../cocos-game-to-english/references/page-richness.md#第一轮就查留白与功能键实际大小用户-2026-10-24两个板块)：检查可见图片尺寸和整组布局，不以点击框放大代替画面放大。

首轮美工即执行[按钮反例约束](../cocos-game-to-english/references/page-richness.md#首轮按钮反例荧光底加普通字用户-2026-10-24)：禁止高亮纯色/荧光按钮配非生成普通字，也不能生成空底后叠 `cc.Label` 当作完成；具体做法沿用现有“按钮一次成整图”，交预览前自查。

**新玩法首现必测（用户 2026-10-24）**：关卡表中每个新玩法第一次出现的关卡加 `"tags": ["intro"]`；推荐记录稳定的 `mechanics` 标识。测试时用 `plan_level_tests.py --level-plan <实际关卡表> --out <清单.json>`，所有首现关并入必测；漏标提醒需补齐再生成。详见[首现关与必测清单](../cocos-game-to-english/references/prepackage-mobile-review.md#新玩法首现关与必测清单2026-10-24)。


**上传体积硬限制（2026-10-25）**：全部 TikTok 上传 ZIP 路线统一使用 `cocos-game-to-english/scripts/upload_size_gate.py` 的固定未压缩限额：总包≤30,000,000、主包≤4,000,000、独立分包各≤4,000,000字节。正式 `make_tiktok_zip.py` 和轻量 `cocos-tiktok-package-check/scripts/build_checked_zip.py` 的底层写 ZIP 函数均在打开输出前拒绝超限；目录检查与最终 ZIP verifier 同样保留。成品直接出包走轻量 writer，不重跑游戏CI；禁止另写未接入同一门禁的压缩脚本或Finder手压。新增出包入口必须接此门禁，并先用旧超限反例证明无输出，再用正常包证明通过；未知/未接入的外部压缩工具不在自动拦截范围。
