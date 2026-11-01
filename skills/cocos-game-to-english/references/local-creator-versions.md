# Cocos Creator 版本和已知问题（英化包 10.2.10，任何电脑都适用）

开工第一件事是用原游戏的版本把中文原版导出成 Web（英化入口第 1 阶段）。2026-10-30 那批英化游戏每款都卡在这一步：香肠太难了多花约 37 分钟，Runaway Rush 约 46 分钟，Cube Digits 约 15 分钟，有一款还是用户自己去 Cocos Dashboard 下的引擎。英化包是给别人用的，编辑器装在哪、装了哪几个版本，每台电脑都不一样（Saul 2026-10-31），所以不要假设路径，用脚本找。

**找编辑器、拿构建命令**：`python3 <skills>/cocos-game-to-english/scripts/find_creator.py --project <工程>`（Windows 把 `python3` 换成 `python`）。它读工程的版本（2.x 看 `project.json` 的 `version`，3.x 看 `package.json` 的 `creator.version`），按下面的顺序找本机的编辑器，再打印导出 Web 和出 TikTok 小游戏包的完整命令：

1. 用户设的 `COCOS_CREATOR`（CocosCreator 程序、`.app` 或它所在的文件夹）；
2. Cocos Dashboard 自己记下的已装编辑器：`<用户目录>/.cocos/profiles/editor.json`（macOS、Windows 都有）；
3. 常用安装位置：macOS `/Applications/Cocos/Creator/<版本>/CocosCreator.app`；Windows `C:\CocosDashboard\resources\.editors\Creator\<版本>\CocosCreator.exe`、`C:\ProgramData\cocos\editors\Creator\<版本>\CocosCreator.exe`。

工程那个版本没装时，先用同一小版本里最近的那个（2.4.4 → 2.4.5），在 `docs/english/engine.txt` 写一行「原工程 X，用 Y 构建」；同一小版本都没有，就用大白话请用户打开 Cocos Dashboard 下载那个版本，等的时候接着改源码，不停手。`find_creator.py --list` 列出本机所有编辑器。

**同一时间整台电脑只跑一个构建**：构建前跑 `find_creator.py --busy`，有构建在跑就等它结束。构建都在工程的副本上做，原工程一个文件都不动。

| 版本 | 怎么构建 | 已知问题（出处） |
|---|---|---|
| 2.4.15 | `--path <工程> --build "platform=web-mobile;debug=true"` | macOS 上构建卡在导入资源不动时，加 `--no-sandbox --disable-gpu-sandbox --disable-gpu`（Saul 的 Mac） |
| 2.4.3 | 把本包的 [`assets/build-worker-canvas-compat/`](../assets/build-worker-canvas-compat/README.md) 整个复制到工程副本的 `packages/` 下，命令最前面加 `--use-gl=desktop`：`--use-gl=desktop --path <工程> --build "platform=web-mobile;debug=true"` | 不加这个扩展，构建进程拿不到 WebGL，报 `Device._initCaps`（Saul 的 Mac，香肠太难了 10-31 用这个写法出过 Web 和 TikTok 包）。扩展只在 macOS 的 2.4.3 编辑器里起作用，导出的游戏还是 WebGL，也不进游戏包。平台包的加载保护要用下载器索引，2.4.3 没有，第 5 阶段出包时要补 |
| 2.4.4 | 同 2.4.15 | 在 Saul 的 Mac 上一次都没构建成功（WebGL 初始化错误；`--use-gl=swiftshader`、`--use-gl=desktop --disable-features=Metal` 都试过，重装也一样）。**构建报一次 WebGL 初始化错误就别再试，改用同一小版本里装了的另一个**（`find_creator.py` 选的最近的那个，例如 2.4.5），在 `docs/english/engine.txt` 记一行。Runaway Rush 就是用 2.4.5 过的 |
| 2.4.5、2.4.6 | 同 2.4.15 | — |
| 3.0.0、3.6.2、3.8.8 | `--project <工程> --build "platform=web-mobile;debug=true"` | 3.x 工程用 `--project`；`--path` 只对 2.4 有效，3.x 用了会找不到工程。官方说成功的退出码是 36（32 是参数错，34 是构建失败），以导出目录里的文件为准 |
| 3.7.1 | 同 3.6.2 | 退出码 36 也是成功。命令行构建时平台的收尾步骤可能没跑，web-mobile 导出里缺 `index.html`、`index.js`、`style.css`（Cube Digits 10-31）：跑 `python3 <skills>/cocos-game-to-english/scripts/fix_web_entry_3x.py --export <这次的 web-mobile> --project <工程>`，它用本机编辑器自带的 web-mobile 模板补上，只补缺的，不碰游戏文件（在 Cube Digits 的导出上补出来的三个文件，和当时修好、试玩过的逐字节相同）。3.6、3.8 导出缺入口页时也用它 |

**看构建成没成功**：不只看退出码。导出目录里要有 `index.html`（3.x 缺了照上面补）和这次改过的图，再用 [`scripts/check_export_images.py`](../scripts/check_export_images.py) 核对导出里的图是不是工程里现在的图。

**表里没有的版本**：照同一大版本的写法构建（2.x 用 `--path`，3.x 用 `--project`）。成了或出了新的问题，把写法和报错补进本表，写明是哪台电脑、哪款游戏。

更多命令行参数见 [真实 Cocos 运行](../../remake-core/references/cocos-runtime.md)。
