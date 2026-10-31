# TikTok 固定适配（必须遵循）

修订：`2026-10-30.tiktok-fixed.3`（v7.8：美术回执进写包入口、源码段静态查遮罩/比例/看不见的碰撞体、底子原图原声和生图记录、声音来源和成品响度、布局状态和按钮普查等运行时套件出包必跑、子资源 uuid 认旧游戏；每条写在下面对应的节里，标 v7.8。上一版 `tiktok-fixed.2`（v7.7）：出包时自动装上标准件，再由门禁确认装上了，见下面「出包时怎么装」；再上一版 `tiktok-fixed.1` 是 Saul 2026-10-29 10:20 定的：这份总结很重要，所有 Skill 的最新版都要放进去，以后每款游戏都必须照做）。英化包和重塑包共用本页（`cocos-game-check` 两包字节相同）；本页和其他板块说法冲突时，以本页为准。

**来源**：58 款游戏（40 款 10-27～10-29 修过的新游戏 + 18 款真机完结的老游戏）的修复记录，整理出 526 条“问题—根因—修法—证据”。全部记录、分类表和统计在（只读）：
`/Users/sijunting/Downloads/！自制游戏/！交付游戏/1香吉士-射击高手2048/检测修复_20261029/跨游戏调查_20261029/`（`全部记录.jsonl` 每行一条带证据路径，`NOTES.md` 逐类笔记，`matrix.json` / `matrix.md` 统计）。总表原文：`/Users/sijunting/Downloads/！自制游戏/启动包工坊/！Skill更新/发给Skill制作_跨游戏TikTok固定适配总表_复制这段话.txt`。逐款经过不在本页重复，要查就去记录文件夹。

**为什么要写死**：出现最多的几类（扫码转圈、激励广告、包体、触摸、加桌面回访、存档读值）每款游戏都一样、和玩法无关，以前却每款各自重新写一遍修法。

## 怎么读每一条

- **规则**：一两句，做到什么算对。
- **标准件**：直接用的平台包文件或脚本（路径相对 Skill 包根目录；平台包 = `remake-core/assets/platform-kit/`，接法见 [平台包接入说明](../../remake-core/assets/platform-kit/README_接入说明.md)）。
- **现在怎么拦**：当前版本（v7.8）里已经能拦的门禁或脚本 id，v7.8 新加的标了「v7.8」。写着“仍是文档规则，计划做成出包硬拦截”的，现在出包不拦，但照样必须做到。
- **验收包**：坏包必须被拦、修好的包必须通过（取自总表第五部分和修改要求总表）。

## 已定口径（不再让模型临场决定）

1. **广告计时 = v7.4 规则**（Saul 10-29 03:18）：请求到 `show()` 成功最多 15 秒，只算前台；`show()` 之后不计时，只在 `onClose(res)` 且 `res.isEnded === true` 时发一次奖；开播 30 秒没有回调出 X，按 X 不发奖；超时、按 X、取消之后才开播或才看完的视频**不补发**；不留收尾锁，下一次广告马上能发。详见 `remake-ads/references/ad-timeout-and-regression.md`（重塑包内）。
2. **英化游戏一律加看广告复活**，没有失败状态的游戏也加（Saul 10-29）。一局结束先出复活页（只有看广告复活 + 免费 NO THANKS），放弃或已用过复活后再进结算页（只有看广告 x2，RESTART/HOME 在下面）；**同一屏只放一个看广告按钮**。
3. **英化分享奖励**：核心玩法里的分享奖励（复活、礼物、双倍）改成激励视频；其他分享入口（成就分享、升级分享、邀请好友等）连同触发它的礼物球、弹窗删干净，不留“本平台不可用”的死按钮。
4. **加桌面、主页回访的一次性奖励**：每项都等于一次首页礼盒的基础奖励 **5B**，换算成这款游戏自己的货币；没有首页礼盒的游戏也按 5B 算（Saul 10-29 09:11）。以前 20～150 各不相同的，下次出包统一改。平台包取值见第一部分第 7 条。
5. **新游戏必须用平台包标准件**，不手写、不“照抄平台包”另存一份；**旧游戏**（在冻结的遗留名单上的）不自动替换，只给警告，由各自的游戏会话处理。哪些算旧游戏见下一节「新游戏和旧游戏」。
6. **交付回复写“标准件待真机复测”**：v7.7 的标准件（平台包 `main.js` v1.6、`storage-guard.js`、`tiktok-touch-3x.js`、`HomeGrowthEntries.js`、3.x 插件版、WebP 探针）都只在 Node 和模拟宿主里测过，没有扫码确认。第一款 v7.7 新游戏扫码通过之前，每个交付回复都写这一句。v7.8 的三个可选件（`parts/CapsuleLayout.js`、`parts/CourseLane.js`、`parts/PhysicsClock.js`）也一样，用了它们的游戏照样写这一句。
7. **美术回执进写包入口，出包不重跑美术检查**（Saul 10-30 同意；10-24「打包时不再全面重测美术」不变）：美术关跑过 `art_check.py`、留下回执，之后图没变就能出包；改过图就要重跑美术检查。见「出包时怎么装」的「美术回执和美术记录」。
8. **代码画的按钮和数字不算图片字**（Saul 10-30）：按钮和数字图片字都要用 GPT 生图，生图要留记录（H10，见「出包时怎么装」）；PIL、字体离线画的 PNG 不能登记成「允许代码画」。
9. **布局状态、按钮普查出包必跑**（Saul 10-30 10:4x）：新游戏拦、名单上的老游戏只警告；3.x 先只拦开局下载（超过 10 MiB 或带声音），其余只警告。
10. **关卡难度和样板**（Saul 10-29、10-30）：新关卡表默认 `wave-tiers.v2`（第 1、2 关教学，第 3 关就是难关），按旧 v1 排好的表不返工（第二部分第 8 节）。完整换皮照搬底子要写 `mode=reskin` 并有 Saul 点头记录；样板先行（首页样图、20 秒试玩、BGM 三选一、3～5 个样关）只管自制新游戏，只提示、不拦。
11. **声音和美术的五件**（Saul 10-30 21:3x）：①启动包自带的声音，接收时按启动包记录把音效库来源写进 `docs/audio/credits.csv`，算从音效库选的；底子原游戏自带的声音重塑不许用。②英化游戏的源码段美术检查（`K_art_aspect`、`K_art_hidden_body`）只警告。③`W_audio_harsh`（可能刺耳）不报 0.3 秒以内的声音。④timeout、time_out、times_up 这类「时间到」的声音算失败音（2 秒以内带淡出，门禁 2.5 秒）。⑤装 v7.8 前已开工的新游戏（新游戏标记日期在 2026-10-31 或以前）可以一次性跑 `art_records.py pre-v78`，把工程里已有、没有生成记录的图登记成「v7.8 前已有」；美术检查每次都列出这些图，和底子相同的图照样拦。

## 出包时怎么装（v7.7 起，`tiktok_finalize`；v7.8 加美术回执、运行时套件必跑、出包后整理）

标准件不再靠模型复制。`remake-core/scripts/tiktok_finalize.py` 在出包时把它们装上，门禁再直接读包里的字节确认装上了。模型只做脚本做不了的两件事：把游戏的发奖函数接到平台包广告服务上，把首页两个入口挂到首页节点上。

**命令**（路径相对 Skill 包根目录）：

1. **起项目 / 英化开工**：`python3 remake-core/scripts/tiktok_finalize.py init --project <工程> --board remake`（英化用 `--board localize`），写新游戏标记 `<工程>/.tiktok-kit/policy.json`。v7.8 起重塑加 `--base <底子工程文件夹或源码 ZIP>`（从零做的写 `--no-base-why "<原因>"`），同时记下底子的图和声音（H8，见下面「美术回执和美术记录」）；两个都没给时 init 照常写标记，只提示补记命令 `art_records.py base --project <工程> --from <底子>`。英化接着跑 `tiktok_finalize.py inventory --project <工程>`，把原版里的广告、加桌面/回访、触摸、启动、存档、分享/跳转/统计、登录代码列到 `docs/english/platform-inventory.json`。
2. **源码段，Creator 构建之前**：`python3 remake-core/scripts/tiktok_finalize.py source --project <工程> --board remake|localize [--app-id <ID>]`。按顺序跑 `images`（WebP 换 PNG/JPG、缩图）、`kit_sources`（平台包模块逐字节对齐）、`physics_clock`（v7.8，P16：用了 2.4 物理、自己没开 enabledAccumulator 的新游戏装平台包 `parts/PhysicsClock.js`，老游戏只警告 `K_W_physics_clock_legacy`，从不拦包）、`build_templates`（只对重塑新游戏：`build-templates/` 只留平台包件；英化工程和旧游戏的构建模板不动，触摸、存档、启动件改在产物段装）、`settings`（写 App ID）、`orientation`（v7.8，B31：`K_portrait_design`）、`art_static`（v7.8，U7 补、H6：`K_art_aspect`、`K_art_hidden_body`，只读；遮罩不量透明度，Saul 10-31）。v7.8 起 `source` 还做三件事：判出「只靠子资源 uuid 对上名单、但工程在启动包里或旁边、或带 `--board remake`」时自动写新游戏标记（B27，见「新游戏和旧游戏」）；跑步骤前先核美术回执，图全对得上时把回执跟到自己转换、缩放后的图上；把生成记录、底子记录跟到改了格式或名字的文件上（`art_records`，出错不会让源码段失败）。改动前的原图在 `<工程>/.tiktok-kit/originals/`，被换掉的文件在 `<工程>/.tiktok-kit/removed/`，记录写 `<工程>/.tiktok-kit/finalize-source.json`（含 `assets/`、`build-templates/`、`settings/` 的内容哈希，和本次用的 `--keep-webp-exception` 原因 `options`）。跑完再构建；构建后又改了这三个目录，要重跑 `source` 再构建，否则写包入口拒绝（K5）。旧游戏源码段只写 App ID，也必须跑。
   - 游戏脚本和平台包模块同名（Cocos 2.4 的模块名全局唯一，MabelsMeadow r8 自带 `assets/scripts/platform/TikTokMissionService.js`、`MissionFlow.js`，Creator 因此报 Filename conflict）：新游戏由 `kit_sources` 把游戏那份连 `.meta` 移到 `<工程>/.tiktok-kit/removed/<原路径>`，警告 `K_W_kit_module_duplicate`，游戏里 `require` 这个名字时加载的就是平台包模块；旧游戏只警告。还同名就是 `K_kit_module_duplicate`（新游戏拦，旧游戏警告）。
3. **产物段，在写包入口里**：`make_tiktok_zip.py` 和 `build_checked_zip.py` 先查源码段记录（K5，被拒时构建目录一个字节都不改），再在任何门禁之前调用 `finalize_native`（取代 v7.5 的 `adapter_fix.apply`），原地改 `--native` 构建目录，顺序 `adapter → startup → touch → storage → login → appid → png → structure`。移走的文件放 `<构建目录的上一级>/.tiktok-kit-removed/<构建目录名>/`，不进 ZIP。两个写包入口都必须给 `--project`：`build_checked_zip.py` 不给时命令行报错（退出码 2）；`make_tiktok_zip.py` 不给时被它原有的参数检查拒绝（退出码 2，要求同时给 `--review`、`--project`、`--web`、`--build-tag`），都在 finalize 之前。写包报告的 `finalize.table_markdown` 是一张中文小表（标准件、结果、改动文件数、警告数），收据的 `finalize.table` 是同一张表，交付回复直接贴这张表；结果写 `已装（插加载行）` 表示文件本来就是平台包的、本次只插了加载行。收据升到 schema 2：没有 `finalize`、`finalize` 有拦截、用过 `--policy`、`finalize` 改过的文件和 ZIP 对不上，都算“非官方入口”，`prepare_delivery.py` 拒收。**v7.6 写的收据在 v7.7 一律不再是官方入口，交付前要用 v7.7 写包入口重新出包。** v7.8 起写包入口在查 K5 的同时核对美术回执（`ART_receipt`、`ART_base_audio`），并跑运行时套件，见下面两段；发布后整理交付文件夹，见「出包后」。
   - 游戏自己的打包步骤（例如 MabelsMeadow 的 `scripts/prepare-native-package.py` 把 `config/*.json` 放到包根）不是标准件，仍归这款游戏负责：在写包入口之前对构建目录做完，finalize 不替它做。
4. **单独查看**：`tiktok_finalize.py decide --project <工程>`（或 `--native` / `--zip`）写出判成新游戏还是旧游戏、为什么；`tiktok_finalize.py native --native <构建目录> --project <工程> --board …` 单独跑产物段。`--policy new|legacy` 只给测试和校准用，写包入口不接受（只读的 `check_package.py` 有这个参数，也只给测试）；用它做出的源码段记录会被 K5 拒绝。
5. 同一工程连跑两次，第二次 0 改动（pngquant 结果有缓存 `<工程>/.tiktok-kit/png-cache.json`，pngquant 版本或参数变了缓存作废）。缺 `pngquant` 就拒绝，不跳过。

**美术回执和美术记录（v7.8，总表 U7 补、H8、H10、H11、H6）**：

