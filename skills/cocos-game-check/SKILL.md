---
name: cocos-game-check
description: "统一检查（触发词：检查、测试、验收、找bug、修bug、启动、进不去、白屏、卡加载、按钮没反应、音量、出包、打包、ZIP、检查包、包太大、评审）。所有Cocos小游戏共用的检查Skill：英化游戏和重塑游戏都用同一份。启动与稳定、功能测试与修复、出包、最终包检查、评审（只检测不修改）、美术检查，以及全部检查脚本。"
---

**手机仍失败时先撤销结案（用户2026-11-12）**：按[已报告手机问题](package-check/references/resource-and-reported-issues.md)登记实际故障包和原始症状。先区分平台包挂载/入口前、适配器至首帧、游戏内加载、进入玩法后。受控存档或广告通过不能关闭“平台加载页无游戏画面”；保留本地通过的原范围，手机故障保持未解决。实际产物先跑当前启动审计；已知SDKVersion、子域判断、包内fs.access旧写法在适用Cocos2产物中必须经共享normalizer修正，重建后补入口能力差异对照。缺日志不能补成“入口已执行”，模拟器自动补全接口不能冒充缺字段覆盖。没有原症状对照或真机成功证据，不再交同字节包宣称修复；诊断候选只在用户明确授权后按既有defer-external登记。局部/旧游戏/--draft不豁免故障追踪和实际writer回执，不扩测无关内容。

**跨平台语义与冷升级（用户 2026-11-11）**：Android、浏览器触控或标记为iOS的宿主通过，不能证明iOS Native通过。首次平台接入及存档/启动/SDK相关依赖变化时，按[跨平台运行与旧存档升级](../remake-core/references/cross-platform-runtime-contract.md)补最短Native链：新玩家、旧类型存档升级、同步失真/异步保值恢复、不可恢复时保档与可见Retry、实际触控进入玩法。已有存档不可读不能当空档重置。STORAGE-01 v3核原始类型、恢复结果和同runner反例；无裸数值按实际schema举证。正式、轻量写包与最终交付共用只读核准回执，旧报告不覆盖新增场景。只补受影响节点，真机与语义模型分列。

**六标准广告节点与美工制作已接入（用户2026-11-11）**。首次完整制作与明确的六类迁移，结束、主页、永久皮肤、体力、局内道具、周期试用六类全部必需；额外奖励循环不能替代任何一类。按[六标准广告制作联动](../remake-core/references/ad-standard-six.md)在制作时调用同包ad-boost与remake-art。旧“0～2个才推荐/无系统不新增/英化默认不加这些系统”不再限制这六类所需依赖。已交付游戏的无关局部维护保留原授权范围和有效记录，不自动改原件。


**返工写包与修复续跑（2026-11-10）**。本轮要求检查或交付游戏时，按[执行范围计划及修复续跑](../remake-core/references/regression-scope-gate.md)核对实际改动与可沿用证据。遇到漏传计划、整包通配、执行中换计划、执行器粒度过粗或最终交付回执缺失、失配时，当前 AI 直接修复具体缺口，重新核准后回到原节点，继续到已授权的检查与交付完成。有效证据直接沿用，新检查限于实际受影响或确实缺证的项目。只讨论流程或更新 Skill 时，完成讨论和规则更新即可，游戏案例用于说明。

**当前检查执行规则（用户 2026-11-08）**：先读[一次通过、按改动复验](../remake-core/references/incremental-checks.md)。图片、文字/字幕、音效、玩法、关卡、平台检查均按命名节点留存真实记录；已通过且依赖未变的项禁止重复执行，代码或配置变化也不触发全量。浏览器和写包读取同一计划；旧文中的“每次必跑/全量检查”改按完整覆盖核对解释。最终 ZIP 的本次体积与分包核对按用户单独要求保留。

**正式 Native 启动与交付记录**：启动合同、两个写包入口和正式交付共用 `startup.native.renderer` 实跑账本。先核本版启动、遮罩消失、真实触控及 Retry 证据，再按 Native 内容、运行器、环境和规则决定沿用或只补跑启动项。交付记录逐项写明执行方式及证据；阻断写独立拒绝回执。[复用边界](../remake-core/references/native-startup-ledger.md)

