---
name: cocos-game-to-english
description: "英化（触发词：英化、英化skill、中文源码、翻译成英文、英化这个游戏）。拿到能运行的中文Cocos完整游戏时用：开工先给中文原版的手机试玩链接（不等回复）；把中文美工和文字改成英文（第一轮按美工板块 remake-art 照原画风重新生成所有按钮和文字）；补齐固定入口（个人主页回访、添加桌面、音效/BGM音量、关内暂停键、结算页看广告双倍与Retry、看广告复活），删除分享/更多游戏/联网排行榜；看广告的几项按包里的 remake-ads、remake-economy 做，看广告的板块默认按包里的 ad-boost 诊断后按推荐加，不问 Saul；先过美工检查和中文专项检查，再给英文试玩链接和人工检测清单；Saul 试玩没问题后做其余全量检查和出包；macOS、Windows 都能用，没有 Ego 时用 Chrome/Edge 跑检查。默认不改玩法、不加关卡、不加新系统。"
---

> 2026-11-01 用户更新：Grok 图片识别已停用。本文任何 Grok 读图、OCR、截图转录或 `grok-image-review` 路由均失效；所有读图由 Codex 自己直接查看并完成。文本搬取等非图片任务按各自规则执行。

# 英化（独立流程）

修订：`2026-11-06.english-simple.11.17.3`（英文美工按状态和视口决定重拍，同页多状态分别检查，旧截图保留原始来源。历次改动见[版本历史](版本历史.md)。）

共用功能验收与故障复验按[实际触发与玩家结果](../cocos-game-check/test/README.md)选测。

**每次给测试包都复查分包体积（用户 2026-11-05）**：新旧、外来、同版重发、仅改名或用户仅索取已有文件均不豁免；交最终 ZIP 前按[统一检查的本次体积复查](../cocos-game-check/package-check/references/fresh-upload-size.md)重新读最终文件并生成新回执。不复用旧体积结果，不以 CRC/哈希或 Web 可玩替代；局部返工只查改动也不能跳过本项。失败/未跑不交包，已被平台拒绝的同字节 ZIP 不得原样重发。

**减少美工返工（11.17.3）**：新按钮/切图先列全部使用页的 CSS 尺寸预算；共享数字字体先定字距和最长串，再批量接入。第一件检查旧 Widget/Layout 回写、资源角色错绑、状态图重复染色和点击区。按视口连续采新截图减少启动；旧图沿用需独立整页一致、本轮受控存档和完整通过记录。规则与命令仍在下方制作/采集引用中，只做美工，不扩大玩法。

**美工制作即检查（11.17.2）**：第 2 / 4 阶段按[制作与检测共用证据](../remake-art/references/production-check-link.md)执行。固定按钮和切片由生成工具登记约束，第一件接入即调用原图文/像素检查；第 3 阶段复用输入与规则均未变化的计算。首件不发试玩回执，完整美工与中文检查时点不变。

**美工检查时点（Saul 2026-11-03）**：完整美工检查移到每轮英文试玩链接之前，先查、修好、复查通过再给链接；后续轮次复查受影响整页、共享组件和新增页面。广告回归、平台兼容及其余出包检查仍在试玩确认后的第 5 阶段。

上一修订：`2026-11-01.english-simple.11`（简化.11：①每次给英文试玩链接前先过中文专项检查 `chinese_audit.py`：全部资源列清单，每张图和每个图集切片逐个识字，复核结论要带证据文件并按 sha 绑定，过没过由 check 自己算；英化入口的 `serve_preview.py` 没过就不起英文试玩链接，Saul 2026-11-01（这也太牛了的 highwave 图集切片里还有「高波来袭！」）；②重做美术的小样补三点：真页面上挑、先过美术检查、挑一次定死（Saul 2026-11-01「把这三点补进v7.9一起改」）；③交付回复原样转手机问题的结论（问题门禁 `device_issues`）；④创新玩法新加的部分在第 5 阶段查；两包共用的检查、货币板块和本包带的 ad-boost 改了什么见包根目录 README；以前各版见 [版本历史.md](版本历史.md)）。

英化和重塑是两条独立的路：英化默认只用本包（本包带广告 remake-ads、货币 remake-economy、皮肤 remake-skins 三个板块和广告加量 ad-boost）；Saul 要求创新玩法时，新加的部分用这三个板块和重塑包里的关卡、引导板块（见下面「创新玩法」）。

## 分数与奖励的制作及交付硬约束（score-reward-1，2026-11-04）

第一轮先做实际失败结算与奖励行代表样：`SCORE` / `REWARD` 固定词用整词图片，实时数量用生成的位图数字。不能通过 `EnglishUI.label(..., 'Score '+value, ...)`、TTF 描边或把数值登记为 runtime-text 来替代。按原画风制作，保留真实数据绑定。

写英文后运行 `fit_english_labels.py`，其源码预查现在同时拦普通字体数值。脚本动态创建的界面必须实际打开；首件接入立即采集同帧 dump 和截图，执行 `python <skills>/remake-core/scripts/audit_value_presentation.py --project <工程> --dumps <本轮首件采集目录>`，非零不得批量复制该模板。运行时结果仍须由 Codex 直接看图。固定词、图标、数量各占一槽，移除重复旧字层；用真实字宽布局，在 `docs/art/longest-text.json` 的 `labels` 中按节点路径记录最长合法显示值（`path`、`text`），实际显示该值复查。成功、失败、奖励初开及重开、两种手机比例在既有页面清单中覆盖。

每轮英文试玩之前，完整 `art_check.py --board localize` 必须通过；已接入上述检查。英化回执缺失、失败、旧版本缺专项运行证据、3.x 未覆盖都阻断用户试玩与出包，不再降为警告。回执同时绑定文字代码、场景/prefab、字体与 meta；只改坐标或文字也使旧回执失效，改完重跑 `art_check.py` 就会更新回执，别手改 `art-receipt.json`。`--draft` 不绕过美工门禁；中文原版与内部 QA 按原入口。首件通过不能替代全页面检查，源码预查通过不能替代运行检查。

## 一屏看懂（先读这个）

拿到中文 Cocos 完整游戏，按五步走：

- ① 盘点：拿到的源码或包先跑 `python3 <skills>/remake-core/scripts/which_package.py --project <工程或包> --roots <游戏文件夹> --roots <工作区里放这款游戏的文件夹>`（按字节和 Cocos 资源 uuid 找同一款游戏的全部包）；它说「放在 N 个地方 / 可能有两条以上的版本线」时，先用一句话问 Saul 在哪条线上接着做，不要另起一条（音乐消消乐 11-05：Kiro、Codex 各从 v29b 做到 v30、v31、v32，修过的问题互相没带上）。中文源码用 `unpack_source.py` 放进工作目录（不带 .git，Saul 2026-11-04）；先查电脑（`check_machine.py`，见「换电脑也能用」），再给 Saul 中文原版的试玩链接，不等回复；接着写新游戏标记、列清单。
- ② 修改：做下面「只做这几件事」的 9 项。第一轮美工照原画风重新生成所有按钮和文字，第一个链接只等首页、设置、暂停、复活、结算和局内数字；第 8 项 ad-boost 这一步只诊断、定下加哪几个。
- ③ 英文试玩链接：先过完整美工检查（见第 3 阶段）和中文专项检查（`chinese_audit.py` 扫描、看清要复核的几项、check 通过；不过不给链接，Saul 2026-11-01），再确认能进首页、能玩一局、没有报错卡死，就给链接，回复里直接打出人工检测清单。
- ④ 试玩改进：每轮起新链接前照样过中文专项检查（只识新加和改过的图），同时复查受影响整页、共享组件和新增页面的美工，过了再给链接；改动功能的局部验证随实现完成，其余完整套件留到第 5 阶段。Saul 说的一次改完，每轮起新链接；同时做完其余页面的新图和第 8 项的板块。
- ⑤ 全量检查和出包：Saul 说没问题以后做，检查一条不减，用写包入口出包。测试包交了以后再改（返工），只查改到的部分，不从头再查（见第 5 阶段「出包后返工」）。

每一步的细节在下面「阶段」一节；要读哪些文件见「读哪些文件」。每个阶段做完都把用时发给 Saul，见「用时汇报」。

**必须遵循（Saul 2026-10-29）**：TikTok 固定适配（触摸、启动加载、激励广告、存档读值、适配层、图片、加桌面/回访、登录/App ID、胶囊/首页底排/不要 Credits）和跨游戏通用流程一律按 [TikTok 固定适配](../cocos-game-check/references/tiktok-fixed-adaptation.md) 做：英化一律加看广告复活，核心玩法里的分享奖励改激励视频、其他分享入口删掉，加桌面/回访奖励各 5B；新游戏只用平台包标准件，不手写；旧游戏只给警告，由各自会话处理。

拿到的是一个能运行的完整游戏。默认保留原工程、原玩法、原关卡、原画风、原声音和存档；不补关，不加经济、皮肤、礼盒、签到、教程等系统（看广告的板块由 ad-boost 默认加，见第 8 项）。关卡、皮肤、引导板块不主动调用；广告板块只用在下面「看广告的几项按广告板块做」写的几处（不用 Saul 点名），货币板块只用来算这几处和 ad-boost 板块的数额，原游戏的价格和其他数值不改。第 4 阶段 Saul 试玩时点名要改的玩法、手感、难度和数值，照他说的改，只改他点名的。

**创新玩法（Saul 2026-10-30）**：Saul 要求给英化游戏加新玩法时，算单独任务。新加的部分用现成的板块做：广告 remake-ads、货币 remake-economy、皮肤 [remake-skins](../remake-skins/SKILL.md)（本包自带；皮肤一定连着货币和广告，新加皮肤就要同时有货币、看广告解锁款和看广告试用弹窗，Saul 2026-11-04）；关卡 remake-levels、引导 remake-onboarding（在重塑包里；只装了英化包的电脑要先装重塑包）。不另写一套，这样不容易出新 bug，做过的也能复用。只做 Saul 点名的部分，原有玩法照旧不动；加关在关卡表写 `explicit_total`，新加的部分照对应板块的检查查，在第 5 阶段全量检查时一起查；新加部分的美工仍须在英文试玩链接前按第 3 阶段检查；新增功能先按[前期预防](references/early-prevention.md)做局部验证，玩法、经济等完整回归留到第 5 阶段。