- **回执**：`remake-core/scripts/art_check.py` 跑完分析写 `<工程>/.tiktok-kit/art-receipt.json`（结论 `pass` / `fail` / `not_covered_3x`、art-check.json 的哈希、`assets/` 下全部图片指纹，含图集 `.plist` 和 `.fbx/.gltf/.glb`）。两个写包入口和 `serve_preview.py --keep --project <工程>` 只核对这份回执、不重跑美术检查（`art_receipt.check`）。`ART_receipt`：重塑新游戏没有回执、回执不是通过、或图和回执对不上，就不出 ZIP、不起试玩，提示「美术改过（或没跑美术检查），重跑 art_check」并列出改了、新增、删了的图；旧游戏、英化游戏只警告（警告进 finalize 记录和 ZIP 收据）。`ART_receipt_3x_not_covered`：3.x 工程 art_check 采集不到，回执写「3.x 未覆盖」，放行并在写包结果和 finalize 表里标出，交付说明照实写，不能写成通过；但 3.x 的 H8、H10 两行不通过时回执写 `fail`。`serve_preview.py --keep` 不给 `--project` 退出码 2、回执不通过退出码 1，都不起服务。工程 `assets/` 下一张图都没有时记 `no_images` 放行。
- **底子原图原声不留（H8）**：底子的图、声音、模型内嵌贴图的哈希记在 `docs/art/base-assets.json`（`init --base` 或 `art_records.py base --project <工程> --from <底子>`；从零做的 `--none --why`）。工程 `assets/` 下会进包的文件和底子逐字节相同、又没写进 `docs/art/base-keep.json`（每条要写 why，`art_records.py keep`）的，美术检查这一行不通过，回执写 fail。「会进包」= 在 `resources` 或资源包文件夹里、被场景/预制体/图集/字体/脚本直接或间接引用（含 subMetas 的 uuid）、或者认不出（没有 .meta、代码写了它的 uuid 或路径）；工程里没用到的只列「不会进包（不拦，建议删掉）」。要按成品包核对就加 `--build <包或构建文件夹>`，按 uuid 认文件（不要拿成品包按字节比，构建会重新压缩图）。4×4 以内的图、平台包和官方加载页的图不算；没有底子记录的重塑游戏不通过。英化（board localize 或 art-style original）不查。回执只记图，所以写包入口另拿当前声音和底子记录比一次：`ART_base_audio`，新重塑游戏拒，老游戏警告，英化不查。
- **新做的图都有生成记录（H10）**：每出一张图就记进 `docs/art/generated.json`（sha256、file、prompt、tool、date；`art_records.py generated`，生图原图另存的加 `--raw`；以后再改同一张跑 `art_records.py derive`；素材库 CC0 图用 `--source` 加 `--license`）。会进包、不是底子图、不在记录里的新图报「不是生成的图」；生成后又改过、没补记的单独报，并给出 derive 命令。确实要代码画的（纯色九宫格底板这类）写进 `docs/art/script-drawn-allow.json` 并写 why（`art_records.py allow`）；PIL、字体画的按钮和数字不能登记成 allow（已定口径第 8 条）。新重塑游戏不通过；英化只提示，而且要先 `art_records.py base --from <中文原版>` 记下原版才分得出新图，没记时写「不适用」。`tiktok_finalize.py source` 自己转格式、缩图时自动补记，不用手工再记。这项只认记录、分不出像素是谁画的，故意把 PIL 图登记成「生成的」拦不住，看图清单仍要看按钮是不是一整张生成图。
- **v7.8 前已有的图（Saul 10-30 21:3x）**：新游戏标记日期在 2026-10-31 或以前的游戏，可以一次性跑 `art_records.py pre-v78 --project <工程> --why "装 v7.8 时工程里已有的图"`，把工程里已有、没有生成记录的图登记成「v7.8 前已有」（`generated.json` 里 `pre_v78: true`）。只能跑一次；美术检查每次都列出这些图的数量；和底子相同的图照样拦（H8 不受影响）。
- **美术检查新加的其他行**（都在美术关跑，需处理就写 fail 回执）：
  - 首页主角露全、HUD 数字够大够清楚、复活/结算页没有黑边（H11、H6）：`home_hero_hidden`（主角可见包围盒在屏幕内不到 90%）、`home_hero_small`（占屏不到 8%）、`home_hero_unknown`（认不出主角；确实没有主角或认错时在 `docs/art/hero.json` 写 `{"home": ["节点路径或帧名"]}`）；`hud_digit_small`（HUD 数字按屏幕上的字号算不到屏高 3%）、`hud_digit_contrast`（和背景对比度不到 3:1）；同一页出现 3 次以上的局内棋子上的数字不算 HUD；`black_edge_band`（复活、结算页最上或最下 4% 近黑）。
  - 「位置穿模」一行多三类：`overlap_button_picture`、`busy_text_background`、`stacked_text_layers`，见第二部分第 3 节。
  - 图集切片（`audit_atlas_slices.py`）：图片字、局内棋子、投射物、障碍的切片也查，报 `connected_body_cut_by_rect`（主体被切断）、`edge_fragment`（边上挂着别家的细残片）；tile、地面、九宫格、平铺、四边不透明的整块和写了 `"slice_role": "tileset"` 的跳过。
  - 动态闪屏：美术关要录四段（首页点按钮、开关弹窗、调音量、局内消除，见 `chrome-mobile-testing/SKILL.md`「美术关必录的四段」），一段都没有这一行不通过；Ego 录不到一帧闪烁时写「闪烁未测」。
  - 命令行发现本机 Python 没有 numpy 或 Pillow 时，自动改用有这两样的 Python 重跑（`/usr/bin/python3` 等），不装任何东西。
- **源码段静态拦（`art_static`，v7.8）**：`K_art_aspect`：SIMPLE + CUSTOM 的 Sprite 节点比例和图片比例差超过 10%；九宫格/平铺、ProgressBar 的 bar、沿拉伸方向同色的图不算。`K_art_hidden_body`：带启用的、不是 sensor 的 2D 碰撞体，自己和子孙的 Sprite 全被关或没有图（剪刀达人 v17/v18 板子看不见却能剪）；完全没有 Sprite 的隐形墙、Graphics 画的地面不报。新的重塑游戏拦（进源码记录，写包入口靠 K5 拒）；旧游戏和英化游戏只警告 `K_W_art_aspect` / `K_W_art_hidden_body`（英化只警告是 Saul 10-30 21:3x 定的）。运行时被代码藏起来或换图的底子节点，写进 `docs/art/static-exempt.json` 并写 why，每条列在警告 `K_W_art_static_exempt` 里。只靠代码设的帧、预制体实例覆盖、动画看不到，仍由美术关的运行时 dump 查。弹窗遮罩不量透明度（Saul 10-31 撤掉 150/255 和 0.55 倍两种门槛）：明暗跟游戏风格走，整体不要太亮；不要暗沉、没有设计图案的背景（一张黑遮罩加一个空底板、纯色块都不行）；按钮和图标要么是新生成的图，要么沿用原游戏的图案。只能人看，不做数值门禁。

**运行时套件出包必跑（v7.8，总表 B30、P2 补、P16、E1 补）**：`check_package.runtime_gate()` 按 `required_suites` 跑全部适用的套件（`cocos-game-check/package-check/scripts/runtime_regression/suites/`，说明见 `package-check/references/runtime-regression.md`）。写包时新老游戏的判定和共用门禁用同一个（finalize 记录里的 policy，不再按包的字节判：FoxDenDash、全民飞车 v3.1 回执写 new、按字节判 legacy，现在按 new），board 一起传下去。

| 套件 | 查什么 | 什么时候跑 | 新游戏 | 老游戏 |
|---|---|---|---|---|
| `startup` / `startup3x`、`network`（v7.5 起，不变） | 见第一部分第 2 节、第二部分第 5 节 | 每个 TikTok 包 | 同 v7.7.5 | 同 v7.7.5 |
| `dead_shell`（v7.8，`VIS_DEAD_SHELL`） | 首页、真点 PLAY 后的局内、`enter_level` 后的关内，还显示着的退役互推、排行、更多游戏槽位，见第二部分第 5 节 | 每个 2.x 包（3.x 没做） | 拦 | 警告 |
| `layout_state`（v7.8，D） | 开局下载实测（第一部分第 2 节）、胶囊和首页规则（第一部分第 9 节）、被 3D 盖住、伸出屏幕、伸进底部横条 | 每个 TikTok 包 | 拦 | 警告；3.x 只拦开局下载 |
| `button_sweep`（v7.8，E） | 首页每个按钮和它打开的一层弹窗里的按钮真点一次，见第二部分第 3 节 | 每个 TikTok 包 | 拦 | 警告；3.x 警告 |
| `popin`（v7.8，P2 补） | 滚动障碍在可见范围里凭空出现、消失、瞬移，见第二部分第 8 节 | 每个 2.4 包；适配文件要有 `popin` 块或 `{"n/a": "原因"}` | 拦（缺 `popin` 也拒） | 警告、缺字段不跑 |
| `frame_rate`（v7.8，P16） | 60 帧和 120 帧跑同一段操作，位置差超过 5% 不过，见第二部分第 8 节 | 每个 2.4 包；适配文件要有 `frame_rate` 块或 `{"n/a": "原因"}` | 拦（缺 `frame_rate` 也拒） | 警告、缺字段不跑 |
| `ad_entries`（v7.8，B） | 适配文件列出的每个看广告入口（含复活）真点后 2 秒内有反应，见第一部分第 3 节 | 适配文件有 `ad_entries` 时 | 拦 | 警告 |
| `trial_link`（v7.8，F） | 本地试玩链接点一次看广告，模拟广告窗在最上层、点看完后游戏有变化，见第一部分第 3 节 | 有试玩链接时（`serve_preview.py --keep` 给链接前、`runtime_regression.py trial --url`） | 不过不给链接 | 同左 |

- 3.x 上 `popin`、`frame_rate` 只警告「未覆盖」，`dead_shell` 不跑（只做了 2.x）；没跑的套件和原因写在摘要 `not_run` 里。
- 两个写包入口都跑这些套件和 10 个广告用例，适配文件都来自 `--ad-regression` 或 `$TIKTOK_AD_REGRESSION_ADAPTER`：`build_checked_zip.py`（和 `prepare_delivery.py`）经 `check_package.check()`；`make_tiktok_zip.py`（重塑游戏的正式写包入口，v7.8 第四轮 W97 接上，以前一个运行时套件都不跑）调 `check_package.writer_regressions()`，跑在刚写好、重读过的 ZIP 的解压副本上（就是要发出去的字节），policy 用 finalize 记录的、board 用 `--board`。新游戏没有适配文件、没有 Ego、环境不完整、任一用例没过都不写 ZIP，一次列出全部原因；名单上的老游戏同样的原因只写进报告 `warnings`（带「[legacy game: warning]」），照样出包。结果在报告的 `rewarded_ad_regression`、`runtime_regression`。这一步排在所有便宜检查之后。
- 开跑前先查环境（A6，见第一部分第 1 节），环境不完整报「环境不完整：……」，退出码 2，不算包不通过。
- 多花的时间（这台机器实测）：`dead_shell` 15～30 秒，`layout_state` 30～104 秒，`button_sweep` 110～500 秒（首页预算 480 秒封顶，W93 加局内后另有 90 秒上限），`popin` 约 112 秒，`frame_rate` 30～60 秒，写了 n/a 的 0 秒；每款出包合计多约 5～15 分钟。

**出包后（v7.8，总表 B32）**：
- 两个写包入口发布 ZIP 和回执后，把同一文件夹里同款游戏的旧包（appid 相同、游戏自己的文件至少 30% 相同）连同回执、报告挪进「旧包/」，写「最新.txt」（上传 TikTok 用哪个包的完整路径、sha256、「源码包、试玩文件夹不能上传」）；源码 ZIP、别的游戏的包、`delivery_receipt_*.json`、说明文件不动；「旧包/」里重名加「 (2)」，不覆盖、不删。`--keep-old-packages` 或 `TIKTOK_KEEP_OLD_PACKAGES=1` 什么都不挪。交付回复照「最新.txt」写「上传 TikTok 用这个」。
- 按新设计作废旧问题：`package_issue_gate.py supersede --id <旧> --by <新> --quote '<Saul 原话>' --date YYYY-MM-DD`，没有原话、日期不对或是将来、新问题没登记都拒；作废后旧问题不再拦包，新问题复验通过前照样拦。v7～v7.7.5 写的复验证明照样认，已关掉的问题不用重测。
- 用的检查工具和安装版、发布记录（PROVENANCE.json）都对不上时，`check_package` 的结果里写「改过的工具」（`tool_identity`，只警告、不拦），并写一份反馈草稿到 `！Skill更新/反馈草稿_改过的工具_<游戏>_<日期>.md`（同一天同样的改动只写一次）。
- 拆包前的旧路径 `cocos-game-check/core/scripts/<脚本>.py`（19 个）是转发桩，转到 `remake-core/scripts/` 的同名脚本，并提示新路径；新写的文档和命令用新路径。

