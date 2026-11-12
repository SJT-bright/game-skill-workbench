---
name: remake-art
description: "美工（英化第一轮由英化入口调用，照原画风重新生成按钮和文字；新增功能界面在设计时自动调用，英化首次主页默认重排，其他既有页面的额外改造按任务范围做；触发词：用美工skill、重做美术、美术skill、这页太丑、重新设计界面）。重做或局部修改Cocos游戏美术、按钮、图标和界面布局。英化里的中文图片字和带字按钮照原画风重新生成，属于英化入口第1项和第2阶段「第一轮美工」（Saul 2026-10-31）。"
---

**六标准广告节点与美工制作已接入（用户2026-11-11）**。首次完整制作与明确的六类迁移，结束、主页、永久皮肤、体力、局内道具、周期试用六类全部必需；额外奖励循环不能替代任何一类。按[六标准广告制作联动](../remake-core/references/ad-standard-six.md)在制作时调用同包ad-boost与remake-art。旧“0～2个才推荐/无系统不新增/英化默认不加这些系统”不再限制这六类所需依赖。已交付游戏的无关局部维护保留原授权范围和有效记录，不自动改原件。


**当前检查执行规则（用户 2026-11-08）**：先读[一次通过、按改动复验](../remake-core/references/incremental-checks.md)。图片、文字/字幕、音效、玩法、关卡、平台检查均按命名节点留存真实记录；已通过且依赖未变的项禁止重复执行，代码或配置变化也不触发全量。浏览器和写包读取同一计划；旧文中的“每次必跑/全量检查”改按完整覆盖核对解释。最终 ZIP 的本次体积与分包核对按用户单独要求保留。

**已交付返工的视觉交付规则（用户 2026-11-08）**：已交付源码/测试包后，用户要求“改完这处美工给测试包”即授权本次指定视觉修改免 AI 美工复验；按[返工交付与人工快查](../remake-core/references/returned-art-delivery.md)记录独立授权并继续完成同版 ZIP＋试玩入口。旧文“每轮必须先过美工/回执过期必须复验”不适用于此授权范围；不伪造技术通过，不扩到功能。人工快查放原有 Native 试玩与反馈时，不新增出包等待。


> **英化包说明（Saul 2026-10-28，10-31 补）**：下述首轮与后续复查要求不覆盖本页开头的“已交付返工视觉授权”；英化第一轮由英化入口调用本 Skill，照原游戏画风重新生成按钮和文字（范围见英化入口第 2 阶段「第一轮美工」，Saul 2026-10-31）；新增功能界面走下文的制作规则。英化没有启动包，**保持原游戏画风**；首次英化主页默认按[原画风主页排版](references/english-home-layout.md)重新设计；其他未受影响页面和已交付后的局部返工不追溯重做；下文“画风跟随启动包”只适用于重塑。英化每轮按第 3 阶段在真实页面核对当前制作范围，使用同版有效证据。适用的图集、布局和点击缺陷修复后定点复查。动效、明显闪屏和整体观感随已有试玩由人工检查，按[人工试玩清单](../remake-core/references/manual-visual-review.md)交接。
>
> **新功能的界面从设计开始归本 Skill（用户 2026-11-10）**。页面、弹窗、子面板和入口控件在选型、排版和出图前走[新增界面制作](references/new-feature-ui.md)。功能板块负责业务行为，本 Skill 负责玩家实际看到的画面。英化以原游戏同类界面为参考，包含首次英化内新增和后续补做；现有模板只用于接线或结构，成品先按本 Skill 定稿。

> **例外（Saul 2026-10-30）**：[Saul 的美术禁区与必做项](references/saul-art-rules.md)第一节里，"等级、关卡号、分数、货币用图片字和位图数字"和"不显示版本号、Credits"两条英化也必做，不用等用户点名，按原游戏画风做。原版是一整行普通字（例如 "LEVEL 1 • +10 PEARLS"）的，英化时换成图片字的词、生成的位图数字和货币图标。`font_number`、`font_value_label`、`dev_info_text` 在英化游戏同样拦。


**英化主页默认重新设计排版（用户 2026-11-10）**。首次主页先按[原画风主页排版](references/english-home-layout.md)确定主次、分区、英文空间与手机安全区，再制作接图；不以保留旧按钮坐标为默认。保留玩法、奖励、存档和真实入口。局部维护按本轮范围，修改 Skill 本身不自动改已有游戏。

# Cocos美术重做与局部修正（美术与UI板块）

