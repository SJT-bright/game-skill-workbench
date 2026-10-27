# Google Chrome 移动触摸运行模式

适用范围：所有本地游戏预览、试玩代测、玩法设计后的首个可玩确认、按钮/拖动/弹窗回归，以及美术或逻辑修改后的受影响输入验证。用户明确指定其他执行器时再切换；普通鼠标点击只作辅助排错。

## 运行合同

Chrome DevTools 的 Device Mode 只负责显示尺寸和设备参数；真正的输入必须通过 Playwright/CDP 触摸通道发送。现有 `chrome-mobile-testing/scripts/chrome_touch.py` 已支持这一通道：

- 移动视口：默认 `iphone_15`，393×852、DPR 3；按项目需要补跑 `iphone_se` 375×667。
- `is_mobile=true`、`has_touch=true`、移动 UA、`maxTouchPoints`。
- `Emulation.setTouchEmulationEnabled` 与 `Emulation.setEmitTouchEventsForMouse`。
- 点击使用 `page.touchscreen.tap` 或 CDP `Input.dispatchTouchEvent` 的 `touchStart → touchEnd`。
- 拖动使用 `touchStart → touchMove* → touchEnd`；取消使用 `touchCancel`。
- 记录 `touchstart/touchmove/touchend/touchcancel`、`pointerdown/up`、`pointerType`、`isTrusted`、坐标、Canvas CSS 范围和最终业务结果。

默认启动命令（当前用户已授权本机 Chrome 模式）：

```sh
python3 <skills>/chrome-mobile-testing/scripts/chrome_touch.py \
  --url http://127.0.0.1:<PORT>/ \
  --plan <project>/docs/qa/touch-plan.json \
  --out <project>/docs/qa/touch-run-<version> \
  --user-approved-chrome \
  --channel chrome \
  --name "<game> Chrome touch"
```

`--cdp-url` 只用于用户明确要求连接已有 Chromium/Ego 实例的情况；当前统一测试默认启动独立 Google Chrome 隔离上下文。脚本的 `input_transport` 必须是 `playwright_cdp_touch`，不能用 `page.mouse` 结果替代。

## 通过条件

一次手机触摸通过必须同时满足：

1. 运行记录的 `device`、viewport、DPR 和 UA 与本次计划一致。
2. 事件证据包含可信的触摸输入；至少有 `touchstart/touchend` 或由 Cocos 接收的 `TOUCH_START/TOUCH_END`。只有 `mousedown/mouseup/click` 不能通过。
3. 触摸坐标在当前 Canvas CSS 坐标和按钮命中区域内，没有依赖旧视口坐标。
4. 业务结果真实发生，例如页面打开、设置值变化、签到状态改变、关卡进入、汉堡移动或弹窗关闭；`clicked` 回执、颜色变化、SDK 被调用或无异常都不能单独通过。
5. 触摸取消、滑出按钮、重复触摸、弹窗关闭后重新点击等适用状态也能收口。

页面中的 `pointerType="mouse"` 记录只能标记为鼠标辅助结果。电脑物理触摸屏可作为额外人工对照，但必须读取实际 `pointerType`；若驱动把它转换成 mouse，不计作手机触摸。

## 与用户预览的关系

用户预览链接仍可使用 `serve_preview.py --keep` 提供固定手机尺寸外壳，方便用户在 Codex 中试玩。这个外壳是展示和交接容器，不是输入验收器。Agent 需要测试时打开同一版本的 Chrome touch 原始入口或外壳内部实际游戏页，保留真实 Canvas 和同源存档；不能只点击外壳、iframe 或装饰层后写手机通过。

## 覆盖边界

此模式大幅减少桌面鼠标与手机触摸的差异，能抓住坐标/DPR、Canvas 命中、触摸监听、遮罩、`touchcancel`、拖动结束、异步页面切换和按钮状态问题。它仍不是物理手机或 TikTok Native：真实系统手势、厂商触摸驱动、TikTok 原生 SDK、广告、前后台宿主行为和平台上传接受仍需单独记录。不要把 Chromium 模拟结果写成 `physical_device`、`Native SDK` 或真实 IAA 通过。

## 最小计划示例

```json
{
  "device": "iphone_15",
  "actions": [
    {"type": "dump_ui", "screen": "home", "kind": "home", "purpose": "home"},
    {"type": "tap", "x": 196, "y": 730},
    {"type": "drag", "points": [[196, 520], [220, 520], [250, 520]]},
    {"type": "wait", "ms": 300}
  ]
}
```

计划里的坐标必须按当前截图重新确定；不能复用另一个视口或旧版本的坐标。每次构建版本、Canvas 尺寸或外壳结构变化，都重新读取输入证据。

## 输出和报告固定措辞

每次给用户、项目交接或测试报告输出时，必须明确写出：`已在 Google Chrome 的 iPhone 触摸模式测试`，并列出 device、viewport、DPR、`input_transport=playwright_cdp_touch` 和业务结果。

如果只在 Codex 内置浏览器打开或点击过，输出必须写：`Codex 内置浏览器仅查看，未作为手机触摸测试`；不能写“手机测试通过”“触摸通过”“按钮已验证”，也不能把 Codex 页面截图当作 Chrome 触摸证据。

用户预览链接的说明必须提醒独立 Google Chrome。即使 Codex 自动把本地链接显示在内置页面里，Agent 仍需在独立 Chrome 完成预检后才能交付测试结论。
