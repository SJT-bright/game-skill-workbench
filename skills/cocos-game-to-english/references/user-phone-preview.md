# 用户本地试玩：生成链接前落实手机视口（2026-10-25）

触发于用户亲自体验 Cocos 游戏的任何入口：预览、试玩、游玩、打开游戏、本地看一下、恢复旧试玩链接，以及重塑/美化/英化过程中和随测试包附带的本地链接。仅试玩时走本页的轻量交接，不启动全量测试、美术重审、关卡或奖励矩阵。

- 交链接之前，默认将真实游戏放在同源固定手机尺寸 iframe 中。竖屏内部视口默认390×844 CSS px；项目明确其他机型则用该机型，横屏默认844×390。
- 桌面宽窗口周围保留留白，尺寸不超过一部手机；窗口变大不把游戏放大全屏。小窗口只整体等比缩小，iframe 内部尺寸不变，不裁掉游戏/控件、不要求用户手动缩浏览器或切开发者工具。
- 使用当前共享 `scripts/serve_preview.py`，用户试玩用 `--snapshot --keep` 默认自动请求独立 Google Chrome 手机框窗口，回复同时保留本地链接，无需用户先点链接。已有同版窗口核对后复用；启动回执不等于窗口已可见，须通过可用接口读回准确 URL/窗口并核首页和开始。Chrome 缺失或启动失败如实报告；浏览器工具被设置禁止时停止对应操作，继续可做的离线工作。
- 恢复旧链接也先检查外壳；可在原端口重启当前服务以保留 origin/存档。外壳在服务层生成，不改已验证的 Web/Native 导出或 ZIP，不清存档，不凭此重新打包。
- 手机外壳必须以 `Permissions-Policy: fullscreen=()` 和 iframe `allow="fullscreen 'none'"` 禁止游戏自动全屏；真实触摸 PLAY 后再次核 iframe 内部尺寸及外框，防止首页合格、开局却铺满窗口。外壳策略不改 Web/Native 产物。
- 发链接前只做相称检查：桌面宽窗口下读回 iframe 内390×844（或明确尺寸）、外框未放大且留白；小窗口整体缩放不溢出；确认真实游戏首页与 PLAY/开始可用。HTTP200、标题正确或设置手机 UA 单独都不够。
- 本次修复仅测显示容器和一次开始操作，不重跑已通过的全游戏CI。验证完成后关闭自有 Ego 空间；保留用户试玩服务，用户结束或被替代时正常关闭并核实。

```sh
python3 scripts/serve_preview.py --directory <同版Web导出> --snapshot --keep --name "游戏 用户试玩"
# 项目明确机型时：--phone-width 393 --phone-height 852
# 横屏游戏：--orientation landscape
```

`--raw` 仅供必须使用顶层 Canvas 的内部自动化 QA，不能与 `--keep` 合用，打印的内部 URL 不得作为用户试玩链接。旧项目复制的脚本可能没有手机外壳，优先使用当前共享脚本；不能靠旧记录里写过“手机预览”就认定已落实。

已有广告入口的重塑/英化可玩候选，默认按[用户可操作广告模拟](manual-ad-simulation.md)启用 `--ad-simulator`，交接前核真实按钮→模拟结果→原奖励业务。仅交试玩不因此扩大为全量验收。

## 电脑试玩输入与原生触屏

电脑鼠标与手机触摸分别验证；预览宿主需要指针桥接时，执行[输入桥接去重](google-touch-runtime.md#输入桥接去重)。桥接只属于预览宿主，不混入平台 Native 包；手机框可见或 HTTP 成功不代表可操作。

适用范围与修复闭环见[通用问题规范](feedback-regressions.md#通用化判据)。


用户试玩窗口自动打开已获持续授权。内部准备可用 `--no-browser`，内部 QA 不自动弹窗；不把此参数用于默认用户交接。用户玩完或被新版替代后，Agent 用受支持接口只关闭自有准确 URL 对应页面，再关闭服务并核实；保留其他 Chrome 页面、登录与存档。


## 用户试玩必须真实启用触摸模拟（用户2026-10-27）

固定手机 iframe 只证明显示比例。默认用户试玩必须由 `serve_preview.py --snapshot --keep` 调用 `preview_touch_window.py`，在首次导航前设置移动 UA、is_mobile、has_touch、viewport/DPR、CDP TouchEmulation 与 `setEmitTouchEventsForMouse(configuration=mobile)`。普通鼠标按下/拖动/松开须产生可信 touchstart/move/end；读回游戏所在 frame 的 maxTouchPoints、Cocos touches 能力和一次实际操作结果后交接。禁止普通 Chrome new-window 代替触控试玩；失败不可静默回退。每个URL使用独立持久目录保留该试玩存档，不接管用户Chrome配置。服务退出后关闭它自己持有的窗口；用户关闭窗口同样结束对应上下文。
