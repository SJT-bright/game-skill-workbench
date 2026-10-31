# 加载恢复必测：无回调、失效定时器、旧请求与真实可玩

适用：所有游戏的逻辑检查、启动/分包/资源加载维护、最终检查及打包前复核。与 startup-contract.md、startup-loading-timing.md、page-readiness-and-cancel.md 合并执行；不替代原计时、页面路线、真机和广告检查。LOAD-03 必须附 `audit_loading_recovery` 当前构建报告；缺项、未测、失败不能写通过。用户限定局部范围时说明未覆盖范围，不能冒称全游戏完成。

## 为什么增加这一项

Mosslight Ferry 的真实反馈是：首页可以显示，点 SET SAIL 后停在进关加载 4/26。用户视频只记录约六秒等待，不能据此断言无限卡死或唯一的手机 SDK 根因。受控故障复现确认了可造成同形症状的两处缺陷：加载超时只靠一个 250ms interval；同时扣住该 interval 和分包回调后，每帧没有超时兜底。随后即使强制进入错误页，Retry 仍加入 `pending[bundle]` 中已被放弃的任务，底层没有第二次请求。

此前漏测原因：成功路径的 Web 加载与 ZIP 检查没有执行 Native 分包适配器；没有组合“SDK 无回调＋原超时定时器不执行”；看到 Retry 没有继续核请求身份、实际进关和输入效果。脚本断言数、HTTP 200、首页截图、ZIP 完整性均不能覆盖这些缺口。

修复原则：每帧/独立调度兜底检查前台连续无进展时间；每次实际资源请求有独立身份，失败或放弃后释放等待队列，先使旧业务代次失效，再针对失效任务发新请求；旧结果不提交当前页面/场景。正常进行中的安全共享任务和已加载成果保留，不能每次导航就全量 reset。进度只在真实字节/百分比递增时续期，后台时间排除。Native hook 必须在适配器捕获函数之前安装；仅包住后来没有被调用的全局函数没有作用。兼容 callback、Promise、两者同时及无可选进度接口，结算一次。

本案例修复后已用旧版失败、新版故障恢复、无注入正常流程对照；最终 Native 编译业务代码、双比例真实触摸、重新请求后进关滑动、热资源重开验证通过。它证明受控故障链的修复，不等于原视频手机根因已完整取证、实际 TikTok SDK/真机/平台通过。具体包、SHA、脚本及视频记录留在项目 `games/mosslight-ferry-v19-loading-fix/docs/修复说明.md`；其他机器没有该工程时按本页重建测试，不能引用该项目通过替代自己的游戏测试。

## 必测矩阵（测试开始和最终构建都执行）

| scenario | 故障/条件 | 必须观察 |
|---|---|---|
| sdk_and_watchdog_held | 扣住真正的分包/图片 SDK 回调，同时扣住原加载 interval；渲染/每帧仍运行 | 在前台无进展预算后出现 Retry（沿用连续无进展≤10秒、之后≤2秒反馈）；真实点 Retry 触发不同身份的新请求→ready→真实输入改变棋盘/计分 |
| explicit_failure | 404/503、SDK fail/reject/throw | 失败可见；真实重试发新请求并可玩 |
| slow_progress | 持续递增进度，总时长越过旧总截止 | 不中途误超时；完成后实际可玩；重复相同进度不能续命 |
| background_wait | 后台等待长于无进展预算，分别测后台完成和未完成 | 不把后台时间算无进展；回前台状态正确且可玩 |
| late_success / late_failure | 放弃第1请求，发第2请求，再放出第1请求成功/失败 | 第1结果不切旧场景、不覆盖新状态、不重复提交；第2请求可玩 |
| callback_promise | 实际加载边界分别 callback-only、Promise-only、两者同时；无 onProgressUpdate | 各终态兑现一次，不因可选接口缺失卡住；失败/拒绝有恢复 |
| warm_reentry | 已加载后暂停重开、返回再进、下一关 | 棋盘/计时重置正确，缓存成果保留；不重复下载相同依赖 |
| normal_control | 无注入冷缓存，从正常存档/首关进入 | 首页→PLAY→实际动作有效，原存档保留 |

每条真实入口（PLAY、地图选关、Next、失败 Retry、复活、后台返回、关掉重开）沿 LOAD-02/03 原路线表逐一检查。至少两种手机比例；故障组合的 Retry→第二次请求→关卡动作链在两种比例均走完。首次修复保留同判据旧版失败、新版通过、正常对照；新游戏没有旧包时可用隔离的已知坏加载器校准判据，明确“合成校准”，不得伪造旧游戏失败。

