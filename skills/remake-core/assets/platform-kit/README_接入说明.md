# TikTok 平台包 2.0（Cocos Creator 2.4.15，重塑/自制游戏专用；3.x 插件版见第七节）

2.0（2026-10-29，重塑 Skill v7.7）：出包时由 `tiktok_finalize` 自动装上标准件，再由门禁 `kit_parts` 直接读包里的字节证明装上了（第六节）。新增存档层 `parts/storage-guard.js`、首页双入口组件 `HomeGrowthEntries.js`、启动件 `main.js` v1.6（v1.3：装存档层、一次静默登录、WebP 例外时才加载标准探针；v1.4：图片解码看守接到 2.4 真正的图片解析器，场景出来后再点 Retry 不会把加载遮罩盖回去；在 2.4.4 / 2.4.6 / 2.4.13 真包上宿主实跑通过，finalize 在这四个版本上都换平台包 `main.js`；v1.5：数字不变，单个文件重发算进度，文件还在自己的 30 秒里时 10 秒总看守不出 Retry，所以卡一个文件只在它真失败时出 Retry，重发后进了首页也不会压着 "Load failed"；v1.6：启动场景因为图片超时加载失败后，第一次点 Retry 就能进场景，以前第一次 Retry 一定马上又失败、要点第二次）；平台包 `main.js` 总是带着 `webp-decode-probe.js` 一起放进包根（只放脚本，不放探针图、不插开关行，不开 WebP 例外时它不执行）；`KIT_MANIFEST.json` 加 `parts` 段，是所有哈希的唯一来源。

v1.1（2026-10-27）：卡住判定 20 秒 → 10 秒（skill 规定 10 秒无进展必须出 Retry）；放进重塑 Skill 的 `remake-core/assets/platform-kit/`，原样用平台包的游戏不再单独做 Retry 专项测试。

**必须遵循（Saul 2026-10-29）**：每个 TikTok 游戏都按 [TikTok 固定适配](../../../cocos-game-check/references/tiktok-fixed-adaptation.md) 做；本包就是那页说的“标准件”，新游戏直接引用，不手写、不另抄一份。

这一包是每个自制游戏都一样的 **TikTok 部分**：启动加载、激励广告、桌面快捷方式、个人主页回访、存档。
玩法、美术、关卡、货币数值都不在这里。

**规则只有一条：除了 `PlatformConfig.js`，其他文件整份复制，一个字都不改。**
要改就改平台包本身，升版本号（1.1 → 2.0），重新跑测试，再发给所有游戏。

---

## 一、包里有什么、从哪来

