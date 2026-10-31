# 出包前运行时回归（runtime regression，v7.5）

用途：在模拟的 TikTok 宿主里运行**上传包本身**（真实的 game.js → adapter → 引擎），制造启动/网络/图片故障，
拦住网页版测不出的问题。这是浏览器模拟，不是真机，也不是真实广告；用它通过的包仍要按规则真机复测。

## 命令

```
cd cocos-game-check/package-check/scripts
python3 -B runtime_regression.py list
python3 -B runtime_regression.py required --package <解压包或.zip> --adapter <adapter.json>
python3 -B runtime_regression.py run --package <解压包或.zip> --adapter <adapter.json> [--suites a,b] [--board remake|localize] [--trial <试玩链接>] [--out r.json] [--work 目录]
python3 -B runtime_regression.py trial --url http://127.0.0.1:<端口>/ [--adapter <adapter.json>] [--out r.json]   # v7.8：只跑试玩链接冒烟
```

- 必须有 Ego 浏览器（`ego-browser`）和 adapter；缺任何一个、缺套件需要的字段、套件没写结果、超时、任何一条 case
  不过，都是拒绝（`RuntimeRefused`），不会跳过。`warnings` 只记录，不拒绝。
- 每个套件单独起宿主服务，只绑 127.0.0.1，套件结束就停。环境变量 `RUNTIME_REGRESSION_SPACE` 可指定 Ego 任务空间名。
- 出包入口已接入（两个写包入口都跑，v7.8 W97 起）：
  - `build_checked_zip.py`、`prepare_delivery.py` 经 `check_package.check()`：对每个有 game.js 的包用
    `required_suites(files, adapter)` 算出必跑套件、`run(package_dir, adapter_path, suites)` 跑，和激励广告回归用同一个
    adapter（`--ad-regression` 或 `$TIKTOK_AD_REGRESSION_ADAPTER`）。没跑通就拒绝出包（没 adapter、广告用例没过时老游戏也拒；套件自己对老游戏只警告的照旧），结果写在报告的
    `runtime_regression`。
  - `make_tiktok_zip.py`（重塑游戏的正式写包入口）不调 `check()`，改调 `check_package.writer_regressions()`：同样的
    激励广告回归 + 运行时套件，跑在刚写好、重读过的 ZIP 的解压副本上（就是要发出去的字节），adapter 同样来自
    `--ad-regression` 或 `$TIKTOK_AD_REGRESSION_ADAPTER`，policy 用 finalize 记录的、board 用 `--board`。新游戏：没
    adapter、没 Ego、环境不完整、任一用例没过都不写 ZIP，并列出全部原因；名单上的老游戏：同样的原因只写进报告
    `warnings`（带「[legacy game: warning]」），照样出包。结果写在报告的 `rewarded_ad_regression`、`runtime_regression`。
    这一步排在所有便宜检查之后，每款多几分钟（FoxDenDash v1 光广告回归就 457 秒）。
- 套件约定（给写套件的人）：`scripts/runtime_regression/README.md`。
- 新游戏 / 老游戏（v7.8）：`run(..., policy=None)` 不给时按包的字节判（和 `package_gates` 一样：场景 / 资源 uuid 对
  `LEGACY_GAMES.json`，不在名单 = 新游戏，判不出 = 新游戏），结果写在摘要的 `policy`、`policy_reason`，并传给套件
  （`CFG.policy`）。`--policy new|legacy` 只给测试和校准用。写包时 `check_package.check()` 把共用门禁定下的 policy（写包入口
  finalize 记录里的那个）传给 `runtime_gate(..., policy=)`，运行时套件和共用门禁按同一个判定（FoxDenDash v1 回执写 new、
  按字节判 legacy，写包时按 new）。只给 ZIP 跑 `check_package.py` 时没有 finalize 记录，两边都按字节判。

### 开跑前查环境（v7.8，总表 A6 补）

企鹅雪道 v4 对没收尾的构建跑广告回归：`tiktok-touch-3x.js` 在目录里、`game.js` 没装，X 点不进游戏，nocallback 看起来像广告坏了。
现在 `runtime_regression.py` 和 `ad_regression.py` 开跑前先查环境，不完整就报「环境不完整：……」，不跑用例：

- **触摸件**（两种调用都查）：用上传检查同一个触摸探针（`remake-core/scripts/audit_upload_startup.py` 里的
  `probe_cocos2/3_touch_coordinates.cjs`，跑包自己的 game.js 和引擎触摸转换）。探针不过 = 环境不完整，并写明 2.4 要平台包
  `touch-coordinates.js`、3.x 要 `tiktok-touch-3x.js`、这个包里装没装。别的写法的触摸修正探针认就算有；探针跑不了时才只看平台包触摸件装没装。
  不是 Cocos 包不查。
- **写包回执**（只在命令行对 ZIP 跑时查）：ZIP 旁边要有写包入口给这份字节写的回执（`verify_native_zip.receipt_status`，和
  `check_package.py` 认回执的办法一样，改名后按字节找也认）。写包入口自己在写回执之前调用 `run()`，所以 Python 里调用 `run()`
  从不查回执；对解压目录跑也不查。要诊断手打的 ZIP，解压后对目录跑。
- 退出码：0 通过、1 包不通过（用例不过或运行被拒）、2 环境不完整；`--out` / `--report` 里 `status: environment_incomplete`、
  `verdict` 写结论，stderr 最后一行「结论: ……」。写包入口照样拒绝（`EnvironmentIncomplete` 是 `RuntimeRefused` /
  `RegressionRefused` 的子类），拒绝原因以「环境不完整：」开头。
