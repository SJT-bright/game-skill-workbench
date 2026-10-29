# Native 奖励存档与无功能旧入口（2026-10-23）

来自 Screw It v9 实际检测包问题。本文是复现方法与生产约束，不代表所有游戏存在同一故障。

## 没有功能的原游戏入口

英化不继承空实现。排行榜、更多游戏、分享、跳转等旧入口必须追到实际业务和目标平台能力：空 handler、只有音效、只打开无数据空框、依赖已失效原平台服务，都移除入口、事件和不可达页面，调整附近布局。不能为保留空入口新增虚构功能。原游戏自带并不构成 keep_original 的理由；分享与全部排行榜即使可用也移除；其他非禁止业务有实际可用功能及本次运行证据才可保留。临时无数据但有真实服务/空态与重试，不自动判为无功能。TikTok 系统右上角胶囊属于平台，不是游戏旧按钮，不按此规则删除。

## 确认过的失败链

原导出 adapter 的 getItem 直接返回 getStorageSync。账本只接受 null/undefined 代表无记录，缺键若返回空字符串则 JSON.parse 抛错。snapshot catch 隐去原因并返回 valid:false，Remove/Answer 在调用广告前被统一拒绝。浏览器 localStorage 缺键返回 null，正常浏览器试玩能掩盖 Native 差异。视频只有提示而没有原始存储返回值时，只能确认这条代码缺陷已复现，不能宣称唯一手机根因。

## 修复边界

- 按实际适配器契约区分缺键（null/undefined/空字符串）、合法字符串 JSON、合法原生对象、坏 JSON、读取抛错；不要用 if(!value) 把 0/false/错误记录当新用户。
- 对象返回同样必须通过完整 schema、scope、余额、校验和、pending 验证。写后读回要与真实返回类型一致，不能比较两个对象引用。
- 有效旧档与既有奖励不清零；损坏非空记录不静默覆盖，不拿“默认空余额”伪装恢复。不清用户正式存档。真正存储失败仍拒绝不安全扣费/发奖，日志记录原因阶段、类型/版本，不打印完整私人存档或凭据。
- Read/parse/schema/checksum/pending/write/readback 等失败要区分；用户提示可简洁，不能把这些全部吞成无诊断的 saved reward couldn't be read。

## 最小回归（实际代码，不能只测自写替身）

