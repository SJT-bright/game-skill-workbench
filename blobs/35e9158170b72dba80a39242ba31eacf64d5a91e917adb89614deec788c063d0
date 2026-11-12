## 浏览器测试路线（用户 2026-11-06，取代旧回退规则）

英化人工操作用 **Computer Use + Edge**。自动检查仍在 **Ego Lite** 独立 TaskSpace 执行原有脚本并复用有效证据。英化的 Google Chrome 只在美工试玩和最终测试包交接时打开。 其他流程的自动检查按原 Ego 路线执行。缺少对应能力时继续离线工作，记录实际未测项。详见 `<SKILLS_DIR>/remake-core/references/browser-testing-policy.md`。

# 用户本地试玩：生成链接前落实手机视口（2026-10-25）

**默认 BGM（2026-11-11）**：已确认首页有配乐时，在现有预览命令加 `--expect-home-bgm`；首页检查复用同一 Ego 页补最多一次普通 PLAY 与播放时间采样。漏掉默认请求或普通输入后仍停住时拦截，浏览器 autoplay 限制与 TikTok 真机输出分列。细则见 [BGM 分域与轻量核验](bgm-startup-preview.md)，不重跑完整声音矩阵。

英化使用[两次正式试玩交接](../../cocos-game-to-english/references/preview-handoff.md)。英化入口的 `--keep` 保留内部服务，窗口由交接入口打开。

其他普通用户预览触发于用户亲自体验 Cocos 游戏的入口：预览、试玩、游玩、打开游戏、本地看一下、恢复旧试玩链接，以及重塑/美化/英化过程中和随测试包附带的本地链接。仅试玩时走本页的轻量交接，不启动全量测试、美术重审、关卡或奖励矩阵。

- 交链接之前，默认将真实游戏放在同源固定手机尺寸 iframe 中。竖屏内部视口默认390×844 CSS px；项目明确其他机型则用该机型，横屏默认844×390。
- 桌面宽窗口周围保留留白，尺寸不超过一部手机；窗口变大不把游戏放大全屏。小窗口只整体等比缩小，iframe 内部尺寸不变，不裁掉游戏/控件、不要求用户手动缩浏览器或切开发者工具。
- 使用当前共享 `scripts/serve_preview.py`，默认已经实施手机外壳。非英化的用户试玩用 `--snapshot --keep`，默认自动请求打开独立 Google Chrome 窗口，同时把本地链接写在回复中。无需用户先点链接或再说“打开浏览器”。不能直接把 `python -m http.server`、裸导出 `/index.html`、Vite 全窗口地址或旧版预览脚本的链接交给用户。
- 用可用的浏览器接口读回准确 URL 和实际可见窗口，再确认首页/PLAY；`PREVIEW_BROWSER status=launch_requested` 仅说明已提交启动请求。Chrome 缺失或启动失败时保留可用链接并报告具体错误，不静默打开其他浏览器。工具设置禁止浏览器访问时停止对应操作，不绕过；可继续离线验证。
- 已有同版可用窗口时核对后复用并置前，不为每次截图、刷新或继续游玩重复弹窗；只在没有对应窗口或明确新版本时启动。
- 恢复旧链接也先检查外壳；可在原端口重启当前服务以保留 origin/存档。外壳在服务层生成，不改已验证的 Web/Native 导出或 ZIP，不清存档，不凭此重新打包。
- 手机外壳必须以 `Permissions-Policy: fullscreen=()` 和 iframe `allow="fullscreen 'none'"` 禁止游戏自动全屏；真实触摸 PLAY 后再次核 iframe 内部尺寸及外框，防止首页合格、开局却铺满窗口。外壳策略不改 Web/Native 产物。
- 发链接前只做相称检查：桌面宽窗口下读回 iframe 内390×844（或明确尺寸）、外框未放大且留白；小窗口整体缩放不溢出；确认真实游戏首页与 PLAY/开始可用。HTTP200、标题正确或设置手机 UA 单独都不够。
- Agent 对显示容器和一次开始操作的检查在 Ego 内完成；用户 Chrome 窗口只作试玩交接，不在其中运行验收。验证完成后关闭自有 QA 页面；保留正在交给用户的 Chrome 窗口与试玩服务。用户结束或被新版替代后，通过受支持接口关闭准确 URL 对应的自有页面，再关闭服务并核实；不退出整个 Chrome、不清登录/存档，不关闭用户其他页面。

