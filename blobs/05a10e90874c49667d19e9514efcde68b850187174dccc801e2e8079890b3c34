# 局部 UI 运行契约

仅在本次改动涉及按钮组合、动态已领/失败重试文案、工具图标时，声明受影响页面/状态并运行；不自动扩大到全游戏、不重跑完整 CI，也不替代最终人工实景判断。

- 从真实引擎渲染后读取每个 Sprite、Label 的世界框及有效可见性，统一转为屏幕 CSS top-down 坐标。按钮 root 缩小而子图未缩小必须失败。实际图框、字框分别检查 viewport、父框、声明槽位及跨槽重叠；默认容差1 CSS px，契约最多允许2 px，不能用百分比放宽。
- 用稳定语义 `slot` 收集正常、已领、写失败 Retry 等受影响状态。按钮换成独立 Label 后仍属于原槽位。缺状态、空采集、隐藏/透明内容或缺真实图框不能通过。`kind:status`可无按钮Sprite，仍必须采集并检查真实字框。
- 对本次受影响的语义工具声明允许的实际SpriteFrame；真实Sprite、texture均须加载且可见，并实际点击验证返回页面。默认 Graphics 方块、只剩Label或空资源不能代替图标。
- `audit_ui_contract.py`自行调用已审阅并锁定SHA的固定Python runner，不能接受外部JSON的`passed`或执行`report.command`。Skill内`ui_contract_trusted_runners.json`登记project、runner/dependencies及contract精确SHA、非空依赖清单、允许变体、1..600秒超时。新runner需先审阅再登记；不提供命令行自注册绕过。
- 同一checker实际运行故障旧UI、修复、单缺陷回注。原故障的启动错误已修复时只保留旧UI，以免启动失败冒充UI缺陷被识别；回注只改独立副本，不改交付候选或ZIP。反例必须命中声明UI错误，缺截图/启动失败/空采集不能当校准成功。

局部入口（只执行此契约，不进入完整美术脚本或CI）：

```sh
python3 scripts/art_check.py --project PROJECT --ui-contract CONTRACT.json \
  --ui-native EXACT_NATIVE --ui-runner REVIEWED_KEY --ui-calibrate --out FRESH_OUT
```

输出`ui-contract-check.json`含每变体真实运行文件及SHA、逐状态错误、预期故障是否被识别。普通`--variant`发现缺陷即exit1，不能因成功识别缺陷而exit0；仅显式`--ui-calibrate`/`--calibrate`以`calibration_passed`表示正反例校准套件成功并exit0，负例execution的`passed`始终false，报告整体`passed`仍表示所有execution无错误。仅复查已批准且未再改动的状态时可省略`--ui-calibrate`，仍会真实执行final runner。

契约`ui_contract.v1`使用非空`states`映射，每状态指定`modal`与非空`slots`。每槽指定`kind:button|status`、`rect:{x,y,width,height,anchor_x:left|center,anchor_y:top|bottom}`、`require_sprite`、`require_caption`、可选`frames/min_font_px`；bottom表示距viewport底边的距离，center的x为相对中线偏移。可选`tools`映射声明`frames`与`click_return_page`。`calibration`映射变体到必须实际命中的错误code列表，游戏名、节点名和变体实现留项目collector/contract。

运行报告`ui_contract_runtime.v1`顶层固定`producer:real_browser_ui_contract`及`execution`。execution含variant、base/实际native_tree_sha256、renderer_identity五项原始身份、viewport、非空events、errors、states；每状态有同次截图路径/SHA和buttons数组。每entity含稳定slot、id、kind、visible、effective_opacity、parent.world_rect、sprites及captions；子项也记录真实world_rect与有效可见性。Sprite另有frame、loaded、texture_loaded；caption另有text、font_size。tools同样记录真实frame/texture状态及实际click_return_page。有效opacity使用0..255范围，至少1才算可见；所有rect必须有限且宽高正。collector不填pass，由checker判定。

拒绝逻辑自测：`python3 scripts/test_ui_contract_refusal.py`。这些合成几何单测不能替代真实runner的正反例运行。