## 注入和证据边界

- 注入只在 SDK/网络/引擎外部依赖和被隔离的原定时器处；不改生产加载器、超时判断、ready 或 Retry 业务，不直接调用按钮回调。不暂停全部 JS/渲染循环来要求 JS watchdog 工作；那种全线程冻结需另查主线程阻塞。
- 盘点实际路径：game.js→适配器捕获→fsUtils.loadSubpackage→平台方法→bundle→页面。Web 资源路径通常绕过 Native SDK；必须另用最终编译 Native 模块/实际适配器边界验证。受控 SDK 的报告明确写模拟边界，不称物理手机实测。
- 同时记录请求 ID、阶段、最后进度时刻、可见 Retry、可信触摸、新请求、ready、实际输入效果和脚本错误。只出现按钮或重回首页均不够。
- 最终提取包与源码/Web/Native 指纹绑定；包后修改必须重测受影响链。旧的 `game.pack`/DevTool 中间目录不能代替带真实根 game.js 的上传包（见打包 Skill）；结构通过仍需上述运行验证。
- 未修版本、修复版本、无注入正常对照保留原始日志和截图/录屏；不能只写一串 true。Codex 必须读原始记录并核实际画面。测试空间与故障服务按拥有者接口立即收尾，用户试玩与存档保留。

## 报告与门禁

运行 `scripts/audit_loading_recovery.py --runtime <loading-recovery-runtime.json> --binding <known-issue-review.json> --out <loading-recovery-report.json>`，将报告路径及 SHA 放入 LOAD-03 的 `auto_reports`，观察项写 `combined_watchdog_failure / fresh_request_after_retry / native_boundary_and_controls`。原 `audit_startup_loading` 报告仍必需。

runtime JSON：`binding` 为本轮完整 source/native/web SHA 与 build_tag；`producer: real_browser_touch_trace`；`viewports` 为两种实际比例；`native_boundary_verified: true` 及 `native_boundary_description` 描述实际捕获顺序和受控边界；`raw_evidence` 为非空原始文件的 `{path, sha256}` 数组（相对 runtime 所在目录）；`calibration` 写 `old_failed / fixed_passed / evidence_refs`。`cases` 每个 scenario 一行，均含 `evidence_refs`（raw_evidence 的索引）、`injection_boundary`、`production_code_unchanged: true`。

每行必需的条件字段见脚本 `SCENARIOS`；它们是原始记录的索引摘要，必须对应实际记录。Retry 类场景 `events` 顺序：`request / retry_visible / retry_touch / new_request / ready / input_effect`，各含 `t_ms`；request/new_request/ready 含 `request_id`，前后请求身份必须不同，ready 归属新请求；retry_touch/input_effect 含 `trusted_touch: true`，input_effect 含具体 `effect`。组合故障另写 `idle_budget_ms / last_progress_ms`。其他场景写 `trusted_touch` 与具体 `interaction_effect`。

脚本只能查覆盖、时序、请求身份、证据哈希和版本，不能判断证据陈述是否真实。不得复制本页或自测夹具给真实游戏填通过。没有原始证据就待验；脚本自测只证明门禁拒绝已知错误，不是游戏通过。执行 `scripts/test_loading_recovery_gate.py` 验证门禁，现有 `test_known_issue_gate.py` 验证主检查表集成。


## 真实图片请求与 Cocos 内部合并队列（2026-10-23 本游戏复查追加）

只在 loadBundle 调用入口扣住回调，不能证明引擎内部的 Retry。Mosslight 完整复查时新增真实 HTTP 故障：首屏图片在服务器不返回，13/14 完成后出现 Retry；放行未来请求并真实点 Retry，旧版仍只有一个 HTTP 请求，再次超时。原因是 Cocos downloader 的同 ID 等待队列未收到原失败回调，新调用被并入旧任务。该问题独立于已修的分包等待队列。

新增必测 `image_inflight_retry`：实际进入当前编译加载器和 Cocos 下载管线，在真实网络/原生文件或图片解码边界扣住一项；记录原请求→可见失败→真实 Retry→同一资源的新底层请求→ready→实际操作。不能用引擎入口外的替身返回一个假成功包代替。Web 条件允许时用独立 HTTP 故障服务，放行未来请求但保持旧请求挂起，以服务器日志证明请求数增加；结束即收尾服务。附 `real_image_response_held / engine_inflight_released / old_transport_aborted_or_late_isolated / same_url_requested_again`，沿用 Retry 类事件时序和请求身份字段，缺此项 LOAD-03 不通过。