- 校准（2026-10-30，本机 354 个带 game.js 的 ZIP）：123 个报环境不完整，和上传触摸探针的结论 352/354 一致（另 2 个引擎触摸转换认不出，
  探针报「未验证」，这里不报）。报出的都是 v7.3.3 平台包触摸件之前的包或底子原包，现在走写包入口同样被上传触摸探针拒；
  `！交付游戏/1Hao-TobinsGem` 两个包装了平台包触摸件，探针报 `cc.Touch is not a constructor`，也被上传检查拒，是否探针误报没查。

### 3.x 相机（v7.8，总表 A13 补）

节点换成屏幕点分两步：`// cam-point:begin … // cam-point:end`（世界点 → 相机屏幕点）和 `// css-point:begin … // css-point:end`
（屏幕点 → 页面 CSS 点），`ad_regression/cases.mjs` 1 处、`runtime_regression/lib.mjs` 的 findLabels 和 locate 2 处，三处逐字相同。
2.x 用节点自己的相机（不变）；3.x 沿父链找节点所在 Canvas 的 `cameraComponent`，找不到才退回场景第一个相机。v7.7.5 的 3.x 直接用
`cams[0]`，3D 游戏取到世界相机：企鹅雪道 v7 包的 X 被算到 (818, -918)，nocallback 报 5 条问题；改后点到 (354, 78)，nocallback 通过。
`test_tap_point.py` 用假数据核对（含「3D 场景 + UI 相机」），在 cocos-game-check 里不在 cam-point 块中取 `cams[0]` 就失败。

## 套件（v7.5 起；v7.8 加 dead_shell、layout_state、button_sweep、ad_entries、trial_link、popin、frame_rate）