**16 个标准件**（`remake-core/assets/platform-kit/KIT_MANIFEST.json` v2.0 的 `parts` 段 9 个，加它引入的 `parts-3x/KIT_PARTS_3X.json` 7 个；哈希只以清单为准）：

| 件名 | 引擎 / 段 | 文件 | 修什么 | 新游戏 | 旧游戏 |
|---|---|---|---|---|---|
| `touch24` | 2.4 / 产物 | `touch-coordinates.js` | TikTok 触点只给 screenX/screenY，引擎算出 (0,0)，按钮点不动 | 装上；自写的同类件换掉 | 没有任何触摸修正时才补 |
| `startup24` | 2.4 / 产物 | `main.js` v1.6，包根同时放 `webp-decode-probe.js` | 扫码转圈：单文件 10 秒重发、30 秒判失败、后台不计、Retry；重发算进度，有文件还在自己的 30 秒里时 10 秒总看守不出 Retry；同时加载 storage-guard、发一次静默登录（不等结果）、WebP 例外时运行探针 | 换成平台包 `main.js`（只在清单 `engine_versions` 列出的引擎版本上换：2.4.4、2.4.6、2.4.13、2.4.15；其他 2.4.x 保留编辑器 `main.js`，触摸和存档各插一行，警告 `K_W_startup_engine`）。`main.js` 里 require 了探针，所以包根总放 `webp-decode-probe.js`（只放脚本，不放探针图、不插开关行，不走 WebP 例外时它不执行）。自写启动件的加载行能整句拿掉的就拿掉并移走文件；拿不掉的、或包里还有别的文件 require 它的，保留并警告 `K_W_own_startup_kept`（`required_by` 写明是谁） | 不换，警告 `K_W_own_startup` |
| `storage24` | 2.4 / 产物 | `storage-guard.js` | 没存过的键读到 false / ''，数字读回 true | 装上；射击高手 pkg83/84、pkg85 的旧版存档层换成新版 | 不装 |
| `webp_probe24` | 2.4 / 产物 | `webp-decode-probe.js` + `loading/webp-probe.webp` | canvas 导不出 WebP 时引擎误判不支持，报 3121 | 只在 WebP 例外时装探针图 `loading/webp-probe.webp` 和开关行（需要平台包 `main.js`）；脚本本身随 `startup24` 每次都放 | 不装；保留 WebP 的旧游戏仍由 G4 查探针 |
| `rewarded` | 2.4 / 源码 | `assets/tiktok-platform/RewardedService.js` | 广告计时和卡死（v7.4 规则） | 缺了补上，改过的恢复成平台包原文件 | 只报差异 |
| `missions` | 2.4 / 源码 | `MissionFlow.js` + `TikTokMissionService.js` | 加桌面/回访：领奖查询、只发一次、SDK 查找顺序 | 同上 | 只报差异 |
| `home_entries` | 2.4 / 源码 | `HomeGrowthEntries.js` | 首页两个入口：不支持时提示、图片失败时有文字、奖励读 `growthReward()` | 同上（挂到首页节点由模型做） | 只报差异 |
| `savestore` | 2.4 / 源码 | `SaveStore.js` | 整档一个键、写后读回、读档后登录 | 同上 | 只报差异 |
| `platform_config` | 2.4 / 源码 | `PlatformConfig.js` | 每款唯一可改的文件：gameId、appId、广告位、`normalLevelCoins` | 没有才放，改过的值保留 | 只报差异 |
| `touch3x` | 3.x / 产物 | `tiktok-touch-3x.js` | 同 `touch24`，插在 `require('./web-adapter')` 之前 | 装上；自写的同类件换掉 | 没有任何触摸修正时才补 |
| `storage3x` | 3.x / 产物 | `storage-guard.js` | 同 `storage24`，插在 `require('./web-adapter')` 之后（`window.localStorage` 由 web-adapter 创建） | 装上 | 不装 |
| `platformconfig3x`、`rewarded3x`、`missions3x`、`missionflow3x`、`savestore3x` | 3.x / 源码 | `assets/tiktok-platform/*.plugin.js` | 2.4 模块外面包一层插件脚本，游戏里用 `globalThis.TikTokKit.*`；核心逐字节相同（`make_plugin_scripts.py --check`） | 装上，`.meta` 勾导入为插件；`PlatformConfig.plugin.js` 每款只改 BEGIN..END 里的 `gameId`、`appId`、`placementMap`、`normalLevelCoins`，改过的值保留（`growthReward()` 固定 5B，不改） | 只报差异 |

v7.8 另有三个可选件，登记在 `KIT_MANIFEST.json` 的 `files` 段（`reference: true, optional: true`），K1/K2、finalize、`check_kit_project.py` 都不要求它们，没装的工程不会被拒：`parts/CapsuleLayout.js`（胶囊避让，第一部分第 9 节）、`parts/CourseLane.js`（滚动障碍，第二部分第 8 节）、`parts/PhysicsClock.js`（物理按时间走，源码段 `physics_clock` 只给用了 2.4 物理的新游戏装）。清单另带 `KIT_FINGERPRINTS.json`（旧版平台包模块的特征，给 `K6_kit_module_old` 用）。kit 版本号仍是 2.0。

3.x 没有启动件（Q5，没有真机通过的底子）、没有 `HomeGrowthEntries`（3.x 首页入口直接用 `TikTokKit.MissionFlow`）、没有 WebP 探针，也没有 WebP 例外（DECISIONS 13:25：3.x 新游戏只能靠 PNG/JPG 和 `max_side` 缩到 30 MB 以内；带 `--keep-webp-exception` 时源码段、产物段在任何步骤之前拒绝，不改工程和构建文件，写包门禁也拦，`K_webp_exception_3x`；3.x 探针放到 v7.8）。另外两步每款都跑、不是文件：`adapter`（v7.5 的适配层三处，第 5 条）、`appid`（`project.config.json` 写 App ID，第 8 条）；`png`、`structure` 见第 6 条。

**新门禁**（`remake-core/scripts/package_gates/kit_parts.py`，挂在 `package_gates` 里，两个写包入口和只读的 `check_package.py` 都跑；只读包里的字节和清单，不信记录）：

| 门禁 | 查什么 | 新游戏 | 旧游戏 |
|---|---|---|---|
| `K1_kit_bytes` | 适用的产物段标准件文件在包里，哈希等于清单；包里的 `main.js` require 了 `./webp-decode-probe`，`webp-decode-probe.js` 就必须在、而且是平台包文件 | 拦 | 只查 finalize 装上的件；旧版本哈希、缺探针脚本警告 |
| `K2_kit_wiring` | 加载行正好一次、在锚点对的一侧；用平台包 `main.js` 时 `game.js` 真的 require 了 `./main` 一次（Nanas 教训） | 拦 | 只查 finalize 插的行（带 `// tiktok-kit:<件名>:2.0` 注释） |
| `K3_single_layer` | 同一类只有一层：没有第二份触摸修正、第二份存档层 | 拦 | 警告 |
| `K4_finalize_ran` | 只在写包入口：本次产物段记录在、没有拒绝项、它写的文件在包里且字节一致 | 拦 | 拦 |
| `K5_source_finalized` | 只在写包入口：源码段记录在、kit 版本等于当前清单、工程在源码段之后没改过、不是 `--policy` 做的、写包入口的 `--keep-webp-exception` 和源码段记录的 `options` 一字不差（没有 `options` 的旧记录当作没用例外） | 拦 | 拦（旧游戏源码段只写 App ID，也要有记录） |
| `K_webp_exception_3x` | 3.x 工程或构建带 `--keep-webp-exception`（v7.7 没有 3.x WebP 例外） | 拦 | 拦 |
| `K1_plugin3x` | 只查 3.x 新游戏：`src/settings.json` 的 `plugins.jsList` 列出清单里全部 5 个插件脚本，每个文件保留 `// tiktok-kit:plugin3x:<名字>:` 标记和 `---- BEGIN` / `---- END` 两行（Creator 会重新包装插件，所以不比字节） | 拦 | 不查 |
| `K_platform_config` | 包里的平台包 `PlatformConfig`（2.4 模块、3.x `PlatformConfig.plugin.js` 的 BEGIN..END 段；写包入口还查工程 `assets/tiktok-platform/` 里那份）：`gameId` 不能还是 `'change-me'` 或空，`normalLevelCoins` 要大于 0，否则加桌面/回访发 0 而不是 5B | 拦 | 警告 |
| `K2_login` | 2.4 包里有登录调用：平台包 `main.js` 的登录行，或游戏自己的登录调用（例如 `SaveStore.js` 读档后那次） | 拦 | 警告 `K_W_login`（3.x 新游戏也只警告，平台包还没有 3.x 登录件） |
| `K_appid_*` | `project.config.json` 的 appid 是真的 TikTok App ID，和 `PlatformConfig.js` 一致 | 拦 | 拦 |
| `K_S_zero_byte`、`K_S_outside_path` | 0 字节文件、`..` 路径或符号链接 | 拦 | 拦 |
| `K_S_webp` | 构建产物里有 `.webp`（例外且装了标准探针时放行） | 拦 | 警告 |
| `L4_debug_code` | 调试开关、vConsole、诊断节点、模拟广告窗、测试跳关 | 拦 | 警告 |
| `W_duplicate_files` | 1 KB 以上的相同文件，可省多少字节（Q7：只报告，不删） | 警告 | 警告 |
| `K_engine_unknown`（v7.7.4） | 认不出 Cocos 2.4 / 3.x 引擎文件（改了名，或不是 Cocos 小游戏构建），标准件一项都没法查；以前直接跳过、不报 | 拦 | 警告 |
| `GATE_MISSING_<名字>`（v7.7.4，所有门禁） | `package_gates/` 里有门禁文件不在（安装不全），它的检查没跑；以前只记进 missing | 拦 | 拦 |
| `A1_rewarded_outside_kit`（已有，改级别） | 平台包 `RewardedService` 以外调用 `createRewardedVideoAd` | 拦 | 警告 |
| `G1k_growth_outside_kit`（新） | 平台包 `TikTokMissionService` / `MissionFlow` 以外调用 `addShortcut`、`checkShortcut`、`startEntranceMission`、`getShortcutMissionReward`、`getEntranceMissionReward` | 拦 | 警告 |
| `K6_kit_module_old`（v7.8，`package_gates/kit_versions.py`，只查 2.4） | 合并压缩后的脚本包里是旧版平台包模块（构建比 `tiktok_finalize source` 早，或工程里另有旧副本）；认版本用 `platform-kit/KIT_FINGERPRINTS.json`。只差显示文字（MissionFlow 的提示）一律只警告；认不出写 `K6_kit_module_unknown`、特征文件过期写 `K6_fingerprints_stale`，都只警告 | 拦（重新 source、构建即可） | 警告 |

A1 和 G1k 认平台包件时，文件名和 `KIT_MANIFEST.json` 里的指纹都要对上（2.4 模块或 3.x `.plugin.js`），只有平台包的名字、没有平台包代码的不算；只算真正的调用（`.x(`、`.x.call(`、`['x'](`），方法定义和字符串不算。

新警告：`K_W_own_startup_kept`（自写启动件拿不掉，或包里别的文件还 require 它，`evidence.required_by` 写明是谁）、`K_W_kit_module_duplicate`（源码段移走了和平台包模块同名的游戏脚本）。`check_package.py` 只给 ZIP、`prepare_delivery.py` 收包时，都从包里的 uuid 判新旧。

源码段的件（2.4 模块、3.x 插件脚本）不在包里比哈希（Creator 构建可能压缩或改名），由源码段 `kit_sources` 在工程里逐字节核对，再由 K5 证明源码段跑过。运行时探针（触摸探针、`startup` 套件、10 个广告用例）照常必跑，证明“装上了也真的生效”。

## 新游戏和旧游戏