| 文件 | 作用 | 来源 | 状态 |
|---|---|---|---|
| `assets/tiktok-platform/PlatformConfig.js` | App ID、广告位、存档名、B（加桌面/回访奖励 5B） | 新整理 | **每个游戏只改这一个** |
| `assets/tiktok-platform/RewardedService.js` | 激励广告：每次新建、只有看完才发奖、防叠开；只在请求阶段 15 秒超时（切后台不计），开播后不判超时，开播 30 秒无回调时 `onExitAvailable` 通知显示 X、`exit()` 收尾，超时或按 X 后解绑旧回调并立刻放开下一次请求；游戏切后台/回前台时调 `onHide()`/`onShow()` | 以 SnakeVSBlock v32 为底，v7.4（2026-10-28）按 Basil 超时规则改写 | Snake 回归用例 + 出包前广告回归（Marlows r5 10/10）通过 |
| `assets/tiktok-platform/TikTokMissionService.js` | 快捷方式/回访的 4 个 TikTok 接口 | SnakeVSBlock v32，逐字节相同 | 已在 Snake 中通过 |
| `assets/tiktok-platform/SaveStore.js` | 存档：一个 key、一个字符串、写后读回比对；v7.5：读回 true/false/undefined 或抛错时，用 `getStorageInfoSync().keys` 判断有没有这个 key，没有就是新存档（写默认值），不再报 \"Saved value is unavailable\"；读档后发一次登录（不等结果，失败或没有接口都不影响任何流程） | 平台包新写 | Node 测试通过，**待第一次扫码** |
| `assets/tiktok-platform/MissionFlow.js` | 主页两个按钮的完整流程（不画界面）；v7.5：判断是不是真机用和 `TikTokMissionService.js` 一样的顺序（TTMinis.game / tt / wx），只有 tt 的环境不再显示 LOCAL PREVIEW；2.0：不给 `reward` 时自己按 `growthReward()`（5B）加到 `coins`，文案 `+N Coins` | 平台包新写 | Node 测试通过，**待第一次扫码** |
| `assets/tiktok-platform/HomeGrowthEntries.js` | 2.0 新增：首页底排两个固定入口（Add to Home / Profile Revisit）。奖励只读 `growthReward()`，没有改数额的参数；没有 TikTok 运行环境时入口仍可见，点按不显示说明；图标缺失或 2 秒没加载出来就显示文字；请求中的连点合并成一次 生成时预防 N、N2 批起：init 后下一帧按首页按钮和带触摸监听的可见节点的包围盒自动摆两个入口（半屏以上的背景和遮罩不算），放不下报错不动；首页再加按钮后调一次 `placeEntries()`；`init(store, {place:false})` 关掉 | 平台包新写 | Node 测试通过，**待真机复测** |
| `build-templates/bytedance/main.js` | 启动：每一步失败或卡住都在 20 秒内出可见 Retry，10 秒没进度就提示；v7.5：包内每个文件 10 秒没结果再请求一次（先到的结果为准），30 秒算失败，切后台不计时、每帧最多计 1 秒；启动异常会被接住并显示，不会停在 \"Starting...\"；v1.3（2.0）：触摸修正之后装 `storage-guard.js`（出错不挡启动），启动时发一次静默登录（不等结果），只有包里设了 `__TIKTOK_KIT_WEBP_PROBE__ = true` 才加载 `webp-decode-probe.js`；v1.4：图片解码（小游戏里图片在解析这一步才真正解码，`downloader.downloadDomImage`，引擎没有超时）也按同一规则 10 秒重发、30 秒算失败；v1.2～v1.3 找的 `parser._parsers` 在所有 2.4 引擎里都不存在，这一半以前没生效；场景已经出来后点到迟到的 Retry，只关掉加载提示，不再盖一个一直不消失的 "Loading 95%"；v1.5：10 秒重发、30 秒失败、后台不计时这几个数字不变，单个文件重发算进度，而且有文件还在自己的 30 秒里时，10 秒总看守等它（它 10 秒重发、30 秒失败，失败会经这一步的出错回调出 Retry）：卡一个文件只在它真失败时出 Retry，重发后进了首页不会压着 "Load failed"（v1.4 两个 10 秒同时到期，宿主每秒约 1 帧时 Retry 先弹出）；v1.6：启动场景的 JSON 已经反序列化、它用的图片超时导致场景失败时，引擎把这份已被改写的 JSON 留在文件缓存（`cc.assetManager._files`）里，场景又不进解析缓存，下一次加载就拿它再反序列化一次，马上失败（调试版引擎报 \"Can not deserialize the same JSON data again\"，去掉这条调试检查的正式版报 `TypeError: Cannot read properties of undefined (reading '0')`），所以以前第一次 Retry 一定失败、第二次才进得去；Retry 重新加载场景前先从缓存里删掉这一项（2.4.4 / 2.4.6 / 2.4.13 / 2.4.15 引擎这段代码相同），计时数字不变。`main.js` 第 33 行在开关里 require `./webp-decode-probe`，静态启动依赖检查不看 `if`，所以 finalize 装平台包 `main.js` 时总是把 `webp-decode-probe.js` 一起放进包根（`KIT_MANIFEST` 的 `startup24.extra_files`，K1 查它的哈希）  | MetalMaster r5 + 1 行触摸修正，v7.5 按射击高手2048 v82 的加载守卫改写 | Node 测试通过，**待真机复测** |
| `build-templates/bytedance/touch-coordinates.js` | TikTok 触点只有 screenX/screenY、Cocos 2.4 读 clientX/clientY：不装就按钮点不动（必装，探针校验）；v7.9 起切后台时还按着的手指在 EVENT_HIDE / EVENT_SHOW 时取消，回来后第一下不丢 | 坐标部分是 StarPop v50（`1aeb690c…`，逐字节相同，现在记为旧版本）；取消手指的部分是甜点消消乐 R48 的 `touch-lifecycle-reset.js`。注意：躲雨小鸭 v20、射击高手 pkg85 用的 `0369875d…` 是另一份代码，不是这个文件 | 坐标部分：StarPop v50 没有找到扫码确认记录，**待真机复测**；取消手指：R48 Saul 手机验收过，模拟宿主里割草 v015 从拒到过 |
| `parts/storage-guard.js` | 2.0 新增存档层：写入一律存文字（数字、布尔转成字符串）；读到 null/undefined/''/false/true 时用 `getStorageInfoSync().keys` 判断键在不在，不在就当新玩家（返回 null）；读出对象原样给；SaveStore 的键原样读（SaveStore 自己判断坏档）。工程里放在 `build-templates/bytedance/storage-guard.js`（`KIT_MANIFEST.json` 的 `project_path`），由 `main.js` 在游戏脚本之前装上 | 射击高手2048 v85 的 `storage-guard.js` + TobinsGem/Tansys 的键列表判断 | Node 测试通过，**待真机复测** |
| `parts/PhysicsClock.js` | v7.8 新增：Cocos 2.4 物理按真实时间走（`enabledAccumulator = true`），给推力按时间缩放的 `Clock.force(v, dt)` / `Clock.scale(dt)`。用了 2.4 物理的**新游戏**由 `tiktok_finalize.py source` 自动装到 `assets/tiktok-platform/PhysicsClock.js`，老游戏不装（见第十节） | 平台包新写（全民飞车漂移 v3.1 在 120 帧屏幕上起步 1 秒多跑 19.9%） | Node 测试通过（`tests/physics-clock.test.js`），**待真机复测** |
| `parts/CourseLane.js` | v7.8 新增、**按需用**：滚动障碍的出生位置、回收时机、要几组、复活怎么清障，全按引擎真实可见范围算（宽屏、上下黑边都对）。2.4 和 3.x 同一个文件（见第九节） | 平台包新写（BreezyBalloon v2.1 按设计宽度回收柱子，宽屏上柱子在屏幕中间凭空出现） | Node 测试通过（`tests/course-lane.test.js`），**待真机复测** |
| `parts/CapsuleLayout.js` | v7.8 新增、**按需用**：读 `tt.getMenuButtonBoundingClientRect()`，自己判断返回的是点还是像素（Saul 的 iPhone 14 返回的是像素），换算成界面世界坐标（含上下黑边），给顶栏、设置钮这些贴着胶囊的节点用。2.4 和 3.x 同一个文件（见第八节） | 平台包新写（全民飞车漂移 v2、SpiderSwing、Hollys、FoxDenDash 都是拿原始值摆顶栏，按像素返回时顶栏掉下去） | Node 测试通过（`tests/capsule-layout.test.js`），**待真机复测** |
| `parts/GameUIKit.js` | 生成时预防 P05 新增（Cocos 2.4）：所有新做或改动的弹窗、按钮、提示条、位图数字都用它，不手写。`tiktok_finalize.py sync` 给新游戏装到 `assets/tiktok-platform/GameUIKit.js`（见第十一节） 1.1.1（A2、A3 批）：暂停 / 复活 / 结算 x2 页面模板、`valueLabel`、`adoptPopup`；3.x 版 `parts-3x/GameUIKit.ts` 由 `tools/make_gameuikit_3x.py` 从 2.4 核心逐字节生成（`--check` 可验），3.x 版由 `sync` 装到 `assets/tiktok-platform/GameUIKit.ts`（R4B） | 由 ad-boost `AdBoostKit` 1.2.0 去掉广告部分而来，加了 `UI.button`、`UI.wrapExisting`、`popup.guard` | Node 测试通过（`tests/game-ui-kit.test.js`，10 条，每条带照旧手写的反例），**待真机复测** |
| `parts/RunSession.js` | 生成时预防 G 批新增、**新游戏写玩法必用**：一局的状态只放 `session.state`，开局/Retry/下一关 `newRun`；回调用 `guard`/`once`；定时用 `after`/`every`；暂停按原因 `pause(reason)` 返回 `release()`；切后台自动暂停；移动用 `move(node, vx, vy, dt)`；`adHooks()` 接 ad-boost。2.4 和 3.x 同一个文件（见第十二节） | 平台包新写（割草分数、Pinecone 复活次数、大西瓜旧回调和 setInterval、甜点消消乐暂停布尔） | Node 测试通过（`tests/run-session.test.js`），**待真机复测** |
| `parts/FxPool.js` | 生成时预防 G 批新增、**新游戏必用**：特效、子弹、飘字从池里取，播完自动回池，节点数有上限；开发版 `FxPool.devWatch(cc)` 在 update 里造节点、场景节点一直涨时警告。2.4 和 3.x 同一个文件（见第十二节） | 平台包新写（方块迷阵 120 次合并剩 86 个空特效） | Node 测试通过（`tests/fx-pool.test.js`），**待真机复测** |
| `parts/ShopTx.js` | 生成时预防 R4L3 新增、**新游戏经营类必用**：买、做、退都进事务，开始取快照、期间锁按钮、结束一次 `SaveStore.grant`、取消只扣已用掉的；`catalog` 拦重复示例行。2.4 和 3.x 同一个文件（见第十九节） | 平台包新写（喵咪小吃铺 4 条） | Node 测试通过（`tests/shop-tx.test.js`），**待真机复测** |
| `parts/AudioService.js` | 生成时预防 H 批新增、新游戏的声音都用它：music 和 sfx 各自开关和音量（存进 SaveStore 的 `audio` 键）、播放前查开关、首页第一帧画出来以后才加载音频、看广告时静音并恢复玩家自己的音量、同一音效 80 ms 内不重复播；读设置不改任何开关。1.1（F2 批）只经 `ResKeys` 加载，过平台包资源扫描。1.2（R4E）：没调 bindFirstFrame 时首页第一次播放后 5 秒兜底开播。2.4 和 3.x 同一个文件（见第十三节） | 平台包新写（搭桥小能手打开音乐面板就解除静音、音效加载完越过静音） | Node 测试通过（`tests/audio-service.test.js`，8 个旧写法反例），**待真机复测** |
| `parts/ResLoader.js` | 生成时预防 F 批新增：只收资源表 `ResKeys` 里的常量，类型由表定；每次加载一定有结果（前台 10 秒重发、出错重试一次、30 秒失败，后台不计时）；首页必需图 `Res.loadAll`，其余图 `Res.sprite`（先放占位、失败可重试）。1.1（F2 批）自己不再调引擎加载，用 `make_res_keys.py` 写进每条的 `request(cb)`。2.4 和 3.x 同一个文件（见第十五节） | 平台包新写（反例：甜品消除大师 v11 的 ResMgr） | Node 测试通过（`tests/res-loader.test.js`），**待真机复测** |
| `parts/rewarded-guard.js` | 生成时预防 D 批新增、激励广告平台层兜底：同一时间只放一个 `show()`、到开播最多 15 秒前台时间、作废的那次迟到回调不再转给游戏；`RewardedService.js` 自己创建的广告带 `__tiktokKitRewardedDirect` 标记直接放行（D2 批）。**R4A 起由 `main.js` v1.7 自动装（新重塑工程 `build_templates` 放进 `build-templates/bytedance/`，英化原生包由启动件带上），不要手改、不要手动复制**；出包检查按 KIT_MANIFEST 哈希认它，不算游戏调广告（见第十六节） | 生成时预防 D、D2、F2 批；夹具来自埃及宝石、拇指弹球 v6、搭桥小能手 | Node 测试通过（`tests/rewarded-guard.test.js`），**待真机复测** |
| `parts/ScreenFit.js` | 生成时预防 K2 批新增、**按需用**：背景按引擎真实可见范围铺满（`cover`），顶栏、底排整组进安全区和胶囊下（`safeTop` / `safeBottom`），只开一种 fit。2.4 和 3.x 同一个文件（见第十七节） | 平台包新写 | Node 测试通过（`tests/screen-fit.test.js`），**待真机复测** |
| `parts/TouchOwner.js` | 生成时预防 K2 批新增、**按需用**：拖拽、摇杆、滑动只认第一个手指，touchcancel 和切后台释放；屏幕点按所在相机换算成世界点。和触摸修正件一起用，不替代它们。2.4 和 3.x 同一个文件（见第十八节） | 平台包新写 | Node 测试通过（`tests/touch-owner.test.js`），**待真机复测** |
| `parts/CapsuleAuto.js` | 生成时预防 I3 新增，**新游戏默认装**：`tiktok_finalize.py source` 把它和 CapsuleLayout.js 一起拷进 assets/tiktok-platform/，场景启动后自己把压在胶囊下的顶栏挪下来，不用写调用；英化和老游戏只列出顶栏节点警告 | 平台包新写（普查重叠 64 款 99 次、胶囊遮挡 16 次） | Node 测试通过（`tests/capsule-auto.test.js`），**待真机复测** |
| `parts/host-shim.js` | 生成时预防 B 批新增、宿主接口兜底（2.4 和 3.x 同一份）：`getSystemInfoSync` 缺失或抛错时兜底、补 `SDKVersion`、`canIUse`、`getOpenDataContext`，只补缺的、不覆盖已有的；新代码读版本号用 `parseVersion` / `sdkVersion`。**R4B 起由 `tiktok_finalize` startup 步骤自动装进 `game.js`**（见第十四节） | 平台包新写（躲雨小鸭 v16、射击高手2048 的写法） | Node 测试通过（`tests/host-shim.test.js`），**待真机复测** |
| `parts-3x/boot-guard-3x.js` | 生成时预防 B 批新增、Cocos 3.x 启动看守，规则和 2.4 `main.js` v1.6 一样（单个文件 10 秒重发、30 秒失败、只算前台、Retry 发新请求）。**R4B 起由 `tiktok_finalize` startup 步骤自动装进 `game.js`**（见第十四节） | 平台包新写（TrashPanda、恢复线场、美女快跑的固定 15 秒总期限） | Node 测试通过（`tests/boot-3x.test.js`），**待真机复测** |
| `tools/home_free_slot.js` | 生成时预防 E 批：首页找空位。按首页现有按钮的包围盒找两个平台入口不重叠的位置，放不下就报错；英化游戏原按钮不动。R4G1 起 `--dump` 也躲开 ui_dump 记下的带触摸监听节点（`comps.touch`，代码 `node.on(TOUCH_END)` 挂的，例如 ad-boost 首页入口），不用再传 `--obstacle` | 平台包新写 | Node 测试通过（`tests/home-free-slot.test.js`） |
| `KIT_FINGERPRINTS.json`、`tools/build_kit_fingerprints.py`、`tools/kit_versions/` | v7.8 新增：认出包里脚本合并文件中旧版平台包模块（门禁 K6_kit_module_old）用的特征；改了 `assets/tiktok-platform/*.js` 就重跑 `build_kit_fingerprints.py`，旧版原文按 `<模块>/<sha256>.txt` 留在 `tools/kit_versions/` | 全民飞车门禁原型 C | `remake-core/scripts/test_kit_module_versions.py` |
| `settings/bytedance.json` | 字节构建设置模板：数字 App ID（7683427172773644296 是多款游戏共用的测试组 ID，相同是正常的）、首场景分包关、REMOTE_SERVER_ROOT 空。没有它命令行出包会是 `testappId` | 细菌2048 build2 起验证过的写法 | 检查脚本强制 |
| `webp-probe/cocos2.4/` | 老游戏保留 WebP 时用的标准探针：`webp-decode-probe.js` + `loading/webp-probe.webp`（放主包），用 TikTok 的 createImage 真解码这张图，解出宽高才开 WebP，5 秒没回应算不开、显示 Retry、点了重新检测 | Mabel's Meadow r8，逐字节相同 | `test_webp_decode_probe.cjs` 通过，**待真机复测** |
| `webp-probe/cocos3.x-reference/` | 已有 3.x 游戏的参考件：`webp-probe.js`（`check(cc, sdk, timeout, done)` / `apply(cc, ok)`）、`webp-check.webp`、`boot-loading.js` | LunasJade v0.10.1；v7.5 去掉了 data: 备用 | `test_webp_decode_probe.cjs` 通过，**待真机复测** |
| `tools/check_kit_project.py` | 一条命令检查工程（2.0：还查 storage-guard.js、HomeGrowthEntries.js、`growthReward()` 固定 5B、`normalLevelCoins` 已填） | 平台包新写 | — |
| `tests/` | 全部测试 | Snake 原测试 + 平台包新测试 | 全部通过 |
| `KIT_MANIFEST.json` | `files`：每个文件的 SHA256 和旧版本哈希；`parts`：每个标准件放在包里哪、加载行插在哪、怎么认自写件、新旧游戏各怎么处理；`includes` 引入 3.x 的 `parts-3x/KIT_PARTS_3X.json` | — | 检查脚本、`tiktok_finalize`、`kit_parts` 门禁都只读它 |
| `build-templates/bytedance-mini-game/tiktok-touch-3x.js`、`plugins-3x/`、`parts-3x/`、`tools/make_plugin_scripts.py` | 3.x 用的触摸修正（v7.9 起也在 `tt.onHide` / `tt.onShow` 时取消还按着的手指）和插件版平台包（第七节） | Marlows R6 `marlow-touch.js` 改通用名；插件版由 2.4 模块生成 | Node 测试通过；取消手指在模拟宿主里猴子快跑 v12 从拒到过；**待真机复测** |

---

## 二、构建规则（7 个通过的自制游戏总结出来的共同点）

