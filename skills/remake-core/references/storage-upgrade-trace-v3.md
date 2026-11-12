### STORAGE-01 回执 v3（2026-11-11；“读不出来的旧值”部分 2026-11-12 重写）

`audit_native_storage_contract.py` 与 `check_known_issues.py` 共同核准 `native_storage_trace.v3`。v1/v2 仍能读并检查原字段，但返回 `needs_upgrade`，不能沿用成新增覆盖通过。原 23 项及 `missing_empty_string` 原负例的有效证据保留；v3 另有 4 项：`legacy_numeric_nonbinary_typed`、`legacy_numeric_boundary_typed`、`legacy_unreadable_preserved`、`legacy_upgrade_touch_play`。只补存储这个节点，不要求重跑其他已有效检查。

规则本身见[跨平台语义与旧存档](cross-platform-runtime-contract.md)：存档读不出来不能让游戏停下。这一页只讲证据怎么写。项名和 `policy_version: 3` 没有变（`legacy_unreadable_preserved` 这个名字保留，含义现在是“读不出来的旧值不挡启动”），所以新旧报告由同一批读取方读取；新核准的报告多一个 `storage_policy: "unreadable_starts_with_fallback.2026-11-12"`。

命令保持：

```bash
python3 -B scripts/audit_native_storage_contract.py --trace <trace.json> --native <最终Native目录> --binding <review.json> --out <本次报告.json>
```

trace 仍含原 `binding`、`execution`（当前 runner 文件/hash 与带 `{bundle}`、`{adapter}` 占位的 argv）、`current`、`negative_control`；v3 同时沿用 v2 `project`、`trace_base`、`route_inventory` 的当前源码/实际 UI 路由判据。`upgrade_negative_control` 使用与原 negative 相同的 bundle/adapter/raw_report 文件和 hash 字段，并由同一 runner 在首次审计核准时实际重放。`kind` 为 `historical_release` 或 `controlled_legacy_fixture`，必须有 checked_ref 的 provenance；受控反例额外按既有规则核 base_bundle 及精确单行变异。不要伪造某款游戏不存在的历史故障。

## 先声明这款游戏有没有“原样写过的旧值”

```json
"legacy_data": {"earlier_release_wrote_raw_values": false,
                "basis": "首次在 TikTok 上线；从第一个包起就装着平台存档保护件，写入都是文本"}
```

- 写了 `false` 和依据：前两项 typed 恢复（`legacy_numeric_nonbinary_typed`、`legacy_numeric_boundary_typed`）在 `cases` 里填 `not_applicable`，不用提供对应观察；`legacy_upgrade_touch_play.fixture_case` 填 `legacy_unreadable_preserved`；升级反例用下面的 `unreadable_stops_startup`。
- 不写、依据为空、或写 `true`（某个上线版本没装保护件、把数字或布尔值原样写进了存档）：前两项仍必须 pass，格式见“旧值可取回”一节。

依据要是能核对的事实（哪个版本上线过、包里有没有保护件），不是“应该没有”。

## 读不出来的旧值：带默认值启动

`upgrade_observations.legacy_unreadable_preserved` 记录一个本作实际存档键的一次运行：启动前把它种成“同步读回布尔值、异步也拿不到”，游戏照常进首页并真实点进玩法。

```json
{
  "outcome": "started_with_fallback",
  "key": "PROJECT_FIELD",
  "fixture_installed_before_entry": true,
  "storage_before": {"PROJECT_FIELD": 45, "unrelated": "keep"},
  "storage_after": {"PROJECT_FIELD": "0", "unrelated": "keep"},
  "sync_read": {"type": "boolean", "value": true},
  "async_read": {"status": "unavailable"},
  "writes": [{"key": "PROJECT_FIELD", "value": "0"}],
  "removed_keys": [],
  "first_exception": null,
  "loading_overlay_visible": false,
  "business": {"home": {...}, "play": {...}}
}
```

审计器核：fixture 在 Native 入口前种入；同步读确实是布尔值；`async_read.status` 是 `unreadable` / `error` / `timeout` / `unavailable` 之一；没有异常、加载遮罩已退出；`business` 按 `startup_business_contract.py` 的 home/play 结构，首页就绪→可信触控→玩法产生实际变化；`removed_keys` 为空，`storage_before` 里的其他键在 `storage_after` 里原样还在。这个键自己的值可以被游戏写成默认值，也可以多出备份键（SaveStore 的 `<键>:corrupt-backup`）。不能用首页截图、`passed:true` 或场景名代替 `business`。

声明了“没有原样写过的旧值”的游戏，种入的可以是任何类型的原始值（数字、布尔值都行），只要同步读回的是布尔值；声明“写过”的游戏用本作合法的旧数字（见下一节）。

