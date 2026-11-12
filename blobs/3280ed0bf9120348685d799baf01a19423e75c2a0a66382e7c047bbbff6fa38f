### STORAGE-01 冷升级覆盖回执 v3（2026-11-11）

`audit_native_storage_contract.py` 与 `check_known_issues.py` 共同核准 `native_storage_trace.v3`。v1/v2 仍能读并检查原字段，但返回 `needs_upgrade`，不能沿用成新增跨环境/旧存档覆盖通过。原23项及 `missing_empty_string` 原负例的有效证据保留；v3新增4项：`legacy_numeric_nonbinary_typed`、`legacy_numeric_boundary_typed`、`legacy_unreadable_preserved`、`legacy_upgrade_touch_play`。只补该存储节点，不要求重跑其他已有效检查。

命令保持：

```bash
python3 -B scripts/audit_native_storage_contract.py --trace <trace.json> --native <最终Native目录> --binding <review.json> --out <本次报告.json>
```

trace仍含原 `binding`、`execution`（当前runner文件/hash与带 `{bundle}`、`{adapter}` 占位的argv）、`current`、`negative_control`；v3同时沿用v2 `project`、`trace_base`、`route_inventory` 的当前源码/实际UI路由判据。新增 `upgrade_negative_control` 使用与原negative相同的bundle/adapter/raw_report文件和hash字段，并由同一runner在首次审计核准时实际重放。consumer复核首次核准回执、trace及当前依赖；不在每次写包读取时重复执行长矩阵。`kind` 为 `historical_release` 或 `controlled_legacy_fixture`，必须有checked_ref的provenance；受控反例额外按既有规则核base_bundle及精确单行变异。不要伪造某款游戏不存在的历史故障；共享保护逻辑可以用可审查的受控误处理变异校准。

current原始结果除 `cases` 外新增 `upgrade_observations`。有旧裸数字字段的游戏，前三项分别记录本作合法的非0/1值（例如金币45、音量0.7）、合法边界0或1与不可读旧值。值与键名由本作schema/fixture决定，绝不全游戏硬编码Coin或45。每项包含expected_numeric与expected_text；兼容缺字段时暂按45/0及str(value)读取，新增运行器须显式写本作合法值。每项包含：

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

必须在Native入口前种入fixture，不允许先启动后修补观察值。`type` 与真实值类型必须相符；Boolean不能当0/1。边界案例按实际schema使用0或1；expected_numeric支持finite int/float，严禁Boolean；非0/1项不能填0或1。expected_text解析后须等于该数值，恢复写入与读回按该字符串逐字一致（如音量0.7可声明"0.70"）；typed异步允许等值数字或数值字符串。恢复写入只能保留原值，其他原有数据保持。不可恢复项保持原始storage_before/after、writes为空，async_read.status为unreadable/error/timeout/unavailable，并记录 `recovery_feedback_visible:true`、`loading_overlay_visible:false`、`retry_or_exit_available:true`；不允许猜默认、清存档或一直罩Loading。

`legacy_upgrade_touch_play` 含 `fixture_case:"legacy_numeric_nonbinary_typed"`，其余直接采用 `startup_business_contract.py` 的business.home/play实测结构：同一次旧存档启动后，首页就绪、遮罩消失、可信触控进入玩法且产生实际变化。不能用首页截图、`passed:true`或场景名代替业务结果。

numeric升级负例raw必须含 `cases.legacy_numeric_nonbinary_typed:"fail"`，对应upgrade_observations记录同一本作合法旧数字fixture与同步Boolean，并观察到丢键/原值被改，或者first_exception+loading_overlay_visible；`failure_kind:"legacy_numeric_bridge"`。只有case字符串fail不算反例。旧空字符串负例仍独立保留并同runner重放。

**没有裸数字存档的游戏不强制制造错误数字schema。** trace可声明 `numeric_scope.mode:"schema_backed_non_numeric"`，但必须checked_ref实际schema和当前读写清单；已存在的 `json_only` 声明保持兼容。下列JSON-only例子展示最小结构，原生Boolean、文本等同样按各自真实编码举证：

```json
{
  "numeric_scope": {
    "mode":"schema_backed_non_numeric",
    "schema":{"path":"storage-schema.json","sha256":"..."},
    "access_inventory":{"path":"storage-accesses.json","sha256":"..."}
  }
}
```

