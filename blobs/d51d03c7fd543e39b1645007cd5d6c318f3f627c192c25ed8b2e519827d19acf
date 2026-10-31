# 用户本地试玩：生成链接前落实手机视口（2026-10-25）

触发于用户亲自体验 Cocos 游戏的任何入口：预览、试玩、游玩、打开游戏、本地看一下、恢复旧试玩链接，以及重塑/美化/英化过程中和随测试包附带的本地链接。仅试玩时走本页的轻量交接，不启动全量测试、美术重审、关卡或奖励矩阵。

- 交链接之前，默认将真实游戏放在同源固定手机尺寸 iframe 中。竖屏内部视口默认390×844 CSS px；项目明确其他机型则用该机型，横屏默认844×390。
- 桌面宽窗口周围保留留白，尺寸不超过一部手机；窗口变大不把游戏放大全屏。小窗口只整体等比缩小，iframe 内部尺寸不变，不裁掉游戏/控件、不要求用户手动缩浏览器或切开发者工具。
- 使用当前共享 `scripts/serve_preview.py`，默认已经实施手机外壳。用户试玩用 `--snapshot --keep`，默认自动请求打开独立 Google Chrome 窗口，同时把本地链接写在回复中。无需用户先点链接或再说“打开浏览器”。不能直接把 `python -m http.server`、裸导出 `/index.html`、Vite 全窗口地址或旧版预览脚本的链接交给用户。
- 用可用的浏览器接口读回准确 URL 和实际可见窗口，再确认首页/PLAY；`PREVIEW_BROWSER status=launch_requested` 仅说明已提交启动请求。Chrome 缺失或启动失败时保留可用链接并报告具体错误，不静默打开其他浏览器。工具设置禁止浏览器访问时停止对应操作，不绕过；可继续离线验证。
- 已有同版可用窗口时核对后复用并置前，不为每次截图、刷新或继续游玩重复弹窗；只在没有对应窗口或明确新版本时启动。
- 恢复旧链接也先检查外壳；可在原端口重启当前服务以保留 origin/存档。外壳在服务层生成，不改已验证的 Web/Native 导出或 ZIP，不清存档，不凭此重新打包。
- 手机外壳必须以 `Permissions-Policy: fullscreen=()` 和 iframe `allow="fullscreen 'none'"` 禁止游戏自动全屏；真实触摸 PLAY 后再次核 iframe 内部尺寸及外框，防止首页合格、开局却铺满窗口。外壳策略不改 Web/Native 产物。
- 发链接前只做相称检查：桌面宽窗口下读回 iframe 内390×844（或明确尺寸）、外框未放大且留白；小窗口整体缩放不溢出；确认真实游戏首页与 PLAY/开始可用。HTTP200、标题正确或设置手机 UA 单独都不够。
- 本次修复仅测显示容器和一次开始操作，不重跑已通过的全游戏CI。验证完成后关闭自有 QA 页面；保留正在交给用户的 Chrome 窗口与试玩服务。用户结束或被新版替代后，通过受支持接口关闭准确 URL 对应的自有页面，再关闭服务并核实；不退出整个 Chrome、不清登录/存档，不关闭用户其他页面。

```sh
python3 scripts/serve_preview.py --directory <同版Web导出> --snapshot --keep --project <工程> --name "游戏 用户试玩"
# 项目明确机型时：--phone-width 393 --phone-height 852
# 横屏游戏：--orientation landscape
```

`--no-browser` 显式禁止自动打开窗口，只用于内部准备或用户要求不弹窗；`--open` 可在不保留服务时显式请求 Chrome。普通内部服务默认不打开浏览器。

`--raw` 仅供必须使用顶层 Canvas 的内部自动化 QA，不能与 `--keep` 合用，打印的内部 URL 不得作为用户试玩链接。旧项目复制的脚本可能没有手机外壳，优先使用当前共享脚本；不能靠旧记录里写过“手机预览”就认定已落实。

**试玩链接冒烟（v7.8，总表 B21 / B30 F）**：`--keep` 起服务后、打印链接之前，自动在这个链接上按 Saul 的用法点一次看广告（cocos-game-check 的 `runtime_regression.py` trial_smoke，套件 `trial_link`）：电脑窗口 1180×960、清存档，等场景稳定，真实鼠标点到看广告入口；2.5 秒内模拟广告窗必须盖在游戏上面（画面中心点到的是广告窗），点「模拟看完」后游戏必须有变化。不过就**不给链接**（退出码 1，打印原因）；没法跑（没有 Ego、首页没找到看广告入口）就打印「试玩链接冒烟没跑：原因」再给链接；导出里不调用 `createRewardedVideoAd` 的不跑。看广告入口不在首页一层的，用 `--adapter <运行时 adapter.json>`，在它的 `trial` 里写 `taps`（节点路径，按顺序点）和 `reward_js`（返回奖励数值）。别的链接也能手动跑：`python3 -B cocos-game-check/package-check/scripts/runtime_regression.py trial --url http://127.0.0.1:端口/ [--adapter ...]`。英化包的入口 `cocos-game-to-english/scripts/serve_preview.py` 转到同一个 `remake-core/scripts/serve_preview.py`（v7.8 前它指向不存在的 cocos-game-core，起不来）。原因：全民飞车漂移 v1～v3 的旧试玩宿主把模拟广告窗挂在适配器换掉的 body 上，点看广告后什么都看不到，像卡死。往页面上加的元素一律挂在画布的父节点上。

手机比例（B7）：默认链接就是固定的竖屏手机（390×844，窗口小只等比缩小，不放大）；`--raw` 是检查用的整窗页面，不能给用户。

已有广告入口的重塑/英化可玩候选，默认按[用户可操作广告模拟](../../remake-ads/references/manual-ad-simulation.md)启用 `--ad-simulator`，交接前核真实按钮→模拟结果→原奖励业务。仅交试玩不因此扩大为全量验收。