1. **引擎固定 Cocos Creator 2.4.15**，构建平台选 **ByteDance Mini Game（字节小游戏）**，不要用 Web Mobile。
2. **`assets/resources` 设为 Asset Bundle，压缩类型 ByteDance 选"小游戏分包"**。大图、音频都放这里，主包才能 ≤ 4MB。
3. **WebP 规则（全 Skill 统一这一条）：新游戏图片只用 PNG / JPG，不用 WebP**。（手机能显示 WebP、但引擎的判断说不支持时，引擎会跳过所有 WebP 图，报 3121、卡在加载失败页或首页全空白）**老游戏要保留 WebP，必须带标准探针**（2.4 用 `webp-probe/cocos2.4/`，3.x 参考 `webp-probe/cocos3.x-reference/`），探针解码主包里一张真实的 .webp 文件，不用 data: URI；出包检查（G4）会拦住没有探针、探针用 data: URI 或探针图不在主包的包。本平台包工程里不能有 .webp（`check_kit_project.py` 拒绝）。
4. **ByteDance 构建设置里"首场景分包 Start Scene Asset Bundle"关掉，REMOTE_SERVER_ROOT 留空**。不从外网下载任何东西。工程里必须有 `settings/bytedance.json`（复制平台包的 `settings/bytedance.json`），`appid` 是数字 App ID 并和 `PlatformConfig.js` 的 `appId` 一样；空的、`testappId`、非数字都会被 `check_kit_project.py` 拒绝（改 `settings/builder.json` 对命令行出包无效）。
5. **`build-templates/bytedance/` 里只放平台包的 `main.js`、`touch-coordinates.js`、`storage-guard.js`（2.0）和 `rewarded-guard.js`（R4A，`main.js` v1.7 在存档层下一行装它）**。不放 `game.js`、`game.json`，让编辑器自己生成，这样引擎文件名永远对；放了别的文件，`check_kit_project.py` 给警告，出包前 `tiktok_finalize.py source` 会把它们移到 `.tiktok-kit/removed/`。触摸修正装在 `main.js` 里那一行 `require('./touch-coordinates').install(cc)`，存档层装在下面一行 `require('./storage-guard')(cc, platform)`，触摸探针按真实启动链认它（编辑器的 `game.js` 加载 `main.js`，`main.js` 里有这一行就通过；删掉这一行就拒绝出包）。
   - 不用平台包的老游戏，探针还认：`game.js` 里的同一行；在适配器（`adapter-min.js` / `adapter.js`）之前 require 的 SDK 触摸包装模块 `tiktok-input.js`（Basil 的写法）；或者工程自己命名的模块，在 `game.js` 里加一行声明 `// tiktok-touch-adapter: ./文件名.js` 并在适配器之前 require 它。模块缺失、在适配器之后才装，都判不合格。引擎文件 `cocos/cocos2d-js-min.js`（发布版）和 `cocos/cocos2d-js.js`（调试版）都会被探测，Creator 2.4.5 起转换函数里的闭包变量也已支持。
   - 触摸探针不只管 2.4：`remake-core/scripts/audit_upload_startup.py` 对 Cocos 3.x 包（`web-adapter.js` + `cocos-js/`）也跑 `probe_cocos3_touch_coordinates.cjs`。3.x 包不用本包的 `touch-coordinates.js`，要在 `game.js` 里、引擎加载（`System.warmup`）之前给 `tt.onTouch*` 装坐标修正（例：Marlows r5 的 `marlow-touch.js`、Gimble's v9.1 的 `grotto-touch.js`），只给 `identifier/screenX/screenY/force` 时引擎坐标必须有限、在屏幕内、落在点按位置上。**探针结果为空（`touch_coordinates: null`）不算通过**，认不出引擎触摸转换的 TikTok Cocos 包直接失败。
6. 不调用分享、排行榜、更多游戏（skill 原规则）。
7. 游戏代码不直接调用 `createRewardedVideoAd`、`addShortcut` 这类 TikTok 接口，统一通过平台包。

---

## 三、新游戏怎么接（给 AI 照做）

### 第 1 步：复制

- 把 `assets/tiktok-platform/` 整个文件夹复制到游戏的 `assets/` 下（2.0 起 6 个文件，含 `HomeGrowthEntries.js`）。
- 把 `build-templates/bytedance/` 里的两个文件和 `parts/storage-guard.js` 复制到游戏工程的 `build-templates/bytedance/`（一共三个文件）。
- 把 `settings/bytedance.json` 复制到游戏工程的 `settings/`（已有就核对 `appid`）。
- 2.0 起这一步出包时也会自动做：`tiktok_finalize.py source` 把缺的补上、被改过的换回平台包原文件（旧游戏只报告）。手动复制仍然是起项目时的做法，自动这一步是兜底。

### 第 2 步：改配置（唯一要改的文件）

`PlatformConfig.js`：

- `gameId` 改成这个游戏的英文小写名，比如 `'juicerelax'`。
- `appId`、`clientKey`、三个广告位从电脑上的 `~/.game-skill/ad-config.json` 抄过来（skill 的统一广告配置），不填 Client Secret。
- `placementMap` 里列出这个游戏用到的广告位置，比如 `revive`、`double_coins`、`gift`、`hint`、`skin`。没列出的位置会返回 `unconfigured`，不会乱播。
- `normalLevelCoins` 填本游戏的 B（= `unlock_table.json` 的 `normal_level_coins`）。加桌面、主页回访各发一次 `config.growthReward()` = 5B（Saul 2026-10-29，等于一次首页礼盒基础奖励；没有首页礼盒的游戏也是 5B）。不填时 `growthReward()` 抛错，领奖写入被拒、不发奖也不记已领取，kit 测试里有这条用例。
- 原游戏没有金币的英化游戏（R4O3，Saul 2026-11-04 ECON-SHORTCUT / ECON-REVISIT）：`normalLevelCoins` 留 0，生成首页时 `HomeGrowthEntries` 必须传替代奖励，别手写桥接：`init(save, {reward: function (kind, draft) { draft.energy = (Number(draft.energy) || 0) + 3; }, rewardText: '+3 Energy', onGranted: ...})`（发什么看 `docs/economy/economy_capabilities.json` 的 `no_wallet_substitutes`；没有体力的先加一种金币和皮肤，再按上面发 5B）。有金币时 `reward` 选项不生效，照发 5B。两样都没有时不发奖、不记已领取、不提示存档失败，原因写在 `controller.rewardIssue` 和 `[TikTokKit]` 日志里；写包入口的 `check_kit_project.py` 报 `K_home_entries_no_reward`（工程有 `economy_capabilities.json` wallet false 记录的拦，没有记录的只警告）。用例：`tests/home-entries-no-coin.test.js`。

### 第 3 步：存档（金币和"已领取"必须在同一个存档里）

```js
var SaveStore = require('SaveStore');
var save = new SaveStore({coins: 0, level: 1, skins: {}});   // 默认值
save.load();                                                  // 游戏启动时一次

var data = save.get();                                        // 读：拿到一份拷贝
var r = save.update(function (d) { d.coins += 30; });         // 写：只能这样改
if (!r.ok) showToast('Could not save. Please try again.');    // 写失败：不发奖、不改界面
```

- 一次操作要改的东西（比如扣金币 + 解锁皮肤）放在**同一个 update** 里。
- **存档键和范围由配置表生成，别手写（R4E，蛋壳特工队把等级、地图、VIP、皮肤 ID 写成 999999 后读档抛错或全解锁）**：新游戏每个存档键（含默认值、类型、范围、对应哪张配置表）只写在 `docs/save/save_keys.json`，然后跑 `python3 ../../scripts/make_save_schema.py --project <工程>` 生成 `assets/tiktok-platform/SaveSchema.js`；代码写成 `var S = require('SaveSchema'); var save = new SaveStore(S.defaults, {schema: S});`（3.x 把 SaveSchema.js 勾「导入为插件」，SaveStore 自己读全局 `TikTokSaveSchema`）。读档时越界、类型不对、表里没有的值回落默认值，每个值打一行 `[SaveStore] schema:` 日志；列表、字典只去掉坏的那几项。**新加存档键时同一步改 save_keys.json 再跑一次**；改了配置表也要再跑。出包前 `make_save_schema.py --project <工程> --check` 必须退出 0（过期会报），它也列出代码里 `draft.X =` 写了但 save_keys.json 没登记的键。没有 schema 的老游戏和英化游戏行为不变。测试：`python3 ../../scripts/test_make_save_schema.py`、`tests/kit.test.js` 的 `schema_*`。
- **零件自己建的状态对象，子键登记时必须写 `"in_defaults": false`（R4J1，广告skill ad-boost v1.2.17：登记子键会让新存档带上半个对象，签到第 1 天奖励没了、首页礼盒先冷却 30 分钟、0 体力开局）**：签到 `checkin.state.*`、礼盒 `gifts.*`、体力 `energy.*`、各板块的 `round` / `board` 这类由 CheckinFlow、GiftCenter、Energy、norm() 自己建的键，只校验、不进新存档的默认值；父键写了 `"in_defaults": false`，下面的子键自动跟着，可以不写 default（坏了就删掉，零件自己重建）。可能是 null 的值写 `"nullable": true`（签到 `last_day`、转盘 `pending`、复活标记 `run`），整个对象只查「是对象」用 `"type": "object"`。用到这三样的 schema 是第 2 版，工程里的 SaveStore.js 比它旧时 make_save_schema.py 拒写。
- **每天都能领的奖，领奖 id 里写上日期（R4J1）**：`grant()` 把 `online-ladder:`、`timer-chest:`、`coin-ad:`、`gift:home:`、`offline:quick:`、`quest-x2:daily:` 开头、带 `YYYY-MM-DD` 或毫秒时间的 id 在那天过去 7 天后清掉（同一次写入），一年不再攒几千条；不带日期的 id（`gift:chest:L6`、关卡首通）和别的前缀照旧永久保存。同一天重试、迟到的回调仍然只发一次。改前缀用构造参数 `grantDayPrefixes`，`[]` 关掉。测试：`tests/kit.test.js` 的 `grant_daily_ids_*`、`grant_pruning_*`、`schema2_*`。
- `r.ok` 是 false 时，存档和内存都没变，游戏当作没发生。

### 第 4 步：激励广告

```js
var RewardedService = require('RewardedService');
var ads = new RewardedService();              // 整个游戏只建一个

// 结算页"看广告 ×2"按钮
var panelAlive = true;
ads.request({
  placementKey: 'double_coins', ownerId: 'result',
  isCurrent: function () { return panelAlive && cc.isValid(panelNode); }
}).then(function (r) {
  if (!r.rewarded) { showToast(r.message); return; }       // 取消/失败/超时：每种都有英文提示
  var s = save.update(function (d) { d.coins += doubled; });
  if (!s.ok) showToast('Could not save. Please try again.');
});

// 弹窗关闭时
panelAlive = false; ads.cancelOwner('result');
```

- 只有用户**完整看完**（`onClose` 里 `isEnded === true`）才 `rewarded: true`。
- 浏览器里没有 TikTok，`r.status` 是 `unsupported`，不会发奖。
- 金额怎么算仍用 skill 里的 `AdRewards.ts`，平台包只负责"播广告 + 看没看完"。
- 3.x 开工跑 rewire-ads，原入口自动改到 AdBridge3x.ts；rewire_todo 的 ad / ad_call / ad_handler 行清零；不要写浏览器直接发奖的分支（R4O6；出包 `A3_nonplatform_grant` 新游戏拦、老游戏警告）。
- 原游戏自己的发奖、扣费按 inventory 的 `reward_todo` 改走 `grant` / `ShopTx`：凭证 → 保存读回 → 刷新界面 → 播动画，动画回调里不发奖；x2 只算一次基础整数（R4Q4；sync 的 `reward_order_scan` 只提示不拦）。

### 第 5 步：主页两个按钮

首页保留两个同风格的固定图标按钮 Add to Home Screen 和 Profile Revisit。点一下直接发起对应的平台导航。制作和迁移都移除旧任务面板、提示 Label、文字贴图、toast 和二次点击的绑定。Studio 和普通 Web 同样显示两个按钮。没有对应 SDK、失败、取消或超时都安静结束，入口可以重试。

**Cocos 2.4** 使用 `HomeGrowthEntries.js`，将按钮拖给组件的 `shortcutNode` / `profileNode`。钱包可用后调 `init(save, {onGranted: refreshWallet})`。组件负责点按和冷/热进入监听。图标失效时只用入口名称和原有奖励标识作为备用。

**Cocos 3.x** 使用插件，分别接两处实际触摸回调：

```js
var flow = new globalThis.TikTokKit.MissionFlow({
  store: save,
  render: function () {},
  onGranted: refreshWallet // (kind, data) => 用实际入账后的 data 刷新余额
});
flow.startEntryTracking(); // 钱包可用后即初始化，不等玩家点按钮
shortcutButton.on(cc.Node.EventType.TOUCH_END, function () { flow.open('shortcut', {navigate: true}); });
profileButton.on(cc.Node.EventType.TOUCH_END, function () { flow.open('profile', {navigate: true}); });
// 组件销毁时解除按钮监听，并调用 flow.dispose()。
```