- **规则（Saul Q1，2026-10-29）**：平台包里有一份冻结的遗留名单 `remake-core/assets/platform-kit/LEGACY_GAMES.json`，只有 Skill 发版才能改。**不在名单上的游戏都是新游戏**，包括正在做、还没交付过的游戏。
- **怎么认**：按场景 uuid 认，工程里读 `*.fire.meta` / `*.scene.meta`，只有构建产物时读各 bundle 的 `config.json`。名单只存本游戏独有的 uuid：在两个以上启动包里出现的、两款以上游戏共有的都去掉；只在一个启动包里出现的保留（启动包工坊里放着英化游戏的原版源码，全去掉这些游戏就认不出了），所以用这类启动包起的新项目也带着名单游戏的 uuid。独有场景 uuid 重合 1 个，或独有资源 uuid 重合至少 5 个且占所存的 20% 以上，就是名单上的那款游戏。复制工程出新版本不改 uuid，同一款游戏的新版本还在名单上。读不出 uuid 的按新游戏。v7.7.5 起（总表 B27）：工程文件夹正好是名单记下的那款游戏最后一版源码文件夹（`last_package.path`）时也判旧游戏，只认这个文件夹本身，不认上级、下级或别处的副本（剪刀达人、欢乐刮水果靠这条认出来：名单的 uuid 是从包里读的，包里有图片帧这类子资源，工程顶层 .meta 读不到）。v7.8 起（总表 B27 后半）：前面几步都没对上时，再读工程每个 `.meta` 的 subMetas uuid（精灵帧等，嵌套的也读；源码 ZIP 也读），用同样的阈值对名单。对上以后：工程在启动包里面或旁边（往上 3 层里有一层是启动包：有 `workshop.json` / `starter.json`，或 `START_HERE.md` 和 `GAME_DESIGN.md` / `ECONOMY.json` 放在一起；或下面放着 1～2 个启动包，3 个以上算合集文件夹不算），或调用方带了 `--board remake`，判**新游戏**；其余（`--board localize` 或没给 board）判旧游戏，搬走的剪刀达人 v30 就靠这条认出来。判 new 的结果带 `auto_new`（原因）和 `sub_asset_match`（本来会对上谁）。
- **标记只能往严里改**：`<工程>/.tiktok-kit/policy.json` 有新游戏标记，就按新游戏，名单也盖不住；没有“标记成旧游戏”的写法。用名单上的游戏（例如英化原版、完结游戏）做底子的新游戏会带着底子的 uuid，所以起项目时必须跑 `init`。现在没有门禁检查起项目时跑没跑 `init`：漏跑时不在名单上的游戏照样按新游戏处理，用名单游戏做底子的会被当成旧游戏。v7.8 起 `tiktok_finalize.py source` 判出上面「子资源对上、但有启动包痕迹或带 `--board remake`」时，马上写新游戏标记（`by: source (auto: …)`，源码记录写 `marker_written`），之后不带 board 的工具（写包入口、art_receipt、logic_check、audit_audio_sources）都按新游戏判；所以从启动包开的游戏漏跑 `init`，最晚在第一次 `source` 时也会被标成新游戏。英化游戏不自动写标记。工程搬到别处、又没给 board、也还没跑过 `source` 时，不带 board 的工具会暂时按旧游戏只警告，直到第一次 `source`。`init` 照旧推荐跑。
- **已经开工、用名单游戏做底子的工程**：名单第二版生成时查到 `！自制游戏` 下 12 个正在做、还没交付的工程会被名单认成旧游戏（`LEGACY_GAMES.json` 的 `stats.in_progress_matching_legacy`），另有 21 个启动包和名单游戏同源（`stats.template_packs_matching_legacy`），用它们起的新项目同样全靠 `init`。按 Q1 这些工程是新游戏：下一次出包之前先跑一次 `tiktok_finalize.py init --project <工程> --board remake`（英化用 `localize`），再跑 `source`、构建、写包；不跑就按旧游戏处理。音乐消消乐的工作副本本来就是名单上的那款，不用跑。
- **出过测试包、还在做的新游戏也要跑 `init`**：名单把出过 TikTok 包的文件夹都算了进去，所以已经出过测试包、还没完结的新游戏也会被认成旧游戏。2026-10-29 用 `decide` 查到 4 个：丛林荡藤 VineSwing（认成我是蜘蛛人）、海底泡泡合成 OceanBubbleMerge（认成细菌2048）、HollysHayHop（认成方块冲冲）、MeteorBlaster（名单上它自己那条）。拿不准时先跑 `tiktok_finalize.py decide --project <工程>`（只读，不改文件）：结果是 `legacy`、游戏又还没通过官方测试，就跑 `init`。不在名单上的游戏多跑一次 `init` 也没有坏处。
- **已完结的游戏（Saul 2026-10-29）**：官方测试通过就算完结，之后只再交一次源码。完结游戏不用新版 Skill 重出包、不补测试，也不在它的工程上跑 `tiktok_finalize.py source` / `native`（源码段会改工程文件，交出去的源码就和通过测试的那一版对不上了），直接交通过官方测试那一版的源码。「v7.6 写的收据不再是官方入口、要重新出包」只管还要再出包的游戏。
- **旧游戏改用标准件**：`tiktok_finalize.py adopt --project <工程>` 写新游戏标记，下一次出包起按新游戏处理。
- **名单现状**：`LEGACY_GAMES.json` 是第二版（`"version": 2`，123 款），Saul 2026-10-29 过目后在 v7.7.1 冻结（`"frozen": true`；判定不看这个字段，冻结前后认法一样）。扫了 `！交付游戏`、`！成功完结游戏`、`！自制游戏` 下的游戏文件夹、`~/游戏出海项目制作` 的交付和工作目录、学习库索引；同一款游戏在几个文件夹里的合成一条。漏在名单外的旧游戏会被当成新游戏拦住；只能等下一次 Skill 发版补进名单，会话自己不能加。

## 第一部分：TikTok 固定适配（每个游戏都一样）

### 1. 触摸坐标（19 款：新 15、老 4）
- **规则**：TikTok 触点只给 screenX/screenY，Cocos 2.4 和 3.x 都读 clientX/clientY，会算出 (0,0)。每个 TikTok 包都必须在引擎之前装好坐标修正，并确认**构建产物里真的加载了**（Nanas 复制了模板但 game.js 没加载它），包里只能有一层修正。
- **标准件**：2.4 用平台包 `build-templates/bytedance/touch-coordinates.js`（件名 `touch24`）。3.x 用平台包 `build-templates/bytedance-mini-game/tiktok-touch-3x.js`（件名 `touch3x`，以 Marlows R6 `marlow-touch.js` 为底改成通用件，SDK 查找 TTMinis.game → tt），在 web-adapter 克隆 `tt.onTouch*` 之前装。哈希以 `KIT_MANIFEST.json` 为准。**哈希更正**：平台包件 `1aeb690c…` 就是 StarPop v50 那份（交付包包根和源码 `build-templates/bytedance/` 逐字节相同）；v7.6 总表写的 `0369875d…` 是另一份代码，是躲雨小鸭（RainyDuck）v20 和射击高手（MergeShot）pkg85 用的，清单把它记为自写件（新游戏换掉，旧游戏保留）。两份都没有扫码确认。
- **出包时怎么装**：产物段 `touch` 步。2.4 的产物 `main.js` 是平台包 `main.js` 时由它加载触摸件，不再插行；不是时（引擎版本不在清单 `startup24` 的 `engine_versions` 里、旧游戏）把 `touch-coordinates.js` 放到包根，在 `game.js` 的 `__globalAdapter.adaptEngine()` 之后插一行。3.x 在 `require('./web-adapter')` 之前插一行。新游戏的自写触摸件移走、加载行注释掉；旧游戏有自写的就不动，没有才补。
- **现在怎么拦**：`K1_kit_bytes`、`K2_kit_wiring`、`K3_single_layer`（`touch24` / `touch3x`）。2.x、3.x 包都必跑触摸探针（`remake-core/scripts/audit_upload_startup.py` 调 `probe_cocos2_touch_coordinates.cjs` / `probe_cocos3_touch_coordinates.cjs`），探针结果为空也算失败。v7.8（总表 A6 补）：运行时回归、广告回归开跑前先用同一个触摸探针查触摸件（探针跑不了时看平台包 `touch-coordinates.js` / `tiktok-touch-3x.js` 有没有装进 game.js）；命令行对 ZIP 跑时再查写包回执。不完整就报「环境不完整：……」（写明要装哪个件）、退出码 2，不跑用例，不报成「包不通过」（企鹅雪道 v4 对没收尾的构建跑广告回归，X 点不进游戏，看起来像广告逻辑坏了）。写包入口调用时只查触摸件、不查回执（回执还没写）。
- **验收包**：射击高手 v81、Marlows r4、小熊拳击 R27 只给 screenX/screenY 时点不动（拒），装上标准件后能点中；Ingrids r9 只有一层包装。

### 2. 启动和加载（30 款，最多的一类）
- **规则**：一次写对反复出现的 8 个错误：按“多少秒没有新字节”判卡住，不按固定总时长；下载分包接上 `onFileProgress` 显示进度；后台时间不计入超时；每次加载有代次，旧回调作废，Retry 不复用旧队列；每一步失败或卡住都出现最上层、点得中的 Retry，点了重启真正卡住的那一步；首页按钮画出来才算启动完成；首帧前只下首页必需的资源；平台接口缺一个不能拦住启动。
- **标准件**：2.4 用平台包 `build-templates/bytedance/main.js` v1.6（件名 `startup24`；v7.5 起：单文件 10 秒重发、30 秒才判失败、后台不计、每帧最多计 1 秒、场景步骤纳入看门狗、启动异常显示 Retry；v1.3 加：引擎前装 storage-guard、一次静默登录不等结果、WebP 例外时才运行标准探针；v1.4：图片解码看守挂到引擎真正的图片解析函数 `downloader.downloadDomImage` 上，一张图解码一直不回应也会重新请求（v1.2～v1.3 找的 `parser._parsers` 在 2.4 引擎里都没有）；v1.5：单个文件的重发算进度，有文件还在自己的 30 秒里时 10 秒总看守不出 Retry，所以一个卡住的文件只在真失败时出 Retry，重发后首页出来时不会再压着 “Load failed”；v1.6：启动场景反序列化之后因为一张图超时失败时，Retry 先从引擎文件缓存 `cc.assetManager._files` 里删掉这个场景再重新加载，第一次点 Retry 就能进，v1.5 及以前第一次 Retry 会马上又失败，调试版引擎报 `Can not deserialize the same JSON data again`，正式版报 `TypeError`）。3.x 平台包没有启动件（Q5），`webp-probe/cocos3.x-reference/boot-loading.js` 只作参考。
- **出包时怎么装**：重塑 2.4 新游戏源码段把 `build-templates/bytedance/` 换成只有平台包的 `main.js`、`touch-coordinates.js`、`storage-guard.js`（其他文件移到 `.tiktok-kit/removed/`）。产物段 `startup` 步：新游戏的产物 `main.js` 不是平台包的（英化工程、旧版平台包）就换成平台包 `main.js`，但只在清单 `startup24` 的 `engine_versions` 列出的引擎版本上换（2.4.4、2.4.6、2.4.13、2.4.15，前三个在模拟宿主里实测过首页和第 1 关）；其他版本保留编辑器 `main.js`，警告 `K_W_startup_engine`。装平台包 `main.js` 时包根同时放 `webp-decode-probe.js`（只放脚本，见 16 件表）。自写启动件（`native-load-guard` 一类）的加载行能整句注释掉就注释并移走文件；拿不掉的（用回调包着引擎、加载结果赋给了变量）或包里还有别的文件 require 它的，保留，警告 `K_W_own_startup_kept`，交给本游戏会话。旧游戏不替换，警告 `K_W_own_startup`。3.x 只核对、不安装。
- **现在怎么拦**：`K1_kit_bytes`（含平台包 `main.js` 要的 `webp-decode-probe.js`）、`K2_kit_wiring`（`startup24`：`game.js` 正好 require 一次 `./main`）。用本机 Creator 2.4.15 出包的重塑工程，`build-templates/bytedance/` 缺平台包 `main.js` / `touch-coordinates.js` 或被改过就拒（`audit_platform_kit_required.py`，内含 `check_kit_project.py`）；英化工程（`.tiktok-kit/policy.json` 的 board 是 `localize`，或有 `docs/english/`）的构建模板不再查，这一行改查源码段记录是否新鲜（和 K5 同一个检查），所以英化跑 `preflight.py` 之前也要先跑 `source`。静态门禁：`G3_progress`（大分包不报进度却有短看门狗，拦）、`G5_3x_presubpackage`（3.x 首帧前 await 大分包，拦）、`G6_3x_splash`（重塑拦、其他板块警告）、`G7_file_load_guard`（图片加载 10 秒就判失败，拦）、`W8_prehome_bytes`（按启动代码静态估算进首页前的下载，超过 15 MB 只警告；v7.8 起拦截用的是下面 `layout_state` 的实测，两个数并列在 `check_package` 报告的 `pre_home_bytes` 和 `pre_home_bytes.measured` 里）、`G9_doc_hidden_clock` / `G9_dom_retry`（游戏自写的看门狗用 document.hidden 计时、用网页元素画 Retry，拦；指尖麻将 v57）。运行时：`check_package` 必跑启动套件（`package-check/scripts/runtime_regression/suites/startup`，含分包变慢、下到 40% 卡死、config 失败/卡住、SDK 字段缺失，以及生命周期：加载中时钟跳 12 秒、切后台 60 秒、第一张图不回应后真点 PLAY）和 3.x 的 `startup3x`。v7.8（总表 S8 补）：开局下载用宿主实测，运行时套件 `layout_state` 记下首页场景 EVENT_BEFORE_SCENE_LOADING（3.x 按场景文件名）之前请求的分包，主包加这些分包超过 10 MiB 就拦（`startup_size`），里面有声音也拦（`startup_audio`）；新游戏拦、老游戏警告，3.x 也拦这两条。飞车 v1 实测 24.75 MiB（声音 1.26 MiB）被拦，v3.1 5.68 MiB 通过。v7.8 另修一处：3.x 原生包首个场景放在 `subpackages/<名>/config.json` 里时，`audit_native_startup_renderer.py` 也认它是场景包（加了测试）。3.x 启动件：仍是文档规则，没有真机通过的底子之前不做。
- **验收包**：MabelsMeadow r7 慢速下载、射击高手 v81 启动第二步卡住、DoubleJumpDuo 的 Retry 被遮挡、RestoreLines 2Mbps 下载，在模拟宿主里都必须复现失败；换上标准件后全部出 Retry，点一次就进首页。