## 换电脑也能用（10.2.10，Saul 2026-10-31）

英化包是给别人用的，会装在别人的电脑上（macOS 或 Windows）。照下面做，每一步在哪台电脑上都能跑（Saul 2026-10-31：「我的英化skill基本是给别人用的……各个步骤都要具有不同电脑的通用性，不要出现ego这些不兼容，无法测试……cocos无法正常使用等问题」）：

- **「Saul」是谁**：本包写的「Saul」指正在用这个 Skill 的人（给你游戏、试玩、做决定的那个人）。「Saul 定的」规则照样遵守；回复照样用大白话，要他定的只出选择题，跑命令、找路径、装东西都由你来做。
- **开工先查电脑**：第 1 阶段第一件事跑 `python3 <skills>/cocos-game-to-english/scripts/check_machine.py --project <中文原工程>`，一分钟内查完 Python、Pillow、numpy、ffmpeg、Node.js、出包检查用的浏览器和这款游戏的 Cocos Creator。缺必须的，用大白话告诉用户缺什么、影响哪一步，问一句能不能装；同意后由你来装，装好再跑一次。缺的东西不影响的步骤先接着做。它打印的第一行「引擎路线」不是「照常开工」时，先照它做（2.0～2.3 复制一份副本升到 2.4.15；3.0～3.5 先装同一小版本的 Creator 导出原版），零件只装它列出的那些，再做别的。它报「Cocos 编辑器配置能解析」不通过时，先关 Creator，把报出的文件改名备份，再开 Creator。
- **Cocos Creator**：不假设装在哪。用 `find_creator.py --project <工程>` 找本机的编辑器、拿 2.x/3.x 对应的构建命令；构建前跑 `find_creator.py --busy`（整台电脑同时只跑一个构建）；3.x 的 web-mobile 导出缺 `index.html` 时跑 `fix_web_entry_3x.py --export <导出> --project <工程>`。没装工程那个版本怎么办、各版本的已知问题，见 [Cocos Creator 版本和已知问题](references/local-creator-versions.md)。
- **浏览器**：要开浏览器的检查和出包命令，一律在前面加 `python3 <skills>/cocos-game-to-english/scripts/browser_env.py --`：写包入口 `make_tiktok_zip.py`、`build_checked_zip.py`，`check_package.py`、`prepare_delivery.py`、`ad_regression.py`、`runtime_regression.py`，交付试玩链接 `serve_preview.py --keep`，截图和 dump_ui 用的 `chrome_touch.py`。装了 Ego Lite 就用 Ego；没装就用 Chrome、Edge 或 Chromium：后台运行、单独的临时资料夹，不碰用户自己的浏览器和窗口。**不用让用户装 Ego。** Ego 起不来或卡住（运行超时、报 browser exit、环境不完整）时，在 `browser_env.py` 后面加 `--browser chrome` 重跑同一个命令，不要让用户重启 Ego。10.2.10 在真包上比过两条路线：两款游戏的广告回归 10 例、一款游戏的 5 套运行时检查（启动、网络、布局、按钮普查、空壳），Chrome 和 Ego 的结论逐条相同。两包共用的文件里写着「必须用 Ego」「换 Chrome 要先问用户」的地方，英化以本段为准。
- **自己看画面**（第 1、3 阶段「确认能进首页、能玩一局」）：有 Ego 就在 Ego 里打开链接；没有就用 `browser_env.py --` 包着 chrome-mobile-testing 的 `chrome_touch.py` 跑一个计划（等首页、截图、点开始、再截图，计划写法见 chrome-mobile-testing），看截图和报告里的 `page_errors`。
- **Windows**：`python3` 写成 `python`（或 `py -3`）；路径有空格或中文时整段加引号。本包和 ad-boost 里 macOS 才有的写法换掉：`pgrep` 用 `find_creator.py --busy`；`/usr/bin/python3` 用 `python`；`cp -c`（macOS 的快速复制）用普通复制；`open -R`（在访达里选中文件）改成直接给完整路径；构建卡住时加的 `--no-sandbox --disable-gpu-sandbox --disable-gpu` 是 macOS 的写法，Windows 先不加。
- **浏览器卡住和构建沙箱（简化.11.14）**：要开浏览器的检查一律用 `browser_env.py --game <游戏名> --report <文件> -- <命令>`；Ego 卡住它会自己换 Chrome，回复里照 report 写「这一步换成 Chrome 跑的」，不要自己去退出或重启 Ego。构建前先跑 `find_creator.py --preflight`，退出 3 就别构建、也别重试，换不受沙箱限制的终端；构建命令照 find_creator 打印的原样用（TikTok 那条前后各带一次 sync，sync 没过不构建；3.x 出包命令带 `configPath=docs/startup/build-config-3x.json`），别删末尾三个参数，也别只复制 Creator 那半条。
- **试玩链接打不开窗口**：`serve_preview.py` 会试着开一个 Google Chrome 窗口；没装 Chrome 时窗口不开，服务照样在。把 `http://127.0.0.1:端口/` 链接发给用户，用户用任何浏览器（Edge、Safari 都行）打开。
- **没有生图工具**：有核准整词字图和同款干净无字底时，先用包内[固定英文按钮生成器](../remake-art/references/fixed-caption-button.md)完成；需要新画的资产再用生图工具生成（代码画的不算）。你没有生图工具时，先用大白话告诉用户：这台电脑上的 AI 不能生成图片；再出一道选择题：「换一个能生图的 AI 来做美术这一步」「先把别的做完给试玩链接，带中文的图先留原图」。选第二个，就把要换的图列进 `docs/english/art-todo.json`（每张：图片路径、在哪一页、中文原文、英文定稿、尺寸），其余照常做；图里还有中文的出不了包（图片复核记录会拦）。ad-boost 的美术流水线没有 Codex 时退出码 3，照 ad-boost 说的用你自己的生图工具出图，再用 `record_manual.py` 补记录。
- **没有 Grok**：`grok-image-review` 只是帮忙读图上的字，没有就自己打开原图看。
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
| 2 | 首页加两个功能键 | 个人主页回访（Revisit from Profile）、添加桌面（Add to Home Screen）。**原首页按钮全部不动**，只在原布局空位加这两个；所有环境都显示、不隐藏（本地试玩也显示）；平台不支持时点击提示 “Available in TikTok”，不发奖；真实成功才发奖，奖励各 5B（一次首页礼盒基础奖励，换算成原游戏货币），失败有反馈。原游戏没有金币的（Saul 2026-11-04）：有体力的各发体力 +3；金币体力都没有的，先加一种金币和皮肤给它当花处，再发 5B（[经济规则](../remake-economy/references/economy-rules.md)第三节末尾）。|
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
- 做法：照 ad-boost 流程 ⓪（这台电脑第一次用先跑 `scripts/doctor.py`）和 ①（`scripts/diagnose_ads.py` 加 `--mode localize`）。**跳过 ② 和 ③：不出选择题、不问 Saul**，直接按诊断的推荐顺序加：广告量「缺必备」或「少」加前 3 个（带 ★ 的），「一般」加前 2 个，「多」加第 1 个。再照 ④ 一个一个装：零件（装完跑 `assemble.py --verify`）、面板、音效、按原游戏画风生成美术、接线。复活和结算 x2 照第 6、7 项做。**时间（10.2.7）**：第一个链接前只跑 ⓪ ①、定下加哪几个；④ 的安装在第 4 阶段 Saul 试玩第一轮时做，第二轮链接带上（见第 2 阶段「第一轮美工」）。
- 哪些不加：诊断「不推荐」的不加；道具补给、皮肤看广告、体力 +3、商店看广告免费领、任务/成就领奖 x2 只在原游戏本来就有这个系统时才加（诊断已经按这个排）；奖励关会动原关卡，不加。
- 授权：英化本来不加新系统，**这几个看广告板块是 Saul 2026-10-31 定的默认例外**，不用再问。Saul 试玩后说不要哪个，就把那个板块拆掉（入口、面板、广告位）。
- 首页：**原首页按钮一个都不动**（不挪、不缩放、不重排），新入口只放空位，不压原按钮和首页上方的大图。**没有空位时不问**，换推荐顺序里下一个不用首页入口的板块（局内漂浮礼物、道具补给、开局增益这类）。接线前后各截一张同一手机尺寸的首页（`docs/adboost/home_before.png`、`home_after.png`），加入试玩链接前先对比，确认原按钮没有被遮挡或移动。
- 画风和数值：新板块的面板、按钮和图标跟原游戏画风走，排在主要页面的图后面生成（整台电脑同时最多 2 个生图任务，ad-boost 的 `gen_images.py` 管）。数值只用 ad-boost 各板块 README 第 5 节的已定数值（数额按货币板块），原游戏已有的数值不改；板块数值没有默认时不问，换下一个推荐板块。
- 检查放哪：ad-boost 新面板、按钮、图标、布局及按钮可达性的美工检查，放在带上该板块的英文试玩链接之前；接入时先验证本次操作的奖励、保存和防重复结果；各板块 README 第 8 节的完整验收及广告回归放到第 5 阶段。试玩链接照本页第 3 阶段起，ad-boost ⑤ 的试玩宿主只在没有 web-mobile 版时用；出包照本页第 5 阶段（`--board localize`）。
- ad-boost 里写英化要等 Saul 在选择题里选、没有空位时问 Saul、交付记录写「在选择题里的选择」的地方，英化游戏以本页为准。
- 交付记录写一行：「XX、YY 板块按英化默认做法加入（Saul 2026-10-31：英化默认执行广告 Skill，不用询问）。」

## 阶段