两个导航请求都在原始点击回调内发出。仅从相应入口回来才自动核验资格。只有严格的 `canReceiveReward === true` 且保存成功才更新实际奖励，余额与领取标志一次提交。每项每存档只发一次。已领取仍可打开平台入口。项目配置及无金币项目的奖励替代按原规则接入。

### 第 6 步：弹窗和按钮（生成时预防 P05）

新做或改动的弹窗、按钮一律用 `parts/GameUIKit.js`（`var UI = require('GameUIKit')`），别手写遮罩、淡出、点击和防连点；英化时动过的原版按钮用 `UI.wrapExisting`。写法见第十一节。

---

## 四、检查和测试

```sh
# 检查一个游戏工程（文件没被改、构建规则对）
python3 tools/check_kit_project.py --project /路径/游戏工程

# 跑平台包全部测试（改平台包后必须跑）
node tests/run-all.js
```

测试内容（2026-10-29 kit 2.0，`run-all.js` 13 组全过；v1.4、v1.5 后重跑仍 13 组全过）：

- **Snake 原测试**：广告 + 回访组件 20 项、接口兼容 8 项、4 个故意改坏的反例，证明这两个文件和 Snake 里通过的版本行为一样。
- **存档 + 主页流程**（`kit.test.js`）：33 项，场景来自 skill 记录过的故障（离开再回来、连点、超时、complete-only、存档失败、旧结果覆盖新结果、只有 tt 的真机环境、读档读到 true/undefined/抛错、缺 key 的新存档、登录失败不影响流程……）；2.0 加：SaveStore 和 storage-guard 一起跑结果不变、不传 reward 时按 `growthReward()` 发奖（B 未填不发、可重试）。
- **启动文件**（`boot.test.js`）：43 项（正常启动、分包失败 Retry、分包无响应 10 秒提示、旧回调不重复启动、后台不计时、触摸修正；v7.5 加：包内文件 10 秒重发、30 秒失败、每帧最多计 1 秒、场景出错/卡住出 Retry、启动异常显示 Retry、Retry 跳过已完成步骤；2.0 加：storage-guard 在游戏脚本前装上、登录只发一次且不等结果、登录抛错/失败/没有接口都不影响启动、WebP 探针只在开关打开时加载、每次 Retry 先重新探测；v1.4 加：假解析器按真 2.4 的样子写（处理函数表不公开、同一个 id 的第二次请求并到第一次上），图片解码 10 秒重发、30 秒失败后下一次请求重新解码、后台不计时、出错重试一次、plist 等非图片解析不包、场景出来后的 Retry 不再显示加载；v1.5 加 4 项：每秒约 1 帧时卡一个首页图、重发后进首页不出 "Load failed"，一直卡只在 30 秒文件失败时出 Retry（10 秒、20 秒都不出），文件有结果后 10 秒总看守照常工作，重发本身算进度；v1.6 加 4 项：假引擎按真 2.4 的样子加载场景（场景 JSON 进文件缓存、原地反序列化、依赖失败时缓存不删），场景图片超时后点一次 Retry 就进场景，图片一直卡时 Retry 后不会马上又失败、等图片真失败才再出 Retry，被取代的那次场景失败也会被清掉，正常启动和没有缓存接口的引擎不受影响）。
- **工程检查**（`check-kit-project.test.js`）：19 项（模板通过；App ID 缺文件、没有 appid、空、testappId、非数字、和 PlatformConfig 不一致都拒绝；2.0 加：缺或改 storage-guard.js、缺或改 HomeGrowthEntries.js、5B 改成别的数、删掉 growthReward、B 没填、main.js 删掉存档层那一行都拒绝；build-templates 里的自写件和游戏代码直接调 `checkShortcut` 只警告）。
- **激励广告计时**：8 项，按 v7.4 口径（请求 15 秒只算前台、开播后不计时、30 秒无回调出 X、超时/X/取消后迟到的视频不发奖）：视频 200 秒、16 秒后才开播、播放中切后台、加载中切后台、一直加载不出来、开播后没有回调、取消后迟到看完、isEnded 不是 true。旧的 v7.3 `RewardedService.js` 跑这套会失败 7 项。
- **存档层**（`storage-guard.test.js`）：16 项（读到 null/undefined/''/false/0/true、数字和布尔写入转文字、键列表判新玩家、读出对象原样、装两次只一层、SaveStore 键原样读）。
- **首页双入口**（`home-entries.test.js`）：两键首击直跳、缺能力和失败时无提示、图标文字备用、回访资格及单次入账。
- **3.x**：`touch-3x.test.js` 15 项、`plugins-3x.test.js` 21 项（第七节）。
- **生成时预防（简化.11.13）**：`game-ui-kit.test.js`、`run-session.test.js`、`fx-pool.test.js`、`host-shim.test.js`、`boot-3x.test.js`、`home-free-slot.test.js`，每个都带照旧写法的反例，都进了 `run-all.js`。
- **生成时预防（简化.11.14）**：`audio-service.test.js`、`res-loader.test.js`、`rewarded-guard.test.js`（D2 放行标记）、`screen-fit.test.js`、`touch-owner.test.js`、`capsule-auto.test.js`、`game-ui-pages.test.js`、`game-ui-adopt.test.js`、`home-entries-slot.test.js`、`home-entries-touch.test.js`，都带照旧写法的反例，都进了 `run-all.js`。
- **反例**：存档/流程 14 个、启动 32 个（v1.4 加 4 个：图片解码不包、照旧读 `_parsers`、改成包 `parser.parse` 入口、迟到 Retry 又显示加载；v1.5 加 3 个：总看守不等等待中的文件、等待计数不减、重发不算进度；v1.6 加 3 个：失败的场景不清缓存、按错的 id 清、被取代的那次失败不记）、存档层 8 个、首页入口 6 个故意改坏的版本，测试都会变红（另有 Snake 4 个、3.x 触摸 8 个）。证明测试能抓错，不是摆设。

---

## 五、现在的验证程度（如实）

- `TikTokMissionService.js` 和 SnakeVSBlock v32 逐字节相同，原游戏已扫码通过。`touch-coordinates.js` 和 StarPop v50 逐字节相同，但 StarPop v50 没有找到用户扫码确认的记录，**待真机复测**（2026-10-29 R1 核对；以前写的"已在 StarPop 中通过"没有证据）。`RewardedService.js` 在 v7.4 按 Basil 超时规则改写（见 `remake-ads/references/ad-timeout-and-regression.md`），由 Snake 回归用例和出包前 10 个广告用例证明，还没有新的真机扫码记录。
- `main.js` 以 MetalMaster 已通过的原文件为底，加了一行触摸修正，v7.5 又按射击高手2048 v82 改写了加载守卫和 Retry，2.0 又加了存档层、登录和 WebP 例外开关，**只在 Node 模拟环境测过，待真机复测**。它按 Cocos 2.4.15 编辑器的 `main.js` 约定写；v7.7 在模拟宿主里用 finalize 后的真包实跑过 2.4.4（DotsDelivery v40）、2.4.6（BobbysBeat v22）、2.4.13（射击高手 pkg81）：首页和第 1 关都正常，所以 `startup24.needs.engine_versions` 是这四个版本，finalize 在它们上面都换平台包 `main.js`；其他 2.4.x 保留自己的 `main.js`、只插触摸和存档两行并警告。宿主不等于真机。
- `webp-probe/` 两套探针件都是从游戏包里拿来的（2.4 来自 Mabel's Meadow r8，3.x 来自 LunasJade v0.10.1 并去掉 data: 备用），**都待真机复测**。
- `SaveStore.js`、`MissionFlow.js`、`HomeGrowthEntries.js`、`storage-guard.js`（以射击高手 v85 真机版为底改写）是新写或改写的，只在 Node 模拟环境测过。
- 所有测试都是模拟环境，**不等于手机扫码通过、不等于真实广告能播**。2.0 以后每个新游戏都会自动装上这些件，一处出错就是所有新游戏一起出错；第一款 v7.7 新游戏扫码通过之前，交付回复里写明"标准件待真机复测"。

**所以 2.0 的用法**：先用下一个新游戏接入，上传扫码，测一遍"进游戏 → 点按钮有反应 → 看广告 → 加桌面回来领奖 → 个人主页回来领奖 → 关掉重开奖励和进度还在"。全部正常后，把 `KIT_MANIFEST.json` 里这几项的状态改成"已扫码通过"，之后所有游戏照搬。
如果扫码出问题，只修平台包、升版本号，不要在单个游戏里改。

---

## 六、在重塑 Skill 里的位置（2026-10-27 已接入）

- 平台包放在重塑 Skill 的 `remake-core/assets/platform-kit/`，规则写在 `cocos-game-check/startup` 板块的"防卡住固定做法"。
- 出包门禁：工程原样用平台包（`check_kit_project.py` 通过，打包出来的 `main.js`、`touch-coordinates.js` 和平台包逐字节一致）时，不再要求单独交 Retry 专项证据；"冷启动进首页 → 真实触摸 → 玩法有反应"的启动证明照样必须做。
- 启动包工坊的适配以后单独做；工坊包里带平台包时，要原字节、版本号和 `KIT_MANIFEST.json` 一致。

### 2.0（v7.7）：出包时自动装、门禁证明装上了

- 出包分两段，都由 `remake-core/scripts/tiktok_finalize.py` 做：构建前 `source` 段把平台包文件放进工程（缺的补、改过的换回）、换图片格式、写 App ID；构建后写包入口里的 native 段在 `game.js` 插加载行、放包根文件、压 PNG。两段都只读 `KIT_MANIFEST.json`。
- `parts` 里 2.4 和通用的件：`touch24`（触摸）、`startup24`（`main.js`，含静默登录检查）、`storage24`（存档层）、`webp_probe24`（只在 `--keep-webp-exception` 时装）、`rewarded`、`missions`（MissionFlow + TikTokMissionService）、`home_entries`、`savestore`、`platform_config`（唯一可改）。3.x 的件在 `parts-3x/KIT_PARTS_3X.json`（`touch3x`、`storage3x` 和 5 个插件件），由 `includes` 合进来，名字不能重复。
- 产物的 `main.js` 是平台包原文件时，触摸和存档层由它自己装（`wiring` 里 `when: kit_main` 那条，只核对）；不是时（英化工程、旧游戏），在 `game.js` 的 `__globalAdapter.adaptEngine();` 后面各插一行，行尾带 `// tiktok-kit:<件名>:2.0`，第二次跑看到同一行就不再插。插在适配器之后是因为两个件都要用 `cc`（StarPop v50、射击高手 pkg85 都是这个位置）。
- v7.7 W-F1a：装平台包 `main.js` 时同时放 `webp-decode-probe.js`（只放脚本）；自写启动件还被包里别的文件 require 时不移走、给 `K_W_own_startup_kept` 警告；移走后 `game.js` 里注释掉的那一行写成 `require_removed(`，不会再被当成加载语句（射击高手 pkg81 的 "missing entry require: ./native-load-guard" 就是这行注释引起的）；源码段发现游戏自带和平台包模块同名的脚本（Cocos 2.4 模块名全局唯一，MabelsMeadow r8 自带 `TikTokMissionService.js`、旧 `MissionFlow.js`），新游戏连 `.meta` 一起移到 `.tiktok-kit/removed/<原路径>` 并警告，旧游戏只报告；2.4.4 适配器（DotsDelivery v40）没有 SDKVersion 判断、包内文件不做 fs.access，算已修好写法。游戏自己的打包步骤（例如 MabelsMeadow 的 `scripts/prepare-native-package.py` 把 `config/*.json` 放到包根）仍由游戏自己在写包入口之前做，不是平台包件。
- 门禁 `package_gates/kit_parts.py` 直接读包里的字节和清单比：文件哈希（K1）、加载行正好一次且位置对（K2）、同类件只有一层（K3）。新游戏不过就出不了包；旧游戏（遗留名单上的）只补缺了一定坏的件，其余只警告。