修法要让原始引擎 downloader/parser 回调以失败结算一次，释放其等待队列与并发名额；支持中止时中止旧传输，不支持时严格隔离迟到结果。保留 Native 适配器实际注册的文件/缓存/图片解码处理器，别直接套 Web Image 替代 Native 适配；正常已完成资源不清空。原始请求和回调均只能结算一次。用实际引擎网络回归验证，不只用简化的 loadBundle 替身。

另测“守卫先安装，启动耗时超过十秒，随后才创建请求”：新请求的无进展计时必须从它自己的创建/最近进度时间开始，不能加上守卫安装前后整段启动耗时。原始进度到达后也要更新该请求的时间基准；覆盖无帧间隔后先到进度、再到帧，避免刚收到真实进度就超时。Mosslight 的分包与图片守卫都已加入这两个负例。

本次修复记录仍在游戏实体和本游戏 docs；受控 SDK/生命周期、实际 Web HTTP、Native 编译模块、真机和平台接受继续分层，不能互相冒充。

完整复盘、故障根因与移植示例见[加载重试案例](loading-recovery-casebook.md)。真实HTTP层不能被入口替身替代，最终证据需绑定本轮产物。


## Cocos 2.4 失败中间缓存与首次 Retry（2026-10-23 Sock Drawer 复查）

本游戏在真实图片 HTTP 挂起检查中发现，释放 downloader 等待队列之后，失败场景仍可能留下已反序列化过的 `@import` 原始数据及未提交的 parsed 对象。仅显示 Retry、仅重调 loadScene、仅清错名称的 `assetManager.files`（2.4 实际为 `_files`），都不足以证明恢复；重用已变异的原始数据还可能出现 `split is not a function`。修复按实际版本定点清理失败/未提交的 import 中间数据，保留 `assetManager.assets` 中正常完成的资源与用户存档。不要把这里的内部字段名当作跨版本通用补丁。

验收必须证明**第一次、单次真实 Retry 触摸**就触发新的底层同 URL 请求，并到达 ready 与真实棋盘操作；记录触摸、请求和 ready 的实际时间，单次触摸的节点/DOM原始事件及请求序号。第二次人工补点、后来服务器放行旧请求、直接改 ready、清空存档后可玩都不能算第一次重试通过。任何手工诊断干预均应另存并使受影响用例重跑。

引入图片压缩格式时，额外检查最终 Native 引擎选择纹理格式的能力判断与真实解码边界。Canvas 是否能编码某格式不等于 Image 是否能解码；不要盲目强行置 true。需要探测时用平台公开 Image API 实际解码小样，成功后才选择格式，失败/无回调有可恢复终态，迟到结果隔离；浏览器解码和受控 SDK 检查仍不能填写真机通过。

本游戏证据见 `games/sock-drawer-showdown/audio-ready-v3.1-r8/docs/` 的 recovery、shipped-native-adapter、native-codec-delta、normal-control 与最终维护验收报告。前一构建证据只能在明确列出差异、证明所测文件逐字节相同并补测新路径后复用，保留原执行指纹；禁止把旧报告直接改指纹冒充重新执行。


## 出包前恢复矩阵补齐（2026-10-23）

矩阵从10项扩为12项，增加optional_font：font_failure_nonblocking / font_hang_nonblocking / late_font_no_page_restart；request_local_clock：clock_starts_at_request / progress_before_frame_preserved。两行沿用真实输入效果、原始证据SHA、当前构建绑定和不替换产品加载器要求。字体无外部调用时可在原始记录写实际调用计数0与普通流程真实效果，不能凭源代码猜测。时钟受控片段可作补充，真实加载链及操作仍必需。旧报告保留历史，不把新增行自动填成通过。简要清单见known-issue-checklist.md“提供测试包前”。


## 上传前机器约束升级：sock-first-retry-v2（2026-10-23）

当前 `audit_loading_recovery.py` 报告带 `policy_version: sock-first-retry-v2`、实际 `runtime_file` 与 SHA256。正式 known-issue 门禁重新读取 runtime，重新校验证据与规则；只有旧 passed、旧版本章或已变更原始文件不得放行，测试包同样执行正式 writer。

新增运行数据：顶层必须声明 `image_format_change` 布尔值；变更格式时必须有 `native_codec_verified: true` 和有效 `codec_evidence_refs`。每条 case 必须有实际 `observed_viewports`，覆盖顶层两个比例，不能只填一个双比例标题。`image_inflight_retry` 必须有整数 `retry_gesture_count: 1` 和 `manual_intervention: false`；Retry事件只能有一次，时序必须是有限数值。同一资源新底层请求必须只增加一次。原始证据路径限制在运行记录目录内，拒绝路径越界。