## 浏览器测试路线（用户 2026-11-06，取代旧回退规则）

英化人工操作用 **Computer Use + Edge**。自动检查仍在 **Ego Lite** 独立 TaskSpace 执行原有脚本并复用有效证据。英化的 Google Chrome 只在美工试玩和最终测试包交接时打开。 其他流程的自动检查按原 Ego 路线执行。缺少对应能力时继续离线工作，记录实际未测项。详见 `<SKILLS_DIR>/remake-core/references/browser-testing-policy.md`。


修订：`2026-10-27.modules-v6`。**管什么**：画风禁止项（只写负向约束；画风本身跟启动包走，用户 2026-10-27/28）、页面布局与分区、按钮、图片字与首页大图、图标、动效、首页与设置页、加载页画面。**不管什么**：文字内容是否地道（文案（重塑包 remake-copy 板块，英化包不含））、数值（[经济](../remake-economy/SKILL.md)）、关卡数据（关卡（重塑包 remake-levels 板块，英化包不含））。

**必须遵循（Saul 2026-10-29）**：TikTok 固定适配（触摸、启动加载、激励广告、存档读值、适配层、图片、加桌面/回访、登录/App ID、胶囊/首页底排/不要 Credits）和跨游戏通用流程一律按 [TikTok 固定适配](../cocos-game-check/references/tiktok-fixed-adaptation.md) 做：美术只出 PNG/JPG，右上角留给胶囊，首页底排只放两个平台入口，不做 Credits；新游戏只用平台包标准件，不手写；旧游戏只给警告，由各自会话处理。