**前期预防（Saul 2026-11-04）**：第 1 阶段读取[前期预防](references/early-prevention.md)，把条件状态、共享组件使用者及改动涉及的保存/接入信息补进已有记录；第 2 / 4 阶段按该页先确认代表件实际状态，再批量制作，改动功能就地核对结果与重载。下文“第 5 阶段检查”指完整回归与出包套件，不推迟这些制作和接入时的局部验证。

**先查美工，再给英文试玩链接（Saul 2026-11-03）**：顺序是 ① 盘点＋中文原版链接 → ② 英化、第一轮美工和 ad-boost 诊断 → ③ 导出核对、中文专项检查、完整美工检查，修复并复查通过后给英文试玩链接＋人工检测清单 → ④ 试玩改进，每轮给新链接前复查受影响整页、共享组件和新增页面；其余页面的新图和 ad-boost 板块也先查再带入链接 → ⑤ 用户确认后做其余全量检查和出包。明显的画面、排版、图片和按钮问题由 AI 先发现并修好，不留给 Saul 试玩来找。美工检查按第 3 阶段和美工 Skill 验收清单执行；广告回归 10 例、运行时套件、`preflight.py`、已知问题、平台兼容和写包入口仍在第 5 阶段。共享库和美工板块中旧的“英化试玩前不查美工、第 5 阶段才查”说明作废，以本页为准。

**用时（10.2.12）**：每个阶段开始跑 `T stage <N>`、做完跑 `T done`，中间每一步记 `T begin`／`T end`，`done` 打印的用时发给 Saul。`T` 是 `python3 <skills>/cocos-game-to-english/scripts/stage_timer.py --project <工程>`；什么时候跑哪一条、步骤叫什么名字，见下面「用时汇报」。

1. **盘点**：**中文源码不带 .git（Saul 2026-11-04，91 SLS11）**：91 卖家给的 SLS11.zip 带着完整的 `.git`，提交记录里有上架文案 `app_desc.txt`（开发者账号和密码）。中文源码一律用 `python3 scripts/unpack_source.py --source <中文源码.zip 或文件夹> --out <新的工作目录>` 放进工作目录，不要直接 unzip / cp：`.git` `.svn` `.hg` `.idea` `.vscode` `__MACOSX` 不拷，`app_desc.txt`、`.env`、签名证书和私钥不拷，文本里像账号密码的行（比如 `settings/project.json` 的 `appSecret`）列在 `docs/source-intake.json`，交源码前把值清空。原 ZIP / 原文件夹不动；`unpack_source.py` 还会先把原包复制进游戏文件夹的只读 `_原始输入/`（只有 Saul 自己能删）。清理旧版本只用 `python3 <skills>/remake-core/scripts/clean_old_versions.py`，不手写 `rm -rf`。开工打印「已装 Skill 被改过，请走补丁」时，把列出的改动写成补丁交 Skill 会话，不要接着直接改已装文件。要交源码时用 `python3 <skills>/remake-core/scripts/make_source_zip.py --project <工程> --out <游戏_Source.zip>`（不带上面这些，带凭据就拒绝），`prepare_delivery.py --source` 和两个写包入口按同一规则拦（`source_hygiene.py`、出包门禁 `H1_vcs_ide_in_package` / `H2_credentials_in_package`）。
   **开工先给 Saul 中文原版的手机试玩链接，不等回复，接着往下做**（Saul 2026-10-31）。在中文原工程的一份副本上导出 Web（复制到工程外再导出，原工程一个文件都不动；用原游戏对应版本的 Creator 命令行：先跑 `check_machine.py --project <中文原工程>` 查电脑，再用 `find_creator.py --project <副本>` 找本机的编辑器、拿构建命令（见上面「换电脑也能用」和 [Cocos Creator 版本和已知问题](references/local-creator-versions.md)：没装那个版本先用同一小版本里最近的；2.4.3 要先放进本包的构建扩展再加 `--use-gl=desktop`；3.x 导出缺入口页时用 `fix_web_entry_3x.py` 补），其他写法见[真实 Cocos 运行](../remake-core/references/cocos-runtime.md)：2.4 是 `--path <副本> --build "platform=web-mobile"`，3.x 是 `--project <副本> --build "platform=web-mobile"`；macOS 命令行卡在导入资源时加 `--no-sandbox --disable-gpu-sandbox --disable-gpu`；原工程里已经有没改过的 `build/web-mobile` 也可以直接用），把导出的 `web-mobile` 整个复制到游戏文件夹的 `本地试玩_中文原版（不用上传）/`，再在后台起链接：`python3 <skills>/cocos-game-to-english/scripts/serve_preview.py --directory "<游戏文件夹>/本地试玩_中文原版（不用上传）" --snapshot --open --idle-minutes 0 --chinese-original --name "<游戏> 中文原版"`（`--chinese-original`：这是中文原版，不做中文专项检查；不加它，英化入口的 `serve_preview.py` 会当成英文链接去查，找不到英化工程就不起）。原版不用 `--keep`：原版没有美术回执，广告也还没接平台包，看广告冒烟对它没有意义。自己先打开链接，确认能进首页、能开始玩一局，再把链接发给 Saul（怎么自己看画面见「换电脑也能用」）。导不出 Web 时（引擎版本不对、构建报错、只有小游戏包没有源码），把原因写给 Saul，同样接着做。这份导出后面截中英对照图（`docs/baseline/`）也用。然后跑 `python3 <skills>/remake-core/scripts/tiktok_finalize.py init --project <中文原工程> --board localize`（写新游戏标记 `.tiktok-kit/policy.json`），再跑 `tiktok_finalize.py inventory --project <中文原工程>`，它把原版里的广告、加桌面/回访、触摸、启动、存档、分享/跳转/统计、登录代码逐项列到 `docs/english/platform-inventory.json`，第 2 阶段按它逐项改。inventory 之后马上跑 `tiktok_finalize.py rewire-ads --project <英化工程>`，再跑 sync；原版广告和加桌面/回访奖励由它改线，别手写桥；剩下的按 platform-inventory.json 的 rewire_todo 手改，delete_list 照单删（见 [rewire-ads](../remake-core/references/rewire-ads.md)）。3.x 游戏也一样跑 rewire-ads；`rewire_todo` 里 ad / ad_call / ad_handler 的行清零才往下做，别自己写浏览器里直接发奖的分支。和 `audit_new_english_images.py --make-list` 放在同一步做。然后列出全部中文（文字和图片字）、首页现有按钮、设置项、结算页、分享/更多游戏/排行榜入口、已知的操作问题。存档也在这一步盘点：跑 `python3 <skills>/remake-core/scripts/make_save_schema.py --project <工程> --inventory`，把原游戏所有存档键写进 `docs/save/save_keys.json`，关卡进度、金币、已买皮肤没存档的写进待改清单；原游戏有关卡文件时跑 `make_level_plan.py --project <工程> --record-level-files '<关卡文件 glob>'`。再跑一次 `fit_english_labels.py --project <工程> --dry-run`，哪些槽放不下最长的译文、要多宽，写进首件清单。把中文原名和英文名都写进 `docs/copy/glossary.json` 的 `"game_name"`（一定要写）：出包时 `game_name_scan` 用它比对 Label 文字和中文专项检查已经识出的图片文字，11-05 起开工的英化游戏有命中就拦，更早的只警告（见第 2 阶段「游戏里不放游戏名」）。`audit_new_english_images.py --make-list` 写出的 `art-replace-round1.json` 里，`regenerate` 带 `title_logo` 的那张是原游戏的标题 logo：第一轮按它的 prompt 画成主角、图案或场景，不写游戏名，也不要译成英文 logo。`platform-inventory.json` 的 `audio_todo` 列的是原游戏自己的声音入口（播放调用、平台音频对象、音乐和音效开关读写）：英化时把它们全部改走平台包 `AudioService`（音乐和音效分开开关），`audio_todo` 清零；`audio_summary` 有 `one_switch_suspect` 时，先确认音乐开关有没有连音效一起管，设置页两个开关各试一次。`reward_todo` 列的是原游戏自己加钱、扣钱、改道具的地方：英化时每条改走 SaveStore `grant`（发奖）或 `ShopTx`（扣费换东西），只改发奖和存档的写法，玩法不动；顺序固定为「凭证 → 保存读回 → 刷新界面 → 播动画」，动画回调里不发奖、不存档；x2 只算一次基础整数，显示和到账都读它的 2 倍；局内已进钱包的收益，结算时不再发一次。sync 报 `K_W_reward_*` / `K_W_x2_rounding_mismatch` 时照提示改。盘点原版时顺手查调试和别家残留：跑一次 `tiktok_finalize.py source`（会跑 `debug_leftover_scan`），把开着的 debug/cheat/test 按钮设成 inactive 或删掉，删掉能打开 FPS 统计的代码，原工作室开屏（启动场景里开局计时后自己淡出的节点、写着某某 Games/Studio 的字）直接去掉，让首页一出来就能点；平台配置的 App ID 和广告位只用平台包模板里的共用测试 App 或本游戏 `docs/platform/platform_ids.json` 记的，不留原游戏或别的游戏的。遗留名单上的旧英化游戏（射击高手、音乐消消乐等）继续做新版本时不跑 `init`，按旧游戏出包（拿不准就先跑 `tiktok_finalize.py decide --project <工程>` 看判定）；要改用标准件才跑 `tiktok_finalize.py adopt --project <工程>`。用时：开工第一件事跑 `T stage 1`，中文原版链接用 `serve_preview.py --chinese-original --project <工程>` 起，它自动记「中文原版链接」（没带 `--project` 或没记上时手动跑 `T mark 中文原版链接`），盘点做完跑 `T done`，用时发给 Saul，不等回复，接着做第 2 阶段。

   **标准件开工就装，每次构建前自动同步（生成时预防 P02/P05）**：`init` 之后紧接着跑一次 `python3 <skills>/remake-core/scripts/tiktok_finalize.py source --project <英化工程> --board localize`，再跑 `tiktok_finalize.py sync --project <英化工程> --board localize`，以后**每次构建前**都先跑 `sync`（约 1 秒，只把平台包文件按哈希换回原样、装上 `GameUIKit.js`，不动图片）；TikTok 小游戏包的构建命令照 `find_creator.py --project <英化工程>` 打印的整条用：构建成功后它自动跑 `sync --project <英化工程> --board localize --native <构建目录>`，把启动件、触摸修正、存档层、宿主接口兜底 host-shim、3.x 启动看守和 guard 装进这份构建（不手写 game.js 那几行），别只复制 Creator 那半条，不然包里没有 guard，出包时会报 `K_W_rewarded_guard`；sync --native 没过就先改它报的问题，别拿这个构建出包。find_creator 算不出构建目录时会提示，按提示手跑。3.x 工程 sync 也装 `GameUIKit.ts`。这样试玩和自测跑的就是带标准件的代码，不等出包才装（射击高手 v81、小熊拳击 R27 漏装触摸修正，指尖麻将 v55 重建丢了补丁，拇指弹球留着旧版 `RewardedService.js`）。遗留名单上的旧游戏 `sync` 只报告不改。新加或改动的弹窗、按钮一律用平台包的 `GameUIKit`（`var UI = require('GameUIKit')`：`UI.popup`、`UI.button`、`UI.toast`、`UI.digits`），别手写遮罩、淡出和点击；新加的正文 Label 一律用 `UI.text(parent, {w, h, text, overflow})`，教程手指一律用 `UI.guide(目标)`，原游戏的 Label 不动；AI 动过的原版按钮用 `UI.wrapExisting(节点, 函数)` 包一层；弹窗里的计时器和异步回调用 `popup.guard(回调)` 包住。用法见[平台包接入说明](../remake-core/assets/platform-kit/README_接入说明.md)第十一节。英化新加的弹窗用 `UI.popup`，提示文字从文案表取；`source` 会对手搭弹窗、写死遮罩和 PREVIEW/DEBUG/TODO 字样给警告。图标加数字（签到格、HUD 金币、价格）用 `UI.iconValue`，别手摆；页面上从存档来的数值写进 popup / 页面模板的 `refresh`；只在某些状态才出现的按钮用 `UI.newButton({active: false})`；首页两个入口的提示和排位交给平台包（2.4 的 `HomeGrowthEntries` 在 init 时传 `homePanel`，3.x 的 `placeLater` 自己等布局稳了再排），不要自己写提示 Label 或 scheduleOnce 一帧就排。弹窗的关闭图、提示底图、数字图开工时用 `UI.setup` 设一次，页面里别改 `UI.config()`；GameUIKit 1.1.7 起图被释放也会自动换回自带图。3.x 游戏的 PlatformConfig 由 `plugin3x_scan` 查 id 是不是从别的游戏拷来的；要查本机别的游戏，设 `TIKTOK_KIT_PEERS`。
