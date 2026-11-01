---
name: cocos-game-to-english
description: "英化（触发词：英化、英化skill、中文源码、翻译成英文、英化这个游戏）。拿到能运行的中文Cocos完整游戏时用：开工先给中文原版的手机试玩链接（不等回复）；把中文美工和文字改成英文（第一轮按美工板块 remake-art 照原画风重新生成所有按钮和文字）；补齐固定入口（个人主页回访、添加桌面、音效/BGM音量、结算页看广告双倍与Retry、看广告复活），删除分享/更多游戏/联网排行榜；看广告的几项按包里的 remake-ads、remake-economy 做，看广告的板块默认按包里的 ad-boost 诊断后按推荐加，不问 Saul；先给英文试玩链接和人工检测清单，Saul 试玩没问题后才做全量检查和出包；macOS、Windows 都能用，没有 Ego 时用 Chrome/Edge 跑检查。默认不改玩法、不加关卡、不加新系统。"
---

# 英化（独立流程）

修订：`2026-10-31.english-simple.10.2.10`（10.2.10：换电脑也能用：开工先跑 `check_machine.py` 查电脑，`find_creator.py` 找 Cocos Creator，要开浏览器的检查都用 `browser_env.py` 包一层（没有 Ego 就用 Chrome/Edge），3.x 导出缺入口页用 `fix_web_entry_3x.py` 补，写明 Windows、没有生图工具、没有 Grok 时怎么做，Saul 2026-10-31「英化skill基本是给别人用的……各个步骤都要具有不同电脑的通用性」；以前各版见 [版本历史.md](版本历史.md)）。

英化和重塑是两条独立的路：英化默认只用本包（本包带广告 remake-ads、货币 remake-economy 两个板块和广告加量 ad-boost）；Saul 要求创新玩法时，新加的部分用这两个板块和重塑包里的关卡、皮肤、引导板块（见下面「创新玩法」）。

## 一屏看懂（先读这个）

拿到中文 Cocos 完整游戏，按五步走：

- ① 盘点：先查电脑（`check_machine.py`，见「换电脑也能用」），再给 Saul 中文原版的试玩链接，不等回复；接着写新游戏标记、列清单。
- ② 修改：做下面「只做这几件事」的 8 项。第一轮美工照原画风重新生成所有按钮和文字，第一个链接只等首页、设置、暂停、复活、结算和局内数字；第 8 项 ad-boost 这一步只诊断、定下加哪几个。
- ③ 英文试玩链接：只确认能进首页、能玩一局、没有报错卡死，就给链接，回复里直接打出人工检测清单。
- ④ 试玩改进：不跑检查。Saul 说的一次改完，每轮起新链接；同时做完其余页面的新图和第 8 项的板块。
- ⑤ 全量检查和出包：Saul 说没问题以后做，检查一条不减，用写包入口出包。

每一步的细节在下面「阶段」一节；要读哪些文件见「读哪些文件」。

**必须遵循（Saul 2026-10-29）**：TikTok 固定适配（触摸、启动加载、激励广告、存档读值、适配层、图片、加桌面/回访、登录/App ID、胶囊/首页底排/不要 Credits）和跨游戏通用流程一律按 [TikTok 固定适配](../cocos-game-check/references/tiktok-fixed-adaptation.md) 做：英化一律加看广告复活，核心玩法里的分享奖励改激励视频、其他分享入口删掉，加桌面/回访奖励各 5B；新游戏只用平台包标准件，不手写；旧游戏只给警告，由各自会话处理。

拿到的是一个能运行的完整游戏。默认保留原工程、原玩法、原关卡、原画风、原声音和存档；不补关，不加经济、皮肤、礼盒、签到、教程等系统（看广告的板块由 ad-boost 默认加，见第 8 项）。关卡、皮肤、引导板块不主动调用；广告板块只用在下面「看广告的几项按广告板块做」写的几处（不用 Saul 点名），货币板块只用来算这几处和 ad-boost 板块的数额，原游戏的价格和其他数值不改。第 4 阶段 Saul 试玩时点名要改的玩法、手感、难度和数值，照他说的改，只改他点名的。

**创新玩法（Saul 2026-10-30）**：Saul 要求给英化游戏加新玩法时，算单独任务。新加的部分用现成的板块做：广告 remake-ads、货币 remake-economy（本包自带）；关卡 remake-levels、皮肤 remake-skins、引导 remake-onboarding（在重塑包里；只装了英化包的电脑要先装重塑包）。不另写一套，这样不容易出新 bug，做过的也能复用。只做 Saul 点名的部分，原有玩法照旧不动；加关在关卡表写 `explicit_total`，新加的部分照对应板块的检查查。

## 换电脑也能用（10.2.10，Saul 2026-10-31）

英化包是给别人用的，会装在别人的电脑上（macOS 或 Windows）。照下面做，每一步在哪台电脑上都能跑（Saul 2026-10-31：「我的英化skill基本是给别人用的……各个步骤都要具有不同电脑的通用性，不要出现ego这些不兼容，无法测试……cocos无法正常使用等问题」）：

