# TikTok 固定适配（必须遵循）

修订：`2026-10-29.tiktok-fixed.2`（v7.7：出包时自动装上标准件，再由门禁确认装上了，见下面「出包时怎么装」；上一版 `tiktok-fixed.1` 是 Saul 2026-10-29 10:20 定的：这份总结很重要，所有 Skill 的最新版都要放进去，以后每款游戏都必须照做）。英化包和重塑包共用本页（`cocos-game-check` 两包字节相同）；本页和其他板块说法冲突时，以本页为准。

**来源**：58 款游戏（40 款 10-27～10-29 修过的新游戏 + 18 款真机完结的老游戏）的修复记录，整理出 526 条“问题—根因—修法—证据”。全部记录、分类表和统计在（只读）：
`/Users/sijunting/Downloads/！自制游戏/！交付游戏/1香吉士-射击高手2048/检测修复_20261029/跨游戏调查_20261029/`（`全部记录.jsonl` 每行一条带证据路径，`NOTES.md` 逐类笔记，`matrix.json` / `matrix.md` 统计）。总表原文：`/Users/sijunting/Downloads/！自制游戏/启动包工坊/！Skill更新/发给Skill制作_跨游戏TikTok固定适配总表_复制这段话.txt`。逐款经过不在本页重复，要查就去记录文件夹。

**为什么要写死**：出现最多的几类（扫码转圈、激励广告、包体、触摸、加桌面回访、存档读值）每款游戏都一样、和玩法无关，以前却每款各自重新写一遍修法。

## 怎么读每一条

- **规则**：一两句，做到什么算对。
- **标准件**：直接用的平台包文件或脚本（路径相对 Skill 包根目录；平台包 = `remake-core/assets/platform-kit/`，接法见 [平台包接入说明](../../remake-core/assets/platform-kit/README_接入说明.md)）。
- **现在怎么拦**：v7.7 里已经能拦的门禁或脚本 id。写着“仍是文档规则，计划做成出包硬拦截”的，现在出包不拦，但照样必须做到。
- **验收包**：坏包必须被拦、修好的包必须通过（取自总表第五部分和修改要求总表）。

## 已定口径（不再让模型临场决定）

1. **广告计时 = v7.4 规则**（Saul 10-29 03:18）：请求到 `show()` 成功最多 15 秒，只算前台；`show()` 之后不计时，只在 `onClose(res)` 且 `res.isEnded === true` 时发一次奖；开播 30 秒没有回调出 X，按 X 不发奖；超时、按 X、取消之后才开播或才看完的视频**不补发**；不留收尾锁，下一次广告马上能发。详见 `remake-ads/references/ad-timeout-and-regression.md`（重塑包内）。
2. **英化游戏一律加看广告复活**，没有失败状态的游戏也加（Saul 10-29）。一局结束先出复活页（只有看广告复活 + 免费 NO THANKS），放弃或已用过复活后再进结算页（只有看广告 x2，RESTART/HOME 在下面）；**同一屏只放一个看广告按钮**。
3. **英化分享奖励**：核心玩法里的分享奖励（复活、礼物、双倍）改成激励视频；其他分享入口（成就分享、升级分享、邀请好友等）连同触发它的礼物球、弹窗删干净，不留“本平台不可用”的死按钮。
4. **加桌面、主页回访的一次性奖励**：每项都等于一次首页礼盒的基础奖励 **5B**，换算成这款游戏自己的货币；没有首页礼盒的游戏也按 5B 算（Saul 10-29 09:11）。以前 20～150 各不相同的，下次出包统一改。平台包取值见第一部分第 7 条。
5. **新游戏必须用平台包标准件**，不手写、不“照抄平台包”另存一份；**旧游戏**（在冻结的遗留名单上的）不自动替换，只给警告，由各自的游戏会话处理。哪些算旧游戏见下一节「新游戏和旧游戏」。
6. **交付回复写“标准件待真机复测”**：v7.7 的标准件（平台包 `main.js` v1.6、`storage-guard.js`、`tiktok-touch-3x.js`、`HomeGrowthEntries.js`、3.x 插件版、WebP 探针）都只在 Node 和模拟宿主里测过，没有扫码确认。第一款 v7.7 新游戏扫码通过之前，每个交付回复都写这一句。

