# 测试包启动故障：完整已知结论与可执行防复发

## 2026-10-24：入口存在，引擎被漏出包

实际扫码视频约49秒停留平台首次加载容器；未展开vConsole，没有登录错误栈。故只能观察到平台容器打开、游戏首屏未出现，不能直接诊断为登录失败。

实际交付ZIP的game.js显式require cocos/cocos2d-js-min.js，中央目录中该文件不存在。旧ZIP结构验证仍返回local_structure_checks_passed，并且expected_tree_exact=false。说明CRC、根文件、App ID、大小都通过仍可能启动必败；之前的“可上传可用”结论超出证据。

同工程先前Native留有匹配Cocos Creator 2.4.15引擎1,914,272字节。修复包原198文件全部原字节保留，只新增此引擎为199文件；主包恢复2,385,286字节，总内容11,092,766字节，ZIP与修复输入一致。本地修复只关闭缺失依赖，不宣称扫码复测成功。未证明文件如何从最初输出丢失，不能凭体积差就归因于压缩器、清理脚本或平台。

**防复发**：共享verifier从game.js构建依赖闭包，根require和其可达子模块都必须存在。旧真实包必须失败、修复包通过；合成夹具分别删engine、transitive module、settings jsList、subpackage/game.js和Cocos import pack，检查器和writer均拒绝，失败不发布ZIP。最终逐文件比较以原Native输入为基准，不以ZIP自己回解目录为基准。

## 同时排查的其他四款

BadHairDay最新v9（另查旧“自制”包）、EmberCircuit DeviceFix、Juniper v12 r7、Double Jump Duo v13r2均带引擎、根入口直接依赖及声明分包入口；没有复现上述同一种漏引擎。它们共用测试应用ID，但共用ID不证明配置错误，也不证明扫码失败原因相同。仍需各自实际上传版本和vConsole首条错误。

校准时发现两类检查器误报并关闭：Browserify工厂内部require('PlatformConfig')属于内部模块ID；额外自定义资源分包不必出现在Cocos settings bundle列表。按词法function作用域跳过局部绑定require；仅要求Cocos引用的bundle已声明，不反向禁止自定义分包。空无代码分包game.js合法，空引擎文件拒绝。

## 已有TikTok检查的融合

原verify_native_zip保留格式/路径/CRC/体积/目标ID/原树字节校验。原audit_packed_assets保留字面资源路径、图集尺寸/边界/哈希。新增audit_upload_startup补入口传递闭包、Cocos2 jsList/scene注册/import packs与分包入口。它们共用最终ZIP输入，报告包含覆盖范围，不能把静态检查记作真实renderer成功。

已有Ember案例还发现：共享Canvas先取2D会阻止WebGL建立；下载器返回Image与Native parser所需路径字符串不符。普通Web、宽松SDK替身和仅方法断言不能覆盖这些问题。沿用已有真实Native renderer/parser正反例执行协议，不能为出包添加永远成功的SDK/资源回调。

## 正式资料与运行证据

官方资料：[Cocos接入](https://developers.tiktok.com/docs/en/build-mini-games-with-cocos)、[Cocos故障排错](https://developers.tiktok.com/docs/en/cocos-development-troubleshooting)、[扫码/权限/地区/网络/vConsole](https://developers.tiktok.com/docs/en/mini-games-development-troubleshooting)。平台规则变化时按需复核。

具体原始视频、实际游戏ZIP、版本指纹、完整运行报告和个人配置留对应项目；Wiki实体/来源导航到它们。通用Skill不分发私有游戏包或账号。test_package_checks.py生成完整可复制的合成缺陷，真实包回归在维护工程记录各输入SHA、检查器SHA和完整输出；不得拿历史通过替代本次候选。