| 套件 | 引擎 | 何时必跑 | 内容 | 证明 |
|---|---|---|---|---|
| `startup` | 2.x | 所有 TikTok 包 | 冷启动；分包慢进度 40 s；分包卡在 40%；分包失败一次；第 2 次分包失败/卡住；`assets/main/config` 失败/卡住一次；没有 SDKVersion；没有 getOpenDataContext；存档键不存在。要求：进首页，最多点 1 次 Retry，Retry 在故障后 20 s 内出现（慢进度一次都不许要 Retry）。生命周期（指尖麻将 v57）：加载中 Date.now 跳 12 秒且不发 onHide、onHide+60 秒+onShow（都不许出 Retry）、第一张包内图片不回应（最多 1 次 Retry），之后用 `play` 真点首页 PLAY，必须离开首页。宿主按 TikTok：document.hidden 恒 false、不发 visibilitychange、游戏加的网页元素不显示（DOM Retry 不算） | 指尖麻将 v57 拒（时钟跳 12 秒、图片不回应后首页按钮全锁）/ v58 过；Mabel r7 拒（慢进度要 Retry、卡 40% 要 2 次）/ r8 过；射击高手2048 v81 拒（4 条卡死 + SDK + 缺键提示 unavailable）、v82/v83 拒 sdk 和 opendata、v84 只拒 opendata；MusicSlice v29b 拒 sdk+opendata、v30 这两条过 |
| `network` | 2.x | 所有 TikTok 包 | 启动、首页停 5 s、进一关玩 `level_timeout_s` 秒，记录所有外部请求（tt.request、downloadFile、connectSocket、XHR、fetch、WebSocket、sendBeacon、图片）。不在 `runtime_regression/network-allowlist.json` 的域名 = **警告**并列出。只有没进首页、`enter_level` 抛错才拒绝 | MusicSlice v29b 警告 pas.qq.com（启动 3 次 + 关内 2 次）/ v30 无警告 |
| `dead_shell`（v7.8，总表 E1 补，规则名 VIS_DEAD_SHELL） | 2.x | 所有 TikTok 包 | 互推、排行榜、更多游戏的代码删了，节点却还显示着一张图（Holly's Hay Hop v1：原版 WxGameBox 拿不到配置时把挂件设成 inactive，换成什么都不做的 EmptyGameBox 后，局内齿轮下面一直显示「Try It」框；`H14_cross_promo` 只查代码，查不到）。扫三个画面：首页；用 `play` 真点 PLAY 之后的局内；有 `enter_level` 时重新启动、调用它之后的关内。命中要两条同时成立：①玩家看得见：`activeInHierarchy`、自身和父链 opacity 都大于 0、有 enabled 的 Sprite 且有 spriteFrame 或非空 Label、在可见区域内、宽高都大于 4 px；②节点自己的名字或 sprite 帧名正好是退役槽位：gameBox、leftGameBox、leftGameBtn、gameIcon、popBox、fullScreenBox、leftBox、moreGame(s)、more、bannerAdv、banner_border、friendRank、phb、jxyx、hy、tj（整名匹配，不分大小写；rank、ranking 不算槽位：Saul 2026-10-31 允许局内对本地机器人的名次，68 小熊拳击的分数牌就叫 rank，好友榜 friendRank、phb 照旧算）；item_bg 太常见，只在这些槽位节点里面才算。槽位节点的子节点不因为父节点名字就算命中（原型这样做，Meteor Blaster r9 的局内玩法容器就叫 `Canvas/gameBox`，砖块全被带进来；指尖麻将 v56 的金币、体力条用 item_bg 帧）。新游戏命中就拒，点名节点路径、sprite 和尺寸；名单上的老游戏（`policy`，见下）只写警告。`play` 和 `enter_level` 都没有、或真点 PLAY 后没离开首页，都判不通过（局内没扫到不算过）。修法：把节点设成 inactive，空实现的 `init(nodes)` 把传进来的节点设成 inactive | Holly v1 拒（after_play、enter_level 都命中 `Canvas/gameLayer/gameView/info/gameBox/bg`，sprite gameIcon，118×133）；Holly v2、方块冲冲 BUGFIX7、FoxDenDash v1 过；Holly v1 按老游戏跑只警告。另 7 款 0 命中：全民飞车漂移 v3.1、GardenGuard v1、Meteor Blaster r9、BreezyBalloon v2.2、FeedPals v2、丛林荡藤 v6、指尖麻将 v56（证据 `briefs/out/W85/evidence/dead_shell-*.json`） |
| `startup3x` | 3.x | 所有 3.x TikTok 包 | 1.5 MB/s 冷启动包内第一帧 ≤ `first_frame_ms`（默认 5 s）；`webp_slow` 首页所有精灵有贴图；`img_events_only` 出第一帧并进首页；每条记录帧率，<30 fps 判本次无效 | LunasJade v0.10.0 三条全拒（第一帧 14.8 s、0/14 贴图、无第一帧）/ v0.10.1 三条全过（0.6 s、14/14、60 fps） |
| `layout_state`（v7.8，总表 B30 D、S8 补、U1） | 2.x、3.x | 所有 TikTok 包（两个写包入口必跑） | iPhone 14（底部横条 34 点）和 SE，胶囊按点 / 按像素各一遍，乘 adapter 的 `layout_states`（不写 = 新玩家首页）。每遍暂停逻辑后量每个看得见的按钮和文字：被 3D 盖住（按钮 ≥30%、文字 ≥50%，按像素量：节点和 3D 各开关一次）`covered_3d`；按钮伸出屏幕 `offscreen`；按钮或文字压胶囊 `capsule`（SE 胶囊横向位置没实测，只警告）；按钮中心在底部横条里 `safe_area`（只压进一点只警告）；同一设备同一状态按点和按像素两遍里不动的按钮或文字位置差超过 4 点 `unit_shift`；状态没进去 `state`。首页规则（第一个状态、iPhone 14、按点）按 board：remake 查设置钮在左上 `settings_pos`、最下面一排只有主页回访和加桌面 `bottom_row`、两个入口都在 `platform_entries`；localize 原首页按钮不动，只查两个入口在首页、能点、不压原按钮；board 不知道只警告。开局下载（第一遍）：进首页前请求的分包加主包，以首页场景的 EVENT_BEFORE_SCENE_LOADING 为界（宿主 `scene-loading` 记录），超过 10 MiB `startup_size`、含声音 `startup_audio`。**新游戏拦、名单上的老游戏只警告；3.x 只有开局下载两条会拦，其余只警告**（Saul 10-30，22.6 第 2 问）。页面帧率低于 20（Ego 窗口被挡）报 `invalid_run`，不算游戏的问题，重跑。和 `W8_prehome_bytes` 的关系：W8 是按启动代码静态估算（15 MB 只警告），这里是宿主实测、拦截用的数；`check_package` 报告里 `pre_home_bytes`（静态）和 `pre_home_bytes.measured`（实测）并列 | 全民飞车漂移 v1 拒（开局 24.75 MiB 含声音 1.26 MiB、胶囊按像素时顶栏下移、被 3D 盖住）、v3 拒（展台上有车时 RACE 被 3D 盖 37%，要 `layout_states` 的 car_on_turntable）、v3.1 过（5.68 MiB）；HappyCup v20.7.1 过；校准见 `briefs/out/W87/RESULT.md` |
| `button_sweep`（v7.8，总表 B30 E、H4） | 2.x、3.x | 所有 TikTok 包（两个写包入口必跑） | iPhone 14、新存档。首页每个按钮（cc.Button，或带自己触摸监听的节点）用真实鼠标点一次，它打开的弹窗里的按钮各点一次（每次重新加载）。点后 2 秒内有任何一种算有反应：调广告、toast / modal、平台调用（主页回访、加桌面、登录）、换场景、节点出现 / 消失 / 移动（同路径换了 uuid 也算，RETRY 重建画面）、文字或图片帧变化；点前空等 1.5 秒，自己会变的不算；第一次没反应等目标停稳再点一次。`dead_button` 能点的 cc.Button 没反应；`popup_layout` 弹窗按钮伸出屏幕、压胶囊或中心在底部横条；`covered_3d` 点出来的新按钮被 3D 盖住 ≥30%。只警告：只有触摸监听的节点（拖动目标）、已选中的项和标签页、灰按钮、被后画的拦截节点盖住、时间用完（`sweep_budget_s`，默认 480）。找到的看广告入口写在证据 `adEntries`。**v7.8 W93 补三处**：① 关后再点：弹窗里的关闭 / 返回 / X 类按钮点了、弹窗确实消失后**不重新加载**，再点一次打开它的按钮（必须再打开同一个弹窗），再点一个之前有反应的按钮（必须有反应），否则 `blocked_after_close`（点名哪个按钮打开、哪个按钮关的）；关掉后留下透明遮罩、全屏 BlockInputEvents、busy 没放开都会这样。② 诊断：每条 `dead_button`、`blocked_after_close` 后面写卡在哪一段，一句话：「点不到（被 X 盖住）」（写名字、路径、有没有 BlockInputEvents、透明度、是否全屏）、「回调没执行（…）」（没收到抬起、interactable=false、clickEvents 指向不存在的方法、没挂回调）、「回调报错：…」（从触摸分发里抛出的异常）、「请求没回来：…」（tt.* 有 success/fail/complete 或 Promise、cc.resources / cc.loader / assetManager / loadScene 有回调却没回、分包请求没有 -ok/-fail、广告 show 了没关）、「点到了也执行了，但画面没变」；2 秒内只是打印出来的报错（console.error、cc.error、window.onerror）附在结论后面，点前 3 秒出现过的同一条不算。按钮自己按下时的缩放 / 位移不算反应（回调抛错时 SCALE 过渡停在 0.95，以前会被当成有反应）。③ 局内：adapter 有 `play` 就真点 PLAY 进局，照首页的办法扫局内按钮（暂停、设置、技能）和它们打开的一层弹窗，含关后再点；局内自己会动的（同一父节点下点前就在变的）不算反应；局内时间单独算，上限 min(`sweep_budget_s`, 90 秒)，超时只警告；局内弹窗的位置问题只警告。没有 `play` 不扫局内，原因写在证据 `notRun` 和警告里。新游戏拦、老游戏和 3.x 只警告；只有触摸监听的拖动目标、已选中项、灰按钮只警告 | 全民飞车漂移 v1 拒（商店顶条空按钮）、v3 拒（买第一辆车后 RACE 被 3D 盖 37%）、v3.1 过；HappyCup v20.7.1 过；W93：HappyCup 副本在页面里改坏（关闭只设 opacity 0 且留着全屏遮罩、关闭后留下全屏 BlockInputEvents）报 `blocked_after_close`，回调抛错报「回调报错」，透明节点盖住报「点不到（被 X 盖住）」，tt 调用不回报「请求没回来」，busy 标志报「点到了也执行了，但画面没变」，原包过（`briefs/out/W93/RESULT.md`） |
| `ad_entries`（v7.8，总表 A12、B30 B） | 2.x、3.x | adapter 有 `ad_entries` 时 | 每个看广告入口（5 个入口加复活）的每个状态：新存档到首页，跑状态里的真实操作 `actions`（点、拖、等场景、等节点），再跑 `setup_js`，按钮必须在屏幕上（不在 = `missing_entry`）、没被盖住，空等 2 秒后真实鼠标点它，2 秒内要调广告、toast / modal，或出现新文字（告诉玩家为什么不能看）；都没有 = `dead_button`。灰按钮没反应只警告。**复活要等主角自己失败**（`wait_node` 等复活按钮），开局 3 秒强制 `finish(false)` 会在游戏还不该给复活的地方误报，适配文件这样写直接拒。和 `ad_regression` 的分工：ad_regression 用 `request` 直接发起广告，测 SDK 回调（超时、X、只发一次奖励）；这里只证明玩家真点的按钮能走到那条流程。新游戏拦、老游戏只警告 | 全民飞车漂移 v1 拒（离线收益为 0 时 x2 哑按钮、没有复活页）、v3.1 过 |
| `popin`（v7.8，总表 P2 补） | 2.x（3.x 只警告「未覆盖」） | 所有 TikTok 包（两个写包入口必跑）；adapter `popin` 写 `{"n/a": 原因}` 的不开浏览器直接过 | 障碍不许在屏幕里凭空出现、消失、瞬移。四种屏幕 390×844、375×667、768×1024、1115×791（CSS 点，新存档）：进首页，开局（`popin.start` 或真点 `play`），等 `game_node`，`invincible_js` 让主角无敌，在屏幕中间按一下，飞 18 秒，调 `revive_js`（复活那段代码），再看 4 秒。每画一帧，查所有带碰撞体（`cc.PhysicsCollider` / `cc.Collider`）而且画得出东西（自己或下面有渲染组件）的节点，主角和它下面的、`ignore` / `ignore_groups` 不算：`appeared_on_screen` 上一帧没显示（或透明度不到 5%）、这一帧在可见范围里显示（≥25%）；`vanished_on_screen` 在可见范围里显示着，下一帧没了、关了或透明度不到 5%（被销毁也算）；`jumped_on_screen` 前后一帧有一帧在可见范围里，一帧挪了 40 以上（按帧时间放大：卡一下 100 ms 门槛是 240）。可见范围按引擎真实可见区（2.4 经节点的相机 `getWorldToScreenPoint`，宽屏和上下黑边跟着 `cc.view`）。允许的：淡入淡出（0.3 秒的淡出不会一帧从 ≥25% 掉到 <5%）、在整屏不透明（≥98%）的遮罩下面处理。一个障碍都没看到 = 适配写错，不过。页面低于 20 帧 = `invalid_run`，重跑。缺 `popin` 或写错：新游戏拒、老游戏警告不跑。**新游戏拦、名单上的老游戏只警告**。写法要求见 `remake-game/references/creation-gates.md`「滚动障碍」，标准件 `platform-kit/parts/CourseLane.js`。每款多约 2 分钟 | BreezyBalloon v2.1（9b7b556a…）四种全拒（390×844 复活 2 次、375×667 复活 4 次、768×1024 飞行 28 次 + 复活 8 次、1115×791 飞行 26 次 + 复活 6 次）、v2.2 四种全过、v2.1 运行时换成 CourseLane 回收和复活四种全过；底子潜艇冲冲 V32 拒；VineSwing v6、SpiderSwing v2.4 过；全民飞车漂移 v3.1、HappyCup v20.7.1 写 n/a 过（`briefs/out/W89/RESULT.md`）。观察器的纯逻辑测试 `test_popin_gate.py`（Node 假引擎） |
| `frame_rate`（v7.8，总表 P16 第 3 步） | 2.x（3.x 只警告「未覆盖」） | 所有 TikTok 包（两个写包入口必跑）；adapter `frame_rate` 写 `{"n/a": 原因}` 的不开浏览器直接过 | 物理和推力不许跟着屏幕帧率走，这一条是 P16 的最终裁判（logic_check 的 L-FPS 三条只是静态提示）。同一段操作跑两次：页面加载前用 CDP 把 `requestAnimationFrame` 换成定频时钟，一次 60 Hz（手机）、一次 120 Hz（Saul 的 Mac、测试浏览器），Cocos 2.4 主循环、`dt` 和 2.4 物理都跟着它走。每次：新存档进首页、`after_home_js`、`frame_rate.start`（真实操作，可选）、`prepare_js`（可选）、等 `settle_ms`，然后在 t0 跑 `drive_js`（那段操作，例如按 RACE），`steps` 按真实时间再跑几步，每 10 ms 记一次 `track` 节点的世界坐标，记 `run_s` 秒。比较：从节点开始动的那一刻（`align: "move"`，默认；`"drive"` 从 t0 起）往后 1 秒起每 0.25 秒一个比较点，两次的位移差除以较大的位移，最大的超过 5% `same_motion` 不通过；节点没动够 `min_move`（默认 20 世界单位）`no_motion` = 适配写错。时钟没跑到目标帧率（差 8% 以上，机器太忙或窗口被挡）`clock_60` / `clock_120` = 本次无效，一律拒、重跑；引擎帧数和时钟对不上（frameRate 30 之类）只警告。缺 `frame_rate` 或写错：新游戏拒、老游戏警告不跑。**新游戏拦、名单上的老游戏只警告**。修法：开 `enabledAccumulator`（用了 2.4 物理的新游戏 `tiktok_finalize.py source` 自动装平台包 `parts/PhysicsClock.js`），推力按时间缩放（`Clock.force(v, dt)`），移动乘 dt，schedule 间隔不小于 1/60。每款多约 1 分钟 | 全民飞车漂移 v3.1 拒（起步 1 秒时 60 Hz 走 111.9、120 Hz 走 139.7，差 19.9%）；同一个包运行时打开 enabledAccumulator 并把 run_time 里的推力和扭矩乘 dt×60 后过（最大差 1.05%），只在页面里跑一遍平台包 `PhysicsClock.js` 也过（1.39%）。BreezyBalloon v2.2 拒（障碍按 linearVelocity 走，120 Hz 快一倍，差 49.9%），跑一遍 `PhysicsClock.js` 后过（1.08%）（`briefs/out/W92/RESULT.md`，适配 `briefs/out/W92/adapters/`）。纯逻辑测试 `test_frame_rate_gate.py`（Node：时钟真到 60/120 Hz、每帧推的写法拒、按时间推的写法带起步差和采样抖动照样过） |
| `trial_link`（v7.8，总表 B21、B30 F） | 2.x、3.x | 有试玩链接时：`serve_preview.py --keep` 给出链接之前；`runtime_regression.py trial --url <链接>` 手动对任意链接；写包入口没有链接，不跑（摘要 `not_run` 写明） | 按 Saul 的用法打开链接（1180×960 电脑窗口、清存档），等场景稳定，真实鼠标点到看广告（adapter `trial.taps`，或 `trial.open` + `trial.ad_button`；没写就找首页上文字 / 图名像看广告的按钮，最多试 3 个）。2.5 秒内画面中心必须被模拟广告窗盖住（serve_preview 的 `#__ad-simulator`，在 shadow root 里；TikTok 宿主的 `#__adOverlay`），或有 toast / modal、或文字变化；否则 `ad_window_hidden`。有广告窗就等「看完」可点后点它，游戏必须变化（`trial.reward_js`，没写看画面文字），否则 `reward_missing`。不知道、也找不到看广告入口 = 没跑（写原因，只警告） | 原型：全民飞车漂移 v1～v3 的旧试玩宿主（广告窗挂在适配器换掉的 body 上）拦，v3.1 过 |

