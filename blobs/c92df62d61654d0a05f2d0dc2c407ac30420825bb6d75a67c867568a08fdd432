---
name: cocos-game-tiktok-package
description: "开始前移除分享与全部排行榜（好友排行、Ranking、Leaderboard），不得保留。打包/出包：用户说打包、重新打包、出包、出个包、给我包、上传包、上传测试包、测试包、检测包、给别人检测的包、上传 TikTok 平台包、TikTok 包、平台包、压缩包、ZIP、交付包、正式包、提审包（package / build zip / upload zip / TikTok package）时使用。不管叫什么，只交一种包：可以直接上传 TikTok 后台的平台包——Cocos 真实 Native 小游戏构建，ZIP 根目录直接是 game.js、game.json、project.config.json，assets/resources 等大资源放进 Cocos 小游戏普通分包，未压缩主包≤4,000,000 字节、总包≤30,000,000、独立分包各≤4,000,000，写 ZIP 之前就拒绝超限。严禁外层文件夹、Web 包冒充 Native、主包超 4MB、源码包、ZIP 套 ZIP、__MACOSX/.DS_Store、测试跳关残留、旧 App ID。用 make_tiktok_zip.py 出包（先跑门禁、不合格不写 ZIP、写完回读核对每个字节），同时给同版本地试玩链接。 发现阻断项自动修复、补对应测试并持续到测试ZIP交付，不以拒包报告结束。"
---