## 出包时怎么装（v7.7，`tiktok_finalize`）

标准件不再靠模型复制。`remake-core/scripts/tiktok_finalize.py` 在出包时把它们装上，门禁再直接读包里的字节确认装上了。模型只做脚本做不了的两件事：把游戏的发奖函数接到平台包广告服务上，把首页两个入口挂到首页节点上。

**命令**（路径相对 Skill 包根目录）：

1. **起项目 / 英化开工**：`python3 remake-core/scripts/tiktok_finalize.py init --project <工程> --board remake`（英化用 `--board localize`），写新游戏标记 `<工程>/.tiktok-kit/policy.json`。英化接着跑 `tiktok_finalize.py inventory --project <工程>`，把原版里的广告、加桌面/回访、触摸、启动、存档、分享/跳转/统计、登录代码列到 `docs/english/platform-inventory.json`。
2. **源码段，Creator 构建之前**：`python3 remake-core/scripts/tiktok_finalize.py source --project <工程> --board remake|localize [--app-id <ID>]`。按顺序跑 `images`（WebP 换 PNG/JPG、缩图）、`kit_sources`（平台包模块逐字节对齐）、`build_templates`（只对重塑新游戏：`build-templates/` 只留平台包件；英化工程和旧游戏的构建模板不动，触摸、存档、启动件改在产物段装）、`settings`（写 App ID）。改动前的原图在 `<工程>/.tiktok-kit/originals/`，被换掉的文件在 `<工程>/.tiktok-kit/removed/`，记录写 `<工程>/.tiktok-kit/finalize-source.json`（含 `assets/`、`build-templates/`、`settings/` 的内容哈希，和本次用的 `--keep-webp-exception` 原因 `options`）。跑完再构建；构建后又改了这三个目录，要重跑 `source` 再构建，否则写包入口拒绝（K5）。旧游戏源码段只写 App ID，也必须跑。
   - 游戏脚本和平台包模块同名（Cocos 2.4 的模块名全局唯一，MabelsMeadow r8 自带 `assets/scripts/platform/TikTokMissionService.js`、`MissionFlow.js`，Creator 因此报 Filename conflict）：新游戏由 `kit_sources` 把游戏那份连 `.meta` 移到 `<工程>/.tiktok-kit/removed/<原路径>`，警告 `K_W_kit_module_duplicate`，游戏里 `require` 这个名字时加载的就是平台包模块；旧游戏只警告。还同名就是 `K_kit_module_duplicate`（新游戏拦，旧游戏警告）。
3. **产物段，在写包入口里**：`make_tiktok_zip.py` 和 `build_checked_zip.py` 先查源码段记录（K5，被拒时构建目录一个字节都不改），再在任何门禁之前调用 `finalize_native`（取代 v7.5 的 `adapter_fix.apply`），原地改 `--native` 构建目录，顺序 `adapter → startup → touch → storage → login → appid → png → structure`。移走的文件放 `<构建目录的上一级>/.tiktok-kit-removed/<构建目录名>/`，不进 ZIP。两个写包入口都必须给 `--project`：`build_checked_zip.py` 不给时命令行报错（退出码 2）；`make_tiktok_zip.py` 不给时被它原有的参数检查拒绝（退出码 2，要求同时给 `--review`、`--project`、`--web`、`--build-tag`），都在 finalize 之前。写包报告的 `finalize.table_markdown` 是一张中文小表（标准件、结果、改动文件数、警告数），收据的 `finalize.table` 是同一张表，交付回复直接贴这张表；结果写 `已装（插加载行）` 表示文件本来就是平台包的、本次只插了加载行。收据升到 schema 2：没有 `finalize`、`finalize` 有拦截、用过 `--policy`、`finalize` 改过的文件和 ZIP 对不上，都算“非官方入口”，`prepare_delivery.py` 拒收。**v7.6 写的收据在 v7.7 一律不再是官方入口，交付前要用 v7.7 写包入口重新出包。**
   - 游戏自己的打包步骤（例如 MabelsMeadow 的 `scripts/prepare-native-package.py` 把 `config/*.json` 放到包根）不是标准件，仍归这款游戏负责：在写包入口之前对构建目录做完，finalize 不替它做。