这条观察可以直接取自[存档读取点两次运行](startup-storage-consumer-gate.md)里“全 true”那一次，不用另跑。

反例（`upgrade_negative_control`）：同一个键、同一个 `storage_before`，在旧包或单行改坏的包上启动被挡住。raw 里 `cases.legacy_unreadable_preserved:"fail"`，对应观察写 `failure_kind:"unreadable_stops_startup"`、同步布尔值，以及至少一项实际症状：`first_exception` 有内容、`loading_overlay_visible:true`、或 `business` 不成立。只有 case 字符串 fail 不算反例。用 2026-11-11 保护件出的旧包（一读到布尔值就抛 `Stored value unreadable`）就是现成的历史反例；没有旧包时用受控单行变异，例如把某个读存档调用改成直接抛错。

## 旧值可取回（只有声明“原样写过旧值”的游戏）

前两项分别记录本作合法的非 0/1 值（例如金币 45、音量 0.7）与合法边界 0 或 1。值与键名由本作 schema/fixture 决定，绝不全游戏硬编码 Coin 或 45。每项包含 expected_numeric 与 expected_text；兼容缺字段时暂按 45/0 及 str(value) 读取，新增运行器须显式写本作合法值：

```json
{
  "key": "PROJECT_FIELD",
  "expected_numeric": 45,
  "expected_text": "45",
  "fixture_installed_before_entry": true,
  "storage_before": {"PROJECT_FIELD":45,"unrelated":"keep"},
  "storage_after": {"PROJECT_FIELD":"45","unrelated":"keep"},
  "sync_read": {"type":"boolean","value":true},
  "async_read": {"type":"number","value":45},
  "writes": [{"key":"PROJECT_FIELD","value":"45"}],
  "removed_keys": [],
  "first_exception": null
}
```

必须在 Native 入口前种入 fixture，不允许先启动后修补观察值。`type` 与真实值类型必须相符；布尔值不能当 0/1。边界案例按实际 schema 使用 0 或 1；expected_numeric 支持 finite int/float，严禁布尔值；非 0/1 项不能填 0 或 1。expected_text 解析后须等于该数值，恢复写入与读回按该字符串逐字一致（如音量 0.7 可声明 "0.70"）；typed 异步允许等值数字或数值字符串。恢复写入只能保留原值，其他原有数据保持。

这时 `legacy_upgrade_touch_play` 含 `fixture_case:"legacy_numeric_nonbinary_typed"`，其余直接采用 business.home/play 实测结构。升级反例可以用上一节的 `unreadable_stops_startup`，也可以用数值桥反例：raw 含 `cases.legacy_numeric_nonbinary_typed:"fail"`，对应观察记录同一合法旧数字 fixture 与同步布尔值，并观察到丢键/原值被改，或 first_exception + loading_overlay_visible；`failure_kind:"legacy_numeric_bridge"`。旧空字符串负例仍独立保留并同 runner 重放。

游戏里用 `TikTokStorageGuard.recoverTyped` 取回旧值（见规则页）。它拿不到真实值时按“没有值”继续，所以同一款游戏的“读不出来”那一项照上一节写。

## 没有裸数字存档的游戏

不强制制造错误数字 schema。trace 可声明 `numeric_scope.mode:"schema_backed_non_numeric"`，但必须 checked_ref 实际 schema 和当前读写清单；已存在的 `json_only` 声明保持兼容：

```json
{
  "numeric_scope": {
    "mode":"schema_backed_non_numeric",
    "schema":{"path":"storage-schema.json","sha256":"..."},
    "access_inventory":{"path":"storage-accesses.json","sha256":"..."}
  }
}
```

schema 为 `storage_value_schema.v1`，`fields` 逐实际键声明当前及所有已支持旧版本的真实编码；例如 JSON 对象使用 `encoding:"json_object"` 与 `legacy_encodings:["json_object"]`。布尔、文本等填写各自编码，不能掩盖旧版曾写裸数字的键。access inventory 为 `storage_access_inventory.v1`，包含当前 binding、schema_sha256、complete:true、unknown_or_dynamic_keys:[] 与 keys 列表；keys 与 schema 集合完全一致，每键 read/write 各有实际 source checked_ref 及唯一可定位 expression。源码必须来自当前工程真实存储消费者。清单是受证据约束的项目声明，不是 JavaScript 全路径静态证明，发现动态键或未知旧类型就不能使用 n/a。仅写 reason、空清单、过期源码或存在未覆盖的旧类型/裸数字字段会拒绝。

获准后前两项 numeric typed cases 为 not_applicable。另外两条观察：