v7.8 B30 的套件都来自全民飞车门禁原型（`1全民飞车漂移/_work/skill_feedback/gates/`，`README_通用自查.md`），原型校准时修掉的 10 条
2.4 误报和 4 条 3.x 误报都保留在代码里（`runtime_regression/layout_rules.mjs`、`gates.mjs`、`geom.mjs` 的注释标了是第几条）。
纯规则的测试：`test_layout_gates.py`；接线测试：`test_runtime_regression.py` 的 `B30Wiring`。每款出包多 6～10 分钟。
摘要（`run()` 返回、`--out`）多了 `not_run`（没跑的套件和原因）、`board`、`startup_measured`。

证据都在 `WORK/evidence/W3a/item2-*`、`item3-*`、`item4-*`。广告回归（10 条）仍由 `ad_regression.py` 单独跑，
规则见 `remake-ads/references/ad-timeout-and-regression.md`（v7.4 口径不变）。

已知没拦住的：MusicSlice v29b/v30 和射击高手2048 v81 在「分包卡在 40%」「config 卡住一次」时黑屏、没有 Retry——
这是真实缺口，startup 套件照样拒绝。

## adapter 字段

一个 adapter JSON 同时给广告回归和运行时回归用（`ad_regression.load_adapter` 也认下面这些键，v7.5 R1）。
值都是页面里执行的 JavaScript 函数体（`return ...`），除非另写。

