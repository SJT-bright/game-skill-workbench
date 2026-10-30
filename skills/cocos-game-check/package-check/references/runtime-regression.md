# 出包前运行时回归（runtime regression，v7.5）

用途：在模拟的 TikTok 宿主里运行**上传包本身**（真实的 game.js → adapter → 引擎），制造启动/网络/图片故障，
拦住网页版测不出的问题。这是浏览器模拟，不是真机，也不是真实广告；用它通过的包仍要按规则真机复测。

## 命令

```
cd cocos-game-check/package-check/scripts
python3 -B runtime_regression.py list
python3 -B runtime_regression.py required --package <解压包或.zip> --adapter <adapter.json>
python3 -B runtime_regression.py run --package <解压包或.zip> --adapter <adapter.json> [--suites a,b] [--out r.json] [--work 目录]
```

- 必须有 Ego 浏览器（`ego-browser`）和 adapter；缺任何一个、缺套件需要的字段、套件没写结果、超时、任何一条 case
  不过，都是拒绝（`RuntimeRefused`），不会跳过。`warnings` 只记录，不拒绝。
- 每个套件单独起宿主服务，只绑 127.0.0.1，套件结束就停。环境变量 `RUNTIME_REGRESSION_SPACE` 可指定 Ego 任务空间名。
- 出包入口已接入：`check_package.check()`（`build_checked_zip.py`、`prepare_delivery.py` 都经过它）对每个有 game.js 的包
  用 `required_suites(files, adapter)` 算出必跑套件、`run(package_dir, adapter_path, suites)` 跑，和激励广告回归用同一个
  adapter（`--ad-regression` 或 `$TIKTOK_AD_REGRESSION_ADAPTER`）。没跑通就拒绝出包，结果写在报告的 `runtime_regression`。
- 套件约定（给写套件的人）：`scripts/runtime_regression/README.md`。

## v7.5 的套件

| 套件 | 引擎 | 何时必跑 | 内容 | 证明 |
|---|---|---|---|---|
| `startup` | 2.x | 所有 TikTok 包 | 冷启动；分包慢进度 40 s；分包卡在 40%；分包失败一次；第 2 次分包失败/卡住；`assets/main/config` 失败/卡住一次；没有 SDKVersion；没有 getOpenDataContext；存档键不存在。要求：进首页，最多点 1 次 Retry，Retry 在故障后 20 s 内出现（慢进度一次都不许要 Retry）。生命周期（指尖麻将 v57）：加载中 Date.now 跳 12 秒且不发 onHide、onHide+60 秒+onShow（都不许出 Retry）、第一张包内图片不回应（最多 1 次 Retry），之后用 `play` 真点首页 PLAY，必须离开首页。宿主按 TikTok：document.hidden 恒 false、不发 visibilitychange、游戏加的网页元素不显示（DOM Retry 不算） | 指尖麻将 v57 拒（时钟跳 12 秒、图片不回应后首页按钮全锁）/ v58 过；Mabel r7 拒（慢进度要 Retry、卡 40% 要 2 次）/ r8 过；射击高手2048 v81 拒（4 条卡死 + SDK + 缺键提示 unavailable）、v82/v83 拒 sdk 和 opendata、v84 只拒 opendata；MusicSlice v29b 拒 sdk+opendata、v30 这两条过 |
| `network` | 2.x | 所有 TikTok 包 | 启动、首页停 5 s、进一关玩 `level_timeout_s` 秒，记录所有外部请求（tt.request、downloadFile、connectSocket、XHR、fetch、WebSocket、sendBeacon、图片）。不在 `runtime_regression/network-allowlist.json` 的域名 = **警告**并列出。只有没进首页、`enter_level` 抛错才拒绝 | MusicSlice v29b 警告 pas.qq.com（启动 3 次 + 关内 2 次）/ v30 无警告 |
| `startup3x` | 3.x | 所有 3.x TikTok 包 | 1.5 MB/s 冷启动包内第一帧 ≤ `first_frame_ms`（默认 5 s）；`webp_slow` 首页所有精灵有贴图；`img_events_only` 出第一帧并进首页；每条记录帧率，<30 fps 判本次无效 | LunasJade v0.10.0 三条全拒（第一帧 14.8 s、0/14 贴图、无第一帧）/ v0.10.1 三条全过（0.6 s、14/14、60 fps） |

证据都在 `WORK/evidence/W3a/item2-*`、`item3-*`、`item4-*`。广告回归（10 条）仍由 `ad_regression.py` 单独跑，
规则见 `remake-ads/references/ad-timeout-and-regression.md`（v7.4 口径不变）。

已知没拦住的：MusicSlice v29b/v30 和射击高手2048 v81 在「分包卡在 40%」「config 卡住一次」时黑屏、没有 Retry——
这是真实缺口，startup 套件照样拒绝。

## adapter 字段

一个 adapter JSON 同时给广告回归和运行时回归用（`ad_regression.load_adapter` 也认下面这些键，v7.5 R1）。
值都是页面里执行的 JavaScript 函数体（`return ...`），除非另写。

| 字段 | 谁用 | 含义 |
|---|---|---|
| `request` `state` `ready` `exit` `exit_label` `no_music` `boot_timeout_s` `note` | 广告回归（v7.4） | 见 ad-timeout-and-regression.md；`boot_timeout_s` 也是运行时套件的启动上限（默认 60） |
| `home` | 所有运行时套件（必填） | 首页可用时返回 `true` |
| `retry` | startup | 返回 Retry 控件（cc.Node 或 `{x,y}` CSS 坐标）；不填就按文字找 |
| `play` | startup（必填） | 首页 PLAY 按钮（cc.Node 或 `{x,y}` CSS 坐标；Cocos 2.4 建议直接返回坐标）。生命周期用例真点它，点后 `home` 变 false（或 `in_level` 为 true）才算按钮有效。`home` 写成“首页画出来了”，不要用游戏自己的加载完成标记 |
| `in_level` | startup（可选） | 进了关卡返回 `true`；点 PLAY 后先弹窗、首页仍算可用的游戏要填 |
| `retry_label` | startup | Retry 文字的正则（默认 RETRY/Try again/Reload/重试/重新加载） |
| `startup_cases` | startup | 只跑这些 case（逗号分隔），调试用；出包时不要填 |
| `enter_level` | network | 从首页进一关（调用游戏真实的开始方法），返回 `true` |
| `level_timeout_s` | network | 关内停留秒数（默认 20） |
| `first_frame_ms` | startup3x | 第一帧上限，默认 5000 |
| `engine` | 运行器 | `"2.x"` / `"3.x"`；不填按包内容判断（有 `src/system.bundle.js` 或 `cocos-js/cc*.js` 是 3.x） |
| `host_query` | 运行器 | 每个 URL 都加的宿主参数（字符串） |
| `remake_home` `save_keys` `runtime_note` | 预留 / 说明 | `runtime_note` 是说明文字 |

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