- `upgrade_observations.valid_legacy_record`：本作实际存档 key、Native 入口前 fixture 标记和完整 storage_before/after；能读的旧档按 schema 保留原语义，可做无损文本编码迁移（如布尔 false→"false"、JSON 对象→JSON 文本），不得被默认值覆盖。`legacy_upgrade_touch_play.fixture_case` 填 `valid_legacy_record`。
- `upgrade_observations.legacy_unreadable_preserved`：同一个键、同一份旧 fixture，按上面“带默认值启动”的格式。用 SaveStore 的游戏在这里看到的是：原文进了 `<键>:corrupt-backup`，存档从默认值开始，游戏进了玩法。反例同样是 `unreadable_stops_startup`。

## 2026-11-12 之前的证据格式（只读旧回执时用）

之前“不可恢复”一项要求：storage_before/after 完全相同、writes 为空、`recovery_feedback_visible:true`、`loading_overlay_visible:false`、`retry_or_exit_available:true`（值原样保留、给一个可见的恢复/退出页）；非数字游戏的升级反例是 `non_numeric_unreadable_preserved` / `json_unreadable_preserved`（不可读存档被重置）。这些格式审计器仍然认得：**已经签发的回执继续有效，不用重测**。新核准（`approve_runtime`）不再接受它们，会提示改成“带默认值启动”。

之所以能直接沿用：审计器对旧证据仍按原来的全部条件复判，只是新增了一种可接受的写法；回执里记的是 11.17.27 及更早已审过的审计器文本的 hash，这几个 hash 登记在 `REVIEWED_PREDECESSORS`，其余依赖、trace、runner、原始报告必须一字不差。

## 按既有证据增量核准

本契约是在原存储节点补覆盖，不扩大为整组玩法复验。runner 可复用原 23 项中仍有效的逐项原始证据，执行新增项或确实受影响项，并保留每项 `reused` / `rerun`、真实原时间及依赖身份。审计器首次核准执行同一 runner 的证据组合与反例回放；该 runner 若仍把无关功能混在不可拆整组内，应按现有范围门禁拆项，不能仅因格式升级要求重新跑全部广告和地图。consumer 只读核准回执及原始依赖，不能重造通过时间。

首次核准回执与证据失配时，沿用现有 `repair_required` 流程定位具体缺口，不降级为警告，也不自动扩大测试。

## 三个交付入口共用只读核准

`build_checked_zip.py`、`make_tiktok_zip.py`、`prepare_delivery.py` 在实际写包/交付处共同调用 `audit_final_storage.py`。它只核当前已首次实跑核准的报告及原始依赖，不启动浏览器或重跑矩阵。启动合同通过 `native_storage_report: {path, sha256}` 显式引用该报告；使用既有检查表的入口可复用 `review.STORAGE-01` 的实际 auto_reports。缺引用、报告/trace/运行器/依赖/Native 失配、失败或未核准时均拒绝，不能通过换轻量入口省略。

## 首次执行核准回执

`approve_runtime(trace, native, binding)` 先校验当前原始观察，再真实回放 current、negative_control、upgrade_negative_control；成功才生成 `execution_receipt.schema:"native_storage_execution_receipt.v1"`。回执含 run_id、verified_at、三记录 replayed 列表，以及 trace 完整内容的 canonical SHA、契约工具文件 hash、runner/command/显式 dependencies 列表与逐 raw_report 的路径/hash。self-contained runner 也须写 `execution.dependencies:[]`。这是一致性与执行身份回执，不是密码学签名；不能证明蓄意伪造的 runner 或模型等同真机。

consumer 通过 `validate_execution_receipt(report, trace)` 只读核这些身份和原始观察。修改任何绑定依赖或缺回执会拒绝，须回首次核准节点；已有效原始结果仍按现有增量账本复用，不生成虚假新运行时间。测试/制作代码不得在核准回放执行途中改变，否则本次回执失配应正确拒绝。

## 最终 Native 里的存档读取点

最终 Native 有直接读存档的代码时，审计器自己从语法树找出这些读取点，要求证据覆盖到每一个，见[存档读取点与交付约束](startup-storage-consumer-gate.md)。没有这些读取点（例如只用 SaveStore）则沿用上面的范围。不能给另一个键的旧通过换个 hash 来顶替漏测的键。

边界：此审计器校验原始观察、文件/runner 身份并重放 runner；它不能使不真实的 runner 变真实，也不能把受控 SDK 模型转换成物理 iPhone、真实广告或平台验收。随附的 schema/consumer 测试使用显式 synthetic runner，并隔离 mock 不相关 route_inventory 校验；它们证明门禁拒绝/接收行为，不证明游戏通过。