| 字段 | 谁用 | 含义 |
|---|---|---|
| `request` `state` `ready` `exit` `exit_label` `no_music` `boot_timeout_s` `note` | 广告回归（v7.4） | 见 ad-timeout-and-regression.md；`boot_timeout_s` 也是运行时套件的启动上限（默认 60）。`exit` 直接返回 X 节点（或 `{node, x: 0, y: 0}`），不要自己换算屏幕坐标：v7.7.4 起工具对 2.x 换算正确，以前为绕开旧公式写的 getScreenToWorldPoint / convertToNodeSpaceAR / canvas.width 补偿会把 X 点偏，nocallback、cancel 看起来像游戏广告坏了；v7.7.5 起这样写会出警告（总表 A14） |
| `home` | 所有运行时套件（必填） | 首页可用时返回 `true` |
| `retry` | startup | 返回 Retry 控件（cc.Node 或 `{x,y}` CSS 坐标）；不填就按文字找 |
| `play` | startup（必填）、dead_shell | 首页 PLAY 按钮：直接返回 cc.Node（v7.7.5 起工具对 2.x 按 cc.visibleRect 换算，以前除以 canvas.width 会点偏，总表 A13），也可以返回 `{x,y}` CSS 坐标；算出来的点在画布外时报“定位错误”，不算首页锁死。生命周期用例真点它，点后 `home` 变 false（或 `in_level` 为 true）才算按钮有效。`home` 写成“首页画出来了”，不要用游戏自己的加载完成标记 |
| `in_level` | startup、dead_shell（可选） | 进了关卡返回 `true`；点 PLAY 后先弹窗、首页仍算可用的游戏要填 |
| `retry_label` | startup | Retry 文字的正则（默认 RETRY/Try again/Reload/重试/重新加载） |
| `startup_cases` | startup | 只跑这些 case（逗号分隔），调试用；出包时不要填 |
| `enter_level` | network、dead_shell | 从首页进一关（调用游戏真实的开始方法），返回 `true` |
| `level_timeout_s` | network | 关内停留秒数（默认 20） |
| `first_frame_ms` | startup3x | 第一帧上限，默认 5000 |
| `engine` | 运行器 | `"2.x"` / `"3.x"`；不填按包内容判断（有 `src/system.bundle.js` 或 `cocos-js/cc*.js` 是 3.x） |
| `host_query` | 运行器 | 每个 URL 都加的宿主参数（字符串） |
| `remake_home` `save_keys` `runtime_note` | 预留 / 说明 | `runtime_note` 是说明文字 |
| `home_scene` | layout_state、button_sweep、ad_entries（可选，v7.8） | 首页场景名。不写就用进首页时的场景；不写 `home` 时，「进了首页」= 场景稳定 3 秒、没有分包在下载、画面上有按钮、帧数在涨 |
| `layout_states` | layout_state（可选） | 要多测的状态 `[{name, why, actions, expect_visible, settle_ms}]`，`actions` 是真实操作（`{"tap": 路径}`、`{"drag_js": "...return [a, b]"}`、`{"js": ...}`、`{"wait": ms}`、`{"wait_scene": 名}`、`{"wait_node": 路径, "timeout": ms}`，每步可带 `after`、`optional`）。全民飞车漂移：`car_on_turntable` = 点 Buy 后等 `Canvas/btnks` 出现 |
| `layout_query` | layout_state、button_sweep（可选） | 这两个套件额外的宿主参数 |
| `settings` / `platform_entries` | layout_state 首页规则（可选） | 认设置钮 / 两个平台入口的正则（对节点路径、文字、图名）；不写用默认（setting、gear、齿轮… / profile、revisit、add to home、桌面…）；平台包 HomeGrowthEntries 的两个节点自动认 |
| `after_home_js` | layout_state、button_sweep、ad_entries（可选） | 每次进首页后在页面里跑的函数体（关掉新手引导） |
| `sweep_skip` / `sweep_budget_s` | button_sweep（可选） | 不点的按钮（正则）/ 时间上限秒数（默认 480） |
| `play` / `in_level`（button_sweep 用法，v7.8 W93） | button_sweep（可选） | 同 startup 的 `play` / `in_level`。有 `play` 时 button_sweep 真点它进局，`in_level` 为 true（或 `home` 变 false；两个都没写时看场景换了、首页按钮大半不见）就算进了局，等 2.5 秒再扫局内按钮；10 秒没进局不扫局内、写进 `notRun` |
| `ad_entries` / `ad_entries_query` | ad_entries（有它才跑） | `[{id, button, states: [{name, why, actions, setup_js, settle_ms}]}]`；宿主参数默认 `ad=complete` |
| `trial` | trial_link（可选） | `{taps: [路径…]}` 或 `{open: [{tap}], ad_button}`，`reward_js` 返回奖励数值 |
| `popin` | popin（v7.8，**新游戏必填**；名单上的老游戏缺了只警告） | 对象。必填四个字符串：`player` 主角节点（名字或路径尾，`*/a/b` 也行；它和它下面的节点不算障碍）、`invincible_js` 让主角无敌（返回 `true`）、`revive_js` 看完复活广告后游戏跑的那段复活（不经过广告，直接调）、`game_node` 进局后才出现的节点。可选：`start` 开局的真实操作（格式同 `layout_states.actions`；不写就真点 `play`）、`first_touch`（默认 `true`：开局后在屏幕中间按一下）、`fly_s`（默认 18，5～60）、`settle_ms`（进局后等多久，默认 2500）、`after_start_js`（开局后跑一次，证明或调试用）、`ignore`（路径正则：不算障碍的节点，例如主角射出去的钩子 `^Canvas/point$`）、`ignore_groups`（分组名：例如连续的地面条 `["bottom"]`）、`query`（宿主参数）、`note`。没有滚动障碍的游戏写 `{"n/a": "原因"}`，运行器不开浏览器直接过。BreezyBalloon：`{"player": "submarineItem", "game_node": "LevelView", "invincible_js": "…getComponent('SubmarineItem').safeUntil=Date.now()+1e9;return true;", "revive_js": "…getComponent('LevelView').resumeSameDive();return true;", "ignore_groups": ["bottom"]}`（全文 `briefs/out/W89/adapters/breezyballoon.json`） |
| `frame_rate` | frame_rate（v7.8，**新游戏必填**；名单上的老游戏缺了只警告） | 对象。必填两个字符串：`track` 返回要跟踪的节点（或 `{x, y[, z]}` 世界坐标；还没生成时返回 `null`）、`drive_js` 那段操作的开头（t0 跑一次，例如按开始）。可选：`start` 进局前的真实操作（格式同 `layout_states.actions`）、`prepare_js`（t0 前跑一次）、`steps` `[{"at_s": 秒, "js": "..."}]` 按真实时间跑的后续操作（转向、松手）、`run_s`（默认 5，2～20，要包含倒计时）、`settle_ms`（默认 1000）、`min_move`（默认 20）、`align`（`"move"` 默认 / `"drive"`）、`query`（宿主参数）、`note`。没有物理、没有自己会动的东西的游戏写 `{"n/a": "原因"}`。全民飞车漂移 v3.1：`{"start": [{"tap": "Canvas/MenuBottom/button/btnkj", "after": 2500}], "drive_js": "<W87 的 enter_level：按 RACE>", "track": "try{var R=__require('RunUI').RunUI;return R.car&&R.car.isValid?R.car:null;}catch(e){return null;}", "run_s": 10}`（全文 `briefs/out/W92/adapters/driftracer3d_frame_rate.json`） |