**完整美术回执已撤销（用户 2026-11-08）**。美术制作和实际画面问题按首次制作或受影响的节点处理，保留各项实际结果。常规与轻量写包、正式试玩、最终交付均不得生成、补齐、更新或要求完整美术回执，也不以全量图片复核或截图汇总作为替代条件。已通过的游戏局部返工只检查该改动影响的节点。**保留的三条轻量保障（11.17.14）**：① 首轮正式英文试玩前要有一次完整 `art_check.py` 运行记录（`.tiktok-kit/art-check-record.json`，不绑图片指纹，之后小改不用重跑，最近一次运行有需处理项时先修这些行）；② 两个写包入口只读包内字节，查英化新做的图不超过 800 KB（`docs/english/pre-english-images.json` 里的中文原图不查）；③ 首次英化的人工画面清单并入 Saul“试玩没问题”这一步，返工时清单只是可选快看。最终 ZIP 分包、体积、配置和同版链接核对按原规则执行。

**画面随人工试玩检查（用户 2026-11-08）**。同版试玩附[人工试玩画面清单](../remake-core/references/manual-visual-review.md)的适用项。常规检查走技术日志及必要点位图，偶发画面故障才定点录制。


# 统一检查（英化与重塑共用）

**默认 BGM 与预览分域（2026-11-11）**：有首页 BGM 的项目按 [BGM 轻量核验](../remake-core/references/bgm-startup-preview.md)在现有预览命令加 `--expect-home-bgm`。同页最多补一次普通 PLAY 与真实播放时间采样；缺默认请求或输入后仍停住即拦截。浏览器 `NotAllowedError` 不等于 TikTok 包故障，预览通过不等于真机出声。只在音频启动/宿主变化或已报故障时补该节点，未变化沿用。

**正常游玩优先（用户 2026-11-09）**。默认在原生时钟和支持的手机视口试玩，检查输入、镜头、运动、碰撞及可见卡顿。怀疑帧率影响玩法或接到高刷问题时，才显式选 `frame_rate` 做 60/120 Hz 对照。5% 仅提示轨迹可能分岔，体验结论按真实操作和可复现的玩法后果判断。该诊断不进入默认回归或出包门禁。

**画面问题当轮修复（用户 2026-11-09）**。制作、修复和出包任务中，发现可复现且在当前授权内的遮挡、裁切、重叠、缺图、错层或假按钮，直接修源码或素材、重建并在受影响的正常手机尺寸及操作状态复验，再汇报结果。采集或探针无效时先修测试并重跑。只读评审、超出授权范围或缺少可复现条件时按实际边界记录。

