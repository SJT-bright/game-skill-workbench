# 最终测试包检查合同

本检测针对会导致上传拒绝或启动不可用的最终文件问题。完整制作沿用原CI；成品局部维护不因此重跑全游戏CI。

| 层 | 必须检查 | 内部保存的完整证据 | 边界 |
|---|---|---|---|
| 身份 | 实际Native、最终ZIP、明确目标App ID、当前修改入包 | 绝对来源、版本、Native逐文件SHA、ZIP SHA、目标配置 | 多款游戏共用App ID不自动判错；须与实际测试应用和版本卡核对 |
| ZIP | 根game.js/game.json/project.config.json、安全路径、重复/大小写冲突、CRC、无套娃/源码/桥接文件 | 每条ZIP路径、大小、SHA、格式错误 | ZIP可读取不代表入口可执行 |
| 体积 | 未压缩主包≤4,000,000、总包≤30,000,000、独立分包≤4,000,000字节 | 主包文件、每个分包分类与字节 | 不用压缩后大小替代；普通分包计总量 |
| 启动闭包 | game.js、adapter、engine、physics、main、settings、ccRequire和可达本地CommonJS依赖 | 每条source→require→resolved边、缺失/空引擎/大小写错误 | 静态字面量解析不覆盖动态路径、ESM/import-map或未知模块系统；列未覆盖项并执行生产加载器 |
| 配置/分包 | 声明root/name唯一、game.js存在；Cocos settings引用的bundle在game.json声明；jsList可加载 | 声明与入口、settings映射 | 自定义非Cocos分包可额外存在；无代码分包的空game.js允许 |
| Cocos场景 | launchScene已注册、config.json可读、配置指向的import pack存在 | 场景注册、pack路径错误 | 注册不等于场景解析成功；纹理UUID等动态路径由实际loader验证 |
| 资源 | 已知literal路径、图集纹理/尺寸/边界/指纹、构建与ZIP全量一致 | audit_packed_assets原始结果、所有字节差异 | 不猜测所有UUID或远程CDN成功；实际renderer/parser/字体音频需运行证据 |
| 原生输入 | 实际SDK触点→adapter回调→引擎坐标转换→业务效果；screen坐标、零坐标、已有client坐标及优先保留client对照 | 原始触点、转换结果、identifier、安装顺序及同版脚本指纹 | Web自带client字段不覆盖原生转换；NaN/Infinity拒绝，未知协议列待验 |
| 实跑 | 每包核最终Native实际入口/adapter/引擎，HOME可操作→真实输入→玩法变化，以及失败→Retry新请求→恢复 | 实际运行器/adapter/engine/ZIP SHA、argv、原始日志、首个异常栈、截图/输入与结果 | 不能仅执行Web版、宽松getContext或只汇总恒定pass的runner；受控SDK不是真平台 |
| 平台 | 如有真实扫码故障，核版本卡、Client Key映射、测试账号、地区、客户端、网络和vConsole首错 | 用户/平台返回的实际证据，账号隐私留项目 | 文件检查无法证明账号权限、平台网络或真实IAA；不臆造共同根因 |

## 失败处理

先留实际故障包/日志与SHA，定位第一处确定失败；按受影响路径修复、重建。用同一检查器跑故障反例、修复版和正常对照；修复后从最终ZIP回解运行，不能拿工作目录的另一个引擎或图片偷补缺失。ZIP与Native不一致拒绝交付，保留旧包，新包新名称。

报告结构保留共享verifier的完整字段，包含file_sha256、startup_dependency_check.require_edges、dynamic_requires、packed_resource_check、runtime_execution。静态脚本的runtime_execution固定为未执行，Agent另留真实运行原始记录，不改此字段冒充运行。缺失或未执行项保留明确状态。

## 安装/集成

- 新Skill依赖同级remake-core/scripts中的audit_upload_startup、verify_native_zip、audit_packed_assets。主Skill导出/安装须包含该依赖集；本机成品Skill仍按其LOCAL_ONLY规则排除于通用导出。
- verify_native_zip.verify直接检查最终ZIP启动闭包，原正式writer在Native预检和ZIP回读均接入；不能只有入口文案。
- 成品维护的build_checked_zip在临时ZIP通过同一verifier及资源检查后才原子发布最终文件，无需全量CI。失败无最终ZIP，旧文件不覆盖。
- 新框架/模块协议只扩展经过真实反例校准的解析/运行器；不能为让当前游戏过关而排除整个启动依赖检查。
- TikTok兼容静态检查在remake-core/scripts/package_gates/tiktok_compat.py（GATE_MODULES末项，writer、build_checked_zip、check_package都经package_gates.run()执行）：分离引擎插件、subPackages大小写新老都拦；ogg、超4096纹理、路径空格/#/?/%新游戏拦老游戏警告；回归test_package_gates_compat.py。

## 解析器与已有检验的结合

JS依赖检查使用随工具固定的Acorn 8.15.0（MIT，scripts/vendor/ACORN-LICENSE），通过Node.js读取AST，只解析不执行游戏。区分注释、正则、模板表达式、IIFE转发与Browserify内部工厂；坏JS/被require的坏JSON会拒绝。Node缺失或解析失败不得静默当通过。检查器输出依赖边和未知动态绑定；动态文件加载仍由实际生产Native加载器验证。

现有upload_preflight.py通过同一native_problems/verify继承此次补丁；audit_packed_assets继续验证已知资源和图集；audit_native_resource_paths、audit_native_startup_renderer及[Native场景路径案例](../../startup/references/native-startup-path-casebook.md)、[启动契约](../../startup/references/startup-contract.md)保留其实际路径/renderer/parser故障协议。不得将静态成功覆盖这些运行失败，也不因成品修改自动重跑无关奖励存档CI。