v7.8 全民飞车漂移的正式适配文件（原型三个适配文件合成一个）：`briefs/out/W87/adapters/driftracer3d.json`。

例子（MusicSlice v30）：`evidence/W3a/musicslice-adapter.json`；Mabel：`mabel-adapter.json`；射击高手2048：
`mergeshot-adapter.json`；LunasJade（3.x）：`lunas-adapter.json`；细菌2048 v3：`germ-adapter.json`。

## 宿主

**2.x：`scripts/ad_regression/`（host.js + play.html + server.py），唯一的官方宿主**，广告回归和运行时回归共用。
合并自 Mabel r8、射击高手2048 v82–v84、MusicSlice v30、细菌2048 v3、Basil。和浏览器不同的默认值：

- 触摸只带 identifier/screenX/screenY/force（`touch=full` 才带 clientX/pageX）——细菌2048 原件因此点 PLAY 没反应。
- 适配层换掉 `document.body` 之前先保存真实 body（`window.__NBody`），Retry 弹窗和广告遮罩挂上去看得见。
- 没有 createBannerAd / createInterstitialAd（`legacyads=1` 才给不出广告的空实现）。
- 胶囊按钮 `getMenuButtonBoundingClientRect` = 实测 87×32，距右 10，状态栏下 4。
- 音频 `src=""`（引擎回收播放器）记成「地址已清空」，不是音频错误。
- canvas 不能导出 WebP（`toDataURL('image/webp')` 返回 PNG），图片能正常解码（Basil / Mabel 的真机情况）。
- 外部网络请求全部记录并拦下（`window.__net`，日志 `net-*` 行）；服务器把每个包内文件 GET 记成 `http-get` 行。

