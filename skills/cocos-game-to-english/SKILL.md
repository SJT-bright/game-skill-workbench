---
name: cocos-game-to-english
description: "英化（触发词：英化、英化skill、中文源码、翻译成英文、英化这个游戏）。拿到能运行的中文Cocos完整游戏时用：开工先给中文原版的手机试玩链接（不等回复）；把中文美工和文字改成英文（第一轮按美工板块 remake-art 照原画风重新生成所有按钮和文字）；补齐固定入口（个人主页回访、添加桌面、音效/BGM音量、关内暂停键、结算页看广告双倍与Retry、看广告复活），删除分享/更多游戏/联网排行榜；看广告的几项按包里的 remake-ads、remake-economy 做，看广告的板块默认按包里的 ad-boost 诊断后按推荐加，不问 Saul；先过美工检查和中文专项检查，再给英文试玩链接和人工检测清单；Saul 试玩没问题后核对覆盖、只补缺项并出包；也接收已完成源码和测试包，沿用可核验记录；macOS、Windows 都能用；浏览器测试仅使用 Ego，Chrome 只供用户试玩。默认不改玩法、不加关卡、不加新系统。"
---

**当前检查执行规则（用户 2026-11-08）**：先读[一次通过、按改动复验](../remake-core/references/incremental-checks.md)。图片、文字/字幕、音效、玩法、关卡、平台检查均按命名节点留存真实记录；已通过且依赖未变的项禁止重复执行，代码或配置变化也不触发全量。浏览器和写包读取同一计划；旧文中的“每次必跑/全量检查”改按完整覆盖核对解释。最终 ZIP 的本次体积与分包核对按用户单独要求保留。

**完整美术回执已撤销（用户 2026-11-08）**。美术制作和实际画面问题按首次制作或受影响的节点处理，保留各项实际结果。常规与轻量写包、正式试玩、最终交付均不得生成、补齐、更新或要求完整美术回执，也不以全量图片复核、截图汇总或人工重新确认作为替代条件。已通过的游戏局部返工只检查该改动影响的节点。最终 ZIP 分包、体积、配置和同版链接核对按原规则执行。

**人工画面检查（用户 2026-11-08）**。发同版试玩时给[人工试玩画面清单](../remake-core/references/manual-visual-review.md)中的适用项目。常规美工、启动计时及写包取消默认录屏和 AI 总览图签收，偶发问题按需短录。原资源中文专项、技术检查和版本核对按对应规则执行。

已交付后用户指定改完即出包时，按[返工交付与人工快查](../remake-core/references/returned-art-delivery.md)处理这次改动，实际记录与用户验收分开。


> 2026-11-01 用户更新：Grok 图片识别已停用。本文任何 Grok 读图、OCR、截图转录或 `grok-image-review` 路由均失效；所有读图由 Codex 自己直接查看并完成。文本搬取等非图片任务按各自规则执行。

# 英化（独立流程）

## 浏览器测试路线（用户 2026-11-06，取代旧回退规则）

所有 Agent 浏览器测试必须在 **Ego Lite** 独立 TaskSpace 中执行，包括截图、美术、手机触摸、声音、存档、广告、回归、链接冒烟和出包验收。**Google Chrome 只用于交给用户亲自试玩的本地链接。** Ego 故障先在 Ego 内排查；能力不足保留未测，不自动或沿用旧授权切换 Chrome/Edge/Chromium，不用 Playwright 或伪装 Ego 的启动器补测。离线检查继续使用本地工具。详见[浏览器测试规则](../remake-core/references/browser-testing-policy.md)。

修订：`2026-11-08.english-simple.11.17.13`（回访和桌面入口直跳，人工快查替代常规录屏，撤销完整美术回执。历次改动见[版本历史](版本历史.md)。）

共用功能验收与故障复验按[实际触发与玩家结果](../cocos-game-check/test/README.md)选测。