- **「Saul」是谁**：本包写的「Saul」指正在用这个 Skill 的人（给你游戏、试玩、做决定的那个人）。「Saul 定的」规则照样遵守；回复照样用大白话，要他定的只出选择题，跑命令、找路径、装东西都由你来做。
- **开工先查电脑**：第 1 阶段第一件事跑 `python3 <skills>/cocos-game-to-english/scripts/check_machine.py --project <中文原工程>`，一分钟内查完 Python、Pillow、numpy、ffmpeg、Node.js、出包检查用的浏览器和这款游戏的 Cocos Creator。缺必须的，用大白话告诉用户缺什么、影响哪一步，问一句能不能装；同意后由你来装，装好再跑一次。缺的东西不影响的步骤先接着做。
- **Cocos Creator**：不假设装在哪。用 `find_creator.py --project <工程>` 找本机的编辑器、拿 2.x/3.x 对应的构建命令；构建前跑 `find_creator.py --busy`（整台电脑同时只跑一个构建）；3.x 的 web-mobile 导出缺 `index.html` 时跑 `fix_web_entry_3x.py --export <导出> --project <工程>`。没装工程那个版本怎么办、各版本的已知问题，见 [Cocos Creator 版本和已知问题](references/local-creator-versions.md)。
- **浏览器**：要开浏览器的检查和出包命令，一律在前面加 `python3 <skills>/cocos-game-to-english/scripts/browser_env.py --`：写包入口 `make_tiktok_zip.py`、`build_checked_zip.py`，`check_package.py`、`prepare_delivery.py`、`ad_regression.py`、`runtime_regression.py`，交付试玩链接 `serve_preview.py --keep`，截图和 dump_ui 用的 `chrome_touch.py`。装了 Ego Lite 就用 Ego；没装就用 Chrome、Edge 或 Chromium：后台运行、单独的临时资料夹，不碰用户自己的浏览器和窗口。**不用让用户装 Ego。** Ego 起不来或卡住（运行超时、报 browser exit、环境不完整）时，在 `browser_env.py` 后面加 `--browser chrome` 重跑同一个命令，不要让用户重启 Ego。10.2.10 在真包上比过两条路线：两款游戏的广告回归 10 例、一款游戏的 5 套运行时检查（启动、网络、布局、按钮普查、空壳），Chrome 和 Ego 的结论逐条相同。两包共用的文件里写着「必须用 Ego」「换 Chrome 要先问用户」的地方，英化以本段为准。
- **自己看画面**（第 1、3 阶段「确认能进首页、能玩一局」）：有 Ego 就在 Ego 里打开链接；没有就用 `browser_env.py --` 包着 chrome-mobile-testing 的 `chrome_touch.py` 跑一个计划（等首页、截图、点开始、再截图，计划写法见 chrome-mobile-testing），看截图和报告里的 `page_errors`。
- **Windows**：`python3` 写成 `python`（或 `py -3`）；路径有空格或中文时整段加引号。本包和 ad-boost 里 macOS 才有的写法换掉：`pgrep` 用 `find_creator.py --busy`；`/usr/bin/python3` 用 `python`；`cp -c`（macOS 的快速复制）用普通复制；`open -R`（在访达里选中文件）改成直接给完整路径；构建卡住时加的 `--no-sandbox --disable-gpu-sandbox --disable-gpu` 是 macOS 的写法，Windows 先不加。
- **试玩链接打不开窗口**：`serve_preview.py` 会试着开一个 Google Chrome 窗口；没装 Chrome 时窗口不开，服务照样在。把 `http://127.0.0.1:端口/` 链接发给用户，用户用任何浏览器（Edge、Safari 都行）打开。
- **没有生图工具**：第一轮美工要用生图工具把按钮和字整张生成（代码画的不算）。你没有生图工具时，先用大白话告诉用户：这台电脑上的 AI 不能生成图片；再出一道选择题：「换一个能生图的 AI 来做美术这一步」「先把别的做完给试玩链接，带中文的图先留原图」。选第二个，就把要换的图列进 `docs/english/art-todo.json`（每张：图片路径、在哪一页、中文原文、英文定稿、尺寸），其余照常做；图里还有中文的出不了包（图片复核记录会拦）。ad-boost 的美术流水线没有 Codex 时退出码 3，照 ad-boost 说的用你自己的生图工具出图，再用 `record_manual.py` 补记录。
- **没有 Grok**：`grok-image-review` 只是帮忙读图上的字，没有就自己打开原图看。
- **只在 Saul 电脑上有的路径**：`！游戏学习库/`、`！Skill更新/`、`~/Downloads/！自制游戏/` 这类只是来由和证据的出处，别的电脑上没有，找不到就跳过，不影响做游戏。

## 读哪些文件（只读要用的，10.2.8）

2026-10-30 那批英化游戏，每个线程开工都整页读一遍 TikTok 固定适配，好几个线程还照着美工板块、共享库里「交试玩前做完」的旧说法多做检查。开工和每个子进程都按下面读：