schema为 `storage_value_schema.v1`，`fields`逐实际键声明当前及所有已支持旧版本的真实编码；例如JSON对象使用 `encoding:"json_object"` 与 `legacy_encodings:["json_object"]`。Boolean、文本等填写各自编码，不能掩盖旧版曾写裸数字的键。access inventory为 `storage_access_inventory.v1`，包含当前binding、schema_sha256、complete:true、unknown_or_dynamic_keys:[]与keys列表；keys与schema集合完全一致，每键read/write各有实际source checked_ref及唯一可定位expression。源码必须来自当前工程真实存储消费者，并按审计器接受的工程源码边界提供完整hash与定位表达式。清单须基于实际存储实现与旧版schema盘点；它是受证据约束的人工/项目声明，不是JavaScript全路径静态证明，发现动态键或未知旧类型就不能使用n/a。仅写reason、空清单、过期源码或存在未覆盖的旧类型/裸数字字段会拒绝。

获准无裸数字范围后，仅前两项numeric typed cases为not_applicable；`legacy_unreadable_preserved`仍须pass，核相同实际键/旧fixture的before、after、空writes/removed_keys、同步Boolean失真、异步不可用状态、简短可见反馈、loading消失与可用Retry/退出。旧23项仍须有有效覆盖，可由runner按现有增量账本复用，不因增加本节点重新跑未变广告或地图；`upgrade_observations.valid_legacy_record`记录本作实际存档key、Native入口前fixture标记和完整storage_before/after；依据schema保留原语义，可进行无损文本编码迁移（如Boolean false→"false"、JSON对象→JSON文本），不得默认覆盖，`legacy_upgrade_touch_play.fixture_case`改为valid_legacy_record。升级negative使用 `cases.non_numeric_unreadable_preserved:"fail"` 及同名upgrade_observations，核与当前相同键和旧fixture的不可读数据被错误重置。旧 `json_unreadable_preserved` 格式保持兼容。JSON示例可记录已有JSON字符串→同步Boolean→原JSON被默认覆盖；Boolean、文本则记录本作同一实际类型。此项校准误类型保护，不宣称本游戏历史上确实发生过45金币故障。

边界：此审计器校验原始观察、文件/runner身份并重放runner；它不能使不真实的runner变真实，也不能把受控SDK模型转换成物理iPhone、真实广告或平台验收。新的schema/typed恢复路径仍应由实际Native运行器覆盖，真机结果另列。随补丁的19项schema/consumer测试使用显式synthetic runner，并隔离mock不相关route_inventory校验；它们证明门禁拒绝/接收行为，不证明游戏通过。

## 按既有证据增量核准

本契约是在原存储节点补冷升级覆盖，不扩大为整组玩法复验。runner可复用原23项中仍有效的逐项原始证据，执行新增4项或确实受影响项，并保留每项 `reused` / `rerun`、真实原时间及依赖身份。审计器首次核准执行同一runner的证据组合与反例回放；该runner若仍把无关功能混在不可拆整组内，应按现有范围门禁拆项，不能仅因v3格式升级要求重新跑全部广告和地图。consumer只读核准回执及原始依赖，不能重造通过时间。

首次核准回执与证据失配时，沿用现有 `repair_required` 流程定位具体缺口，不降级为警告，也不自动扩大测试。

## 三个交付入口共用只读核准

`build_checked_zip.py`、`make_tiktok_zip.py`、`prepare_delivery.py` 在实际写包/交付处共同调用 `audit_final_storage.py`。它只核当前已首次实跑核准的报告及原始依赖，不启动浏览器或重跑矩阵。启动合同通过 `native_storage_report: {path, sha256}` 显式引用该报告；使用既有检查表的入口可复用 `review.STORAGE-01` 的实际 auto_reports。缺引用、报告/trace/运行器/依赖/Native失配、失败或未核准时均拒绝，不能通过换轻量入口省略。

## 首次执行核准回执

`approve_runtime(trace, native, binding)` 先校验当前原始观察，再真实回放current、negative_control、upgrade_negative_control；成功才生成 `execution_receipt.schema:"native_storage_execution_receipt.v1"`。回执含run_id、verified_at、三记录replayed列表，以及trace完整内容的canonical SHA、三个契约工具文件hash、runner/command/显式dependencies列表与逐raw_report的路径/hash。self-contained runner也须写 `execution.dependencies:[]`。这是一致性与执行身份回执，不是密码学签名；不能证明蓄意伪造的runner或模型等同真机。

consumer通过 `validate_execution_receipt(report, trace)` 只读核这些身份和原始观察。修改任何绑定依赖或缺回执会拒绝，须回首次核准节点；已有效原始结果仍按现有增量账本复用，不生成虚假新运行时间。测试/制作代码不得在核准回放执行途中改变，否则本次回执失配应正确拒绝。
