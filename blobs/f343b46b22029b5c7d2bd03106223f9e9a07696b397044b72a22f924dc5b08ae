# Native adapter 存储证据合同 v2

适用于已识别激励广告或已有 `qa/storage-boolean-contract.json` 的项目。`audit_ad_storage_contract.verify` 由两个 writer 和最终 delivery 共用的 `package_obligations` 调用。v1 只有形状声明及少量日志，不能沿用为全形态通过；保留旧件，实际重测后生成 v2，不手改旧日志补标签。

## 合同与原始结果

合同 schema 为 `native_ad_storage_contract.v2`，存放 `qa/storage-boolean-contract.json` 或 `docs/test/storage-boolean-contract.json`：

- `native_tree_sha256`：由 `audit_ad_storage_contract.tree_sha(native)` 计算。
- `evidence_layer`：固定 `native_adapter_simulation`；结果只证明 adapter 存储材料，不能标真机、真实广告或玩家全链通过。
- `shapes`：`null/false/true/string_0/string_1/number_0/number_1/invalid_object/invalid_string`，各出现一次。按键契约确定合法值和预期行为，不统一转换 Boolean；需要时在项目测试中增加空字符串、数组、越界、读写抛错等反例。
- `runner`：项目相对 `{path,sha256}`，Python/Node 文件。
- `harness_dependencies`：非空 `{path,sha256}` 数组，包含实际宿主、注入器及其他执行依赖。执行者审阅依赖闭包，脚本不能自动证明完整性。
- `cases`：每种 shape 对应非空业务断言数组，条目 `{path:[字段,...],op:"eq|ne|gt|ge|lt|le",value:预期值}`，作用于 raw.observed。判据由原缺陷和正常业务语义确定，不能为通过而改成实际错误结果。
- `evidence_refs`：每种 shape 对应独立原始 JSON 的 `{path,sha256}`，路径只能位于项目内。

每份原始 JSON schema 为 `native_storage_shape_case.v2`，包含对应 `shape`、`native_tree_sha256`、`runner`、`harness_dependencies`，以及：

```json
{"injection":{"api":"tt.getStorageSync","shape":"false","read_count":1},"errors":[],"observed":{"由真实执行采集的业务字段":"实际值"}}
```

注入次数必须由执行采集；JSON 标签本身不证明执行。单份文件必须是完整 JSON，不能从多段日志中挑最后一个“成功”。采集器输出与合同分开，避免覆盖合同。已有证据不原地改写，相关 Native、runner 或宿主变化需重测。

## 检查器的实际边界

检查器重算字节哈希、读取全部形态原始结果、验证身份/注入元数据并执行业务断言。结果明确为 `adapter_storage_only`。真实按钮、SDK create/show、完成/取消/错误/超时/连点/迟到回调、奖励保存/重开及原消费者需另有玩家链证据；旧故障/修复/正常对照沿用现有问题账本与执行 retest，不能由 v2 合同替代。

SDK 关键字扫描是提示，不能证明无广告。已有合同在 SDK 包装函数更名后仍检查；新游戏无关键字且无合同仍需人工核对入口清单。不得把该返回的 `required:false` 解释为已经证明无广告。

runner、依赖及断言的正确性仍须代码审阅；哈希不鉴别日志作者，也不证明运行器真的执行。真实 TikTok 广告可用性、平台账号/广告位配置、原手机旧档与真机回调仍须对应环境证据。缺少这些证据时只报告已完成的层级。

门禁回归执行 `python3 -m unittest test_ad_storage_contract -v`（工作目录为共享 scripts）。该测试使用隔离合成 fixture，只证明门禁拒绝指定反例，不能作为游戏通过证据。