### 3. 激励广告计时与卡死（34 款）
- **规则**：按上面“已定口径”第 1 条。锁必须在超时、取消、按 X 时一起清掉“正在播放”并解绑 onClose/onError；`onError` 不能是空回调；切到后台不能取消或结束正在播的广告（TikTok 播全屏广告时游戏会切后台）；广告期间暂停 BGM 和音效，各种结局后恢复。
- **标准件**：平台包 `assets/tiktok-platform/RewardedService.js`（件名 `rewarded`，与 v7.4 逐字节相同），单测 `tests/rewarded-timing.test.js`；3.x 用 `RewardedService.plugin.js`（`rewarded3x`，游戏里调 `globalThis.TikTokKit.RewardedService`），同一套计时用例。游戏只调它，不再自写广告服务。
- **出包时怎么装**：源码段 `kit_sources` 让工程里的平台包广告服务和清单逐字节相同（新游戏缺了补上、改过恢复；旧游戏只报差异）。游戏的发奖函数接到哪里，脚本不改，由模型接、由 10 个广告用例验。
- **现在怎么拦**：`check_package --ad-regression <qa/ad-regression.json>` 的 10 个广告用例必跑，有激励广告却没有适配文件或任一用例失败就出不了包（`build_checked_zip.py`、`prepare_delivery.py` 同样接收）。`A2_hide_kills_ad`：重塑拦、其他板块警告。`A1_rewarded_outside_kit`（平台包以外直接调 `createRewardedVideoAd`）：新游戏拦，旧游戏警告。BGM/音效暂停只进警告。v7.8：
  - 3.x 相机（总表 A13 补）：广告回归点 X、运行时回归找字和定位，3.x 改用节点所在 Canvas 的相机（`cameraComponent`），找不到才退回第一个相机；三处换算是同一段 `cam-point` 块（`test_tap_point.py` 会运行它）。企鹅雪道 v7 的 X 以前被算到 (818, -918) 误报 5 条，现在点到 (354, 78) 通过；2.x 不变。
  - 看广告入口真点（总表 A12、B30 B，运行时套件 `ad_entries`）：适配文件写了 `ad_entries` 就跑，5 个看广告入口加复活，状态里写真实操作；真点后 2 秒内要有广告调用、提示或文字变化，哑按钮、没有复活页都拦（新游戏拦、老游戏警告）。复活状态要等主角自己失败，`setup_js` 强制失败又没写 `wait_node` 的适配文件直接拒。和广告回归分工：广告回归测 SDK 回调，`ad_entries` 证明玩家真点的按钮能走到那条流程。
  - 领奖窗看广告双倍（Saul 2026-10-31）：适配文件写了 `double_claim` 就多跑 double_watch（勾着看完 2 倍）、double_quit（中途关 0，同窗取消勾选 1 倍）、double_free（不勾不播广告 1 倍）。
  - 试玩链接冒烟（总表 B21、B30 F，套件 `trial_link`）：`serve_preview.py --keep` 起服务后、打印链接之前，按 Saul 的用法（1180×960 电脑窗口、清存档）点一次看广告：2.5 秒内画面中心要被模拟广告窗盖住，等「看完」可点后点它，游戏必须有变化；不过就不给链接、退出码 1；跑不了（没有 Ego、找不到入口）时打印原因再给链接。手动跑 `runtime_regression.py trial --url <链接>`。入口不对时在适配文件写 `trial.taps`（`--adapter`）。试玩页往页面上加元素一律挂画布的父节点（挂在 `document.body` 上会被游戏适配器换掉的 body 吃掉）。英化包的 `cocos-game-to-english/scripts/serve_preview.py` 现在转到 `remake-core/scripts/serve_preview.py`（以前指向不存在的 `cocos-game-core`）。
- **验收包**：10 例广告回归全过（late16 不发奖、bgload 回来看完发奖、long200 发奖、nocallback 30 秒有 X 且下一次马上能用）；任挑一款自写广告服务的旧包（如 SimonsScrew R14）必须被拦，换成平台包后通过。v7.8：全民飞车漂移 v1 的 `ad_entries` 被拦（`offline_x2` 收益 0 时哑按钮、`natural_fall` 没有复活页），v3.1 6/6 通过；飞车 v1 自带的旧试玩宿主 `trial_link` 被拦（广告已开始但页面上看不到广告窗），v3.1 放进手机外壳、ReefGuard v7 经 `serve_preview.py --ad-simulator` 通过。

### 4. 存档读到的值（13 款）
- **规则**：TikTok 存储和浏览器不一样：没存过的键读到 `false` 或 `''`，用数字写进去的值读回 `true`。写入只写文字（数字、布尔先转）；读到 `null`、`undefined`、`''`、`false`、`true`、`0` 时用 key 列表（`getStorageInfoSync().keys`）判断键在不在，不在就是新玩家；读出对象直接用，不再 `JSON.parse` 一次。所有游戏（含英化原版存档代码）都走同一层。
- **标准件**：重塑用平台包 `assets/tiktok-platform/SaveStore.js`（v7.5 已按 key 列表判断）。所有新游戏（重塑和英化）再加一层平台包 `parts/storage-guard.js`（件名 `storage24` / `storage3x`；以射击高手 pkg85 的 `storage-guard.js` 为底，加 TobinsGem / Tansys 的 key 列表判断；SaveStore 的键原样读，和 SaveStore 一起跑有测试）。射击高手 pkg85（`40aee1a4…`）和 pkg83/84（`0e090a0f…`）的存档层被清单认作旧版本。
- **出包时怎么装**：产物段 `storage` 步。2.4 平台包 `main.js` 在加载游戏脚本前装它；不是平台包 `main.js` 时，包根放 `storage-guard.js`，在 `game.js` 的 `__globalAdapter.adaptEngine()` 之后插一行；3.x 插在 `require('./web-adapter')` 之后。新游戏一律装，旧版本换成新版；旧游戏不装（Q6：旧英化游戏只在 `adopt` 以后装；“盘点出数字写入时也装”还没做成脚本，要装就先 `adopt`）。
- **现在怎么拦**：`K1_kit_bytes`、`K2_kit_wiring`、`K3_single_layer`（`storage24` / `storage3x`）；旧游戏带旧版本存档层时报警告。`SaveStore.js`、`storage-guard.js` 单测（`tests/kit.test.js`、`tests/storage-guard.test.js`）；启动套件有“没存过的键”用例。写入类型记录、宿主默认“数字读回 true”、重开保存检查（过一关、领奖、买东西、重开都在）：仍是文档规则，保存检查现在只能手动跑。
- **验收包**：射击高手 v84 必须被拦，v85 通过；SorensRivet R21 在“没存过的键读到 false”时必须被拦，R22 通过；DoubleJumpDuo 的空字符串情况通过。

### 5. 适配层三处旧写法（12 款）
- **规则**：Cocos 2.4 bytedance 适配层的 `SDKVersion[0]`（字段缺失就崩、两位数主版本读错）、“没有 `getOpenDataContext` 就判成开放数据子域”、doNothing 对包内文件做 `fs.access`（真机上这一步可能一直不回），由写包入口统一替换，每处正好命中一次；替换不到或命中多处就拒绝并提示人工确认。SDKVersion 用 `split('.')` 取主版本、缺字段按 2，不用 `String(...)[0]`。模型不手改 adapter。
- **标准件**：`remake-core/scripts/package_gates/adapter_fix.py`，v7.7 由产物段 `adapter` 步原样调用（`make_tiktok_zip.py`、`build_checked_zip.py` 写包前），新旧游戏都做。
- **现在怎么拦**：写包入口自动替换（`ADAPTER_FIX_*`），`check_package` 只读、给 `W_adapter_*` 警告；不做静态硬拦（完结游戏 11/20 原样保留 SDKVersion[0] 也真机通过）。RestoreLines 入口用 `globalThis` 的同类问题：仍是文档规则（v7.7 没做，还没找到它确切的旧写法，做不到“正好一次”）。
- **验收包**：最近 23 个其他 2.4 包经过写包入口后每处正好替换一次；射击高手 v83 在 `sdk=missing` 下停在 “Starting...”，v84 进首页。

### 6. 图片：只出 PNG/JPG，按显示尺寸缩、压缩（WebP 9 款；大图和首屏过多 24 款）
- **规则**：美术导出只出 PNG（有透明，pngquant 压缩）或 JPG（不透明）；不为省体积转 WebP。按显示尺寸 2 倍缩图，非首屏图不进首屏；重复文件由美术那一步删（出包只报告，Q7）。包结构：`game.json` 在 ZIP 根、没有 0 字节文件、没有 `../` 路径。老游戏要保留 WebP，必须带标准探针。
- **标准件**：源码段 `remake-core/scripts/tiktok_finalize_steps/images.py`、产物段 `png.py`、前后对比工具 `remake-core/scripts/finalize_images_compare.py`。WebP 标准探针 2.4 `webp-probe/cocos2.4/webp-decode-probe.js` + `loading/` 样图（件名 `webp_probe24`），3.x 参考 `webp-probe/cocos3.x-reference/`（只有真解码成功才开启 WebP）。
- **出包时怎么装**（新游戏；旧游戏 `images` 一个文件都不改，只警告）：
  - 源码段 `images`：`assets/` 里的 `.webp` 有透明的转无损 PNG、不透明的转 JPG（质量 88），`.meta` 跟着改名、uuid 不变，构建设置里产出 WebP 的压缩选项关掉；原图备份到 `<工程>/.tiktok-kit/originals/`。
  - 自动缩图只在缩了不会改变画面时做：图被场景或预制体里的静态 Sprite 用、没有别的引用、不在 `resources/` 或 bundle 里、只有一帧且没有裁边，宽和高都超过显示尺寸 2 倍才缩到 2 倍。代码按路径加载的图、带裁边的图拿不到显示尺寸，要在 `<工程>/.tiktok-kit/image-overrides.json` 里逐张写 `max_side`（键可以带 `*` / `?` 通配）手动缩，裁边、偏移、九宫格边距一起按比例缩。
  - 产物段 `png`：构建产物里所有 PNG 用 `pngquant --quality=0-85 --skip-if-larger --strip` 压一次（256 色）。
  - **色带（Q3）**：接受 256 色压缩；转完用 `finalize_images_compare.py` 出前后对比，有色带的图在 `image-overrides.json` 里逐张处理（`"quantize": false` 不压缩，或 `"format": "jpg"` 加 `jpg_quality`）。
  - **WebP 例外（Q4，只限 2.4）**：转完还超 30 MB 的游戏先缩图；缩完还超，才允许保留 WebP，并装标准探针。v7.7 里保留 WebP 只支持工程里本来就有 `.webp` 文件的情况（`tiktok_finalize.py source --keep-webp-exception <原因>`，即 `images.py` 的 `keep_webp_exception`；写包入口要给同一个原因，否则 K5 拒绝；标准探针由产物段自动装，需要平台包 `main.js`）。美术是 PNG、按 `max_side` 缩完还超 30 MB 的新游戏，先在工程里把最大的几张图换成 `.webp`，再用这个例外。PNG 自动转 WebP 的步骤放到 v7.8。JaspersKelp 在遗留名单上，保持它现在的 WebP 出包方式。3.x 没有这个例外（`K_webp_exception_3x`，见 16 件表下面那段）。
- **现在怎么拦**：`K_S_webp`（新游戏构建产物里有 `.webp`，拦；例外且装了标准探针才放行；旧游戏警告）；`IMG0_source_images`（源码段拒绝：WebP 缺 `.meta`、脚本按带 `.webp` 的文件名引用要转换的图、要求带透明的图转 JPG、`image-overrides.json` 写错、改完自检不过；新游戏源码段转换图片或关 WebP 压缩时，`assets/` 下 `.json`/`.ts`/`.js`（不含 `.meta`）里写死 `".webp"`，或 `.json` 里以 `.webp` 结尾的路径，按文件拒绝并给出行号，要改成 `.png`/`.jpg`，finalize 不改游戏数据（Marlows R6 的 `"imageExt": ".webp"` 过了所有门禁，构建后 19 张图加载失败）；同一处同时列了 `.png`/`.jpg` 的格式列表、远程 URL、`assets/tiktok-platform/` 不报；旧游戏和 WebP 例外只警告；源码段有拒绝项时写包入口按 K5 拒绝）；`K_S_zero_byte`、`K_S_outside_path`（新旧都拦）；`W_duplicate_files`（只报告可省多少字节）；`G4_webp_probe`（包里有 .webp 却没有启动链里的真解码探针，拦）；平台包工程里有 .webp 就拒（`check_kit_project.py`）；体积由 `upload_size_gate` 拦（总包 30 MB、主包和每个分包 4 MB）；英化新图单张超过 800 KB 拒、超过显示尺寸 2.5 倍列出（`audit_new_english_images.py`）；源码阶段估包体（`audit_package_estimate.py`）；英化每张图要有复核记录（`audit_image_review_record.py`）。已知：3.x 自己下载解码 WebP 的游戏（Marlows R5）会被 G4 误拦，要改成按“美术怎么加载”判断。v7.8（总表 B29，SimonsScrew 补丁，`package_gates/tiktok_compat.py`，三个入口都跑）：新老游戏都拦 `T1`（game.json 的 plugins 里有抖音、微信的分离引擎插件）、`T2`（game.json 把 `subpackages` 写成 `subPackages` 这类大小写，ttmg 拒收，verify_native_zip 也会漏掉这些分包）；新游戏拦、老游戏警告 `T3`（包里有 `.ogg` / `.oga`，iOS 播不了）、`T4`（图片一边超过 4096）、`T5`（路径里有空格、`#`、`?`、`%`）；只警告：图片一边超过 2048（`W_texture_over_2048`）、游戏代码把 `CLEANUP_IMAGE_CACHE` 设成 false、图片读不出尺寸。
- **验收包**：Nanas（57.8 MB）、音乐消消乐原包经出包处理后在 30 MB / 主包 4 MB 以内；Basil、MabelsMeadow 包里 0 张 WebP，模拟“canvas 导不出 WebP”（`webp=encoder_png`）时也没有 3121。v7.8 兼容检查：SimonsScrew StallGuard 的 5 个坏副本各被对应规则拦，FoxDenDash 的 `subPackages` 大写副本被 T2 拦；`！交付游戏` 每款最新包 58 个，兼容检查没有多拦一个。