正式 `make_tiktok_zip.py` 扫描实际 Native 文件；包含 WebP（大小写均识别）时，没有 LOAD-03 的 Native 解码证据就拒绝写 ZIP。声明格式未变也不能绕过：凡声明已验证解码或提供解码证据引用，审计器仍校验引用有效性、原始文件及 SHA；最终还须通过完整门禁。

`execution_binding` 若存在必须与当前 binding 相同。旧版本/不同源码或 Native 的执行只能作历史辅助；当前最终验收需重跑受影响链并保留实际执行指纹，不把字段重签当复测。原有“差异证明后复用”的记录不再满足此版本最终门禁。

校准入口：`python <skills>/remake-core/scripts/test_loading_recovery_gate.py`。它的合成样本只校准拒绝逻辑，不证明游戏正常。至少两轮：第一轮检查缺项/失败/第二次Retry/人工救场/假双比例/旧指纹/编码冒充解码；第二轮反查正式门禁确实重读当前原始证据，并跑游戏旧版失败/当前正常对照。不能声称脚本能判断截图真假或阻止模型刻意绕开所有工具；这些仍需人工原始证据审阅及真实平台测试。

## 引擎下载前的不可见动画与录屏工具校准（2026-10-23）

有 CSS `animation` 不等于玩家看见动画：进度条的 span 初始宽度为0时，内部条纹持续移动仍没有任何可见像素。Sock Drawer 的2Mbps实际旧版录屏确认此区域连续约5.8秒静止。必须从引擎脚本下载前的 HTML 首屏开始录制，逐阶段检查实际可见指示区域；引擎运行后的资源准备页同样要有持续可见反馈。修复用独立于未知进度的可见忙碌指示，不能编造百分比或资源数量。最终仍执行 `audit_startup_loading.py` 的预先计划、两比例本地/首次联网/慢网及异常矩阵，不以12项恢复摘要代替计时与动态画面验证。

先校准录屏链再批量测。长时间独占页面 RPC 的 wait 调用可能饿死 screencast ACK，导致只有首尾几帧；这是工具采样无效，不能据此认定游戏真的冻住。保留失败记录，修复为有界只读轮询与持续帧ACK后重跑；真实业务效果标记须等到观察到实际变化。禁止修改时间戳、复制帧或放宽冻结阈值来让稀疏录像通过。


## 异常进度字段短检（2026-10-26）

相关补充见下文的 Native 本地图片解码与 Retry 可见性。

下载进度的显示值与存活判据分开：百分比只显示有限的0–100；负数、越界、NaN、缺字段用不定进度，不凭异常百分比直接判失败。SDK真实字节可用时以字节前进为准；异常计数变化只能作受限活动信号，不能冒称完成，重复值不续期，并保留整体截止、后台排除及SDK终态。

发生此类故障，在最终adapter→SDK→业务守卫的同一路径核四项：异常字段持续变化且最终成功时不误超时；重复/无回调仍在预算内失败；一次真实Retry产生新请求且旧回调隔离；正常0/100与有效字节对照。用准确旧包命中同一后置条件，再验候选。局部VM/SDK探针只证明逻辑；最终仍需同版真实renderer中HOME→输入→玩法变化。缺手机首错时不把本地同形故障说成手机唯一根因。

## Native 本地图片解码与 Retry 可见性（2026-10-26）

Cocos 2.4 Native 本地图片下载器可先返回文件路径，再由实际 adapter 注册的图片 parser 等待 SDK Image 解码。只保护 downloader 不能覆盖 parser 无回调。遇到这类故障，在实际 Image.src/解码边界扣住一项，保留原 parser，使原完成回调按失败结算一次，释放 Cocos parser 合并队列；Retry 须产生新图片请求，旧回调不能提交。不要假定引擎公开 `_parsers`；按当前接口读取，或在实际 adapter 注册时捕获原 handler，不换成 Web 解码替身。正常完成的资源仍复用缓存。

Retry 节点 active、可命中或点击后恢复，不能单独证明玩家看得见。Cocos 同节点多个渲染组件及加载遮罩层级可能留下透明热区：背景与文字用独立渲染节点，放在实际加载遮罩之上。等真实绘制后核截图中的按钮区域，再真实点一次，核新请求、HOME 和玩法变化。可补用实际运行坐标映射截图的底色与文字像素检查；须以已知不可见反例校准，保留原图，不能修图、只读节点或手填可见。只回归受影响的图片恢复与正常启动，不重做已批准美术。
