# 本机 Cocos Creator 版本表（英化包 10.2.7，Saul 2026-10-31）

开工第一件事是用原游戏的版本把中文原版导出成 Web（英化入口第 1 阶段）。2026-10-30 那批英化游戏每款都卡在这一步：香肠太难了多花约 37 分钟，Runaway Rush 约 46 分钟，Cube Digits 约 15 分钟，有一款还是 Saul 自己去 Cocos Dashboard 下的引擎。照下表做，第一次就能构建。

**先确认版本**：2.4 工程看 `project.json` 的 `version`，3.x 工程看 `package.json` 的 `creator.version`。编辑器都装在 `/Applications/Cocos/Creator/<版本>/CocosCreator.app`，命令行是里面的 `Contents/MacOS/CocosCreator`。同一时间整台电脑只跑一个构建：先 `pgrep -fl "MacOS/CocosCreator .*--build"`，有就等它结束。构建都在工程的副本上做，原工程一个文件都不动。

| 版本 | 怎么构建（这台电脑上实测能用的写法） | 已知问题 |
|---|---|---|
| 2.4.15 | `--path <工程> --build "platform=web-mobile;debug=true"`；卡在导入资源不动时加 `--no-sandbox --disable-gpu-sandbox --disable-gpu` | 新重塑游戏固定用它 |
| 2.4.3 | 把本包的 [`assets/build-worker-canvas-compat/`](../assets/build-worker-canvas-compat/README.md) 整个复制到工程副本的 `packages/` 下，再加 `--use-gl=desktop`：`--use-gl=desktop --path <工程> --build "platform=web-mobile;debug=true"`（香肠太难了 10-31 用这个写法出过 Web 和 TikTok 包，日志 `Built bytedance successfully`） | 不加这个扩展，构建进程拿不到 WebGL，报 `Device._initCaps`。扩展只在编辑器的资源构建进程里用 Canvas，导出的游戏还是 WebGL，也不进游戏包。平台包的加载保护要用下载器索引，2.4.3 没有，第 5 阶段出包时要补 |
| 2.4.4 | **不用 2.4.4 构建，改用 2.4.5**，并在 `docs/english/engine.txt` 写一行「原工程 2.4.4，用 2.4.5 构建」 | 2.4.4 在这台电脑上一次都没构建成功（WebGL 初始化错误；`--use-gl=swiftshader`、`--use-gl=desktop --disable-features=Metal` 都试过，Saul 10-31 用 Dashboard 重装也一样）。Runaway Rush 就是用 2.4.5 过的 |
| 2.4.5 | 直接构建，不加参数 | — |
| 2.4.6、3.0.0 | 照同一大版本的写法构建（2.4.6 照 2.4.5，3.0.0 照 3.6.2） | 这台电脑上还没构建过。第一次用时把结果（成功的写法或报错）补进本表 |
| 3.6.2 | `--project <工程> --build "platform=web-mobile;debug=true"`，不加别的参数 | 3.x 工程用 `--project`；`--path` 只对 2.4 有效，3.x 用了会找不到工程 |
| 3.7.1 | 同 3.6.2 | 构建成功时退出码也是 36。命令行构建时平台的收尾步骤没跑，web-mobile 导出里缺 `index.html`、`index.js`、`style.css`：照 Cube Digits 的做法，用 3.7.1 自带模板（`CocosCreator.app/Contents/Resources/resources/3d/engine/templates/web-mobile/` 下的 `index.ejs`、`index.js.ejs`、`style.css`）补上，做法记在 `！游戏学习库/游戏文件/CC3x立方体数字cubeDigits/docs/test/redesign371-final/official-entry-repair.json` |
| 3.8.8 | 同 3.6.2 | 官方说成功的退出码是 36（32 是参数错，34 是构建失败），以导出目录里的文件为准。ad-boost 的测试用它构建过，退出码 36、产物正常 |

**看构建成没成功**：不只看退出码。导出目录里要有 `index.html`（3.7.1 照上面补）和这次改过的图，再用 [`scripts/check_export_images.py`](../scripts/check_export_images.py) 核对导出里的图是不是工程里现在的图。

**表里没有的版本**：先看 `/Applications/Cocos/Creator/` 下有没有（可能是新装的），有就照同一大版本的写法试，成了补进本表。没有就用大白话告诉 Saul 缺哪个版本，同时接着改源码，不停手；能不能用相近的版本代替，由 Saul 定。

更多命令行参数见 [真实 Cocos 运行](../../remake-core/references/cocos-runtime.md)。调用次数和成功次数的统计（10-24～10-31 的 Codex 记录）在 `！Skill更新/Skill修改要求总表_去重_20261029.md` 第 15 条。