2. **修改**：按上表 1–8 做。按[前期预防](references/early-prevention.md)先确认本批代表件和实际状态，再铺到所有受影响使用位置；涉及功能改动时随实现验证保存和重开结果。开始跑 `T stage 2`；做完跑 `T done`，用时发给 Saul，不等回复。
   - **第一轮美工：按美工 Skill 照原画风重新生成按钮和文字（Saul 2026-10-31）**：第一轮就做，不等点名。范围：所有按钮（带字的和不带字的图标按钮都算，Saul 2026-10-31：第一轮所有按钮都重新生成）、页面标题和所有图片字（中文改英文）；**游戏里不放游戏名**（Saul 2026-11-05：「以后的游戏都不要出现游戏名字，把对应的部分换成图案或者主角等美工来填充，不要是具体的游戏名字」）：原版首页等处的游戏名标题不做英文版，原位置换成照原画风生成的主角或图案图，大小和位置跟原标题一样；出包时 `tiktok_finalize` 的 `game_name_scan` 会查场景、预制体、文案表和已识出的图片文字里还有没有游戏名（11-05 起开工的英化游戏有命中就拦，更早的只警告）；报了不要停下来问 Saul：先跑 `python3 <skills>/remake-core/scripts/fix_game_name.py --project <工程>`，文字当场去掉；它写的 `docs/art/game_name_fix.json` 里每张图照提示词和参考图生成同名、同尺寸的无字图，放进一个文件夹，再跑 `fix_game_name.py --project <工程> --apply-images <文件夹>`，退出 0 就干净了；出图前跑 `python3 <skills>/remake-art/scripts/prompt_name_guard.py --project <工程> --file <提示词文件>`，提示词里不写游戏名（加 `--fix` 直接写出改好的提示词）；等级、关卡号、分数、货币（图片字的词＋0-9 位图数字＋货币图标）；新加的按钮（主页回访、加桌面、Watch Ad x2、复活、ad-boost 板块的按钮）和 Claim 小字。**分两批做（10.2.7，Saul 2026-10-31 同意）**：第一个链接只等主要页面：首页、设置、暂停、复活、结算这几页的所有按钮、标题和图片字，加上局内的等级、关卡号、分数、货币数字，以及主页回访、加桌面、Watch Ad x2、复活、Claim。其余页面（关卡选择、商店、皮肤、原游戏的签到/转盘/礼包、教程等）的按钮和图片字，以及第 8 项 ad-boost 板块的图，排在后面，第 4 阶段 Saul 试玩第一轮时接着生成，第二轮链接带上。一款要生成的图常有 100～150 张，全做完再给链接要 2～4 小时；主要页面一般 20～30 张。界面上的文字（Label、代码里的字）第一轮全部改成英文，只有图片里的中文分两批换。做法按[美工 Skill](../remake-art/SKILL.md)：固定按钮优先复用同款合格整钮。已有核准整词字图及同款无字底时，先按[固定英文按钮生成](../remake-art/references/fixed-caption-button.md)用本包脚本等比合成，图标和旧字层只保留一份。缺少核准原料时，用生图工具（image_gen）按定稿制作并核字，原图放进参考图照着画，尺寸、描边、颜色、位置跟原图一致；代码和字体画的按钮、数字不算（Saul 2026-10-30）；每出一张图跑 `art_records.py generated` 记下来。句子（说明、教学、提示）照第 1 项用真正的英文字体，不生成图片。先做 2～3 个有代表性的（一个带字按钮、一个标题、一组数字）放进游戏看一眼合成效果，没问题再批量做，有共性问题先改共用的图再接着做。画风照原游戏，不换风格；Saul 要求换画风或重新设计时看下面「美工」一节。沿用原画风时，原包里本来就有的深色、纯色背景和面板不用重做：art_check 按图片 SHA 认原图，记「原图保留，不适用」；Saul 选了保留原画风就写一行 `docs/art/keep_original_style.json`（decided_by、date、why），回执和出包会读它，不要再在会话里另记人工授权，也不要再问 Saul。开工时的纯色面板清单在 `art-replace-round1.json` 的 `style_choices` 里，只有 Saul 点名美工 Skill 才重做（`--make-list --flat-panels regenerate`）。
   - 固定按钮随包可运行样例见[CLAIM 配方](../remake-art/examples/fixed-caption/recipe.json)。按目标游戏内框重定参数，空间不足停止出图。试玩前在两种手机尺寸检查最终画面，分层图标按钮登记 horizontal_gap。
   - 美工领到新图或旧画面反馈时，先按[把曾经漏掉的画面问题用于首件制作](references/english-ui-rebuild.md#把曾经漏掉的画面问题用于首件制作)选对应做法，写进该类素材的生成或接图参数。先完成最窄尺寸的一件，再复用到同组。
   - **美工制作预防（Saul 2026-11-03）**：开始生图前先按[美工制作预防](../remake-art/references/production-prevention.md)落实 T01–T14 的适用项，再执行[生成前先定尺寸与分区](references/english-ui-rebuild.md#生成前先定尺寸与分区制作时消除问题saul-2026-11-03)：英文定稿、实际可读空间、宽高比与文字/图标/状态/动作分区先确定，再写进提示词；接图等比缩放并处理被替代的旧视觉层。先把最长按钮词、标题、密集卡片等代表样接到真实页面确认，再批量做，每批就地看组合效果并修共性问题，不留到第 3 阶段才返工。保持原游戏画风；“尺寸、位置跟原图一致”指尽量沿用外部布局，不能强行把英文压进原中文窄框。
凡新增或改动图标＋文字按钮、海报说明条、长正文和奖励计数，按[图文内区检查](../remake-art/references/local-ui-contract.md)登记受影响状态。试玩前普通 art_check 读取 docs/art/visual-slots.json；逐项核对实际截图，原料切对、语义绑定和运行布局分别验。

   - **平台能力用平台包**：激励视频用平台包的 `RewardedService.js`，加桌面、主页回访用 `TikTokMissionService.js`（`remake-core/assets/platform-kit/`），不另写一份桥接。它们已经把 UI 回调包在 try/catch 里，提示抛错也不会把请求锁死（MusicSlice v29b 手写的 bridge 提示一抛错，看广告、加桌面、回访全部卡在 Checking）。触摸修正、存档层、启动件、适配层、App ID、图片格式和压缩由出包入口自动装上并核对，不要手写；手写的同类文件会被换掉（旧游戏除外）。新英化游戏一律装存档层 `storage-guard.js`（原版多键存储也走它）；旧英化游戏默认不装，只在 `adopt` 以后装（Q6）。原版的广告管理器改成调 `RewardedService`、原版里直接 `createRewardedVideoAd` 或直接调加桌面/回访接口的代码删掉：新游戏漏改出不了包（`A1_rewarded_outside_kit`、`G1k_growth_outside_kit`）。原版（2.4）自带和平台包模块同名的脚本（例如自己的 `TikTokMissionService.js`），`source` 段会把它移到 `.tiktok-kit/removed/`。`PlatformConfig.js` 要填本游戏的 `gameId` 和 `normalLevelCoins`，没填新游戏出不了包（`K_platform_config`）；原游戏没金币时 `normalLevelCoins` 留 0（写包只警告），首页的 `HomeGrowthEntries.init(save, {reward, rewardText})` 传 `economy_capabilities.json` 里 `no_wallet_substitutes` 给的替代奖励（有体力的各 +3 体力；没体力的先加一种金币和皮肤，再发 5B），不传写包会报 `K_home_entries_no_reward`。 原版广告管理器先跑 rewire-ads，改不了的才手改。新做或重建的界面：背景用 `parts/ScreenFit.js` 的 cover 铺满，顶栏和底排用 safeTop / safeBottom；拖拽、滑动、摇杆用 `parts/TouchOwner.js`，不另写（见平台包接入说明第十七、十八节）。原版界面不动。
   - **做的时候就做对（生成时预防，简化.11.13）**：① Label、prefab 里的中文改成英文以后马上跑 `python3 <skills>/cocos-game-to-english/scripts/fit_english_labels.py --project <工程>`：放不下的单行字它直接改成 SHRINK（缩后不低于原字号 70%）；退出码是 1 时按 `docs/english/fit-labels.json` 的 todo 一条条改（加宽框、改短英文、多给一行），改完再跑，直到退出码为 0。数值、百分比、倒计时这类 Label 先在 `docs/english/label-values.json` 登记最长值（`max_value` / `longest` / `room`）再跑。倒计时按它自己的格式量（mm:ss 不按 00:00:00）；NONE 的字只记录不改，记录里 `wider_than_parent_plate` 的那几条接图时看一眼。跑完看记录里的 `bitmap_needed`：分数类数字已自动换成位图字，列出的固定词要用美工 Skill 生成整词图再接上，别用字体补。换字体或加 TTF/OTF 后马上跑 `python3 <skills>/remake-core/scripts/subset_fonts.py --project <工程>`（本机没有 fontTools 先 `python3 -m pip install fonttools`），别把整套字体放进主包。英文写进 Label 和 prefab 以后，紧接着跑 `python3 <skills>/cocos-game-to-english/scripts/english_copy_guard.py --project <工程>`：字面的 `\n` 它自动改成真换行；RichText 标签不配对、登记过的看广告按钮上没写 WATCH AD 时退出码是 1，改完再跑。美工生成位图数字和整词图之前先读 `docs/english/charset.json`：位图数字按 `value_charset` 一次画全，`word_images` 在首件之前一次生成齐；先拼进变量、过几行再赋给 Label 的格式串，english_copy_guard 算字符集时也认得出。位图数字的字符集以 `docs/english/charset.json` 的 `value_charset` 为准，数值格式化里的单位字母（K/M/B…）和符号也在里面；`fonts[].missing` 不为空就按这份字符集重画位图字，或者把单位和符号改用整字图 Sprite 槽，不要只画 0-9。第一轮接图按 `art-replace-round1.json` 的 `runtime_words.missing` 把代码运行时取的整词图一起画好（`txt_<slug>.png`），`untranslated_names` 先翻译再画。只改了几个节点时，`fit_english_labels.py` 加 `--nodes <这几个节点>`；停用的旧占位符在 `label-values.json` 写 `status: retired` 和 `reason`。preflight 的「文案写入校验」一行也会列出 RichText 不配对、看广告按钮没写 WATCH AD 的地方（现在只提示），看到了就跑 `english_copy_guard.py --project <工程>` 改掉。② 首页加主页回访、加桌面两个入口：2.4 挂 `HomeGrowthEntries`，不写入口坐标，它在 init 后按首页按钮和带触摸的节点自动摆，放不下报错；3.x 用平台包装好的 `TikTokKit.HomeEntrySlots.placeLater` 运行时摆两个入口，别手写入口坐标，手写了 `source` 会报 `K_W_home_entry_coords`（想先看空位时可以跑 `node <skills>/remake-core/assets/platform-kit/tools/home_free_slot.js --dump <首页 ui_dump> --screen <宽x高> --entry <宽x高>`）。首页新加的按钮一律用 cc.Button，加完调一次 `HomeGrowthEntries.placeEntries()`，不自己估坐标。原按钮不动；放不下就问 Saul。③ 换图接图用 `python3 <skills>/remake-art/scripts/bind_art.py --project <工程>`（2.4 和 3.x 都支持；按新图比例装进原框，自动设 trim 和 sizeMode），不手改节点宽高；接完跑 `bind_art.py --project <工程> --check`，只改这一轮换过图的节点，原游戏的图（拉满屏的遮罩、角色部件、进度条）照原样。生成的透明图裁边用 `remake-art/scripts/trim_visible.py`，别手写 getbbox；整词图、按钮字这类字图裁边时加 `--word`，它先自动去掉描边外的半透明彩色光晕（原图留作备份）再裁；退出码 1 表示光晕去不掉，按它打印的提示词（同尺寸、同字、no glow）重生成再跑，旧图别接。原游戏有皮肤的，皮肤预览只接每款自己的 previewFrame，别用槽框图、别整张染色，接完跑 `python3 <skills>/remake-core/scripts/check_skin_preview.py --table <皮肤表> --board localize`；皮肤表的 previewFrame 也由 `tiktok_finalize` 的 source、sync 自动查（英化只警告）。带字的新图过 ad-boost 的 `postprocess.py` 时会量字和字底的对比度，被拒就整张重生。④ AI 新加的图（主页回访、加桌面、广告板块的按钮图）走资源表：`python3 <skills>/remake-core/scripts/make_res_keys.py --project <工程>`（英化不加 `--strict`），代码用 `Res.sprite(ResKeys.x)`、`Res.request(ResKeys.x)`；原版加载代码不改。⑤ 原版玩法代码不改；AI 新加的暂停、复活、广告入口用平台包 `RunSession`（`pause('revive')`、`adHooks()`），不要再写一个暂停布尔。数值文字（音量 %、金币、分数、倒计时）用 `UI.valueLabel(node, {longest})`，别按当前值定宽。⑥ 要从音效库加声音时用 `python3 <skills>/remake-core/scripts/import_audio.py --project <工程> --file <音效库里的文件>` 导入（自动写 `docs/audio/credits.csv`），不手工复制；AI 新加的声音逻辑用平台包 `AudioService.js`；原版的声音文件不动，原版的播放调用、平台音频对象和开关读写按盘点的 `audio_todo` 改走 `AudioService`（见第 1 阶段盘点）。⑦ 原游戏关数少于 60 时，先跑 `python3 <skills>/remake-core/scripts/game_capabilities.py write --project <工程> --merge --level-count <原关数>`，再跑 `make_skin_table.py`、`make_economy_config.py`，两个都加 `--project <工程>`。跑完 `make_economy_config.py` 后接着跑 `python3 <skills>/remake-core/scripts/game_capabilities.py write --project <工程> --pause-button <关内暂停键路径>|--no-pause-button "原因" --ad-entry double=<路径> --ad-entry revive=<路径> …|--no-ad-entries "原因"`（ad-boost 加完板块后再跑一次补上新入口）；装 ad-boost 板块时照它的 SKILL 把各板块的 `save_keys.json` 合进工程 `docs/save/save_keys.json`，再跑 `make_save_schema.py`，零件自己建的状态（签到、礼盒、体力、板块的 round/board）登记子键时写 `"in_defaults": false`，可能是 null 的写 `"nullable": true`，别为了能登记把子键写进默认值；沿用原游戏的签到表时，`CheckinFlow` 传 `design: 'original'`；没有局外金币的游戏用 `make_economy_config.py --no-wallet --kind english --systems <有的系统>`，不再问「B 是多少」；货币审计一律带 `--project <工程>`；写 runtime 适配文件后跑一次 `game_capabilities.py adapter --project <工程> --adapter <适配文件> --out <新文件>`，用它出的那份。零件用法见[平台包接入说明](../remake-core/assets/platform-kit/README_接入说明.md)第十一至十八节。
   - **原版的 `.webp` 图**：新英化游戏由 `source` 段换成 PNG/JPG；数据或脚本里写死的 `.webp`（例如 `"imageExt": ".webp"`）按文件和行号被拒（`IMG0_source_images`），要改成 `.png`/`.jpg`。原版是 Cocos 3.x 的没有 WebP 例外（`K_webp_exception_3x`），只能靠 PNG/JPG 和 `max_side` 缩到 30 MB 以内。
   - **新做的英文图**：按显示尺寸 2 倍导出再压缩。新图（哈希不在英化前的图片清单里）单张超过 800 KB，出包会被拒；宽/高超过显示尺寸 2.5 倍的会被列出来，要改小（`remake-core/scripts/audit_new_english_images.py`；开工时用 `--make-list <中文原工程> --out docs/english/pre-english-images.json` 存英化前清单，出包时缺这份清单也会被拒。它同时把每张图、每个图集切片和动画帧读一遍，写 `docs/english/art-replace-round1.json`：replace 里的图第一轮美术就照原画风换成英文，manual_review 里的自己打开看；没有识字工具的电脑上全部列进 manual_review，一张都不能跳过；`regenerate` 里是整块单色的面板和背景，第一轮照原画风重画成有边框、明暗和图案的版本）。
   - **准备 `qa/ad-regression.json`（第 1 / 2 阶段定位真实入口与字段，第 5 阶段补齐并运行完整套件；不挡英文试玩链接）**：出包前的 10 个广告回归用例要它。`request` 走游戏自己真实的看广告方法，`grant` 挂在游戏真实的发奖函数上，`ready` 写首页已就绪的条件。示例：[examples/MusicSlice_ad-regression.json](examples/MusicSlice_ad-regression.json)（多渠道 AdsManager：`config.videoType=0` 后调 `config.AdsManager.ShowVideo()`，发奖统一走 `config.getReward`，示例把它换成计数）。同一个文件也给出包时必跑的运行时回归用（`cocos-game-check/package-check/references/runtime-regression.md`）：必须有 `home`（首页可用时返回 true），建议写 `enter_level`；缺 `home` 出包会被拒。**手机才出的问题要的几块（v7.9 手机问题源头约束，新游戏缺了出包被拒）**：`play`（首页 PLAY）；`resume_play`（`start` 进到一关、`probe` 真点一下、`state_js`，有倒计时写 `clock_js`；暂停键、继续键、关内广告名字认得出就不用写）；`ad_entries` 至少写结算页 Watch Ad x2（`"role": "double"`）和复活（`"role": "revive"`），各带真实操作到它出现（过关；让主角自己失败，`wait_node` 等按钮），第 8 项加的板块也写进去；`save_restart` 每一步写 `kind`，首页有什么就要有什么：过一关（`level`）、商店 / 皮肤买一件（`buy`）、领一次奖（`claim`）。写法和例子见 runtime-regression.md 的「手机检查补全」一节。
   - **广告规则去哪看**：按上面「看广告的几项按广告板块做」：广告计时和广告回归看 [超时规则与广告回归](../remake-ads/references/ad-timeout-and-regression.md)，复活页和结算 x2 两屏看 [一局结束：每屏一个视频按钮](../remake-ads/references/end-flow-one-video.md)，领奖窗看广告双倍勾选框看 [广告板块共用表](../remake-ads/SKILL.md#共用的广告设计)，数额看 [经济规则](../remake-economy/references/economy-rules.md)；和 [TikTok 固定适配·已定口径](../cocos-game-check/references/tiktok-fixed-adaptation.md) 有出入时以已定口径为准。
   - **图片复核记录 `docs/english/image-review.json`（第 5 阶段写，不挡英文试玩链接）**：上传包里每张不同的图（按 SHA-256）一条：谁看的、有没有中文、换成了什么；图集按切片看（`"slices_reviewed": true`）。缺记录、还是 pending、写着有中文却还是同一张图，出包会被拒（`remake-core/scripts/audit_image_review_record.py`）。图上的文字由 Codex 自己读取并作出结论。**照中文专项检查的结果写（Saul 2026-11-01）**：每张图有没有中文、图集是不是逐个切片看过，以 `docs/english/chinese-audit/` 里最后一次通过的 check 为准（自动扫描覆盖的写 `"reviewer": "chinese_audit 自动扫描"`，有复核结论的写复核编号）；不能凭印象手写 done / no / `slices_reviewed: true`，Garden Guardians 的 highwave 就是这样漏掉的。出包时程序把这两份对起来查，留 v7.9。 **这份记录不许手写（简化.11.14）**：出包前跑 `python3 <skills>/remake-core/scripts/audit_image_review_record.py write --zip <上传包> --out docs/english/image-review.json`；还剩 pending 的图，自己看过以后加 `--verdict <sha256>=yes|no --by "<谁看的>"` 再跑一次。手写或手改过的记录，出包时会被拒。
3. **英文试玩链接＋人工检测清单（Saul 2026-10-31）**：第 2 阶段做完导出 Web，先完成下面的中文专项检查和完整美工检查，通过后再给链接。每次导出后先跑 `python3 <skills>/cocos-game-to-english/scripts/check_export_images.py --project <工程> --export <这轮的 Web 导出>`（几秒，只看导出里是不是工程里现在的图；报旧图就是导出没成功，删掉导出目录重新构建，到 0 张旧图再往下走，见[常见坑](references/english-ui-rebuild.md)第 3 条；3.x 导出里没有 `index.html` 时先跑 `fix_web_entry_3x.py --export <这轮的 Web 导出> --project <工程>`）。
   **中文专项检查（Saul 2026-11-01，每次给英文试玩链接前都做）**：这也太牛了的波次警告里还有「高波来袭！」：字在 Spine 图集 highwave.png 的 `wave` 切片里，脚本和场景里搜不到，旧的图片复核记录却写着没中文。所以给链接前用 `python3 <skills>/cocos-game-to-english/scripts/chinese_audit.py` 查，结果都在工程的 `docs/english/chinese-audit/`：
   ① `scan --project <工程> --export <这轮的 Web 导出>`：列出全部资源；脚本、场景、预制体、配置里的字按字符串、注释、字段分开（注释、开发日志、节点名、编辑器路径自动放过，会显示的要结论）；每张图和每个图集切片（Spine `.atlas`、`.plist`、BMFont、龙骨）逐个识字；导出里对不上源图的图单独识。第一轮几分钟，以后每轮只识新加和改过的。
   ② 有要复核的：`sheet --project <工程> --pending` 拼出复核图（每格都看得清），你打开逐项看，每项写结论：`review --project <工程> --id <编号> --verdict <结论> --by "<你>" --evidence <复核图或切片图>`。确有中文写 `chinese`，然后把图改成英文、重新导出、回到 ①；识字认错了（特效、花纹、数字被认成字）写 `false_positive`，图一个像素都不改；会显示的文字确实不显示写 `not_displayed --reason "<理由>"`。识字出错、这台电脑没有识字工具的，也要这样逐个看过，不能当成没有字。隔离渲染的截图证据写 `--evidence-kind isolated_render`，它只证明资源显示对了，不算自然玩到、也不算真机。
   ③ `check --project <工程> --export <这轮的 Web 导出>`：通过才往下。过没过由它重算（清单、切片、识字回执、复核证据都要对得上现在的文件），手写的记录不算。它报「导出不是这版源码」时，用现在的源码重新导出，再 `scan --export`、`check`，不能拿旧导出凑通过。
   **改图后的重拍清单**：在第一张图开工时登记状态、共享资源、视口和可复查的数据条件；按[按状态补拍](../remake-art/references/capture-rounds.md)建立本轮来源记录。重拍有变化的状态，合并可沿用的原图，再用本轮真实 Web 导出跑完整美工检查。

   **完整美工检查（每轮给链接前必做）**：按 [美工验收清单](../remake-art/SKILL.md#验收清单)、[美术禁区与必做项](../remake-art/references/saul-art-rules.md)、[全量视觉巡检](../remake-art/references/full-visual-review.md)和[动态画面检查](../remake-art/references/dynamic-visual-review.md)执行。第一轮覆盖这轮导出中实际可见的全部页面、弹窗和条件状态（含加载中、加载失败/重试、首页、设置、暂停、复活、结算及已有广告面板），不只查首页；原图仍会显示的页面也要查，尚未替换的计划如实说明。iPhone 15、iPhone SE 两种尺寸截图并 `dump_ui`，Codex 自己逐页看图，检查中文、字形、超框、重叠、遮挡、压扁拉伸、清晰度、按钮/图标风格、数字图片字及版本号/Credits；图片显示宽高比与原图差不超过 10%。真实点击各页面按钮与弹窗开关，按动态画面规则录屏查闪屏。运行 `python3 <skills>/remake-core/scripts/art_check.py --project <工程> --dumps <这轮采集目录> --board localize --build <这轮的 Web 导出>`，按适用项通过并保留报告、截图和看图结论；发现问题直接修，重新导出后核对并复查受影响范围，未通过不给英文试玩链接。检查证据必须对应实际交给 Saul 的这轮导出；检查后再改图、布局或导出，受影响证据失效。后续轮次查改动影响的整页、共享组件和新页面（含新增广告面板），未变化且已通过的证据可沿用，不重复重评已认可的画风。这里验证广告面板的画面与按钮可达性；新接功能的局部奖励/保存验证已随实现完成，完整广告奖励行为回归仍放第 5 阶段。
   起链接：`python3 <skills>/cocos-game-to-english/scripts/serve_preview.py --directory <这轮的 Web 导出> --project <工程> --snapshot --open --idle-minutes 0 --ad-simulator --name "<游戏> 英文 第1轮"`。英化入口的 `serve_preview.py` 起英文链接前自己再查一遍：没过不起；它拿给 Saul 的快照和查过的导出一字不差才给链接，记在 `docs/english/chinese-audit/trial-links.json`（构建还在跑、查完导出又变了，会被拒，重新 ①③ 再起）。Saul 明说要先看没做完的英文版时才加 `--draft`：没过也起，回复里照它打印的列出没处理的问题，不能说检查过。 试玩链接由 serve_preview 自动截首页图核对（全黑、停在加载页、报错就不给链接），看它打出的截图，不要自己另外截图或 sleep 等待；它说没截图就是没核对。
   顶栏不手算胶囊位置：新游戏 source 自动装 CapsuleAuto。页面背景一律用 `ScreenFit.cover(cc, bg, {watch:true})`，别按设计尺寸铺，source 会查首页、局内、结算的背景（新游戏拦，英化警告）。update 里移动一律乘 dt（或 RunSession.move），节点在 onLoad 建好或从 FxPool 取，别在 update 里 new；sync 每次构建前会扫（新游戏拦，英化只提示）。
   中文专项检查和完整美工检查都通过后，再确认三件：能进首页；能开始玩一局；浏览器控制台没有报错卡死。美工硬问题已由 AI 先查并修复；Saul 试玩确认画面偏好、游玩体验和玩法改进。上面起链接的命令转到同包 `remake-core/scripts/serve_preview.py`（不加 `--keep`：`--keep` 会先跑看广告冒烟，没过就不给链接，看广告留到第 5 阶段查。`--ad-simulator` 让电脑上点看广告会弹出模拟广告窗，见[用户可操作广告模拟](../remake-ads/references/manual-ad-simulation.md)；用法见[固定手机尺寸试玩](../remake-core/references/user-phone-preview.md)）。自己先打开链接，确认进得了首页再发（怎么自己看画面见「换电脑也能用」）。用时：这一阶段开始跑 `T stage 3`；发链接前跑 `T done`（第 1 轮链接由 `serve_preview.py` 自动记，它打印「没记上」时手动跑 `T link 1`），`done` 打印的第 3 阶段用时贴在这条回复最后。
   回复里先用一句话说：这款原来有几个看广告的地方，第 8 项默认加哪几个板块（Saul 2026-10-31 定的默认做法，不用他选），这几个板块第二轮链接带上，不要哪个直接说。再用一句话写明这轮还是原图的页面（按这款写，例如「关卡选择、商店两页的按钮还是原图，第二轮换」），这几页的按钮这轮不用看。
   回复里直接打出**人工检测清单**：写在回复正文里，一条一行，不写成文件、不发文件路径。按这款游戏实际的页面、按钮和模式写，下面是要包含的内容，不照抄：
   - 画面：每一页（首页、设置、关卡选择、商店/皮肤、暂停、结算、复活……按这款写）还有没有中文；字有没有超框、重叠、被挡；按钮和文字是不是原游戏的样子；图有没有压扁、拉长、发糊；每个弹窗的关闭按钮看得见、点了能回去。
   - 新加的东西：首页的主页回访、加桌面两个按钮，点了提示 “Available in TikTok”；设置里音效、音乐两个音量分开调；结算页 Watch Ad x2 最大，下面一行小字 Claim，还有 Retry；失败时先出复活页；关里有暂停键，点开有 Continue、Restart、Home；第 8 项加的板块（这款加了哪几个就写哪几个，例如首页转盘、七天签到）点开能用，样子跟原游戏一样（第一轮链接里还没有这些板块，这一条从第二轮起列）。
   - 游玩：从第 1 关玩到第 N 关（按这款写）；每个模式都能暂停、继续、重来、回首页；过关、失败、复活、领奖后金币和数字对不对；退出再进，进度、金币、设置还在；操作点得准不准，手感怎么样。
   - 玩法改进：哪里太难、太无聊、想改的，直接说。
   - 不用你查：广告能不能真的播、播完发不发奖；TikTok 上的兼容问题（加载、触摸、存档、加桌面、回访）；只有手机上才会出的问题。这些等你说试玩没问题以后，我做全量检查。
   - 怎么告诉我：说哪一页、哪个按钮、什么样就行，能截图更好；一次说多条，我一起改。
4. **试玩改进（Saul 找问题、提改进，AI 改）**：用时：发完第一个链接就跑 `T stage 4`；Saul 每次回复先跑 `T back`；每起一轮新链接，`serve_preview.py` 自动记 `T link <第几轮>`（同一份导出重开不算新一轮），它打印的上一轮用时贴在新链接那条回复最后；它打印「没记上」时手动跑；Saul 说没问题时跑 `T back` 和 `T done`，用时发给他。Saul 试玩时接着做已计划的剩余内容；每轮起新链接前做中文专项检查和受影响范围的完整美工复查（见第 3 阶段），本轮功能的局部验证随实现完成，完整套件留到第 5 阶段。等的时候接着做第一个链接没等的部分（10.2.7）：其余页面的按钮和图片字，以及第 8 项 ad-boost 板块（零件、面板、音效、美术、接线）。他发来问题时先改他说的；这时已经做好的图和板块一起放进这一轮，没做完的放下一轮，不为了等图拖住他的修改。第 5 阶段之前，至少要有一轮链接带齐所有页面的新图和第 8 项的板块；Saul 在那之前就说没问题，就把剩下的做完、起新一轮链接，跟他说「剩下的 XX 页和 YY 板块换好了，看一眼没问题就说一声，我开始全量检查」。他说的每一条（画面和游玩的 bug，以及他点名的玩法、手感、难度、数值改动）一次全部改完、只构建一次；按第 3 阶段复查受影响整页、共享组件和新增页面的美工，通过后再起这一轮的新链接：照第 3 阶段对这一轮的导出过一次中文专项检查（scan 只识新加和改过的图，没变的沿用上一轮的回执和复核；新出来要复核的照样逐项看）；过了，先停掉上一轮的试玩服务，再用同样的命令起，`--name` 写第几轮（`--snapshot` 起的链接不会跟着重新导出变，不能只叫他刷新）。只是重开同一份导出（服务停了、Saul 要再看一遍）时，`serve_preview.py` 核对过它就是查过的那份，不用重新 scan。回复里写改了哪几条，再列一遍清单里和这几处有关的几条请他复查。玩法改动只改 Saul 点名的；要加新系统的，照上面「创新玩法」用现成板块。这样来回，直到 Saul 说试玩没问题（「没问题了」「可以了」「出包」这类话）。等他回复时可以先写第 5 阶段要用的 `qa/ad-regression.json`，这是提前准备适配；本轮改动的局部验证照常执行，不提前跑第 5 阶段的完整套件。
5. **全量检查和出包（Saul 说试玩没问题以后）**：Saul 说试玩没问题，就是同意做全量检查和出包，不再问一次。检查一条不减：
   - **先固定可验候选，再跑长矩阵**：按[稳定候选上的检查调度](../cocos-game-check/test/references/candidate-execution.md)，先核声音控件有实际播放消费者、奖励能落到真实可用对象、暂停重开没有旧回调，再校准实际 Native 的 adapter 准备路径；已有有效证据引用即可。同批已确认修复集中构建，完整套件前固定生产产物与检查器。工具失败先定点诊断；局部排查、完整验收和 writer 的结论各自保留，不减少下列门禁。
   - 这一阶段要开浏览器的命令，前面都加 `python3 <skills>/cocos-game-to-english/scripts/browser_env.py --`（哪些命令见「换电脑也能用」；有 Ego 的电脑照样用 Ego，没有的用 Chrome/Edge）。
   - **测试按完整清单跑完才算（生成时预防 R4D）**：`runtime_regression.py`、`ad_regression.py` 只有按完整清单跑完才算通过；带 `--suites` / `--cases` 是排查用，结论是「没跑完」（退出码 3），交付回复里照写没跑的项，不写成通过。检查脚本报告开头写引擎版本和实际检查项数，0 项、缺第三方库都报 not_run（并给安装命令），not_run 不算通过；检查脚本默认只读，`--help` 和不带参数都不许崩（发版自检 C10 逐个跑一遍）。
   - 先补齐记录：`qa/ad-regression.json` 和 `docs/english/image-review.json`（写法见第 2 阶段；image-review.json 用 `audit_image_review_record.py write` 生成，不手写）。
   - **美工检查已在每轮试玩链接前完成**：核对最后通过的美工证据与当前交付版本一致，不重复评审已认可的画风和配色。本阶段若改动图片、布局或新增页面，按第 3 阶段复查受影响整页、共享组件和条件状态；用户可见的改动先给通过美工检查的新链接确认，再继续出包。出包转换、压缩引起的缺图、变形、色带等仍须在最终产物核查。
   - 电脑上看不出来的：用[统一检查](../cocos-game-check/SKILL.md)，类型选“英化”。先跑一次 `python3 <skills>/remake-core/scripts/tiktok_finalize.py source --project <工程> --board localize`（英化工程的「平台包」一行查的是源码段记录是否新鲜，不查 `build-templates/bytedance/`），再跑 `check_known_issues.py`、`preflight.py`、`logic_check.py`（以往积累的已知问题在这里查）；广告、触摸、启动加载、存档、加桌面/回访按 [TikTok 固定适配](../cocos-game-check/references/tiktok-fixed-adaptation.md) 查。出包检查的页面探针读场景和坐标一律走 `remake-core/scripts/engine_adapter.js`（`runtime_regression/engine_adapter.mjs` 是它的拷贝）；报「引擎还没起来」是页面还在加载，会自动重试，不是游戏的错。3.x 工程要做完整 TS 检查时用 `python3 <skills>/cocos-game-to-english/scripts/ts_full_check.py --project <工程>`，别直接 `tsc -p tsconfig.json`（它会读 temp/ 里别的电脑的引擎路径）。
   - 标准件同步（P02）：第 1 阶段起每次构建前已跑 `sync`；这里的 `source` 只是出包前的最后一次，它报出要换回的文件时，说明前面有构建没跑 `sync`，那几次构建的自测要按新构建重做受影响的部分。
   - 广告加量（第 8 项 ad-boost 加的板块）：照 ad-boost 各板块 `modules/<板块>/README.md` 第 8 节验收；对比接线前后的两张首页，原按钮一个没动；每个新的看广告按钮真实点击测看完、取消、失败、超时、连点；`qa/ad-regression.json` 照 ad-boost 的例子写（签到、转盘结果、礼包领奖窗这种带勾选框的写 `double_claim`）。
   - 出包：改过源码就再跑一次 `source` 再构建，再用写包入口出包（`make_tiktok_zip.py` 和 `build_checked_zip.py` 都要给 `--project`；游戏自己的打包步骤在写包入口之前做完；广告回归 10 例和运行时套件由写包入口跑），按统一检查里的出包与最终包检查。v7.6 写包入口出的收据在 v7.7 不再是官方入口，交付前用 v7.7 写包入口重新出。交付时的试玩链接用 `--snapshot --keep --project <工程>` 起（这时跑看广告冒烟；中文专项检查照第 3 阶段对这份导出再过一次）。中文专项检查只管 Web 试玩；上传包里的图照样按出包检查查，不能拿试玩的结果代替。交付回复贴写包报告里的标准件小表，并写“标准件待真机复测”。
   - 手机上看到的问题（v7.9）：Saul 在手机上报过问题的，登记时写 `--source device` 和手机上跑的那个 ZIP；问题门禁 `check` 的结果有 `device_issues` 时，每条的 `line`（「复现了手机上的画面和同一行报错」「不能完全确定是同一个原因」「电脑上没复现，不能说修好了」）原样贴进交付回复，不改成「已修复」。做法见统一检查的[手机上看到的问题](../cocos-game-check/package-check/references/resource-and-reported-issues.md)。
   - 用时：这一阶段开始跑 `T stage 5`；交付时依次跑 `T mark 交付`、`T done`、`T report --all`，第 5 阶段用时和全程总表都放进交付回复。
   - **出包后返工（简化.11.15，Saul 2026-11-04：「出包后的返工修改，就只检查修改涉及的那些部分」「比如我修改了贴图，之后出包甚至又要检查一遍音频，这种情况不要发生」）**：测试包交给 Saul 以后又要改，只查改到的部分，不从头再查一遍：
     1. 照上面改源码、构建（`sync`、`source` 照旧）以后，出包前先跑 `python3 <skills>/cocos-game-check/package-check/scripts/rework_scope.py --old <出包文件夹> --native <新的 bytedance 构建> --project <工程>`。它先在构建的副本上装平台件、压 PNG（写包入口出包时对构建做的同一步；构建文件夹不动），再和出包文件夹 `最新.txt` 里的上一个交付包逐文件比，打印「返工范围」几行：改了哪些文件、用到改动的页面、写包时重跑哪些检查、沿用哪些、你自己要查的和不用再查的；同时记进 `<工程>/docs/checks/rework-<时间>.json`，下一个接手的 AI 读这份就知道查过什么、改了什么。
     2. 你自己只查「你（AI）自己要查的」那几项。改了图：只看用到这些图的页面（两种手机尺寸截图看图，对这几页跑 `art_check.py`）、中文专项检查（本来就只识新加和改过的图）、给改过的图补图片复核；不再听声音，不重测存档、广告流程、慢网和 Retry、帧率、触摸、加桌面和回访，也不重看没用到这些图的页面。改了音频：只播改过的声音、看设置里的音效和音乐开关。改了代码：就地验证改的那个功能，回复里写清改了哪个功能、怎么验的、为什么别处不受影响。
     3. 出包照旧用写包入口。两个写包入口的 `--rework-of` 默认 `auto`，自己找上一个交付包：只改了图片、音频、字体（代码、设置、页面结构、数据表、adapter、检查工具都没变）时，只重跑看得见这次改动的浏览器检查，其余沿用上一个包回执里的通过结果；别的改动全部照跑，并写明原因。静态检查和 ZIP 核对每次都跑。出完包写包入口自己再记一份 `docs/checks/rework-<时间>.json`，以这份为准。规则见统一检查的[出包后返工只查改动](../cocos-game-check/package-check/references/runtime-regression.md#出包后返工只查改动简化1115saul-2026-11-04)。
     4. 交付回复贴写包入口打印的「返工范围」几行，写明哪些沿用了上一个包的结果。不要为了「保险」自己再把全部检查跑一遍；Saul 明说要全部重查时，写包入口加 `--rework-of none`。

## 用时汇报（10.2.12，Saul 2026-11-01）

每个阶段做完，把这一阶段用了多久、里面每一步各用了多久发给 Saul；每轮试玩链接带上这一轮的用时；交付时给全程总表（Saul 2026-11-01：「能不能在skill放一个阶段用时的汇报，就是自动对应的每一个阶段结束了发一下用时多久，比如修改的一个阶段，改美工花了多久，第一步英化的美工设计花了多久，等等，全面一点设计」）。时间由 `stage_timer.py` 按电脑时钟记在 `<工程>/docs/timing/stage-timing.jsonl`，汇报也由它算好打印出来，原样发，不要自己估、自己算；压缩或重开以后记录还在。`T` 指 `python3 <skills>/cocos-game-to-english/scripts/stage_timer.py --project <工程>`。

- **阶段**：每个阶段开始跑 `T stage <1-5>`，做完跑 `T done`。`done` 打印的「用时｜第 N 阶段……」几行原样发给 Saul：第 3 阶段的贴在英文试玩链接那条回复最后，第 5 阶段的放进交付回复；第 1、2、4 阶段做完时单独发一条短消息，不等回复，接着做。忘了 `done` 就直接跑下一个 `stage`：上一阶段自动结束，它的用时一起打印出来，照样发。
- **每一步**：下表每一步开始跑 `T begin <步骤>`，做完跑 `T end <步骤>`；生成了图加 `--count 图=<张数>`。同一步做几次就记几次（构建导出每次都记），汇报写次数和总时间。派给子进程的步骤，派活时 `begin` 加 `--who 美术子进程`（代码子进程、文字子进程同理），子进程报回来时 `end`；子进程自己不记。表里没有、又花了 10 分钟以上的事，也用 `begin`／`end` 记，名字用大白话。
- **等 Saul**：英文试玩链接由 `serve_preview.py` 自动记（简化.11.9：第 1 款真游戏割草·蛋壳特工队的第 2 轮链接靠记得跑命令，没记上，结果 6 小时都算成了第 1 轮）。轮次按交给 Saul 的不同导出依次加 1，同一份导出重开不算新一轮；它打印「用时没记上」时手动跑 `T link <第几轮>`（同一轮号不会重复记）。从发链接起算等 Saul 试玩；问了 Saul 一件要他回答才能往下做的事（例如能不能装 Cocos），跑 `T ask <事情>`。Saul 回复了跑 `T back`（没在等时跑也不会错）。等 Saul 的时间单独算，不算进 Saul 等你的时间。中文原版链接不等回复，用 `serve_preview.py --chinese-original --project <工程>` 起时自动记；没带 `--project` 时发出去跑 `T mark 中文原版链接`；Saul 中途改要求时跑 `T mark 改要求：<几个字>`。
- **每轮试玩**：第 4 阶段每起一个新链接，`serve_preview.py` 记下 `T link <N>` 并打印上一轮的用时：Saul 试玩和回复用了多久、从他回复到新链接你用了多久、这一轮每一步各多久。这几行贴在新链接那条回复最后。
- **交付**：依次跑 `T mark 交付`、`T done`、`T report --all`。`report --all` 打印全程总表：各阶段用时、Saul 等你和你等 Saul 各多久、中文原版链接和第一个英文链接是开工后多久给的、每轮试玩从他回复到新链接多久、最花时间的三步、构建几次、生成了几张图、他中途改了几次要求。总表贴进交付回复，也写进 `docs/timing/timing-report.md`（每一步的开始、结束和谁做的都在里面）。
- **超过参考用时**：参考用时是第 1 阶段 30 分、第 2 阶段 1 小时 30 分、第 5 阶段 1 小时 30 分，第 4 阶段每一轮从 Saul 回复到新链接 45 分（等 Saul 的时间不算）。第 3 阶段先不设：10.2.12 定的 20 分只算三项确认，11 起加了中文专项检查、11.3.1 起加了完整美工检查，等第一款按现在的规矩走完第 3 阶段再按实际用时定（简化.11.9）。超过了，`begin`、`end`、`mark`、`status` 会打印一句提醒，每阶段、每轮只提醒一次；看到就用一句话告诉 Saul 卡在哪、大概还要多久。参考用时只是提醒，不是硬限制，不为了赶时间少做一步。
- **压缩或重开以后**：先跑 `T status`，看哪个阶段、哪几步还开着，在不在等 Saul，接着记。忘了记的，知道时间就加 `--at 时:分` 补上。
- **不挡流程**：用时记录出错（写不进、命令报错）就接着做英化，汇报里写一句「这一段没记上」。

| 阶段 | 步骤名（`begin`／`end` 用这些名字） |
|---|---|
| 1 盘点 | 查电脑（check_machine）、找Cocos（find_creator）、中文原版导出（导出到起链接）、盘点清单（init、inventory、列中文和页面） |
| 2 修改 | 英文文字、美工小样（先做的 2～3 个放进游戏看效果）、美工主要页面、固定入口、平台包、广告诊断（ad-boost ⓪①）、构建导出 |
| 3 英文试玩链接 | 构建导出、导出核对（check_export_images）、中文专项检查（chinese_audit 的 scan、复核、check）、完整美工检查（截图、dump、看图、art_check、点击与动态画面）、三项确认 |
| 4 试玩改进 | 改问题（Saul 这一轮说的）、美工其余页面、广告板块美术、广告板块（零件、面板、音效、接线）、构建导出、中文专项检查、美工复查 |
| 5 全量检查和出包 | 补记录（ad-regression.json、image-review.json）、美工证据与交付版本核对、统一检查、广告板块验收、出包（写包入口，含广告回归和运行时套件） |
| 哪个阶段都可能有 | 重做美术小样（Saul 要求重新设计时）、装环境（装 Cocos、Pillow 这类）、修构建（构建报错、导出还是旧图） |

发给 Saul 的样子（数字是举例）：

```
用时｜第 2 阶段「修改」：1 小时 10 分；从开工算起共 1 小时 30 分
- 英文文字：25 分
- 美工小样：10 分（3 张图）
- 美工主要页面：50 分（24 张图）
- 固定入口：30 分
- 构建导出：2 次，共 5 分
几步是同时做的，加起来比阶段用时长。
```

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

**重做美术先出小样（Saul 2026-10-31）**：Saul 要求英化游戏重做美术或重新设计时，先出小样，不直接做整套：出 2～3 套，每套 1 张首页加 2 个按钮（主按钮、看广告按钮），其中一套是「保持原画风，只改英文和新入口」；30 分钟内放进试玩链接或发图给 Saul 挑，他选了再做整套，都不满意就再出几套。等他选的时候接着做不碰美术的部分（广告入口、代码）；小样发出前按下文查，做成可玩英文链接时仍按第 3 阶段完成美工检查。小样和 Saul 选的那套记在 `docs/samples/samples.json`。小样这样做（Saul 2026-11-01「把这三点补进v7.9一起改」）：
- **给 Saul 挑的是做出来的样子**：每套的 2 个按钮和标题单独生成，按计划显示尺寸摆进游戏真实首页，截图给他挑。不拿一次画出的整页效果图给他挑：整页图上的字常是乱的，排版也和真页面不一样，挑中以后按钮一张张生成再拼进游戏，会和效果图对不上。整页图可以拿来定方向、当生成按钮的参考图。
- **每套先过美术检查再给他看**（以下两行是小样的重点项；可玩英文试玩链接仍须过第 3 阶段的完整美工检查）：摆好以后 dump 这一页跑 `art_check.py`，「按钮底色不深、物品图标不另垫底板」和「深色粗字（永久禁止）」两行不过的那套，先改好或换一套。不然他挑中的那套，出包时会被拦。
- **挑一次就定死**：只在开工时，和 Saul 说「换风格」「这页重做」时挑；之后每轮美工不再重新挑。选定以后把这套的颜色（HEX）、材质、圆角、描边写进 `docs/samples/samples.json` 选中的那套；之后每个按钮都带这套的截图和 2 个按钮当参考图生成，先做 3 个放进游戏看对不对，再批量做。