4. **单独查看**：`tiktok_finalize.py decide --project <工程>`（或 `--native` / `--zip`）写出判成新游戏还是旧游戏、为什么；`tiktok_finalize.py native --native <构建目录> --project <工程> --board …` 单独跑产物段。`--policy new|legacy` 只给测试和校准用，写包入口不接受（只读的 `check_package.py` 有这个参数，也只给测试）；用它做出的源码段记录会被 K5 拒绝。
5. 同一工程连跑两次，第二次 0 改动（pngquant 结果有缓存 `<工程>/.tiktok-kit/png-cache.json`，pngquant 版本或参数变了缓存作废）。缺 `pngquant` 就拒绝，不跳过。

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

A1 和 G1k 认平台包件时，文件名和 `KIT_MANIFEST.json` 里的指纹都要对上（2.4 模块或 3.x `.plugin.js`），只有平台包的名字、没有平台包代码的不算；只算真正的调用（`.x(`、`.x.call(`、`['x'](`），方法定义和字符串不算。

新警告：`K_W_own_startup_kept`（自写启动件拿不掉，或包里别的文件还 require 它，`evidence.required_by` 写明是谁）、`K_W_kit_module_duplicate`（源码段移走了和平台包模块同名的游戏脚本）。`check_package.py` 只给 ZIP、`prepare_delivery.py` 收包时，都从包里的 uuid 判新旧。

源码段的件（2.4 模块、3.x 插件脚本）不在包里比哈希（Creator 构建可能压缩或改名），由源码段 `kit_sources` 在工程里逐字节核对，再由 K5 证明源码段跑过。运行时探针（触摸探针、`startup` 套件、10 个广告用例）照常必跑，证明“装上了也真的生效”。

## 新游戏和旧游戏

- **规则（Saul Q1，2026-10-29）**：平台包里有一份冻结的遗留名单 `remake-core/assets/platform-kit/LEGACY_GAMES.json`，只有 Skill 发版才能改。**不在名单上的游戏都是新游戏**，包括正在做、还没交付过的游戏。
- **怎么认**：按场景 uuid 认，工程里读 `*.fire.meta` / `*.scene.meta`，只有构建产物时读各 bundle 的 `config.json`。名单只存本游戏独有的 uuid：在两个以上启动包里出现的、两款以上游戏共有的都去掉；只在一个启动包里出现的保留（启动包工坊里放着英化游戏的原版源码，全去掉这些游戏就认不出了），所以用这类启动包起的新项目也带着名单游戏的 uuid。独有场景 uuid 重合 1 个，或独有资源 uuid 重合至少 5 个且占所存的 20% 以上，就是名单上的那款游戏。复制工程出新版本不改 uuid，同一款游戏的新版本还在名单上。读不出 uuid 的按新游戏。v7.7.5 起（总表 B27）：工程文件夹正好是名单记下的那款游戏最后一版源码文件夹（`last_package.path`）时也判旧游戏，只认这个文件夹本身，不认上级、下级或别处的副本（剪刀达人、欢乐刮水果靠这条认出来：名单的 uuid 是从包里读的，包里有图片帧这类子资源，工程顶层 .meta 读不到）。
- **标记只能往严里改**：`<工程>/.tiktok-kit/policy.json` 有新游戏标记，就按新游戏，名单也盖不住；没有“标记成旧游戏”的写法。用名单上的游戏（例如英化原版、完结游戏）做底子的新游戏会带着底子的 uuid，所以起项目时必须跑 `init`。现在没有门禁检查起项目时跑没跑 `init`：漏跑时不在名单上的游戏照样按新游戏处理，用名单游戏做底子的会被当成旧游戏。
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
- **现在怎么拦**：`K1_kit_bytes`、`K2_kit_wiring`、`K3_single_layer`（`touch24` / `touch3x`）。2.x、3.x 包都必跑触摸探针（`remake-core/scripts/audit_upload_startup.py` 调 `probe_cocos2_touch_coordinates.cjs` / `probe_cocos3_touch_coordinates.cjs`），探针结果为空也算失败。
- **验收包**：射击高手 v81、Marlows r4、小熊拳击 R27 只给 screenX/screenY 时点不动（拒），装上标准件后能点中；Ingrids r9 只有一层包装。