**成品测试通过后自动接续出包（用户2026-10-26）**：按[成品测试通过后自动出包](../cocos-game-to-english/references/check-fix-package-loop.md#成品测试通过后自动出包用户2026-10-26)执行。当前成品测试完成后连续封装证据、执行正式writer与交付核验，主动交同版ZIP和试玩链接；不得停在“报告未封装/未再次要求打包”等待“继续”。用户明确仅检测、评审、试玩或暂停时按其边界。


**每次制作的时间、token与结案统计（用户2026-10-26）**：按[制作记录与完结汇总](../cocos-game-to-english/references/production-accounting.md)，确定项目后即启用本游戏追加台账；各玩法/美工/实现/实际测试/返工/交付步骤主动记录起止、工作/工具/等待、结果与证据，阶段边界增量收集绑定会话用量。用户说“项目完结了”时主动在当前聊天推送分阶段及总历时、可核实token/额度/成本、测试明细和优化分析，并本地归档；缺数据标未知，缓存/推理不重复相加，共用账户额度不冒称项目独占。记录不扩大制作/CI范围，不建常驻进程或额外定时任务。


**本地广告模拟与上传包隔离（用户2026-10-26）**：用户明确用于自行检测的广告模拟，只在独立本地试玩服务中启用，按[手动广告模拟](../cocos-game-to-english/references/manual-ad-simulation.md)操作。平台上传测试包、Native和最终ZIP不得包含模拟面板、模拟SDK、伪完成入口或模拟降级发奖；无真实SDK时不可自动奖励。写ZIP前和最终ZIP检查均执行共享`audit_no_ad_simulator.py`，发现本工具文件名或特征字节（即使改名、关闭开关）拒包，清理重建后继续；保留正式广告适配器及真实奖励代码。该静态检查只覆盖已知工具残留，其他自定义假SDK/无条件成功仍须按实际广告适配器检查，不能宣称静态扫描证明一切真实接入。仅用户明确的本地模拟试玩可通过原奖励流程保存模拟奖励，不能带入平台产物。


**不展示 Credits 界面（用户 2026-10-26）**：玩家端不新增或保留 Credits、制作人员、鸣谢页面、弹窗、标签及入口，也不以 About 页面承载相同制作说明。已有入口连同对应路由/弹窗移除，不能仅改名；不向玩家展示 AI/GPT 分工、英化/改编过程或原素材保留说明。游戏名和版本号可在设置页底部小字展示；“皮肤仅改变外观”放皮肤页。素材来源、作者、许可证和制作记录保留在项目交接文档；优先选择无需游戏内署名的素材，现有许可证确有强制展示要求时先说明并采用符合许可且不新增 Credits 界面的方式，必要时更换素材，不能直接删掉许可义务。制作/修改检查受影响设置入口与弹窗；出包只核本次相关入口和实际产物，不重跑无关CI。



**索取测试包即持续修复到交付（用户2026-10-26）**：“可以给我上传测试包”“给我测试包”“打包/重新打包”“出可上传包”等同义请求，按[出包请求就是修复到交付的授权](../cocos-game-to-english/references/check-fix-package-loop.md#出包请求就是修复到交付的授权用户2026-10-26)执行：发现拒包项后自动修复、补对应测试、重建并继续正式出包，交最终ZIP；不得只报拒包或候选未完成就结束/等待“继续”。只复测阻断项，不绕门禁，不扩大平台上传发布权限；用户明确只检测或只改Skill时按其范围。

**资源漏项与已报告问题拒包（2026-10-26.package-gate-v2）**：按[实际资源反查与定点问题复验](../cocos-tiktok-package-check/references/resource-and-reported-issues.md)执行。两个writer和最终交付共用强制门禁：清单遗漏实际调用、无法展开的动态请求、未登记历史、未复验/失败/旧指纹问题均拒绝；已有有效定点证据仅核依赖，不重跑无关全量CI。收到故障反馈先登记固定问题历史，禁止出包时换空表。

**每次新测试包必查启动与卡加载（用户 2026-10-26）**：按[最终Native启动与恢复门禁](../cocos-game-to-english/references/final-package-startup-gate.md)执行。成品直接出包也必须核当前Native的真实入口/adapter/引擎、HOME可操作→真实触摸→玩法变化及失败→Retry新请求→恢复；缺同版证据、旧绑定或失败拒包。仅限启动链，不重跑无关CI或已批准美工；本地通过不得写成手机扫码通过。


**统一 Cocos 加载界面（用户 2026-10-26）**：按[官方默认加载与重试样式](../cocos-game-to-english/references/cocos-loading-screen.md)执行。所有开发者可控加载页使用 Cocos 官方样式，不出现游戏标题、角色、场景或游戏专属加载文案；保留真实进度、失败重试及首页就绪判据。


**任何用户本地预览/试玩链接的前置条件（用户2026-10-25）**：生成、恢复或随包附带链接之前，先按[固定手机尺寸试玩](../cocos-game-to-english/references/user-phone-preview.md)实施并验证。共享 `serve_preview.py` 默认内部390×844手机框，桌面不放大全屏，小窗口只等比缩小；原始导出/Native/ZIP和用户存档不改。只交试玩时仅核外壳尺寸、真实首页及一次开始，不启动全量CI。不得先发裸全屏地址再让用户自行缩窗口。


**持续执行与进度汇报（2026-10-25纠错）**：已授权工作按[持续修复与交付](../cocos-game-to-english/references/check-fix-package-loop.md)推进，进度用commentary，不以固定时间/修复数或“整体未完成”要求用户发继续。只在授权终点、必需人工节点、用户/工具停止或确需外部输入且独立工作已尽时结束；新聊天按既有接续授权。


**加载页假通过防复发（2026-10-25）**：启动故障/加载维护或所属最终功能轮，按[启动业务完成与工具反例校准](../cocos-game-to-english/references/loading-scene-false-positive.md)核HOME可操作→真实输入→玩法变化。scene active、满进度、桩或ZIP闭包不替代实际业务；先查首错，不隐藏Loading。普通换图不扩CI，已有故障定点闭合。


**本地验证的已知前提与汇报（用户 2026-10-25）**：内部保留实际证据层级，用户已知本地与上传验证的区别；日常不重复该前提或免责声明。仅在询问、具体混淆或需要处理的失败时说明，不把本地结果称为真机/真实广告通过。


**美术检查前移（用户 2026-10-25）**：按[美术验收前移与试玩后锁定](../cocos-game-to-english/references/art-before-trial.md)执行：所有美术测试在交用户试玩前完成；用户确认后到测试包交付之间不再美工测试、不重新评判已批准画面。最终画面字段只查运行故障，不夹带美术标准。

**主包超限的已知故障防复发（2026-10-24）**：按 [完整解法与最小拒包合同](../cocos-tiktok-package-check/references/main-package-overflow.md)执行。所有包按未压缩字节查主包/总包/分包，写临时ZIP前拒绝超限，最终ZIP与原Native全量比对；只有分包/加载改动才追加失败→单次真实Retry→玩法输入复测，不因此重跑无关全游戏CI。


**所有测试包的最终文件检测（2026-10-24）**：凡已授权产出TikTok测试包/上传包/扫码包/平台ZIP，最终交付前使用 [TikTok测试包最终检测](../cocos-tiktok-package-check/SKILL.md)。共享verifier现强制检查game.js可达依赖、引擎、分包入口、Cocos场景/数据pack；已批准的成品直接出包使用新Skill的build_checked_zip.py作为文件校验writer，旧文仅允许make_tiktok_zip.py和全量review的要求在该成品模式下由此限定路线替代。成品直接出包也执行该文件级检查，沿用本轮授权范围，不因此重跑完整游戏CI。检查失败继续定点修复和出包，完整证据留内部，默认只交最终ZIP。


**Native场景路径复发门禁（2026-10-24）**：手机卡启动、scene-load-failed、分包迁移或适用出包风险，按[Native启动与场景路径案例](../cocos-game-to-english/references/native-startup-path-casebook.md)执行现有audit_native_resource_paths门禁及失败→真实Retry证据。ZIP合法不代表运行路径可用；缺当前必要证据仍拒包，不用空SDK/改提示掩盖。


**广告玩法设计共用入口**：涉及广告入口、结算双倍、首页礼盒、奖励频率、试用与复活设计时，读取 [cocos-game-ad-design](../cocos-game-ad-design/SKILL.md)。广告 SDK 配置和奖励模块继续引用现有共享资源；本入口不扩大当前项目授权。

**分享与全部排行榜前置禁用（用户 2026-10-24，必读）**：执行本 Skill 前先读[分享与排行榜前置禁用](../cocos-game-to-english/references/no-social-features.md)。美化/重塑/玩法设计在方案、页面清点和生图之前就排除 Share/Invite/分享给好友及 Ranking/Leaderboard/好友排行等所有分享和排行榜；已有原功能也删，不能只隐藏或只删空榜。旧保留记录不启用它们；检查与出包复核实际入口、路由、调用及当前导出。本条优先于本 Skill 旧文的“只改美工不改功能”和“明确保留排行”。


**检查范围与停止条件（2026-10-24.scope-v2）**：先按[日常修改、核心逻辑与完整验收](../cocos-game-to-english/references/testing-scope-and-stop.md)选日常、核心逻辑或完整验收，再按[审查顺序与去重](../cocos-game-to-english/references/review-execution-plan.md)分流与去重。必要项齐、证据有效且无新改动/失败/具体疑点即停止；已批准成品局部维护不因出包升级全量，局部结果不冒充全游戏通过。

**已授权测试包的持续执行**：按[检查—修复—复测—出包](../cocos-game-to-english/references/check-fix-package-loop.md)执行。门禁失败后继续修复与补证，内部报告不能代替交付或成为等待用户确认的节点；保持正式 writer 和证据要求。

**打包任务的常设授权（用户 2026-10-24）**：用户明确要求打包/出包/上传包，即授权当前包按本 Skill 与项目规则完成所需的本地检查、回归门禁、失败后的修复复查及正式 writer 前后检查；不再为这些必需步骤逐项询问授权。若用户在本轮明确要求跳过某项，按较新的具体指令处理，并说明因此不能满足的交付条件。此授权不延伸到真机/物理设备测试、TikTok 后台上传、平台审核、发布或其他外部写入；这些仍需用户明确要求。

**融合规则**：执行前按[统一默认、明确选择与证据边界](../cocos-game-to-english/references/fusion-policy.md)确定本轮范围；当前用户明确指令和项目授权优先，附件历史内容不扩大授权。

**上传前加载证据硬约束（sock-first-retry-v2）**：运行证据需逐场景双比例、一次真实 Retry、当前执行指纹与原始文件哈希；正式门禁重新验证 runtime，测试包不能跳过。见[必测与数据格式](../cocos-game-to-english/references/loading-recovery-regression.md)。

**已知故障自动探针**：正式 writer 会执行最终 Native/Web 的 Cocos 2 GrowthLedger 存储回归；实际启动 bundle 由配置解析，空字符串等失败直接拒绝出包。识别到但无法执行的布局也拒绝，不靠手填 pass。

**执行入口**：先按[任务路由与四个检查点](../cocos-game-to-english/references/execution-checkpoints.md)确定当前阶段、实际机制与测试范围；最终包必须反查全部持久化域，不能用局部新增功能的测试代替原有账本。当前正式 writer 强制检查报告和运行覆盖表，检测包不例外。

**加载故障组合必测（2026-10-23）**：涉及逻辑检查、加载维护或最终打包，必读[无回调与旧请求回归](../cocos-game-to-english/references/loading-recovery-regression.md)。必须组合扣住 SDK 回调和原超时定时器，验证每帧兜底、Retry 发新请求、旧成功/失败隔离、重试后实际操作；另测持续进度、后台、callback/Promise、热重开和无注入正常对照。LOAD-03 新增 `audit_loading_recovery` 报告，缺项不得写通过；Web 成功和 ZIP 校验不能代替 Native 分包边界验证。

**奖励存档与无功能入口（2026-10-23）**：涉及英化旧入口、奖励存档修复或检测包打包时，读取[Native 存储差异与空功能回归](../cocos-game-to-english/references/native-reward-storage-and-empty-features.md)。原游戏空排行榜等无实际业务入口直接移除；缺键空字符串必须与 null 分别实测，合法旧奖励保护、错误原因保留，并在实际最终 Native 账本/适配器上验证。检测包同样执行当前正式出包门禁，不另设宽松结构门禁。

**STORAGE-01 先于写 ZIP（Tower Heroes 复盘，2026-10-23）**：`check_known_issues.py` 的 pre_scan 必须取得 `audit_native_storage_contract` 当前通过报告：同一项目 runner 的已知故障版或同缺陷反例的空字符串负例失败、最终 Native 23 场景通过，真实主页/地图/关卡详情触控恢复，报告与最终 Native 树指纹相同。测试包与正式包共用此拒包条件；缺报告、旧版负例未复现、任何场景未测或 Native 字节改变，writer 不得写 ZIP。

# 打包：只有一种包——可直接上传 TikTok 的平台包（用户 2026-10-23）

## 已发现缺陷必须变成可执行拒包条件

人工发现的新问题先保存故障反例，再让同一自动检查在反例失败、修复版和正常对照通过；通过后接入 writer，不能只追加一句“仔细检查”。当前 `make_tiktok_zip.py` 已在完整 review 前强制执行体积与 `audit_packed_assets.py`，检查迁移后丢失的本地路径、入口 require、图集越界、压缩后图片 SHA 过期；`run_reward_storage_probe.py` 已支持 PaperCut 的实际 GameData＋Native adapter，自动测合法零余额、坏档保留、读写/回读失败和重复奖励。已识别协议无法加载时拒绝，不把它变成 N/A。工具自校准用 `test_packed_assets_gate.py`；本游戏负例、日志、GUI 和复盘留项目，不复制到共享 Skill。

通用流程按 [可执行回归沉淀](../cocos-game-to-english/references/executable-regression-retention.md)。这些约束用于已知缺陷，不能保证自动发现全部未知问题，也不替代真实画面与互动验收。

## 新增硬门禁：先查未压缩总包体积（2026-10-24）

本次平台拒包暴露了一个流程漏洞：只做 ZIP CRC/路径检查、手工压缩，仍可能把 30 MB 以上的包交给后台。以后每次“测试包/上传包”先运行只读快速探针，再运行完整 writer：

```sh
python3 scripts/upload_preflight.py <Native目录或现成ZIP>
```

探针必须读取目录或 ZIP 条目 `file_size` 的**未压缩字节**，把结果写进本轮证据；ZIP 压缩后大小不能替代它。`total_uncompressed_bytes > 30_000_000` 或主包 `> 4_000_000` 立即拒绝，禁止继续手工压缩、删文件凑数或把超限包交给用户。模拟/复盘必须使用一个已知超限反例验证探针返回 `status=refuse`，再进入 `make_tiktok_zip.py`。任何交付 ZIP 都必须由正式 writer 生成；手工 `zip -r`、Finder 压缩或绕过 writer 的旧流程视为失败。

**为什么单独一个 Skill**：SquareRush 的旧包被 TikTok 拒绝——Cocos 的 `assets/resources` 留在主包里，**未压缩主包 8,754,975 字节，超过平台主包上限 4,000,000**。修好的 UPLOADFIX 版本把 resources 配成 Cocos 小游戏**普通分包**（`subpackages/resources`），启动时带进度加载，写 ZIP 之前就按平台限额检查，旧包作为反例被拒绝且一个 ZIP 都不写。以前还出过：多套一层外层文件夹、Web 包改名当 Native、源码包、ZIP 里套 ZIP、带 `__MACOSX` 的包。**从现在起，所有包都只能是 UPLOADFIX 这种形式。**

工具：`../cocos-game-to-english/scripts/make_tiktok_zip.py`（出包，下文简称 `make_tiktok_zip.py`）和 `../cocos-game-to-english/scripts/verify_native_zip.py`（检查任何一个现成的包）。形式规则和每种错包的改法见[包的形式](references/package-forms.md)。

## 什么时候用

先判断当前任务路线，不能只按“测试包”三个字决定重跑范围。完整制作首次出包走完整 writer；已有用户批准的成品局部维护/原样重出走最终文件检查 writer，沿用有效功能证据，新增故障只查受影响链。美术锁定后不重开美术验收。

| 用户说 | 做什么 |
|---|---|
| 打包、重新打包、出包、给我上传包、正式包、提审包、交付包 | 正式出包：四个阶段（英化/重塑的阶段 4）通过后才做，**带门禁**（下面第 3 步加 `--review`） |
| 上传测试包、测试包、检测包、给别人检测的包、先出个包看看、压缩包、ZIP | 按当前任务分流：完整制作使用 `make_tiktok_zip.py` 及当前 `--review/--project/--web/--build-tag`；已批准成品维护使用 `../cocos-tiktok-package-check/scripts/build_checked_zip.py`，随后最终ZIP与实际Native核对及主动交付；不重跑完整游戏CI |
| "这个包能不能传""检查一下这个包"（现成的 ZIP，含别人的） | `python verify_native_zip.py <包.zip>`：内置 TikTok 限额和禁止项，不通过就说明哪一条、怎么改 |
| 要源码、要工程 | 那不是上传包：另外给源码，**不叫"包"、不和上传包混在一起**，也不放进上传 ZIP |

不自动打包：用户没说就不出包（两个主 Skill 的规则不变）。

## 唯一允许的形式

1. **Cocos 真实 Native 小游戏构建**（项目已有的 TikTok 小游戏构建配置），不是 web-mobile，不是预览目录。
2. ZIP **根目录**直接是 `game.js`、`game.json`、`project.config.json`（还有 `src/`、`assets/`、`subpackages/` 等构建产物），**没有外层文件夹**。
3. **未压缩主包 ≤ 4,000,000 字节**、**总包 ≤ 30,000,000 字节**、**每个独立分包 ≤ 4,000,000 字节**；普通分包只计入总包（2026-10-05 平台概览，非 Unity）。按未压缩字节算，不看 ZIP 压缩后的大小。
4. `assets/resources` 和其他大 bundle（大图集、声音）配置成 **Cocos 小游戏普通分包**，构建后在 `subpackages/<名字>/`，`game.json` 的 `subpackages` 有声明，引擎配置（2.4 的 `src/settings.js`、3.x 的 `src/settings.json`）和 `ccRequire.js` 同步；主包只留引擎、入口和首屏要用的东西。
5. 启动时先加载分包：**看得见的进度**、前台无进度超时、Retry 重新发请求（不是重放旧回调）、迟到的旧回调不影响新请求、切后台的时间不算超时（按[启动契约](../cocos-game-to-english/references/startup-contract.md)）。
6. `project.config.json` 的 appid 是**当前目标**的 App ID；广告位等公开配置是这个应用的。
7. 没有：源码（`.ts`、`.meta`、`library/`、`temp/`、`settings/`）、ZIP/7z/RAR 套娃、`__MACOSX`/`.DS_Store`/`Thumbs.db`、非 ASCII 路径、测试跳关标记 `__QA_LEVEL_JUMP__`、说明文档和截图。
8. 用户拿到就能**直接选择或拖进 TikTok 后台代码包上传区**，不用解压、重压、挑内层文件。

## 步骤

以下第3、5步的完整review流程只用于完整制作/完整验收路线。已批准成品直接执行 [最终文件检查与交付](../cocos-tiktok-package-check/SKILL.md) 的轻量writer路线；不得为满足本节旧字段重新验收已批准美术或补跑无关CI。两条路线都执行固定体积、真实Native依赖、目标配置及最终字节检查。

1. **导出 Native 构建**：Cocos 里用项目的 TikTok 小游戏构建配置导出（显式写项目、构建配置、版本、输出目录；打包前读回实际配置，防止带入旧游戏或旧 App ID）。
2. **配分包**（只做一次，以后每次构建都在）：
   - Cocos 2.4：资源管理器里选 `assets/resources` 文件夹（它本来就是 Bundle）→ 属性检查器里目标小游戏平台的"压缩类型"选"小游戏分包"，构建后看 `subpackages/resources/`；其他大文件夹先勾"配置为 Bundle"再同样设置。
   - Cocos 3.x：选 bundle 文件夹 → 勾"配置为 Bundle（Is Bundle）"，目标平台的压缩类型选"小游戏分包（Mini Game Subpackage）"；不能只给 `.meta` 写 `compressionType` 就说分好了（见 [Native 与 IAA](../cocos-game-to-english/references/tiktok-native-iaa.md)）。
   - 构建后迁移的方案：分包里的入口 `game.js`、`config.json` 路径必须和 Cocos 加载器一致，`game.json`/settings/`ccRequire.js` 一起改，并在 Ego 里真实启动到首关。
   - 声音等其他大资源也单独分包（主包首屏前不加载大文件，见[启动加载计时](../cocos-game-to-english/references/startup-loading-timing.md)）。
3. **出包**（在 `cocos-game-to-english/scripts` 里运行或写绝对路径）：

   ```sh
   python3 make_tiktok_zip.py --native <Native构建目录> --app-id <App ID> \
     --out <交付目录>/<游戏名>_TikTok_<test或release>_<版本>.zip \
     --project <工程> --web <同版Web构建> --build-tag <版本> --review <工程>/docs/test/known-issue-review.json \
     --resource-manifest <工程QA目录/当前业务资源清单.json> \
     --startup-contract <当前启动报告.json> --loading-recovery-runtime <当前恢复runtime.json> \
     [--board localize|remake]
   ```

   脚本按顺序：先跑门禁 `check_known_issues.py check --stage pre_scan`（失败就停，BUILD-03）→ 查形式（外层文件夹、Web 构建、源码、套娃、非 ASCII、测试跳关、App ID）和体积（主包/总包/独立分包），**不合格就拒绝、一个 ZIP 都不写**，并列出主包里最大的 5 个文件和改法 → 写到临时文件 → 回读核 CRC、安全路径、根入口、限额、每个文件和 Native 构建同字节 → 再独立解压到带空格的目录比一遍 → 全过才移到 `--out`，旁边写 `<ZIP名>.report.json`。`.DS_Store`/`Thumbs.db` 这类垃圾文件自动不放进 ZIP（报告 `left_out_junk` 列出来）。已有同名 ZIP 不覆盖：新版本用新名字。
4. **被拒绝时**：按报错改源头再重跑，不手工改 ZIP、不删文件凑体积、不调大限额（`--max-*-bytes` 只能更严）。常见改法见[包的形式](references/package-forms.md#被拒绝了怎么改)。
5. **正式出包还要**（BUILD-02/03/04，`--stage post_package`）：
   - BUILD-03：`test_writer_refusal.py` 用本脚本当打包命令跑一遍（给它单独的 `--out`，跑完删掉那个检查用的 ZIP），证明缺检查表、有失败项、指纹过期都出不了包；
   - BUILD-04：`<ZIP名>.report.json` 放进 BUILD-04 的 `auto_reports`，观察项见[检查表](../cocos-game-to-english/references/known-issue-checklist.md#只有一种包可直接上传的-tiktok-平台包build-04)；
   - 包内启动：从这个 ZIP 解压出的文件在 Ego 里真实启动到首关（含一次分包加载失败 → Retry 恢复），见 [Native 启动到首关](../cocos-game-to-english/references/cocos-runtime.md#先验证-native-启动到首关)；
   - 其余交付检查按[包与交接](../cocos-game-to-english/references/delivery-and-handoff.md)。
6. **交付回复**（同一条回复里）：
   - 同版本地试玩链接 + 这个 ZIP 的可点击链接（只给一个 ZIP，不给多个候选；旧 ZIP 保留，在交付记录中标明被哪一版替代；未经用户明确要求不删除历史包）；
   - 目标 App ID；
   - 体积表：主包 X / 4,000,000、总包 Y / 30,000,000、分包（普通/独立）各多少字节；
   - "直接上传，无需解压重压"；
   - 完整制作路线必须通过当前review门禁；已批准成品路线须经轻量writer和最终文件检查。两者都主动附当前ZIP链接，不用诊断报告代替交付。

## 不能做的（全部是以前真实出过的错）

- 主包超 4,000,000（resources 留在主包）——SquareRush 被拒的原因；
- ZIP 里多一层文件夹（`Game/game.js`）；
- Web（web-mobile、有 `index.html`）ZIP 改名或补个空 `game.json` 冒充 Native；
- 源码 ZIP、工程目录、`library/`/`temp/`、`.ts`/`.meta` 进包；
- ZIP 套 ZIP（上传包里再放一个 zip，或把上传包和说明一起再压一层交出去）；
- `__MACOSX`、`._xxx`、`.DS_Store`、`Thumbs.db`；
- 测试跳关、调试面板留在包里；用别的游戏/旧应用的 App ID；
- 绕过适用的正式writer自己手压（完整制作用 `make_tiktok_zip.py`，已批准成品维护用 `build_checked_zip.py`；禁止Finder"压缩"、`zip -r 文件夹`）；
- 把"本地检查通过"说成"平台已接受""已上线"。

**加载故障复盘入口（v20完整复检）**：加载维护、完整逻辑检查或打包前，按[加载与重试案例及验证方法](../cocos-game-to-english/references/loading-recovery-casebook.md)识别本项目实际加载层，读取对应复现与修复步骤；字体/图片/原生分包、请求独立计时、取消重进、真实HTTP新请求、最终产物绑定均不可由入口替身检查代替。案例中的历史游戏结果不代表当前项目通过。

**完整制作路线交付前必检**：按[简要问题清单](../cocos-game-to-english/references/known-issue-checklist.md#提供测试包前的简要问题清单2026-10-23)执行适用LOAD/LOGIC/BUILD门禁及当前 `--review`，不以“测试包”名称绕过。已批准成品维护按前述最终文件检查路线，不套完整制作清单；本轮加载/逻辑改动仍定点修复复验，不把未测项写成通过。

## 输入只有 Native 导出包时

用户确认原始工程不存在、现有 Native ZIP 就是全部材料时，不把缺 assets/ 直接当作无法维护，也不伪造源码目录。允许建立导出包维护工程：保留原 ZIP SHA、全部修改列表、维护脚本与新增模块，以独立临时目录重建并比较 Native/Web 全字节。当前 Cocos 2 Screw/GrowthLedger 维护路径通过同一正式 writer 和 check_known_issues 的 `export_maintenance_review.v1` 输入分支，使用 `audit_export_maintenance.py`；它强制重建、执行实际业务回归、核 UI 证据/产物指纹和维护检查项，之后仍执行存储覆盖、Native 形式/体积、回解逐文件比对。缺报告、失败行、陈旧指纹仍须由 writer 实际拒绝测试证明。

此输入分支仅用于用户明确授权的已有导出包维护；不是“完整英化/重塑验收通过”，不能用来绕过新游戏制作、美术重做或未测功能。其他导出结构需增加经旧失败/正常对照校准的生产加载器，不把任意 ZIP 填成此 schema 就算通过。没有原编辑器源码应如实说明，但不机械要求用户提供已明确不存在的文件。

## 明确授权的完整源码维护输入

用户明确要求保留已有玩法、美术、关卡且只做维护时，不擅自新增新品模板中的皮肤、70关或礼盒。可用正式 `check_known_issues.py` 的 `source_maintenance_review.v1` 分支，不能拿新品制作通过章代替维护验收。该分支目前只支持经本轮校准的 `sock_reward_audit.v1` 生产测试协议：须保留已交付完整基线与ZIP、明确授权记录、逐文件审查源码差异；不允许替换 resources 美术/音频/关卡；完整210组双比例页面矩阵、26组启动录帧、126项源码/编译Native业务及196项机制、6项桥接、6项交付边界测试须实际重跑，LOAD-03当前12场景及原始证据重验、STORAGE-01亲自重跑23场景与负例、全部持久化域覆盖、正常通关存档、实际声音及Codex视觉检查均不可豁免。正式writer和上传ZIP规则不变，post_package还核当前writer五种拒绝对照与包内全字节。输入/协议不支持时失败，不把任意报告套此schema放行。完整制作、美术重做、资源替换及新增玩法不适用此保留范围。


**上传体积硬限制（2026-10-25）**：全部 TikTok 上传 ZIP 路线统一使用 `cocos-game-to-english/scripts/upload_size_gate.py` 的固定未压缩限额：总包≤30,000,000、主包≤4,000,000、独立分包各≤4,000,000字节。正式 `make_tiktok_zip.py` 和轻量 `cocos-tiktok-package-check/scripts/build_checked_zip.py` 的底层写 ZIP 函数均在打开输出前拒绝超限；目录检查与最终 ZIP verifier 同样保留。成品直接出包走轻量 writer，不重跑游戏CI；禁止另写未接入同一门禁的压缩脚本或Finder手压。新增出包入口必须接此门禁，并先用旧超限反例证明无输出，再用正常包证明通过；未知/未接入的外部压缩工具不在自动拦截范围。