### 7. 加桌面、主页回访，以及 SDK 去哪里找（19 款；SDK 命名空间 6 款）
- **规则**：首页固定两个入口，任何环境都显示；平台不支持时点了给提示，不隐藏、不模拟成功、不发奖；不能是只显示说明文字的假入口，也不能只有跳转没有领奖查询（`getShortcutMissionReward` / `getEntranceMissionReward` / `canReceiveReward`）；只在平台真实返回可领时发一次奖，“已领取”和加币一次写入；处理好 Promise 结果。奖励 = 5B（已定口径第 4 条）。SDK 查找顺序 `TTMinis.game → tt → wx` 只写在平台包一处。
- **标准件**：平台包 `assets/tiktok-platform/TikTokMissionService.js` + `MissionFlow.js`（件名 `missions`）和固定的首页双入口组件 `HomeGrowthEntries.js`（`home_entries`：两个入口任何环境都显示，不支持时提示 “Available in TikTok”，图片加载失败时有文字备用，重复点击只发一次）；3.x 用 `TikTokMissionService.plugin.js` + `MissionFlow.plugin.js`（`missions3x`、`missionflow3x`），首页入口直接调 `globalThis.TikTokKit.MissionFlow`，没有 3.x 版组件。奖励数额用 `PlatformConfig.js` 的 `growthReward()`（固定 5B，`GROWTH_REWARD_B = 5`，不让每款自定）：先把 `normalLevelCoins` 填成本游戏的 B（= `unlock_table.json` 的 `normal_level_coins`），`MissionFlow` 不传 reward 时就按 `growthReward()` 发奖；自己写 reward 时用 `reward: function (kind, draft) { draft.coins += config.growthReward(); }`。
- **出包时怎么装**：源码段 `kit_sources` 放好、恢复这几个文件（新游戏）。把组件挂到首页节点、位置按第 9 条，仍由模型做（脚本不知道首页布局）。
- **现在怎么拦**：`G1_growth_apis`（游戏代码里 5 个接口缺一个就拒，所有板块）；`G1k_growth_outside_kit`（平台包以外调加桌面/回访接口：新游戏拦，旧游戏警告）；GROW-01 对所有 TikTok 游戏必填（`check_known_issues.py`、`audit_platform_markers.py`）；`check_kit_project.py`：`PlatformConfig.js` 必须保留 `growthReward()` 和 `GROWTH_REWARD_B = 5`、`normalLevelCoins` 必须大于 0；`K_platform_config`（包里的 `PlatformConfig` 的 `gameId` 还是 `'change-me'` 或空、`normalLevelCoins` 不大于 0：新游戏拦，旧游戏警告）；`MissionFlow.js` 的 SDK 查找顺序已统一（`tests/kit.test.js`），组件有 `tests/home-entries.test.js`。运行时领奖回归（不支持时提示、领奖只发一次、重开仍是已领取、10 秒不回应有提示）、`normalLevelCoins` 等于经济表 B 值的核对：仍是文档规则，计划做成出包硬拦截。
- **验收包**：方块迷阵原包（没接）、TovesTulip（假入口）、CindersDragon v3.1（只跳转不领奖）必须被拦；接上标准组件后领奖用例通过（CindersDragon v3.2、Marlows R6）。

### 8. 登录、App ID 和广告位（没调登录 4 款；App ID / 广告位 / 调试代码 12 款）
- **规则**：启动后发一次静默登录、不等结果、失败不影响任何流程。App ID 是数字 ID（不是空、不是 `testappId`），和 `PlatformConfig.js` 一致，在源码阶段就查；广告位从项目配置读，不沿用抖音或别的平台配置。正式包里不能有调试开关、诊断代码、模拟广告窗、测试跳关。
- **标准件**：平台包 `main.js` v1.6 启动后发一次静默登录、不等结果（2.4）；`SaveStore.js` 读档后也发一次登录；`settings/bytedance.json` 模板（命令行出包靠它写 appid）；`PlatformConfig.js` 的 `appId` 和 `rewardedPlacements`。
- **出包时怎么装**：源码段 `settings` 写 `settings/bytedance.json` 的 `appid`（新游戏同时写 `startSceneAssetBundle: false`、`REMOTE_SERVER_ROOT: ""`；旧游戏只写 appid；3.x 只在工程里有 `profiles/v2/packages/bytedance-mini-game.json` 时写）。产物段 `appid` 把构建出的 `project.config.json` 的 `appid` 改成本游戏 App ID（来源顺序：写包入口的 `--app-id` → 工程 `PlatformConfig.js` 的 `appId` → `~/.game-skill/ad-config.json`），新旧游戏都做，构建后不用再手改。广告位只核对、不写：`PlatformConfig.js` 填错了，脚本不替模型猜。
- **现在怎么拦**：`K_appid_missing` / `K_appid_invalid` / `K_appid_mismatch`（appid 缺失、空、testappId、非数字、和 `PlatformConfig.js` 不一致都拒）；`K2_login`（2.4 新游戏没有登录调用就拒，旧游戏 `K_W_login` 警告；v7.5 的 `W2_login` 警告仍在）；`L4_debug_code`（调试开关、vConsole、诊断节点、模拟广告窗、测试跳关：新游戏拦，旧游戏警告）；`check_kit_project.py` 与 `audit_source_appid.py` 保留；模拟广告窗、测试跳关、Credits/About 拒绝出包（`audit_no_ad_simulator.py`）。广告位后台状态核实：仍是交付检查表里的人工项。
- **验收包**：细菌2048 原件（testappId）“需处理”，v3 源码通过且构建出的 `project.config.json` 一致；切水果源码经过 finalize 后必须不用手改就带正确 App ID（v7.7 还没在切水果上实测）。`L4_debug_code` 在 J 的 100 个上传包上校准过，只命中甜点消消乐的诊断节点（`R47DiagnosticBadge`）；RunHome、CleosCloud 在 J 里没有可扫的上传包，还没校准。音乐消消乐沿用抖音广告位：广告位不自动写，仍靠人工核对。

### 9. 界面固定规则：胶囊、首页底排、不要 Credits（胶囊 5 款；底排 5 款；Credits 12 款）
- **规则**：右上角留给 TikTok 胶囊（实测 87×32、距右边 10、状态栏下 4），按钮和顶栏在 393×852、375×667 两种屏幕、首页、关卡、每个弹窗都不能压到它，布局按 `getMenuButtonBoundingClientRect` 读到的位置避让。首页固定为“左上设置 + 资源栏同一行、右上空给胶囊、最下面一排只放主页回访和加桌面两个平台入口”（英化保持原首页按钮不动，只在空位加这两个）。不做 Credits 窗口；素材只用 CC0，就没有必须署名的素材。
  v7.8（总表 B31）：所有 TikTok 小游戏都是竖屏：每个场景、预制体的 cc.Canvas 设计分辨率、3.x 项目设置的 designResolution 都要高大于宽，game.json 写了 `deviceOrientation` 就必须是 `portrait`（不写时 TikTok 默认竖屏，不拦）。
- **标准件**：首页分区规则见 `remake-art`（重塑包）；官方宿主 `package-check/scripts/ad_regression/host.js` 提供胶囊位置（v7.8 起支持 `dev=iphone14|se`、`capsule=pt|px`）。v7.8 平台包可选件 `parts/CapsuleLayout.js`（2.4 用 `require('CapsuleLayout')`，3.x 插件脚本用全局 `TikTokCapsuleLayout`）：自己判断胶囊接口返回的是点还是像素，按引擎真实视口换成设计坐标，`safeTopY`、`placeBelow`（只往下挪）、`alignBelow`（顶边正好在胶囊下）；顶栏、右上按钮用它避让胶囊，不再每款自己换算（Spider、Hollys、Fox、飞车 v2 都中过“胶囊按像素返回时顶栏下移”）。它是 `reference: true, optional: true` 的件，finalize 不自动装，没装它的工程不会被拒。
- **现在怎么拦**：Credits/About 窗口拒绝出包（`audit_no_ad_simulator.py`，`check_package` 一次列出）；重塑首页分区（设置在顶行、PLAY 下面只放回访和加桌面）由 `audit_ui_coverage.py` 判不通过。v7.8 运行时套件 `layout_state`（出包必跑，见「出包时怎么装」的运行时套件表）：iPhone 14 和 SE 两种屏幕、胶囊按点和按像素各一遍、适配文件 `layout_states` 列的每个状态，查按钮被屏幕边切掉（`offscreen`）、按钮或文字压胶囊（`capsule`；SE 的胶囊横向位置是推算的，只警告）、按钮中心在底部横条里（`safe_area`，只伸进一点只警告）、被 3D 盖住（`covered_3d`，按钮 30%、文字 50% 以上）、两遍位置差超过 4 点（`unit_shift`，胶囊按像素时跟着走）；首页规则按 board 分：重塑查设置在左上（`settings_pos`）、最下面一排只有两个平台入口（`bottom_row`），英化只查两个平台入口在首页、能点、不压原按钮（`platform_entries`，原首页按钮不动）。新游戏拦、老游戏警告，3.x 只警告。竖屏（v7.8）：包里 game.json 的 `deviceOrientation` 不是 portrait 拦（`O1_device_orientation`，`package_gates/portrait.py`，新老游戏都拦）；源码段 `orientation` 步：任一场景或预制体的 Canvas、3.x 项目设置宽大于高拦（`K_portrait_design`，进源码记录，写包入口靠 K5 拒；读不出只警告）。启动包和重塑模板源头删掉 Credits：仍是文档规则，计划做成出包硬拦截。美术素材只用 CC0 写在 `remake-art`，也只是文档规则，没有门禁。`known-issues.json` 的 ART-05 还写着“左上或右上”，以本页“左上”为准。
- **验收包**：Mabel r7 两种屏幕都报压胶囊、r8 不报；拇指弹球 v5 拒、v6 过；CindersDragon v3.1、Marlows R5 底排多按钮拒，v3.2、R6 过；Pinecone 原包的 Credits 和底排 4 个方框在模板改过以后不再出现。v7.8：全民飞车漂移 v1（开局 24.75 MiB 含声音、按像素时顶栏 10 个节点下移 166 点、钱和文字被 3D 盖住）、v3（RACE 被 3D 展台盖住 37%）被 `layout_state` 拦，v3.1、HappyCup v20.7.1 通过；飞车 v1 首页改用 `CapsuleLayout.alignBelow` 后 `unit_shift` 清零。竖屏：`！游戏学习库/检查工具/校准样例/坏_横屏`（1280×720）拦，Pinecone 源码、FoxDenDash v1、DriftRacer v3.1 通过。