---

## 七、Cocos 3.x：插件版平台包

- 3.x 工程用 `plugins-3x/` 里的 5 个 `*.plugin.js`（PlatformConfig、TikTokMissionService、RewardedService、SaveStore、MissionFlow），放进工程 `assets/tiktok-platform/`，在编辑器里勾"导入为插件"并在原生和小游戏里加载（`tiktok_finalize.py source` 会写好 `.meta`）。它们由 `tools/make_plugin_scripts.py` 从 2.4 模块生成，BEGIN 和 END 之间和 2.4 模块逐字节相同；改了 2.4 的 5 个模块或 `parts/storage-guard.js` 以后必须先跑 `python3 -B tools/make_plugin_scripts.py`，再跑 `--check`，不跑的话 `plugins-3x.test.js` 会故意变红。
- 游戏代码用 `globalThis.TikTokKit.RewardedService`、`TikTokKit.SaveStore`、`TikTokKit.MissionFlow` 等，不 `require`。
- `PlatformConfig.plugin.js` 只改 BEGIN 和 END 之间的 `gameId`、`appId`、`placementMap`、`normalLevelCoins`，和 2.4 一样（生成的文件头也这样写）；加桌面、回访奖励 `growthReward()` 固定 5B，不改。
- 3.x 没有 `HomeGrowthEntries`（它是 2.4 的 `cc.Class` 组件），首页底排两个入口直接用 `TikTokKit.MissionFlow`（不传 `reward` 时自己发 `growthReward()`）。
- **入口摆在哪由插件运行时定，别手写坐标（生成时预防 R4G1）**：`plugins-3x/HomeEntrySlots.plugin.js`（件 homeslots3x，源 `parts/HomeEntrySlots.js`，找空位代码和 2.4 `HomeGrowthEntries.js` 逐字节相同，`make_plugin_scripts.py --check` 验）由 `tiktok_finalize.py source` / `sync` 给新 3.x 游戏装上，老游戏只报告。首页组件在首页按钮和 ad-boost 入口都建好后调 `TikTokKit.HomeEntrySlots.placeLater(cc, this, {root: canvasNode, entries: [profileNode, shortcutNode]})`（下一帧、Widget 跑完后）；首页后来又加按钮就再调一次 `place(cc, {...})`。可见的 `cc.Button`（禁用的也算）和带触摸监听的节点都躲开，半屏以上的触摸背景和 BlockInputEvents 遮罩不算；放不下返回 `{ok:false}`、打一行 `[TikTokKit]`、不挪。测试：`tests/plugins-3x.test.js` 的 `home_slots_*`。
- **手写入口坐标会被报出（生成时预防 R4L1）**：`tiktok_finalize_steps/home_entry_scan.py` 在 `source` 里查 3.x 新游戏：装了 `HomeEntrySlots.plugin.js`、工程里没人调 `HomeEntrySlots.place/placeLater`，却给 profile / shortcut / desktop 入口写数字坐标（`setPosition(-220, -760)`、`position = v3(..)`、`.x = 0`，或 `this.button('profile', .., 165, -top + 128, ..)` 这类按钮工厂），报 `K_W_home_entry_coords`（老游戏只记录）。确实不是入口的那行写 `// tiktok-kit:ui-ok <原因>`。测试：`python3 ../../scripts/test_r4l1_home_entry_coords.py`。
- 触摸修正 `build-templates/bytedance-mini-game/tiktok-touch-3x.js` 插在 `game.js` 的 `require('./web-adapter')` 之前；存档层 `storage-guard.js` 插在它之后（之前插时 `window.localStorage` 还不存在，什么都装不上，Marlows R4 实测）。v7.7 不给 3.x 装启动件（没有真机通过的底子）。

---

## 八、胶囊位置标准件 `parts/CapsuleLayout.js`（v7.8，总表 U1 / B30）

为什么要有：TikTok 的 `getMenuButtonBoundingClientRect()` 文档和模拟器给的是点，Saul 的 iPhone 14（2026-10-29）给的是像素（每个值乘 3）。
全民飞车漂移 v2 拿原始值把顶栏摆到胶囊下面，真机上顶栏掉下去 166 像素压进 3D 展台；SpiderSwing、Hollys、FoxDenDash 同一类。
这个件自己判断单位，不要每款游戏自己换算。

- **按需用，不是必装件**：只有把顶栏、设置钮这类节点贴着胶囊放的游戏才用。`tiktok_finalize` 不装它，`check_kit_project.py` 和 K1/K2 不要求它，
  所以没装它的老工程不会因此被拒（清单里登记为 `reference: true, optional: true`）。真正拦问题的是写包入口必跑的运行时套件
  `layout_state`：胶囊按点和按像素两遍里，不动的按钮或文字位置差超过 4 点就拦（`unit_shift`），不管游戏用的是这个件还是自己的写法。
- 2.4：复制到 `assets/`（例如 `assets/tiktok-platform/CapsuleLayout.js`），`var Capsule = require('CapsuleLayout');`。
  3.x：放进 `assets/` 并勾「导入为插件」，用全局 `TikTokCapsuleLayout`。
- 用法：
  - `Capsule.screenRect()`：胶囊在屏幕上的位置（点，y 向下），带 `unit`（SDK 给的是 `pt` 还是 `px`）。判断办法：右边超出窗口宽度、或高度超过 80 点，就是像素，除以 pixelRatio。没有接口或返回空框时用默认胶囊（87×32，距右 10，状态栏下 4）。
  - `Capsule.designRect(cc)`：同一个框换成界面世界坐标（y 向上），按引擎真实视口换算，上下有黑边的游戏也对。
  - `Capsule.safeTopY(cc, 8)`：胶囊下沿再往下 8 个设计单位，节点顶边要在它下面。
  - `Capsule.placeBelow(cc, node, 8)`：节点顶边高过 `safeTopY` 就往下挪到正好在它下面，返回挪了多少；已经在下面的不动。在 `onLoad` / 首页打开时调一次。
  - `Capsule.alignBelow(cc, node, 8)`：顶边正好放在 `safeTopY`（往上往下都挪），给「紧贴胶囊下沿」的顶栏用。
- 测试：`node tests/capsule-layout.test.js`（按点、按像素得到同一个设计坐标；2.4 竖屏铺满、2.4 上下黑边、3.x；原样把像素当点用会差 300 多个设计单位；没有接口时用默认值；`placeBelow` 两种单位挪到同一个位置）。
  运行时：全民飞车漂移 v1 首页用这个件把顶栏放到胶囊下，`layout_state` 的 `unit_shift` 从 10 个节点下移 166 点变成 0（证据 `briefs/out/W87/RESULT.md`）。**待真机复测**。
- 新 2.4 游戏不用手动复制 CapsuleLayout：source 会一起装好 CapsuleAuto（简化.11.14，生成时预防 I3）；自己摆顶栏的游戏写 `TikTokCapsuleAuto.off = true`。
- **3.x 也一样（生成时预防 R4G2）**：新 3.x 游戏由 `source`（capsule_auto 步骤）装插件脚本 `CapsuleLayout.plugin.js`、`CapsuleAuto.plugin.js`（`plugins-3x/`，带「导入为插件」的 .meta），场景启动后自己把压在胶囊下的顶栏挪下来，别手写胶囊位置；英化和老游戏只警告。测试 `tests/capsule-auto-3x.test.js`，**待真机复测**。

---

## 九、滚动障碍标准件 `parts/CourseLane.js`（v7.8，总表 P2 补）

为什么要有：BreezyBalloon v2.1（底子潜艇冲冲）按设计宽度 750 回收柱子（回收到世界坐标 816）。宽屏上真实可见宽度是 1000～1880，
回收的柱子在屏幕中间凭空出现，1115×791 上飞 18 秒瞬移 39 次；复活时又把看得见的柱子一帧挪走 796。这个件所有数都按引擎真实可见范围算
（`cc.view` 的可见尺寸和原点，或画这条赛道的相机），宽屏、上下黑边都对。

- **按需用，不是必装件**：跑酷、飞行这类有滚动障碍的游戏用。`tiktok_finalize` 不装它，`check_kit_project.py` 和 K1/K2 不要求它，
  没装它的老工程不会因此被拒（清单里登记为 `reference: true, optional: true`）。真正拦问题的是写包入口必跑的运行时套件 `popin`：
  四种屏幕上主角无敌飞 18 秒再复活一次，障碍在屏幕里凭空出现、消失、一帧跳 40 以上就拦，不管游戏用的是这个件还是自己的写法。
- 2.4：复制到 `assets/`（例如 `assets/tiktok-platform/CourseLane.js`），`var Lane = require('CourseLane');`。
  3.x：放进 `assets/` 并勾「导入为插件」，用全局 `TikTokCourseLane`。
- 用法（`opts` 里 `halfWidth` 是障碍半宽，`space` 是障碍所在的父节点，`camera` 是跟着赛道走的相机，都可不填）：
  - `Lane.visibleRect(cc, opts)`：玩家真实看得见的范围 `{left, right, bottom, top, width, height}`。
  - `Lane.spawnX(cc, {halfWidth, lastX, gap})`：新障碍放的 x = 右边缘 + 半宽 + 至少 100；比「上一个 + 间距」小时用后者。
  - `Lane.isGone(cc, x, {halfWidth})` / `Lane.recycleX(...)`：障碍完全离开左边缘（x + 半宽 < 左边缘）才回收。
  - `Lane.lanesNeeded(cc, {gap, halfWidth, screens})`：要同时活着的障碍组数，屏幕越宽越多；开局 `screens: 3` 一次生成前方 3 个屏宽。
  - `Lane.clearForRevive(cc, items, {playerX, clearAhead, apply, onFaded})`：复活清障分三组：屏幕外的随便挪；看得见、在主角前方
    `clearAhead`（默认 300）以内的淡出（至少 0.3 秒，`apply: true` 时件自己用 `cc.tween` 做，做完调 `onFaded(item)`，在里面挪走并把透明度设回）；
    看得见、更远的不动。淡出期间要先关掉这些障碍的碰撞体（件只管透明度），挪走后再打开。也可以不清障，把主角退回安全点（BreezyBalloon v2.2 的做法），或在不透明遮罩下处理。
- 测试：`node tests/course-lane.test.js`（可见范围按引擎、出生在右边缘外、完全离开才回收、宽屏组数多、复活淡出 ≥0.3 秒、相机和父节点坐标、3.x；
  含 v2.1 按设计宽度出生在宽屏里的反例）。运行时：BreezyBalloon v2.1 只在运行时把回收和复活换成这个件的算法，`popin` 四种屏幕全过
  （原包四种全拦，证据 `briefs/out/W89/RESULT.md`）。**待真机复测**。

## 十、物理时钟 `parts/PhysicsClock.js`（v7.8，总表 P16）

为什么要有：Cocos 2.4 没开 `enabledAccumulator` 时，物理每一帧固定走 1/60 秒，不看真实过了多久。游戏循环跑到 120 帧（Saul 的 Mac、测试浏览器）
时整个物理就跑成两倍速；每帧推一次、或用 `schedule(cb, 0.01)`（每帧最多触发一次）推的力也跟着屏幕走。全民飞车漂移 v3.1
（`pysTouchEvent.ts:91` 每 0.01 秒推 65、`RunUI.ts:145` 只写了 `enabled = true`）起步 1 秒时 120 帧比 60 帧多跑 19.9%；
拿它当底子的 Pizza Drift 换美术后第 1 到 5 关第一个弯就掉下去。