**减少美工返工（11.17.5）**：开工先按[采集清单审查](../remake-art/references/art-iteration-workflow.md#开工先审采集清单)定下独立画面状态、可合并项和可沿用项，再开始首轮采集。第 2 / 4 阶段按[少返工的制作与采集](../remake-art/references/art-iteration-workflow.md)盘点共享用途、定 CSS / 字体预算，显式选首件整页检查后再铺同类；每批结束或失败时按工具计划分清原料、接入、构建与采集原因。同因修正合批，保持有效轮次，连续采新截图；旧图沿用仍由原采集门禁决定。只做美工，不扩大玩法；首次试玩前按范围核对美术，后续只复验受影响的项目。

**美工制作即检查（11.17.2）**：第 2 / 4 阶段按[制作与检测共用证据](../remake-art/references/production-check-link.md)执行。固定按钮和切片由生成工具登记约束，第一件接入即调用原图文/像素检查；第 3 阶段复用输入与规则均未变化的计算。首件在制作节点完成，中文专项仍随正式试玩候选执行。

**独立图标防放大（11.17.4）**：视频图标、勾、乘号、关闭符号和图文按钮在制作前明确角色与显示槽，首次接入按[独立显示预算](../remake-art/references/local-ui-contract.md#高清图标接入时锁定独立显示预算)登记受影响视口；源 PNG 分辨率不作显示尺寸。图标位置与文字净空以真实 Art 底板为准，尺寸正常不能代替内框和图文间隔通过。使用 ad-boost 面板时先执行[模板显示槽规则](../ad-boost/references/art-display-slots.md)，批量生图前运行调用集回归；不能把乘号当作勾、把烘焙在图里的图标再叠一份。

**每次给测试包都复查分包体积（用户 2026-11-05）**：新旧、外来、同版重发、仅改名或用户仅索取已有文件均不豁免；交最终 ZIP 前按[统一检查的本次体积复查](../cocos-game-check/package-check/references/fresh-upload-size.md)重新读最终文件并生成新回执。不复用旧体积结果，不以 CRC/哈希或 Web 可玩替代；局部返工只查改动也不能跳过本项。失败/未跑不交包，已被平台拒绝的同字节 ZIP 不得原样重发。

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
- ② 修改：做下面「只做这几件事」的 9 项。第一轮美工照原画风重新生成所有按钮和文字，第一个英文链接前完成实际可见的全部中文图文及相应美术覆盖，已通过项直接沿用；第 8 项 ad-boost 按诊断完成本轮计划的接入和美工。
- ③ 英文试玩链接：按第 3 阶段完成首次或受影响的美工检查，执行中文专项检查（`chinese_audit.py` 扫描、看清要复核的几项、check 通过；不过不给链接，Saul 2026-11-01），再确认能进首页、能玩一局、没有报错卡死，就给链接，回复里直接打出人工检测清单。
- ④ 试玩改进：每轮起新链接前照样过中文专项检查（只识新加和改过的图），同时复查受影响整页、共享组件和新增页面的美工，过了再给链接；改动功能的局部验证随实现完成，其余未覆盖的检查在相应制作节点执行一次，第 5 阶段只核对旧证据和补缺。Saul 说的一次改完，每轮起新链接；首轮已完成的页面和第 8 项板块保留有效记录。
- ⑤ 补缺与出包：Saul 说没问题后核对适用项覆盖，只执行缺项及真实改动项，用写包入口出包。测试包交了以后再改（返工），只查改到的部分，不从头再查（见第 5 阶段「出包后返工」）。

每一步的细节在下面「阶段」一节；要读哪些文件见「读哪些文件」。每个命名节点开始、完成、失败或变更范围时均报告当前动作、执行或沿用、实耗、结果和下一节点；每阶段结束汇总用时，见「用时汇报」。

**必须遵循（Saul 2026-10-29）**：TikTok 固定适配（触摸、启动加载、激励广告、存档读值、适配层、图片、加桌面/回访、登录/App ID、胶囊/首页底排/不要 Credits）和跨游戏通用流程一律按 [TikTok 固定适配](../cocos-game-check/references/tiktok-fixed-adaptation.md) 做：英化一律加看广告复活，核心玩法里的分享奖励改激励视频、其他分享入口删掉，加桌面/回访奖励各 5B；新游戏只用平台包标准件，不手写；旧游戏只给警告，由各自会话处理。

拿到的是一个能运行的完整游戏。默认保留原工程、原玩法、原关卡、原画风、原声音和存档；不补关，不加经济、皮肤、礼盒、签到、教程等系统（看广告的板块由 ad-boost 默认加，见第 8 项）。关卡、皮肤、引导板块不主动调用；广告板块只用在下面「看广告的几项按广告板块做」写的几处（不用 Saul 点名），货币板块只用来算这几处和 ad-boost 板块的数额，原游戏的价格和其他数值不改。第 4 阶段 Saul 试玩时点名要改的玩法、手感、难度和数值，照他说的改，只改他点名的。

**创新玩法（Saul 2026-10-30）**：Saul 要求给英化游戏加新玩法时，算单独任务。新加的部分用现成的板块做：广告 remake-ads、货币 remake-economy、皮肤 [remake-skins](../remake-skins/SKILL.md)（本包自带；皮肤一定连着货币和广告，新加皮肤就要同时有货币、看广告解锁款和看广告试用弹窗，Saul 2026-11-04）；关卡 remake-levels、引导 remake-onboarding（在重塑包里；只装了英化包的电脑要先装重塑包）。不另写一套，这样不容易出新 bug，做过的也能复用。只做 Saul 点名的部分，原有玩法照旧不动；加关在关卡表写 `explicit_total`，新加的部分照对应板块的检查查，在对应制作节点检查一次，第 5 阶段核对其有效记录；新加部分的美工仍须在英文试玩链接前按第 3 阶段检查；新增功能先按[前期预防](references/early-prevention.md)做局部验证，玩法、经济等检查随对应制作节点完成，第 5 阶段只补缺和核对已通过记录。

## 换电脑也能用（10.2.10，Saul 2026-10-31）

英化包供 macOS 和 Windows 使用。开工先检查本机依赖。没有可用的 Ego Lite 时，浏览器相关项目记为未测，离线检查可继续。

- **「Saul」是谁**：本包写的「Saul」指正在用这个 Skill 的人（给你游戏、试玩、做决定的那个人）。「Saul 定的」规则照样遵守；回复照样用大白话，要他定的只出选择题，跑命令、找路径、装东西都由你来做。
- **开工先查电脑**：第 1 阶段第一件事跑 `python3 <skills>/cocos-game-to-english/scripts/check_machine.py --project <中文原工程>`，一分钟内查完 Python、Pillow、numpy、ffmpeg、Node.js、出包检查用的浏览器和这款游戏的 Cocos Creator。缺必须的，用大白话告诉用户缺什么、影响哪一步，问一句能不能装；同意后由你来装，装好再跑一次。缺的东西不影响的步骤先接着做。它打印的第一行「引擎路线」不是「照常开工」时，先照它做（2.0～2.3 复制一份副本升到 2.4.15；3.0～3.5 先装同一小版本的 Creator 导出原版），零件只装它列出的那些，再做别的。它报「Cocos 编辑器配置能解析」不通过时，先关 Creator，把报出的文件改名备份，再开 Creator。
- **Cocos Creator**：不假设装在哪。用 `find_creator.py --project <工程>` 找本机的编辑器、拿 2.x/3.x 对应的构建命令；构建前跑 `find_creator.py --busy`（整台电脑同时只跑一个构建）；3.x 的 web-mobile 导出缺 `index.html` 时跑 `fix_web_entry_3x.py --export <导出> --project <工程>`。没装工程那个版本怎么办、各版本的已知问题，见 [Cocos Creator 版本和已知问题](references/local-creator-versions.md)。
- **浏览器**：浏览器测试、截图、美术、试玩链接冒烟及出包命令用 `python3 <skills>/cocos-game-to-english/scripts/browser_env.py -- <命令>`；启动器只选官方 Ego，不创建 Chrome 替身、不回退 Chrome。没装或起不来时按 ego-browser 指南诊断并保留未测。用户试玩由 `serve_preview.py --keep` 另开独立 Chrome 手机框。
- **自己看画面**：首次进首页、开始一局及后续视觉验收均在 Ego 中完成；没有 Ego 或操作失败时先修复 Ego 环境，不使用 Chrome 补验。
- **Windows**：`python3` 写成 `python`（或 `py -3`）；路径有空格或中文时整段加引号。本包和 ad-boost 里 macOS 才有的写法换掉：`pgrep` 用 `find_creator.py --busy`；`/usr/bin/python3` 用 `python`；`cp -c`（macOS 的快速复制）用普通复制；`open -R`（在访达里选中文件）改成直接给完整路径；构建卡住时加的 `--no-sandbox --disable-gpu-sandbox --disable-gpu` 是 macOS 的写法，Windows 先不加。
- **浏览器卡住和构建沙箱**：浏览器命令可用 `browser_env.py --game <游戏名> --report <文件> -- <命令>` 记录路线。Ego 卡住时保留首个错误，在 Ego 内排查；不能自动换 Chrome。构建前先跑 `find_creator.py --preflight`，退出 3 就别构建、也别重试，换不受沙箱限制的终端；构建命令照 find_creator 打印的原样用（TikTok 那条前后各带一次 sync，sync 没过不构建；3.x 出包命令带 `configPath=docs/startup/build-config-3x.json`），别删末尾三个参数，也别只复制 Creator 那半条。
- **试玩链接打不开窗口**：`serve_preview.py` 会试着开一个 Google Chrome 窗口；没装 Chrome 时窗口不开，服务照样在。把 `http://127.0.0.1:端口/` 链接发给用户，用户用任何浏览器（Edge、Safari 都行）打开。
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
- **不用读**：皮肤板块 remake-skins 和重塑包的关卡、引导板块（创新玩法时才读）；`remake-core/references/` 里的总规则（检查报错指过去时只读那一页）；ad-boost 没加的板块。
- **子进程**（见「并行分工」）：美术只读第一轮美工那三页；代码只读固定入口、[平台包接入说明](../remake-core/assets/platform-kit/README_接入说明.md)、「看广告」一节和 TikTok 固定适配第二部分；文字只读英文界面重建和商标词表 `remake-core/assets/trademark-words.json`。主线程派活时把要用的一两条规则贴进去，子进程不整页读 TikTok 固定适配。

## 只做这几件事

逐项判断这个游戏要不要做；不需要做的写一句原因跳过。

| # | 做什么 | 说明 |
|---|---|---|
| 1 | 中文改英文 | 代码字符串、Label、平台文案改成自然英文；中文图片字和带字的按钮第一轮就按[美工 Skill](../remake-art/SKILL.md)照原画风重新生成英文版（尺寸、描边、颜色、位置跟原图一致，见第 2 阶段「第一轮美工」），换字体并确认放得下。**句子（说明、教学、提示，两个以上单词）用真正的英文字体（TTF），不许用生成的字母图集拼句子**——那样小写会被画成大写，出现 HelP/TaP/Pond；图片字只用于固定短词和数字。**等级、关卡号、分数、货币、奖励数（Saul 2026-10-30："这种是所有游戏都需要进行的"）**：原版不管是图片字还是普通字，英化后一律按原画风做成"图片字的词（LEVEL、货币名）＋生成的 0-9 位图数字＋货币图标"，不能是一整行英文普通字（反例："LEVEL 1 • +10 PEARLS" 白字压在半透明色条上）；数字后面也不铺纯色色条。`art_check.py` 的 `font_number`、`font_value_label`、`flat_value_plate` 在英化游戏同样拦，登记成运行时文字也不豁免。设置页不显示版本号和 Credits（`dev_info_text`）。**品牌车名、动漫角色名不直译**（v7.8 E8：「法拉利458」不写 Ferrari 458，写 Supercar 这类通用叫法），`audit_copy_quality.py` 按 `remake-core/assets/trademark-words.json` 拦，并写出命中的词。改完全屏扫一遍，不许残留中文（含角落小字）。规则见 [英文界面重建](references/english-ui-rebuild.md)、[动态文字字形](references/dynamic-text-glyph-review.md) |
| 2 | 首页加两个功能键 | 个人主页回访（Revisit from Profile）、添加桌面（Add to Home Screen）。**原首页按钮全部不动**，只在原布局空位加这两个；所有环境都显示、不隐藏（本地试玩也显示）；**点一次立即调用对应平台入口**，没有说明弹窗、过渡提示或手动领奖键。Studio 和 Web 保留两个按钮，缺能力、失败或取消时安静结束，可再点。玩家从对应入口回来、平台确认资格并存档成功后自动发奖，奖励各 5B（一次首页礼盒基础奖励，换算成原游戏货币）。原游戏没有金币的（Saul 2026-11-04）：有体力的各发体力 +3；金币体力都没有的，先加一种金币和皮肤给它当花处，再发 5B（[经济规则](../remake-economy/references/economy-rules.md)第三节末尾）。|
| 3 | 设置里两个音量 | 音效（SFX）和背景音乐（BGM）分开调节、立即生效、重启后保留 |
| 4 | 删除三类功能 | 分享给朋友、更多游戏、排行榜：按钮、入口和相关代码调用全部删掉，删后页面不留空洞。**例外（v7.5，Saul 在细菌2048 的选择）**：原游戏核心玩法里的分享奖励（复活、礼物、双倍）改成激励视频；其他分享入口连同触发它的礼物球、弹窗一起删干净。不许留“本平台不可用”的提示按钮；每个分享调用在 `docs/` 写明删掉还是改成广告。**局内本地名次可以留（Saul 2026-10-31，照 68 小熊拳击）**：一局里玩家和电脑对手的名次（局内分数牌、结算名次）、按名次给的本地奖杯和段位、个人星级和最高分都不算排行榜；数据只存本机、不联网，匹配页写 Finding opponents，电脑对手不用真人风格的名字，段位叫 Tier 不叫 League。要删的是联网的世界/好友/地区/周榜（含开放数据域）、本地编出来的全服名次（如 “You are #3,512”、“Top 5%”）和假联赛；`remake-core/scripts/audit_no_social_features.py` 按这个口径查。见 [固定入口](references/fixed-entries.md) |
| 5 | 修正操作 | 原来操作有问题的位置改好（点不到、点了没反应、改动后某处操作消失要补回）；不新增玩法 |
| 6 | 每关结算页 | 有 Retry；统一加 **Watch Ad x2** 入口，是结算页上最大、最显眼的按钮；普通领取（Claim）是它正下方一行可点的小字，不做成第二个按钮（Saul 2026-10-31）。见 [固定入口](references/fixed-entries.md)；样子按[广告板块·结算页设计](../remake-ads/SKILL.md#结算页设计用户-2026-10-27)，广告行为和 x2 数额按广告、货币板块（见下面「看广告的几项按广告板块做」） |
| 7 | 看广告复活 | 有失败/中断的一局都加“看广告复活”；**没有失败状态的游戏也加**（按 MusicSlice v30 的能量条做法）。单独一节，见 [固定入口·看广告复活](references/fixed-entries.md#看广告复活单独一节可整节删除)；实施和检查按广告板块（见下面「看广告的几项按广告板块做」） |
| 8 | 广告加量（ad-boost） | 默认做，不问 Saul（Saul 2026-10-31）：按本包的 [ad-boost](../ad-boost/SKILL.md) 诊断这款有几个看广告的地方，按推荐加看广告的板块（转盘、礼包、签到等）：广告量少加 3 个、一般加 2 个、多加 1 个。原首页按钮不动，新入口只放空位，画风跟原游戏。做法见下面「默认按 ad-boost 加广告板块」 |
| 9 | 关内暂停键 | 每个模式的关里都要有暂停键或设置键，点开暂停窗有 **Continue**（一下就关、接着玩）、**Restart**、**Home**（规则一直有：[逻辑规则](../cocos-game-check/test/references/logic-rules.md)「关卡内（HUD）」一行；以前不在这张表里，割草 v015、人鱼 v18 英化后关里没有暂停键，出包被拒）。原游戏有暂停 / 设置窗的保留原样，缺哪个按钮补哪个；只有返回键、回首页键的加一个暂停键，不改玩法。暂停窗开着时计时、物理、生成都停。暂停页、复活页、结算 x2 页用 GameUIKit 的 pausePage / revivePage / resultPage 生成，别手写；英化游戏把 RunSession 只接在这几页上（原版玩法代码不动），没有 RunSession 的原版游戏不传 session，在 onResume / onRestart 里接原版的暂停和重开函数。见 [固定入口·关内暂停键](references/fixed-entries.md#关内暂停键v79-手机问题源头约束英化第-9-项) |

## 看广告：固定几项按广告板块做，第 8 项默认加 ad-boost 板块

**看广告的几项按广告板块做（Saul 2026-10-31）**：英化自己要做的广告的事，自动按本包的[广告板块 remake-ads](../remake-ads/SKILL.md)做，数额按[货币板块 remake-economy](../remake-economy/SKILL.md)，不用 Saul 点名：

- 第 6 项结算 Watch Ad x2：x2 是结算页上最大的按钮，Claim 是它正下方一行可点的小字，样子和位置按[结算页设计](../remake-ads/SKILL.md#结算页设计用户-2026-10-27)表里「看广告 ×2 按钮」「直接领取」两行（Saul 2026-10-31）；看完到账、取消/失败/超时停在结算页且 Claim 仍可点、只发一次，按[共用的广告设计](../remake-ads/SKILL.md#共用的广告设计)的结算一行；数额按[经济规则·货币和结算×2](../remake-economy/references/economy-rules.md#二货币和结算2)（基础已发只补差额；没有货币的游戏翻倍本局捡到的道具）。
- 第 7 项看广告复活：按[复活审查](../remake-ads/references/rewarded-revive-and-help-layout.md)的实施和检查做（英化一律加，不用再审要不要加；页尾的小型教程英化不做）；复活页用 GameUIKit 的 `revivePage` 生成（只认看完），别手写；复活页 → 结算页的顺序按[一局结束：每屏一个视频按钮](../remake-ads/references/end-flow-one-video.md)。
- 原游戏自带签到、转盘、礼包领奖窗时的看广告双倍勾选框：按广告板块共用表那一行和验收清单；数额按[经济规则·第四节](../remake-economy/references/economy-rules.md#四七日签到的数值用户-2026-10-27)末尾（有数量的项 ×2，皮肤不翻倍）。
- 原游戏已有的看广告入口改接平台包、广告计时、`qa/ad-regression.json`：按[广告机制](../remake-ads/references/ad-mechanism.md)和[超时规则与广告回归](../remake-ads/references/ad-timeout-and-regression.md)。

其他页面和按钮仍按本页和[固定入口](references/fixed-entries.md)（原游戏的保留，结算页上原有的按钮不能比 x2 大）。其他看广告入口不另外按广告板块加，由第 8 项 ad-boost 默认按诊断推荐加（见下面「默认按 ad-boost 加广告板块」），广告行为照广告板块。

**默认按 ad-boost 加广告板块，不问 Saul（Saul 2026-10-31：英化 Skill 融合广告 Skill，默认执行，不需要询问）**：每款英化游戏在第 2 阶段都跑本包带的[广告加量 Skill ad-boost](../ad-boost/SKILL.md)，不用等 Saul 说「广告太少」。本机 `~/.kiro/crew/skills/ad-boost`、`~/.codex/skills/ad-boost` 或 `~/.claude/skills/ad-boost` 有比本包新的版本（`CHANGELOG.md` 第一个版本号更大）时，用新的那份。
- 做法：照 ad-boost 流程 ⓪（这台电脑第一次用先跑 `scripts/doctor.py`）和 ①（`scripts/diagnose_ads.py` 加 `--mode localize`）。**跳过 ② 和 ③：不出选择题、不问 Saul**，直接按诊断的推荐顺序加：广告量「缺必备」或「少」加前 3 个（带 ★ 的），「一般」加前 2 个，「多」加第 1 个。再照 ④ 一个一个装：零件（装完跑 `assemble.py --verify`）、面板、音效、按原游戏画风生成美术、接线。复活和结算 x2 照第 6、7 项做。**时间（用户现行要求）**：第一个正式 Native 英文试玩链接前完成 ⓪ ① 和本轮计划的 ④ 安装、美工与接入验证（见第 2 阶段「第一轮美工」）；后续新增或改动的板块在对应轮次发链接前通过受影响项检查，已通过项不重测。
- 哪些不加：诊断「不推荐」的不加；道具补给、皮肤看广告、体力 +3、商店看广告免费领、任务/成就领奖 x2 只在原游戏本来就有这个系统时才加（诊断已经按这个排）；奖励关会动原关卡，不加。
- 授权：英化本来不加新系统，**这几个看广告板块是 Saul 2026-10-31 定的默认例外**，不用再问。Saul 试玩后说不要哪个，就把那个板块拆掉（入口、面板、广告位）。
- 首页：**原首页按钮一个都不动**（不挪、不缩放、不重排），新入口只放空位，不压原按钮和首页上方的大图。**没有空位时不问**，换推荐顺序里下一个不用首页入口的板块（局内漂浮礼物、道具补给、开局增益这类）。接线前后各截一张同一手机尺寸的首页（`docs/adboost/home_before.png`、`home_after.png`），加入试玩链接前先对比，确认原按钮没有被遮挡或移动。
- 画风和数值：新板块的面板、按钮和图标跟原游戏画风走，排在主要页面的图后面生成（整台电脑同时最多 2 个生图任务，ad-boost 的 `gen_images.py` 管）。数值只用 ad-boost 各板块 README 第 5 节的已定数值（数额按货币板块），原游戏已有的数值不改；板块数值没有默认时不问，换下一个推荐板块。
- 检查放哪：ad-boost 新面板、按钮、图标、布局及按钮可达性的美工检查，放在带上该板块的英文试玩链接之前；接入时先验证本次操作的奖励、保存和防重复结果；各板块 README 第 8 节的验收及广告回归按命名节点随接入完成一次，第 5 阶段只核对完整覆盖并补缺或复验真实受影响项。试玩链接照本页第 3 阶段起，ad-boost ⑤ 的试玩宿主只在没有 web-mobile 版时用；出包照本页第 5 阶段（`--board localize`）。
- ad-boost 里写英化要等 Saul 在选择题里选、没有空位时问 Saul、交付记录写「在选择题里的选择」的地方，英化游戏以本页为准。
- 交付记录写一行：「XX、YY 板块按英化默认做法加入（Saul 2026-10-31：英化默认执行广告 Skill，不用询问）。」

## 阶段

**前期预防（Saul 2026-11-04）**：第 1 阶段读取[前期预防](references/early-prevention.md)，把条件状态、共享组件使用者及改动涉及的保存/接入信息补进已有记录；第 2 / 4 阶段按该页先确认代表件实际状态，再批量制作，改动功能就地核对结果与重载。下文“第 5 阶段检查”指核对完整覆盖、补缺及最终写包，不推迟这些制作和接入时的局部验证，也不重复已有有效记录。

**先查美工，再给英文试玩链接（Saul 2026-11-03）**：顺序是 ① 盘点＋中文原版链接 → ② 英化、第一轮全部美工及 ad-boost 诊断和接入 → ③ 导出核对、中文专项检查、制作范围内的技术美工检查，修复并复查通过后给英文试玩链接＋人工检测清单 → ④ 试玩改进，每轮给新链接前复查受影响整页、共享组件和新增页面；新增 ad-boost 板块也先查再带入链接 → ⑤ 用户确认后核包文件与同版身份，功能按影响补项后出包。制作节点核对适用技术项，发现的排版、图片和按钮问题先修好。画面观感按同版人工快查；广告回归 10 例、运行时套件、`preflight.py`、已知问题与平台兼容仍须完整覆盖，各项在对应制作节点执行一次；第 5 阶段和写包入口读取同一记录，只补缺项或复验真实受影响项。英化试玩与交付按本页现行技术核对和人工快查分工执行，以本页为准。

**用时（10.2.12）**：每个阶段开始跑 `T stage <N>`、做完跑 `T done`，中间每一步记 `T begin`／`T end`，`done` 打印的用时发给 Saul。`T` 是 `python3 <skills>/cocos-game-to-english/scripts/stage_timer.py --project <工程>`；什么时候跑哪一条、步骤叫什么名字，见下面「用时汇报」。

1. **盘点**：**中文源码不带 .git（Saul 2026-11-04，91 SLS11）**：91 卖家给的 SLS11.zip 带着完整的 `.git`，提交记录里有上架文案 `app_desc.txt`（开发者账号和密码）。中文源码一律用 `python3 scripts/unpack_source.py --source <中文源码.zip 或文件夹> --out <新的工作目录>` 放进工作目录，不要直接 unzip / cp：`.git` `.svn` `.hg` `.idea` `.vscode` `__MACOSX` 不拷，`app_desc.txt`、`.env`、签名证书和私钥不拷，文本里像账号密码的行（比如 `settings/project.json` 的 `appSecret`）列在 `docs/source-intake.json`，交源码前把值清空。原 ZIP / 原文件夹不动；`unpack_source.py` 还会先把原包复制进游戏文件夹的只读 `_原始输入/`（只有 Saul 自己能删）。清理旧版本只用 `python3 <skills>/remake-core/scripts/clean_old_versions.py`，不手写 `rm -rf`。开工打印「已装 Skill 被改过，请走补丁」时，把列出的改动写成补丁交 Skill 会话，不要接着直接改已装文件。要交源码时用 `python3 <skills>/remake-core/scripts/make_source_zip.py --project <工程> --out <游戏_Source.zip>`（不带上面这些，带凭据就拒绝），`prepare_delivery.py --source` 和两个写包入口按同一规则拦（`source_hygiene.py`、出包门禁 `H1_vcs_ide_in_package` / `H2_credentials_in_package`）。
   **开工先给 Saul 中文原版的手机试玩链接，不等回复，接着往下做**（Saul 2026-10-31）。在中文原工程的一份副本上导出 Web（复制到工程外再导出，原工程一个文件都不动；用原游戏对应版本的 Creator 命令行：先跑 `check_machine.py --project <中文原工程>` 查电脑，再用 `find_creator.py --project <副本>` 找本机的编辑器、拿构建命令（见上面「换电脑也能用」和 [Cocos Creator 版本和已知问题](references/local-creator-versions.md)：没装那个版本先用同一小版本里最近的；2.4.3 要先放进本包的构建扩展再加 `--use-gl=desktop`；3.x 导出缺入口页时用 `fix_web_entry_3x.py` 补），其他写法见[真实 Cocos 运行](../remake-core/references/cocos-runtime.md)：2.4 是 `--path <副本> --build "platform=web-mobile"`，3.x 是 `--project <副本> --build "platform=web-mobile"`；macOS 命令行卡在导入资源时加 `--no-sandbox --disable-gpu-sandbox --disable-gpu`；原工程里已经有没改过的 `build/web-mobile` 也可以直接用），把导出的 `web-mobile` 整个复制到游戏文件夹的 `本地试玩_中文原版（不用上传）/`，再在后台起链接：`python3 <skills>/cocos-game-to-english/scripts/serve_preview.py --directory "<游戏文件夹>/本地试玩_中文原版（不用上传）" --snapshot --open --idle-minutes 0 --chinese-original --name "<游戏> 中文原版"`（`--chinese-original`：这是中文原版，不做中文专项检查；不加它，英化入口的 `serve_preview.py` 会当成英文链接去查，找不到英化工程就不起）。原版不用 `--keep`：原版没有美术回执，广告也还没接平台包，看广告冒烟对它没有意义。服务先读回实际入口字节，再用 Chrome 交给 Saul 亲自试玩；中文原版不启动 AI 自动截图、广告冒烟或反复浏览器检查。导不出 Web 时（引擎版本不对、构建报错、只有小游戏包没有源码），把原因写给 Saul，同样接着做。这份导出后面截中英对照图（`docs/baseline/`）也用。然后跑 `python3 <skills>/remake-core/scripts/tiktok_finalize.py init --project <中文原工程> --board localize`（写新游戏标记 `.tiktok-kit/policy.json`），再跑 `tiktok_finalize.py inventory --project <中文原工程>`，它把原版里的广告、加桌面/回访、触摸、启动、存档、分享/跳转/统计、登录代码逐项列到 `docs/english/platform-inventory.json`，第 2 阶段按它逐项改。inventory 之后马上跑 `tiktok_finalize.py rewire-ads --project <英化工程>`，再跑 sync；原版广告和加桌面/回访奖励由它改线，别手写桥；剩下的按 platform-inventory.json 的 rewire_todo 手改，delete_list 照单删（见 [rewire-ads](../remake-core/references/rewire-ads.md)）。3.x 游戏也一样跑 rewire-ads；`rewire_todo` 里 ad / ad_call / ad_handler 的行清零才往下做，别自己写浏览器里直接发奖的分支。和 `audit_new_english_images.py --make-list <工程> --out <工程>/docs/art/original-images.json` 放在同一步做。然后列出全部中文（文字和图片字）、首页现有按钮、设置项、结算页、分享/更多游戏/排行榜入口、已知的操作问题。存档也在这一步盘点：跑 `python3 <skills>/remake-core/scripts/make_save_schema.py --project <工程> --inventory`，把原游戏所有存档键写进 `docs/save/save_keys.json`，关卡进度、金币、已买皮肤没存档的写进待改清单；原游戏有关卡文件时跑 `make_level_plan.py --project <工程> --record-level-files '<关卡文件 glob>'`。再跑一次 `fit_english_labels.py --project <工程> --dry-run`，哪些槽放不下最长的译文、要多宽，写进首件清单。把中文原名和英文名都写进 `docs/copy/glossary.json` 的 `"game_name"`（一定要写）：出包时 `game_name_scan` 用它比对 Label 文字和中文专项检查已经识出的图片文字，11-05 起开工的英化游戏有命中就拦，更早的只警告（见第 2 阶段「游戏里不放游戏名」）。`audit_new_english_images.py --make-list` 写出的 `art-replace-round1.json` 里，`regenerate` 带 `title_logo` 的那张是原游戏的标题 logo：第一轮按它的 prompt 画成主角、图案或场景，不写游戏名，也不要译成英文 logo。`platform-inventory.json` 的 `audio_todo` 列的是原游戏自己的声音入口（播放调用、平台音频对象、音乐和音效开关读写）：英化时把它们全部改走平台包 `AudioService`（音乐和音效分开开关），`audio_todo` 清零；`audio_summary` 有 `one_switch_suspect` 时，先确认音乐开关有没有连音效一起管，设置页两个开关各试一次。`reward_todo` 列的是原游戏自己加钱、扣钱、改道具的地方：英化时每条改走 SaveStore `grant`（发奖）或 `ShopTx`（扣费换东西），只改发奖和存档的写法，玩法不动；顺序固定为「凭证 → 保存读回 → 刷新界面 → 播动画」，动画回调里不发奖、不存档；x2 只算一次基础整数，显示和到账都读它的 2 倍；局内已进钱包的收益，结算时不再发一次。sync 报 `K_W_reward_*` / `K_W_x2_rounding_mismatch` 时照提示改。盘点原版时顺手查调试和别家残留：跑一次 `tiktok_finalize.py source`（会跑 `debug_leftover_scan`），把开着的 debug/cheat/test 按钮设成 inactive 或删掉，删掉能打开 FPS 统计的代码，原工作室开屏（启动场景里开局计时后自己淡出的节点、写着某某 Games/Studio 的字）直接去掉，让首页一出来就能点；平台配置的 App ID 和广告位只用平台包模板里的共用测试 App 或本游戏 `docs/platform/platform_ids.json` 记的，不留原游戏或别的游戏的。遗留名单上的旧英化游戏（射击高手、音乐消消乐等）继续做新版本时不跑 `init`，按旧游戏出包（拿不准就先跑 `tiktok_finalize.py decide --project <工程>` 看判定）；要改用标准件才跑 `tiktok_finalize.py adopt --project <工程>`。用时：开工第一件事先 `T start --run-id <本轮唯一ID> --route source` 再跑 `T stage 1`，中文原版链接用 `serve_preview.py --chinese-original --project <工程>` 起，它自动记「中文原版链接」（没带 `--project` 或没记上时手动跑 `T mark 中文原版链接`），盘点做完跑 `T done`，用时发给 Saul，不等回复，接着做第 2 阶段。

   **标准件开工就装，每次构建前自动同步（生成时预防 P02/P05）**：`init` 之后紧接着跑一次 `python3 <skills>/remake-core/scripts/tiktok_finalize.py source --project <英化工程> --board localize`，再跑 `tiktok_finalize.py sync --project <英化工程> --board localize`，以后**每次构建前**都先跑 `sync`（约 1 秒，只把平台包文件按哈希换回原样、装上 `GameUIKit.js`，不动图片）；TikTok 小游戏包的构建命令照 `find_creator.py --project <英化工程>` 打印的整条用：构建成功后它自动跑 `sync --project <英化工程> --board localize --native <构建目录>`，把启动件、触摸修正、存档层、宿主接口兜底 host-shim、3.x 启动看守和 guard 装进这份构建（不手写 game.js 那几行），别只复制 Creator 那半条，不然包里没有 guard，出包时会报 `K_W_rewarded_guard`；sync --native 没过就先改它报的问题，别拿这个构建出包。find_creator 算不出构建目录时会提示，按提示手跑。3.x 工程 sync 也装 `GameUIKit.ts`。这样试玩和自测跑的就是带标准件的代码，不等出包才装（射击高手 v81、小熊拳击 R27 漏装触摸修正，指尖麻将 v55 重建丢了补丁，拇指弹球留着旧版 `RewardedService.js`）。遗留名单上的旧游戏 `sync` 只报告不改。新加或改动的弹窗、按钮一律用平台包的 `GameUIKit`（`var UI = require('GameUIKit')`：`UI.popup`、`UI.button`、`UI.toast`、`UI.digits`），别手写遮罩、淡出和点击；新加的正文 Label 一律用 `UI.text(parent, {w, h, text, overflow})`，教程手指一律用 `UI.guide(目标)`，原游戏的 Label 不动；AI 动过的原版按钮用 `UI.wrapExisting(节点, 函数)` 包一层；弹窗里的计时器和异步回调用 `popup.guard(回调)` 包住。用法见[平台包接入说明](../remake-core/assets/platform-kit/README_接入说明.md)第十一节。英化新加的弹窗用 `UI.popup`，提示文字从文案表取；`source` 会对手搭弹窗、写死遮罩和 PREVIEW/DEBUG/TODO 字样给警告。图标加数字（签到格、HUD 金币、价格）用 `UI.iconValue`，别手摆；页面上从存档来的数值写进 popup / 页面模板的 `refresh`；只在某些状态才出现的按钮用 `UI.newButton({active: false})`；首页两个入口的提示和排位交给平台包（2.4 的 `HomeGrowthEntries` 在 init 时传 `homePanel`，3.x 的 `placeLater` 自己等布局稳了再排），不要自己写提示 Label 或 scheduleOnce 一帧就排。弹窗的关闭图、提示底图、数字图开工时用 `UI.setup` 设一次，页面里别改 `UI.config()`；GameUIKit 1.1.7 起图被释放也会自动换回自带图。3.x 游戏的 PlatformConfig 由 `plugin3x_scan` 查 id 是不是从别的游戏拷来的；要查本机别的游戏，设 `TIKTOK_KIT_PEERS`。
2. **修改**：按上表 1–8 做。按[前期预防](references/early-prevention.md)先确认本批代表件和实际状态，再铺到所有受影响使用位置；涉及功能改动时随实现验证保存和重开结果。开始跑 `T stage 2`；做完跑 `T done`，用时发给 Saul，不等回复。
   - **第一轮美工：按美工 Skill 照原画风重新生成按钮和文字（Saul 2026-10-31）**：第一轮就做，不等点名。范围：所有按钮（带字的和不带字的图标按钮都算，Saul 2026-10-31：第一轮所有按钮都重新生成）、页面标题和所有图片字（中文改英文）；**游戏里不放游戏名**（Saul 2026-11-05：「以后的游戏都不要出现游戏名字，把对应的部分换成图案或者主角等美工来填充，不要是具体的游戏名字」）：原版首页等处的游戏名标题不做英文版，原位置换成照原画风生成的主角或图案图，大小和位置跟原标题一样；出包时 `tiktok_finalize` 的 `game_name_scan` 会查场景、预制体、文案表和已识出的图片文字里还有没有游戏名（11-05 起开工的英化游戏有命中就拦，更早的只警告）；报了不要停下来问 Saul：先跑 `python3 <skills>/remake-core/scripts/fix_game_name.py --project <工程>`，文字当场去掉；它写的 `docs/art/game_name_fix.json` 里每张图照提示词和参考图生成同名、同尺寸的无字图，放进一个文件夹，再跑 `fix_game_name.py --project <工程> --apply-images <文件夹>`，退出 0 就干净了；出图前跑 `python3 <skills>/remake-art/scripts/prompt_name_guard.py --project <工程> --file <提示词文件>`，提示词里不写游戏名（加 `--fix` 直接写出改好的提示词）；等级、关卡号、分数、货币（图片字的词＋0-9 位图数字＋货币图标）；新加的按钮（主页回访、加桌面、Watch Ad x2、复活、ad-boost 板块的按钮）和 Claim 小字。**正式试玩前全部完成（用户现行要求）**：第一个正式 Native 英文试玩链接前，完成全部计划美工：首页、设置、暂停、复活、结算、关卡选择、商店、皮肤、原游戏的签到/转盘/礼包、教程等实际存在页面的按钮、标题和图片字，局内的等级、关卡号、分数、货币数字，以及第 8 项 ad-boost 板块的图。制作可分批，首件通过后再铺开；不能把未完成页面、中文图片字或本轮已计划的板块留到第二轮再补。界面上的文字（Label、代码里的字）也全部改成英文，按第 3 阶段核对完整美工与中文专项覆盖后才发正式链接，已有有效证据直接沿用。做法按[美工 Skill](../remake-art/SKILL.md)：固定按钮优先复用同款合格整钮。已有核准整词字图及同款无字底时，先按[固定英文按钮生成](../remake-art/references/fixed-caption-button.md)用本包脚本等比合成，图标和旧字层只保留一份。缺少核准原料时，用生图工具（image_gen）按定稿制作并核字，原图放进参考图照着画，尺寸、描边、颜色、位置跟原图一致；代码和字体画的按钮、数字不算（Saul 2026-10-30）；每出一张图跑 `art_records.py generated` 记下来。句子（说明、教学、提示）照第 1 项用真正的英文字体，不生成图片。先做 2～3 个有代表性的（一个带字按钮、一个标题、一组数字）放进游戏看一眼合成效果，没问题再批量做，有共性问题先改共用的图再接着做。画风照原游戏，不换风格；Saul 要求换画风或重新设计时看下面「美工」一节。沿用原画风时，原包里本来就有的深色、纯色背景和面板不用重做：art_check 按图片 SHA 认原图，记「原图保留，不适用」；Saul 选了保留原画风就写一行 `docs/art/keep_original_style.json`（decided_by、date、why），回执和出包会读它，不要再在会话里另记人工授权，也不要再问 Saul。开工时的纯色面板清单在 `art-replace-round1.json` 的 `style_choices` 里，只有 Saul 点名美工 Skill 才重做（`--make-list --flat-panels regenerate`）。
   - 固定按钮随包可运行样例见[CLAIM 配方](../remake-art/examples/fixed-caption/recipe.json)。按目标游戏内框重定参数，空间不足停止出图。试玩前在两种手机尺寸检查最终画面，分层图标按钮登记 horizontal_gap。
   - 美工领到新图或旧画面反馈时，先按[把曾经漏掉的画面问题用于首件制作](references/english-ui-rebuild.md#把曾经漏掉的画面问题用于首件制作)选对应做法，写进该类素材的生成或接图参数。先完成最窄尺寸的一件，再复用到同组。
   - **美工制作预防（Saul 2026-11-03）**：开始生图前先按[美工制作预防](../remake-art/references/production-prevention.md)落实 T01–T14 的适用项，再执行[生成前先定尺寸与分区](references/english-ui-rebuild.md#生成前先定尺寸与分区制作时消除问题saul-2026-11-03)：英文定稿、实际可读空间、宽高比与文字/图标/状态/动作分区先确定，再写进提示词；接图等比缩放并处理被替代的旧视觉层。先把最长按钮词、标题、密集卡片等代表样接到真实页面确认，再批量做，每批就地看组合效果并修共性问题，不留到第 3 阶段才返工。保持原游戏画风；“尺寸、位置跟原图一致”指尽量沿用外部布局，不能强行把英文压进原中文窄框。
凡新增或改动图标＋文字按钮、海报说明条、长正文和奖励计数，按[图文内区检查](../remake-art/references/local-ui-contract.md)登记受影响状态。试玩前普通 art_check 读取 docs/art/visual-slots.json；逐项核对实际截图，原料切对、语义绑定和运行布局分别验。

   - **平台能力用平台包**：激励视频用平台包的 `RewardedService.js`，加桌面、主页回访用 `TikTokMissionService.js`（`remake-core/assets/platform-kit/`），不另写一份桥接。它们已经把 UI 回调包在 try/catch 里，提示抛错也不会把请求锁死（MusicSlice v29b 手写的 bridge 提示一抛错，看广告、加桌面、回访全部卡在 Checking）。触摸修正、存档层、启动件、适配层、App ID 由平台脚本安装和核对。图片格式和压缩在试玩前用相同脚本处理；手写的同类文件会被换掉（旧游戏除外）。新英化游戏一律装存档层 `storage-guard.js`（原版多键存储也走它）；旧英化游戏默认不装，只在 `adopt` 以后装（Q6）。原版的广告管理器改成调 `RewardedService`、原版里直接 `createRewardedVideoAd` 或直接调加桌面/回访接口的代码删掉：新游戏漏改出不了包（`A1_rewarded_outside_kit`、`G1k_growth_outside_kit`）。原版（2.4）自带和平台包模块同名的脚本（例如自己的 `TikTokMissionService.js`），`source` 段会把它移到 `.tiktok-kit/removed/`。`PlatformConfig.js` 要填本游戏的 `gameId` 和 `normalLevelCoins`，没填新游戏出不了包（`K_platform_config`）；原游戏没金币时 `normalLevelCoins` 留 0（写包只警告），首页的 `HomeGrowthEntries.init(save, {reward, rewardText})` 传 `economy_capabilities.json` 里 `no_wallet_substitutes` 给的替代奖励（有体力的各 +3 体力；没体力的先加一种金币和皮肤，再发 5B），不传写包会报 `K_home_entries_no_reward`。 原版广告管理器先跑 rewire-ads，改不了的才手改。新做或重建的界面：背景用 `parts/ScreenFit.js` 的 cover 铺满，顶栏和底排用 safeTop / safeBottom；拖拽、滑动、摇杆用 `parts/TouchOwner.js`，不另写（见平台包接入说明第十七、十八节）。原版界面不动。
   - **做的时候就做对（生成时预防，简化.11.13）**：① Label、prefab 里的中文改成英文以后马上跑 `python3 <skills>/cocos-game-to-english/scripts/fit_english_labels.py --project <工程>`：放不下的单行字它直接改成 SHRINK（缩后不低于原字号 70%）；退出码是 1 时按 `docs/english/fit-labels.json` 的 todo 一条条改（加宽框、改短英文、多给一行），改完再跑，直到退出码为 0。数值、百分比、倒计时这类 Label 先在 `docs/english/label-values.json` 登记最长值（`max_value` / `longest` / `room`）再跑。倒计时按它自己的格式量（mm:ss 不按 00:00:00）；NONE 的字只记录不改，记录里 `wider_than_parent_plate` 的那几条接图时看一眼。跑完看记录里的 `bitmap_needed`：分数类数字已自动换成位图字，列出的固定词要用美工 Skill 生成整词图再接上，别用字体补。换字体或加 TTF/OTF 后马上跑 `python3 <skills>/remake-core/scripts/subset_fonts.py --project <工程>`（本机没有 fontTools 先 `python3 -m pip install fonttools`），别把整套字体放进主包。英文写进 Label 和 prefab 以后，紧接着跑 `python3 <skills>/cocos-game-to-english/scripts/english_copy_guard.py --project <工程>`：字面的 `\n` 它自动改成真换行；RichText 标签不配对、登记过的看广告按钮上没写 WATCH AD 时退出码是 1，改完再跑。美工生成位图数字和整词图之前先读 `docs/english/charset.json`：位图数字按 `value_charset` 一次画全，`word_images` 在首件之前一次生成齐；先拼进变量、过几行再赋给 Label 的格式串，english_copy_guard 算字符集时也认得出。位图数字的字符集以 `docs/english/charset.json` 的 `value_charset` 为准，数值格式化里的单位字母（K/M/B…）和符号也在里面；`fonts[].missing` 不为空就按这份字符集重画位图字，或者把单位和符号改用整字图 Sprite 槽，不要只画 0-9。第一轮接图按 `art-replace-round1.json` 的 `runtime_words.missing` 把代码运行时取的整词图一起画好（`txt_<slug>.png`），`untranslated_names` 先翻译再画。只改了几个节点时，`fit_english_labels.py` 加 `--nodes <这几个节点>`；停用的旧占位符在 `label-values.json` 写 `status: retired` 和 `reason`。preflight 的「文案写入校验」一行也会列出 RichText 不配对、看广告按钮没写 WATCH AD 的地方（现在只提示），看到了就跑 `english_copy_guard.py --project <工程>` 改掉。② 首页加主页回访、加桌面两个入口：2.4 挂 `HomeGrowthEntries`，不写入口坐标，它在 init 后按首页按钮和带触摸的节点自动摆，放不下报错；3.x 用平台包装好的 `TikTokKit.HomeEntrySlots.placeLater` 运行时摆两个入口，别手写入口坐标，手写了 `source` 会报 `K_W_home_entry_coords`（想先看空位时可以跑 `node <skills>/remake-core/assets/platform-kit/tools/home_free_slot.js --dump <首页 ui_dump> --screen <宽x高> --entry <宽x高>`）。首页新加的按钮一律用 cc.Button，加完调一次 `HomeGrowthEntries.placeEntries()`，不自己估坐标。原按钮不动；放不下就问 Saul。③ 换图接图用 `python3 <skills>/remake-art/scripts/bind_art.py --project <工程>`（2.4 和 3.x 都支持；按新图比例装进原框，自动设 trim 和 sizeMode），不手改节点宽高；接完跑 `bind_art.py --project <工程> --check`，只改这一轮换过图的节点，原游戏的图（拉满屏的遮罩、角色部件、进度条）照原样。生成的透明图裁边用 `remake-art/scripts/trim_visible.py`，别手写 getbbox；整词图、按钮字这类字图裁边时加 `--word`，它先自动去掉描边外的半透明彩色光晕（原图留作备份）再裁；退出码 1 表示光晕去不掉，按它打印的提示词（同尺寸、同字、no glow）重生成再跑，旧图别接。原游戏有皮肤的，皮肤预览只接每款自己的 previewFrame，别用槽框图、别整张染色，接完跑 `python3 <skills>/remake-core/scripts/check_skin_preview.py --table <皮肤表> --board localize`；皮肤表的 previewFrame 也由 `tiktok_finalize` 的 source、sync 自动查（英化只警告）。带字的新图过 ad-boost 的 `postprocess.py` 时会量字和字底的对比度，被拒就整张重生。④ AI 新加的图（主页回访、加桌面、广告板块的按钮图）走资源表：`python3 <skills>/remake-core/scripts/make_res_keys.py --project <工程>`（英化不加 `--strict`），代码用 `Res.sprite(ResKeys.x)`、`Res.request(ResKeys.x)`；原版加载代码不改。⑤ 原版玩法代码不改；AI 新加的暂停、复活、广告入口用平台包 `RunSession`（`pause('revive')`、`adHooks()`），不要再写一个暂停布尔。数值文字（音量 %、金币、分数、倒计时）用 `UI.valueLabel(node, {longest})`，别按当前值定宽。⑥ 要从音效库加声音时用 `python3 <skills>/remake-core/scripts/import_audio.py --project <工程> --file <音效库里的文件>` 导入（自动写 `docs/audio/credits.csv`），不手工复制；AI 新加的声音逻辑用平台包 `AudioService.js`；原版的声音文件不动，原版的播放调用、平台音频对象和开关读写按盘点的 `audio_todo` 改走 `AudioService`（见第 1 阶段盘点）。⑦ 原游戏关数少于 60 时，先跑 `python3 <skills>/remake-core/scripts/game_capabilities.py write --project <工程> --merge --level-count <原关数>`，再跑 `make_skin_table.py`、`make_economy_config.py`，两个都加 `--project <工程>`。跑完 `make_economy_config.py` 后接着跑 `python3 <skills>/remake-core/scripts/game_capabilities.py write --project <工程> --pause-button <关内暂停键路径>|--no-pause-button "原因" --ad-entry double=<路径> --ad-entry revive=<路径> …|--no-ad-entries "原因"`（ad-boost 加完板块后再跑一次补上新入口）；装 ad-boost 板块时照它的 SKILL 把各板块的 `save_keys.json` 合进工程 `docs/save/save_keys.json`，再跑 `make_save_schema.py`，零件自己建的状态（签到、礼盒、体力、板块的 round/board）登记子键时写 `"in_defaults": false`，可能是 null 的写 `"nullable": true`，别为了能登记把子键写进默认值；沿用原游戏的签到表时，`CheckinFlow` 传 `design: 'original'`；没有局外金币的游戏用 `make_economy_config.py --no-wallet --kind english --systems <有的系统>`，不再问「B 是多少」；货币审计一律带 `--project <工程>`；写 runtime 适配文件后跑一次 `game_capabilities.py adapter --project <工程> --adapter <适配文件> --out <新文件>`，用它出的那份。零件用法见[平台包接入说明](../remake-core/assets/platform-kit/README_接入说明.md)第十一至十八节。
   - **原版的 `.webp` 图**：新英化游戏由 `source` 段换成 PNG/JPG；数据或脚本里写死的 `.webp`（例如 `"imageExt": ".webp"`）按文件和行号被拒（`IMG0_source_images`），要改成 `.png`/`.jpg`。原版是 Cocos 3.x 的没有 WebP 例外（`K_webp_exception_3x`），只能靠 PNG/JPG 和 `max_side` 缩到 30 MB 以内。
   - **新做的英文图**：按显示尺寸 2 倍导出再压缩。新图（哈希不在英化前的图片清单里）单张超过 800 KB，出包会被拒；宽/高超过显示尺寸 2.5 倍的会被列出来，要改小（`remake-core/scripts/audit_new_english_images.py`；开工时用 `--make-list <中文原工程> --out docs/english/pre-english-images.json` 存英化前清单，出包时缺这份清单也会被拒。它同时把每张图、每个图集切片和动画帧读一遍，写 `docs/english/art-replace-round1.json`：replace 里的图第一轮美术就照原画风换成英文，manual_review 里的自己打开看；没有识字工具的电脑上全部列进 manual_review，一张都不能跳过；`regenerate` 里是整块单色的面板和背景，第一轮照原画风重画成有边框、明暗和图案的版本）。
   - **准备 `qa/ad-regression.json`（第 1 / 2 阶段定位真实入口与字段，各项随制作执行一次，第 5 阶段只补缺及复验真实改动项；不挡英文试玩链接）**：出包前的 10 个广告回归用例要它。`request` 走游戏自己真实的看广告方法，`grant` 挂在游戏真实的发奖函数上，`ready` 写首页已就绪的条件。示例：[examples/MusicSlice_ad-regression.json](examples/MusicSlice_ad-regression.json)（多渠道 AdsManager：`config.videoType=0` 后调 `config.AdsManager.ShowVideo()`，发奖统一走 `config.getReward`，示例把它换成计数）。同一个文件也给出包时核对有效覆盖的运行时回归用（`cocos-game-check/package-check/references/runtime-regression.md`）：必须有 `home`（首页可用时返回 true），建议写 `enter_level`；缺 `home` 出包会被拒。**手机才出的问题要的几块（v7.9 手机问题源头约束，新游戏缺了出包被拒）**：`play`（首页 PLAY）；`resume_play`（`start` 进到一关、`probe` 真点一下、`state_js`，有倒计时写 `clock_js`；暂停键、继续键、关内广告名字认得出就不用写）；`ad_entries` 至少写结算页 Watch Ad x2（`"role": "double"`）和复活（`"role": "revive"`），各带真实操作到它出现（过关；让主角自己失败，`wait_node` 等按钮），第 8 项加的板块也写进去；`save_restart` 每一步写 `kind`，首页有什么就要有什么：过一关（`level`）、商店 / 皮肤买一件（`buy`）、领一次奖（`claim`）。写法和例子见 runtime-regression.md 的「手机检查补全」一节。
   - **广告规则去哪看**：按上面「看广告的几项按广告板块做」：广告计时和广告回归看 [超时规则与广告回归](../remake-ads/references/ad-timeout-and-regression.md)，复活页和结算 x2 两屏看 [一局结束：每屏一个视频按钮](../remake-ads/references/end-flow-one-video.md)，领奖窗看广告双倍勾选框看 [广告板块共用表](../remake-ads/SKILL.md#共用的广告设计)，数额看 [经济规则](../remake-economy/references/economy-rules.md)；和 [TikTok 固定适配·已定口径](../cocos-game-check/references/tiktok-fixed-adaptation.md) 有出入时以已定口径为准。
   - 图片字和切片在实际制作范围内复核。可保存逐项结论与真实素材对应关系，供中文排查或定点回归使用。
3. **英文试玩链接＋人工检测清单（Saul 2026-10-31）**。先把首件共性问题合批修好，再确定本轮正式候选。在同一版上完成中文专项及本次制作涉及的美工项，核实页面启动和输入后发链接。内部首件与诊断可先用 Web，只有正式英文试玩候选才准备同版 Web 与 Native。
   **准备同版候选**。对定稿源码执行 `python3 <skills>/remake-core/scripts/tiktok_finalize.py source --project <工程> --board localize`，审阅 Sprite 比例结果并处理本轮相关项。以同一份源码备齐 Web 和 TikTok Native。现成导出经同源核对可沿用，只构建缺失或已变的目标。Web 缺 3.x 入口时先执行 `fix_web_entry_3x.py --export <这轮的 Web 导出> --project <工程>`，并用 `check_export_images.py --project <工程> --export <这轮的 Web 导出>` 核对导出的图与当前工程一致；报旧图才清理并重建对应的导出目录。用 `tiktok_finalize.py native --project <工程> --native <Native> --board localize --app-id <目标AppID>` 完成 Native 平台件与 PNG 处理。查看实际受处理图片，修复缺图、变形、色带后再验收。这一步会记录已处理 Native 的文件指纹及源码身份，供正式试玩核对。旧项目缺该记录时，先确认原构建来源，再补做 Native 准备。保留这对导出供试玩和出包。

   **核实际图片和切片**。检查本次制作和改动范围内的图片字、图集切片与共享引用。有疑问时使用 `audit_image_review_record.py` 定位 Web 与 Native 导出的差别，保留已核的具体结果。
   **中文专项检查（Saul 2026-11-01，每次给英文试玩链接前都做）**：这也太牛了的波次警告里还有「高波来袭！」：字在 Spine 图集 highwave.png 的 `wave` 切片里，脚本和场景里搜不到，旧的图片复核记录却写着没中文。所以给链接前用 `python3 <skills>/cocos-game-to-english/scripts/chinese_audit.py` 查，结果都在工程的 `docs/english/chinese-audit/`：
   ① `scan --project <工程> --export <这轮的 Web 导出>`：列出全部资源；脚本、场景、预制体、配置里的字按字符串、注释、字段分开（注释、开发日志、节点名、编辑器路径自动放过，会显示的要结论）；每张图和每个图集切片（Spine `.atlas`、`.plist`、BMFont、龙骨）逐个识字；导出里对不上源图的图单独识。第一轮几分钟，以后每轮只识新加和改过的。
   ② 有要复核的：`sheet --project <工程> --pending` 拼出复核图（每格都看得清），你打开逐项看，每项写结论：`review --project <工程> --id <编号> --verdict <结论> --by "<你>" --evidence <复核图或切片图>`。确有中文写 `chinese`，然后把图改成英文、重新导出、回到 ①；识字认错了（特效、花纹、数字被认成字）写 `false_positive`，图一个像素都不改；会显示的文字确实不显示写 `not_displayed --reason "<理由>"`。识字出错、这台电脑没有识字工具的，也要这样逐个看过，不能当成没有字。隔离渲染的截图证据写 `--evidence-kind isolated_render`，它只证明资源显示对了，不算自然玩到、也不算真机。
   ③ `check --project <工程> --export <这轮的 Web 导出>`：通过才往下。过没过由它重算（清单、切片、识字回执、复核证据都要对得上现在的文件），手写的记录不算。它报「导出不是这版源码」时，用现在的源码重新导出，再 `scan --export`、`check`，不能拿旧导出凑通过。
   **改图后的重拍清单**。登记受影响状态、共享资源、视口和复现数据，按[按状态补拍](../remake-art/references/capture-rounds.md)复用旧证据，只采改动涉及的状态。

   **制作阶段核对画面**。按本轮实际范围完成资源、图集、可测布局等技术项。观感、遮挡、动画和闪烁按[人工试玩画面清单](../remake-core/references/manual-visual-review.md)交接。
   **通过后启动正式英文试玩**。运行 `python3 <skills>/cocos-game-to-english/scripts/serve_preview.py --directory <本轮 Web> --project <工程> --snapshot --open --idle-minutes 0 --native <已处理的 Native> --ad-simulator --name "<游戏> 英文 第1轮"`。英化入口核对中文专项、独立试玩快照和 Native 准备记录。实际试玩服务通过入口、首页及适用的冒烟检查后才写入 `docs/english/chinese-audit/trial-links.json`。用户要求重开且仍是同版时，加 `--reopen` 核对已有通过记录。仅在用户明确要求查看草稿时使用 `--draft`。
   顶栏不手算胶囊位置：新游戏 source 自动装 CapsuleAuto。页面背景一律用 `ScreenFit.cover(cc, bg, {watch:true})`，别按设计尺寸铺，source 会查首页、局内、结算的背景（新游戏拦，英化警告）。update 里移动一律乘 dt（或 RunSession.move），节点在 onLoad 建好或从 FxPool 取，别在 update 里 new；sync 每次构建前会扫（新游戏拦，英化只提示）。
   用 Ego Lite 确认本轮导出能进首页、能开始一局，控制台没有导致卡死的报错。已在本轮美工采集中取得这些证据时直接引用。用户试玩使用已验收快照。第 3 阶段开始跑 `T stage 3`。试玩入口未自动记用时时补跑 `T link 1`，完成跑 `T done`，把输出贴在这条回复最后。
   回复里先用一句话说：这款原来有几个看广告的地方，第 8 项默认加哪几个板块（Saul 2026-10-31 定的默认做法，不用他选），本轮已完成接入与美工，不要哪个直接说。按实际候选列明已完成的页面和板块，不能把未完成的计划美工留到第二轮。
   回复里随同版 Native 试玩给出**人工快查清单**，按[返工交付与人工快查](../remake-core/references/returned-art-delivery.md#4-人工快查放在原有-native-试玩与反馈节点)只列本轮实际页面上适合用户判断的 3–5 条以内项目：风格是否符合参考、固定文案与图意是否准确、指定位置是否还有重影、压字，首次转场或开关弹窗有没有闪黑、闪白、停顿或缺图。只改一处就一条。不要照抄全游戏清单、让用户重玩所有关卡或重复机器已完成的技术验证；奖励去重、存档读回、冷启动和异步回调等仍由 AI 按真实依赖计划处理。
   用户指出一项就进入对应节点；已交付返工并要求改完出包时，这份清单仅供交包后可选快看，不再等一轮人工批准，不把未回复记成人工实测通过。

4. **试玩改进（Saul 找问题、提改进，AI 改）**：已交付后指定美工返工并要求出包时，直接按[返工交付](../remake-core/references/returned-art-delivery.md)采用独立视觉授权，跳过下文美工复验与再次等回复；本段其余规则用于首轮试玩反馈或未获本次视觉交付授权的修改。用时：发完第一个链接就跑 `T stage 4`；Saul 每次回复先跑 `T back`；每起一轮新链接，`serve_preview.py` 自动记 `T link <第几轮>`（同一份导出重开不算新一轮），它打印的上一轮用时贴在新链接那条回复最后；它打印「没记上」时手动跑；Saul 说没问题时跑 `T back` 和 `T done`，用时发给他。首次正式试玩前已完成全部计划美工；Saul 试玩时准备尚缺的功能或平台适配记录；每轮起新链接前做中文专项检查和受影响范围的定点美工复查（见第 3 阶段），本轮功能的局部验证随实现完成，未覆盖的检查在相应制作节点执行一次，第 5 阶段只核对旧证据和补缺。后续只处理 Saul 的反馈和明确新增要求，不将首轮欠下的页面、按钮、图片字或已计划广告面板作为后续轮次补做。新增页面、板块及其素材在该轮正式链接前完成制作并通过受影响项检查。他说的每一条（画面和游玩的 bug，以及他点名的玩法、手感、难度、数值改动）一次全部改完，同批导出 Web 和 Native 各一次；按第 3 阶段复查受影响整页、共享组件和新增页面的美工，通过后再起这一轮的新链接：照第 3 阶段对这一轮的导出过一次中文专项检查（scan 只识新加和改过的图，没变的沿用上一轮的回执和复核；新出来要复核的照样逐项看）；过了，先停掉上一轮的试玩服务，再用同样的命令起，`--name` 写第几轮（`--snapshot` 起的链接不会跟着重新导出变，不能只叫他刷新）。只是重开同一份导出（服务停了、Saul 要再看一遍）时，加上 `--reopen`。`serve_preview.py` 核对过它就是查过的那份，不用重新 scan。回复里写改了哪几条，再列一遍清单里和这几处有关的几条请他复查。玩法改动只改 Saul 点名的；要加新系统的，照上面「创新玩法」用现成板块。这样来回，直到 Saul 说试玩没问题（「没问题了」「可以了」「出包」这类话）。等他回复时可以先写第 5 阶段要用的 `qa/ad-regression.json`，这是提前准备适配；本轮改动的局部验证照常执行，不在第 5 阶段重跑已有通过项。
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
   - 用 `make_tiktok_zip.py` 或 `build_checked_zip.py` 对已验收候选出包，带上 `--project`。正式写包按同一 ledger 只补缺项和真实受影响项，已通过项直接沿用。正式交付读取同一 ZIP 的写包回执，绑定一致的回归可沿用，并按交付规则重新复查最终 ZIP 的分包体积。测试包与同版可用的手机试玩链接同发。现有同版服务经核实可以沿用；要重开时用英化入口的 `serve_preview.py --directory <同版 Web> --snapshot --keep --project <工程> --native <已处理的 Native> --reopen`，按需核验试玩服务。
   - 手机上看到的问题（v7.9）：Saul 在手机上报过问题的，登记时写 `--source device` 和手机上跑的那个 ZIP；问题门禁 `check` 的结果有 `device_issues` 时，每条的 `line`（「复现了手机上的画面和同一行报错」「不能完全确定是同一个原因」「电脑上没复现，不能说修好了」）原样贴进交付回复，不改成「已修复」。做法见统一检查的[手机上看到的问题](../cocos-game-check/package-check/references/resource-and-reported-issues.md)。
   - 用时：这一阶段开始跑 `T stage 5`；交付时依次跑 `T mark 交付`、`T done`、`T report --all`，第 5 阶段用时和全程总表都放进交付回复。
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
- 阶段结束 `T done`，试玩交付与最终交付用 `T report --all`。报告区分整轮墙钟、已完成执行区间并集、工具区间、外部等待、用户等待、暂停、未记录空档。并行项和父子任务不能直接相加；开放节点不是已完成准确实耗。底层 suite 缺单项计时就写未知，不能把整个批次秒数复制给每项。
- 预算在盘点后按实际页面状态、中文素材量、引擎/环境、外部生成队列填写，作为发现卡点的参考。超过预算先定位当前进程、输入和依赖，不因超时自动全测、重启浏览器或重复构建；也不能单凭耗时判断模型出错。优化比较须同输入同范围，不能把几秒脚本差异说成整轮节省几小时。

| 阶段 | 必须分别记录的节点 |
|---|---|
| 1 盘点 | 输入身份与安全解包；环境与引擎；中文原版构建与 ready；中文/资产/平台/存档清单 |
| 2 修改 | 最长文案与内框预算；首件；批次生成与等待；切图；图文接入；原功能平台适配；音频；实际构建与局部验证 |
| 3 英文试玩 | 候选准备或复用；页面采集路线；首次缺项检查或证据沿用；链接 ready；人工试玩交接 |
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

**第一轮就用美工 Skill（Saul 2026-10-31）**：英化第一轮按[美工 Skill](../remake-art/SKILL.md)照原游戏画风重新生成所有按钮和文字（范围和做法见第 2 阶段「第一轮美工」），不用等点名；页面排版、背景和角色这些原游戏画得好的图和原画风不动。别的美术改动（重新设计、换画风、改排版、“这页太丑改一下”）仍只在 Saul 点名时做。等级、关卡号、分数、货币美化，以及不显示版本号和 Credits，英化必做（Saul 2026-10-30，见 [Saul 的美术禁区与必做项](../remake-art/references/saul-art-rules.md)）。

**Saul 要求“重新设计”英化游戏时，画风也照原游戏**（Saul 2026-10-31，香肠太难了 Redesign v2：他说“结合广告skill和美工skill重新设计游戏”，结果原版亮橙色、薄荷绿的圆角按钮和木色金边的六边形图标钮全被换成同一种深红方块；Saul：“要按照原游戏的风格去设计美工”）：原图能用就用，要新生成就把原图放进参考图照着画；按钮底色不用深色（深红、砖红、深棕、藏青、深灰、黑这类），金币、爱心、礼盒这些物品图标后面不另加底板；原游戏本来带底座、奶油色边或高光的照原游戏。只有他明说换画风（例如“按重塑画风重做”）才换。用 ad-boost 加的新板块也一样，面板和图标跟原游戏走。

**重做美术先出小样（Saul 2026-10-31）**：Saul 要求英化游戏重做美术或重新设计时，先出小样，不直接做整套：出 2～3 套，每套 1 张首页加 2 个按钮（主按钮、看广告按钮），其中一套是「保持原画风，只改英文和新入口」；30 分钟内发小样图给 Saul 挑，已按第 3 阶段验收的同版候选也可给正式试玩链接，他选了再做整套，都不满意就再出几套。等他选的时候接着做不碰美术的部分（广告入口、代码）；小样发出前按下文查，做成可玩英文链接时仍按第 3 阶段完成美工检查。小样和 Saul 选的那套记在 `docs/samples/samples.json`。小样这样做（Saul 2026-11-01「把这三点补进v7.9一起改」）：
- **给 Saul 挑的是做出来的样子**：每套的 2 个按钮和标题单独生成，按计划显示尺寸摆进游戏真实首页，截图给他挑。不拿一次画出的整页效果图给他挑：整页图上的字常是乱的，排版也和真页面不一样，挑中以后按钮一张张生成再拼进游戏，会和效果图对不上。整页图可以拿来定方向、当生成按钮的参考图。
- **每套先过美术检查再给他看**（以下两行是小样的重点项；正式制作时按第 3 阶段处理真实画面问题）：摆好以后 dump 这一页跑 `art_check.py`，「按钮底色不深、物品图标不另垫底板」和「深色粗字（永久禁止）」两行不过的那套，先改好或换一套。这样用户在挑选时看到的就是实际接入效果。
- **挑一次就定死**：只在开工时，和 Saul 说「换风格」「这页重做」时挑；之后每轮美工不再重新挑。选定以后把这套的颜色（HEX）、材质、圆角、描边写进 `docs/samples/samples.json` 选中的那套；之后每个按钮都带这套的截图和 2 个按钮当参考图生成，先做 3 个放进游戏看对不对，再批量做。