### 10. 声音：来源、用量和成品响度（v7.8 新加，总表 H7）
- **规则**：重塑游戏的声音从本机音效库 `~/GameAudioLibrary` 选（`game-audio-library`），底子原游戏自带的声音不许用，避开别的游戏用过很多次的；只用 CC0、可商用、免署名的素材。成品响度：音效 -16 LUFS、BGM -20 LUFS，各 ±4 LU；失败音（名字带 fail、lose、gameover、defeat、death 等，以及 timeout、time_out、times_up 这类「时间到」，Saul 10-30 21:3x）2 秒以内、结尾淡出。英化游戏照旧：原版的声音写「原游戏自带」就算来源。
- **启动包自带的声音**（Saul 10-30 21:3x）：会话把启动包声音的原字节复制进工程后，跑 `python3 remake-game/scripts/starter_audio_credits.py --starter <启动包文件夹> --project <工程>`。它读启动包的 `audio/AUDIO_IMPORT.json` 和 `audio/CANDIDATES.json`（没有就读 `licenses/`（`credits.csv`、`<cue>.json` 的 `source_sha256`）和 `CREDITS.txt`），一律以音效库 `index.csv` 为准（先按路径，再按 sha256、「包 + 名」、文件名），把每个声音的 `library_path`、`source_sha256`、授权、作者、网址写进 `docs/audio/credits.csv`，算从音效库选的。字节和启动包记录对不上、库里找不到、对上多条的不写，列进 `missing`（退出码 1），这些要从音效库补选。sources.md 只写「启动包提供」「原游戏自带」的，重塑不算来源。写完后被 2 款以上别的游戏用过、要署名的照样被拦（校准里每款约 1～8 个要换）。
- **标准件**：音效库的 `process_audio.py` 把名字算失败音的截到 1.94 秒、末尾淡出 0.35 秒；`search_index.py` 选失败音不超过 2 秒。失败音名单和秒数只写在 `remake-core/scripts/package_gates/audio.py`（`FAIL_TOKENS`、`FAIL_TARGET_SECONDS`），音效库经 `game-audio-library/scripts/fail_sound.py` 读它。
- **现在怎么拦**：
  - 来源（`remake-core/scripts/audit_audio_sources.py`，preflight 和问题清单里跑）：board=remake 时每个声音都要在 `~/GameAudioLibrary/index.csv` 找到来源（按 library_path、original_path、source_path、file、两种 sha256、「包 / 名」、url、文件本身的 sha256；credits.csv 的 8 种表头都认）；来源要署名的算问题；同一素材被 2 款以上别的游戏用过（读 `usage/*.json`）算问题，1 款只提醒；credits 写的路径和实际位置不一致只提醒。新游戏拦，名单上的老游戏警告；没有任何记录的声音新老都拦（原有规则）。
  - 成品（`package_gates/audio.py`，三个入口都跑，每个音频跑一次 ffmpeg）：`A1_audio_loudness`（偏离目标超过 ±4 LU：音效 -20..-12，BGM -24..-16，名字判为 jingle 的 -24..-12；0.5 秒以下不测；测成静音也算）、`A2_fail_sound_length`（失败音超过 2.5 秒）、`A0_ffmpeg_missing`（没装 ffmpeg，提示装上再出包，不静默跳过）：新游戏拦、老游戏和英化警告。只警告：`W_audio_harsh`（4 kHz 以上能量只比全频低不到 6 dB，0.3 秒以内的不报）、`W_audio_unmeasured`、`W_audio_unnamed`。音效、BGM 还是 jingle 按顺序判：工程 `docs/audio/needs.csv` 的 type、像失败音的算 jingle、名字带 win/victory/fanfare 等算 jingle、带 bgm/music/loop 等算 BGM、超过 15 秒算 BGM，其余算音效；包里的文件名是 uuid，门禁读 bundle 的 config.json 和工程 .meta 对回资源名。
- **验收包**：Pinecone fix1 源码（21 个声音都没有记录）被来源检查拦；Pinecone fix2 的 6.0 秒 `jingle_lose` 被 A2 拦，用 `process_audio.py` 处理后 1.94 秒、A1 和 A2 都过；企鹅雪道、珊瑚守卫、丛林荡藤两项都通过。FoxDenDash v1 的 `timeout`（3.1 秒、-26.0 LUFS）被 A1、A2 拦。

## 第二部分：跨游戏通用流程（多数游戏都会遇到，位置每款不同）

规定写法，再用运行时用例去验。

### 1. 存档写入和事务（15 款）
- **规则**：写失败要提示，不能继续扣东西；写后读回确认；奖励和“已领取”在一次写入里完成，写失败给 Retry Save，不让玩家重看广告；坏档先备份原文再用默认档，不直接覆盖；`JSON.parse` 外面有 try；新加字段进默认值和校验，读档不丢。
- **标准件**：重塑用平台包 `SaveStore.js`（整档一个键）；英化把原版多键存储包进第一部分第 4 条那一层。
- **现在怎么拦**：`logic_check.py` 的 `L-DAILY-DATE`（每日奖励只比几号，fail）、`--stage final` 时回归用例缺失算失败；`L-SAVE-PARSE` 只提示。存档故障宿主、重开保存检查（过一关、领一次奖、买一件，重开都还在）：仍是文档规则，计划做成出包硬拦截。
- **验收包**：方块冲冲 BUGFIX4 失败，BUGFIX5 和 `方块冲冲tk.zip` 通过；射击高手 v84 重开后进度丢失（拒）、v85 通过；CindersDragon v3.1 拒、v3.2 过。

### 2. 看广告复活、结算 x2（14 款）
- **规则**：按“已定口径”第 2 条：先复活页、再结算页，每屏一个看广告按钮；复活每局一次，Retry 后不能凭空没了；看完回到这一局继续，分数金币保留，复活前看得见的局内按钮（BACK、暂停）复活后照样看得见点得动；结算 x2 看完正好多发一份且只一次，失败结算不显示 x2；没有货币的游戏 x2 翻倍本局捡到的道具。英化一律加复活。
- **标准件**：复活和 x2 都走平台包 `RewardedService.js`；流程规则见 `remake-ads/references/end-flow-one-video.md`（重塑包内）和英化 `cocos-game-to-english/references/fixed-entries.md`（英化包内）。
- **现在怎么拦**：`audit_page_richness.py` 的 `two_video_buttons`（同一屏两个看广告按钮）；签到 / 转盘结果 / 礼包领奖窗由 `audit_claim_double.py` 拦两个广告入口、必须看广告才能领、默认不勾；10 例广告回归（有勾选框时另加 3 例）。复活和 x2 的运行时用例：仍是文档规则，计划做成出包硬拦截。
- **验收包**：方块迷阵 v6（复活和 x2 同一弹窗）失败、v6.1 通过；MusicSlice 原包找不到 x2 失败、v30 通过；方块冲冲 BUGFIX5（没有复活）失败、BUGFIX6 通过；拇指弹球 v5 复活后 BACK 不见失败、v6 通过。

### 3. 弹窗布局、空位、提示挡操作区（17 款）
- **规则**：删掉入口后同一组剩下的按钮要重排，不留空位和无效点击区；提示文字不压玩法区、触摸区、按钮和常驻 HUD，最多两行。
- **现在怎么拦**：英化固定入口已写“删后重排”。按钮间距检查：仍是文档规则，计划做成出包硬拦截。v7.8：
  - 美术关的「位置穿模」一行（`audit_page_richness.py`，总表 U11）：`overlap_button_picture`（按钮压着可见的框类图，含只挂 BlockInputEvents 的小按钮；按钮坐在面板上、角标红点、价格签不算；珊瑚守卫的「Video closed…」提示条压住按钮也在这里报）、`busy_text_background`（没有底板的字，身后背景超过 13 种颜色，报「加底板或挪位置」）、`stacked_text_layers`（同一个 Label 下面可见的字图超过 1 层：换字时旧字图没删，剪刀达人 v26；换字前先清掉同名子节点，状态会变的弹窗每个状态都 dump）。首页两个平台入口下面的说明字默认放在底板上（`remake-art/references/common-game-components.md`：字和按钮一起生成成整张图，或照 Holly v3 在入口节点下、`EntryCaption` 之前加同级节点 `EntryCaptionPlate` 画圆角底板）。
  - 弹窗遮罩：有全屏 BlockInputEvents 就算挡住下面的页面，不看透明度（Saul 10-31 撤掉 U7 补的遮罩门槛，源码段也没有 `K_art_dim`）。明暗只能人看。
  - 运行时套件 `button_sweep`（总表 B30 E，出包必跑）：iPhone 14、真鼠标，首页每个按钮点一次，再把它打开的一层弹窗里的按钮各点一次；点后 2 秒内没有任何变化报没反应（`dead_button`），弹窗按钮伸出屏幕、压胶囊、在底部横条里、被 3D 盖住也报，并列出所有看广告入口。已选中项、只有触摸监听的拖动目标、灰按钮、屏幕上看不到的列表项只警告。新游戏拦、老游戏和 3.x 警告。v7.8 第四轮（总表 B30 补，W93）补三处：①弹窗里的关闭/返回/X 点了、弹窗确实消失后**不重新加载**，再点一次打开它的按钮（必须再打开同一个弹窗），再点一个之前有反应的按钮（必须有反应），否则 `blocked_after_close`（点名哪个按钮打开、哪个按钮关的；关掉后留下透明遮罩、全屏 BlockInputEvents、busy 没放开都会这样）。②每条 `dead_button`、`blocked_after_close` 后面写卡在哪一段：「点不到（被 X 盖住）」（名字、路径、有没有 BlockInputEvents、透明度）、「回调没执行（…）」（没收到抬起、interactable=false、clickEvents 指向不存在的方法、没挂回调）、「回调报错：…」（从触摸分发里抛出的异常）、「请求没回来：…」（tt 调用、资源加载、分包、广告发出去没回）、「点到了也执行了，但画面没变」；2 秒内只是打印出来的报错附在结论后面；按钮自己按下时的缩放、位移不算反应。③适配文件有 `play` 时真点 PLAY 进局，照首页的办法扫局内按钮（暂停、设置、技能）和它们打开的一层弹窗，含关后再点；局内时间上限 min(`sweep_budget_s`, 90 秒)，超时只警告，局内弹窗的位置问题只警告；没有 `play` 不扫局内，原因写在证据 `notRun` 和警告里。每个按钮的业务结果断言（点了以后预期的事确实发生）留到下一版。
- **验收包**：射击高手 v84 设置页间距 200/100 报出、v85（都是 115）不报；JaspersKelp r6 的取消提示报“压住 SwipeZone / 三行超过两行”。v7.8：Holly v1 局内设置压着遗留互推框（`overlap_button_picture`）、v1/v2 首页 PROFILE 压栅栏（`busy_text_background`）报出，v3、v6 不报；剪刀达人 v30 的 dump 照 v26 写法加一层字图报 `stacked_text_layers`，原样不报。全民飞车漂移 v1 商店顶条 `Canvas/Shop/anim/ScrollView/car` 空按钮（W93 诊断：clickEvents 有一项没有目标节点）、v3 买第一辆车后 RACE 被盖 37% 被 `button_sweep` 拦，v3.1、HappyCup v20.7.1 通过；W93 在 HappyCup 副本页面里改坏：关闭只设 opacity 0 并留着全屏遮罩、关闭后留下全屏 BlockInputEvents 报 `blocked_after_close`，回调抛错报「回调报错」，透明节点盖住报「点不到」，tt 调用不回报「请求没回来」，busy 标志报「画面没变」，原包通过。

### 4. 源码和上传包对不上（21 款）
- **规则**：上传包只能从源码经官方写包入口（`make_tiktok_zip.py` / `build_checked_zip.py`）出；直接改包必须带补丁脚本，对源码和包打同一组改动、每处正好命中一次，并写进源码说明。
- **现在怎么拦**：两个写包入口都写 `<zip>.receipt.json`，没有回执的 ZIP 标“非官方入口”，`prepare_delivery.py` 拒收；`prepare_delivery.py` 比对 `logic_check` 报告里的源码哈希和交付源码。v7.7 起写包入口还查 `K5_source_finalized`（源码段之后工程没改过）和 `K4_finalize_ran`（产物段写的文件和包里一致），收据升到 schema 2、带 `finalize` 记录；v7.6 写的收据不再是官方入口，要用 v7.7 写包入口重新出包。v7.7.4 起 `verify_native_zip.py` 和 `upload_preflight.py` 单独运行时也拒收没有匹配回执的 ZIP（退出码 3 / refuse；DriftRacer v2 就是只跑了这两个、带着旧版广告服务交的包），只看结构加 `--structure-only`。v7.7.5 起 ZIP 改了名也认：同名回执不在时，在同一文件夹里找为这份 ZIP 字节写的回执（官方写包入口写的、`zip_sha256` 相同），内容改过一个字节就找不到。v7.8（总表 B17）：`check_package.py` 命令行对没有匹配写包回执的 ZIP，结论写「只读预检，不可交付（非官方入口）」，状态 `unofficial_not_deliverable`，**退出码 3**（以前照样报通过，丛林荡藤 v6、剪刀达人 v30 都是这样）；给的是 Native 目录时写「只读预检，不可交付（Native 目录不是上传包）」；`--structure-only` 只看结构，结论仍写不可交付；官方入口写的包写「官方入口写出的包，本地检查通过」。写包入口和 prepare_delivery 调的 `check()` 不变。v7.8 起写包入口还要美术回执（`ART_receipt`），见「出包时怎么装」。build-templates 和包根文件逐字节比对、补丁脚本要求：仍是文档规则，计划做成出包硬拦截。
- **验收包**：Basil fix1、fix2 配 0.4.0 源码被拦；Marlows R6 配 R6 源码通过；方块冲冲原包配现在的源码被拒、`方块冲冲tk.zip` 通过。

### 5. 英化固定清理：分享、更多游戏、排行、跳转、国内统计（10 款 + 统计 2 款）
- **规则**：按“已定口径”第 3 条处理分享；更多游戏、联网/好友排行榜（含开放数据域）、跳转其他小程序的入口和调用删干净（局内对本地机器人的名次可以留，Saul 10-31），删后重排；国内统计上报（腾讯 MTA 等）删掉。组件被预制体引用时保留同名字段、清空行为，不直接删类。
  把 WxGameBox 这类旧类换成空实现时，`init(nodes)` 要把传进来的节点设成 `active = false`，不能让节点一直显示（Holly v1 局内的「Try It」框就是方块冲冲的微信互推挂件，代码删了、节点还在）。