1. 从当前与修复前 Native bundle 加载实际账本，以及最终 adapter 的存储模块。假 SDK 只控制返回值/故障，不重写账本。
2. 同跑 missing null、undefined、空字符串；空对象、false、0、坏 JSON、错误 schema、越界、checksum、合法 v1/v2、pending、读抛错、写抛错/回读不一致。覆盖真实环境可能的 typed object。
3. 真实奖励链：新用户零余额→允许进入广告请求；完整广告结果→实际效果/存档；取消/失败零发奖；旧奖励消费一次；pending 重开恢复/确认；失败后能重试。合法旧档不重复发奖、不丢余额。
   已报商店读取错误时，加测“有历史记录→实点屏幕显示的广告/付费动作→读取守卫→SDK→库存→消费→重开”；不能拿结算账本通过代替该入口。广告不依赖无关余额，必须读取的库存异常仍保留并拒绝不安全发奖；共用按钮按[前置守卫检查](../../test/references/button-state-check.md#无响应故障的最短定位)定点核对，不扩默认成品CI。
4. 同一 harness 在旧版上失败、修复版上通过，正常对照保留。source、Web、Native 和回解最终 ZIP 分别绑定 SHA。真实触控验证 Remove、Answer 等每个实际入口；离线通过不称真广告已通过。
5. 不能用新增地图加时/普通关卡进度测试代替原有 GrowthLedger 等账本。列出所有持久化域与全部入口。出包名称为 test/检测包也不得跳过当前正式 writer 门禁、或另写只核 ZIP 结构的宽松门禁。

本次项目证据留游戏 Wiki/工程，不在 Skill 存用户视频、账户标识、广告 ID、存档值。新规则不代表其他已打开聊天已同步。

## 固定出包步骤：STORAGE-01

Tower Heroes 暴露出原规则的执行缺口：Web `localStorage` 的缺键 `null` 被当作正常对照，却没有在**最终 Native bundle** 上强制测试缺键空字符串；人工 R02 记录与 Web 首关截图仍可能让测试包流出。先前预览已经出现同类收据错误和未闭合的等待领奖日志，却仍将原包逐字节交为测试包。以后当前候选的运行日志或画面只要出现奖励阻断、等待保存、跨页重复 Retry，就须记录失败，修复并重跑对应场景；ZIP 结构通过和“能进首关”不能覆盖未闭合错误。`STORAGE-01.known_runtime_reward_errors_closed` 记录本轮日志与复验依据。

现在每次游戏测试及出包都盘点全部存储域，使用同一项目 runner 实际载入已知故障版（新游戏可用隔离生成的同缺陷反例）和最终 Native 的账本、存储 adapter。只替换底层存储/SDK 边界，不改被测业务方法。原始结果包括 `cases`（每项 `pass` 或 `fail`）、runner/bundle/adapter SHA；已知故障版或同缺陷反例的 `missing_empty_string` 必须 `fail`，当前全部 23 项必须 `pass`。

将执行记录写成 `native_storage_trace.v1` JSON：顶层 `binding` 等于本轮 review 的完整 binding；`execution` 含绝对 `runner`、`runner_sha256`、实际命令参数数组 `command`（例如 `node /path/runner.mjs --bundle {bundle} --adapter {adapter}`，数组中 `{bundle}`、`{adapter}` 是必须的独立参数）；`current` 与 `negative_control` 各含 `bundle`、`bundle_sha256`、`adapter`、`adapter_sha256`、`raw_report`、`raw_sha256`。两个 raw JSON 均含 `runner_sha256`、`bundle_sha256`、`adapter_sha256`、`cases`。审计脚本会亲自重跑两次命令、解析 stdout JSON，并与原始结果比较，不能手填通过。bundle 与 adapter 可以是同一编译文件，但 `current` 两者必须在最终 Native 树内。完整场景名以脚本 `CASES` 为准，不允许缺项或“暂无相关功能”替代；无广告入口的取消和完成场景，用本游戏真实的持久化写入动作检查未误记及只记一次，不能虚构广告成功。

执行：`python3 scripts/audit_native_storage_contract.py --trace <trace.json> --native <最终Native目录> --binding <review.json> --out <storage-report.json>`。将报告 SHA 放到 `STORAGE-01.auto_reports`。`check_known_issues.py` 会复核 trace、原始结果、重跑 runner、最终 Native 树哈希；只写一个 `passed:true` 报告无法过门禁。游戏打包脚本必须执行本轮 `pre_scan`，不通过不得写任何测试 ZIP。真实触控录像/截图另记 `STORAGE-01` 六个观察字段，尤其主页→地图→关卡详情的重开、Retry 可用、遮罩退出和已知运行错误关闭。

## 既有 JavaScript 游戏的明确保留范围

用户明确选择“保留现有玩法，只修复并交测试包”时，模板的新 TS 模块、皮肤、礼盒、签到样式及结算倍数不能覆盖该决定。默认新制作规则不变；本分支只支持已有奖励链的生产 JavaScript 维护。`MOD-01/02` 仍必验，签到存在时 `FEAT-02` 仍必验；不将整项永久 N/A，不免除奖励清单、广告终态、事务、存档、双比例 GUI、性能、当前 binding/raw SHA 或 ZIP writer 门禁。

`audit_game_modules.py` 和 `audit_optional_features.py` 可用 `--maintenance-scope <path>` 指向游戏工程外部的维护证据；不必改冻结源码。未给参数时仅发现 `<project>/docs/maintenance-scope.json`，没有记录仍走原模板分支；记录残缺或新模块请求不能退化成通过。

scope JSON 使用 `schema: maintenance_scope.v1`、`mode: preserve_existing_gameplay`、`new_modules_requested: false`、准确 `project` 和完整当前 `binding`。必须附 `authorization:{path,sha256,excerpt}`（保存用户决定原文，excerpt 必须在文件中）、`original_sources:[{path,sha256}]`、`existing_features`（保留签到用 `daily_checkin`），以及 `source_inventory`、`gui_evidence`、`runtime_trace` 的引用。引用都是 `{path,sha256}`，相对包含它的 JSON 文件解析。该记录是须由 Codex 复核的授权与适用性声明，不声称 JSON 能鉴别人类作者。

`source_inventory` 指向 `maintenance_source_inventory.v1`：当前 binding、`source_files`、完整 `scene_files`（实际 assets 下全部 .fire/.scene），和 `routes.home/map/stage_details`。每条 route 有 `present`、`source_reason`、`gui_evidence`；存在的 route 还须映射实际 `scene_files`。不存在地图或详情，须有源码扫描及实际导航盘点，不能凭类型猜测。场景名中已发现 map/stage-details 或场景清单不完整会拒绝不存在声明；其他语义别名由 Codex 对照原始源码及真实 GUI 核实。维护模块还须填 `reward_api`（实际 qualified JS API）和 `reward_callsites:[{path,sha256,line,reward_entry_id}]`，扫描到的所有调用位置须完整映射固定奖励入口。

GUI 引用指向 wrapper：`execution_binding`、`route`、`viewport:[w,h]`、`trusted_touch:true`、具体 `interaction_effect` 和非空 `raw_evidence` 引用。各 route 和通用证据均需两种不同手机比例。route wrapper 有 `route_present` 与 `actions`：存在的 route 必须包含 `reopen`、`retry`；不存在的 route 包含 `navigation_inventory`。必须保留实际触摸、源服务指纹、状态变化及截图；wrapper 标签不替代原始证据，检查器只核引用，最终仍由 Codex 审原始执行。

`runtime_trace` 指向 `maintenance_runtime_trace.v1`，含当前 binding、`artifact_roots:{source,web,native}`、`execution:{runner,runner_sha256,command,dependencies:[ref]}`、`raw_report:ref`。command 为 argv 数组，真实生产 artifacts 或其根目录必须是明确输入；Web/Native 整树指纹须匹配最终 binding。runner 要真正加载生产函数并断言，不得只汇总旧报告或返回恒定 pass；脚本及其 helper 都要列 hash。检查器重跑该命令，stdout JSON 必须与 raw_report 完全相同。

raw 使用 `maintenance_runtime.v1`，有当前 binding、`contexts.source/web/native`，各含实际 JS `artifacts` 引用及 `cases`，另保留原始观测 `raw_evidence`。三个 context 都必须通过下列 case：

- `ads.` 前缀：`completed_once`、`cancel_no_reward`、`duplicate_callback_once`、`late_callback_ignored`、`timeout_no_reward`、`leave_reopen`、`storage_failure_no_reward`、`readback_ambiguity`、`reload_durable`、`ledger_balanced`。
- `modules.` 前缀：`button_inventory_complete`、`economy_preserved`、`original_mechanics_preserved`。
- 保留签到时 `checkin.` 前缀：`date_boundary`、`same_day_duplicate`、`day7_reward`、`clock_rollback`、`save_failure`、`readback_ambiguity`、`restart`。

结果仍要求现有广告按钮的可信触摸、取消/完成的实际 UI 反馈、既定倍数、到账、重开一致和性能证据。分享、邀请、交叉推广和未获授权的新增扩展不会因本分支自动变为合法。MOD-02 / FEAT-02 的维护观察字段在 catalog 的 `maintenance_observations` 中；只有当前 scope 完整验证通过才启用这些映射，原始模板字段保留。

### STORAGE-01 v2 的真实存在路由与负例

原 `native_storage_trace.v1` 的全部要求保持。`native_storage_trace.v2` 额外提供 `project`、`trace_base`（相对引用基准）和 `route_inventory:ref`，使用上述实际源码与 GUI 路由清单。当前23个 case ID 都仍需出现；不存在的地图/详情只能明确写 `not_applicable`，存在的必须真实 reopen/Retry 且 pass。报告分列 checked_routes / excluded_routes，不把缺项转换成 pass。

负例 `kind` 为 `historical_release` 或 `controlled_legacy_fixture`，并有 `provenance:ref`。历史发布包若不复现该缺陷就如实保留比较，不得称已复现。受控 fixture 还必须提供 `base_bundle:ref`、`patch:{before,after}`、`mechanism`；before/after 是一条准确单行，base 中只出现一次，精确替换后字节必须等于 fixture。相同 runner 必须执行 fixture，让恰好 `missing_empty_string` 失败，其余非缺席路由 case 继续通过，排除无关崩溃。当前 Native 该 case 必须通过；runner、输入、raw 任一修改均须更新指纹并重新执行，手改结果无法通过 replay。受控 fixture 报告明确写受控校准，不冒称旧发布包或真机。

路由不存在判定还必须解析序列化 `cc.Node._name` 与 `cc.ClickEvent` / `cc.Component.EventHandler.handler`，不能只看 `.fire` 文件名。`panel-map`、`openMap`、`level-details` 等候选保留 `{route,scene,pointer,value,kind}`；不存在声明下，未解释的候选拒绝。纯美术命名误中时，用 `route_candidate_explanations` 逐项精确匹配 candidate，写 `classification: decorative|not_navigation`、具体 `reason`、`source_evidence` 与两比例 `gui_evidence`；ClickEvent 不可称 decorative。不能用通配排除或一条“不是地图”断言忽略全部候选。

source inventory 另附 `ui_route_inventory:ref`，其 JSON 有当前 `binding`、真实 `routes:[{id,role}]` 和非空 `raw_evidence` 引用；role 为 home/map/stage_details/other。GUI inventory 中存在 map/details 时，对应路由不能 N/A。现有 core 路由的 `actions` 可用 `reopen`＋`recovery`（真实业务恢复）或 `reopen`＋`retry`，不为通过检查而制造不存在的网络错误。GUI 原始 JSON 至少保留实际 trusted touch 观测，不能仅凭 wrapper 标签或截图通过。

候选解释的 GUI wrapper 还需 `target_candidate` 精确等于该 candidate；ClickEvent 的 `not_navigation` 解释须引用含真实 handler 实现的 JS 源码，并有 `candidate_activate` 的实际触摸动作，不能拿通用首页截图替代该候选的检查。外置 scope 可用 `module_decision:{currency,button_audit}` 保存已有按钮审计；无须在冻结源码内创建 `docs/modules.json`。

### 已有收集经济与临时角色（ECON-01/02）

维护游戏已有英雄/拳套等收集时，不能把 ECON-01/02 整项 N/A，也不能为过模板新增现代皮肤/地图。`audit_acquisition_progression.py --project <source> --maintenance-scope <scope> --binding <review> --report <out>` 校验保留分支；无该显式参数仍须原 unlock table/template。

scope.existing_features 包含 `collection`，并给 `economy_catalog:ref`：`maintenance_collection_catalog.v1` 有当前 binding、`original` / `current` 两侧，每侧包含实际 `artifacts` 引用、`groups:[{id,items:[稳定ID,...]}]` 与非空实际采样 `prices:[{id,value}]`。两侧 groups/prices 必须严格相等；价格需由原生产函数与当前 source/Web/Native 实际执行采集，不是抄常量或改报告。若要改变原价，需另有明确经济设计授权，不能假称 preserve。

生产 runtime 三个 context 还须 `economy.` 前缀的 `collection_inventory`、`purchase_cost`、`insufficient_cost`、`merge`、`equip`、`effect`、`persistence`、`duplicate_claim`、`prices_preserved` 全部通过。已有临时角色时加入 `hero_trial` 并测 `trial.ad_completed`、`trial.ad_cancelled`、`trial.only_current_round`、`trial.permanent_unlock_unchanged`、`trial.effect_applied`、`trial.restart_restore`。source reward entry ID含 trial 而缺此声明会拒绝。实际 trial 按原入口和本局效果/结束还原/永久解锁记录判定，不强制新增试用弹窗或地图；真实 GUI 仍按 catalog ECON-02 的 maintenance_observations 检验。没有授权或少了这些当前生产证据，原规则继续拒绝。

## Source-maintenance review: criterion-level template applicability

`source_maintenance_review.v1` accepts a `criteria_scope` object using `maintenance_criteria_scope.v1`. This filters named template additions only; it never waives the compound MOD/ECON/FEAT/LEVEL/RANK review rows or their preserved-game criteria. The adapter still requires and replays the complete top-level check domains, including `BUSINESS`, `PAGES`, `NORMAL`, `ENGLISH`, `STORAGE-01`, `LOAD-01`, and `LOAD-03`.

The criteria matrix is derived from current, hash-checked project documents: `docs/features.json`, `docs/levels/level_plan.json`, `docs/league/decision.json`, and the validated current `maintenance_scope.v1`. All references must match the exact project paths and current review binding. Missing documents, absent scope, stale hashes/bindings, contradictions with source/UI inventory, missing criterion rows, and absent observations block by default.

Only criteria representing new template additions can be `scoped_out`, with a criterion-specific reason and references to the governing current documents. Existing daily check-in, ad entry/completion, reward claim and persistence, original match/result behavior, original collection/trial, English/UI/no-share, Native storage, loading/recovery, and current route inventory remain required. `skin_bonus=true`, fixed-level mode, or an affirmative weekly-league decision restores the corresponding requirement. If the current maintenance profile has no enforced check domain for that applicable criterion, the audit blocks until the profile gains a real executor; a matrix-only pass is insufficient. Absence cannot be inferred from an incomplete inventory. User intent to preserve the game alone cannot satisfy implementation checks.

No blanket scope can authorize the template's 70-level map, skin bonuses, gift-box module, settlement ad multiplier x2, or weekly league. These stay out unless current bound decisions explicitly request them and the appropriate real implementation checks exist. This filter does not create missing project decision records or change product/review state.