### 2. 启动和加载（30 款，最多的一类）
- **规则**：一次写对反复出现的 8 个错误：按“多少秒没有新字节”判卡住，不按固定总时长；下载分包接上 `onFileProgress` 显示进度；后台时间不计入超时；每次加载有代次，旧回调作废，Retry 不复用旧队列；每一步失败或卡住都出现最上层、点得中的 Retry，点了重启真正卡住的那一步；首页按钮画出来才算启动完成；首帧前只下首页必需的资源；平台接口缺一个不能拦住启动。
- **标准件**：2.4 用平台包 `build-templates/bytedance/main.js` v1.6（件名 `startup24`；v7.5 起：单文件 10 秒重发、30 秒才判失败、后台不计、每帧最多计 1 秒、场景步骤纳入看门狗、启动异常显示 Retry；v1.3 加：引擎前装 storage-guard、一次静默登录不等结果、WebP 例外时才运行标准探针；v1.4：图片解码看守挂到引擎真正的图片解析函数 `downloader.downloadDomImage` 上，一张图解码一直不回应也会重新请求（v1.2～v1.3 找的 `parser._parsers` 在 2.4 引擎里都没有）；v1.5：单个文件的重发算进度，有文件还在自己的 30 秒里时 10 秒总看守不出 Retry，所以一个卡住的文件只在真失败时出 Retry，重发后首页出来时不会再压着 “Load failed”；v1.6：启动场景反序列化之后因为一张图超时失败时，Retry 先从引擎文件缓存 `cc.assetManager._files` 里删掉这个场景再重新加载，第一次点 Retry 就能进，v1.5 及以前第一次 Retry 会马上又失败，调试版引擎报 `Can not deserialize the same JSON data again`，正式版报 `TypeError`）。3.x 平台包没有启动件（Q5），`webp-probe/cocos3.x-reference/boot-loading.js` 只作参考。
- **出包时怎么装**：重塑 2.4 新游戏源码段把 `build-templates/bytedance/` 换成只有平台包的 `main.js`、`touch-coordinates.js`、`storage-guard.js`（其他文件移到 `.tiktok-kit/removed/`）。产物段 `startup` 步：新游戏的产物 `main.js` 不是平台包的（英化工程、旧版平台包）就换成平台包 `main.js`，但只在清单 `startup24` 的 `engine_versions` 列出的引擎版本上换（2.4.4、2.4.6、2.4.13、2.4.15，前三个在模拟宿主里实测过首页和第 1 关）；其他版本保留编辑器 `main.js`，警告 `K_W_startup_engine`。装平台包 `main.js` 时包根同时放 `webp-decode-probe.js`（只放脚本，见 16 件表）。自写启动件（`native-load-guard` 一类）的加载行能整句注释掉就注释并移走文件；拿不掉的（用回调包着引擎、加载结果赋给了变量）或包里还有别的文件 require 它的，保留，警告 `K_W_own_startup_kept`，交给本游戏会话。旧游戏不替换，警告 `K_W_own_startup`。3.x 只核对、不安装。
- **现在怎么拦**：`K1_kit_bytes`（含平台包 `main.js` 要的 `webp-decode-probe.js`）、`K2_kit_wiring`（`startup24`：`game.js` 正好 require 一次 `./main`）。用本机 Creator 2.4.15 出包的重塑工程，`build-templates/bytedance/` 缺平台包 `main.js` / `touch-coordinates.js` 或被改过就拒（`audit_platform_kit_required.py`，内含 `check_kit_project.py`）；英化工程（`.tiktok-kit/policy.json` 的 board 是 `localize`，或有 `docs/english/`）的构建模板不再查，这一行改查源码段记录是否新鲜（和 K5 同一个检查），所以英化跑 `preflight.py` 之前也要先跑 `source`。静态门禁：`G3_progress`（大分包不报进度却有短看门狗，拦）、`G5_3x_presubpackage`（3.x 首帧前 await 大分包，拦）、`G6_3x_splash`（重塑拦、其他板块警告）、`G7_file_load_guard`（图片加载 10 秒就判失败，拦）、`W8_prehome_bytes`（进首页前下载超过 15 MB，警告）、`G9_doc_hidden_clock` / `G9_dom_retry`（游戏自写的看门狗用 document.hidden 计时、用网页元素画 Retry，拦；指尖麻将 v57）。运行时：`check_package` 必跑启动套件（`package-check/scripts/runtime_regression/suites/startup`，含分包变慢、下到 40% 卡死、config 失败/卡住、SDK 字段缺失，以及生命周期：加载中时钟跳 12 秒、切后台 60 秒、第一张图不回应后真点 PLAY）和 3.x 的 `startup3x`。3.x 启动件：仍是文档规则，没有真机通过的底子之前不做。
- **验收包**：MabelsMeadow r7 慢速下载、射击高手 v81 启动第二步卡住、DoubleJumpDuo 的 Retry 被遮挡、RestoreLines 2Mbps 下载，在模拟宿主里都必须复现失败；换上标准件后全部出 Retry，点一次就进首页。

