# 包的形式：唯一能交的包，和以前出过的错包（用户 2026-10-23）

所有叫法（打包、出包、上传测试包、检测包、压缩包、TikTok 平台包、正式包）都只交**一种**包。下面是它的样子、以前真实出过的错包，以及被 `make_tiktok_zip.py` / `verify_native_zip.py` 拒绝时怎么改。

## 正确的包长这样（SquareRush UPLOADFIX）

```
SquareRush_TikTok_test_v12.zip          ← 用户直接拖进 TikTok 后台，不解压
├── game.js                             ← 根目录直接是入口，没有外层文件夹
├── game.json                           ← "subpackages": [{"name": "resources", "root": "subpackages/resources/"}]
├── project.config.json                 ← "appid": 当前目标的 App ID
├── ccRequire.js / src/settings.js(2.4) 或 src/settings.json(3.x)   ← 分包声明同步
├── cocos/ 或 cocos2d-js-min.js、assets/internal、assets/main …     ← 主包：引擎、入口、首屏  ≤ 4,000,000 字节
└── subpackages/
    └── resources/                      ← 普通分包：只计入总包（总包 ≤ 30,000,000 字节）
        ├── game.js
        ├── config.json
        └── import/ native/ …
```

体积按**未压缩字节**算（ZIP 压缩后 7 MiB 不代表主包合格）。限额（2026-10-05 平台概览，非 Unity）：总包 30MB、主包 4MB、独立分包各 4MB、普通分包只计入总包；脚本按 30,000,000 / 4,000,000 字节执行，只能更严、不能调大。平台以后改了限额，先按新官方文档改 `verify_native_zip.py` 里的常量和日期，再出包。

## 以前出过的错包（全部禁止）

| 错包 | 怎么发现的 | 脚本怎么拦 |
|---|---|---|
| resources 留在主包，主包 8,754,975 字节 | TikTok 拒绝上传（SquareRush） | `main package … > 4000000`，列出主包最大的 5 个文件 |
| ZIP 里多一层文件夹 `Game/game.js` | 平台找不到根目录的 game.json | `outer folder` |
| Web（web-mobile，有 index.html）改名当 Native，或补个空 game.json | 不是小游戏运行时 | `web build` / `index.html at the root` |
| 源码 ZIP、工程目录、`.ts`/`.meta`/`library/`/`temp/` 进包 | 包很大、平台不认 | `source-project` |
| ZIP 套 ZIP（上传包里放 zip，或上传包和说明再压一层） | 平台只认最外层 | `zip-in-zip` |
| `__MACOSX`、`._xxx`、`.DS_Store`、`Thumbs.db` | Mac Finder 压缩带进来的 | 出包时自动不放进去；现成的包里有就 `junk` |
| 独立分包超 4,000,000 | 平台限额 | `independent subpackage` |
| 测试跳关 `__QA_LEVEL_JUMP__` 留在包里 | 玩家能跳关 | `level jump` |
| App ID 是旧游戏/别的应用的 | 上传到错的应用 | `App ID` |
| 中文/全角路径 | 部分环境解压出错 | `non-ASCII path` |

## 被拒绝了怎么改

- **主包超限**：把 `assets/resources`（和其他大 bundle）配成小游戏普通分包（见 SKILL 第 2 步），重新构建；启动链先加载分包、有进度和 Retry。不要删资源凑数，不要把资源挪成远程下载又不做失败恢复。首屏要用的图留主包，其余进分包。
- **总包超限**：压缩图（合图、降到实际显示 2 倍、去掉没用的图）、声音转码（mp3/ogg 合适码率）、删掉没用的资源；不能靠"不放进包"让游戏缺图。
- **外层文件夹**：`--native` 指向里面那层（有 game.js 的那层）。
- **Web 构建**：Cocos 里重新用 TikTok 小游戏构建配置导出 Native。
- **源码/套娃/垃圾**：`--native` 指向构建输出目录，不是工程目录；构建目录里别放其他 zip。
- **App ID 不对**：改构建配置的 appid，重新构建（不要只改 ZIP 里的 project.config.json）。
- **测试跳关**：用正式构建配置重新构建（去掉 QA 开关）。

## 检查现成的包（含别人的、旧的）

```sh
python3 verify_native_zip.py <包.zip> --expected-app-id <App ID> [--expected-tree <从这个ZIP独立解压的目录>] --report <新报告.json>
```

内置 TikTok 限额和禁止项（以前要手动传 `--max-*-bytes`，现在不用传，传了也只能更严）。通过只说明本地结构对，不代表平台接受、广告可用或真机正常。复核记录（如 Mosslight r1/r2）里每一轮都写：主包/总包字节、根入口、App ID、分包入口和 config 目录、JSON/JS 语法检查结果；平台上次报错的原因没查清的，照实写"未解决"。
