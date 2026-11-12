# 平台宏跳过普通按钮绑定

适用于 Cocos 2.x 源码或实际 Native JS 中，旧平台宏影响 `cc.Class` 的 `onLoad/start/onEnable` 输入接线。通用 PLAY、Retry、返回等节点的输入应在所有支持的宿主上建立；平台能力差异放到回调内部处理。只在某个平台出现的控件应同时明确其可见性和替代路径，不机械删除一切平台判断。

## 已有要求与新增拦截

原启动合同、逐按钮覆盖已要求“首页可见 → 实际触摸 → 玩法变化”。本条补的是默认浏览器宿主未走到的分支：`CC_WECHATGAME` 等宏为另一取值时，按钮仍可见，但 `node.on('click', ...)` 根本没有执行。文件、体积、TikTok CLI 及默认宿主点通都不能证明这个分支有监听。

`remake-core/scripts/scan_platform_input_bindings.cjs` 复用现有 Acorn AST，按相关宏的布尔取值分析 Cocos 生命周期和可解析的本地辅助方法。已覆盖 `if`、早退、三元、短路/逗号压缩写法、布尔别名及 `this.node/getComponent(cc.Button).node` 别名。

- **制作期**：`audit_startup_contract.py --source-only`，已有 `preflight.py` 自动调用。确定缺失绑定产生 `platform_input_binding` 阻断，不能用旧的文字说明或“浏览器点通过”豁免。
- **Native 出包期**：`audit_upload_startup.audit_files()` 扫实际依赖闭包中的业务脚本，返回具体文件、行/列、事件、绑定/缺失条件。正式 writer、轻量 writer 和最终包检查原本已调用它，复用同一判定，不再启动一套全游戏回归。
- **本次实际使用过的专项 ZIP 路径**：每次交付必跑的 `upload_size_gate.py` 也接入同一分析。复用 `scan_tiktok_host_refs.cjs` 已解析的 AST；旧宏可跳过普通输入时，最终 ZIP 检查直接拒绝。缺少该扫描结果也拒绝，不能只凭体积和 CLI 通过交包。这仍是轻量文件检查，不替代 Native 实际游玩。
- 正常对照：两分支各有输入绑定、平台差异只影响可选 SDK/音频、不可用分支明确隐藏该节点、注释/字符串和局部同名变量，不按这个已知缺陷拒绝。

支持的旧宏当前为 `CC_WECHATGAME`、`CC_WECHATGAMESUB`、`CC_BYTEDANCEGAME`、`CC_QQPLAY`。这是局部静态证明，不是任意 JS 的全程序分析。异步动态接线、未知控制流或继承/平台专属替代路径需实际审查；`unresolved` 表示本项未覆盖，不能据此宣称跨平台输入已通过。TypeScript 不以正则猜执行结果，最终仍检查实际编译 JS。

## 这些宏的值从哪来：电脑上为什么测不出（2026-11-12 补）

在 Cocos 2.4.15 的引擎文件 `cocos/cocos2d-js-min.js` 里（一款实际出过这个故障的包里查到的原文），`CC_WECHATGAME`、`CC_WECHATGAMESUB`、`CC_QQPLAY` 不是构建时写死的常量，而是引擎加载时按运行环境算一次、挂在全局上的只读属性（全局上已经有同名值时不覆盖）：

| 宏 | 引擎加载时怎么算 |
| --- | --- |
| `CC_WECHATGAME` | 全局有 `wx` 对象，并且它有 `getSystemInfoSync` 或 `getSharedCanvas` |
| `CC_WECHATGAMESUB` | 全局有 `wx` 对象，并且它有 `getSharedCanvas` |
| `CC_QQPLAY` | 全局有 `bk` 对象 |

所以这些宏的值取决于**宿主有没有暴露全局 `wx`**，和这个包是不是给微信构建的无关：

- 浏览器和本机测试宿主没有 `wx`，值是 `false`。像 `CC_WECHATGAME || 绑定点击` 这样的写法会照常绑定，按钮点得动，怎么测都是通过。
- 宿主如果暴露了带 `getSystemInfoSync` 的全局 `wx`，值就是 `true`，同一行代码跳过绑定：按钮看得见、点不动。
- TikTok 真机上有没有全局 `wx`，本 Skill 没有实测记录。出过这个故障的那款游戏在手机上 PLAY 没反应，和“手机上这个宏是 true”对得上，但当时的录像没有拍到宏的值，所以只能算线索。要判断某台手机是不是这个原因，在手机调试面板里看 `typeof wx` 和 `CC_WECHATGAME` 的实际值，记进项目记录；读这几个宏时引擎会在控制台打一条 1400 号弃用警告（提示改用 `cc.sys.platform === ...`），手机日志里有这条警告说明代码确实读了宏。
- 做受控对照时，在引擎加载前给宿主加一个带 `getSystemInfoSync` 的全局 `wx` 对象，就能走到另一条分支；这只是对照，不等于手机上就是这样。

其他引擎版本和构建方式可能不同（有的构建会把宏替换成常量），以实际包里的引擎文件为准。修法不受这个影响：普通按钮的绑定不放在任何平台宏后面。

## 命中后怎么补验

只对受影响入口补验，不为每个游戏无条件增加所有平台组合。先保留实际旧故障包和原症状；用同一入口、adapter、引擎和真实触摸，对照缺失条件与正常条件，记录宏/SDK能力的**实际或受控取值**、节点可见/可交互状态、监听接线、触摸和业务结果。修复优先消除普通输入对旧宏的依赖，不能靠让测试宿主强制把宏设成 false 绕过。

原生设备宏值未采集时，只能说“受控条件复现了会造成相同现象的代码缺陷”，不能说已确认手机唯一根因。修复版局部通过与手机故障结案分别记录；原视频、包身份及真机待验项保留在项目记录。

用户授权“局部修改”“不要求原回执”只改变已授权制作/记录范围，不自动把包体、CLI 或默认浏览器预览升级为完整平台启动验收。报告区分字节核对、静态绑定检查、浏览器实际输入、真实设备结果。

## 回归

`python3 -B -m unittest test_platform_input_bindings test_startup_parse_reuse test_upload_size_gate`（在 `remake-core/scripts`）。包括真实缺陷形状的源码和压缩形式、早退/别名/辅助方法，以及正确分支、隐藏控件、无关 SDK、局部同名变量和未走正式 writer 的直接 ZIP 路径。实际故障/修复游戏及其 SHA、审计输出保留项目，不写进共享 Skill。
