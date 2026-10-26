# 竖屏试玩的手机边界复核

适用于竖屏手机游戏的 Web 试玩交付与相关画布/Widget 改动，补充本轮受影响整页检查；不强迫横屏游戏套竖屏框，也不扩大为全游戏 CI。

1. 除两种手机比例外，真实打开**交付URL**的桌面宽窗、窄窗；不要只在测试工具内模拟手机。声明预览手机框尺寸上限，每次浏览器调用都设置并读回实际视口。绑定入口脚本SHA、完整原图、PNG像素尺寸和CSS坐标换算，文件名不能代替实际尺寸。
2. 分别测量外层窗口、iframe、Canvas、相机有效游戏区和主要背景可见框。把当前可见UI贴图的四角投影到同一外层CSS坐标，用完整截图校准。控件位于Canvas之内仍可能落在竖屏背景之外；白边/留白不能承载游戏入口。不要用裁切溢出控件替代修复或把遮罩下的控件算成当前可点击入口。
3. 当前页面须ready，图片/字体无pending或错误，无有效加载遮罩；已有SpriteFrame不代表可交付。布局稳定后采样3次，漂移不超过1 CSS px。真实点边缘入口并关闭，在**首触后、窗口调整后、刷新后**复测；防止引擎自动全屏把iframe撑满浏览器。若测量与实图不符，先修坐标转换，不按错误采样改图。
4. 用同一checker检测未修运行副本和修复版：旧缺陷必须以真实越界fail检出，正常手机对照仍pass，修复版在受影响尺寸与状态均pass。加载中、空目标、缺截图、尺寸/哈希不符一律不可检查，不能充作旧缺陷检出。实际看整页与相关控件组合图，再确认真实点击反馈；只有闭环有效后才将候选流程写入正式技能。

辅助命令：`python3 scripts/check_phone_boundary.py CAPTURE.json [...] --out report.json`。

采集字段：`producer: real_cocos_phone_boundary`、真实`requested_viewport`/`viewport`、`bundle_sha256`、`screenshot`绝对路径及`screenshot_sha256`、`screenshot_pixel_size`和`screenshot_css_scale`（标准PNG/CSS1:1可省这两项）、`canvas_rect`/`content_rect`/可选`phone_rect`、项目声明`preview_max_css_width`、`delivery_preview`、`render_ready`、`loading_guards`、`pending_assets`、非空`targets:[{path,rect,loaded}]`、至少3次`samples`及`maximum_target_drift_css_px`、`calibrated_to_full_screenshot:true`。矩形均为同一外层CSS坐标的`[x,y,width,height]`，容差1px。不能手填几何或就绪标志冒充运行采集；collector和项目原图留项目。

checker只验证已采集边界与证据完整性，不独立证明采集诚实、点击发生、贴图内装饰无遮挡或全美工合格；保留实际整图复核与交互回执。
