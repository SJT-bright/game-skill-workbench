---
name: cocos-game-to-english
description: "英化（触发词：英化、英化skill、中文源码、翻译成英文、英化这个游戏、整改侧栏、整改侧边栏）。已交付旧游戏要求整改侧栏时，按局部维护统一处理去游戏名、侧栏布局、主页回访和添加桌面。拿到能运行的中文Cocos完整游戏时用：开工核中文原版的内部基线；把中文美工和文字改成英文（第一轮按美工板块 remake-art 照原画风重新生成所有按钮和文字）；由美工 Skill 默认重新设计英化主页排版，补齐固定入口（个人主页回访、添加桌面、音效/BGM音量、关内暂停键、结算页看广告双倍与Retry、看广告复活），删除分享/更多游戏/联网排行榜；看广告的几项按包里的 remake-ads、remake-economy 做，看广告的板块由同包ad-boost按六标准类全部补齐，制作前联动美工，不问已定系统；先完成操作测速、倍速连续游玩、美工与中文专项检查，再给左侧同版试玩、右侧清单的 H5；Saul 试玩没问题后核对覆盖、只补缺项并出包；也接收已完成源码和测试包，沿用可核验记录；macOS、Windows 都能用；手动检查使用 Computer Use + Edge，自动回归使用 Ego，Chrome 只在美工试玩和最终测试包交接时打开。默认保留核心玩法与关卡；六标准广告所需的皮肤、体力、道具、主页组合和周期试用依赖必须补齐。"
---

**首轮试玩前完成连续游玩（用户 2026-11-12）**。每款游戏按[操作测速与倍速连续游玩](../cocos-game-check/test/references/pretrial-continuous-play.md)先测实际操作的持续速度，建立原速完整路线基准，再匹配本作稳定倍速并完成连续游玩及免费重开。第 3 阶段在同版候选上完成并核对原始观测后才交首个正式英文试玩；第 5 阶段沿用有效证据并补真实缺项。倍率、时长和覆盖指标由本作实测确定。


**六标准广告节点与美工制作已接入（用户2026-11-11）**。首次完整制作与明确的六类迁移，结束、主页、永久皮肤、体力、局内道具、周期试用六类全部必需；额外奖励循环不能替代任何一类。按[六标准广告制作联动](../remake-core/references/ad-standard-six.md)在制作时调用同包ad-boost与remake-art。旧“0～2个才推荐/无系统不新增/英化默认不加这些系统”不再限制这六类所需依赖。已交付游戏的无关局部维护保留原授权范围和有效记录，不自动改原件。


**英化主页默认重新设计排版（用户 2026-11-10）**。首次制作主页前加载 [美工 Skill](../remake-art/SKILL.md)，按[原画风主页排版](../remake-art/references/english-home-layout.md)统一规划主操作、资源栏、新旧功能入口和英文空间，再接入素材。已交付后的无关局部返工不追溯重做主页；只维护 Skill 时不自动改已有游戏。

**跨视口玩法（2026-11-11）**。首次英化适配及玩法空间、坐标、运动/碰撞或操作锁受影响时，按[坐标与完成结果](../remake-core/references/viewport-gameplay.md)实施。并入现有核心操作和第二比例检查，沿用有效证据及本轮免验范围，不因本条扩展无关返工或新增一轮验收。

**返工写包与修复续跑（2026-11-10）**。本轮要求检查或交付游戏时，按[执行范围计划及修复续跑](../remake-core/references/regression-scope-gate.md)核对实际改动与可沿用证据。遇到漏传计划、整包通配、执行中换计划、执行器粒度过粗或最终交付回执缺失、失配时，当前 AI 直接修复具体缺口，重新核准后回到原节点，继续到已授权的检查与交付完成。有效证据直接沿用，新检查限于实际受影响或确实缺证的项目。只讨论流程或更新 Skill 时，完成讨论和规则更新即可，游戏案例用于说明。

**局部修复继续执行（2026-11-12）**。按共享[门禁调度与恢复路径](../remake-core/references/regression-scope-gate.md)处理漏计划、整包通配、混合用例和失配回执。机器能核准的计划绑定直接恢复；需判断代码依赖时由当前 AI 修好并通过 `resume_scoped_step` 回到原正式入口。修复只能沿用或执行原授权中的具体项目，`repair_required`、`plan_ready` 和 `resumed` 都不能作为停止交付的完成状态。只维护 Skill 的任务不启动游戏。

**当前检查执行规则（用户 2026-11-08）**：先读[一次通过、按改动复验](../remake-core/references/incremental-checks.md)。图片、文字/字幕、音效、玩法、关卡、平台检查均按命名节点留存真实记录；已通过且依赖未变的项禁止重复执行，代码或配置变化也不触发全量。浏览器和写包读取同一计划；旧文中的“每次必跑/全量检查”改按完整覆盖核对解释。最终 ZIP 的本次体积与分包核对按用户单独要求保留。

**完整美术回执已撤销（用户 2026-11-08）**。美术制作和实际画面问题按首次制作或受影响的节点处理，保留各项实际结果。常规与轻量写包、正式试玩、最终交付均不得生成、补齐、更新或要求完整美术回执，也不以全量图片复核或截图汇总作为替代条件。已通过的游戏局部返工只检查该改动影响的节点。**保留的三条轻量保障（11.17.14）**：① 首轮正式英文试玩前要有一次完整 `art_check.py` 运行记录（`.tiktok-kit/art-check-record.json`，不绑图片指纹，之后小改不用重跑，最近一次运行有需处理项时先修这些行）；② 两个写包入口只读包内字节，查英化新做的图不超过 800 KB（`docs/english/pre-english-images.json` 里的中文原图不查）；③ 首次英化的人工画面清单并入 Saul“试玩没问题”这一步，返工时清单只是可选快看。最终 ZIP 分包、体积、配置和同版链接核对按原规则执行。

**人工画面检查（用户 2026-11-08）**。正式英文试玩和测试包随[同页试玩 H5](references/playtest-h5.md)交接，左侧同版游戏，右侧逐页清单。从[人工试玩画面清单](../remake-core/references/manual-visual-review.md)挑本轮适用项目。常规美工、启动计时及写包取消默认录屏和 AI 总览图签收，偶发问题按需短录。原资源中文专项、技术检查和版本核对按对应规则执行。

已交付后用户指定改完即出包时，按[返工交付与人工快查](../remake-core/references/returned-art-delivery.md)处理这次改动，实际记录与用户验收分开。


> 2026-11-01 用户更新：Grok 图片识别已停用。本文任何 Grok 读图、OCR、截图转录或 `grok-image-review` 路由均失效；所有读图由 Codex 自己直接查看并完成。文本搬取等非图片任务按各自规则执行。

# 英化（独立流程）

**持续做到当前交付节点（用户 2026-11-11）**。先按[失败后的修复与续跑](references/delivery-continuation.md)确定本轮完成条件。构建完成、ZIP 尚未生成、写包拒绝或预览未就绪时，当前 AI 报告节点及实耗后继续定位、修复和定点补验，直到已授权的同版交付完成。有效旧记录沿用，真实变化按独立节点核准。

## 整改侧栏的快捷入口（用户 2026-11-10）

用户说“用最新版 Skill 整改侧栏”“整改侧边栏”或同义请求时，先执行[旧游戏侧栏局部整改](references/sidebar-retrofit.md)。这句话同时授权去游戏名、侧栏布局、个人主页回访和桌面快捷方式四项整改，适用于旧游戏与遗留工程。按实际改动及共享依赖复验，沿用其余有效记录；完成四项后继续同版交付。

## 浏览器测试路线与两次用户交接

英化人工操作用 **Computer Use + Edge**。自动检查仍在 **Ego Lite** 独立 TaskSpace 执行原有脚本并复用有效证据。英化的 Google Chrome 只在美工试玩和最终测试包交接时打开。详见[浏览器测试规则](../remake-core/references/browser-testing-policy.md)及[试玩交接](references/preview-handoff.md)。

修订：`2026-11-12.english-simple.11.17.28`（合入规则口径统一、存档不挡启动与四样交付，补齐制作期存档消费者预防；保留局部复验和阶段计时。历次改动见[版本历史](版本历史.md)。）