- **谁装**：`tiktok_finalize.py source` 的 `physics_clock` 步骤，只给**新游戏**、Cocos 2.4、游戏脚本里打开了物理
  （`getPhysicsManager().enabled = true`，或先存进变量再 `.enabled = true`）、自己又没写 `enabledAccumulator = true` 的工程，
  复制成 `assets/tiktok-platform/PhysicsClock.js`（和清单哈希一致；工程里那份被改过就换回、旧的挪进 `.tiktok-kit/removed/`）。
  **老游戏一律不装**（手感是按老写法调、测过的），只在 finalize 记录里写一条警告。游戏自己已经开了 accumulator、没用物理、3.x
  （物理本来就是固定步长）都不装。游戏里已有同名脚本 `PhysicsClock` 时不装，写警告（2.4 模块名是全局的）。
  清单里登记为 `reference: true, optional: true`，`kit_sources` 不会把它复制进每个游戏，`check_kit_project.py`、K1/K2 都不要求它。
- **它做什么**：2.4 的脚本在游戏启动时全部执行一遍，它在那时、以及每次切场景前把
  `cc.director.getPhysicsManager().enabledAccumulator = true`：物理按固定 1/60 秒一步、按真实时间走（120 帧时每帧 0 或 1 步）。
  装上以后 logic_check 的 L-FPS-ACCUM 就不报了。
- **推力还是游戏自己的代码，要自己改**：每次调用推一次的力按它覆盖的时间缩放：
  `var Clock = require('PhysicsClock');`、`body.applyForceToCenter(Clock.force(cc.v2(fx, fy), dt), true)`、`body.applyTorque(Clock.scale(dt) * 10, true)`；
  移动一律「每秒多少 × dt」；`schedule` 的间隔不要小于 1/60（用 `update(dt)`）。`dt` 用回调自己收到的（`schedule(cb, interval)` 会把这次经过的时间传进来）。
  logic_check 的 L-FPS-DT、L-FPS-SCHEDULE 会列出没乘 dt 的地方。实测：飞车 v3.1 的 `schedule(run_time, 0.01)` 在 120 帧时隔一帧才触发一次，
  正好每 1/60 秒推一次，所以只装这个时钟就过了（差 1.39%）；BreezyBalloon v2.2 的障碍靠 `linearVelocity` 走，只装时钟也过（差 1.08%，不装 49.9%）。
  写在 `update` 里每帧推一次的游戏只装时钟不够（Node 测试里「只开 accumulator」那个反例），推力必须乘 dt。
- **最终裁判**是写包入口必跑的运行时套件 `frame_rate`（`cocos-game-check/package-check/references/runtime-regression.md`）：同一段操作在 60 Hz 和 120 Hz 的显示时钟下各跑一次，按真实时间比位置，差超过 5% 新游戏拦、老游戏警告。
- 测试：`node tests/physics-clock.test.js`（载入时和切场景前打开 accumulator；引擎还没好时等 EVENT_GAME_INITED；按 2.4 PhysicsManager 的步进算 2 秒距离：
  accumulator + 按时间推 60/120 帧相同，飞车 v3.1 的写法差 57%、只开 accumulator 不改推力差 50%，两个反例都必须被抓到）。运行时：全民飞车漂移 v3.1
  在运行时打开 accumulator、把 `run_time` 里的推力和扭矩乘 dt×60（和 `Clock.force` 同一个算法）后 `frame_rate` 过（最大差 1.05%），原包拒（19.9%）
  （`briefs/out/W92/RESULT.md`）。**待真机复测**。

## 十一、开工就装、每次构建前同步（P02）和弹窗按钮零件 `parts/GameUIKit.js`（P05，生成时预防 2026-11-04）

为什么要有：问题普查（2026-11-04，`ranking.json`）里，标准件只在出包前的 `source` 才装，试玩和自测一直跑在没有它们的代码上：触摸没修正 28 款、卡在加载页 34 款、Retry 没用 26 款，射击高手 v81、小熊拳击 R27 漏装触摸修正，指尖麻将 v55 重建丢了补丁。弹窗和按钮每款手写：按钮被挡 14 款、弹窗关不掉 10 款、连点两次 14 款、闪屏 18 款、没绑回调 11 款、点按区不对 13 款（花园守卫者淡出后还吃点击，最强推球关闭键 32×32，割草复活键绑了不存在的函数，挪车冲冲冲动画帧撑大点按区）。

**同步（`tiktok_finalize.py sync`）**

- 开工：`init` → `source` → `sync`；以后**每次构建前**跑 `sync --project <工程> --board <remake|localize>`。英化工程构建出 TikTok 小游戏包后再跑 `sync ... --native <构建目录>`。
- 它做什么：`kit_sources`、`build_templates`（英化不动原版 build-templates）按 `KIT_MANIFEST.json` 哈希换回平台包原文件，旧文件挪进 `.tiktok-kit/removed/`；给新的 2.4 游戏装 `GameUIKit.js`；带 `--native` 时再跑 `startup`、`touch`、`storage`。不跑图片、PNG、设置、美术步骤，夹具上不到 0.2 秒。
- 旧游戏（遗留名单）只报告，一个文件都不写。记录在 `<工程>/.tiktok-kit/sync.json`；它不是源码段记录，出包前照样要跑 `source`（K5 不变）。
- 测试：`python3 ../../scripts/test_finalize_sync.py`（删掉触摸件、换成旧版 `RewardedService.js`、删掉 `main.js` 里 storage-guard 那一行，`sync` 后三处都回到清单哈希；英化构建目录装上启动件、触摸、存档层；旧游戏前后一字节不变；耗时 < 3 秒）。

**弹窗和按钮（`GameUIKit`，Cocos 2.4）**

- 装在哪：`sync` 复制到 `assets/tiktok-platform/GameUIKit.js`。清单里登记为 `reference: true, optional: true`，`check_kit_project.py`、K1/K2 都不要求它，不会因此拦旧游戏。
- 写法：

```js
var UI = require('GameUIKit');
UI.setup({closeFrame: this.closeFrame, maskColor: [40, 30, 50], sfx: function (id) { Sound.play(id); }});
var p = UI.popup(canvas, {panelFrame: this.panel, titleFrame: this.title, keep: true}); // 遮罩吞点击；关闭键点按区 ≥104
UI.button(p.body.getChildByName('Revive'), this.onRevive.bind(this), {name: 'Revive'}); // 函数不存在当场报错
UI.wrapExisting(this.shopBtn, this.openShop.bind(this));     // 原版 cc.Button：去掉旧点击事件，SCALE 改 COLOR
this.scheduleOnce(p.guard(function () { this.showReward(); }.bind(this)), 0.8);       // 弹窗关了或重开后丢弃
p.close();       // 淡出 160ms 后一定 active=false（keep 的下次 p.open() 复用同一批节点，不重建）
UI.toast('Come back tomorrow');
```

- **美工首件尺寸（GameUIKit 1.1.8）**：制作前分别记录「PNG 像素 / trim 后 frame」「设计显示槽位」「点击区」，不能把高清图片像素当成按钮显示宽高。`button` / `wrapExisting` 每个轴优先用显式 `width/height`，再用节点已有正尺寸；只有缺失的轴才取 `art` 在按钮坐标中的显示包围盒（含中间父节点缩放），最后才退到 frame 尺寸。弹球 FREE GEMS 的设计槽位为 136×122，R14 frame 为 1136×1149，不能因为换高清图把按钮扩成 1136×1149。布局/Widget 尚未算出尺寸、art 偏移或锚点不同、希望热区大于画面时，制作阶段显式定义槽位并对齐子图，不靠回退猜布局；本接口不自动改锚点、重排或重建原节点。按钮根节点仍按既有契约保持 scale=1，缩放效果放在子图上。
- **关闭 X 首件分层**：新做按钮用无 Sprite 的 `CloseHit` 承担点按区，图片放在居中子节点 `CloseArt`；例如先定 `CloseArt` 78×78，再 `UI.wrapExisting(CloseHit, onClose, {close:true, width:104, height:104, art:CloseArt})`。点击区为 104×104，X 仍为 78×78。不要把 X 图片放在同一个节点，再以放大图片的方式扩大热区；已有用户节点不由工具自动拆分。`close:true` 原有 ≥104 规则继续生效；热区与相邻关闭键、标题/按钮的关系在首次接页检查。
- **首件记录和验收**：接入前记录上述三种尺寸及节点/子图；第一次到达实际页核对最终 display_size 与预定槽位、整图是否压住标题、相邻控件能否正常点到。同类按钮复用这个尺寸契约再批量生成。Node 回放只能证明默认尺寸和交互规则，不能替代实际页首次截图；已有合格截图复用仍受版本与依赖身份门禁约束。
- 已经管好的事：弹窗开着时下层点不到；关掉后一定不再挡点击；500ms 内连点只算一次；`handler` 不是函数在搭页面时就报错；按下只变暗不缩放，按钮节点上的动画帧不改点按区；禁用的按钮点了有提示；`popup.guard` 包住的迟到回调不执行。
- 和 AdBoostKit 的关系：`GameUIKit` 是 AdBoostKit 1.2.0 去掉 `adButton`、`doubleCheckbox`、`runAd` 后的同一套弹窗、提示条、数字、切条和 `fitTrim`。看广告的按钮和勾选框仍用 ad-boost 的 `AdBoostKit`。两份叠弹窗的记录是分开的：同一页上两种弹窗叠开时，下层的遮罩不会被自动藏起来。
- 测试：`node tests/game-ui-kit.test.js`（19 条 × 2 引擎：原有弹窗/按钮/PageRegistry 契约，加高清图不扩槽、显式尺寸优先、缩放子图、缺失轴、frame 最后回退和 X 分层。1.1.8 回归在 1.1.7 上有 14 条失败，在候选版 38 条通过）。用 `GAMEUI_KIT_FILE=<另一份文件>` 可以拿同一组用例测别的写法。**待真机复测**。
- 3.x（生成时预防 R4B 起）：`tiktok_finalize.py sync` 给新 3.x 游戏装 `assets/tiktok-platform/GameUIKit.ts`（`parts-3x/GameUIKit.ts` 原样，旧游戏只报告），别手拷；`import GameUIKit from '../tiktok-platform/GameUIKit'`，接口和 2.4 一样。页面模板：暂停 `UI.pausePage(canvas, {session, initRun, onResume, onRestart, onHome})`；复活 `UI.revivePage(canvas, {session, ads, placementKey:'revive', onRevive, onGiveUp})`；结算 `UI.resultPage(canvas, {session, store, amount, ads, placementKey:'result_x2', onNext, onHome})`。新加的按钮只能 `page.addButton('extra', {frame, text}, fn)`；分数、奖励数字放 `page.info`。会变的数值文字一律用 `UI.valueLabel(node, {longest:'100%'})`。
- 别的 Kit 的弹窗（AdBoostKit.popup）用 `var release = UI.adoptPopup({isOpen, setCovered})` 进同一个叠弹窗记录，关掉时调 `release()`；只有最上面一层暗、有 X。
- 别的 Kit 自己搭的弹窗打开时调 `UI.recordPage({id: 'ad-boost:wheel', name, kind: 'popup', close: 'Close'}, node, closeNode)`（GameUIKit 1.1.3，R4J2）记进页面登记表，和 popup() 记的一样；`ad-boost:` 开头、pages.json 里还没有的页，merge-dumps 先只警告。
- 正文、引导、标题（GameUIKit 1.1.4，R4N4）：新加的正文 Label（规则、商店说明、提示）一律 `UI.text(parent, {w, h, text, overflow:'shrink'|'clamp'|'resize'})`，它先设框、overflow 和换行，再赋字体和字；别 `addComponent(cc.Label)` 后先赋 `.string` 再设 CLAMP（SLS35 正文被撑成约 1.5 屏宽，`ui_kit_scan` 报 `K_W_ui_label_order`）。教程手指和高亮用 `UI.guide(目标节点, {frame})`，每帧绘制前和尺寸变化时按目标的世界坐标重摆，别把目标一次性换父（火箭三消偏 93.75）。页面模板的标题框用 `titleSize: {width, height}`，会转发到弹窗。
- 1.1.2（R4H 批）：每次 `popup()` / `open()` / 页面模板打开都记进 PageRegistry（开发版），生成时给 `pageId`（= pages.json 的 id），别手标 `seen_at_runtime`。分数、结算字、标题、按钮字只用图：数字用 `UI.digits`，标题用 `titleFrame`，页面按钮字用 `buttons.<槽位>.textFrame`（整词图）或字画在按钮图上加 `text: ''`；别 `new cc.Label` 加字体（页面模板用字体画按钮字会警告）。
- 还没做：`sync` 自动装 3.x 版、ad-boost 接上 adoptPopup（广告skill 下一版）。
- **source 会查手搭弹窗、写死的遮罩和开发用文字（R4F3）**：`tiktok_finalize_steps/ui_kit_scan.py` 在 `source` 里扫 `assets/` 的脚本和场景：`new cc.Node` 加 `BlockInputEvents` 却没用 GameUIKit（`K_ui_handmade_popup`）；mask / dim / shade / overlay 节点在代码里写死透明度或颜色（`K_ui_mask_hardcoded`，遮罩颜色只在 `UI.setup({maskColor, maskOpacity})` 写一次）；面向玩家的文字里有 PREVIEW、DEBUG、TODO、测试、调试、预览版等（`K_dev_text`，回家快跑「LOCAL PREVIEW」）。开发用文字新游戏拦（进源码记录，写包入口靠 K5 拒）；手搭弹窗和写死遮罩先只警告（新游戏也是 `K_W_…`，校准到完结游戏和新开工程都干净后再改回拦）；英化警告，旧游戏只记录。生成时弹窗一律 `UI.popup`，玩家文字从文案表取，预览专用文字只放在 serve_preview 外壳里；确实不是弹窗的整屏挡点层在那行写 `// tiktok-kit:ui-ok <原因>`。测试：`python3 ../../scripts/test_ui_kit_scan.py`。
- **从开工就装了 GameUIKit 的新游戏，手搭弹窗和写死遮罩直接拦（R4L1）**：`ui_kit_scan.ui_kit_era` 判「开工就有 kit」：工程里有 `assets/tiktok-platform/GameUIKit.js`（3.x `.ts`），并且 `.tiktok-kit/policy.json` 是 `init` 写的、带 `ui_kit_at_start: true`（R4L1 起 init 第一次写标记就记）或创建时间不早于 11.13 发布（2026-11-04 19:00 PST）。两样都满足，`K_ui_handmade_popup` / `K_ui_mask_hardcoded` 拦（进源码记录、写包入口 K5 拒）；只看文件不行，因为 sync 给每个新游戏都装 GameUIKit，11.13 以前开工的 25 个工程会全被拦。adopt / source 自动写的标记、11.13 以前 init 的照旧警告。测试：`python3 ../../scripts/test_r4l1_ui_kit_era.py`。

