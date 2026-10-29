# 手机按钮与平台触控：交付前必检

直接拖动物件、邻接误选、透明弹窗挡触摸、"下一局其实不能玩"，按[重开与触摸输入](replay-and-input-checks.md)检查（锁定后由测试执行完成，画面结论由 GPT 看总览图下）。

在开始盘点、修复任何 UI/输入反馈后、最终包独立解压后读取本页。适用于实际存在的开始、重试、返回、广告、关闭、奖励、设置等永久和条件按钮；不为补表添加游戏功能。每个按钮必须能证明“原始触点 → 引擎坐标 → 命中 → 按下反馈 → 同一指松手 → 一次回调 → 实际状态变化”。电脑鼠标可用、窄屏截图、SDK 标记和几何模拟都不能替代这条链路。

## 已知失败及检查边界

- **TikTok 与 Cocos 的触摸差别（用户 2026-10-28，最严重的一类“点不动”）**：Cocos Creator 2.4 的触摸转换（`getTouchesByEvent`）读触点的 `clientX/clientY`，TikTok 运行环境给的触点只有 `screenX/screenY`，算出的坐标是无效值，扫码后按钮点不动、常卡在首页。浏览器手机模拟会给 `clientX`，**测不出这个问题**。所以每个 Cocos 2.x 的 TikTok 包都必须：用平台包 `build-templates/bytedance/` 原样的 `main.js` 与 `touch-coordinates.js`（不要自写 patch_build 替代），并通过 `remake-core/scripts/audit_upload_startup.py` 里的触摸坐标探针（`probe_cocos2_touch_coordinates.cjs`，对打包产物真实执行，只给 screenX/screenY 也要得到有效坐标）。探针不过不出包。