### 3. 激励广告计时与卡死（34 款）
- **规则**：按上面“已定口径”第 1 条。锁必须在超时、取消、按 X 时一起清掉“正在播放”并解绑 onClose/onError；`onError` 不能是空回调；切到后台不能取消或结束正在播的广告（TikTok 播全屏广告时游戏会切后台）；广告期间暂停 BGM 和音效，各种结局后恢复。
- **标准件**：平台包 `assets/tiktok-platform/RewardedService.js`（件名 `rewarded`，与 v7.4 逐字节相同），单测 `tests/rewarded-timing.test.js`；3.x 用 `RewardedService.plugin.js`（`rewarded3x`，游戏里调 `globalThis.TikTokKit.RewardedService`），同一套计时用例。游戏只调它，不再自写广告服务。
- **出包时怎么装**：源码段 `kit_sources` 让工程里的平台包广告服务和清单逐字节相同（新游戏缺了补上、改过恢复；旧游戏只报差异）。游戏的发奖函数接到哪里，脚本不改，由模型接、由 10 个广告用例验。
- **现在怎么拦**：`check_package --ad-regression <qa/ad-regression.json>` 的 10 个广告用例必跑，有激励广告却没有适配文件或任一用例失败就出不了包（`build_checked_zip.py`、`prepare_delivery.py` 同样接收）。`A2_hide_kills_ad`：重塑拦、其他板块警告。`A1_rewarded_outside_kit`（平台包以外直接调 `createRewardedVideoAd`）：新游戏拦，旧游戏警告。BGM/音效暂停只进警告。
- **验收包**：10 例广告回归全过（late16 不发奖、bgload 回来看完发奖、long200 发奖、nocallback 30 秒有 X 且下一次马上能用）；任挑一款自写广告服务的旧包（如 SimonsScrew R14）必须被拦，换成平台包后通过。

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
- **现在怎么拦**：`K_S_webp`（新游戏构建产物里有 `.webp`，拦；例外且装了标准探针才放行；旧游戏警告）；`IMG0_source_images`（源码段拒绝：WebP 缺 `.meta`、脚本按带 `.webp` 的文件名引用要转换的图、要求带透明的图转 JPG、`image-overrides.json` 写错、改完自检不过；新游戏源码段转换图片或关 WebP 压缩时，`assets/` 下 `.json`/`.ts`/`.js`（不含 `.meta`）里写死 `".webp"`，或 `.json` 里以 `.webp` 结尾的路径，按文件拒绝并给出行号，要改成 `.png`/`.jpg`，finalize 不改游戏数据（Marlows R6 的 `"imageExt": ".webp"` 过了所有门禁，构建后 19 张图加载失败）；同一处同时列了 `.png`/`.jpg` 的格式列表、远程 URL、`assets/tiktok-platform/` 不报；旧游戏和 WebP 例外只警告；源码段有拒绝项时写包入口按 K5 拒绝）；`K_S_zero_byte`、`K_S_outside_path`（新旧都拦）；`W_duplicate_files`（只报告可省多少字节）；`G4_webp_probe`（包里有 .webp 却没有启动链里的真解码探针，拦）；平台包工程里有 .webp 就拒（`check_kit_project.py`）；体积由 `upload_size_gate` 拦（总包 30 MB、主包和每个分包 4 MB）；英化新图单张超过 800 KB 拒、超过显示尺寸 2.5 倍列出（`audit_new_english_images.py`）；源码阶段估包体（`audit_package_estimate.py`）；英化每张图要有复核记录（`audit_image_review_record.py`）。已知：3.x 自己下载解码 WebP 的游戏（Marlows R5）会被 G4 误拦，要改成按“美术怎么加载”判断。
- **验收包**：Nanas（57.8 MB）、音乐消消乐原包经出包处理后在 30 MB / 主包 4 MB 以内；Basil、MabelsMeadow 包里 0 张 WebP，模拟“canvas 导不出 WebP”（`webp=encoder_png`）时也没有 3121。

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
- **标准件**：首页分区规则见 `remake-art`（重塑包）；官方宿主 `package-check/scripts/ad_regression/host.js` 提供胶囊位置。
- **现在怎么拦**：Credits/About 窗口拒绝出包（`audit_no_ad_simulator.py`，`check_package` 一次列出）；重塑首页分区（设置在顶行、PLAY 下面只放回访和加桌面）由 `audit_ui_coverage.py` 判不通过。胶囊几何检查（运行时套件挪到下一版）、启动包和重塑模板源头删掉 Credits：仍是文档规则，计划做成出包硬拦截。美术素材只用 CC0 写在 `remake-art`，也只是文档规则，没有门禁。`known-issues.json` 的 ART-05 还写着“左上或右上”，以本页“左上”为准。
- **验收包**：Mabel r7 两种屏幕都报压胶囊、r8 不报；拇指弹球 v5 拒、v6 过；CindersDragon v3.1、Marlows R5 底排多按钮拒，v3.2、R6 过；Pinecone 原包的 Credits 和底排 4 个方框在模板改过以后不再出现。

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
- **现在怎么拦**：`audit_page_richness.py` 的 `two_video_buttons`（同一屏两个看广告按钮）；10 例广告回归。复活和 x2 的运行时用例：仍是文档规则，计划做成出包硬拦截。
- **验收包**：方块迷阵 v6（复活和 x2 同一弹窗）失败、v6.1 通过；MusicSlice 原包找不到 x2 失败、v30 通过；方块冲冲 BUGFIX5（没有复活）失败、BUGFIX6 通过；拇指弹球 v5 复活后 BACK 不见失败、v6 通过。