**制作时落实。** 新增或改变共享回归时，在本次 Skill 更新中把能提前落实的设计写回制作基线和对应板块。项目按现成规则实施，实际适用回归按当前证据验收。 [制作基线](../remake-core/references/production-baseline.md#维护这份基线)

**弹窗关闭后卡住（2026-11-11）**。按[实例归属](../remake-core/references/modal-input-ownership.md)落实异步防重和清理；新机制首件、相关修改或故障排查使用独立的[modal_lifecycle 专项](package-check/references/modal-lifecycle.md)，同一管理器/关闭机制用代表件。默认预检与出包套件保持原样，已有等价实测直接复用，不逐页面叠加，也不因新补丁重测旧游戏。

**适用于所有 Cocos 游戏的局内激励广告复活（用户 2026-11-09）**。在美工完成后第一次交同版试玩时，游戏有此入口就把它列入[首轮人工试玩清单](../remake-core/references/manual-visual-review.md#首轮人工试玩的局内广告复活)。由真人正常走关、触发失败、取消或看完广告，再确认原局及操作。这个用例退出最终自动回归和出包门禁。其他激励广告、普通后台恢复和存档照各自规则检查。

**已交付返工的视觉交付规则（用户 2026-11-08）**：已交付源码/测试包后，用户要求“改完这处美工给测试包”即授权本次指定视觉修改免 AI 美工复验；按[返工交付与人工快查](../remake-core/references/returned-art-delivery.md)记录独立授权并继续完成同版 ZIP＋试玩入口。旧文“每轮必须先过美工/回执过期必须复验”不适用于此授权范围；不伪造技术通过，不扩到功能。人工快查放原有 Native 试玩与反馈时，不新增出包等待。

**英化旧游戏整改侧栏（2026-11-10）**。收到“用最新版 Skill 整改侧栏”等请求时，先按[四项局部整改](../remake-core/references/tiktok-home-growth.md)处理去游戏名、侧栏布局、主页回访和桌面快捷方式。旧工程按本次明确授权执行；检查读取同一增量计划，只补验真实改动和共享依赖，沿用其余有效记录。

**免费领取被广告状态挡住（2026-11-10）**。有基础奖励和可选广告加赠时，沿用原广告入口盘点，核对请求未完成、回到游戏但结束回调缺失时的真实免费领取路径。共享静态检查 `A4_free_claim_ad_lock` 提示已支持的共用函数风险写法，逐入口记录按项目既有退出和领取路径判定业务结果；请求阶段 15 秒和播放成功后 30 秒提供退出的规则继续适用，细则见[广告异常与免费领取](../remake-ads/references/ad-timeout-and-regression.md#免费领取与广告加赠共用状态2026-11-10)。本项缺证时定点补齐，有效证据沿用。

**TikTok 最终 ZIP（用户 2026-11-08）**。每次交付测试 ZIP，对实际归档重新做体积、分包和 CRC 检查，并由脚本自动运行官方 `ttmg check`、`ttmg build`。首用缺 CLI 时自动下载已验证版本。失败或缺回执不交包。返工按实际改动及依赖做专项回归，复用未受影响的有效美术与玩法记录。详见[最终 ZIP 与 TikTok CLI](package-check/references/fresh-upload-size.md)。

**测试包与同版试玩链接同发（用户 2026-11-07）**。只要交付含游戏测试包，同一回复须给出 ZIP 和已启动、可打开的同版手机试玩链接。跳过美术、重发、改名同样适用，用户明确说本次不用链接时按其指示。仅有 ZIP 只算出包，交付未完成。正式交付用 `prepare_delivery.py --preview-url` 回读手机入口与脚本，并用启动合同的 Web 指纹校验正在服务的快照，任何一项失败都不写交付回执。

## 浏览器测试路线（用户 2026-11-06，取代旧回退规则）

英化人工操作用 **Computer Use + Edge**。自动检查仍在 **Ego Lite** 独立 TaskSpace 执行原有脚本并复用有效证据。英化的 Google Chrome 只在美工试玩和最终测试包交接时打开。 其他流程的自动检查按原 Ego 路线执行。缺少对应能力时继续离线工作，记录实际未测项。详见 `<SKILLS_DIR>/remake-core/references/browser-testing-policy.md`。


修订：`2026-10-28.check-unified.4`。英化包和重塑包内这个 Skill 字节相同。检查规则以重塑包 v7.1 的检查板块为准（`startup/`、`test/`、`package/`、`package-check/`），评审沿用原评审入口（`review/`）。检查脚本与规则库用同包的共享库 [remake-core](../remake-core/SKILL.md)，美术检查用同包的 [remake-art](../remake-art/SKILL.md)；本 Skill 不再自带它们的副本（v7.3.2 去重）。

**必须遵循（Saul 2026-10-29）**：TikTok 固定适配（触摸、启动加载、激励广告、存档读值、适配层、图片、加桌面/回访、登录/App ID、胶囊/首页底排/不要 Credits）和跨游戏通用流程一律按 [TikTok 固定适配](references/tiktok-fixed-adaptation.md) 做（英化和重塑都适用，本页每条写了现在由哪个门禁拦、哪些仍是文档规则）；新游戏只用平台包标准件，不手写；旧游戏普通历史项沿用原警告政策，已报手机故障和本次命中的三种Cocos2启动不安全旧式不降为警告，由对应会话按真实原包闭环。

## 先定是哪一类游戏

**冷启动过渡须有有效覆盖**。首次或启动相关依赖变化时，用独立 Ego TaskSpace 对实际交付构建执行[冷启动到首页可操作的过渡检查](startup/references/cocos-loading-screen.md#每次交付必检冷启动到首页可操作用户-2026-11-07)。故意延迟首页必需素材，从导航前观察到首页就绪和真实触摸产生业务结果。已有且相关依赖未变的通过记录沿用；目标失败、未覆盖或证据无效时只处理对应目标。

**每次给测试包前必跑（用户 2026-11-05）**：无论新旧、外来包、同版重发、仅改名、没有重新构建，或用户只说“给我测试包”，先按[每次交付的分包体积复查](package-check/references/fresh-upload-size.md)重新读实际最终 ZIP 并生成本次新回执。此项不复用旧结论，不被启动/广告探针失败中断，也不受“局部修改只查改动”豁免。检查不过/未跑不交包；CRC/哈希正确不等于体积与分包正确。平台已拒绝的同字节包不能靠本地体积通过解封。

| 类型 | 判断 | 适用 |
|---|---|---|
| 英化 | 拿到的是能运行的中文完整游戏，只改中文美工/文字，加少量固定入口 | 下表“英化”列；默认不查关数、经济数值、皮肤、签到、教程等重塑专属项（Saul 要求创新玩法时，新加的部分要查） |
| 重塑 | 用启动包做的新游戏 | 全部检查 |

工程里写 `docs/board.txt`（`localize` 或 `remake`）；没写时按 [两个制作入口](../remake-core/references/two-boards.md) 判断。

## 三道关：哪一关在什么时候跑（用户 2026-10-28）

本 Skill 把所有检查放在一处，但**不是做完游戏才一次查完**。按制作阶段分三道关，前一关通过才进下一阶段，后面的关不重复前面已经查过的内容（详见 [检查分阶段](../remake-core/references/check-stages.md)）：

| 关 | 什么时候跑 | 查什么 | 不查什么 |
|---|---|---|---|
| 1. 设计关 | 玩法（占位图）做完、交用户确认玩法之前 | 玩法、关卡、经济、皮肤、模块，以及所有广告节点的位置与流程（复活、结算×2、局内道具/增益、礼包、看广告解锁）；`remake-core/scripts/design_check.py` | 美术 |
| 2. 美术关 | 美术做完、交用户试玩之前；之后改图只复查受影响整页、共享组件和相关状态 | 画面、按钮、图片字、穿模、暗区、清晰度；英化同时核对 Sprite 比例及实际导出的图集切片；`remake-core/scripts/art_check.py`、[art](../remake-art/SKILL.md) | 设计数值 |
| 3. 最终总检测 | 用户确认玩法和美术、锁定之后，出包之前 | 只查功能：能进、不卡加载、按钮有反应（含 TikTok 触摸坐标探针）、广告完成/取消/失败、存档、包体；`remake-core/scripts/check_known_issues.py`、`preflight.py`、`logic_check.py`，再出包与最终包检查 | 美术与设计沿用已通过的证据；核对证据和实际交付文件一致 |

美术制作及受影响页面的定点检查见[美术验收前移与试玩后锁定](../remake-art/references/art-before-trial.md)。用户已确认的游戏局部返工按本次依赖执行。写包按最终产物、平台和受影响功能的证据核对。

## 完整验收的执行顺序

首次完整验收与返修按[稳定候选上的检查调度](test/references/candidate-execution.md)执行：先处理源码预检、奖励消费者与声音控件的真实阻断，校准实际引擎和 adapter 的准备路径，集中修复后固定候选，再跑长矩阵。失败先区分产品、适配器、缺输入和运行身份；局部排查不冒充完整通过，writer 与本次最终 ZIP 体积门禁不减。已锁定美术只按实际变化处理，不因新构建号重开整套审美验收。

## 检查项与入口

| 检查 | 英化 | 重塑 | 入口 |
|---|---|---|---|
| 启动与稳定：进得去、加载页、Retry、存档 | 必查 | 必查 | [startup](startup/README.md) |
| 功能测试与修复：按钮、输入、胜负、重开、异步广告 | 必查 | 必查 | [test](test/README.md)；存档/领奖/签到日期等静态规则 `remake-core/scripts/logic_check.py`（`preflight.py` 的「逻辑检查」行） |
| 无中文残留、英文文案 | 必查 | 必查 | `remake-core/scripts/audit_english_coverage.py`、`audit_copy_quality.py` |
| 位图字只用于数字和符号；句子用真字体；字母大小写不串（禁止 HelP/TaP 这类） | 必查 | 必查 | `remake-core/scripts/audit_bitmap_letter_fonts.py`（美术关 `art_check.py` 已接入） |
| TikTok 触摸坐标：Cocos 2.x 包装好平台包 `touch-coordinates.js`，Cocos 3.x 包在引擎加载前给 `tt.onTouch*` 装好坐标修正，只给 screenX/screenY 也能点到原位（浏览器模拟测不出）；探针结果为空即失败 | 必查 | 必查 | `remake-core/scripts/audit_upload_startup.py`（触摸坐标探针：2.x `probe_cocos2_touch_coordinates.cjs`，3.x `probe_cocos3_touch_coordinates.cjs`）、平台包 `remake-core/assets/platform-kit/build-templates/bytedance/` |
| 设置里音效/BGM 两个音量分开可调且保存；有声音控件就必须真有音频文件、播放调用和引擎音频模块（「这轮没改声音」、老游戏、英化都不免查；review 不算通过；不适用只认 `docs/audio/silent_design.md` 且没有声音控件） | 必查 | 必查 | `package-check/scripts/audit_sound_settings.py`；源码阶段 `remake-core/scripts/audit_sound_settings_static.py`（`preflight.py` 的「声音设置」行，最终阶段 review 是需处理）；成品 `remake-core/scripts/package_gates/sound.py`（三个写包/检查入口都跑，S1–S4，见 [固定适配 10](references/tiktok-fixed-adaptation.md)） |
| 源码和上传包不带 `.git` / `.svn` / `.idea` 和账号密码（Saul 2026-11-04，91 SLS11 的 `.git` 里有开发者账号密码）：英化开工用 `unpack_source.py` 放源码，交源码用 `make_source_zip.py` | 必查 | 必查 | `remake-core/scripts/source_hygiene.py`；出包门禁 `package_gates/secrets.py`（H1/H2，三个入口都跑）；`prepare_delivery.py --source` |
| 删除分享、更多游戏、排行榜。把 `WxGameBox` 这类旧类换成空实现时，空实现的 `init(nodes)` 要把传进来的节点设成 `active = false`，不能什么都不做（v7.8，Holly's Hay Hop v1：旧类原本负责隐藏挂件，换成空类后局内一直显示「Try It」框） | 必查 | 必查 | `remake-core/scripts/audit_no_social_features.py`、[前置规则](../remake-core/references/no-social-features.md)；`preflight.py` 的「分享/排行榜」「互推」「分享换奖励」（`audit_share_entries.py`）行，`--stage final` 时「跳过」也算需处理；还显示着的退役槽位由写包入口必跑的运行时套件 `dead_shell`（VIS_DEAD_SHELL，[运行时回归](package-check/references/runtime-regression.md)）拦 |
| 个人主页侧栏回访、添加桌面 | 必查 | 必查 | 实际 Native 先查旧句残留，再跑 [`growth_entry`](package-check/references/runtime-regression.md)，验证冷启动、保活返回、到账与重复领取。历史包重出同样必查 |
| 结算页 Watch Ad x2 与 Retry；广告取消/失败不发奖、只用激励视频、无广告跳关 | 必查 | 必查 | `remake-core/scripts/audit_ad_binding.py`、`audit_no_ad_skip.py`、`audit_no_ad_simulator.py` |
| 美术检查（穿模、暗区、按钮覆盖、图片清晰度） | 只查改过的页面 | 必查 | [art](../remake-art/SKILL.md)、`remake-core/scripts/art_check.py` |
| 关卡、经济、皮肤、签到、教程、模块 | 默认不查；创新玩法新加的部分要查 | 必查 | `remake-core/scripts/audit_level_plan.py`、`audit_game_modules.py`、`audit_acquisition_progression.py` 等 |
| 出包与最终包检查 | 必查 | 必查 | [package](package/README.md)、[package-check](package-check/README.md) |
| 出包时的布局状态、按钮普查（v7.8，总表 B30，Saul 10-30 定必跑）：iPhone 14 和 SE、胶囊按点 / 按像素，查按钮伸出屏幕、压胶囊、压底部横条、被 3D 盖住、胶囊单位一变就移位、开局下载超过 10 MiB 或带声音；首页每个按钮和一层弹窗按钮真点一次，没反应就拦。首页规则：重塑查设置在左上、最下面一排只放主页回访和加桌面；首次英化主页按[默认主页排版](../remake-art/references/english-home-layout.md)由美工 Skill 重新设计，检查两个平台入口及本次重排控件在首页可见、能点、不重叠；已交付后的局部返工只查受影响区域。新游戏拦、老游戏只警告；3.x 只有开局下载会拦 | 必查 | 必查 | 写包入口自动跑（运行时套件 `layout_state`、`button_sweep`，[运行时回归](package-check/references/runtime-regression.md)），每款多 6～10 分钟；要测「展台上有车」这类首页一层点不到的状态，在 adapter 写 `layout_states`。顶栏、设置钮贴着胶囊放的，用平台包 `parts/CapsuleLayout.js` 读胶囊位置 |
| 正常游玩手感 | 按实际玩法核输入、运动和流畅度 | 同左 | 怀疑帧率相关时显式运行 `frame_rate` 对照诊断，5% 只提示位移差，默认终检和出包不跑 |
| 出包流程（v7.8，总表 B32）：出包后同款旧包连同回执挪进「旧包/」，交付文件夹只留这一个包和「最新.txt」（上传用哪个包、sha256、时间）；检查用的工具不是安装版（自己复制改过的）报「改过的工具」并写反馈草稿到 ！Skill更新/；Saul 改了设计、旧问题的用例不再适用时，按新设计登记新问题再用 `package_issue_gate.py supersede` 作废旧的（要 Saul 原话、日期、新问题编号）；旧笔记里的 `cocos-game-check/core/scripts/<脚本>.py` 转到 `remake-core/scripts/` | 自动 | 自动 | 两个写包入口自动挪包、写 最新.txt（不想挪加 `--keep-old-packages`）；`check_package` 报告的 `modified_tools`；作废见 [已报告问题](package-check/references/resource-and-reported-issues.md)「按新设计作废旧问题」 |
| 障碍不许在屏幕里凭空出现、消失、瞬移（v7.8，总表 P2 补）：四种屏幕（390×844、375×667、768×1024、1115×791）上主角无敌飞 18 秒，带碰撞体的障碍在看得见的地方新出现、消失、一帧跳 40 以上就拦。新游戏拦、老游戏只警告；3.x 只警告「未覆盖」 | 必查 | 必查 | 写包入口自动跑（运行时套件 `popin`）；adapter 要写 `popin` 块（主角、无敌、游戏节点），没有滚动障碍的写 `{"n/a": "原因"}`。跑酷、飞行类用平台包 `parts/CourseLane.js` 算出生、回收和复活清障 |
| 看广告入口真点（局内广告复活在首轮人工试玩）、试玩链接点看广告 | 有 adapter `ad_entries` 时必查；给 Saul 试玩链接前必查 | 同左 | 运行时套件 `ad_entries`（只执行适用的自动广告入口）；`serve_preview.py --keep` 给链接前自动跑 `trial_link`（模拟广告窗要在最上层、点「看完」游戏要变），不过就不给链接，也能 `runtime_regression.py trial --url <链接>` 手动跑 |
| 评审别人的游戏（只检测不修改） | 可用 | 可用 | [review](review/README.md) |

引擎：重塑固定 Cocos Creator 2.4.15 与平台包；英化保持原游戏的引擎版本。v7.7 起出包时由 `tiktok_finalize` 把平台包标准件装进英化工程（2.4.x 和 3.x 都装，见 [TikTok 固定适配·出包时怎么装](references/tiktok-fixed-adaptation.md)）；换成平台包 `main.js` 只在清单 `startup24` 列出的引擎版本上做（2.4.4、2.4.6、2.4.13、2.4.15；其他 2.4 版本保留自己的 `main.js`，触摸和存档两行插进 `game.js`）。平台包工程检查（`remake-core/scripts/audit_platform_kit_required.py`，内含 `check_kit_project.py`）按实际构建用的 Creator 版本判断：2.x 重塑工程用本机 2.4.15 构建，要求 `build-templates/bytedance/` 带平台包 `main.js` 和 `touch-coordinates.js`；英化工程（`.tiktok-kit/policy.json` 的 board 是 `localize`，或有 `docs/english/`）不查构建模板，改查源码段记录是否新鲜（和写包入口的 K5 同一个检查）。试玩前跑 `tiktok_finalize.py source`，最终预检核对该记录。

## 模拟测试逐按钮必检（用户 2026-11-03）

模拟功能验收必须先按实际画面盘点，再逐个实点并验证业务结果；只有 Sprite、没有点击绑定的按钮样式区域也须纳入。完整验收覆盖实际存在的页面与条件状态，局部修复覆盖受影响页面和状态；同版有效证据可复用。漏测、受限、无响应不得写“所有按钮通过”。执行时必读[逐按钮覆盖规则](test/references/button-interaction-coverage.md)，报告应测、实点、复用、失败和未测数量；button_sweep 的 passed 不能代替此项验收。

英化复合控件有历史漏检时，制作方提供目标槽、状态、正常参考和原问题图；在正式试玩前按[局部 UI 契约](../remake-art/references/local-ui-contract.md)调用 art_check 的局部入口，使用 pixel_reference 或 pixel_regions 校准按钮占用、文字分区和角标可见性；素材切片另走源图检查。记录具体声明和跑到的状态。

凡新增或改动图标＋文字按钮、海报说明条、长正文和奖励计数，按[图文内区检查](../remake-art/references/local-ui-contract.md)登记受影响状态。试玩前普通 art_check 读取 docs/art/visual-slots.json；逐项核对实际截图，原料切对、语义绑定和运行布局分别验。

有按钮文字穿框反馈时，为当前模板的每个可见实例分别记录词尾留白、图标间距和内容可见性。执行[按钮内框验收](../remake-art/references/local-ui-contract.md#按钮内框验收)，原问题图能报错、正常按钮能通过后，再核本次构建的实际画面。

## 规则

- **TikTok 与 Cocos 的触摸差别（用户 2026-10-28，最严重的一类“点不动”）**：Cocos Creator 2.4 的触摸转换（`getTouchesByEvent`）读触点的 `clientX/clientY`，TikTok 运行环境给的触点只有 `screenX/screenY`，算出的坐标是无效值，扫码后按钮点不动、常卡在首页。浏览器手机模拟会给 `clientX`，**测不出这个问题**。所以每个 Cocos 2.x 的 TikTok 包都必须带平台包的 `touch-coordinates.js`（v7.7 起由写包入口里的 `tiktok_finalize` 自动装上：产物 `main.js` 是平台包 `main.js` 时由它加载，否则在 `game.js` 里插一行；不要自写 patch_build 替代，见 [TikTok 固定适配·出包时怎么装](references/tiktok-fixed-adaptation.md)），并通过 `remake-core/scripts/audit_upload_startup.py` 里的触摸坐标探针（`probe_cocos2_touch_coordinates.cjs`，对打包产物真实执行，只给 screenX/screenY 也要得到有效坐标）。探针不过不出包。**Cocos 3.x 包同样必查（v7.4，Marlows r4 漏过）**：3.x 的小游戏触摸输入同样读 `clientX/clientY`，缺字段时引擎的 Vec2 把 NaN 变成 0，点哪里都落在左下角 (0,0)。`audit_upload_startup.py` 对 `web-adapter.js` + `cocos-js/` 的包运行 `probe_cocos3_touch_coordinates.cjs`：真实执行包里的 `game.js` → `web-adapter.js`（以及引擎加载前 require 的修正模块，如 `marlow-touch.js`、`grotto-touch.js`），触点只带 `identifier/screenX/screenY/force`，再走引擎自己的 SDK 拷贝和触摸回调；引擎收到的坐标必须是有限值、在屏幕内、并且落在点按的位置上才算通过。修正要在引擎加载（`System.warmup`/`System.import`）之前装到 `tt.onTouch*` 上。**探针结果为空（`touch_coordinates: null`）不算通过**：TikTok 的 Cocos 2.x/3.x 包认不出引擎触摸转换时直接失败，并写明原因。

- 本 Skill 只检查和修检查出的 bug；美术、玩法、经济的设计改动交给对应制作 Skill，英化美工只在用户点名时才做。
- 结果写在工程 `docs/`；失败如实保留，不改阈值、不改检查器替游戏过检。
- 共用功能（广告、存档、Retry）只测一次，不乘到每关。
- 浏览器与触屏测试用同包的 `chrome-mobile-testing`、`mobile-touch-computer-use`、`ego-browser`。

局内广告复活按[首轮人工试玩清单](../remake-core/references/manual-visual-review.md#首轮人工试玩的局内广告复活)执行；状态契约用于制作与已报问题定位，不作为最终自动回归或出包门禁。