## 十二、一局状态 `parts/RunSession.js` 和特效池 `parts/FxPool.js`（生成时预防 P11、P18）

- 2.4：复制到 `assets/tiktok-platform/`，`var RunSession = require('RunSession'); var FxPool = require('FxPool');`。3.x：放进 `assets/` 并勾「导入为插件」，用全局 `TikTokRunSession`、`TikTokFxPool`。
- 新游戏（重塑/自制，board remake）不用手拷：`tiktok_finalize.py sync` 按 KIT_MANIFEST 的 `sync_install` 装好 `RunSession.js`、`FxPool.js`（3.x 连同「导入为插件」的 .meta），改过的副本按哈希换回；英化和老游戏不装（生成时预防 R4F1）。
- 场景主组件 `onLoad`：`this.session = RunSession.create(cc, {owner: this.node}); this.session.newRun(initState);`；`update(dt)`：`var d = this.session.tick(dt); if (!d) return;` 后面的移动、计时、`pool.tick(d)` 都用 `d`；`onDestroy`：`this.session.dispose(); this.pool.destroy();`。
- 一局的缓动和动作登记给会话（RunSession 1.2，R4N4）：`this.session.track(this.board)`，`newRun` 只停登记过的节点；Retry/Home 别用 `Tween.stopAll`、`cc.Tween.stopAll` 或根节点 `stopAllActions`，会把弹窗收尾动画也停了（SLS35，`ui_kit_scan` 报 `K_W_tween_stop_all`）。
- Retry、下一关：只调 `session.newRun(initState)`（`initState` 每次返回新对象），特效池 `releaseAll()`。
- 障碍物、敌人、子弹（生成时预防 R4L2，回家快跑蜗牛图没了碰撞体还挡人）：图片、动画、碰撞体挂在同一个根节点下，回收或隐藏一律整只走零件：池里的 `pool.release(根节点)`，不进池的 `session.recycle(根节点)`（要删加 `{destroy: true}`），复用 `pool.spawn` / `session.reuse(根节点)`。零件关掉根节点和子节点上全部碰撞体、物理体（2.4 `cc.Collider`/`cc.PhysicsCollider`/`cc.RigidBody`，3.x `Collider2D`/`RigidBody2D`），停缓动、动作、组件 `schedule` 和用 `session.every(ms, fn, 根节点)` 绑在它身上的定时器，复用时只打开它关掉的碰撞体。别自己写 `图片节点.active = false` / `destroy()`。敌人自己的定时器在 `reset` 或 `onEnable` 里重开。测试 `tests/entity-retire.test.js`。
- 弹窗：打开时 `var release = session.pause('popup')`，关掉时 `release()`；复活页 `'revive'`；ad-boost：`Kit.runAd(ads, {..., pauseGame: h.pauseGame, resumeGame: h.resumeGame})`，`h = session.adHooks()`。
- 写法表和反例见 `remake-core/references/game-modules.md`「一局的状态、定时、特效、移动」一节。英化游戏只在 AI 新加的暂停/复活/广告入口用。
- `tiktok_finalize` 不自动装这两个件（和 `CourseLane` 一样按需复制），`check_kit_project.py`、K1/K2 不要求它们。

## 十三、音效库的声音导入即登记 `import_audio.py`（生成时预防 P15）

- 从音效库选用的声音一律用 `python3 ../../scripts/import_audio.py --project <工程> --file <音效库里的文件>` 导进工程：复制文件、写 `docs/audio/credits.csv`（来源、授权、作者、两份 SHA-256）和音效库的使用记录，只有失败音（名字含 fail、lose、gameover、timeout 等，或 `--fail`）超过 2 秒的截到 2.0 秒并淡出；结算、领奖、胜利音（end、reward、win、complete 等，或 `--result`）记成 jingle、原样复制不截（R4E，Saul 定）；授权不能用、不在音效库里、被 2 款以上游戏用过的直接拒，什么都不写。判定和出包时的 `audit_audio_sources.py` 是同一套。测试：`python3 ../../scripts/test_import_audio.py`。
- 英化游戏原版的声音代码和声音文件不动；AI 新加的声音按上面导入。
- 声音零件 `parts/AudioService.js`（简化.11.14 起随包，1.1 只经 `ResKeys` 加载，能过平台包资源扫描）：`create` → `register`（ad-boost 的 `docs/audio/ad-boost-sfx.json` 里的 events 可以直接登记）→ `bindFirstFrame(director, Director)`（首页第一帧画出来以后才开始加载音频）→ `playMusic` / `playSfx`。1.2（R4E，没声音 15 款都是漏了 bindFirstFrame）：漏调时，首页第一次 `playMusic` / `playSfx` 后 5 秒自动开始放，并打一行 `[AudioService]` 警告；照样要在首页 `start()` 里调 `bindFirstFrame`，兜底只防漏。设置页只用 `setMusicOn` / `setSfxOn` / `setMusicVolume` / `setSfxVolume`，打开面板时只调 `settings()`。看广告用 `wrapRewarded(rewardedService).request(...)`，或 `adBegin()` / `adEnd()`。新游戏的声音都走它，英化游戏原版的声音代码不动。

## 十四、宿主接口兜底 `parts/host-shim.js` 和 3.x 启动看守 `parts-3x/boot-guard-3x.js`（生成时预防 P03）

- **生成时预防 R4B 起由 `tiktok_finalize` 自动装，别手写那一行**（标准件 hostshim24 / hostshim3x / boot3x，startup 步骤装）：`source` 把文件放进 `build-templates/bytedance/`（2.4）或 `build-templates/bytedance-mini-game/`（3.x）；3.x 工程自带 `build-templates/bytedance-mini-game/game.js` 时，`source` 和每次 `sync` 直接在它里面加好两行；构建出来的 `game.js` 由 `native` 和 `sync --native` 加（2.4 的 `game.js` 是编辑器构建时写的，只能在这一步加）。位置固定：host-shim 在适配层（2.4 `adapter-min.js`、3.x `web-adapter`）那一行正上方，启动看守在 `System.warmup(` 正上方，各一行，带 `// tiktok-kit:<件名>:2.0` 标记。
- 遗留名单上的旧游戏只报告、不改。自己有启动页的 3.x 游戏（`game.js` 加载 `./boot-loading`，或根目录有 `boot-loading.js` / `native-recovery.js`，例如 LunasJade）照装 host-shim，启动看守只报告 `K_W_own_startup`，不叠装。`game.js` 里找不到锚点（不是 Cocos 生成的 `game.js`）时只报告 `K_W_startup_anchor`、不写；锚点出现两次拒绝（K2）。
- 测试：`python3 remake-core/scripts/test_finalize_hostshim_boot.py`（8 项，在简化.11.14 原版上 8 项都失败）。
- 新代码读版本号用 `parseVersion` / `sdkVersion`，不要读 `SDKVersion[0]`，也不要按 `getOpenDataContext` 在不在判主域。新 3.x 游戏不要再自己写「15 秒没进首页就弹失败」这类总期限。
- 测试：`node tests/boot-3x.test.js`（15 项、11 个反例）、`node tests/host-shim.test.js`（10 项、8 个反例）。只在 Node 里测过，**待真机复测**。

## 十五、资源加载 `parts/ResLoader.js` 和资源表 `make_res_keys.py`（生成时预防 P12，简化.11.14）

- 开工先跑 `python3 ../../scripts/make_res_keys.py --project <工程>`，生成 `assets/scripts/generated/ResKeys.js`（3.x 是 `.ts`）；每条带写死路径的 `request(cb)`。加图、删图、改名后再跑。新游戏出包前 `--check --strict` 必须退出 0（表过期、引用了表里没有的资源、直接调引擎加载，都会报）。
- 游戏代码只写 `Res.request(ResKeys.x)`，不写路径和类型；首页必需图用 `Res.loadAll`，其余用 `Res.sprite`（占位＋重试，不阻塞页面）；加载失败按 Retry 再调一次。
- 英化游戏：原版加载代码不改，`make_res_keys.py` 不加 `--strict`；AI 新加的图（主页回访、加桌面、广告板块的按钮图）用 `ResKeys` ＋ `Res.sprite`。
- `tiktok_finalize` 不自动装 `ResLoader.js`，新游戏开工时复制到 `assets/tiktok-platform/`（3.x 设为插件脚本）。
- R4N3：各零件能装在哪些引擎上写在 `KIT_MANIFEST.json` 的 `needs.engine_versions`（`2.4.x`、`3.x` 这种写法），支持表在顶层 `engine_support`；`ResLoader`、`AudioService`、`ResKeys` 要 `cc.assetManager`，2.4 以前的引擎不装。开工用 `cocos-game-to-english/scripts/check_machine.py --project <工程>` 看零件清单，别手挑。