URL 参数（都要主动打开）：

| 参数 | 作用 | 来源 |
|---|---|---|
| `pkgprog=1&pkgms=N` | 分包按进度事件慢慢下完，共 N ms | D4 2.2 |
| `stallpkg=0.4` | 分包进度到 40% 后不动 | D4 2.2 |
| `failpkg=<名字>` / `hangpkg=<名字>` | 该分包第一次失败 / 不回调 | D4 2.2 |
| `nthpkg=<名字>:K&nthmode=fail\|hang` | 第 K 次加载该分包失败 / 卡住 | D6 3 |
| `failfile=<子串>&failfile_n=K` / `hangfile=...&hangfile_n=K` | 读包内文件失败 / 不回调前 K 次 | D6 3 |
| `accesshang=1` | `fs.access` 不回调 | D6 3 |
| `failrequire=<子串>` | require 该文件抛错 | D6 |
| `missing=true\|false\|undefined\|throw`，`numbool=1`，`reset=1` | 读不存在的存档键返回什么 / 清存档 | D6 4 |
| `sdk=missing`，`opendata=missing` | 没有 SDKVersion / 没有 getOpenDataContext | D6 8，D5 5.3 |
| `imghang=<子串>&imghang_n=K`，`datauri=error` | 图片不回调 / data: 图片报错 | D4 |
| `webpenc=...`，`webp=...` | canvas WebP 导出 / 解码能力 | D2，D4 |
| `ad=manual\|complete\|cancel\|error\|pending`，`adms=N` | 广告模式；`pending` = 永远不回调 | D7 9 / 13 |
| `legacyads=1` | 提供横幅/插屏空实现 | D5 |
| `login=...`，`mission(s)=...`，`__setMission()` | 登录计数、侧边栏任务 | D4 |
| `mouse=1` | 鼠标转 TikTok 触摸（运行器总是带上） | - |
| `dev=iphone14\|se` | 机型（点）：iPhone 14 = 390×844、pixelRatio 3、状态栏 47、胶囊 293/51/380/83、安全区底 810；SE = 375×667、pixelRatio 2、状态栏 20、胶囊 278/24/365/56（横向是推算的）、安全区底 667。套件同时用 CDP 把页面设成同样大小 | v7.8 B30（Saul iPhone 14 实测） |
| `capsule=pt\|px` | `getMenuButtonBoundingClientRect` 按点给，或每个值乘 pixelRatio（Saul 的 iPhone 2026-10-29 返回的是像素）；`getSystemInfoSync` 始终按点 | v7.8 B30、U1 |

v7.8 起两个宿主（2.x 和 3.x）都有：`window.__gateLog`（`ad-create`、`ad-show`、`toast`、`modal`、`capsule-rect`，用宿主自己的时钟
`window.__gateNow()`）、`window.__gateDevice`，宿主日志里 `scene-loading` / `scene-launch`（首页场景开始加载的时间点）和
`subpackage` / `subpackage-ok` / `subpackage-fail`。3.x 宿主另认 `reset=1`（= `fresh=1`）、`ad=`（= `ads=`）、`dev=`、`capsule=`，
并把广告、toast、modal、主页回访 / 加桌面调用写进日志。原型里的副本宿主（`gates/host`、`gates/host3x`）不再需要。

