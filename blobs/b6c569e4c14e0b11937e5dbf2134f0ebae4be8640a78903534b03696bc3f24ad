# 局部 UI 运行契约

仅在本次改动涉及按钮组合、动态已领/失败重试文案、工具图标时，声明受影响页面/状态并运行；不自动扩大到全游戏、不重跑完整 CI，也不替代最终人工实景判断。

- 从真实引擎渲染后读取每个 Sprite、Label 的世界框及有效可见性，统一转为屏幕 CSS top-down 坐标。按钮 root 缩小而子图未缩小必须失败。实际图框、字框分别检查 viewport、父框、声明槽位及跨槽重叠；默认容差1 CSS px，契约最多允许2 px，不能用百分比放宽。
- 用稳定语义 `slot` 收集正常、已领、写失败 Retry 等受影响状态。按钮换成独立 Label 后仍属于原槽位。缺状态、空采集、隐藏/透明内容或缺真实图框不能通过。`kind:status`可无按钮Sprite，仍必须采集并检查真实字框。
- 对本次受影响的语义工具声明允许的实际SpriteFrame；真实Sprite、texture均须加载且可见，并实际点击验证返回页面。默认 Graphics 方块、只剩Label或空资源不能代替图标。
- `audit_ui_contract.py`自行调用已审阅并锁定SHA的固定Python runner，不能接受外部JSON的`passed`或执行`report.command`。按[项目QA注册](../../remake-core/references/project-qa-registration.md)登记工程内相对runner/dependencies及contract精确SHA、非空依赖清单与允许变体，超时1..120秒。新runner先审阅实际代码再登记；登记不等于证据通过，不执行报告command。
- 同一checker实际运行故障旧UI、修复、单缺陷回注。原故障的启动错误已修复时只保留旧UI，以免启动失败冒充UI缺陷被识别；回注只改独立副本，不改交付候选或ZIP。反例必须命中声明UI错误，缺截图/启动失败/空采集不能当校准成功。

局部入口（只执行此契约，不进入完整美术脚本或CI）：

```sh
python3 <skills>/remake-core/scripts/art_check.py --project PROJECT --ui-contract CONTRACT.json \
  --ui-native EXACT_NATIVE --ui-runner REVIEWED_KEY --ui-calibrate --out FRESH_OUT
```

输出`ui-contract-check.json`含每变体真实运行文件及SHA、逐状态错误、预期故障是否被识别。普通`--variant`发现缺陷即exit1，不能因成功识别缺陷而exit0；仅显式`--ui-calibrate`/`--calibrate`以`calibration_passed`表示正反例校准套件成功并exit0，负例execution的`passed`始终false，报告整体`passed`仍表示所有execution无错误。仅复查已批准且未再改动的状态时可省略`--ui-calibrate`，仍会真实执行final runner。

契约`ui_contract.v1`使用非空`states`映射，每状态指定`modal`与非空`slots`。每槽指定`kind:button|status`、`rect:{x,y,width,height,anchor_x:left|center,anchor_y:top|bottom}`、`require_sprite`、`require_caption`、可选`frames/min_font_px`；bottom表示距viewport底边的距离，center的x为相对中线偏移。可选`tools`映射声明`frames`与`click_return_page`。`calibration`映射变体到必须实际命中的错误code列表，游戏名、节点名和变体实现留项目collector/contract。

运行报告`ui_contract_runtime.v1`顶层固定`producer:real_browser_ui_contract`及`execution`。execution含variant、base/实际native_tree_sha256、renderer_identity五项原始身份、viewport、非空events、errors、states；每状态有同次截图路径/SHA和buttons数组。每entity含稳定slot、id、kind、visible、effective_opacity、parent.world_rect、sprites及captions；子项也记录真实world_rect与有效可见性。Sprite另有frame、loaded、texture_loaded；caption另有text、font_size。tools同样记录真实frame/texture状态及实际click_return_page。有效opacity使用0..255范围，至少1才算可见；所有rect必须有限且宽高正。collector不填pass，由checker判定。

拒绝逻辑自测：`python3 <skills>/remake-core/scripts/test_ui_contract_refusal.py`。这些合成几何单测不能替代真实runner的正反例运行。

## 开始接图时先预防

按[统一坐标与绘制职责](production-prevention.md#接入前统一坐标与绘制职责2026-11-03)先明确锚点、父变换、布局控制者、裁切及实际渲染路径。当前几何契约本身不能证明像素没被覆盖；配合同版本截图直接查看与真实点击，不能把 node active / world_rect 通过写成可见按钮通过。自定义批量绘制的覆盖要在真实引擎里回归，简单 DOM 或节点桩不算该项证据。

**静态按钮遮挡或错图复发时**，给受影响的单 Sprite 槽在已审核契约中声明 `pixel_reference`，例如 `{"frame":"upgrade","path":"assets/ui/upgrade.png","sha256":"<参考原图实际 SHA256>","max_mae":35}`。收集整张 viewport 截图。检查器解码 PNG，按当前截图与 CSS 视口换算像素坐标，在目标位置对照参考图不透明部分。资源节点正常但像素偏差超过该槽上限时报告 `sprite_pixel_mismatch`。阈值用本项目同状态正常和遮挡截图校准，35 只是示例。只用于完整、无旋转、无染色、无额外覆盖的固定画面。多层按钮、动画、九宫格或局部文字遮挡要选稳定独立子槽或直接看图，整块平均值不能证明每个字正确。更新契约按原流程重新登记，原有 runner 的几何检查继续适用。

采集配对时等待布局与入场动画稳定，在同一稳定渲染状态保存 screenshot 与节点框。若肉眼可见的对照按钮也超过误差限，先查同帧坐标、缩放和资源状态，结果记为“参考图与截图不匹配，原因待查”。禁止直接归因为遮挡或调高阈值。离屏和只露半个的控件保留越界失败，不能裁到可见部分再算通过。

### 已知风险槽的小区域检查

在已审核的状态槽上可声明非空 `pixel_regions` 数组。例：`{"id":"badge-visible-height","region":[0,0,1,1],"rgb_min":[150,0,0],"rgb_max":[255,95,120],"metric":"height","range":[0.45,1]}`。region 为相对已声明槽的左、上、右、下，截图换算遵循 viewport；颜色、范围和通过区间由本游戏的正常资产和问题样本校准，只对声明状态生效。metric 选 fill（像素面积占比）、width 或 height（匹配像素包围范围）；invert=true 可反选稳定背景色。检查图标占用不足、保留空隙被文字侵入、活动角标只露细边。背景变化、相同颜色来自多层或粒子混入时改用静态参考图/分层采集。不能凭区域报警指定是哪一层，不能把没有声明的状态当成已检查。每个已知故障至少跑一次原问题图和一个正常对照，缺少同状态采集不得作为交付通过依据。