**画风跟随启动包（用户 2026-10-28）**：本板块不规定任何正向画风（不要求明亮、Q版、糖果色、光泽、胶囊按钮、固定颜色含义、亮度下限或华丽感），只写[禁止项清单](references/style-limits.md#〇画风禁止项清单只查负向用户-2026-10-28)。有启动包时，`ART_DIRECTION.md`（以及 UI_PAGES、EXPERIENCE 的页面与素材需求）就是本作的美术规格：题材、主角与角色造型、场景、配色、页面清单、按钮与图标需求、生图提示词都按它做，不另起一套画风，也不按 AI 自己的偏好改。只有它和下面的禁止项冲突时才调整，并在项目记录里写明哪一条、怎么改；启动包没写到的部分按同一风格补齐。没有启动包时才按游戏题材自定风格。精简启动包（`supply: light`）的 `ART_DIRECTION.md` 带色板 HEX、逐页背景、UI kit、字体和生图提示词，照它执行，见[精简启动包的详细画风](references/ui-style-and-samples.md#精简启动包的详细画风)。

先确定本轮是完整重做还是已批准画面的局部修改。保留原始素材和用户存档；玩法和经济保持当前授权。分享、联网排行榜（局内本地名次可以留，Saul 2026-10-31）和广告跳关按[前置规则](../remake-core/references/no-social-features.md)移除，其他业务不因美术任务擅自删除或新增。

**图片格式与出包处理（v7.7）**：
- 只交 PNG（有透明）或 JPG（不透明），不交 WebP 美术。新游戏工程里的 `.webp` 出包前由 `tiktok_finalize.py source` 自动换成 PNG/JPG（uuid 不变），构建产物里还有 `.webp` 就拒绝出包（`K_S_webp`）。图换成 PNG/JPG 后，数据和脚本里写死的 `.webp`（例如美术清单里的 `"imageExt": ".webp"`）会让图加载失败，源码段按文件和行号拒绝（`IMG0_source_images`），要自己改成 `.png`/`.jpg`。只有缩完图仍超 30 MB 才能走 WebP 例外，见 [TikTok 固定适配·第 6 条](../cocos-game-check/references/tiktok-fixed-adaptation.md#6-图片只出-pngjpg按显示尺寸缩压缩webp-9-款大图和首屏过多-24-款)。
- 素材只用 CC0（不需要署名，也就不需要 Credits）。这一条只是文档规则，没有门禁会查，选素材时自己核对授权并记在 `docs/` 里。
- 不用按显示尺寸手动缩图：出包时宽和高都超过显示尺寸 2 倍的图会自动缩到 2 倍，但只限场景或预制体里静态 Sprite 用的、单帧、没有裁边、不在 `resources/` 或 bundle 里的图。**代码按路径加载的图、带裁边（trim）的图不会自动缩**，要在 `<工程>/.tiktok-kit/image-overrides.json` 里逐张写 `max_side`（例如 `{"images": {"assets/resources/art/*.png": {"max_side": 900}}}`，键可以用通配；位图字的字形图不要缩）。
- 出包时所有 PNG 压成 256 色（pngquant）。渐变背景出现色带时，按张在同一个 `image-overrides.json` 里改：`{"quantize": false}` 不压缩，或 `{"format": "jpg", "jpg_quality": 95}`（带透明的图不能转 JPG）。前后对比用 `python3 <skills>/remake-core/scripts/finalize_images_compare.py --project <工程> [--native <构建目录>]`，它出成对图和 `index.html`，把可能有色带的图标成 `check` 排在最前面，并给出建议的 `suggested-overrides.json`。

| 工作 | 按需读取 |
|---|---|
| 主题、样板与同套资产 | [UI规范与样板](references/ui-style-and-samples.md)、[画风只守禁止项](references/style-limits.md) |
| 首页大图（不写游戏名）、图片字、按钮连字、位图数字 | [页面不单调与文字](references/page-richness.md)、[字底与字形](references/text-backplate-review.md) |
| 双倍按钮、首页分区和动态标题/主角 | [按钮与首页](references/mobile-button-size-and-home-layout.md)；结算页 ×2 大按钮＋下方一行 Claim 文字见[结算页设计](../remake-ads/SKILL.md#结算页设计用户-2026-10-27) |
| 首页按玩法设计、会动的背景、可互动的首页物件 | [首页按玩法设计](references/home-by-gameplay.md)（用户 2026-10-28） |
| 集合预览、首尾压框、装备对应 | [集合预览](references/collection-preview-review.md) |
| 拼装后的实际画面和输入 | [美术自审](references/artwork-and-feedback.md)、[局部UI契约](references/local-ui-contract.md) |
| 新增/修改实际拦截输入的弹窗、加载层行为，连续操作后无法关闭 | [实例归属](../remake-core/references/modal-input-ownership.md)：沿用现有管理器，机制代表件定点验证；不扩成美术全验 |
| 用户确认后的检查范围 | [美术前移与锁定](references/art-before-trial.md)、[执行去重](../cocos-game-check/test/references/review-execution-plan.md) |
| 新游戏开工、共享修改或反复返工 | [少返工的制作与采集](references/art-iteration-workflow.md)（用途盘点、首件、故障分流和下一步计划） |

已有核准整词字图且可取得同款无字底的固定英文按钮，优先按[固定词按钮生成](references/fixed-caption-button.md)把底图、图标和整词按实尺寸一次合成一张 PNG。其余已知文字/按钮与其底图由内置image_gen整体生成，页面标题用图片字，游戏名不放进游戏（原位置放主角或图案图），动态数字使用生成的位图字；不以程序字或空底叠字冒充。字图等比缩放，实际组合图核字芯/描边、装饰压字、关闭与父面板、最长数字串和字距；普通矩形边界通过不能代替实际画面。

**资源 HUD 先判断是否需要底板（用户 2026-11-11）**：货币、钻石、体力、分数等只显示图标和数值时，默认用透明图标＋同套透明数字/词图；原画面已经清楚就不新增方块、色条或胶囊。生图与接入都按[资源显示的底板决策](references/text-backplate-review.md#资源显示先判定是否需要底板)执行。生成的 PNG、圆角、描边或投影不能豁免纯色填充；“同套画风、数值成组、可点击”也不等于必须有底板。本条优先于旧文中要求动态数字套胶囊的泛化表述。

**数值栏必须整组制作（Saul 2026-11-04）**：任何页面的 LEVEL / Lv. 固定标签都做图片字，与数值同组的 GOAL、SCORE 及 /、:、%、+、−、× 等实际符号一起按同套画风制作。生成前列齐词、数字与符号，按[数值栏整组制作](references/production-prevention.md#数值栏的词数字与符号整组制作)接入第一组；不能只换数字，把普通标签或符号留在旁边。

**制作和检测联动（11.17.5）**：开工按[少返工的制作与采集](references/art-iteration-workflow.md)查共享消费者、定跨用途预算；固定按钮与透明切片用[生产联动入口](references/production-check-link.md)登记原料、配方和实例。首件用 `--production-only --first-piece-case ID` 检查选中整页，其余实例明确待验。每批完成或失败后用原采集身份和下一步计划区分制作、接入、构建与采集故障；同因修正合批，避免重复整轮。完整检查前先核输入，像素计算只复用输入与规则均未变化的项，首件不代替页面或试玩验收。

**独立图标与符号先锁显示槽**：本次新增或替换的视频图标、勾、乘号、关闭符号和图文按钮，生图前确定用途与设计尺寸，PNG 像素不能决定节点显示大小；首件按真实 canvas 换算，在 [visual-slots 的 display_budget](references/local-ui-contract.md#高清图标接入时锁定独立显示预算) 登记各受影响视口的独立期望宽高。图标按等比适配后的实际 Art 底板定位，配合 inside 和图文间隔，不能只核较大的触摸 root。底板文字已烘焙时，生成规格必须预留图标净空；缺留白就调整制作规格或使用完整图文按钮，不能靠默认边距强行叠加。ad-boost 面板同时遵循随包的显示槽规则，并在批量制作前跑其调用集回归。

**所有本轮美工制作先做源头预防（Saul 2026-11-03）**：先读[美工制作预防](references/production-prevention.md)，把美术总表 T01–T14 中与本轮资产有关的要求落成具体提示词、尺寸/状态方案与接图要求；广告板块新增资产也执行。不能只在制作前泛读禁止项、等检查报错再返工。英化保持原画风，按下面的英文空间规则细化。

**英化生图前与接图时先预防（Saul 2026-11-03）**：按[生成前先定尺寸与分区](../cocos-game-to-english/references/english-ui-rebuild.md#生成前先定尺寸与分区制作时消除问题saul-2026-11-03)执行：先按英文定稿规划可读内区和各元素空间，把目标比例、完整文字、留白写进提示词；接图保持比例、处理重复旧层，代表样先在真实页面确认再批量做。每批发现共性问题即修生成模板或共享组件，完整美工检查继续在每轮试玩前完成。英化第一轮换哪些图，照 `docs/english/art-replace-round1.json` 的 `replace`、`manual_review`、`regenerate` 三组做（[英化换图第 0 步](../cocos-game-to-english/references/english-ui-rebuild.md#英化只换带中文字的图画风跟原游戏一致)）。

**接图用 `bind_art.py`、一张图一个主体（R4C）**：接图一律用 `remake-art/scripts/bind_art.py`（3.x 嵌套预制体实例也支持），不手改节点宽高，接完跑 `--check`（英化游戏只改这一轮换过图的节点，原游戏的图照原样）；新美术一张图只放一个主体，条状图只用 `cut_sheet_frame.py` / `ad-boost/scripts/art/cut_strip.py` 切。见[出图和接图的两条固定做法](references/production-prevention.md#出图和接图的两条固定做法r4c普查-squashed_image-32-款sprite_crop_fragment-17-款)。

**先量后做（Saul 2026-11-04，蛋壳特工队六张图）**：按[排版预算与页面全覆盖](references/text-fit-and-coverage.md)做。开工就用 `audit_page_coverage.py` 从工程预制体拿到全部有字或按钮的页面和弹窗，当作本轮的工作和采集清单；带字的按钮、标题、底板、数量槽，先把 Label 换成定稿英文、两种尺寸 `dump_ui`，跑 `audit_text_fit.py --plan`，按「底板至少要」的宽度生图，数字按 `docs/art/longest-text.json` 的最长值留槽；每接好一页马上再跑一次 `audit_text_fit.py`，零发现再做下一页。

**每出一张图就记一次（v7.8 H10，Saul 2026-10-30：代码画的按钮和数字不算图片字）**：生成的图裁好、压缩好、放进工程 `assets/` 之后，跑 `python3 <skills>/remake-core/scripts/art_records.py generated --project <工程> --prompt "<提示词>" --tool "<生图工具>" [--raw <原图>] <最终文件>...`，记进 `docs/art/generated.json`；同一张图再裁切、压缩跑 `art_records.py derive --project <工程> <图>`，`tiktok_finalize.py source` 自己的转换会自动补记。英化游戏开工时用 `art_records.py base --project <工程> --from <中文原版工程或源码 ZIP>` 记下原版，`art_check.py` 才分得出哪些是新做的英文图；没有生成记录的新图只提示、不拦，而且只算会进包的图（resources 和资源包文件夹里的、被场景或预制体等引用的、代码里写了路径的），工程里没用到的只提示「建议删掉」。英化不查「底子原图原声」（原图原声本来就保留）。

**灰盒参考、样板先行、3D 换皮只管重塑（v7.8 H12）**：英化换图要跟原画风一致，可以直接拿原图做参考；重塑包里"生图参考只传灰盒（`remake-art/scripts/make_greybox_reference.py`）、提示词默认不写 highlight 和 outline、先出 1 张首页样板、3D 底子整棵关掉重铺"这几条英化不用。

首次重做按实际页面、弹窗和条件状态分项核对。用户确认后沿用实际结论，后续只处理改动涉及的画面。完整美术回执已撤销；美术工具记录实际检查项，写包和试玩入口使用包与版本身份。`art_check.py` 每次完整运行都会写轻量记录 `.tiktok-kit/art-check-record.json`（不含图片指纹）：英化首轮正式试玩前要有一次完整运行，之后改图只复查受影响的行。见[试玩后锁定](references/art-before-trial.md#用户试玩确认之后)。

共同症状按[当前合同](../remake-core/references/current-contracts.md)进入所属参考。交用户[同版固定手机预览](../remake-core/references/user-phone-preview.md)，结束自建QA页与无用服务。本任务不自动生成游戏包；已报告缺图/遮挡等问题记入项目，并定点修复复验。

## 更多正文（本板块）

[原画风与反馈](references/artwork-and-feedback.md)、[生图后全量巡检](references/full-visual-review.md)、[动态画面](references/dynamic-visual-review.md)、[题材与可读性](references/theme-readability.md)、[图集切片](references/atlas-slice-integrity.md)、[角色姿态交接](references/actor-pose-handoffs.md)、[首页与设置页](references/common-game-components.md)。

## 广告 Skill 加的板块也照本页做（Saul 2026-11-01）

Saul 2026-11-01：「我要使用广告skill，你做一个转盘也要结合美工skill，一起」。ad-boost `~/.kiro/crew/skills/ad-boost/`（Codex：`~/.codex/skills/ad-boost/`；Claude Code：`~/.claude/skills/ad-boost/`） 给游戏加的转盘、礼包、签到、离线收益、皮肤试用这类板块，面板、按钮、图标、位图数字**都按本页做**，不另起一套画风；ad-boost 和本页说法不一样时以本页为准。
- 重塑：色板和画风照这款的 `ART_DIRECTION.md`（强调色只给 PLAY、NEXT、Watch Ad x2 和转盘指针）；提示词照提示词模板（重塑包 remake-art 的 image-prompts-and-3d-reskin.md 第二节，英化包不含），默认不写 highlight、outline、glossy 这些词；[Saul 的美术禁区与必做项](references/saul-art-rules.md)照做（按钮底色不深、物品图标不垫底板、不加装饰）。ad-boost 的生图流水线（`scripts/art/`）由它的 `scripts/art/skill_link.py` 读这几条，并把每张图用 `art_records.py generated` 记进 `docs/art/generated.json`；整页检查用本板块的 `art_check.py`，过[验收清单](#验收清单)。
- 英化：照原游戏画风（[T11](references/saul-art-rules.md#t11-风格统一与换皮完整度)），原图能沿用就沿用。
- 每个板块做哪几张图、多大，看 ad-boost 的 `modules/<板块>/art.json`；分工全文在 ad-boost 的 `references/联动.md`「美术」。没装 ad-boost 时这段不适用。

## 联动表：改了美术与UI，要回查

| 改了 | 回查 |
|---|---|
| 页面布局、按钮位置 | 按钮真实点击与触控区域（测试与修复）；教程手指坐标（新手引导）；广告按钮层级（广告） |
| 图片字、按钮字 | 英文是否准确（文案） |
| 皮肤页、商店页 | 价格/加成显示与表一致（皮肤、经济） |
| 地图、资源栏 | 总关数和数字实时更新（关卡） |

**反过来：别的板块新加了页面或弹窗，美术归本板块**（Saul 2026-11-01：「广告skill做新的转盘的时候，你就要去做这个转盘的美工」）。广告加量 ad-boost 的转盘、礼包、签到、离线收益、体力、道具补给、提示、看广告领币、任务 x2、商店免费领、奖励关等板块，经济的礼盒和看广告领币，皮肤页和试用窗，关卡地图和奖励关节点，教程手指和气泡，都按下表做，见[别的板块交来的页面](references/page-richness.md#别的板块交来的页面美术归美工saul-2026-11-01两个板块)：

| 别的板块加了 | 本板块要做 |
|---|---|
| 新页面、新弹窗、新入口按钮 | 先按[新增界面制作](references/new-feature-ui.md)定原画风或启动包画风、文案、尺寸和状态；接入后仅补采新增及受影响状态，用原工具核对并沿用有效结果 |
| ad-boost 的板块（图在 `assets/resources/adboost/<板块>/`） | ad-boost 的流水线按本板块的规则生图（它的 `scripts/art/skill_link.py` 是唯一入口）；放进工程后跑 `skill_link.py record` 写生成记录；面板和结果窗两种尺寸都要有 dump，否则 `art_check.py` 报「缺采集: ad-boost 板块…」，不算美术通过 |
| 两边规则说法不一样 | 以本板块为准（ad-boost `references/联动.md` 也这样写） |

凡新增或改动图标＋文字按钮、海报说明条、长正文和奖励计数，按[图文内区检查](references/local-ui-contract.md)登记受影响状态。试玩前普通 art_check 读取 docs/art/visual-slots.json；逐项核对实际截图，原料切对、语义绑定和运行布局分别验。

固定英文按钮、图标加短词和重复奖励项，先按[按钮文字的实际内框](references/production-prevention.md#按钮文字的实际内框)完成一件实尺寸样板。模板复制前核对首尾字和图标间距，上排卡底露字另列一项。

## 验收清单

- [ ] 画风照启动包（英化照原游戏，Saul 要求重新设计时也一样）、不混用几套；没有[禁止项](references/style-limits.md#〇画风禁止项清单只查负向用户-2026-10-28)：深色/过密/过细的字、大面积深色/纯黑纯色底、大白板、单色图标、刺眼整屏高亮、无层次平涂、字压复杂底图、遮挡穿模、模糊；玩区 ≥80%
- [ ] 功能按上/左/右/下分区，次要功能用小图标
- [ ] `art_check.py` 按适用技术行运行通过，保留实际采集的截图和节点数据
- [ ] [Saul 的美术禁区与必做项](references/saul-art-rules.md)第一节逐项做了；`font_value_label`、`flat_value_plate`、`dev_info_text`、`small_glyph_core`、`small_value_font`（只拦重塑，英化只提示）、`digit_glyph_padding`（数字看得见的字芯够大、数字图紧裁）没有报出
- [ ] `art_check.py` 的「按钮底色不深、物品图标不另垫底板」一行通过（`dark_button`、`icon_plate`、`dark_button_state` 没有报出，列为接近深色的交人工在试玩中看）；英化（包括要求重新设计的）按钮、图标、金币画法和原游戏是一套（Saul 2026-10-31，[美术总表](references/saul-art-rules.md) T02、T09、T11）
- [ ] 别的板块加的页面和弹窗（ad-boost 的转盘、礼包、签到……，礼盒、皮肤页、试用窗、地图）都在 `docs/art/screens.json` 里、两种尺寸都有 dump，`art_check.py` 没有报「缺采集: ad-boost 板块…」；ad-boost 的图都有生成记录（`skill_link.py record`，Saul 2026-11-01）
- [ ] `art_check.py` 的「有字或按钮的页面、弹窗都在两种尺寸采集过」一行通过（页面表从工程预制体来；打不开的写进 `not_reachable` 并写原因）；「没在采集里出现过的英文」看过，没打开的状态补采（Saul 2026-11-04）
- [ ] `art_check.py` 的「字按真字宽放得下」一行通过：`text_outside_plate`、`text_on_icon`、`text_on_text`、`text_off_screen`、`text_off_band`、`words_covered`、`text_over_words`、`longest_does_not_fit`、`unsettled_dump` 都没有报出；`text-plan.md` 里余量为负的都按「底板至少要」改过（Saul 2026-11-04，[排版预算与页面全覆盖](references/text-fit-and-coverage.md)）
- [ ] 交接[人工试玩清单](../remake-core/references/manual-visual-review.md)适用项，在正常试玩中观察点按钮、开关弹窗、调音量、局内操作时的画面
- [ ] 改动页面的按钮真实点击有效
- [ ] 只交 PNG/JPG、素材都是 CC0；代码加载或带裁边的大图已在 `image-overrides.json` 写 `max_side`；有色带的图已按张处理

英文 Web 美工有多轮改图时，第一次就按[按状态补拍](references/capture-rounds.md)建立页面、条件状态与手机视口清单。下一轮先用工具判定哪些原图仍有依据、哪些必须重拍，再接入同一个完整美工检查。旧图缺采集当时的导出记录时列为待拍。
