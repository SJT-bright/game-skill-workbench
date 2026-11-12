### STORAGE-01 冷升级覆盖回执 v3（2026-11-11）

`audit_native_storage_contract.py` 与 `check_known_issues.py` 共同核准 `native_storage_trace.v3`。v1/v2 仍能读并检查原字段，但返回 `needs_upgrade`，不能沿用成新增跨环境/旧存档覆盖通过。原23项及 `missing_empty_string` 原负例保留；v3新增4项：`legacy_numeric_nonbinary_typed`、`legacy_numeric_boundary_typed`、`legacy_unreadable_preserved`、`legacy_upgrade_touch_play`。只补该存储节点，不要求重跑其他已有效检查。

命令保持：

```bash
python3 -B scripts/audit_native_storage_contract.py --trace <trace.json> --native <最终Native目录> --binding <review.json> --out <本次报告.json>
```

trace仍含原 `binding`、`execution`（当前runner文件/hash与带 `{bundle}`、`{adapter}` 占位的argv）、`current`、`negative_control`；v3同时沿用v2 `project`、`trace_base`、`route_inventory` 的当前源码/实际UI路由判据。新增 `upgrade_negative_control` 使用与原negative相同的bundle/adapter/raw_report文件和hash字段，并由同一runner实际重放。`kind` 为 `historical_release` 或 `controlled_legacy_fixture`，必须有checked_ref的provenance；受控反例额外按既有规则核base_bundle及精确单行变异。不要伪造某款游戏不存在的历史故障；共享保护逻辑可以用可审查的受控误处理变异校准。

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

**无裸数字键的JSON-only存档不强制制造错误数字schema。** trace可声明 `numeric_scope.mode:"json_only"`，但必须checked_ref实际schema和当前读写清单：

```json
{
  "numeric_scope": {
    "mode":"json_only",
    "schema":{"path":"storage-schema.json","sha256":"..."},
    "access_inventory":{"path":"storage-accesses.json","sha256":"..."}
  }
}
```

schema为 `storage_value_schema.v1`，`fields`逐实际键声明 `encoding:"json_object"` 与 `legacy_encodings:["json_object"]`；不能掩盖旧版曾写裸数字的键。access inventory为 `storage_access_inventory.v1`，包含当前binding、schema_sha256、complete:true、unknown_or_dynamic_keys:[]与keys列表；keys与schema集合完全一致，每键read/write各有实际source checked_ref及唯一可定位expression。源码必须在当前project/assets中。清单须基于实际存储实现与旧版schema盘点；它是受证据约束的人工/项目声明，不是JavaScript全路径静态证明，发现动态键或未知旧类型就不能使用n/a。仅写reason、空清单、过期源码或存在primitive legacy字段会拒绝。

获准JSON-only后，前三numeric cases为not_applicable，旧23项仍执行；`upgrade_observations.valid_legacy_record`记录真实JSON字符串存档的key、Native入口前fixture标记和完整storage_before/after不变，`legacy_upgrade_touch_play.fixture_case`改为valid_legacy_record。升级negative使用 `cases.json_unreadable_preserved:"fail"` 及同名upgrade_observations，记录已存在的JSON字符串→同步Boolean→原始JSON被静默覆盖，`failure_kind:"existing_json_silently_reset"`。这校准误类型保护，不宣称本游戏历史上确实发生过45金币故障。

边界：此审计器校验原始观察、文件/runner身份并重放runner；它不能使不真实的runner变真实，也不能把受控SDK模型转换成物理iPhone、真实广告或平台验收。新的schema/typed恢复路径仍应由实际Native运行器覆盖，真机结果另列。随补丁的19项schema/consumer测试使用显式synthetic runner，并隔离mock不相关route_inventory校验；它们证明门禁拒绝/接收行为，不证明游戏通过。
