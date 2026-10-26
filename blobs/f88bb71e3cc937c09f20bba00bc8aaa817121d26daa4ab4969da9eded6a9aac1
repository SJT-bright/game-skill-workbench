# 上传包禁入窗口

2026-10-26，用户要求自动阻断，不依赖人工提醒。共享实现`cocos-game-to-english/scripts/audit_no_ad_simulator.py`接在完整writer、轻量writer和`verify_native_zip.py`逐项读取最终ZIP的边界。

禁止本地模拟广告面板、点击伪完成即发奖入口，以及玩家Credits/制作人员/鸣谢页面和承载同类制作说明的About入口/路由。真实广告适配器、正常奖励回执、钻石余额/货币credits及项目外许可证文档不能按关键词误删。去掉实际入口、回调及无用显示映射，不能只改名、隐藏或关闭开关。必要素材许可留项目文档并遵守，不把许可证删掉来通过检测。

当前签名覆盖`Local test ad`、`Complete test ad`、已知模拟工具标记/文件名、精确Credits/About UI标签/路由、转义字及序列化UI；不宣称可静态识别任意图片文字、混淆代码或所有未知模拟工具。遇新变种先保存最小旧失败反例，再补精确签名/解析与正常对照，不做宽泛的credits全文拒绝。实际改动的设置页须运行打开→检查入口→Sound/General→关闭，确认入口已消失；广告真实业务与本地模拟保持隔离。

回归`cocos-game-to-english/scripts/test_no_ad_simulator.py`覆盖准确旧v80、模拟窗口改名/关闭、转义标签、序列化与HTML、两个writer拒绝且无输出、最终ZIP拒绝、正常广告/货币/许可证对照。最终以正式writer和prepare_delivery交包。

复盘：上次门禁只识别另一套模拟器标记，漏了本作preview-ads.js；Credits仅有文字规则，未接最终字节拒包。以后以实际窗口反例校准三个出包边界，不能以“文档已有禁止”当作已执行。