### 3. 弹窗布局、空位、提示挡操作区（17 款）
- **规则**：删掉入口后同一组剩下的按钮要重排，不留空位和无效点击区；提示文字不压玩法区、触摸区、按钮和常驻 HUD，最多两行。
- **现在怎么拦**：英化固定入口已写“删后重排”。按钮间距检查和提示遮挡检查：仍是文档规则，计划做成出包硬拦截。
- **验收包**：射击高手 v84 设置页间距 200/100 报出、v85（都是 115）不报；JaspersKelp r6 的取消提示报“压住 SwipeZone / 三行超过两行”。

### 4. 源码和上传包对不上（21 款）
- **规则**：上传包只能从源码经官方写包入口（`make_tiktok_zip.py` / `build_checked_zip.py`）出；直接改包必须带补丁脚本，对源码和包打同一组改动、每处正好命中一次，并写进源码说明。
- **现在怎么拦**：两个写包入口都写 `<zip>.receipt.json`，没有回执的 ZIP 标“非官方入口”，`prepare_delivery.py` 拒收；`prepare_delivery.py` 比对 `logic_check` 报告里的源码哈希和交付源码。v7.7 起写包入口还查 `K5_source_finalized`（源码段之后工程没改过）和 `K4_finalize_ran`（产物段写的文件和包里一致），收据升到 schema 2、带 `finalize` 记录；v7.6 写的收据不再是官方入口，要用 v7.7 写包入口重新出包。v7.7.4 起 `verify_native_zip.py` 和 `upload_preflight.py` 单独运行时也拒收没有匹配回执的 ZIP（退出码 3 / refuse；DriftRacer v2 就是只跑了这两个、带着旧版广告服务交的包），只看结构加 `--structure-only`。v7.7.5 起 ZIP 改了名也认：同名回执不在时，在同一文件夹里找为这份 ZIP 字节写的回执（官方写包入口写的、`zip_sha256` 相同），内容改过一个字节就找不到。build-templates 和包根文件逐字节比对、补丁脚本要求：仍是文档规则，计划做成出包硬拦截。
- **验收包**：Basil fix1、fix2 配 0.4.0 源码被拦；Marlows R6 配 R6 源码通过；方块冲冲原包配现在的源码被拒、`方块冲冲tk.zip` 通过。