## 十六、激励广告兜底 `parts/rewarded-guard.js`（生成时预防 P01 第 2 点，R4A 接进 `main.js` v1.7）

- 它包住 `createRewardedVideoAd`，让没改线的原版广告代码也按 15 秒前台、不迟到发奖的口径走：同一时间只放一个 `show()`；到开播最多 15 秒前台时间，到点补一次 `onClose({isEnded:false})` 并解绑，`show()` 不 reject；开播后不计时，开播 30 秒没回调时玩家点画面算 X；作废的那次迟到的回调不再转给游戏；`isEnded` 不是 true 一律转成 false。
- `RewardedService.js` 已经带上放行标记（D2 批）：自己创建广告时设 `__tiktokKitRewardedDirect`、创建完还原，它的广告不经过 guard，只有一层 15 秒计时。
- **R4A 起已接线**：`main.js` v1.7 在 `storage-guard` 下一行 `require('./rewarded-guard')(cc, platform)`，出错不挡启动。新重塑工程由 `tiktok_finalize.py source` 的 `build_templates` 放进 `build-templates/bytedance/`（part `rewarded24`），英化原生包由启动件 `startup24.extra_files` 带上。生成时不用、也不要自己写广告超时和迟到判断，更不要手改这份文件。
- **出包检查认得它**：`package_gates/ads_static.kit_guard_hashes()` 按 KIT_MANIFEST 里这份文件的 sha256 认；原样的 guard 不算游戏调广告（`ad_regression.needs_regression`、运行时套件 `rewarded_ads`、门禁 A1/A2/G1k 都跳过它），只有它的包不要求激励广告回归。改过的 guard 哈希对不上，照旧算游戏代码；KIT_MANIFEST 读不到时什么都不认（只会更严）。测试：`cocos-game-check/package-check/scripts/test_kit_rewarded_guard.py`。
- **3.x 也接上了（生成时预防 R4G2，part `rewardguard3x`）**：`tiktok_finalize` 的 startup 步骤在 game.js 的 `web-adapter` 那一行之后、和 storage3x 同一位置写 `require('./rewarded-guard.js')(null, …)`（source 写 `build-templates/bytedance-mini-game/game.js`，native / `sync --native` 写构建出的 game.js），文件和 2.4 是同一份、sha 相同，出包检查照样认得。别手写这一行。测试 `remake-core/scripts/test_rewardguard3x.py`。
- **出包门禁要求新游戏的包接上 guard（生成时预防 R4L1）**：`package_gates/kit_parts.py` 的 `guard_findings` 读包里的字节：2.4 平台包 main.js 加载它、或自带 main.js 时 game.js 那一行；3.x 是 game.js 在 web-adapter 后那一行。新重塑游戏（板块 remake）一行都没有就拦 `K_rewarded_guard`；英化、老游戏、板块不明只报 `K_W_rewarded_guard`。板块按调用方、finalize 记录、工程 `policy.json` 的顺序读。native / sync --native 装完的包都能过。测试：`python3 ../../scripts/test_r4l1_guard_gate.py`。
- 自带 `main.js` 的老游戏还没有 game.js 那一行（finalize 的 `STEP_ALIASES` 还没给 `rewarded24` 起步骤名），只有用平台包 `main.js` 的包带 guard。
- 测试：`node tests/rewarded-guard.test.js`（含 D2 的 3 条：11.12 原版 RewardedService 经 guard 切后台 60 秒后看完不发奖、新版发奖）。**待真机复测**。

## 十七、屏幕适配 `parts/ScreenFit.js`（生成时预防 P07）

- 引入：2.4 复制到 `assets/tiktok-platform/` 后 `var Fit = require('ScreenFit')`；3.x 勾「导入为插件」后用全局 `TikTokScreenFit`。
- `canvasPolicy`（开局定一种 fit）、`cover`（背景按真实可见范围铺满）、`safeTop` / `safeBottom`（整组节点进安全区和胶囊下）、`checkCanvas`（查只开了一种 fit）。
- 约定：背景节点一律调用 `Fit.cover(cc, bg, {watch: true})`，不按设计分辨率写死尺寸；顶栏和底排把整组节点传给 `safeTop` / `safeBottom`，要传同级节点，不要把父节点和它自己的子节点一起传。测试：`node tests/screen-fit.test.js`。**待真机复测**。

## 十八、触摸归属 `parts/TouchOwner.js`（生成时预防 P13）

- 引入：2.4 复制到 `assets/tiktok-platform/` 后 `var Touch = require('TouchOwner')`；3.x 勾「导入为插件」后用全局变量。
- `claim`（第一个手指拿到控件，到 touchend / touchcancel / 切后台才放，按住多久都行）、`swipe` / `direction`（四个方向一套规则）、`cameraFor` / `toWorld` / `toLocal` / `hit`（按画这个节点的相机换算）。和触摸修正件一起用，不替代它们。
- 约定：拖拽、摇杆、滑动一律用 `Touch.claim` / `Touch.swipe`；屏幕点转世界点一律用 `Touch.toWorld`，不手算，也不取场景里的第一个相机。测试：`node tests/touch-owner.test.js`。**待真机复测**。

## 十九、经营事务 `parts/ShopTx.js`（生成时预防 R4L3，补查第 8 组）

- 引入：新游戏（重塑/自制）由 `tiktok_finalize.py sync` 按 KIT_MANIFEST 的 `sync_install` 装到 `assets/tiktok-platform/ShopTx.js`，2.4 `var ShopTx = require('ShopTx')`，3.x 当插件脚本用全局 `TikTokShopTx`；英化和老游戏不装。
- **买、做、退都进事务，别手写**：`var shop = ShopTx.create(saveStore)`；点按钮时 `var tx = shop.begin(kind, {lock, buttons, snapshot, cost})`，返回 null 就什么都不做（连点、另一个按钮在跑、钱不够）；之后只读 `tx.snap`，不再读 `this.currentPrice`、`orders[current]` 这类会变的字段；做菜每用掉一份调 `tx.consume({...})`；完成 `tx.commit({add, apply}, onDone)` 一次 `SaveStore.grant`（扣费、发奖、改存档、领奖 id 同一次写）；取消 `tx.cancel()` 只扣已经 consume 的；离开场景 `shop.abortAll()`；定时器回调包 `tx.guard(fn)`。
- 示例数据和商品表用 `ShopTx.catalog(rows, {name})`：重复 id、除 id 外完全一样的两行（复制出来的示例房间）当场报错。
- 测试：`node tests/shop-tx.test.js`（喵咪小吃铺四种旧写法反例都判错；连点只生效一次；存档失败什么都不变）。**待真机复测**。

## GameUIKit 1.1.6 和首页入口的提示、排位（生成时预防 R4Q6，补查3 第 6/7/8 组）

- **「图标 + 数字」一律用 `UI.iconValue(parent, {w, h, icon, iconW, value})`，别手摆**：签到格、HUD 金币/体力、商店价格、奖励行都用它。图标固定宽在左，数字在右边剩下的地方按实际字宽居中、放不下就缩（方块收割者签到 200 看成 00、局内金币压 LEVEL）。`set(v)` 改数。
- **提示只用 `UI.toast`**：每次打开弹窗、页面模板都会先清掉上一条提示；游戏自己换页（切面板、换场景节点）时调 `UI.clearToast()`。要跨页留着的提示传 `{keepOnPage: true}`。
- **页面上从存档来的数值写进 `refresh`**：`UI.popup(parent, {keep: true, store, refresh: function (saved, page) {...}})`、`pausePage / revivePage / resultPage({store, refresh})`，每次打开都按 `store.get()` 重画（奔跑吧巨人缓存页显示第一次打开时的金币）。
- **只在某些状态才出现的按钮用 `UI.newButton(parent, handler, {name, w, h, active: false})`**（必须给 active），或 `UI.button(node, fn, {active: false})`：节点建出来那一刻就是隐藏的，暂停键不会在首页首帧露出。
- **首页两个入口（HomeGrowthEntries 2.4 / HomeEntrySlots 3.x）**：点击立即发起导航，游戏内不显示前置说明、打开中或重试提示。排位等首页布局稳定才做：至少 3 帧、连续两帧布局签名一致（超过 90 帧还在动就按最后一帧排并打一行 [TikTokKit]）。障碍只在首页面板子树里找：2.4 传 `init(store, {homePanel})` 或让组件挂在名字含 home 的父节点下；3.x 传 `placeLater(cc, this, {root, searchRoot: homePanel, entries})`。别自己写入口坐标、别写 scheduleOnce 一帧就排。
- 测试：`node tests/game-ui-row-state.test.js`、`node tests/home-entries-notice-settle.test.js`（旧零件都失败）。**待真机复测**。

## GameUIKit 1.1.7 弹窗用到已释放的图时自动换回（生成时预防 R4R4，补读第 8 组补充）

- **关闭图、提示底图、数字图在开工时 `UI.setup({closeFrame, toastFrame, digitFrames})` 设一次，页面里别改 `UI.config()`**。火箭三消的原设置面板把 `config().closeFrame` 换成自己 prefab 里的图，设置关掉、prefab 释放后，复活弹窗拿已销毁的图建 Close，建到一半停住（代码允许的路径，没在手机上复现）。
- 1.1.7 起零件自己兜住：`setup()` / `config().closeFrame = f` 收到图时 `addRef()`，换掉时 `decRef(false)`（引擎有这两个方法才调，不会替游戏释放）。每次用图前先查 `cc.isValid(frame, true)` 和贴图还在；关闭图失效就用开工时设的第一张关闭图，那张也没了就画零件自带的 X（圆底 + 两道白杠，点了照样关），记一条日志（`UI.frameIssues()` 可读），不抛错。底板、标题、提示底图、数字图失效时跳过那张图，弹窗、提示、数字照样建好。
- 测试：`node tests/game-ui-frame-release.test.js`（2.4 和 3.x 各 4 条，旧 1.1.6 抛错或不 addRef）。**待真机复测**。

## 3.x 平台配置也查别的游戏拷来的 id（生成时预防 R4R4，接 R4Q5）

- 3.x 游戏的 `assets/tiktok-platform/PlatformConfig.plugin.js` 由 `tiktok_finalize.py` 的 `plugin3x_scan` 步骤用 2.4 同一个 `check_kit_project.foreign_config_findings` 查：共用测试 App（App ID 7683427172773644296 和它的 3 个广告位，Saul 10-29）放行；不是共用测试 App、也没写进本工程 `docs/platform/platform_ids.json`、又在别的游戏里出现的 appId / clientKey / 广告位报 `K_platform_ids_foreign`（新重塑拦、英化警告、老游戏只记录）；gameId 重复和没记录来源的 id 报 `K_W_platform_ids`（警告）。
- 别的游戏从哪里找：`options['peers']` 或环境变量 `TIKTOK_KIT_PEERS`（多个文件夹用系统路径分隔符隔开）；不给就只查共用测试 App 和本工程记录。工程自己的 `build/`、`library/`、`temp/` 下的副本不算别的游戏（2.4 的 `--peers` 同样）。
- 测试：`python3 remake-core/scripts/test_platform_ids_3x.py`（旧 plugin3x_scan 2 条失败）。