在新电脑上使用本包时，先核对该机的依赖和 Cocos 版本。共享检查依据用项目相对路径和内容指纹，试玩链接在接收电脑重新绑定。跨机 H5 使用[转发清单](references/playtest-h5.md#换电脑接手)。

共用功能验收与故障复验按[实际触发与玩家结果](../cocos-game-check/test/README.md)选测。

**减少美工返工（11.17.5）**：开工先按[采集清单审查](../remake-art/references/art-iteration-workflow.md#开工先审采集清单)定下独立画面状态、可合并项和可沿用项，再开始首轮采集。第 2 / 4 阶段按[少返工的制作与采集](../remake-art/references/art-iteration-workflow.md)盘点共享用途、定 CSS / 字体预算，显式选首件整页检查后再铺同类；每批结束或失败时按工具计划分清原料、接入、构建与采集原因。同因修正合批，保持有效轮次，连续采新截图；旧图沿用仍由原采集门禁决定。只做美工，不扩大玩法；首次试玩前按范围核对美术，后续只复验受影响的项目。

**美工制作即检查（11.17.2）**：第 2 / 4 阶段按[制作与检测共用证据](../remake-art/references/production-check-link.md)执行。固定按钮和切片由生成工具登记约束，第一件接入即调用原图文/像素检查；第 3 阶段复用输入与规则均未变化的计算。首件在制作节点完成，中文专项仍随正式试玩候选执行。

**独立图标防放大（11.17.4）**：视频图标、勾、乘号、关闭符号和图文按钮在制作前明确角色与显示槽，首次接入按[独立显示预算](../remake-art/references/local-ui-contract.md#高清图标接入时锁定独立显示预算)登记受影响视口；源 PNG 分辨率不作显示尺寸。图标位置与文字净空以真实 Art 底板为准，尺寸正常不能代替内框和图文间隔通过。使用 ad-boost 面板时先执行[模板显示槽规则](../ad-boost/references/art-display-slots.md)，批量生图前运行调用集回归；不能把乘号当作勾、把烘焙在图里的图标再叠一份。

**每次给测试包都复查分包体积（用户 2026-11-05）**：新旧、外来、同版重发、仅改名或用户仅索取已有文件均不豁免；交最终 ZIP 前按[统一检查的本次体积复查](../cocos-game-check/package-check/references/fresh-upload-size.md)重新读最终文件并生成新回执。不复用旧体积结果，不以 CRC/哈希或 Web 可玩替代；局部返工只查改动也不能跳过本项。失败/未跑不交包，已被平台拒绝的同字节 ZIP 不得原样重发。

**新增界面先走美工 Skill（用户 2026-11-10）**。英化内的默认补齐、试玩后加功能和直接调用其他板块，只要新增玩家可见的页面、弹窗、子面板、入口按钮，或为新功能重建既有面板，就在功能排布、选素材和出图前加载[美工 Skill](../remake-art/SKILL.md)并执行[新增界面制作](../remake-art/references/new-feature-ui.md)。先按原游戏画风确定每个新界面的底板、字图、图标、控件和布局，首件接入后在真实页面按原美工规则定点核对。用已有制作与采集记录；没改的原界面按原英化规则处理。

**美工检查与出包衔接**。第 2 / 4 阶段先在实际页面核代表件并登记素材、共享用途和应查状态。第 3 阶段核首次制作或实际改动涉及的画面、Sprite 比例和切片。第 5 阶段查实际包内资源、候选身份及适用的功能和平台项。每段的输入和证据按[美术验收前移与试玩后锁定](../remake-art/references/art-before-trial.md)衔接。

上一修订：`2026-11-01.english-simple.11`（简化.11：①每次给英文试玩链接前先过中文专项检查 `chinese_audit.py`：全部资源列清单，每张图和每个图集切片逐个识字，复核结论要带证据文件并按 sha 绑定，过没过由 check 自己算；英化入口的 `serve_preview.py` 没过就不起英文试玩链接，Saul 2026-11-01（这也太牛了的 highwave 图集切片里还有「高波来袭！」）；②重做美术的小样补三点：真页面上挑、先过美术检查、挑一次定死（Saul 2026-11-01「把这三点补进v7.9一起改」）；③交付回复原样转手机问题的结论（问题门禁 `device_issues`）；④创新玩法新加的部分在第 5 阶段查；两包共用的检查、货币板块和本包带的 ad-boost 改了什么见包根目录 README；以前各版见 [版本历史.md](版本历史.md)）。

英化和重塑是两条独立的路：英化默认只用本包（本包带广告 remake-ads、货币 remake-economy、皮肤 remake-skins 三个板块和广告加量 ad-boost）；Saul 要求创新玩法时，新加的部分用这三个板块和重塑包里的关卡、引导板块（见下面「创新玩法」）。

## 分数与奖励的制作及交付硬约束（score-reward-1，2026-11-04）

第一轮先做实际失败结算与奖励行代表样：`SCORE` / `REWARD` 固定词用整词图片，实时数量用生成的位图数字。不能通过 `EnglishUI.label(..., 'Score '+value, ...)`、TTF 描边或把数值登记为 runtime-text 来替代。按原画风制作，保留真实数据绑定。

写英文后运行 `fit_english_labels.py`，其源码预查现在同时拦普通字体数值。脚本动态创建的界面必须实际打开；首件接入立即采集同帧 dump 和截图，执行 `python <skills>/remake-core/scripts/audit_value_presentation.py --project <工程> --dumps <本轮首件采集目录>`，非零不得批量复制该模板。肉眼观感随同版试玩核对。固定词、图标、数量各占一槽，移除重复旧字层；用真实字宽布局，在 `docs/art/longest-text.json` 的 `labels` 中按节点路径记录最长合法显示值（`path`、`text`），实际显示该值复查。成功、失败、奖励初开及重开、两种手机比例在既有页面清单中覆盖。

首次英化在制作阶段完成适用的画面技术检查。已有通过项按真实输入沿用，后续只核需要修改的具体显示问题。

## 两个输入入口

开工写入 `docs/checks/workflow.json` 的 route：`source`＝中文源码 ZIP 从零英化；`handoff`＝已经按同 Skill 完成的源码 ZIP＋TikTok 测试 ZIP。后者先核身份并恢复可验证的逐项记录，不重走中文原版试玩和制作。两条路使用同一本检查记录；细节见[逐项记录与执行](../remake-core/references/incremental-checks.md)。安全解包沿用现有工具。先读项目 Creator 版本，再选相匹配的引擎，禁止用 2.x 打开 3.x 工程。中文原版用 Chrome 交用户试玩，不反复留在 AI 测试浏览器里。

## 一屏看懂（先读这个）

拿到中文 Cocos 完整游戏，按五步走：

- ① 盘点：拿到的源码或包先跑 `python3 <skills>/remake-core/scripts/which_package.py --project <工程或包> --roots <游戏文件夹> --roots <工作区里放这款游戏的文件夹>`（按字节和 Cocos 资源 uuid 找同一款游戏的全部包）；它说「放在 N 个地方 / 可能有两条以上的版本线」时，先用一句话问 Saul 在哪条线上接着做，不要另起一条（音乐消消乐 11-05：Kiro、Codex 各从 v29b 做到 v30、v31、v32，修过的问题互相没带上）。中文源码用 `unpack_source.py` 放进工作目录（不带 .git，Saul 2026-11-04）；先查电脑（`check_machine.py`，见「换电脑也能用」），再给 Saul 中文原版的试玩链接，不等回复；接着写新游戏标记、列清单。
- ② 修改：做下面「只做这几件事」的 9 项。第一轮美工照原画风重新生成所有按钮和文字，第一个英文链接前完成实际可见的全部中文图文及相应美术覆盖，已通过项直接沿用；第 8 项 ad-boost 按诊断完成本轮计划的接入和美工；全部新增界面在设计前走[新增界面制作](../remake-art/references/new-feature-ui.md)。
- ③ 英文试玩链接：按第 3 阶段完成美工和 `chinese_audit.py` 中文专项检查，在同版候选完成操作测速、倍速匹配、原速与倍速完整连续游玩及免费重开，核对实际结果和运行错误。候选已构建、检查有待处理项、入口启动失败都属于进行中。用过程消息报节点与实耗，报完立即按[首轮试玩修复](references/first-trial-repair.md)核实、修正和定点补验。继续到同版 Native 试玩实际可打开，检查通过才发同版正式链接。交同页试玩 H5 和阶段用时。交付前只有用户明确暂停、取消或确有只能由用户补齐的输入时才结束执行。 启动与操作需能进首页、能开始一局且无卡死，观察并入本轮连续游玩。
- ④ 试玩改进：修反馈时只核受影响的页面、共享素材和功能。中文专项检查只识新加和改过的图。同版候选留在内部，用 Computer Use 操作 Edge 核实，聊天报告问题、结果和实耗。
- ⑤ 补缺与出包：Saul 说没问题后核对适用项覆盖，只执行缺项及真实改动项，用写包入口出包。测试包交了以后再改（返工），只查改到的部分，不从头再查（见第 5 阶段「出包后返工」）。

每一步的细节在下面「阶段」一节；要读哪些文件见「读哪些文件」。每个命名节点开始、完成、失败或变更范围时均报告当前动作、执行或沿用、实耗、结果和下一节点；每阶段结束汇总用时，见「用时汇报」。

**必须遵循（Saul 2026-10-29）**：TikTok 固定适配（触摸、启动加载、激励广告、存档读值、适配层、图片、加桌面/回访、登录/App ID、胶囊/首页底排/不要 Credits）和跨游戏通用流程一律按 [TikTok 固定适配](../cocos-game-check/references/tiktok-fixed-adaptation.md) 做：英化一律加看广告复活，核心玩法里的分享奖励改激励视频、其他分享入口删掉，加桌面/回访奖励各 5B；新游戏只用平台包标准件，不手写；旧游戏只给警告，由各自会话处理。

拿到的是一个能运行的完整游戏。默认保留原工程、原玩法、原关卡、原画风、原声音和存档；不补原玩法关卡；广告六标准类的经济花处、皮肤、体力、道具、礼盒、转盘、签到与试用按新固定范围补齐，其他新系统仍按当前授权。六标准类所需的皮肤与货币规则由同包 remake-skins、remake-economy 主动联动；关卡与引导板块仅在当前任务确实涉及它们时调用。广告及其新增依赖按六类计划处理，其他原游戏价格和数值保持原范围。第 4 阶段 Saul 试玩时点名要改的玩法、手感、难度和数值，照他说的改，只改他点名的。

**创新玩法（Saul 2026-10-30）**：Saul 要求给英化游戏加新玩法时，算单独任务。新加的部分用现成的板块做：广告 remake-ads、货币 remake-economy、皮肤 [remake-skins](../remake-skins/SKILL.md)（本包自带；皮肤一定连着货币和广告，新加皮肤就要同时有货币、看广告解锁款和看广告试用弹窗，Saul 2026-11-04）；关卡 remake-levels、引导 remake-onboarding（在重塑包里；只装了英化包的电脑要先装重塑包）。不另写一套，这样不容易出新 bug，做过的也能复用。只做 Saul 点名的部分，原有玩法照旧不动；加关在关卡表写 `explicit_total`，新加的部分照对应板块的检查查，在对应制作节点检查一次，第 5 阶段核对其有效记录；新加部分的界面设计先走[美工 Skill 的新增界面制作](../remake-art/references/new-feature-ui.md)，接入的实景结果供第 3 阶段沿用；新增功能先按[前期预防](references/early-prevention.md)做局部验证，玩法、经济等检查随对应制作节点完成，第 5 阶段只补缺和核对已通过记录。

## 换电脑也能用（10.2.10，Saul 2026-10-31）

英化包供 macOS 和 Windows 使用。开工先检查本机依赖。没有可用的 Ego Lite 时，浏览器相关项目记为未测，离线检查可继续。

- **「Saul」是谁**：本包写的「Saul」指正在用这个 Skill 的人（给你游戏、试玩、做决定的那个人）。「Saul 定的」规则照样遵守；回复照样用大白话，要他定的只出选择题，跑命令、找路径、装东西都由你来做。
- **开工先查电脑**：第 1 阶段第一件事跑 `python3 <skills>/cocos-game-to-english/scripts/check_machine.py --project <中文原工程>`，一分钟内查完 Python、Pillow、numpy、ffmpeg、Node.js、出包检查用的浏览器和这款游戏的 Cocos Creator。缺必须的，用大白话告诉用户缺什么、影响哪一步，问一句能不能装；同意后由你来装，装好再跑一次。缺的东西不影响的步骤先接着做。它打印的第一行「引擎路线」不是「照常开工」时，先照它做（2.0～2.3 复制一份副本升到 2.4.15；3.0～3.5 先装同一小版本的 Creator 导出原版），零件只装它列出的那些，再做别的。它报「Cocos 编辑器配置能解析」不通过时，先关 Creator，把报出的文件改名备份，再开 Creator。
- **Cocos Creator**：不假设装在哪。用 `find_creator.py --project <工程>` 找本机的编辑器、拿 2.x/3.x 对应的构建命令；构建前跑 `find_creator.py --busy`（整台电脑同时只跑一个构建）；3.x 的 web-mobile 导出缺 `index.html` 时跑 `fix_web_entry_3x.py --export <导出> --project <工程>`。没装工程那个版本怎么办、各版本的已知问题，见 [Cocos Creator 版本和已知问题](references/local-creator-versions.md)。
- **浏览器**：手动点检把候选的本地地址交给 Computer Use 在 Edge 的测试页打开。结构化脚本和机器取证继续用 `python3 <skills>/cocos-game-to-english/scripts/browser_env.py -- <命令>`。它们复用现有隔离 Ego 会话。需要用户窗口时按[试玩交接](references/preview-handoff.md)运行放行入口。
- **自己看画面**：手动确认首页、开始一局及反馈修复用 Computer Use + Edge，复用同一候选和状态。已有适用的同版截图和节点证据直接读取。当前工具没有 Edge 操作能力时把该项记为未测，继续可执行的脚本检查。
- **Windows**：`python3` 写成 `python`（或 `py -3`）；路径有空格或中文时整段加引号。本包和 ad-boost 里 macOS 才有的写法换掉：`pgrep` 用 `find_creator.py --busy`；`/usr/bin/python3` 用 `python`；`cp -c`（macOS 的快速复制）用普通复制；`open -R`（在访达里选中文件）改成直接给完整路径；构建卡住时加的 `--no-sandbox --disable-gpu-sandbox --disable-gpu` 是 macOS 的写法，Windows 先不加。
- **浏览器卡住和构建沙箱**：浏览器命令可用 `browser_env.py --game <游戏名> --report <文件> -- <命令>` 记录路线。Ego 卡住时保留首个错误，在 Ego 内排查；不能自动换 Chrome。构建前先跑 `find_creator.py --preflight`，退出 3 就别构建、也别重试，换不受沙箱限制的终端；构建命令照 find_creator 打印的原样用（TikTok 那条前后各带一次 sync，sync 没过不构建；3.x 出包命令带 `configPath=docs/startup/build-config-3x.json`），别删末尾三个参数，也别只复制 Creator 那半条。
- **试玩链接打不开窗口**：正式交接入口报告 Chrome 的实际启动请求。服务已通过同版读回但 Chrome 启动失败时，随该次交接附已核准的地址并说明窗口状态。
- **没有生图工具**：有核准整词字图和同款无字底时，用[固定英文按钮生成器](../remake-art/references/fixed-caption-button.md)。其余缺图登记到 `docs/english/art-todo.json`，完成可独立推进的工作。素材补齐并通过美工与中文专项后发正式英文试玩。
- **看图与识字**：Codex 直接看原图和实际页面，OCR 辅助定位待复核内容。
- **识字工具**（中文专项检查用，第 3 阶段）：macOS 用系统自带的 Vision（`chinese_audit.py` 第一次用时自己编译 `ocr_vision.swift`，要有 Xcode 命令行工具里的 `swift`）；Windows 用系统 OCR（要装中文 OCR 语言；这条路还没在 Windows 上试过）；装了中文语言包（chi_sim）的 tesseract 也行。都没有时 `scan` 照样跑完，每张图、每个切片都进「要复核」：用 `sheet` 拼出的复核图自己逐项看，带着复核图写结论，不能当成没有字。
- **只在 Saul 电脑上有的路径**：`！游戏学习库/`、`！Skill更新/`、`~/Downloads/！自制游戏/` 这类只是来由和证据的出处，别的电脑上没有，找不到就跳过，不影响做游戏。

## 读哪些文件（只读要用的，10.2.8）

2026-10-30 那批英化游戏，每个线程开工都整页读一遍 TikTok 固定适配，好几个线程还照着美工板块、共享库里「交试玩前做完」的旧说法多做检查。开工和每个子进程都按下面读：

- **主线程开工**：本页，加[固定入口](references/fixed-entries.md)和[Cocos Creator 版本和已知问题](references/local-creator-versions.md)。
- **[TikTok 固定适配](../cocos-game-check/references/tiktok-fixed-adaptation.md)**（约 98 KB，必须遵循）：开工读这几节就够，约 30 KB：[已定口径](../cocos-game-check/references/tiktok-fixed-adaptation.md#已定口径不再让模型临场决定)；「第二部分：跨游戏通用流程」8 条（存档写入、复活和 x2、弹窗布局、源码和包对不上、英化固定清理、读包内文件、图片卡住、玩法状态）；第一部分第 9 条（胶囊、首页底排、不要 Credits）；最后的「第三部分」「第四部分：不要做」。「出包时怎么装」（约 29 KB）到第 5 阶段出包前再读。第一部分其余几条（触摸、启动加载、广告计时、存档读值、适配层、图片、加桌面/回访 SDK、登录/App ID、声音）是出包入口自动装上、门禁自动查的标准件，不用手写，门禁报到哪一条再读那一条。游戏在遗留名单上时读「新游戏和旧游戏」。这页照样必须遵循，只是不用开工就整页读。
- **第一轮美工**：[美工 Skill](../remake-art/SKILL.md) 开头的英化包说明、[Saul 的美术禁区与必做项](../remake-art/references/saul-art-rules.md)、[英文界面重建](references/english-ui-rebuild.md)。
- **看广告**：下面「看广告」一节列出的那几页；第 8 项读 [ad-boost](../ad-boost/SKILL.md) 和要加的那几个板块的 `modules/<板块>/README.md`。
- **第 5 阶段**：[统一检查](../cocos-game-check/SKILL.md)的「英化」一列，和门禁报出来的那几条。
- **按需读**：六标准类需要永久皮肤时必须读本包 remake-skins；六类之外的关卡、引导板块按创新玩法的实际范围读；`remake-core/references/` 里的总规则（检查报错指过去时只读那一页）；ad-boost 没加的板块。
- **子进程**（见「并行分工」）：美术只读第一轮美工那三页；代码只读固定入口、[平台包接入说明](../remake-core/assets/platform-kit/README_接入说明.md)、「看广告」一节和 TikTok 固定适配第二部分；文字只读英文界面重建和商标词表 `remake-core/assets/trademark-words.json`。主线程派活时把要用的一两条规则贴进去，子进程不整页读 TikTok 固定适配。

## 只做这几件事

下表是功能目录，不按第 1～8 项串行施工。首次完整制作按[依赖顺序](../remake-core/references/production-plan.md#英化制作的依赖顺序)先盘点并规划全部六类广告和新增页面，加载美工定槽位后统一制作；已有合格局部返工沿原范围。

逐项判断这个游戏要不要做；不需要做的写一句原因跳过。

| # | 做什么 | 说明 |
|---|---|---|
| 1 | 中文改英文 | 代码字符串、Label、平台文案改成自然英文；中文图片字和带字的按钮第一轮就按[美工 Skill](../remake-art/SKILL.md)照原画风重新生成英文版（材质、字形和色系跟原画风一致，主页尺寸和位置按本轮设计安排，见第 2 阶段「第一轮美工」），换字体并确认放得下。**句子（说明、教学、提示，两个以上单词）用真正的英文字体（TTF），不许用生成的字母图集拼句子**——那样小写会被画成大写，出现 HelP/TaP/Pond；图片字只用于固定短词和数字。**等级、关卡号、分数、货币、奖励数（Saul 2026-10-30："这种是所有游戏都需要进行的"）**：原版不管是图片字还是普通字，英化后一律按原画风做成"图片字的词（LEVEL、货币名）＋生成的 0-9 位图数字＋货币图标"，不能是一整行英文普通字（反例："LEVEL 1 • +10 PEARLS" 白字压在半透明色条上）；数字后面也不铺纯色色条。`art_check.py` 的 `font_number`、`font_value_label`、`flat_value_plate` 在英化游戏同样拦，登记成运行时文字也不豁免。设置页不显示版本号和 Credits（`dev_info_text`）。**品牌车名、动漫角色名不直译**（v7.8 E8：「法拉利458」不写 Ferrari 458，写 Supercar 这类通用叫法），`audit_copy_quality.py` 按 `remake-core/assets/trademark-words.json` 拦，并写出命中的词。改完全屏扫一遍，不许残留中文（含角落小字）。规则见 [英文界面重建](references/english-ui-rebuild.md)、[动态文字字形](references/dynamic-text-glyph-review.md) |
| 2 | 首页加两个功能键 | 个人主页回访（Revisit from Profile）、添加桌面（Add to Home Screen）。首次英化主页按[默认主页排版](../remake-art/references/english-home-layout.md)统一设计，把这两个入口与原有功能一并安排；所有环境都显示、不隐藏（本地试玩也显示）；**点一次立即调用对应平台入口**，没有说明弹窗、过渡提示或手动领奖键。Studio 和 Web 保留两个按钮，缺能力、失败或取消时安静结束，可再点。玩家从对应入口回来、平台确认资格并存档成功后自动发奖，奖励各 5B（一次首页礼盒基础奖励，换算成原游戏货币）。原游戏没有金币的（Saul 2026-11-04）：有体力的各发体力 +3；金币体力都没有的，先加一种金币和皮肤给它当花处，再发 5B（[经济规则](../remake-economy/references/economy-rules.md)第三节末尾）。|
| 3 | 设置里两个音量 | 音效（SFX）和背景音乐（BGM）分开调节、立即生效、重启后保留 |
| 4 | 删除三类功能 | 分享给朋友、更多游戏、排行榜：按钮、入口和相关代码调用全部删掉，删后页面不留空洞。**例外（v7.5，Saul 在细菌2048 的选择）**：原游戏核心玩法里的分享奖励（复活、礼物、双倍）改成激励视频；其他分享入口连同触发它的礼物球、弹窗一起删干净。不许留“本平台不可用”的提示按钮；每个分享调用在 `docs/` 写明删掉还是改成广告。**局内本地名次可以留（Saul 2026-10-31，照 68 小熊拳击）**：一局里玩家和电脑对手的名次（局内分数牌、结算名次）、按名次给的本地奖杯和段位、个人星级和最高分都不算排行榜；数据只存本机、不联网，匹配页写 Finding opponents，电脑对手不用真人风格的名字，段位叫 Tier 不叫 League。要删的是联网的世界/好友/地区/周榜（含开放数据域）、本地编出来的全服名次（如 “You are #3,512”、“Top 5%”）和假联赛；`remake-core/scripts/audit_no_social_features.py` 按这个口径查。见 [固定入口](references/fixed-entries.md) |
| 5 | 修正操作 | 原来操作有问题的位置改好（点不到、点了没反应、改动后某处操作消失要补回）；不新增玩法 |
| 6 | 每关结算页 | 有 Retry；统一加 **Watch Ad x2** 入口，是结算页上最大、最显眼的按钮；普通领取（Claim）是它正下方一行可点的小字，不做成第二个按钮（Saul 2026-10-31）。见 [固定入口](references/fixed-entries.md)；样子按[广告板块·结算页设计](../remake-ads/SKILL.md#结算页设计用户-2026-10-27)，广告行为和 x2 数额按广告、货币板块（见下面「看广告的几项按广告板块做」） |
| 7 | 看广告复活 | 有失败/中断的一局都加“看广告复活”；**没有失败状态的游戏也加**：按玩法挑一个合理的结束点，用增加一次真实游戏机会承接（例如时间到看广告 +15 秒），不增造失败条件、能量条或固定扣减数值。单独一节，见 [固定入口·看广告复活](references/fixed-entries.md#看广告复活单独一节可整节删除)；实施和检查按广告板块（见下面「看广告的几项按广告板块做」） |
| 8 | 广告加量（ad-boost） | 默认做，不问 Saul（Saul 2026-10-31）：按本包的 [ad-boost](../ad-boost/SKILL.md) 诊断结束、主页、永久皮肤、体力、局内道具、每三局试用六标准类，已有的核实保留，缺失的按固定顺序补齐；同一转盘归主页且只计一次，额外类不替代标准类。新增界面排布前必须联动本包 remake-art。首次英化主页将新旧入口纳入同一美工排版，画风跟原游戏；已交付后的局部接入只处理受影响区域。做法见下面「按 ad-boost 补齐六标准广告节点」 |
| 9 | 关内暂停键 | 每个模式的关里都要有暂停键或设置键，点开暂停窗有 **Continue**（一下就关、接着玩）、**Restart**、**Home**（规则一直有：[逻辑规则](../cocos-game-check/test/references/logic-rules.md)「关卡内（HUD）」一行；以前不在这张表里，割草 v015、人鱼 v18 英化后关里没有暂停键，出包被拒）。原游戏有暂停 / 设置窗的保留原样，缺哪个按钮补哪个；只有返回键、回首页键的加一个暂停键，不改玩法。暂停窗开着时计时、物理、生成都停。暂停页、复活页、结算 x2 页用 GameUIKit 的 pausePage / revivePage / resultPage 生成，别手写；英化游戏把 RunSession 只接在这几页上（原版玩法代码不动），没有 RunSession 的原版游戏不传 session，在 onResume / onRestart 里接原版的暂停和重开函数。见 [固定入口·关内暂停键](references/fixed-entries.md#关内暂停键v79-手机问题源头约束英化第-9-项) |

## 看广告：固定几项按广告板块做，第 8 项默认加 ad-boost 板块

**看广告的几项按广告板块做（Saul 2026-10-31）**：英化自己要做的广告的事，自动按本包的[广告板块 remake-ads](../remake-ads/SKILL.md)做，数额按[货币板块 remake-economy](../remake-economy/SKILL.md)，不用 Saul 点名：

- 第 6 项结算 Watch Ad x2：x2 是结算页上最大的按钮，Claim 是它正下方一行可点的小字，样子和位置按[结算页设计](../remake-ads/SKILL.md#结算页设计用户-2026-10-27)表里「看广告 ×2 按钮」「直接领取」两行（Saul 2026-10-31）；看完到账、取消/失败/超时停在结算页且 Claim 仍可点、只发一次，按[共用的广告设计](../remake-ads/SKILL.md#共用的广告设计)的结算一行；数额按[经济规则·货币和结算×2](../remake-economy/references/economy-rules.md#二货币和结算2)（基础已发只补差额；没有货币的游戏翻倍本局捡到的道具）。
- 第 7 项看广告复活：按[复活审查](../remake-ads/references/rewarded-revive-and-help-layout.md)的实施和检查做（英化一律加，不用再审要不要加；页尾的小型教程英化不做）；复活页用 GameUIKit 的 `revivePage` 生成（只认看完），别手写；复活页 → 结算页的顺序按[一局结束：每屏一个视频按钮](../remake-ads/references/end-flow-one-video.md)。
- 原游戏自带签到、转盘、礼包领奖窗时的看广告双倍勾选框：按广告板块共用表那一行和验收清单；数额按[经济规则·第四节](../remake-economy/references/economy-rules.md#四七日签到的数值用户-2026-10-27)末尾（有数量的项 ×2，皮肤不翻倍）。
- 原游戏已有的看广告入口改接平台包、广告计时、`qa/ad-regression.json`：按[广告机制](../remake-ads/references/ad-mechanism.md)和[超时规则与广告回归](../remake-ads/references/ad-timeout-and-regression.md)。

其他页面和按钮仍按本页和[固定入口](references/fixed-entries.md)（原游戏的保留，结算页上原有的按钮不能比 x2 大）。其他看广告入口不另外按广告板块加，由第8项同包ad-boost按六标准类补齐，广告行为照广告板块。

**默认执行六标准广告完整制作（用户2026-11-11）**：每款首次英化第2阶段调用同包[ad-boost](../ad-boost/SKILL.md)，结束、主页、永久皮肤、体力、局内道具、周期试用六类全部齐全，额外任务/离线等奖励循环不能顶替。先看真实已有系统与入口，候选核实后复用，不重复装；缺系统先装真实依赖，再补广告。
- 节点和依赖按[六类制作联动](../remake-core/references/ad-standard-six.md)逐层完成，不再使用广告量“少/一般/多”的前3/2/1推荐算法，也不因原游戏无皮肤/体力/道具跳过。
- 新增页面、弹窗、按钮和HUD在排布局、选图之前真实运行 `ad-boost/scripts/art/skill_link.py prepare`，读取当前美工和本游戏参考。第3阶段按原画风完成本轮全部广告UI；内部占位不能作为正式试玩完成。
- 逻辑用现有零件、同一RewardedService及SaveStore；数值走经济规则表，皮肤至少10且沿用稀有度/60%广告和单件一种永久获取条件，局内所有道具只算一类。
- 复用pages/visual-slots/capture计划，首件和新状态走美工原局部检查，既有通过项沿用。正式serve_preview/handoff_preview核六类接线与本轮UI；最终两个writer与check_package/prepare_delivery核当前六类运行和实际Native字节。
- 这是本轮用户确定的制作范围，不再逐项询问已定系统；用户明确只诊断、只维护一处或免验时遵守本轮范围并如实报告，未达到新标准不能写六类通过。

- 交付记录写一行：「XX、YY 板块按英化默认做法加入（Saul 2026-10-31：英化默认执行广告 Skill，不用询问）。」

## 阶段

**前期预防（Saul 2026-11-04）**：第 1 阶段读取[前期预防](references/early-prevention.md)，把条件状态、共享组件使用者及改动涉及的保存/接入信息补进已有记录；第 2 / 4 阶段按该页先确认代表件实际状态，再批量制作，改动功能就地核对结果与重载。下文“第 5 阶段检查”指核对完整覆盖、补缺及最终写包，不推迟这些制作和接入时的局部验证，也不重复已有有效记录。

**先查美工，再给英文试玩链接**。开工核中文原版内部基线。第一轮全部美工及 ad-boost 诊断和接入在制作时完成。第 3 阶段完成中文专项检查、制作范围内的技术美工检查，修复并复查通过后给英文试玩链接。ad-boost 板块也先查再带入链接。制作节点核对适用技术项，画面观感按同版人工快查。反馈与最终验收的候选在内部点检。广告回归 10 例按适用项执行，已知问题与平台兼容仍须完整覆盖，各项在对应制作节点执行一次。第 5 阶段和写包入口读取同一记录。英化的交接以本页为准。

**每阶段结束都发结算（用户 2026-11-10）**。开始跑 `T stage <N>`，执行中按节点计时。结束跑 `T done --summary "<完成、沿用或未覆盖的内容>" --next "<下一步>"`，把工具生成的阶段记录和说明发到当前聊天，再进下一阶段。第 3 和第 5 阶段由正式交接入口结算，当前交接回复附该阶段记录。无实测计时的范围标未记录，未走的阶段标不适用。`T` 是 `python3 <skills>/cocos-game-to-english/scripts/stage_timer.py --project <工程>`。

1. **盘点**：**中文源码不带 .git（Saul 2026-11-04，91 SLS11）**：91 卖家给的 SLS11.zip 带着完整的 `.git`，提交记录里有上架文案 `app_desc.txt`（开发者账号和密码）。中文源码一律用 `python3 scripts/unpack_source.py --source <中文源码.zip 或文件夹> --out <新的工作目录>` 放进工作目录，不要直接 unzip / cp：`.git` `.svn` `.hg` `.idea` `.vscode` `__MACOSX` 不拷，`app_desc.txt`、`.env`、签名证书和私钥不拷，文本里像账号密码的行（比如 `settings/project.json` 的 `appSecret`）列在 `docs/source-intake.json`，交源码前把值清空。原 ZIP / 原文件夹不动；`unpack_source.py` 还会先把原包复制进游戏文件夹的只读 `_原始输入/`（只有 Saul 自己能删）。清理旧版本只用 `python3 <skills>/remake-core/scripts/clean_old_versions.py`，不手写 `rm -rf`。开工打印「已装 Skill 被改过，请走补丁」时，把列出的改动写成补丁交 Skill 会话，不要接着直接改已装文件。要交源码时用 `python3 <skills>/remake-core/scripts/make_source_zip.py --project <工程> --out <游戏_Source.zip>`（不带上面这些，带凭据就拒绝），`prepare_delivery.py --source` 和两个写包入口按同一规则拦（`source_hygiene.py`、出包门禁 `H1_vcs_ide_in_package` / `H2_credentials_in_package`）。
   **开工先核中文原版内部基线，核准后继续制作**（Saul 2026-10-31）。在中文原工程的一份副本上导出 Web（复制到工程外再导出，原工程一个文件都不动；用原游戏对应版本的 Creator 命令行：先跑 `check_machine.py --project <中文原工程>` 查电脑，再用 `find_creator.py --project <副本>` 找本机的编辑器、拿构建命令（见上面「换电脑也能用」和 [Cocos Creator 版本和已知问题](references/local-creator-versions.md)：没装那个版本先用同一小版本里最近的；2.4.3 要先放进本包的构建扩展再加 `--use-gl=desktop`；3.x 导出缺入口页时用 `fix_web_entry_3x.py` 补），其他写法见[真实 Cocos 运行](../remake-core/references/cocos-runtime.md)：2.4 是 `--path <副本> --build "platform=web-mobile"`，3.x 是 `--project <副本> --build "platform=web-mobile"`；macOS 命令行卡在导入资源时加 `--no-sandbox --disable-gpu-sandbox --disable-gpu`；原工程里已经有没改过的 `build/web-mobile` 也可以直接用），把导出的 `web-mobile` 整个复制到游戏文件夹的 `本地试玩_中文原版（不用上传）/`，再在后台起链接：`python3 <skills>/cocos-game-to-english/scripts/serve_preview.py --directory "<游戏文件夹>/本地试玩_中文原版（不用上传）" --snapshot --chinese-original --name "<游戏> 中文原版"`（`--chinese-original`：这是中文原版，不做中文专项检查；不加它，英化入口的 `serve_preview.py` 会当成英文链接去查，找不到英化工程就不起）。服务作为内部基线。需要实际点按时由 Computer Use 在 Edge 打开。中文原版不用英文广告冒烟。导不出 Web 时（引擎版本不对、构建报错、只有小游戏包没有源码），把原因写给 Saul，同样接着做。这份导出后面截中英对照图（`docs/baseline/`）也用。然后跑 `python3 <skills>/remake-core/scripts/tiktok_finalize.py init --project <中文原工程> --board localize`（写新游戏标记 `.tiktok-kit/policy.json`），再跑 `tiktok_finalize.py inventory --project <中文原工程>`，它把原版里的广告、加桌面/回访、触摸、启动、存档、分享/跳转/统计、登录代码逐项列到 `docs/english/platform-inventory.json`，第 2 阶段按它逐项改。inventory 之后马上跑 `tiktok_finalize.py rewire-ads --project <英化工程>`，再跑 sync；原版广告和加桌面/回访奖励由它改线，别手写桥；剩下的按 platform-inventory.json 的 rewire_todo 手改，delete_list 照单删（见 [rewire-ads](../remake-core/references/rewire-ads.md)）。3.x 游戏也一样跑 rewire-ads；`rewire_todo` 里 ad / ad_call / ad_handler 的行清零才往下做，别自己写浏览器里直接发奖的分支。和 `audit_new_english_images.py --make-list <工程> --out <工程>/docs/art/original-images.json` 放在同一步做。然后列出全部中文（文字和图片字）、首页现有按钮、设置项、结算页、分享/更多游戏/排行榜入口、已知的操作问题。存档也在这一步盘点：跑 `python3 <skills>/remake-core/scripts/make_save_schema.py --project <工程> --inventory`，把原游戏所有存档键写进 `docs/save/save_keys.json`，关卡进度、金币、已买皮肤没存档的写进待改清单；原游戏有关卡文件时跑 `make_level_plan.py --project <工程> --record-level-files '<关卡文件 glob>'`。再跑一次 `fit_english_labels.py --project <工程> --dry-run`，哪些槽放不下最长的译文、要多宽，写进首件清单。把中文原名和英文名都写进 `docs/copy/glossary.json` 的 `"game_name"`（一定要写）：出包时 `game_name_scan` 用它比对 Label 文字和中文专项检查已经识出的图片文字，11-05 起开工的英化游戏有命中就拦，更早的只警告（见第 2 阶段「游戏里不放游戏名」）。`audit_new_english_images.py --make-list` 写出的 `art-replace-round1.json` 里，`regenerate` 带 `title_logo` 的那张是原游戏的标题 logo：第一轮按它的 prompt 画成主角、图案或场景，不写游戏名，也不要译成英文 logo。`platform-inventory.json` 的 `audio_todo` 列的是原游戏自己的声音入口（播放调用、平台音频对象、音乐和音效开关读写）：英化时把它们全部改走平台包 `AudioService`（音乐和音效分开开关），`audio_todo` 清零；`audio_summary` 有 `one_switch_suspect` 时，先确认音乐开关有没有连音效一起管，设置页两个开关各试一次。`reward_todo` 列的是原游戏自己加钱、扣钱、改道具的地方：英化时每条改走 SaveStore `grant`（发奖）或 `ShopTx`（扣费换东西），只改发奖和存档的写法，玩法不动；顺序固定为「凭证 → 保存读回 → 刷新界面 → 播动画」，动画回调里不发奖、不存档；x2 只算一次基础整数，显示和到账都读它的 2 倍；局内已进钱包的收益，结算时不再发一次。sync 报 `K_W_reward_*` / `K_W_x2_rounding_mismatch` 时照提示改。盘点原版时顺手查调试和别家残留：跑一次 `tiktok_finalize.py source`（会跑 `debug_leftover_scan`），把开着的 debug/cheat/test 按钮设成 inactive 或删掉，删掉能打开 FPS 统计的代码，原工作室开屏（启动场景里开局计时后自己淡出的节点、写着某某 Games/Studio 的字）直接去掉，让首页一出来就能点；平台配置的 App ID 和广告位只用平台包模板里的共用测试 App 或本游戏 `docs/platform/platform_ids.json` 记的，不留原游戏或别的游戏的。遗留名单上的旧英化游戏（射击高手、音乐消消乐等）继续做新版本时不跑 `init`，按旧游戏出包（拿不准就先跑 `tiktok_finalize.py decide --project <工程>` 看判定）；要改用标准件才跑 `tiktok_finalize.py adopt --project <工程>`。用时：开工第一件事先 `T start --run-id <本轮唯一ID> --route source` 再跑 `T stage 1`，中文原版基线用 `serve_preview.py --chinese-original --project <工程>` 起内部服务，它自动记「中文原版链接」（没带 `--project` 或没记上时手动跑 `T mark 中文原版链接`），盘点做完跑 `T done`，用时发给 Saul，不等回复，接着做第 2 阶段。

   **旧 Creator 开工迁移专检**。原工程 2.0～2.3 走 2.4.15 升级路线时，先按[迁移专检](references/creator-migration.md)登记工作副本，用真实目录构建并核对共享模块，用真实同版启动记录或 Computer Use + Edge 实际点 PLAY。通过后才开始第 2 阶段的批量英化接入。该轮沿用迁移基线中的有效证据。

   **标准件开工就装，每次构建前自动同步（生成时预防 P02/P05）**：`init` 之后紧接着跑一次 `python3 <skills>/remake-core/scripts/tiktok_finalize.py source --project <英化工程> --board localize`，再跑 `tiktok_finalize.py sync --project <英化工程> --board localize`，以后**每次构建前**都先跑 `sync`（约 1 秒，只把平台包文件按哈希换回原样、装上 `GameUIKit.js`，不动图片）；TikTok 小游戏包的构建命令照 `find_creator.py --project <英化工程>` 打印的整条用：构建成功后它自动跑 `sync --project <英化工程> --board localize --native <构建目录>`，把启动件、触摸修正、存档层、宿主接口兜底 host-shim、3.x 启动看守和 guard 装进这份构建（不手写 game.js 那几行），别只复制 Creator 那半条，不然包里没有 guard，出包时会报 `K_W_rewarded_guard`；sync --native 没过就先改它报的问题，别拿这个构建出包。find_creator 算不出构建目录时会提示，按提示手跑。3.x 工程 sync 也装 `GameUIKit.ts`。这样试玩和自测跑的就是带标准件的代码，不等出包才装（射击高手 v81、小熊拳击 R27 漏装触摸修正，指尖麻将 v55 重建丢了补丁，拇指弹球留着旧版 `RewardedService.js`）。遗留名单上的旧游戏 `sync` 只报告不改。新加或改动的弹窗、按钮一律用平台包的 `GameUIKit`（`var UI = require('GameUIKit')`：`UI.popup`、`UI.button`、`UI.toast`、`UI.digits`），别手写遮罩、淡出和点击；新加的正文 Label 一律用 `UI.text(parent, {w, h, text, overflow})`，教程手指一律用 `UI.guide(目标)`，原游戏的 Label 不动；AI 动过的原版按钮用 `UI.wrapExisting(节点, 函数)` 包一层；弹窗里的计时器和异步回调用 `popup.guard(回调)` 包住。用法见[平台包接入说明](../remake-core/assets/platform-kit/README_接入说明.md)第十一节。英化新加的弹窗用 `UI.popup`，提示文字从文案表取；`source` 会对手搭弹窗、写死遮罩和 PREVIEW/DEBUG/TODO 字样给警告。图标加数字（签到格、HUD 金币、价格）用 `UI.iconValue`，别手摆；页面上从存档来的数值写进 popup / 页面模板的 `refresh`；只在某些状态才出现的按钮用 `UI.newButton({active: false})`；首页两个入口的提示和排位交给平台包（2.4 的 `HomeGrowthEntries` 在 init 时传 `homePanel`，3.x 的 `placeLater` 自己等布局稳了再排），不要自己写提示 Label 或 scheduleOnce 一帧就排。弹窗的关闭图、提示底图、数字图开工时用 `UI.setup` 设一次，页面里别改 `UI.config()`；GameUIKit 1.1.7 起图被释放也会自动换回自带图。3.x 游戏的 PlatformConfig 由 `plugin3x_scan` 查 id 是不是从别的游戏拷来的；要查本机别的游戏，设 `TIKTOK_KIT_PEERS`。
2. **修改**：功能范围按上表，施工按[依赖顺序](../remake-core/references/production-plan.md#英化制作的依赖顺序)。先把六类广告、两个平台入口、设置及原有页面一并规划，再准备共用接口和数值、加载美工定版式与显示槽、实测代表首件，之后按共享批次接逻辑与批量制作。按[前期预防](references/early-prevention.md)先确认本批代表件和实际状态，再铺到所有受影响使用位置；涉及功能改动时随实现验证保存和重开结果。开始跑 `T stage 2`；做完跑 `T done`，用时发给 Saul，不等回复。
   - **广告规划先于批量美工（用户 2026-11-12）**：开工盘点后用同包 `ad_nodes.py plan` 明确六类现有/缺失项及 `production_schedule`，在已有规格、ad_nodes、页面和显示槽清单登记本轮全部入口、返回、默认/禁用/领奖状态、奖励最长串及资产需求。六类固定顺序用于核实与展示，不能做完一类的整套美工、构建和检查才开始下一类。原页面与广告新增页面共用一次本作画风和批次计划；共享底板、按钮、字形、数字/符号及图标按组制作。新增功能未定前不先把原 UI 批量重做；美工设计仍在布局/选图和接线前加载，逻辑实现和已定稿素材可按文件归属并行。缺项尚未核实时继续盘点，不能把计划或占位图当完成。
   - **第一轮美工：先按美工 Skill 重新设计主页排版，再照原画风制作按钮和文字（用户 2026-11-10）**：第一轮就做，不等点名。范围：所有按钮（带字的和不带字的图标按钮都算，Saul 2026-10-31：第一轮所有按钮都重新生成）、页面标题和所有图片字（中文改英文）；**游戏里不放游戏名**（Saul 2026-11-05：「以后的游戏都不要出现游戏名字，把对应的部分换成图案或者主角等美工来填充，不要是具体的游戏名字」）：原版首页等处的游戏名标题不做英文版，原位置换成照原画风生成的主角或图案图，主页中的大小和位置按本轮主页设计安排，其他页面按受影响区域的可读空间安排；出包时 `tiktok_finalize` 的 `game_name_scan` 会查场景、预制体、文案表和已识出的图片文字里还有没有游戏名（11-05 起开工的英化游戏有命中就拦，更早的只警告）；报了不要停下来问 Saul：先跑 `python3 <skills>/remake-core/scripts/fix_game_name.py --project <工程>`，文字当场去掉；它写的 `docs/art/game_name_fix.json` 里每张图照提示词和参考图生成同名、同尺寸的无字图，放进一个文件夹，再跑 `fix_game_name.py --project <工程> --apply-images <文件夹>`，退出 0 就干净了；出图前跑 `python3 <skills>/remake-art/scripts/prompt_name_guard.py --project <工程> --file <提示词文件>`，提示词里不写游戏名（加 `--fix` 直接写出改好的提示词）；等级、关卡号、分数、货币（图片字的词＋0-9 位图数字＋货币图标）；新加的按钮（主页回访、加桌面、Watch Ad x2、复活、ad-boost 板块的按钮）和 Claim 小字。**正式试玩前全部完成（用户现行要求）**：第一个正式 Native 英文试玩链接前，完成全部计划美工：首页、设置、暂停、复活、结算、关卡选择、商店、皮肤、原游戏的签到/转盘/礼包、教程等实际存在页面的按钮、标题和图片字，局内的等级、关卡号、分数、货币数字，以及第 8 项 ad-boost 板块的图。制作可分批，首件通过后再铺开；不能把未完成页面、中文图片字或本轮已计划的板块留到第二轮再补。界面上的文字（Label、代码里的字）也全部改成英文，按第 3 阶段核对完整美工与中文专项覆盖后才发正式链接，已有有效证据直接沿用。做法按[美工 Skill](../remake-art/SKILL.md)：固定按钮优先复用同款合格整钮。已有核准整词字图及同款无字底时，先按[固定英文按钮生成](../remake-art/references/fixed-caption-button.md)用本包脚本等比合成，图标和旧字层只保留一份。缺少核准原料时，用生图工具（image_gen）按定稿制作并核字，原图放进参考图照着画，材质、字形和色系跟原画风一致，主页尺寸和位置按本轮设计安排；代码和字体画的按钮、数字不算（Saul 2026-10-30）；每出一张图跑 `art_records.py generated` 记下来。句子（说明、教学、提示）照第 1 项用真正的英文字体，不生成图片。先做 2～3 个有代表性的（一个带字按钮、一个标题、一组数字）放进游戏看一眼合成效果，没问题再批量做，有共性问题先改共用的图再接着做。画风照原游戏，不换风格；Saul 要求换画风或重新设计时看下面「美工」一节。沿用原画风时，原包里本来就有的深色、纯色背景和面板不用重做：art_check 按图片 SHA 认原图，记「原图保留，不适用」；Saul 选了保留原画风就写一行 `docs/art/keep_original_style.json`（decided_by、date、why），回执和出包会读它，不要再在会话里另记人工授权，也不要再问 Saul。开工时的纯色面板清单在 `art-replace-round1.json` 的 `style_choices` 里，只有 Saul 点名美工 Skill 才重做（`--make-list --flat-panels regenerate`）。
   - 固定按钮随包可运行样例见[CLAIM 配方](../remake-art/examples/fixed-caption/recipe.json)。按目标游戏内框重定参数，空间不足停止出图。试玩前在两种手机尺寸检查最终画面，分层图标按钮登记 horizontal_gap。
   - 美工领到新图或旧画面反馈时，先按[把曾经漏掉的画面问题用于首件制作](references/english-ui-rebuild.md#把曾经漏掉的画面问题用于首件制作)选对应做法，写进该类素材的生成或接图参数。先完成最窄尺寸的一件，再复用到同组。
   - **美工制作预防（Saul 2026-11-03）**：开始生图前先按[美工制作预防](../remake-art/references/production-prevention.md)落实 T01–T14 的适用项，再执行[生成前先定尺寸与分区](references/english-ui-rebuild.md#生成前先定尺寸与分区制作时消除问题saul-2026-11-03)：英文定稿、实际可读空间、宽高比与文字/图标/状态/动作分区先确定，再写进提示词；接图等比缩放并处理被替代的旧视觉层。先把最长按钮词、标题、密集卡片等代表样接到真实页面确认，再批量做，每批就地看组合效果并修共性问题，不留到第 3 阶段才返工。保持原游戏画风；首次主页按新方案排版，其他页面沿用已批准布局并为英文留足内区，不能把英文强压进原中文窄框。
凡新增或改动图标＋文字按钮、海报说明条、长正文和奖励计数，按[图文内区检查](../remake-art/references/local-ui-contract.md)登记受影响状态。试玩前普通 art_check 读取 docs/art/visual-slots.json；逐项核对实际截图，原料切对、语义绑定和运行布局分别验。

   - **平台能力用平台包**：激励视频用平台包的 `RewardedService.js`，加桌面、主页回访用 `TikTokMissionService.js`（`remake-core/assets/platform-kit/`），不另写一份桥接。它们已经把 UI 回调包在 try/catch 里，提示抛错也不会把请求锁死（MusicSlice v29b 手写的 bridge 提示一抛错，看广告、加桌面、回访全部卡在 Checking）。触摸修正、存档层、启动件、适配层、App ID 由平台脚本安装和核对。图片格式和压缩在试玩前用相同脚本处理；手写的同类文件会被换掉（旧游戏除外）。新英化游戏一律装存档层 `storage-guard.js`（原版多键存储也走它）；旧英化游戏默认不装，只在 `adopt` 以后装（Q6）。原版的广告管理器改成调 `RewardedService`、原版里直接 `createRewardedVideoAd` 或直接调加桌面/回访接口的代码删掉：新游戏漏改出不了包（`A1_rewarded_outside_kit`、`G1k_growth_outside_kit`）。原版（2.4）自带和平台包模块同名的脚本（例如自己的 `TikTokMissionService.js`），`source` 段会把它移到 `.tiktok-kit/removed/`。`PlatformConfig.js` 要填本游戏的 `gameId` 和 `normalLevelCoins`，没填新游戏出不了包（`K_platform_config`）；原游戏没金币时 `normalLevelCoins` 留 0（写包只警告），首页的 `HomeGrowthEntries.init(save, {reward, rewardText})` 传 `economy_capabilities.json` 里 `no_wallet_substitutes` 给的替代奖励（有体力的各 +3 体力；没体力的先加一种金币和皮肤，再发 5B），不传写包会报 `K_home_entries_no_reward`。 原版广告管理器先跑 rewire-ads，改不了的才手改。新做或重建的界面：背景用 `parts/ScreenFit.js` 的 cover 铺满，顶栏和底排用 safeTop / safeBottom；拖拽、滑动、摇杆用 `parts/TouchOwner.js`，不另写（见平台包接入说明第十七、十八节）。原版界面不动。
   - **做的时候就做对（生成时预防，简化.11.13）**：① Label、prefab 里的中文改成英文以后马上跑 `python3 <skills>/cocos-game-to-english/scripts/fit_english_labels.py --project <工程>`：放不下的单行字它直接改成 SHRINK（缩后不低于原字号 70%）；退出码是 1 时按 `docs/english/fit-labels.json` 的 todo 一条条改（加宽框、改短英文、多给一行），改完再跑，直到退出码为 0。数值、百分比、倒计时这类 Label 先在 `docs/english/label-values.json` 登记最长值（`max_value` / `longest` / `room`）再跑。倒计时按它自己的格式量（mm:ss 不按 00:00:00）；NONE 的字只记录不改，记录里 `wider_than_parent_plate` 的那几条接图时看一眼。跑完看记录里的 `bitmap_needed`：分数类数字已自动换成位图字，列出的固定词要用美工 Skill 生成整词图再接上，别用字体补。换字体或加 TTF/OTF 后马上跑 `python3 <skills>/remake-core/scripts/subset_fonts.py --project <工程>`（本机没有 fontTools 先 `python3 -m pip install fonttools`），别把整套字体放进主包。英文写进 Label 和 prefab 以后，紧接着跑 `python3 <skills>/cocos-game-to-english/scripts/english_copy_guard.py --project <工程>`：字面的 `\n` 它自动改成真换行；RichText 标签不配对、登记过的看广告按钮上没写 WATCH AD 时退出码是 1，改完再跑。美工生成位图数字和整词图之前先读 `docs/english/charset.json`：位图数字按 `value_charset` 一次画全，`word_images` 在首件之前一次生成齐；先拼进变量、过几行再赋给 Label 的格式串，english_copy_guard 算字符集时也认得出。位图数字的字符集以 `docs/english/charset.json` 的 `value_charset` 为准，数值格式化里的单位字母（K/M/B…）和符号也在里面；`fonts[].missing` 不为空就按这份字符集重画位图字，或者把单位和符号改用整字图 Sprite 槽，不要只画 0-9。第一轮接图按 `art-replace-round1.json` 的 `runtime_words.missing` 把代码运行时取的整词图一起画好（`txt_<slug>.png`），`untranslated_names` 先翻译再画。只改了几个节点时，`fit_english_labels.py` 加 `--nodes <这几个节点>`；停用的旧占位符在 `label-values.json` 写 `status: retired` 和 `reason`。preflight 的「文案写入校验」一行也会列出 RichText 不配对、看广告按钮没写 WATCH AD 的地方（现在只提示），看到了就跑 `english_copy_guard.py --project <工程>` 改掉。② 首页加主页回访、加桌面两个入口：2.4 挂 `HomeGrowthEntries`，不写入口坐标，它在 init 后按首页按钮和带触摸的节点自动摆，放不下报错；3.x 用平台包装好的 `TikTokKit.HomeEntrySlots.placeLater` 运行时摆两个入口，别手写入口坐标，手写了 `source` 会报 `K_W_home_entry_coords`（想先看空位时可以跑 `node <skills>/remake-core/assets/platform-kit/tools/home_free_slot.js --dump <首页 ui_dump> --screen <宽x高> --entry <宽x高>`）。首页新加的按钮一律用 cc.Button，加完调一次 `HomeGrowthEntries.placeEntries()`，不自己估坐标。首次主页先调整美工留位方案；已交付后的局部接入按当前授权范围处理。③ 换图接图用 `python3 <skills>/remake-art/scripts/bind_art.py --project <工程>`（2.4 和 3.x 都支持；按新图比例装进原框，自动设 trim 和 sizeMode），不手改节点宽高；接完跑 `bind_art.py --project <工程> --check`，只改这一轮换过图的节点，原游戏的图（拉满屏的遮罩、角色部件、进度条）照原样。生成的透明图裁边用 `remake-art/scripts/trim_visible.py`，别手写 getbbox；整词图、按钮字这类字图裁边时加 `--word`，它先自动去掉描边外的半透明彩色光晕（原图留作备份）再裁；退出码 1 表示光晕去不掉，按它打印的提示词（同尺寸、同字、no glow）重生成再跑，旧图别接。原游戏有皮肤的，皮肤预览只接每款自己的 previewFrame，别用槽框图、别整张染色，接完跑 `python3 <skills>/remake-core/scripts/check_skin_preview.py --table <皮肤表> --board localize`；皮肤表的 previewFrame 也由 `tiktok_finalize` 的 source、sync 自动查（英化只警告）。带字的新图过 ad-boost 的 `postprocess.py` 时会量字和字底的对比度，被拒就整张重生。④ AI 新加的图（主页回访、加桌面、广告板块的按钮图）走资源表：`python3 <skills>/remake-core/scripts/make_res_keys.py --project <工程>`（英化不加 `--strict`），代码用 `Res.sprite(ResKeys.x)`、`Res.request(ResKeys.x)`；原版加载代码不改。⑤ 原版玩法代码不改；AI 新加的暂停、复活、广告入口用平台包 `RunSession`（`pause('revive')`、`adHooks()`），不要再写一个暂停布尔。数值文字（音量 %、金币、分数、倒计时）用 `UI.valueLabel(node, {longest})`，别按当前值定宽。⑥ 要从音效库加声音时用 `python3 <skills>/remake-core/scripts/import_audio.py --project <工程> --file <音效库里的文件>` 导入（自动写 `docs/audio/credits.csv`），不手工复制；AI 新加的声音逻辑用平台包 `AudioService.js`；原版的声音文件不动，原版的播放调用、平台音频对象和开关读写按盘点的 `audio_todo` 改走 `AudioService`（见第 1 阶段盘点）。⑦ 原游戏关数少于 60 时，先跑 `python3 <skills>/remake-core/scripts/game_capabilities.py write --project <工程> --merge --level-count <原关数>`，再跑 `make_skin_table.py`、`make_economy_config.py`，两个都加 `--project <工程>`。跑完 `make_economy_config.py` 后接着跑 `python3 <skills>/remake-core/scripts/game_capabilities.py write --project <工程> --pause-button <关内暂停键路径>|--no-pause-button "原因" --ad-entry double=<路径> --ad-entry revive=<路径> …|--no-ad-entries "原因"`（ad-boost 加完板块后再跑一次补上新入口）；装 ad-boost 板块时照它的 SKILL 把各板块的 `save_keys.json` 合进工程 `docs/save/save_keys.json`，再跑 `make_save_schema.py`，零件自己建的状态（签到、礼盒、体力、板块的 round/board）登记子键时写 `"in_defaults": false`，可能是 null 的写 `"nullable": true`，别为了能登记把子键写进默认值；沿用原游戏的签到表时，`CheckinFlow` 传 `design: 'original'`；没有局外金币的游戏用 `make_economy_config.py --no-wallet --kind english --systems <有的系统>`，不再问「B 是多少」；货币审计一律带 `--project <工程>`；写 runtime 适配文件后跑一次 `game_capabilities.py adapter --project <工程> --adapter <适配文件> --out <新文件>`，用它出的那份。零件用法见[平台包接入说明](../remake-core/assets/platform-kit/README_接入说明.md)第十一至十八节。
   - **原版的 `.webp` 图**：新英化游戏由 `source` 段换成 PNG/JPG；数据或脚本里写死的 `.webp`（例如 `"imageExt": ".webp"`）按文件和行号被拒（`IMG0_source_images`），要改成 `.png`/`.jpg`。原版是 Cocos 3.x 的没有 WebP 例外（`K_webp_exception_3x`），只能靠 PNG/JPG 和 `max_side` 缩到 30 MB 以内。
   - **新做的英文图**：按显示尺寸 2 倍导出再压缩。新图（哈希不在英化前的图片清单里）单张超过 800 KB，出包会被拒；宽/高超过显示尺寸 2.5 倍的会被列出来，要改小（`remake-core/scripts/audit_new_english_images.py`；开工时用 `--make-list <中文原工程> --out docs/english/pre-english-images.json` 存英化前清单，出包时缺这份清单也会被拒。它同时把每张图、每个图集切片和动画帧读一遍，写 `docs/english/art-replace-round1.json`：replace 里的图第一轮美术就照原画风换成英文，manual_review 里的自己打开看；没有识字工具的电脑上全部列进 manual_review，一张都不能跳过；`regenerate` 里是整块单色的面板和背景，第一轮照原画风重画成有边框、明暗和图案的版本）。
   - **准备 `qa/ad-regression.json`（第 1 / 2 阶段定位真实入口与字段，各项随制作执行一次，第 5 阶段只补缺及复验真实改动项；不挡英文试玩链接）**：出包前的 10 个广告回归用例要它。`request` 走游戏自己真实的看广告方法，`grant` 挂在游戏真实的发奖函数上，`ready` 写首页已就绪的条件。示例：[examples/MusicSlice_ad-regression.json](examples/MusicSlice_ad-regression.json)（多渠道 AdsManager：`config.videoType=0` 后调 `config.AdsManager.ShowVideo()`，发奖统一走 `config.getReward`，示例把它换成计数）。同一个文件也给出包时核对有效覆盖的运行时回归用（`cocos-game-check/package-check/references/runtime-regression.md`）：必须有 `home`（首页可用时返回 true），建议写 `enter_level`；缺 `home` 出包会被拒。**手机才出的问题要的几块（v7.9 手机问题源头约束，新游戏缺了出包被拒）**：`play`（首页 PLAY）；`resume_play`（`start` 进到一关、`probe` 真点一下、`state_js`，有倒计时写 `clock_js`；暂停键、继续键、关内广告名字认得出就不用写）；`ad_entries` 写适用的结算页 Watch Ad x2（`"role": "double"`）和第 8 项新增的非复活广告入口，各带真实到达操作；局内复活列入美工后首轮人工试玩，旧 `"role": "revive"` 可保留为项目入口清单，自动回归排除该路线，不因缺少复活自动路径拒包；`save_restart` 每一步写 `kind`，首页有什么就要有什么：过一关（`level`）、商店 / 皮肤买一件（`buy`）、领一次奖（`claim`）。写法和例子见 runtime-regression.md 的「手机检查补全」一节。
   - **广告规则去哪看**：按上面「看广告的几项按广告板块做」：广告计时和广告回归看 [超时规则与广告回归](../remake-ads/references/ad-timeout-and-regression.md)，复活页和结算 x2 两屏看 [一局结束：每屏一个视频按钮](../remake-ads/references/end-flow-one-video.md)，领奖窗看广告双倍勾选框看 [广告板块共用表](../remake-ads/SKILL.md#共用的广告设计)，数额看 [经济规则](../remake-economy/references/economy-rules.md)；和 [TikTok 固定适配·已定口径](../cocos-game-check/references/tiktok-fixed-adaptation.md) 有出入时以已定口径为准。
   - 图片字和切片在实际制作范围内复核。可保存逐项结论与真实素材对应关系，供中文排查或定点回归使用。
3. **英文试玩链接＋人工检测清单 H5**。开始候选准备时跑 `T stage 3` 并在聊天报告。先把首件共性问题合批修好，再确定本轮正式候选。在同一版上完成中文专项、本次制作涉及的美工项，以及[操作测速、倍速匹配和完整连续游玩](../cocos-game-check/test/references/pretrial-continuous-play.md)，核对原速基准、稳定档实际覆盖和免费重开后再发链接。内部首件与诊断可先用 Web，只有正式英文试玩候选才准备同版 Web 与 Native。
   **准备同版候选**。对定稿源码执行 `python3 <skills>/remake-core/scripts/tiktok_finalize.py source --project <工程> --board localize`，审阅 Sprite 比例结果并处理本轮相关项。以同一份源码备齐 Web 和 TikTok Native。现成导出经同源核对可沿用，只构建缺失或已变的目标。Web 缺 3.x 入口时先执行 `fix_web_entry_3x.py --export <这轮的 Web 导出> --project <工程>`，并用 `check_export_images.py --project <工程> --export <这轮的 Web 导出>` 核对导出的图与当前工程一致；报旧图才清理并重建对应的导出目录。用 `tiktok_finalize.py native --project <工程> --native <Native> --board localize --app-id <目标AppID>` 完成 Native 平台件与 PNG 处理。查看实际受处理图片，修复缺图、变形、色带后再验收。这一步会记录已处理 Native 的文件指纹及源码身份，供正式试玩核对。旧项目缺该记录时，先确认原构建来源，再补做 Native 准备。保留这对导出供试玩和出包。

   **核实际图片和切片**。检查本次制作和改动范围内的图片字、图集切片与共享引用。有疑问时使用 `audit_image_review_record.py` 定位 Web 与 Native 导出的差别，保留已核的具体结果。
   **中文专项检查（Saul 2026-11-01，每次给英文试玩链接前都做）**：这也太牛了的波次警告里还有「高波来袭！」：字在 Spine 图集 highwave.png 的 `wave` 切片里，脚本和场景里搜不到，旧的图片复核记录却写着没中文。所以给链接前用 `python3 <skills>/cocos-game-to-english/scripts/chinese_audit.py` 查，结果都在工程的 `docs/english/chinese-audit/`：
   ① `scan --project <工程> --export <这轮的 Web 导出>`：列出全部资源；脚本、场景、预制体、配置里的字按字符串、注释、字段分开（注释、开发日志、节点名、编辑器路径自动放过，会显示的要结论）；每张图和每个图集切片（Spine `.atlas`、`.plist`、BMFont、龙骨）逐个识字；导出里对不上源图的图单独识。第一轮几分钟，以后每轮只识新加和改过的。
   ② 有要复核的：`sheet --project <工程> --pending` 拼出复核图（每格都看得清），你打开逐项看，每项写结论：`review --project <工程> --id <编号> --verdict <结论> --by "<你>" --evidence <复核图或切片图>`。确有中文写 `chinese`，然后把图改成英文、重新导出、回到 ①；识字认错了（特效、花纹、数字被认成字）写 `false_positive`，图一个像素都不改；会显示的文字确实不显示写 `not_displayed --reason "<理由>"`。识字出错、这台电脑没有识字工具的，也要这样逐个看过，不能当成没有字。隔离渲染的截图证据写 `--evidence-kind isolated_render`，它只证明资源显示对了，不算自然玩到、也不算真机。
   ③ `check --project <工程> --export <这轮的 Web 导出>`：通过才往下。过没过由它重算（清单、切片、识字回执、复核证据都要对得上现在的文件），手写的记录不算。它报「导出不是这版源码」时，用现在的源码重新导出，再 `scan --export`、`check`，不能拿旧导出凑通过。
   **改图后的重拍清单**。登记受影响状态、共享资源、视口和复现数据，按[按状态补拍](../remake-art/references/capture-rounds.md)复用旧证据，只采改动涉及的状态。

   **制作阶段核对画面**。按本次制作和改动范围核对资源、图集、可测布局等技术项。第一个英文试玩链接前用 `art_check.py --project <工程> --board localize --dumps <本轮采集目录> --build <Web 导出>` 建立首轮技术覆盖。报告有待处理项时立即按[首轮试玩修复](references/first-trial-repair.md)继续。证据有效的通过项沿用，同一原因合批处理，修好后只补验失败组和实际受影响的检查组。技术问题由 AI 在试玩前处理，观感、动画和闪烁随同版链接交接人工快查。
   **美工试玩交接**。使用同版已处理的 Native。英化入口把同版准备记录写到 `trial-links.json`，内部草稿用 `--draft`。当前美工、中文专项、适用启动与输入及本作测速和完整连续游玩检查通过后，按[两次正式试玩交接](references/preview-handoff.md)准备同版服务和 H5 计划。调用 `handoff_preview.py --kind art --plan <计划>`。同页 H5 实际读回通过后结算第 3 阶段，再打开 Chrome。
   顶栏不手算胶囊位置：新游戏 source 自动装 CapsuleAuto。页面背景一律用 `ScreenFit.cover(cc, bg, {watch:true})`，别按设计尺寸铺，source 会查首页、局内、结算的背景（新游戏拦，英化警告）。update 里移动一律乘 dt（或 RunSession.move），节点在 onLoad 建好或从 FxPool 取，别在 update 里 new；sync 每次构建前会扫（新游戏拦，英化只提示）。
   用本轮同版启动记录或 Computer Use + Edge 确认能进首页、能开始一局且没有导致卡死的报错；这些观察沿用同一轮连续游玩，不另加一轮开局检查。自动连续游玩在隔离 Ego 空间按本作原速和匹配倍速完成完整路线、真实结束与免费重开后的进展，并核对运行错误。正式交接前读取实际观测，沿用本轮依赖未变的有效证据。第 3 阶段包含 H5 整理与入口读回。链接交付回复附第 1～3 阶段的实测用时。接力先读 `T status`，未知空档单列。
   回复里先用一句话说：这款原有节点怎样归类、六标准类各完成哪些接入与本轮美工，本轮已完成接入与美工，不要哪个直接说。按实际候选列明已完成的页面和板块，不能把未完成的计划美工留到第二轮。
   交接回复给一个[同页试玩 H5](references/playtest-h5.md)。左侧固定手机尺寸的同版游戏，右侧清单。按[人工试玩画面清单](../remake-core/references/manual-visual-review.md)列实际改到的画风、英文可读性、遮挡裁切、首次打开弹窗和转场观感。奖励去重、存档读回、冷启动、异步回调和平台回归仍由 AI 按真实依赖计划处理。用户直接指出问题或说没问题即可。
   用户指出一项就进入对应节点；已交付返工并要求改完出包时，这份清单仅供交包后可选快看，不再等一轮人工批准，不把未回复记成人工实测通过。

4. **试玩改进（Saul 反馈，AI 定点修改）**：美工试玩交接后跑 `T stage 4`。Saul 回复时先跑 `T back`。修正反馈并按影响复查对应中文、画面或功能，保留同版有效证据。接入的新增界面先按[新增界面制作](../remake-art/references/new-feature-ui.md)定稿。反馈修复与回归的候选供内部测试，处理完报告结果和实耗。本轮功能的局部验证随实现完成，未覆盖的检查在相应制作节点执行一次，第 5 阶段只核对旧证据和补缺。一次全部改完，同批导出 Web 和 Native 各一次。复查受影响整页、共享组件和新增页面，后续只处理 Saul 的反馈和明确新增要求。Saul 说试玩没问题或要求出包时跑 `T done`，进入第 5 阶段。已交付后指定美工返工按[返工交付](../remake-core/references/returned-art-delivery.md)使用本轮授权。
5. **补缺与写包核对（Saul 说试玩没问题以后）**：按逐项记录核对完整覆盖，只执行缺项和真实变化影响的项；不因进入第五阶段重复检查。
   - **先固定可验候选，再跑长矩阵**：按[稳定候选上的检查调度](../cocos-game-check/test/references/candidate-execution.md)，先核声音控件有实际播放消费者、奖励能落到真实可用对象、暂停重开没有旧回调，再校准实际 Native 的 adapter 准备路径；已有有效证据引用即可。同批已确认修复集中构建，完整套件前固定生产产物与检查器。工具失败先定点诊断；局部排查、完整验收和 writer 的结论各自保留，不减少下列门禁。
   - 这一阶段要开浏览器的命令，前面都加 `python3 <skills>/cocos-game-to-english/scripts/browser_env.py --`（哪些命令见「换电脑也能用」；只用 Ego，缺失或故障时保留未测）。
   - 涉及浏览器的入口包括 `make_tiktok_zip.py`、`build_checked_zip.py`、`check_package.py`、`ad_regression.py` 和 `runtime_regression.py`。
   - **完整覆盖不等于完整重跑**：`runtime_regression.py`、`ad_regression.py` 合并有效旧记录和本次结果。`--suites` / `--cases` 只选择补验范围；合并后仍缺项才返回未完成，只补列出的缺项。检查脚本报告开头写引擎版本和实际检查项数，0 项、缺第三方库都报 not_run（并给安装命令），not_run 不算通过；检查脚本默认只读，`--help` 和不带参数都不许崩（发版自检 C10 逐个跑一遍）。
   - 按真实影响和已有证据核功能回归适配 `qa/ad-regression.json`。
   - **写包按最终产物核对**。确认同版 Web、Native 与 ZIP 的身份和包内资源完整性。视觉问题留在制作或定点修复节点。
   - 按[统一检查](../cocos-game-check/SKILL.md)的英化档执行功能、启动、平台兼容与最终 ZIP 检查。写包入口核对当前源码记录；排查缺失或过期记录时可先用 `tiktok_finalize.py check-source --project <工程> --board localize`。其余执行 `check_known_issues.py` 和 `preflight.py`，逻辑结果读取预检生成的 `logic.json`。按 [TikTok 固定适配](../cocos-game-check/references/tiktok-fixed-adaptation.md) 核对平台项。3.x 完整 TS 检查用 `ts_full_check.py --project <工程>`。
   - 平台标准件、素材转换和 Native PNG 处理随第 3 阶段候选完成。第 5 阶段用通过试玩核验的同版 Native；写包工具继续执行需要的 Native 平台接入和包结构检查。
   - 广告加量（第 8 项 ad-boost 加的板块）：按 ad-boost 各板块 `modules/<板块>/README.md` 第 8 节验收功能。每个新的看广告按钮真实点击测看完、取消、失败、超时、连点；`qa/ad-regression.json` 照 ad-boost 的例子写（签到、转盘结果、礼包领奖窗这种带勾选框的写 `double_claim`）。
   - 用 `make_tiktok_zip.py` 或 `build_checked_zip.py` 对已验收候选出包，带上 `--project`。用 `prepare_delivery.py` 核最终 ZIP、适用回归、分包体积和同版入口。正式写包按同一 ledger 只补缺项和真实受影响项，已通过项直接沿用。重新复查最终 ZIP 的分包体积。现有同版服务经核实可以沿用。完整与局部交付均用[同页试玩 H5](references/playtest-h5.md)，局部可选快查只改一处就一条，3–5 条以内。按[最终交接](references/preview-handoff.md#最终测试包交接)打开 Chrome。**测试包、源码包、试玩链接、交接证据包四样同发**（用户 2026-11-12）：最终交接命令自动备齐源码包和交接证据包，把它输出的 `reply_lines` 原样放进回复；链接直接进入同页 H5。
   - 手机上看到的问题（v7.9）：Saul 在手机上报过问题的，登记时写 `--source device` 和手机上跑的那个 ZIP；问题门禁 `check` 的结果有 `device_issues` 时，每条的 `line`（「复现了手机上的画面和同一行报错」「不能完全确定是同一个原因」「电脑上没复现，不能说修好了」）原样贴进交付回复，不改成「已修复」。做法见统一检查的[手机上看到的问题](../cocos-game-check/package-check/references/resource-and-reported-issues.md)。
   - 用时：这一阶段开始跑 `T stage 5`。交接入口完成同页读回后记录 `T mark 交付`、`T done` 和 `T report --all`。第 5 阶段结算和全程总表放进交付回复。
   - **真机反馈修好以后（11.17.16）**：之前的检测、构建、出包都没拦住的问题，修完按[真机反馈补模拟差距](../remake-core/references/executable-regression-retention.md#真机反馈修好后补上模拟环境和真机的差距111716saul-2026-11-09)补一步：找出是检查判错还是模拟环境和真机不一样；判错的改判定，模拟环境不一样的给宿主加可选模式并留反例；没经真机确认的假设只当警告，确认后再拦截。
   - **上传兼容或首页两入口的定点修复（11.17.15）**：平台上传/审核退回、要求“参照鸽鸽小羊的修复方式处理上传兼容”或修回访/桌面入口时，按[上传兼容与首页两入口定点修复](../cocos-game-check/package/references/upload-compat-and-entry-fix.md)：写包时 `upload_compat` 自动补分包 root、`game.js` 引用和编译选项；入口点一下直接跳、不出多余文字、冷启动也查资格、不重复发奖、普通切回前台不提示；只查这些改动、必要启动和最终 ZIP 分包体积，不重跑美工；交付修改清单、测试包和同版试玩链接。
   - **出包后返工（简化.11.15，Saul 2026-11-04：「出包后的返工修改，就只检查修改涉及的那些部分」「比如我修改了贴图，之后出包甚至又要检查一遍音频，这种情况不要发生」）**：测试包交给 Saul 以后又要改，只处理指定部分，不从头再查一遍。用户明确要求“改完美工出测试包”时，本次指定视觉部分默认免 AI 美工复验，先按[返工授权记录](../remake-core/references/returned-art-delivery.md#2-用单独的授权记录不改写测试历史)完成当前候选绑定，下面第 2 步只用于未豁免的实际改动项：
     1. 按第 3 阶段改源码并构建，发新试玩链接前先跑 `python3 <skills>/cocos-game-check/package-check/scripts/rework_scope.py --old <出包文件夹> --native <新的 bytedance 构建> --project <工程>`。它先核对本轮 Native 的真实准备记录；输入、选项与规则均一致时沿用，缺失或变化时才在构建副本上准备（原构建不动），再和出包文件夹 `最新.txt` 里的上一个交付包逐文件比，打印「返工范围」几行：改了哪些文件、用到改动的页面、写包时重跑哪些检查、沿用哪些、你自己要查的和不用再查的；同时记进 `<工程>/docs/checks/rework-<时间>.json`，下一个接手的 AI 读这份就知道查过什么、改了什么。
     2. 你自己只查「你（AI）自己要查的」且未获视觉免复验授权的项。已有本次视觉授权时，不跑改图后的美工、看图、中文扫描和逐图复核；继续完成制作及同版交付。没有本次授权且改了图时，在正式试玩前只看用到这些图的页面（相关手机尺寸的技术采集按重拍规则采集这几页，复用有效旧证据并执行受影响的局部检查）、中文专项检查（本来就只识新加和改过的图）、给改过的图补图片复核；不再听声音，不额外手动重测无影响的功能，也不重看没用到这些图的页面。侧栏和桌面回访也只在其依赖变化或尚未覆盖时执行。改了音频：只播改过的声音、看设置里的音效和音乐开关。改了代码：就地验证改的那个功能，回复里写清改了哪个功能、怎么验的、为什么别处不受影响。
     3. 出包照旧用写包入口。两个写包入口的 `--rework-of` 默认 `auto`，自己找上一个交付包：只改了图片、音频、字体（代码、设置、页面结构、数据表、adapter、检查工具都没变）时，只重跑看得见这次改动的浏览器检查，其余沿用上一个包回执里的通过结果；代码和配置变化也按逐项依赖定位；范围不明时先补映射，禁止自动全部照跑。静态质量判定也沿用有效记录；本次最终 ZIP 的文件身份、体积和分包核对仍按交付规则执行。出完包写包入口自己再记一份 `docs/checks/rework-<时间>.json`，以这份为准。规则见统一检查的[出包后返工只查改动](../cocos-game-check/package-check/references/runtime-regression.md#出包后返工只查改动现行逐项记录)。
     4. 交付回复贴写包入口打印的「返工范围」几行，分别写明哪些沿用了上一个包的结果、哪些本次实测、哪些按用户授权免视觉复验。写包或试玩被拦时，按[障碍与下一步动作](../remake-core/references/returned-art-delivery.md#3-出包障碍必须落实到下一步动作)继续解决具体问题，不能停在“门禁不让出包”。不要为了「保险」自己再把全部检查跑一遍；不要用 `--rework-of none` 或删记录来绕过增量计划；明确变更范围后只执行对应节点。

## 用时汇报（11.17.12：每轮与每节点分别记录）

完整用法见[阶段与节点计时](references/phase-timing.md)。计时只观察真实制作，不形成新门禁、不改变已有质量证据。开工先 `T start --run-id <本轮唯一ID> --route source|handoff|returned|maintenance`，再 `T stage <1-5>`；接力先 `T status`，沿用开放节点。`T` 是 `python3 -B <skills>/cocos-game-to-english/scripts/stage_timer.py --project <工程>`。Skill 维护与游戏生产分开记，未记录区间明确写未记录。

- 命名节点按资源、图片、文字、音效、平台适配、构建、采集、反馈修复和写包分别开始/结束，汇报当前节点、执行或沿用、实耗、结果及下一节点。手工作业 `T begin 名称 --span-id 唯一ID --who 执行者` / `T end 名称 --span-id 同一ID`。同名并行各自用唯一 ID；同一任务只由一个拥有者记，不由主线程与子线程重复记。
- 命令用 `T run --span-id 节点ID --cwd 工程 --log 日志 名称 -- 实际命令 参数`：保留真实退出码、单调时钟秒数和实时输出，不自动重试。构建每一次均有记录，重试前先说明输入或原因发生什么变化。外部生成的提交至完成另用 `external-begin ID 名称` / `external-end ID`；不把服务等待当成纯工作。
- 暂停用 `pause 原因`，继续用 `resume`；取消用 `abort 原因`。等待用户用 `ask 原因` / `back`，不等待用户的中文原版试玩不记等待。中断保留未完成状态，不把隔夜空闲算成连续制作，也不倒填估计秒数。
- 预览入口在真实 ready 后自动记录“启动请求到入口就绪”，Web＋Native 内容共同确定轮次；相同内容重开沿用。不要用外层 `run` 包住常驻预览服务，否则会把用户试玩期间当制作耗时。中文入口也带 `--project`；入口未就绪不写已发布。
- 阶段结束 `T done` 时附 `--summary` 和 `--next` 并在当前聊天发结算。试玩交付与最终交付用 `T report --all`。报告区分整轮墙钟、已完成执行区间并集、工具区间、外部等待、用户等待、暂停、未记录空档。并行项和父子任务不能直接相加；开放节点不是已完成准确实耗。底层 suite 缺单项计时就写未知，不能把整个批次秒数复制给每项。
- 预算在盘点后按实际页面状态、中文素材量、引擎/环境、外部生成队列填写，作为发现卡点的参考。超过预算先定位当前进程、输入和依赖，不因超时自动全测、重启浏览器或重复构建；也不能单凭耗时判断模型出错。优化比较须同输入同范围，不能把几秒脚本差异说成整轮节省几小时。

| 阶段 | 必须分别记录的节点 |
|---|---|
| 1 盘点 | 输入身份与安全解包；环境与引擎；中文原版构建与 ready；中文/资产/平台/存档清单 |
| 2 修改 | 最长文案与内框预算；首件；批次生成与等待；切图；图文接入；原功能平台适配；音频；实际构建与局部验证 |
| 3 英文试玩 | 候选准备或复用；操作测速；倍速匹配；完整连续游玩及免费重开；页面采集路线；首次缺项检查或证据沿用；链接 ready；人工试玩交接 |
| 4 反馈 | 用户指定问题；影响范围；定点修复；只验变化或记录视觉授权；新候选与新链接 |
| 5 补缺与交付 | 已通过覆盖的只读核对；真实缺项；正式写包；本次最终 ZIP 体积/分包/CLI；同版试玩交付 |

## 并行分工（10.2.7，Saul 2026-10-31 同意）

2026-10-30 那批英化游戏都是主线程加 3 个子进程：给链接前的步数里有 21%～26% 花在线程之间传话，几个线程都在构建游戏（构建命令出现 31～40 次），Cube Digits 两次导出里还是旧图，一个子进程空等了约 27 分钟。所以：

- 子进程最多 3 个，按文件分，互不改别人的文件：
  - **美术**：所有要生成的图（按钮、标题、图片字、位图数字、ad-boost 板块的图）。只有它跑生图，整台电脑同时最多 2 个生图任务。
  - **代码**：固定入口第 2～7 项和第 9 项、平台包接入、第 8 项 ad-boost 的零件、面板和接线。
  - **文字**：代码里的字符串、Label、英文文案和用词表。
- **只有主线程**构建、导出、跑 `check_export_images.py`、起试玩链接、合并、跟 Saul 说话。子进程只交文件，不构建、不起试玩服务。
- 子进程做完报一次（改了哪些文件、还差什么），不轮询、不等别的子进程。每一轮把改动攒齐了，主线程只构建一次。
- 用时由主线程记：派活时 `T begin <步骤> --who 美术子进程`（代码、文字子进程同理），子进程报回来时 `T end <步骤>`，生成了图加 `--count 图=<张数>`（见「用时汇报」）。子进程自己不记。
- 第 5 阶段的广告回归和运行时套件只由主线程跑。
- 活不多时不开子进程，主线程自己做更快。
- 每个子进程读哪些文件见上面「读哪些文件」；主线程派活时把要用的一两条规则贴进去，子进程不整页读 TikTok 固定适配。

## 美工：第一轮按美工 Skill 照原画风重做按钮和文字

**第一轮就用美工 Skill（Saul 2026-10-31）**：英化第一轮按[美工 Skill](../remake-art/SKILL.md)照原游戏画风重新生成所有按钮和文字（范围和做法见第 2 阶段「第一轮美工」），不用等点名；首次主页先按[默认主页排版](../remake-art/references/english-home-layout.md)重新组织主次、功能分区和英文空间，合适背景与角色素材继续沿用原画风，位置和尺寸服从本轮主页方案；其他未受影响页面保留当前已批准布局。加功能带来的全部新增界面自动走[新增界面制作](../remake-art/references/new-feature-ui.md)。除首次主页和本轮明确重做范围外，既有未受影响界面的额外重新设计、换画风和改排版仍按当前任务授权。等级、关卡号、分数、货币美化，以及不显示版本号和 Credits，英化必做（Saul 2026-10-30，见 [Saul 的美术禁区与必做项](../remake-art/references/saul-art-rules.md)）。

**默认主页重排或额外要求重新设计时，画风都照原游戏**（Saul 2026-10-31，香肠太难了 Redesign v2：他说“结合广告skill和美工skill重新设计游戏”，结果原版亮橙色、薄荷绿的圆角按钮和木色金边的六边形图标钮全被换成同一种深红方块；Saul：“要按照原游戏的风格去设计美工”）：原图能用就用，要新生成就把原图放进参考图照着画；按钮底色不用深色（深红、砖红、深棕、藏青、深灰、黑这类），金币、爱心、礼盒这些物品图标后面不另加底板；原游戏本来带底座、奶油色边或高光的照原游戏。只有他明说换画风（例如“按重塑画风重做”）才换。用 ad-boost 加的新板块也一样，面板和图标跟原游戏走。

**重做美术先出小样（Saul 2026-10-31）**：Saul 额外要求更换画风或明确要求多套设计方案时，先出小样，不直接做整套：出 2～3 套，每套 1 张首页加 2 个按钮（主按钮、看广告按钮），其中一套是「保持原画风，只改英文和新入口」；30 分钟内发小样图给 Saul 挑，已按第 3 阶段验收的同版候选也可给正式试玩链接，他选了再做整套，都不满意就再出几套。等他选的时候接着做不碰美术的部分（广告入口、代码）；小样发出前按下文查，做成可玩英文链接时仍按第 3 阶段完成美工检查。小样和 Saul 选的那套记在 `docs/samples/samples.json`。小样这样做（Saul 2026-11-01「把这三点补进v7.9一起改」）：
- **给 Saul 挑的是做出来的样子**：每套的 2 个按钮和标题单独生成，按计划显示尺寸摆进游戏真实首页，截图给他挑。不拿一次画出的整页效果图给他挑：整页图上的字常是乱的，排版也和真页面不一样，挑中以后按钮一张张生成再拼进游戏，会和效果图对不上。整页图可以拿来定方向、当生成按钮的参考图。
- **每套先过美术检查再给他看**（以下两行是小样的重点项；正式制作时按第 3 阶段处理真实画面问题）：摆好以后 dump 这一页跑 `art_check.py`，「按钮底色不深、物品图标不另垫底板」和「深色粗字（永久禁止）」两行不过的那套，先改好或换一套。这样用户在挑选时看到的就是实际接入效果。
- **挑一次就定死**：仅本节明确需要用户挑多套风格或方案的任务在开工时挑；默认首次主页的一个原画风排版样板由主 Agent 自审后继续；之后每轮美工不再重新挑。选定以后把这套的颜色（HEX）、材质、圆角、描边写进 `docs/samples/samples.json` 选中的那套；之后每个按钮都带这套的截图和 2 个按钮当参考图生成，先做 3 个放进游戏看对不对，再批量做。