- **主线程开工**：本页，加[固定入口](references/fixed-entries.md)和[Cocos Creator 版本和已知问题](references/local-creator-versions.md)。
- **[TikTok 固定适配](../cocos-game-check/references/tiktok-fixed-adaptation.md)**（约 98 KB，必须遵循）：开工读这几节就够，约 30 KB：[已定口径](../cocos-game-check/references/tiktok-fixed-adaptation.md#已定口径不再让模型临场决定)；「第二部分：跨游戏通用流程」8 条（存档写入、复活和 x2、弹窗布局、源码和包对不上、英化固定清理、读包内文件、图片卡住、玩法状态）；第一部分第 9 条（胶囊、首页底排、不要 Credits）；最后的「第三部分」「第四部分：不要做」。「出包时怎么装」（约 29 KB）到第 5 阶段出包前再读。第一部分其余几条（触摸、启动加载、广告计时、存档读值、适配层、图片、加桌面/回访 SDK、登录/App ID、声音）是出包入口自动装上、门禁自动查的标准件，不用手写，门禁报到哪一条再读那一条。游戏在遗留名单上时读「新游戏和旧游戏」。这页照样必须遵循，只是不用开工就整页读。
- **第一轮美工**：[美工 Skill](../remake-art/SKILL.md) 开头的英化包说明、[Saul 的美术禁区与必做项](../remake-art/references/saul-art-rules.md)、[英文界面重建](references/english-ui-rebuild.md)。
- **看广告**：下面「看广告」一节列出的那几页；第 8 项读 [ad-boost](../ad-boost/SKILL.md) 和要加的那几个板块的 `modules/<板块>/README.md`。
- **第 5 阶段**：[统一检查](../cocos-game-check/SKILL.md)的「英化」一列，和门禁报出来的那几条。
- **不用读**：重塑包的关卡、皮肤、引导板块（创新玩法时才读）；`remake-core/references/` 里的总规则（检查报错指过去时只读那一页）；ad-boost 没加的板块。
- **子进程**（见「并行分工」）：美术只读第一轮美工那三页；代码只读固定入口、[平台包接入说明](../remake-core/assets/platform-kit/README_接入说明.md)、「看广告」一节和 TikTok 固定适配第二部分；文字只读英文界面重建和商标词表 `remake-core/assets/trademark-words.json`。主线程派活时把要用的一两条规则贴进去，子进程不整页读 TikTok 固定适配。

## 只做这几件事

逐项判断这个游戏要不要做；不需要做的写一句原因跳过。

| # | 做什么 | 说明 |
|---|---|---|
| 1 | 中文改英文 | 代码字符串、Label、平台文案改成自然英文；中文图片字和带字的按钮第一轮就按[美工 Skill](../remake-art/SKILL.md)照原画风重新生成英文版（尺寸、描边、颜色、位置跟原图一致，见第 2 阶段「第一轮美工」），换字体并确认放得下。**句子（说明、教学、提示，两个以上单词）用真正的英文字体（TTF），不许用生成的字母图集拼句子**——那样小写会被画成大写，出现 HelP/TaP/Pond；图片字只用于固定短词和数字。**等级、关卡号、分数、货币、奖励数（Saul 2026-10-30："这种是所有游戏都需要进行的"）**：原版不管是图片字还是普通字，英化后一律按原画风做成"图片字的词（LEVEL、货币名）＋生成的 0-9 位图数字＋货币图标"，不能是一整行英文普通字（反例："LEVEL 1 • +10 PEARLS" 白字压在半透明色条上）；数字后面也不铺纯色色条。`art_check.py` 的 `font_number`、`font_value_label`、`flat_value_plate` 在英化游戏同样拦，登记成运行时文字也不豁免。设置页不显示版本号和 Credits（`dev_info_text`）。**品牌车名、动漫角色名不直译**（v7.8 E8：「法拉利458」不写 Ferrari 458，写 Supercar 这类通用叫法），`audit_copy_quality.py` 按 `remake-core/assets/trademark-words.json` 拦，并写出命中的词。改完全屏扫一遍，不许残留中文（含角落小字）。规则见 [英文界面重建](references/english-ui-rebuild.md)、[动态文字字形](references/dynamic-text-glyph-review.md) |
| 2 | 首页加两个功能键 | 个人主页回访（Revisit from Profile）、添加桌面（Add to Home Screen）。**原首页按钮全部不动**，只在原布局空位加这两个；所有环境都显示、不隐藏（本地试玩也显示）；平台不支持时点击提示 “Available in TikTok”，不发奖；真实成功才发奖，奖励各 5B（一次首页礼盒基础奖励，换算成原游戏货币），失败有反馈。|
| 3 | 设置里两个音量 | 音效（SFX）和背景音乐（BGM）分开调节、立即生效、重启后保留 |
| 4 | 删除三类功能 | 分享给朋友、更多游戏、排行榜：按钮、入口和相关代码调用全部删掉，删后页面不留空洞。**例外（v7.5，Saul 在细菌2048 的选择）**：原游戏核心玩法里的分享奖励（复活、礼物、双倍）改成激励视频；其他分享入口连同触发它的礼物球、弹窗一起删干净。不许留“本平台不可用”的提示按钮；每个分享调用在 `docs/` 写明删掉还是改成广告。**局内本地名次可以留（Saul 2026-10-31，照 68 小熊拳击）**：一局里玩家和电脑对手的名次（局内分数牌、结算名次）、按名次给的本地奖杯和段位、个人星级和最高分都不算排行榜；数据只存本机、不联网，匹配页写 Finding opponents，电脑对手不用真人风格的名字，段位叫 Tier 不叫 League。要删的是联网的世界/好友/地区/周榜（含开放数据域）、本地编出来的全服名次（如 “You are #3,512”、“Top 5%”）和假联赛；`remake-core/scripts/audit_no_social_features.py` 按这个口径查。见 [固定入口](references/fixed-entries.md) |
| 5 | 修正操作 | 原来操作有问题的位置改好（点不到、点了没反应、改动后某处操作消失要补回）；不新增玩法 |
| 6 | 每关结算页 | 有 Retry；统一加 **Watch Ad x2** 入口，是结算页上最大、最显眼的按钮；普通领取（Claim）是它正下方一行可点的小字，不做成第二个按钮（Saul 2026-10-31）。见 [固定入口](references/fixed-entries.md)；样子按[广告板块·结算页设计](../remake-ads/SKILL.md#结算页设计用户-2026-10-27)，广告行为和 x2 数额按广告、货币板块（见下面「看广告的几项按广告板块做」） |
| 7 | 看广告复活 | 有失败/中断的一局都加“看广告复活”；**没有失败状态的游戏也加**（按 MusicSlice v30 的能量条做法）。单独一节，见 [固定入口·看广告复活](references/fixed-entries.md#看广告复活单独一节可整节删除)；实施和检查按广告板块（见下面「看广告的几项按广告板块做」） |
| 8 | 广告加量（ad-boost） | 默认做，不问 Saul（Saul 2026-10-31）：按本包的 [ad-boost](../ad-boost/SKILL.md) 诊断这款有几个看广告的地方，按推荐加看广告的板块（转盘、礼包、签到等）：广告量少加 3 个、一般加 2 个、多加 1 个。原首页按钮不动，新入口只放空位，画风跟原游戏。做法见下面「默认按 ad-boost 加广告板块」 |

## 看广告：固定几项按广告板块做，第 8 项默认加 ad-boost 板块

**看广告的几项按广告板块做（Saul 2026-10-31）**：英化自己要做的广告的事，自动按本包的[广告板块 remake-ads](../remake-ads/SKILL.md)做，数额按[货币板块 remake-economy](../remake-economy/SKILL.md)，不用 Saul 点名：

- 第 6 项结算 Watch Ad x2：x2 是结算页上最大的按钮，Claim 是它正下方一行可点的小字，样子和位置按[结算页设计](../remake-ads/SKILL.md#结算页设计用户-2026-10-27)表里「看广告 ×2 按钮」「直接领取」两行（Saul 2026-10-31）；看完到账、取消/失败/超时停在结算页且 Claim 仍可点、只发一次，按[共用的广告设计](../remake-ads/SKILL.md#共用的广告设计)的结算一行；数额按[经济规则·货币和结算×2](../remake-economy/references/economy-rules.md#二货币和结算2)（基础已发只补差额；没有货币的游戏翻倍本局捡到的道具）。
- 第 7 项看广告复活：按[复活审查](../remake-ads/references/rewarded-revive-and-help-layout.md)的实施和检查做（英化一律加，不用再审要不要加；页尾的小型教程英化不做）；复活页 → 结算页的顺序按[一局结束：每屏一个视频按钮](../remake-ads/references/end-flow-one-video.md)。
- 原游戏自带签到、转盘、礼包领奖窗时的看广告双倍勾选框：按广告板块共用表那一行和验收清单；数额按[经济规则·第四节](../remake-economy/references/economy-rules.md#四七日签到的数值用户-2026-10-27)末尾（有数量的项 ×2，皮肤不翻倍）。
- 原游戏已有的看广告入口改接平台包、广告计时、`qa/ad-regression.json`：按[广告机制](../remake-ads/references/ad-mechanism.md)和[超时规则与广告回归](../remake-ads/references/ad-timeout-and-regression.md)。

其他页面和按钮仍按本页和[固定入口](references/fixed-entries.md)（原游戏的保留，结算页上原有的按钮不能比 x2 大）。其他看广告入口不另外按广告板块加，由第 8 项 ad-boost 默认按诊断推荐加（见下面「默认按 ad-boost 加广告板块」），广告行为照广告板块。

**默认按 ad-boost 加广告板块，不问 Saul（Saul 2026-10-31：英化 Skill 融合广告 Skill，默认执行，不需要询问）**：每款英化游戏在第 2 阶段都跑本包带的[广告加量 Skill ad-boost](../ad-boost/SKILL.md)，不用等 Saul 说「广告太少」。本机 `~/.kiro/crew/skills/ad-boost`、`~/.codex/skills/ad-boost` 或 `~/.claude/skills/ad-boost` 有比本包新的版本（`CHANGELOG.md` 第一个版本号更大）时，用新的那份。
- 做法：照 ad-boost 流程 ⓪（这台电脑第一次用先跑 `scripts/doctor.py`）和 ①（`scripts/diagnose_ads.py` 加 `--mode localize`）。**跳过 ② 和 ③：不出选择题、不问 Saul**，直接按诊断的推荐顺序加：广告量「缺必备」或「少」加前 3 个（带 ★ 的），「一般」加前 2 个，「多」加第 1 个。再照 ④ 一个一个装：零件（装完跑 `assemble.py --verify`）、面板、音效、按原游戏画风生成美术、接线。复活和结算 x2 照第 6、7 项做。**时间（10.2.7）**：第一个链接前只跑 ⓪ ①、定下加哪几个；④ 的安装在第 4 阶段 Saul 试玩第一轮时做，第二轮链接带上（见第 2 阶段「第一轮美工」）。
- 哪些不加：诊断「不推荐」的不加；道具补给、皮肤看广告、体力 +3、商店看广告免费领、任务/成就领奖 x2 只在原游戏本来就有这个系统时才加（诊断已经按这个排）；奖励关会动原关卡，不加。
- 授权：英化本来不加新系统，**这几个看广告板块是 Saul 2026-10-31 定的默认例外**，不用再问。Saul 试玩后说不要哪个，就把那个板块拆掉（入口、面板、广告位）。
- 首页：**原首页按钮一个都不动**（不挪、不缩放、不重排），新入口只放空位，不压原按钮和 Logo。**没有空位时不问**，换推荐顺序里下一个不用首页入口的板块（局内漂浮礼物、道具补给、开局增益这类）。接线前后各截一张同一手机尺寸的首页（`docs/adboost/home_before.png`、`home_after.png`），第 5 阶段对比。
- 画风和数值：新板块的面板、按钮和图标跟原游戏画风走，排在主要页面的图后面生成（整台电脑同时最多 2 个生图任务，ad-boost 的 `gen_images.py` 管）。数值只用 ad-boost 各板块 README 第 5 节的已定数值（数额按货币板块），原游戏已有的数值不改；板块数值没有默认时不问，换下一个推荐板块。
- 检查放哪：ad-boost ④ 第 6 步的验收（各板块 README 第 8 节、真实点击、广告回归）放到第 5 阶段一起做。试玩链接照本页第 3 阶段起，ad-boost ⑤ 的试玩宿主只在没有 web-mobile 版时用；出包照本页第 5 阶段（`--board localize`）。
- ad-boost 里写英化要等 Saul 在选择题里选、没有空位时问 Saul、交付记录写「在选择题里的选择」的地方，英化游戏以本页为准。
- 交付记录写一行：「XX、YY 板块按英化默认做法加入（Saul 2026-10-31：英化默认执行广告 Skill，不用询问）。」

## 阶段

**先给英文试玩链接，Saul 试玩找出的问题都改完才做全量检查（Saul 2026-10-31）**：顺序是 ① 盘点＋中文原版链接 → ② 英化、第一轮美工（按美工 Skill 照原画风重新生成所有按钮和文字；第一个链接只等主要页面）和第 8 项 ad-boost 的诊断 → ③ 英文试玩链接＋人工检测清单 → ④ 试玩改进：Saul 找画面和游玩的问题、提玩法改进，AI 改完再给他试，直到他说没问题；同时把其余页面的新图和第 8 项的板块做完，下一轮链接带上 → ⑤ 全量检查和出包。画面和游玩的问题交给 Saul 试玩来找：第 ③、④ 阶段 AI 只确认能进首页、能玩一局，不跑检查。电脑上试玩看不出来的（广告的触发和点击、TikTok 兼容、只有手机上才出的问题、以往积累的已知问题）由 AI 在第 ⑤ 阶段查。检查一条都不减、出包门禁一条都不放松，只是挪到 Saul 试玩以后：截图、`art_check.py`、图片比例、鼠标点按钮和弹窗、扫中文，和广告回归 10 例、运行时套件、`preflight.py`、已知问题检查、写包入口，都在第 ⑤ 阶段做。共享库 `remake-core/references/stage-flow.md`、`check-stages.md` 和 `remake-art/references/art-before-trial.md` 写的旧顺序（美术检查和统一检查在交试玩前 → 用户试玩确认 → 出包），英化以本页为准（v7.9 两包一起改）。还有两处两包共用的文件写着交试玩前要做完的检查，英化不照做，挪到第 ⑤ 阶段（v7.9 两包一起改）：`cocos-game-check/SKILL.md` 三道关表「美术关」一行的「美术做完、交用户试玩之前」；`cocos-game-check/startup/references/cocos-loading-screen.md` 的「交试玩前」。美工板块和共享库里同类的几处（两轮自审、加载失败/重试状态、首页增长小样本、试玩清单模板那句）已经在原地写了英化例外（10.2.8）。2026-10-30 的香肠太难了、Runaway Rush 本来可以早 3.5～5 小时给链接，时间大多花在照这些做的检查上（`！Skill更新/提速调查_20261031/`）。

1. **盘点**：**开工先给 Saul 中文原版的手机试玩链接，不等回复，接着往下做**（Saul 2026-10-31）。在中文原工程的一份副本上导出 Web（复制到工程外再导出，原工程一个文件都不动；用原游戏对应版本的 Creator 命令行：先跑 `check_machine.py --project <中文原工程>` 查电脑，再用 `find_creator.py --project <副本>` 找本机的编辑器、拿构建命令（见上面「换电脑也能用」和 [Cocos Creator 版本和已知问题](references/local-creator-versions.md)：没装那个版本先用同一小版本里最近的；2.4.3 要先放进本包的构建扩展再加 `--use-gl=desktop`；3.x 导出缺入口页时用 `fix_web_entry_3x.py` 补），其他写法见[真实 Cocos 运行](../remake-core/references/cocos-runtime.md)：2.4 是 `--path <副本> --build "platform=web-mobile"`，3.x 是 `--project <副本> --build "platform=web-mobile"`；macOS 命令行卡在导入资源时加 `--no-sandbox --disable-gpu-sandbox --disable-gpu`；原工程里已经有没改过的 `build/web-mobile` 也可以直接用），把导出的 `web-mobile` 整个复制到游戏文件夹的 `本地试玩_中文原版（不用上传）/`，再在后台起链接：`python3 <skills>/cocos-game-to-english/scripts/serve_preview.py --directory "<游戏文件夹>/本地试玩_中文原版（不用上传）" --snapshot --open --idle-minutes 0 --name "<游戏> 中文原版"`。原版不用 `--keep`：原版没有美术回执，广告也还没接平台包，看广告冒烟对它没有意义。自己先打开链接，确认能进首页、能开始玩一局，再把链接发给 Saul（怎么自己看画面见「换电脑也能用」）。导不出 Web 时（引擎版本不对、构建报错、只有小游戏包没有源码），把原因写给 Saul，同样接着做。这份导出后面截中英对照图（`docs/baseline/`）也用。然后跑 `python3 <skills>/remake-core/scripts/tiktok_finalize.py init --project <中文原工程> --board localize`（写新游戏标记 `.tiktok-kit/policy.json`），再跑 `tiktok_finalize.py inventory --project <中文原工程>`，它把原版里的广告、加桌面/回访、触摸、启动、存档、分享/跳转/统计、登录代码逐项列到 `docs/english/platform-inventory.json`，第 2 阶段按它逐项改。和 `audit_new_english_images.py --make-list` 放在同一步做。然后列出全部中文（文字和图片字）、首页现有按钮、设置项、结算页、分享/更多游戏/排行榜入口、已知的操作问题。遗留名单上的旧英化游戏（射击高手、音乐消消乐等）继续做新版本时不跑 `init`，按旧游戏出包（拿不准就先跑 `tiktok_finalize.py decide --project <工程>` 看判定）；要改用标准件才跑 `tiktok_finalize.py adopt --project <工程>`。
2. **修改**：按上表 1–8 做。
   - **第一轮美工：按美工 Skill 照原画风重新生成按钮和文字（Saul 2026-10-31）**：第一轮就做，不等点名。范围：所有按钮（带字的和不带字的图标按钮都算，Saul 2026-10-31：第一轮所有按钮都重新生成）、标题和所有图片字（中文改英文）；等级、关卡号、分数、货币（图片字的词＋0-9 位图数字＋货币图标）；新加的按钮（主页回访、加桌面、Watch Ad x2、复活、ad-boost 板块的按钮）和 Claim 小字。**分两批做（10.2.7，Saul 2026-10-31 同意）**：第一个链接只等主要页面：首页、设置、暂停、复活、结算这几页的所有按钮、标题和图片字，加上局内的等级、关卡号、分数、货币数字，以及主页回访、加桌面、Watch Ad x2、复活、Claim。其余页面（关卡选择、商店、皮肤、原游戏的签到/转盘/礼包、教程等）的按钮和图片字，以及第 8 项 ad-boost 板块的图，排在后面，第 4 阶段 Saul 试玩第一轮时接着生成，第二轮链接带上。一款要生成的图常有 100～150 张，全做完再给链接要 2～4 小时；主要页面一般 20～30 张。界面上的文字（Label、代码里的字）第一轮全部改成英文，只有图片里的中文分两批换。做法按[美工 Skill](../remake-art/SKILL.md)：用生图工具（image_gen）把字和底图整张生成，原图放进参考图照着画，尺寸、描边、颜色、位置跟原图一致；代码和字体画的按钮、数字不算（Saul 2026-10-30）；每出一张图跑 `art_records.py generated` 记下来。句子（说明、教学、提示）照第 1 项用真正的英文字体，不生成图片。先做 2～3 个有代表性的（一个带字按钮、一个标题、一组数字）放进游戏看一眼合成效果，没问题再批量做，有共性问题先改共用的图再接着做。画风照原游戏，不换风格；Saul 要求换画风或重新设计时看下面「美工」一节。
   - **平台能力用平台包**：激励视频用平台包的 `RewardedService.js`，加桌面、主页回访用 `TikTokMissionService.js`（`remake-core/assets/platform-kit/`），不另写一份桥接。它们已经把 UI 回调包在 try/catch 里，提示抛错也不会把请求锁死（MusicSlice v29b 手写的 bridge 提示一抛错，看广告、加桌面、回访全部卡在 Checking）。触摸修正、存档层、启动件、适配层、App ID、图片格式和压缩由出包入口自动装上并核对，不要手写；手写的同类文件会被换掉（旧游戏除外）。新英化游戏一律装存档层 `storage-guard.js`（原版多键存储也走它）；旧英化游戏默认不装，只在 `adopt` 以后装（Q6）。原版的广告管理器改成调 `RewardedService`、原版里直接 `createRewardedVideoAd` 或直接调加桌面/回访接口的代码删掉：新游戏漏改出不了包（`A1_rewarded_outside_kit`、`G1k_growth_outside_kit`）。原版（2.4）自带和平台包模块同名的脚本（例如自己的 `TikTokMissionService.js`），`source` 段会把它移到 `.tiktok-kit/removed/`。`PlatformConfig.js` 要填本游戏的 `gameId` 和 `normalLevelCoins`，没填新游戏出不了包（`K_platform_config`）。
   - **原版的 `.webp` 图**：新英化游戏由 `source` 段换成 PNG/JPG；数据或脚本里写死的 `.webp`（例如 `"imageExt": ".webp"`）按文件和行号被拒（`IMG0_source_images`），要改成 `.png`/`.jpg`。原版是 Cocos 3.x 的没有 WebP 例外（`K_webp_exception_3x`），只能靠 PNG/JPG 和 `max_side` 缩到 30 MB 以内。
   - **新做的英文图**：按显示尺寸 2 倍导出再压缩。新图（哈希不在英化前的图片清单里）单张超过 800 KB，出包会被拒；宽/高超过显示尺寸 2.5 倍的会被列出来，要改小（`remake-core/scripts/audit_new_english_images.py`；开工时用 `--make-list <中文原工程>` 存英化前清单到 `docs/english/pre-english-images.json`，出包时缺这份清单也会被拒）。
   - **写 `qa/ad-regression.json`（第 5 阶段写，不挡英文试玩链接）**：出包前的 10 个广告回归用例要它。`request` 走游戏自己真实的看广告方法，`grant` 挂在游戏真实的发奖函数上，`ready` 写首页已就绪的条件。示例：[examples/MusicSlice_ad-regression.json](examples/MusicSlice_ad-regression.json)（多渠道 AdsManager：`config.videoType=0` 后调 `config.AdsManager.ShowVideo()`，发奖统一走 `config.getReward`，示例把它换成计数）。同一个文件也给出包时必跑的运行时回归用（`cocos-game-check/package-check/references/runtime-regression.md`）：必须有 `home`（首页可用时返回 true），建议写 `enter_level`；缺 `home` 出包会被拒。
   - **广告规则去哪看**：按上面「看广告的几项按广告板块做」：广告计时和广告回归看 [超时规则与广告回归](../remake-ads/references/ad-timeout-and-regression.md)，复活页和结算 x2 两屏看 [一局结束：每屏一个视频按钮](../remake-ads/references/end-flow-one-video.md)，领奖窗看广告双倍勾选框看 [广告板块共用表](../remake-ads/SKILL.md#共用的广告设计)，数额看 [经济规则](../remake-economy/references/economy-rules.md)；和 [TikTok 固定适配·已定口径](../cocos-game-check/references/tiktok-fixed-adaptation.md) 有出入时以已定口径为准。
   - **图片复核记录 `docs/english/image-review.json`（第 5 阶段写，不挡英文试玩链接）**：上传包里每张不同的图（按 SHA-256）一条：谁看的、有没有中文、换成了什么；图集按切片看（`"slices_reviewed": true`）。缺记录、还是 pending、写着有中文却还是同一张图，出包会被拒（`remake-core/scripts/audit_image_review_record.py`）。可以用 grok-image-review 转录图上的字，结论由主 Agent 定。
3. **英文试玩链接＋人工检测清单（Saul 2026-10-31）**：第 2 阶段做完就导出 Web、给链接。每次导出后先跑 `python3 <skills>/cocos-game-to-english/scripts/check_export_images.py --project <工程> --export <这轮的 Web 导出>`（几秒，只看导出里是不是工程里现在的图；报旧图就是导出没成功，删掉导出目录重新构建，到 0 张旧图再往下走，见[常见坑](references/english-ui-rebuild.md)第 3 条；3.x 导出里没有 `index.html` 时先跑 `fix_web_entry_3x.py --export <这轮的 Web 导出> --project <工程>`）。给链接前只确认三件：能进首页；能开始玩一局；浏览器控制台没有报错卡死。别的画面和游玩检查都不做，交给 Saul 试玩来找。起链接：`python3 <skills>/cocos-game-to-english/scripts/serve_preview.py --directory <这轮的 Web 导出> --snapshot --open --idle-minutes 0 --ad-simulator --name "<游戏> 英文 第1轮"`（转到同包 `remake-core/scripts/serve_preview.py`。不加 `--keep`：`--keep` 会先跑看广告冒烟，没过就不给链接，看广告留到第 5 阶段查。`--ad-simulator` 让电脑上点看广告会弹出模拟广告窗，见[用户可操作广告模拟](../remake-ads/references/manual-ad-simulation.md)；用法见[固定手机尺寸试玩](../remake-core/references/user-phone-preview.md)）。自己先打开链接，确认进得了首页再发（怎么自己看画面见「换电脑也能用」）。
   回复里先用一句话说：这款原来有几个看广告的地方，第 8 项默认加哪几个板块（Saul 2026-10-31 定的默认做法，不用他选），这几个板块第二轮链接带上，不要哪个直接说。再用一句话写明这轮还是原图的页面（按这款写，例如「关卡选择、商店两页的按钮还是原图，第二轮换」），这几页的按钮这轮不用看。
   回复里直接打出**人工检测清单**：写在回复正文里，一条一行，不写成文件、不发文件路径。按这款游戏实际的页面、按钮和模式写，下面是要包含的内容，不照抄：
   - 画面：每一页（首页、设置、关卡选择、商店/皮肤、暂停、结算、复活……按这款写）还有没有中文；字有没有超框、重叠、被挡；按钮和文字是不是原游戏的样子；图有没有压扁、拉长、发糊；每个弹窗的关闭按钮看得见、点了能回去。
   - 新加的东西：首页的主页回访、加桌面两个按钮，点了提示 “Available in TikTok”；设置里音效、音乐两个音量分开调；结算页 Watch Ad x2 最大，下面一行小字 Claim，还有 Retry；失败时先出复活页；第 8 项加的板块（这款加了哪几个就写哪几个，例如首页转盘、七天签到）点开能用，样子跟原游戏一样（第一轮链接里还没有这些板块，这一条从第二轮起列）。
   - 游玩：从第 1 关玩到第 N 关（按这款写）；每个模式都能暂停、继续、重来、回首页；过关、失败、复活、领奖后金币和数字对不对；退出再进，进度、金币、设置还在；操作点得准不准，手感怎么样。
   - 玩法改进：哪里太难、太无聊、想改的，直接说。
   - 不用你查：广告能不能真的播、播完发不发奖；TikTok 上的兼容问题（加载、触摸、存档、加桌面、回访）；只有手机上才会出的问题。这些等你说试玩没问题以后，我做全量检查。
   - 怎么告诉我：说哪一页、哪个按钮、什么样就行，能截图更好；一次说多条，我一起改。
4. **试玩改进（Saul 找问题、提改进，AI 改）**：Saul 试玩时 AI 不跑检查，等他的问题。等的时候接着做第一个链接没等的部分（10.2.7）：其余页面的按钮和图片字，以及第 8 项 ad-boost 板块（零件、面板、音效、美术、接线）。他发来问题时先改他说的；这时已经做好的图和板块一起放进这一轮，没做完的放下一轮，不为了等图拖住他的修改。第 5 阶段之前，至少要有一轮链接带齐所有页面的新图和第 8 项的板块；Saul 在那之前就说没问题，就把剩下的做完、起新一轮链接，跟他说「剩下的 XX 页和 YY 板块换好了，看一眼没问题就说一声，我开始全量检查」。他说的每一条（画面和游玩的 bug，以及他点名的玩法、手感、难度、数值改动）一次全部改完、只构建一次；只看改过的地方，截图确认改对了，再起这一轮的新链接：先停掉上一轮的试玩服务，再用同样的命令起，`--name` 写第几轮（`--snapshot` 起的链接不会跟着重新导出变，不能只叫他刷新）。回复里写改了哪几条，再列一遍清单里和这几处有关的几条请他复查。玩法改动只改 Saul 点名的；要加新系统的，照上面「创新玩法」用现成板块。这样来回，直到 Saul 说试玩没问题（「没问题了」「可以了」「出包」这类话）。等他回复时可以先写第 5 阶段要用的 `qa/ad-regression.json`，这只是准备，不跑检查。
5. **全量检查和出包（Saul 说试玩没问题以后）**：Saul 说试玩没问题，就是同意做全量检查和出包，不再问一次。检查一条不减：
   - 这一阶段要开浏览器的命令，前面都加 `python3 <skills>/cocos-game-to-english/scripts/browser_env.py --`（哪些命令见「换电脑也能用」；有 Ego 的电脑照样用 Ego，没有的用 Chrome/Edge）。
   - 先补齐记录：`qa/ad-regression.json` 和 `docs/english/image-review.json`（写法见第 2 阶段）。
   - 画面和点击（原来给链接前做的，挪到这里）：每个页面和弹窗在两种手机尺寸（iPhone 15、iPhone SE）各截一张图，扫有没有残留中文；`art_check.py` 和图片比例（画出来的宽高比和图片本身差不超过 10%）；用鼠标把首页和各页面的按钮点一遍，弹窗能开能关。这里只修硬问题（残留中文、压扁、超框、点不到、数字不是图片字、显示版本号或 Credits）；Saul 试玩时看过、没提意见的画风和配色不重做。改了他看得到的画面，交付时说一句改了哪里。
   - 电脑上看不出来的：用[统一检查](../cocos-game-check/SKILL.md)，类型选“英化”。先跑一次 `python3 <skills>/remake-core/scripts/tiktok_finalize.py source --project <工程> --board localize`（英化工程的「平台包」一行查的是源码段记录是否新鲜，不查 `build-templates/bytedance/`），再跑 `check_known_issues.py`、`preflight.py`、`logic_check.py`（以往积累的已知问题在这里查）；广告、触摸、启动加载、存档、加桌面/回访按 [TikTok 固定适配](../cocos-game-check/references/tiktok-fixed-adaptation.md) 查。
   - 广告加量（第 8 项 ad-boost 加的板块）：照 ad-boost 各板块 `modules/<板块>/README.md` 第 8 节验收；对比接线前后的两张首页，原按钮一个没动；每个新的看广告按钮真实点击测看完、取消、失败、超时、连点；`qa/ad-regression.json` 照 ad-boost 的例子写（签到、转盘结果、礼包领奖窗这种带勾选框的写 `double_claim`）。
   - 出包：改过源码就再跑一次 `source` 再构建，再用写包入口出包（`make_tiktok_zip.py` 和 `build_checked_zip.py` 都要给 `--project`；游戏自己的打包步骤在写包入口之前做完；广告回归 10 例和运行时套件由写包入口跑），按统一检查里的出包与最终包检查。v7.6 写包入口出的收据在 v7.7 不再是官方入口，交付前用 v7.7 写包入口重新出。交付时的试玩链接用 `--snapshot --keep --project <工程>` 起（这时跑看广告冒烟）。交付回复贴写包报告里的标准件小表，并写“标准件待真机复测”。

## 并行分工（10.2.7，Saul 2026-10-31 同意）

2026-10-30 那批英化游戏都是主线程加 3 个子进程：给链接前的步数里有 21%～26% 花在线程之间传话，几个线程都在构建游戏（构建命令出现 31～40 次），Cube Digits 两次导出里还是旧图，一个子进程空等了约 27 分钟。所以：

- 子进程最多 3 个，按文件分，互不改别人的文件：
  - **美术**：所有要生成的图（按钮、标题、图片字、位图数字、ad-boost 板块的图）。只有它跑生图，整台电脑同时最多 2 个生图任务。
  - **代码**：固定入口第 2～7 项、平台包接入、第 8 项 ad-boost 的零件、面板和接线。
  - **文字**：代码里的字符串、Label、英文文案和用词表。
- **只有主线程**构建、导出、跑 `check_export_images.py`、起试玩链接、合并、跟 Saul 说话。子进程只交文件，不构建、不起试玩服务。
- 子进程做完报一次（改了哪些文件、还差什么），不轮询、不等别的子进程。每一轮把改动攒齐了，主线程只构建一次。
- 第 5 阶段的广告回归和运行时套件只由主线程跑。
- 活不多时不开子进程，主线程自己做更快。
- 每个子进程读哪些文件见上面「读哪些文件」；主线程派活时把要用的一两条规则贴进去，子进程不整页读 TikTok 固定适配。

## 美工：第一轮按美工 Skill 照原画风重做按钮和文字

**第一轮就用美工 Skill（Saul 2026-10-31）**：英化第一轮按[美工 Skill](../remake-art/SKILL.md)照原游戏画风重新生成所有按钮和文字（范围和做法见第 2 阶段「第一轮美工」），不用等点名；页面排版、背景和角色这些原游戏画得好的图和原画风不动。别的美术改动（重新设计、换画风、改排版、“这页太丑改一下”）仍只在 Saul 点名时做。等级、关卡号、分数、货币美化，以及不显示版本号和 Credits，英化必做（Saul 2026-10-30，见 [Saul 的美术禁区与必做项](../remake-art/references/saul-art-rules.md)）。

**Saul 要求“重新设计”英化游戏时，画风也照原游戏**（Saul 2026-10-31，香肠太难了 Redesign v2：他说“结合广告skill和美工skill重新设计游戏”，结果原版亮橙色、薄荷绿的圆角按钮和木色金边的六边形图标钮全被换成同一种深红方块；Saul：“要按照原游戏的风格去设计美工”）：原图能用就用，要新生成就把原图放进参考图照着画；按钮底色不用深色（深红、砖红、深棕、藏青、深灰、黑这类），金币、爱心、礼盒这些物品图标后面不另加底板；原游戏本来带底座、奶油色边或高光的照原游戏。只有他明说换画风（例如“按重塑画风重做”）才换。用 ad-boost 加的新板块也一样，面板和图标跟原游戏走。

**重做美术先出小样（Saul 2026-10-31）**：Saul 要求英化游戏重做美术或重新设计时，先出小样，不直接做整套：出 2～3 套，每套 1 张首页加 2 个按钮（主按钮、看广告按钮），其中一套是「保持原画风，只改英文和新入口」；30 分钟内放进试玩链接或发图给 Saul 挑，他选了再做整套，都不满意就再出几套。等他选的时候接着做不碰美术的部分（广告入口、代码），不跑检查。小样和 Saul 选的那套记在 `docs/samples/samples.json`。