**3.x：`scripts/runtime_regression/host3x/`**（来自 LunasJade 宿主，改成通用：分包大小由服务器按真实文件算，
`/__host/sizes.json`）。在独立的 GameGlobal 里跑包，参数 `fault=a,b`：`webp_nodecode`、`webp_slow`（WebP data URI
晚 800 ms 解码，超过引擎 500 ms 判定）、`img_events_only`（图片只认 addEventListener，不认 onload 属性）、
`res_fail[N]` `res_hang[N]` `res_stall[N]`（resources 分包，第 N 次）、`wasm_*`、`modal_nocb`、`storage_throw`、
`caniuse_false`、`no_ads`、`no_ttminis`、`firstrun`；`bps=<字节/秒>` 限速；`ads=complete,cancel,...`。
`__H.summary()` 有第一帧时间（`marks.firstDraw`）、WebP 判定、`__H.sprites()`、`__H.fps()`。

## 广告期间的声音（D7 第 9 条，v7.5 只警告）

`ad_regression/cases.mjs` 每条 case 另做一项检查，不改 10 条 case 的判定：视频开播时和结束前，不能有循环 BGM 在响、
不能有音效在响或新播音效；结束后（看完、关闭、报错、超时、X）BGM 恢复、音效音量和被暂停的音效恢复。不合格写进
结果的 `warnings`（`<case>: ...`），不拒绝，`ad_regression.py` 的摘要里也有 `warnings`。原因：v7.5 只有 Marlows R5 一个完成游戏跑过（0 条警告），细菌2048 v1/v2
的 TikTok 包已清理，没有「坏包被拦」的证明，所以先不做硬门禁。循环 BGM 没恢复仍是 v7.4 的硬性问题。

## 计时有效性（D3 问题 4）

Ego 窗口被挡住时页面约 1 帧/秒（visibilityState 仍是 visible），按帧推进的加载被拉长。

- `chrome_touch.py` 计时模式（`"timing": true`）默认开低画质截屏流，计时前先等空白页到 30 帧/秒（最多 10 s，
  不计入时间），按秒记录 rAF 帧数（报告 `frame_rate`）。最后一个 mark 之前任何一整秒低于 30 帧 = 本次无效：
  `timing_valid: false`、退出码 2，不能当 LOAD-03 证据。`"screencast": false` 可关截屏流（帧率照样检查）。
  `remake-core/scripts/audit_startup_loading.py` 审核时也拒收：带 `frame_rate` 的计时报告只要 `timing_valid` 不是 true 就算不合格。
- 运行时套件：`lib.mjs` 的 `keepFrames(page)`、`fps(page)`、`MIN_FPS`；`startup3x` 每条 case 记帧率，中位数低于 30 判失败。

## 运行时资源清单（D7 第 14 条，D3 问题 5）

运行时拼路径的老游戏（细菌2048 v3：`r.load` 逃出静态清单）和 3.x SystemJS 包，`audit_runtime_resources.py` 静态展开不了，
`build_checked_zip.py` 一直要求的资源清单写不出来，大家只好绕过官方入口。替代门禁：

```
python3 -B runtime_regression.py run --package <包> --adapter <adapter.json> --suites network --work <目录>
python3 -B make_runtime_resource_manifest.py --native <包> --log <目录>/network/host-log.jsonl [--log ...] --out <清单.json>
```

宿主服务器记下的每个包内文件请求都必须在包里、状态 200；包里没有的文件（真机上就是缺资源）直接拒绝，不写清单。
favicon、被拦的外部请求、USER_DATA_PATH（ttfile://）列在 `excluded`。清单绑定每个文件的 sha256 和整包摘要，不能拿去
给别的构建用。证明：细菌2048 v3 静态生成器拒绝；运行记录 136 个文件里请求了 73 个，清单生成并核对通过；删掉一个被请求的
PNG 后进不了首页、清单拒绝（404）。`build_checked_zip.py --resource-manifest` 认这个格式：`audit_runtime_resources.audit()`
遇到 `runtime_resource_manifest.observed.v1` 就按整包摘要和每个文件 sha256 核对；**只在静态展开失败的包上认**，静态能展开的包
仍要用生成的清单。v7.7 起静态扫描按 `KIT_MANIFEST.json` 的哈希（含 `previous_sha256`）认出平台包 `main.js`，把它的
`loadScript(settings.jsList)` 展开成清单里的 `script_files`（jsList 里每个文件和 `webp-decode-probe.js`，都必须在包里），所以静态展开不了的原因
只剩运行时拼路径的业务代码和 3.x SystemJS；其他 `main.js` 和其他 `cc.assetManager.load*` 照旧算动态调用。以前业务代码干净、只因平台包
`main.js` 用了观测清单的游戏，再跑写包入口时观测清单会被拒（`this package expands statically`），改用 `audit_runtime_resources.py --native`
生成的静态清单。注意写包入口会先在产物段改构建目录（v7.7 `tiktok_finalize` 的 `finalize_native`：适配层三处、启动件、触摸和存档层加载行、App ID、PNG 压缩，取代 v7.5 的 adapter_fix），改完包的字节变了：先跑一次
`python3 remake-core/scripts/tiktok_finalize.py native --native <构建目录> --project <工程> --board <板块>`（或先跑一次 `build_checked_zip.py`），再在改过的目录上跑 network 套件、生成清单，否则清单会因整包摘要不同被拒。第二次 finalize 0 改动，所以写包入口再跑一遍也不会改变摘要；前提是单独跑和写包入口用同一个 `--project`（PNG 压缩缓存 `png-cache.json` 在工程的 `.tiktok-kit/` 里，换工程或不给工程会重新压缩）。
3.x 游戏用同一个命令，3.x 宿主服务器也写 `http-get` 行。

## 边界

宿主是模拟：没有真实 TikTok 运行时、真实广告、真实网络和手机性能。凡是根据模拟结果修的包，交付时写「待真机复测」。
