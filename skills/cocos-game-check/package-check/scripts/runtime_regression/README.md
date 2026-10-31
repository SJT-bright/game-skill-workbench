# runtime_regression 套件约定（suite contract）

运行器：`../runtime_regression.py`。字段全表和每个套件的证明见 `../../references/runtime-regression.md`。

## 运行器做什么

```
python3 -B runtime_regression.py run --package <解压后的包或 .zip> --adapter <adapter.json> [--suites a,b] [--out result.json] [--work 目录]
python3 -B runtime_regression.py required --package <包> --adapter <adapter.json>   # 打印这个包必须跑的套件
python3 -B runtime_regression.py list
```

1. 读 `suites/*.json`（套件说明），按包内容和 adapter 算出必跑套件（`required_suites(files, adapter)`）。
2. 每个套件单独起一个宿主服务（只绑 127.0.0.1，套件结束就停）：Cocos 2.x 用 `../ad_regression/`（host.js + play.html +
   server.py），3.x 用 `host3x/`。包是 3.x 的判断：有 `src/system.bundle.js` 或 `cocos-js/cc*.js`，adapter 可用
   `"engine"` 指定。
3. 写 `entry.mjs`（`globalThis.CFG = {...}; await import(<suite>.mjs)`），执行
   `ego-browser nodejs -e "await import(<entry>)"`，读回套件写的结果 JSON。
4. 没有浏览器、没有 adapter、缺套件 `needs` 里的字段、套件没写结果、超时、任何一条 case 不过 = 拒绝（`RuntimeRefused`），
   不会跳过。`warnings` 只记录，不拒绝。

Python 侧给父级用：`run(package_dir, adapter_path, suites=None, work=None)` 通过返回摘要，否则抛 `RuntimeRefused`
（`error.summary` 带摘要）；`required_suites(files, adapter)`，`files` 是 `{相对路径: bytes}`，`adapter` 是 dict 或路径。

## 一个套件 = 两个文件

`suites/<name>.mjs` 和 `suites/<name>.json`（文件名就是套件名，只用小写字母、数字、下划线）。

### `<name>.json`（说明，键只能是下面这些）

```json
{
  "name": "startup",
  "about": "一句话说明",
  "applies": ["tiktok"],
  "needs": ["home"],
  "fields": ["retry", "retry_label"],
  "engines": ["2.x", "3.x"],
  "timeout_s": 600,
  "owner": "W3a",
  "proof": "evidence/W3a/startup-*.json"
}
```

- `applies`：满足任意一条就必跑。`tiktok`（根目录有 game.js，所有 TikTok 包）、`rewarded_ads`（JS 里有
  createRewardedVideoAd）、`missions`（JS 里有 startEntranceMission / addShortcut / navigateToScene）、`remake_home`
  （adapter 里 `"remake_home": true`）、`adapter:<字段>`（adapter 里有这个字段）。
- `needs`：必跑时 adapter 必须有的字段，缺了就拒绝并写出缺哪个。
- `fields`：套件会读、但可选的 adapter 字段。adapter 里出现不在（广告键 ∪ 核心键 ∪ 所有套件 needs/fields）里的键会被拒绝，
  所以新字段一定要登记在这里。
- `engines`：默认两个都支持。`timeout_s`：整套件上限，默认 300。

### `<name>.mjs`（脚本）

运行器注入的 `globalThis.CFG`：

| 键 | 含义 |
|---|---|
| `suite` | 套件名，结果里的 `suite` 必须等于它 |
| `space` | Ego 任务空间名：`$RUNTIME_REGRESSION_SPACE`，否则每次运行唯一的 `tiktok-runtime-<suite>-<pid>-<随机>`（同名空间会被别的运行接管） |
| `engine` | `"2.x"` 或 `"3.x"` |
| `base` | `http://127.0.0.1:<port>`；`hostPage` 宿主页（`/__host/play.html`） |
| `hostQuery` | 每个 URL 都要带的基础参数（`mouse=1&run=<suite>` + adapter.host_query） |
| `package` / `port` | 包目录 / 端口 |
| `adapter` / `adapterPath` | adapter 对象 / 文件路径 |
| `bootTimeoutMs` | adapter.boot_timeout_s × 1000，默认 60000 |
| `logFile` | 宿主服务写的日志（JSON lines：页面 beacon + 每个 GET 请求 `{"kind":"http-get"}`） |
| `resultFile` | 套件必须写的结果 |
| `evidenceDir` | 截图、录屏、额外证据放这里 |
| `lib` | `lib.mjs` 的 file URL |

结果 JSON（写到 `CFG.resultFile`）：

```json
{"suite": "startup", "passed": true,
 "cases": [{"id": "pkgprog_slow", "passed": true, "detail": {"homeMs": 3100}}],
 "warnings": ["..."], "evidence": {"log": "<path>"}, "fatal": null}
```

`passed` 只有在没有 `fatal`、至少一条 case、全部 case `passed === true` 时才是 true；运行器自己再判一遍，不信套件的
`passed`。

### 推荐写法（lib.mjs）

```js
const L = await import(globalThis.CFG.lib);
await L.suite(async ({ out, page }) => {
  const b = await L.boot(page, 'pkgprog=1&pkgms=40000');   // 等 adapter.home（没有就 ready / 场景存在）
  out.add('pkgprog_slow', b.ok, { ms: b.ms, errors: b.errors });
});
```

`lib.mjs` 提供：`result`、`evidence(name, data)`、`open/close`、`url(query)`、`ev`、`adapterCall(page, code)`、
`viewport`、`waitFor(page, code, ms)`、`boot(page, query, {until, timeoutMs})`、`hostLog`、`errors`、`hostState`、
`findLabels(page, regexp)`、`tap(page, x, y)`（真实指针，宿主转成 TikTok 触摸）、`locate(page, adapterCode, labelRegexp)`、
`suite(body)`（开页、存结果、关页）。一次只开一个 Ego 页面；每次 `page.evaluate` 要短（Ego 单次上限 15 秒），等待放在 Node 侧。
v7.5 新增（旧调用不变）：`touchTap(page, x, y)`（真实触摸）、`keepFrames(page)`（低画质截屏流，防止窗口被挡时降到
1 帧/秒）、`fps(page, ms)`（页面 rAF 帧率）、`MIN_FPS`（30；计时类 case 低于它判本次无效）。

## 宿主参数（URL query，2.x 宿主 host.js）

完整列表和来源见 `references/runtime-regression.md` 的「宿主」一节（2.x 宿主参数表、3.x 宿主 `host3x/` 的 `fault=`）。套件要新的宿主能力，写到
`briefs/out/W3b/HOST_REQUESTS.md`，不要改 host.js。

## 广告

广告计时暂停修改：本目录的套件不改 `ad_regression/cases.mjs`，也不改广告 case 的期望。

## v7.5 里的套件

`startup`、`network`（2.x）和 `startup3x`（3.x），都归 W3a。W3b 的玩法类套件（missions、capsule、result_x2、ad_entry、
save_claim、modal_pause、home_motion/interaction）2026-10-29 改到下一版，不在本目录；运行器和测试不依赖它们。