### 5. 英化固定清理：分享、更多游戏、排行、跳转、国内统计（10 款 + 统计 2 款）
- **规则**：按“已定口径”第 3 条处理分享；更多游戏、排行榜、跳转其他小程序的入口和调用删干净，删后重排；国内统计上报（腾讯 MTA 等）删掉。组件被预制体引用时保留同名字段、清空行为，不直接删类。
- **现在怎么拦**：`H14_cross_promo`（真调到跳转/更多游戏，拦；空壳目前也拦）、`H13_analytics_domain`（统计域名，拦）、运行时网络套件（清单外请求，警告）、`audit_share_entries.py`、`audit_no_social_features.py`（一键预检）。
- **验收包**：射击高手 v81 拒、v83 过；甜点消消乐、MabelsBus r5 拒；细菌2048 原件分享换提示被拦、v3 过；MusicSlice 的 mta 故障变体拒、v30 过。

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
- **现在怎么拦**：`logic_check.py` 的 `L-MODAL-PAUSE` 只提示。玩法状态运行器：仍是文档规则，计划做成出包硬拦截。细则见 `/Users/sijunting/Downloads/！自制游戏/启动包工坊/！Skill更新/发给Skill制作_沉淀方块冲冲与横向12款玩法状态问题_复制这段话.txt`。
- **验收包**：方块冲冲原包被拒、`方块冲冲tk.zip` 通过；回家快跑现有源码在监听注销和体力上失败。

## 第三部分：不写死的单款问题

玩法 bug（穿模、物理、判定）、难度和经济数值、美术音频动画观感、字体缺字和浅色字、多点触摸和触摸区域：和每个游戏的内容有关，按 Saul 记在各板块 Skill 里的偏好检查，不做成固定件。

## 第四部分：不要做

1. 不要再在每个游戏里各写一份触摸、启动、广告、存档、任务代码，哪怕只是“照抄平台包”。直接引用平台包文件。
2. 不要把第一部分做成“检查出来再让模型修”。目标是出包时自动装上，再确认装上了。
3. 不要因为旧游戏自写的启动链、广告代码能用，就自动替换。只对新游戏强制，旧游戏给警告，交给各自的会话。
4. 每做成一条硬拦截，都在完结游戏里抽 3 款（至少一款 3.x）跑一次，确认不误拦好包。检查工具自己也会误报漏报（33 款碰到过），探针报错不能说成包不合格。