手机失败排查中确认过两类代码风险，但补齐后真机仍可能失败，不能将其认作已证实的唯一根因：手写 `getUILocation + Canvas.worldPosition - getVisibleSize/2` 忽略相机投影，长屏上按钮画面与矩形错位；改用引擎命中后，仍未覆盖平台原始字段。TikTok [触控字段说明](https://developers.tiktok.com/docs/en/mini-games-sdk-device-and-network) 给出 `identifier / screenX / screenY`，某版 Cocos ByteDance PAL 直接读 `clientX / clientY`。缺字段会算出 NaN，Vec2 的默认行为还可能将其变成 `(0,0)`，因此只检查“坐标有限”仍会漏检。未检查位置的拍翅能响应，不能证明按钮输入正常。

核对**本次**官方 SDK、实际原始事件和导出的引擎输入代码；不把这个特定字段修复无条件复制到所有引擎。若需适配，明确坐标单位、屏幕/画布原点、DPR 和 Y 轴，只转换一次；不使用 `x || fallback`，0 是合法值；不靠扩大按钮或尝试多种偏移命中任意一项掩盖错误。未知/缺失字段不得伪造“有效触点”。保留原始/映射值、触点 ID、阶段、相机/窗口与实际行为证据。

Cocos 3.x 优先内置 Button 或当前引擎公开的屏幕命中方法，核对实际 render camera、viewport、windowId、mask 和节点变换。2.x 使用该版本的 Button/节点事件分发或经验证的相机换算，不照搬 3.x 的 UITransform API，不将私有内部方法当成跨版本契约。

## 手机再次失败时

用户反馈新版仍失败，原先的合成通过结论必须保留其限定范围，不把它延伸为实际问题已解决。截图只有拍翅/死亡日志时，不能推断按钮收到或未收到触点，也不能归为旧包/缓存。缩小或放大外观只是用户要求的布局变化，显示范围与命中范围要一起核对，不能替代事件定位。

保留本版包哈希与可见版本标记，在实际失败界面记录平台原始阶段/changedTouches、引擎坐标、路由是否仍被上一手势占有、按下/松手ID、命中目标、实际相机投影中心/窗口/DPR，以及回调后状态。日志要能在死亡后捕获；只输出开局前几个触点会漏掉真正失败阶段。需要用户协助时，用短的只读状态行或有界日志减少转录负担；明确这是排查候选，不能冒称手机已修好。确认后移除临时诊断显示。

复现必须经过真实编译的原始回调、Touch/TouchManager/EventTouch及Input分发，再进真实按钮处理。直接拼一个getLocation/getID对象只能验证后半条链。模拟仍须标为模拟；不存在设备证据时严格门禁继续阻断。

若死亡/弹窗使用整体director暂停，检查本平台输入、UI生命周期和渲染是否还运行。需要拆分时，只冻结该游戏的物理和运动组件，界面仍更新；记录此前enabled状态，重试/广告复活/返回只恢复本次冻结对象。死亡状态转换清理旧手势；核查不会多跑计分/金币、让鸟坠落或恢复原本禁用的对象。不要仅因为代码有pause就把它认定为手机失效根因。

## 重做按钮输入时

常规开始/重试/关闭/返回优先用当前引擎Button及节点事件，由引擎负责命中、同一触点的后续分发、拖出取消和点击回调；背景玩法仅处理未被UI接管的全局触摸。不要一边让节点吞事件，一边又期待全局监听器收到同一次松手来执行按钮。

弹窗使用该版本的完整遮罩节点和BlockInputEvents，按钮为遮罩内的子节点；核对真实渲染次序和遮罩尺寸。保留单指/重复保护、按下可见反馈、关闭防穿透和旧异步回调失效，但不要重建另一套相机偏移去替代引擎按钮。若用Button子类增补单指或像素绘制，保留引擎注册与标准touch生命周期，检查销毁/禁用解除手势占用。

回归必须含实际PointerEventDispatcher、NodeEventProcessor、Button触摸方法及最终编入游戏UI；连同原始PAL/Touch/EventTouch走一次完整链。节点树排序、事件容器、渲染若是测试替身，要明说；这些检查仍不能代替真实全屏和两类手机。重做完成不自动等于已证明旧版唯一根因。

## 六项检查

| 检查 | 必须保留的证据 |
| --- | --- |
| 源码几何 | 执行本游戏实际命中处理和真实引擎方法；从渲染相机 worldToScreen 独立获得可见按钮中心，测中心命中/外侧拒绝 |
| 包内 Native 几何 | 从最终 ZIP 独立解压，执行实际编入的处理，核对入口、处理模块及引擎字节；不能只跑源码替身 |
| 平台原始输入 | 原始 onTouchStart/Move/End/Cancel 对象，经过最终 Native 输入转换再到真实按钮处理；覆盖官方字段、旧字段、零值、松手 touches 空而 changedTouches 非空、多指及取消 |
| 实际全屏 Web | 真正填满长屏视口的 Cocos 导出，触控输入、按下反馈和状态读回；固定 2:3 试玩 iframe 只可用于体验，不能作这项证据 |
| TikTok iPhone | 实际客户端、实际上传版本，按下/松手、状态读回及录像/日志；模拟设备和 Mock 不作此项证据 |
| TikTok Android | 同上；不能把一种手机结果延伸到另一种手机 |

源码/Native 几何至少覆盖 375×812、390×844、393×852、412×915，DPR 1/2/3，并加入真实设计比例及非零 Canvas/相机 viewport 偏移、缩放、旋转、无效/隐藏节点、正确与错误窗口。这些是合成参数边界，**不是这几台手机已测试**。实际 Web 至少检查两种长屏尺寸，记录真正 Canvas/frame 尺寸；手机按实际机型记录，不要求手机像素恰好等于上述合成样本。

每个可见/条件按钮逐项测试：

- 中心按下有可辨反馈，同一指松手回调恰好一次；读回预先确定的状态，比如免费 RETRY 真正开新局、HOME 真正返回、CLOSE 移除遮罩、广告入口实际进入说明/请求状态。
- 拖出、取消、第二根手指不能误执行；重复松手/连点不能重复回调；按下到松手不得被另一个面板接管。
- 失败/暂停之后仍能点按钮。核对 director/game pause、帧循环和输入分发的实际关系，不凭某一桌面平台的行为推断手机。
- 弹窗遮罩不穿透到拍翅/射击；关闭后可重开、不被同次松手重新打开；关闭、离开、新局后旧广告/回访回调不能发奖或改新界面。
- 无广告、取消、加载失败、超时都能退出；普通 Web 不发假奖。按钮验证不等于真实广告验收。

## 可运行门禁

从技能根目录运行，或用脚本绝对路径。首次为当前**干净源码和最终 Native ZIP**建立待验记录：

```sh
python3 scripts/audit_mobile_input.py /path/to/current-project \
  --native-zip /path/to/final-native.zip --build-tag Game-vN \
  --stage code --init-review /path/to/evidence/mobile-review.json \
  --report /path/to/evidence/mobile-code-audit.json
```

脚本检测已知 Canvas 偏移模式和 Native 中仅接受 client 字段的小游戏 PAL 转换，去掉注释/字符串后检查。未知别名、其他版本、动态代码和死代码仍需实际执行；扫描无风险只能得到 `static_checks_clear_mobile_pending`。它不会自动生成成功的测试记录。

初始化记录含源码指纹、Native SHA 和 build_tag。指纹覆盖 assets、settings、.creator、platform、build-templates、packages/extensions/plugins、src/scripts、LICENSES 及根文件，排除缓存/依赖；外部构建依赖和实际引擎另记。修改源码、平台补丁或 ZIP 后重新建记录，旧测试不能用来放行。录像/JSON/清单放同一核验目录，引用 `{ "path": "relative-file", "sha256": "actual hash" }`；路径、字节、版本不符直接阻断。

`controls` 按 `context/button` 列完整清单，含 `source_file`、最终 ZIP 的 `native_file`、`runtimes: ["web", "tiktok"]`、`modal` 和 `expected_after` 状态字段。条件入口分别列明，不把主页功能当作失败页已检查。`inventory_complete` 须由审查者对照实际节点/运行界面确认；`inventory_evidence` 保留清单来源。不能为绕过检查把真实 TikTok 按钮删出清单。

各 `gates` 引用 JSON 证据，每份含同一 `binding` 和自己的 `gate`：

- 几何记录：`provenance: "actual_engine_methods"`、`oracle: "render_camera_world_to_screen"`、`handler_origin` 为 `source` 或 `extracted_native_zip`。`cases` 含 control、viewport、dpr、layout=fullscreen、screen_point、独立 projected_center、inside_hit=true/outside_hit=false；记录 `offset_scale_rotation_checked`。保留实际引擎/运行器的哈希与输出，不能写另一个简化公式充当游戏处理。
- 原始输入：`handler_origin: "extracted_native_zip"`，保留 `cases` 中的 raw_event。case 名为 documented_screen_fields、client_only_legacy、zero_coordinates、touch_end_empty_current、multi_touch、cancel；映射样例保存 mapped_point/expected_point、pressed_feedback、callback_count 和 passed。预期位置来自相机/可见位置，不能照抄待测函数结果。零坐标若当前 UI 无按钮，用独立明确的测试目标核验，不移动产品按钮。
- 全屏/手机记录：provenance 为 actual_cocos_web_input 或 actual_tiktok_device，保留 reviewer、reviewed_recording 与 recording 引用。environment 包含 layout、viewport、canvas_css_size、dpr；手机还需 physical_device=true、platform=ios/android、tiktok_version、platform_code_version、runtime_build_tag，确认确实加载本次上传版本。
- `cases` 按 control/scenario 记录 tap、drag_out、cancel、second_finger、duplicate_end；含 callback_count、gameplay_callback_count，tap 另有 down_hit、pressed_feedback、before/after 字段；modal 另测 backdrop、close_reopen、late_callback 并记录 passed、unexpected_reward_delta。预先根据本游戏定义 expected_after，再读回实际结果，不用一个 passed 标志代替状态。两个 Web 长屏的真实记录均保留；脚本核验所引用的一份，审查者核对第二份。

最终调用默认严格模式：

```sh
python3 scripts/audit_mobile_input.py /path/to/current-project \
  --native-zip /path/to/final-native.zip \
  --review /path/to/evidence/mobile-review.json \
  --report /path/to/evidence/mobile-final-gate.json
```

已知风险、旧指纹、缺按钮覆盖、失败/缺失证据均返回 2；不允许标为“手机输入验收通过”。脚本核对记录的一致性、覆盖及数值，不能独自证明录像真实性或清单完整，审查者必须实际操作/读回。真实手机仍失败时，以手机证据为准，撤回“修复通过”，回到原始输入定位，不能只加几何用例。

**本 Skill 不做真机测试，所以始终用 code 模式出包**，不问用户有没有手机；浏览器触屏检查照常做完。用户明确只要源码/扫码前候选或跳过手机时同样用 code 模式交付并标注 pending。保留严格模式的缺项记录，不把 code 模式或“用户跳过”转成完整通过。没有真机/工具受限也不得阻碍已授权的候选工作。这个门禁拦截已知回归并要求证据，不承诺所有未来游戏永远无 bug；IAA、后台接受和发布仍按各自证据判断。

## 真实相机配置回归（Jumping Bird v25）

必须从实际场景读取 Canvas 绑定的相机，而不是在测试里自建理想相机。Cocos 3.x 的 ORTHO=0、PERSPECTIVE=1，不能手抄反值。透视相机 near=0 时，当前 UITransform.hitTest 以屏幕 z=0 反投影，点击可能全部落在相机位置：渲染和全局拍翅正常并不代表按钮能命中。默认门禁阻断 Canvas 绑定透视相机；若项目确需透视 UI，应单独实现并验证射线与 UI 平面求交，不直接放行。

实际运行旧版复现失败，再用新构建验证：从渲染相机 worldToScreen 得到按钮中心，UITransform.hitTest 必须为真；浏览器真实指针按下/松开必须产生事件及页面变化。只调用业务回调、模型节点或自设投影矩阵不能代替。独立 QA 的 DOM 标记只可定位鼠标，须 pointer-events:none，无点击处理器，不得调游戏函数。最终普通包不含 QA 标记。保留旧版失败记录、修复后真实点击和两台真机验收边界。

## Ego Lite实际触屏模拟的提前检查

执行顺序和给用户的逐项任务按 [打包前 Agent 检查与手机验收](prepackage-mobile-review.md)，优先调用已安装的 `mobile-touch-computer-use` Skill。Agent 自主完成美术、完整本地功能与浏览器触屏检查后，直接推进已授权测试候选 ZIP，不等待用户操作 Ego、审 UI 或回复；当前实际检查及原自动失败门禁仍须通过。真实手机清单及验收另记，待验不伪填通过，测试候选也不等于最终手机验收。

浏览器里的按钮全测（INPUT-05）由 `ui_dump.js` 用渲染相机的 worldToScreen 给出每个按钮的实际显示位置，`audit_button_coverage.py` 照这个位置点，并报相机/视口偏移（见[每个按钮都点一遍](replay-and-input-checks.md#七每个按钮都点一遍iphone-模拟input-05用户-2026-10-22)）。普通鼠标和只缩窗口不能代替触屏。Ego Lite 通过官方 Page API/page.cdp 设置手机视口与触摸类型，读取实际innerWidth/innerHeight、DPR、maxTouchPoints和浏览器真实生成的touchstart/move/end，再核对isTrusted与按钮前后状态。iPhone规格名称不证明物理iOS或TikTok Native运行。

在至少两个长屏规格的真正全屏游戏页实际检查开局、自然死亡后RETRY/HOME、广告入口/不可用反馈/关闭、按住滑出取消与遮罩防穿透。真实设备/平台原始输入、多指/cancel、IAA与性能仍需各自门禁。QA只被动观察，不调用游戏方法；记录源与包指纹，提示不入普通包。

同时看完整渲染的HUD、说明与按钮边界。命中中心为真不证明完整按钮在屏幕内；固定比例外框不能覆盖所有长屏裁切。Ego Lite被其他页面切换时核对确切URL，不沿用旧AX索引或截图，也不把其他输入归为Agent病例。