本次完整可复用校准结果见[校准记录](calibration-results.json)；真实游戏原始日志/逐文件清单留项目证据库，避免分发私人项目与账号。

## Cocos 2.4 Texture2D 原生文件缺失拒包（2026-10-25）

共享 `audit_packed_assets.py` 解析实际 `config.json` 的 packs/uuids 与 `cc.Texture2D` pack 数据，按引擎扩展名编码和压缩UUID规则解出 native 文件。缺失图片必须在 writer 写 ZIP 前拒绝；不能只检查 JavaScript 字面路径或 ZIP 与当前残缺目录一致。该检测覆盖此明确的2.4纹理pack协议，其他资源协议仍沿用各自检查与实际加载。

回归 `scripts/test_packed_native_textures.py` 包含完整图、缺图、多编码缺失与路径越界反例。真实缺图包先被旧 writer 接受，修复后同一故障边界必须拒绝且无输出；当前完整包再次通过。游戏原始图片、包与运行证据留项目。

## 执行去重与实际耗时

已授权产包走writer→最终交付文件核对；writer内部已经检查的同一产物，不在两个节点之间另手工完整检查。单独检测已有包只运行一次check_package，不为检查重新制作游戏或反复压缩原目录。最终交付核对保留，避免拿错包；内容变化后不能拿旧报告当通过。

启动依赖扫描只复用同一Python进程内相同源码字节和相同解析器/Acorn指纹的纯AST结果（有界、无磁盘缓存）；缺Node、解析失败、源码或解析器变化均不复用。每次仍重新解析项目配置、解析依赖相对路径、核缺失/大小写与当前文件，不缓存包通过、宿主/触摸探针或运行证据。

共享verifier在同一调用内仅解压读取每个ZIP文件一次，CRC、QA标记、文件SHA与启动闭包使用同一份字节；资源分析将这份已验证字节放进隔离临时目录，不再次读取ZIP。临时目录始终收尾，ZIP变化、CRC损坏、错误App ID与源Native差异仍拒绝。不提供读取历史报告即放行的参数。

## 2026-10-26 最终启动与恢复强制门禁

按[每包启动与恢复规则](../../startup/references/final-package-startup-gate.md)执行。轻量writer不再仅靠文件成功放行；正式writer复核同版启动与恢复材料，沿review重跑已登记启动器；prepare_delivery复核同版材料及原始证据。三入口均接共用audit_final_package_startup，缺材料或失败不交普通完成包。不扩大无关CI，也不声称手机扫码已验证。

## 扫码后进不去：出包前清单（2026-10-26）

以下在当前最终Native上逐项关闭；失败和未验均不能用文件成功、Web试玩或旧CI覆盖。

- [ ] **坐标协议**：按包内真实adapter注册回调和引擎转换核SDK字段，验证screenX/screenY、0、已有clientX/clientY及两套字段同时存在；保留identifier、接收者和已有有限值。转换结果须有限，修复须早于输入注册。直接调用转换函数仅是局部合同，仍须真实输入产生业务变化。
- [ ] **启动各阶段失败出口**：入口同步异常、首批资源、主bundle、启动场景失败/无回调均须有玩家可见可操作的恢复入口。`console.error`、直接return、只处理成功回调或浏览器DOM Retry不算小游戏恢复；静态命中先定点验证，不仅凭某个API名判故障。
- [ ] **Retry真实恢复**：记录失败→一次真实触摸Retry→底层新请求身份→HOME可操作→进关并产生玩法变化；检查旧回调隔离。有Retry字样或只回到加载画面不通过。沿用[加载恢复合同](../../startup/references/loading-recovery-regression.md)，不新增平行报告体系。
- [ ] **最终绑定与拒包**：最新共享坐标探针及最终Native启动/恢复门禁必须接真实writer和交付核对。旧故障须被同一判据拒绝，修复及正常对照通过；缺runner/原始材料明确未验，不能补写passed。ZIP改名按SHA确认身份，Native字节变更重新取证。

漏检原因：浏览器触点自带client坐标，绕过SDK字段缺口；只看正常启动忽略失败回调；静态/体积成功被误当作启动完成。上述清单只补输入与启动恢复，不扩大无关玩法/美术CI。实际游戏包、账号和证据留项目，Skill不携带私人路径或App ID。


## 检查顺序与一致性限制（2026-10-26）

按[便宜拒绝、输入冻结与耗时](gate-order-and-identity.md)执行：确定性静态问题先于可信启动运行；最终ZIP核对不省略。启动校验前后候选和证据须一致，交付回执前再次核原Native与ZIP一致。变动或畸形证据返回具体拒绝，不继承前半段通过。


## 资源完整性与已报告问题（2026-10-26.package-gate-v2）

按[强制资源/问题门禁](resource-and-reported-issues.md)执行。动态资源从当前业务AST反查，不能靠只写几个存在的资源通过；问题历史固定且不可用空表替代，未复验/失败/相关指纹变化拒包。完整writer、轻量writer和最终交付都须传当前`--resource-manifest`与`--project`；复用有效定点证据，不触发全量运行。

## 编译包中的资源封装（2026-10-26）

同名 `this.load()` 先确认实际所属组件与方法体，不能直接当引擎资源调用，也不能只按名称豁免；原方法体仍须被独立清点。动态图片域从生产登记表、配置ID和关卡数据展开，只有源码明确的存在性判断才允许裁掉可选分支，不抄整个catalog作需求。版本相关适配绑定完整JS源集合；未知代码变更恢复拒绝。正式采用前用删首页必需资源、删数据推导的末项资源及新增未知动态调用校准，再验当前产物。