```sh
python3 scripts/serve_preview.py --directory <同版Web导出> --snapshot --keep --project <工程> --name "游戏 用户试玩"
# 项目明确机型时：--phone-width 393 --phone-height 852
# 横屏游戏：--orientation landscape
```

`--no-browser` 显式禁止自动打开窗口，只用于内部准备或用户要求不弹窗；非英化的 `--open` 可在不保留服务时显式请求 Chrome。普通内部服务默认不打开浏览器。

`--raw` 仅供必须使用顶层 Canvas 的内部自动化 QA，不能与 `--keep` 合用，打印的内部 URL 不得作为用户试玩链接。旧项目复制的脚本可能没有手机外壳，优先使用当前共享脚本；不能靠旧记录里写过“手机预览”就认定已落实。

**试玩链接冒烟（v7.8，总表 B21 / B30 F）**：`--keep` 起服务后、打印链接之前，自动在这个链接上按 Saul 的用法点一次看广告（cocos-game-check 的 `runtime_regression.py` trial_smoke，套件 `trial_link`）：电脑窗口 1180×960、清存档，等场景稳定，真实鼠标点到看广告入口；普通试玩检查入口有可见响应；专门的模拟链接要求 2.5 秒内显示可操作的广告面板，再等待看完按钮解锁。链接冒烟只说明试玩的响应；奖励是否正确，用业务前后值、实际使用和应保存状态另行核对。不过就**不给链接**（退出码 1，打印原因）；没法跑（没有 Ego、首页没找到看广告入口）就打印「试玩链接冒烟没跑：原因」再给链接；导出里不调用 `createRewardedVideoAd` 的不跑。看广告入口不在首页一层的，用 `--adapter <运行时 adapter.json>`，在它的 `trial` 里写 `taps`（节点路径，按顺序点）和 `reward_js`（返回奖励数值）。别的链接也能手动跑：`python3 -B cocos-game-check/package-check/scripts/runtime_regression.py trial --url http://127.0.0.1:端口/ [--adapter ...]`。英化包的入口 `cocos-game-to-english/scripts/serve_preview.py` 转到同一个 `remake-core/scripts/serve_preview.py`（v7.8 前它指向不存在的 cocos-game-core，起不来）。原因：全民飞车漂移 v1～v3 的旧试玩宿主把模拟广告窗挂在适配器换掉的 body 上，点看广告后什么都看不到，像卡死。往页面上加的元素一律挂在画布的父节点上。

手机比例（B7）：默认链接就是固定的竖屏手机（390×844，窗口小只等比缩小，不放大）；`--raw` 是检查用的整窗页面，不能给用户。

普通试玩使用原适配器。用户要体验广告结果时，另按[用户可操作广告模拟](../../remake-ads/references/manual-ad-simulation.md)启动同版本的独立链接并标明“广告模拟试玩”。

**给链接前自动截首页图（生成时预防 P21 ⑤ 后半）**：给人用的链接（`--keep`、`--open`、`--idle-minutes 0`）读回核对以后，`serve_preview.py` 自己通过 Ego 官方 Page 接口截一张游戏页的图，并读页面探针。全黑、只有一种颜色、12 秒后还停在加载页、页面报错（未捕获异常、未处理的 Promise、console.error、资源加载失败）就**不给链接**，退出码 1。没有浏览器、截图超时、浏览器没写出图时打印「没截图」，照样给链接，不算通过。Cocos 3.x 导出还没校准，有问题只警告。截图路径打在输出里，交链接前自己看一眼。不要另外手写截图或 sleep 等待来代替它。

**手机外壳里鼠标就是手指（P13 ④）**：外壳里的游戏页由服务自动加上 `assets/preview-touch-bridge.js`，只改服务给出的 HTTP 内容，不改导出。在画布上按下、拖动、松开鼠标，会变成 touchstart、touchmove、touchend；窗口失焦时变成 touchcancel。字段有 identifier、clientX/clientY、screenX/screenY（等于游戏页坐标，和 TikTok 一样）、pageX/pageY 和 force，平台包 touch24、tiktok-touch-3x 和 TouchOwner 都能直接读。转换过的那次鼠标事件不再往下传，引擎不会收到两次。点在画布以外（模拟广告面板、vConsole）的照旧按鼠标处理。`--raw` 内部 QA 页面不加这个脚本。只认触摸的游戏在预览里也能拖动，不要在游戏里另写鼠标兼容代码。