- **现在怎么拦**：`H14_cross_promo`（真调到跳转/更多游戏，拦；空壳目前也拦）、`H13_analytics_domain`（统计域名，拦）、运行时网络套件（清单外请求，警告）、`audit_share_entries.py`、`audit_no_social_features.py`（一键预检）。v7.8：
  - `VIS_DEAD_SHELL`（总表 E1 补，运行时套件 `dead_shell`，每个 2.x 包出包必跑）：扫首页、用适配文件 `play` 真点 PLAY 后的局内、有 `enter_level` 时的关内，节点真的看得见（activeInHierarchy、自身和父链透明度大于 0、有图或有字、在屏内、宽高大于 4 px），而且节点自己的名字或图片帧名整名命中退役槽位名单（gameBox、leftGameBox、leftGameBtn、gameIcon、popBox、fullScreenBox、leftBox、moreGame(s)、more、bannerAdv、banner_border、friendRank、phb、jxyx、hy、tj；`item_bg` 只在槽位节点里面才算；rank、ranking 不算，Saul 10-31 允许局内本地名次），就报。祖先节点名命中不算（Meteor 的玩法容器叫 gameBox）。`play`、`enter_level` 都没有，或真点 PLAY 后没离开首页，判不通过。新游戏拦、老游戏警告；3.x 没做。和 H14 不冲突：代码删干净但节点还显示时 H14 过、这条拦。
  - 英化商标词（总表 E8，`audit_copy_quality.py` + `remake-core/assets/trademark-words.json` 61 条）：玩家看得到的字命中 `level: block` 的品牌、车型、角色名（Ferrari、Lamborghini、Porsche、Lykan、Wuling、Optimus Prime、Spider-Man、Mario、Pokémon 等）就阻断，并给通用叫法（如 “Supercar / Red Racer”）；本身也是普通英文的词（Mustang、Jeep、Ford、Tesla 等）和代码、数据里的字符串字面量（车名表常在这里）只进 review。有授权的写进 `docs/copy/glossary.json` 的 `trademark_ok`（`term` 加 `why`）。数据表里的车名要不要算玩家可见、直接拦，留到下一版。
- **验收包**：射击高手 v81 拒、v83 过；甜点消消乐、MabelsBus r5 拒；细菌2048 原件分享换提示被拦、v3 过；MusicSlice 的 mta 故障变体拒、v30 过。v7.8：Holly v1 被 `VIS_DEAD_SHELL` 拦（`Canvas/gameLayer/gameView/info/gameBox/bg`，帧 gameIcon，118×133），Holly v2、方块冲冲 BUGFIX7、FoxDenDash v1 和另外 7 款真包 0 命中；全民3d飞车漂移中文源码副本里首轮英化留下的 “Lykan HyperSport II” 被商标词表拦，本机 11,417 份 ui-dump 0 条命中。

### 6. 读包内文件用错接口、加载不存在的分包（5 款）
- **规则**：代码里 `loadSubpackage` / `loadBundle` 的名字必须是 `game.json` 声明的分包或包里有的 bundle；加载的资源路径要在包里；不准用 `downloader.downloadFile` 读包内文件。
- **现在怎么拦**：`H12_bundle_name`（拦）。资源路径比对、禁止 downloadFile 读包内文件：仍是文档规则，计划做成出包硬拦截。
- **验收包**：MusicSlice 的 general 故障变体拒、v30 过；Junos（artUI）、Pinecone（downloadFile 读包内文件）应被拦。

### 7. 图片卡住后界面元素消失（7 款）
- **规则**：首页必需的图放主包或第一个分包；PLAY、加桌面、主页回访在图卡住或失败时仍看得见、点得动（平台入口带文字备用显示）。
- **现在怎么拦**：静态 `G7_file_load_guard`。图片卡住的运行时用例、平台入口文字备用：仍是文档规则，计划做成出包硬拦截。
- **验收包**：`accesshang=f96eaa92|5cce308a|01b4d089|5261f8dc` 下射击高手 v81 两个入口没图被拦，v82 以后通过。

### 8. 玩法状态（11 款，22 条）
- **规则**：一局结束后旁边的碰撞、计分、连锁、弹窗回调不能再加分加币、不能出第二个结果页；全局事件监听要注销；所有开局入口统一扣体力；体力恢复不超上限；弹窗打开时局内物理和计时停。
  v7.8 加四条：
  - **滚动障碍按真实可见宽度出现和回收**（总表 P2 补，热气球 v2.1）：不许少量障碍按写死的数字循环挪、用设计宽度常数决定出现位置、在可见范围里新建/显示/隐藏/一帧跳 40 以上（复活、暂停恢复、加速时也算）、定时器按距离激活前方节点。要这样写：开局一次生成前方至少 3 个屏宽；新障碍只放在「真实可见右边缘 + 半宽 + 至少 100」之外，完全离开左边缘才回收；屏幕越宽组数越多；复活清障不瞬移看得见的障碍（淡出 0.3 秒以上，或在不透明遮罩下处理）。标准件：平台包可选件 `parts/CourseLane.js`（`visibleRect`、`spawnX`、`recycleX` / `isGone`、`lanesNeeded`、`clearForRevive`；2.4 `require('CourseLane')`，3.x 全局 `TikTokCourseLane`；淡出期间先关掉这些障碍的碰撞体）。写法细则见 `remake-game/references/creation-gates.md`「滚动障碍」。
  - **物理和施力按时间走，不跟屏幕帧率**（总表 P16，全民飞车漂移 `schedule(run_time, 0.01)` 每次推固定的力、没开 enabledAccumulator，120 帧的 Mac 上跑成两倍速）：用了 2.4 物理别自己关 accumulator；推力、扭矩、冲量写成 `Clock.force(v, dt)` / `Clock.scale(dt) * x`（`require('PhysicsClock')`），移动写成每秒多少 × dt，不用间隔小于 1/60 秒的 schedule。标准件：平台包可选件 `parts/PhysicsClock.js`，新游戏由 `tiktok_finalize.py source` 的 `physics_clock` 步自动装（见「出包时怎么装」）；60 帧手机上开不开 accumulator 都是每帧一步，手感不变，只纠正 120 帧的设备。
  - **难度曲线 `wave-tiers.v2`**（总表 P17，Saul 10-29）：第 1、2 关教学，第 3 关固定是难关（`first-hard`），第 4 关起进不规则波浪（不连着两个难关，第 3 关起每个普通关都比第 1、2 关难），每个限定关是高难考核，奖励关位置和 v1 相同。`make_level_plan.py` 默认出 v2，`--policy wave-v1` 还能出 v1（逐字节相同）；`audit_level_plan.py` 按 `level_plan.json` 的 `difficulty_policy` 选规则，已开工、按 v1 排好的表照 v1 查，不返工。难关看广告提示的默认位置跟着改成第 3 关（v1 表仍是第 4 关）。
  - **完整换皮 `mode=reskin`**（总表 P18，Saul 10-30）：照搬底子的关卡、难度、玩法代码，`level_plan.json` 写 `remake_mode: "reskin"`、`reskin.approval`（Saul 的原话和日期）、`reskin.copied`（每个照搬文件的底子路径、工程路径、sha256），`make_level_plan.py --reskin … --approved-by Saul --approved-date … --approved-quote …` 生成；`audit_level_plan.py` 逐个和底子比 sha256，都对上才不受 60 关下限，没有点头记录或有文件改过就不过。新做关卡时先出 3～5 个样关给 Saul 定难度（样板先行，`docs/samples/samples.json`，`design_check.py` 只提示）。
  - 划线、切割类（总表 T7）：`plan_level_tests.py --input cut|slice|draw|line|swipe|stroke` 固定加三条触摸用例（画外松手、起点在目标内 8 px、终点在目标内 8 px），每个抽测关列设计解（必须过）和偏移、斜切两种错误解（必须不过）；Skill 没有通用关卡运行器，游戏自己的运行器照 `remake-levels/references/level-rules.md` 跑，现在没有自动门禁。
- **现在怎么拦**：`logic_check.py` 的 `L-MODAL-PAUSE` 只提示。玩法状态运行器：仍是文档规则，计划做成出包硬拦截。v7.8：
  - 运行时套件 `popin`（出包必跑，2.4）：四种屏幕（390×844、375×667、768×1024、1115×791，新存档），主角无敌飞 18 秒、调一次复活再看 4 秒，每一帧查带碰撞体、画得出东西的节点：`appeared_on_screen`、`vanished_on_screen`（被销毁也算）、`jumped_on_screen`（一帧挪 40 以上，按帧时间放大）；允许淡入淡出，整屏不透明遮罩下面发生的不算。适配文件要有 `popin` 块（必填 `player`、`invincible_js`、`revive_js`、`game_node`，可选 `start`、`fly_s`、`ignore`、`ignore_groups` 等；主角自己射出去的钩子、子弹带碰撞体又不在主角节点下的写进 `ignore`），没有滚动障碍的游戏写 `{"n/a": "原因"}`。一个障碍都没看到算适配写错；页面低于 20 帧本次无效、重跑。新游戏拦（缺 `popin` 也拒）、老游戏警告不跑；3.x 只警告「未覆盖」。
  - 运行时套件 `frame_rate`（出包必跑，2.4，P16 的最终裁判）：把页面时钟换成 60 Hz 和 120 Hz 各跑一次同一段操作，从跟踪节点开始动的那一刻对齐，往后 1 秒起每 0.25 秒比一次位移，差超过 5% 不过；节点没动够 20 个世界单位算适配写错，时钟没跑到目标帧率本次无效、一律拒。适配文件要有 `frame_rate` 块（必填 `track`、`drive_js`，可选 `start`、`prepare_js`、`steps`、`run_s` 等），没有物理、没有自己会动的东西写 `{"n/a": "原因"}`。新游戏拦（缺 `frame_rate` 也拒）、老游戏警告不跑；3.x 只警告「未覆盖」。
  - `logic_check.py`（只静态，总表 P16 第 2 步）：`L-FPS-ACCUM`（开了 2.4 物理、整个工程没有 `enabledAccumulator = true`）、`L-FPS-SCHEDULE`（`schedule(cb, x)` 的 x 小于 1/60 秒且回调不用 dt）、`L-FPS-DT`（每帧回调里施力、冲量、改速度或给位置加步长却不乘 dt）；新游戏需处理、名单上的老游戏只提示。装了 `PhysicsClock` 后 `L-FPS-ACCUM` 不报，`L-FPS-DT` 照报。只查 2.4 的 2D 物理。细则见 `/Users/sijunting/Downloads/！自制游戏/启动包工坊/！Skill更新/发给Skill制作_沉淀方块冲冲与横向12款玩法状态问题_复制这段话.txt`。
- **验收包**：方块冲冲原包被拒、`方块冲冲tk.zip` 通过；回家快跑现有源码在监听注销和体力上失败。v7.8：BreezyBalloon v2.1 四种屏幕都被 `popin` 拒，v2.2 和 v2.1 运行时换用 CourseLane 后四种都过，底子潜艇冲冲 V32 也被拦（复活瞬移是底子原有的）；全民飞车漂移 v3.1 被 `frame_rate` 拒（起步 1 秒 60/120 帧差 19.9%），开 accumulator、推力乘 dt 后 1.05%、只装 PhysicsClock 后 1.39% 通过；BreezyBalloon v2.2 120 帧快一倍（49.9%）被拒，装 PhysicsClock 后 1.08%；飞车英化工程 `logic_check` 报 `L-FPS-ACCUM` `RunUI.ts:145`、`L-FPS-SCHEDULE` / `L-FPS-DT` `pysTouchEvent.ts:91`。

## 第三部分：不写死的单款问题

玩法 bug（穿模、物理、判定）、难度和经济数值、美术音频动画观感、字体缺字和浅色字、多点触摸和触摸区域：和每个游戏的内容有关，按 Saul 记在各板块 Skill 里的偏好检查，不做成固定件。v7.8 起其中能量化的几项做成了门禁：美术见「出包时怎么装」的「美术回执和美术记录」和第二部分第 3 节，声音见第一部分第 10 节，物理跟帧率见第二部分第 8 节；其余照旧只按偏好检查。

## 第四部分：不要做

1. 不要再在每个游戏里各写一份触摸、启动、广告、存档、任务代码，哪怕只是“照抄平台包”。直接引用平台包文件。
2. 不要把第一部分做成“检查出来再让模型修”。目标是出包时自动装上，再确认装上了。
3. 不要因为旧游戏自写的启动链、广告代码能用，就自动替换。只对新游戏强制，旧游戏给警告，交给各自的会话。
4. 每做成一条硬拦截，都在完结游戏里抽 3 款（至少一款 3.x）跑一次，确认不误拦好包。检查工具自己也会误报漏报（33 款碰到过），探针报错不能说成包不合格。
