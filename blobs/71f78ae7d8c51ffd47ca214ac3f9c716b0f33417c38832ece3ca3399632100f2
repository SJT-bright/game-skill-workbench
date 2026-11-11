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

按[统一坐标与绘制职责](production-prevention.md#接入前统一坐标与绘制职责2026-11-03)处理本次结构改动及功能组合。需要复验时，将旧容器实际受影响的剩余控件、图文价格组合、邻接区域和相关弹窗合并进已有 cases/states，复用 inside/children、display_budget、跨槽重叠及适用像素判据；不另建同类检查。规则按本游戏设计声明，故意出框的装饰不强制包含，固定坐标和尺寸不推广到其他游戏。当前几何契约本身不能证明像素没被覆盖；配合同版本截图直接查看与真实点击，不能把 node active / world_rect 通过写成可见按钮通过。自定义批量绘制的覆盖要在真实引擎里回归，简单 DOM 或节点桩不算该项证据。适用范围、已有证据沿用及用户免验仍按原增量与授权规则，不因结构改动自动扩成全页面或全游戏复验。

**静态按钮遮挡或错图复发时**，给受影响的单 Sprite 槽在已审核契约中声明 `pixel_reference`，例如 `{"frame":"upgrade","path":"assets/ui/upgrade.png","sha256":"<参考原图实际 SHA256>","max_mae":35}`。收集整张 viewport 截图。检查器解码 PNG，按当前截图与 CSS 视口换算像素坐标，在目标位置对照参考图不透明部分。资源节点正常但像素偏差超过该槽上限时报告 `sprite_pixel_mismatch`。阈值用本项目同状态正常和遮挡截图校准，35 只是示例。只用于完整、无旋转、无染色、无额外覆盖的固定画面。多层按钮、动画、九宫格或局部文字遮挡要选稳定独立子槽或直接看图，整块平均值不能证明每个字正确。更新契约按原流程重新登记，原有 runner 的几何检查继续适用。

采集配对时等待布局与入场动画稳定，在同一稳定渲染状态保存 screenshot 与节点框。若肉眼可见的对照按钮也超过误差限，先查同帧坐标、缩放和资源状态，结果记为“参考图与截图不匹配，原因待查”。禁止直接归因为遮挡或调高阈值。离屏和只露半个的控件保留越界失败，不能裁到可见部分再算通过。

### 已知风险槽的小区域检查

在已审核的状态槽上可声明非空 `pixel_regions` 数组。例：`{"id":"badge-visible-height","region":[0,0,1,1],"rgb_min":[150,0,0],"rgb_max":[255,95,120],"metric":"height","range":[0.45,1]}`。region 为相对已声明槽的左、上、右、下，截图换算遵循 viewport；颜色、范围和通过区间由本游戏的正常资产和问题样本校准，只对声明状态生效。metric 选 fill（像素面积占比）、width 或 height（匹配像素包围范围）；invert=true 可反选稳定背景色。检查图标占用不足、保留空隙被文字侵入、活动角标只露细边。背景变化、相同颜色来自多层或粒子混入时改用静态参考图/分层采集。不能凭区域报警指定是哪一层，不能把没有声明的状态当成已检查。每个已知故障至少跑一次原问题图和一个正常对照，缺少同状态采集不得作为交付通过依据。

### 普通 art_check 也读取项目声明的高风险控件

在 `docs/art/visual-slots.json` 定义非空 cases。每项用 id、screen（采集状态）、viewport_width（CSS 宽）、expected_width/expected_height（实际截图像素）、owner（实际完整节点路径）绑定同次截图与节点。用 inside:[left,top,right,bottom] 定义 owner 内的相对安全区，children 列出应完整容纳的文字或图标节点路径；也可用上文 pixel_regions 查禁入区域。相同页面要用不同视口分别登记。检查会拒绝缺状态、缺图、同名歧义、截断的 dump、错误像素尺寸及空规则。稳定无字背景的装饰、已认可的故意出框角标要在定义内区时区分。普通截图看不到的状态不能写通过。项目未声明时不会自动推断所有控件的设计意图；制作方须依受影响页面和历史缺陷补齐声明。

## 按钮内框验收

分层按钮在同一 case 声明 inside、children，以及可选的 horizontal_gap，例如 `{"left":"panel/btn/video","right":"panel/btn/title","min_css_px":3}`。左右路径按实际顺序填写，值是项目设计要求的 CSS 像素。检查读取未裁切的两个节点框，负值表示横向相交。节点框含透明边、字体外伸或按钮整体成图时，还要看最终截图。

同一款固定按钮用同一组相对区域在原问题图和已看过的正常图上回放。分别查图标与首字之间、词尾与斜边之间的空隙，再查图标和整词确实可见，避免空按钮也过。可用 pixel_regions 核稳定字色，对同色边框或背景需换区域或做分层对照。检查结果区分模板、实例、视口及状态。登记缺失、样本不配对、截图无法分辨时记未验证。原图回放单列，最终以本次两种手机尺寸的同帧截图及实际页面裁切为准。

## 高清图标接入时锁定独立显示预算

在第一张图的制作规格中，分别记录**源 PNG 像素尺寸**与**每个页面视口的最终 CSS 显示尺寸**。视频图标、复选标记、关闭符号即使清晰且等比，也可能被按原图尺寸接入而放大数倍；只查清晰度、变形、文字溢出或「子图仍在 owner 里面」不能发现 owner 一起变大的情况。源 PNG 可以高清，但调用接图接口必须给出独立的显示槽位尺寸。不要靠缩小源 PNG 代替该约束。

对于本次新增/替换的高风险 Sprite，在已有 `docs/art/visual-slots.json` case 中添加可选的 `display_budget`，例如：

```json
{
  "id": "checkin-video-small",
  "screen": "checkin",
  "viewport_width": 390,
  "viewport_height": 844,
  "expected_width": 780,
  "expected_height": 1688,
  "owner": "Canvas/CheckinPanel",
  "display_budget": {
    "unit": "css_px",
    "nodes": [{
      "path": "Canvas/CheckinPanel/Claim/Icon",
      "frame": "icon-video",
      "expected_css": [48, 48],
      "tolerance_css_px": 1,
      "tolerance_ratio": 0
    }]
  }
}
```

示例尺寸只是示例，必须从该项目制作规格或已看过的正常样本确定。`expected_css` 两轴均为有限正数，可以有小数；不同视口分别登记 case（包括同宽不同高），不能从本次疑似膨胀节点或同步变化的 owner 框反推期望尺寸。设计稿单位要先按实际页面适配换成 CSS 单位，不能直接抄设计分辨率、纹理尺寸或截图物理像素。

锁定显示尺寸后，再按**实际等比适配后的 Art 宽高**定位图标与文字。触摸 root 为 400×110 而按钮底图实际适配为 308×110 时，不能继续按 400 宽定位图标。对于设计要求完整位于底图内的内容，同时声明既有 `inside/children`，owner 指向实际 Art 底图节点或独立设计槽；不要只指向较大的触摸 root。独立显示预算查大小，inside 查位置，任何一项失败都不能报整个按钮合格。

此扩展使用 `audit_art_slots.py` 的同一个入口，因此首件 preflight 与正式美工检查都读取它；旧 case 未声明时行为不变。检查器要求 dump 的 `viewport`、`page` 宽高与声明一致，有有效 `canvas_css`，节点完整路径唯一，实际 Sprite 的非空 frame 名称精确匹配，frame 尺寸有效且节点有效 opacity 大于零。它优先取 `unclipped_screen`，乘 `canvas_css` 的宽高得到真实 CSS 显示尺寸，不重复乘 DPR，也不把截图像素尺寸或 owner 框当预算。缺节点、身份、两轴预算或坐标信息会拒绝通过。当前通用 dump 只提供 frame 名称，名称匹配不等于资源内容身份；已登记的 production 资产链继续绑定真实源文件和输出文件 SHA。

绝对容差默认 1 CSS px，允许 0..2；可选比例容差默认 0，须有限且小于 1。每轴按 `max(绝对容差, 预期尺寸×比例容差)` 比较，最终容差仍不得超过 2 CSS px，且必须小于该轴本身。比例字段不能绕过绝对上限；由本项目正常样本的测量误差支持，不预填大比例掩盖尺寸错误。这里是 `visual-slots` 的显示预算扩展，不改上文 `ui_contract.v1` 原有的最多 2 CSS px、禁止百分比放宽的规则。

同一个 manifest 中已有 `production_assets` 时，production 审核会验证新预算结构，原有 fingerprint 绑定完整 manifest 字节；修改尺寸、容差、路径或 frame 后旧生产绑定失效，必须重新验证受影响页面。仅有历史截图、没有同帧真实 dump 时，可以做直接看图与明确标注的引擎替身验证，但不能伪造旧 dump，也不能据此声明首件或整页通过。此项验证显示尺寸与声明身份，不替代像素遮挡、位置/裁切、字体风格、资源加载完成或交互检查。
