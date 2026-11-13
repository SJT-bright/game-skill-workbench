# 存档读取点与最终交付约束（2026-11-12；同日按“读不出来不挡启动”重写）

适用于最终 Native 里有直接读存档代码（`cc.sys.localStorage.getItem`、`getStorageSync`）的游戏，绝大多数英化游戏都是。起因：一款游戏在主包脚本初始化时读旧的声音开关，2026-11-11 的存档保护件遇到布尔值就抛错，手机上首页没出来；之前的新玩家测试和广告测试都没碰到这条路。

规则见[跨平台语义与旧存档](cross-platform-runtime-contract.md)的第一节：存档读不出来，按没有这个值继续，不挡启动。保护件已经保证读存档这一步不抛错；这一页管的是**游戏自己的代码拿到“没有值”以后会不会出错**，以及交付时怎么证明。

## 制作时

1. 首次接入存档就用实际读取点核对字段类型、缺省值和消费者：包括模块顶层、Config/单例、首页、PLAY 与首个操作，不只核用户报错的第一个键。首份 Native 用下方已有只读盘点命令校对；以后只核新增/变化的读取点，不另建重复清单。
2. 每处读取拿到 `null` 都要能继续：先判空再 `JSON.parse`、`split`、取属性；getter 和显示默认值不写存档。新玩家能玩是基础，不能代替已有键读不出来的对照。
3. 不写“读不懂就抛错、进恢复页、锁功能”的存档保护，不为金币等余额单独做“保档并阻止继续”。
4. 只有“以前上线过、旧版本原样写过数字或布尔值”的游戏，才在读存档之前调用 `TikTokStorageGuard.recoverTyped` 取回旧值；首次上线的游戏不用做。
5. 加载失败（分包、资源）仍然要有实际能点的 Retry，这和存档无关，见规则页“启动链上其余要守的”。

## 检查时：审计器自己找读取点

STORAGE-01 审计在核原始报告时调用 `startup_storage_consumers.coverage_errors`，从当前 Native 业务 JS 的语法树重新找出直接的 `localStorage.getItem`、平台 `getStorageSync` 调用。覆盖 cc.sys/globalThis/window、别名、括号属性、常量拼接和 Cocos `require('cc')`/ESM sys 导入；识别模块工厂顶层初始化。注释、字符串和被参数/局部对象遮蔽的同名对象不算。只跳过引擎目录；平台适配器仅排除语法可确认的原样 getItem 参数→getStorageSync 委托，不按文件名整份豁免。任意包装器、反射等解析不到的路径不在这次扫描里；它不是全程序正确性证明。

只读盘点命令（不启动浏览器，不颁发运行通过）：

```sh
python3 -B <skills>/remake-core/scripts/startup_storage_consumers.py \
  --native <当前实际Native> --out <工程QA/legacy-consumers.json>
```

找到读取点后，证据有两种写法，按游戏情况选一种。

### 写法一：整款游戏两次运行（首次上线，或每个上线版本都装着保护件）

trace 里：

```json
"legacy_data": {"earlier_release_wrote_raw_values": false, "basis": "首次在 TikTok 上线"},
"legacy_consumers": {"mode": "unreadable_start"}
```

runner 的原始报告 `legacy_consumer_observations` 里放两条 `case:"unreadable_start"`，`profile` 分别是 `all_true` 和 `all_false`：

```json
{
  "case": "unreadable_start", "profile": "all_true",
  "fixture_installed_before_entry": true,
  "seeded_keys": ["Coin", "IS_MUSIC"],
  "storage_before": {"Coin": 45, "IS_MUSIC": 45},
  "sync_reads": {"Coin": {"type": "boolean", "value": true}, "IS_MUSIC": {"type": "boolean", "value": true}},
  "read_sites": ["<盘点得到的 site_id>", "..."],
  "async_storage": "unavailable",
  "metadata_status": "unavailable",
  "errors": [], "removed_keys": [], "loading_overlay_visible": false,
  "business": {"home": {...}, "play": {...}}
}
```

审计器核：

- 盘点出的每个字面键都在 `seeded_keys` 里并且启动前已种入（漏一个键会点名）。键名是运行时拼出来的读取点（如 `'level_' + n`）不用逐个列，这次运行本身覆盖它们。
- `read_sites` 是盘点里真实存在的读取点；其中每个字面键在 `sync_reads` 里读回的是这次 profile 的布尔值（全 true 那次是 `true`，全 false 那次是 `false`）。
- `async_storage` 是 `unavailable` / `error` / `timeout` / `unreadable` 之一，也就是没有任何办法拿回原值。
- 没有异常、没有键被删、加载遮罩已退出；`business` 证明首页→可信触控→玩法有实际变化。
- 两次里至少一次 `metadata_status:"unavailable"`（拿不到平台键列表）。

宿主参数照规则页的例子：全 true 把每个键种成非 0 数字，全 false 种成 0，配 `syncnumbool=all&async_storage=unavailable`，其中一次再加 `storage_info=missing`。两次运行就是这一项的全部工作量，不按键数增加。

### 写法二：逐键证明旧值能取回（上线过且原样写过数字或布尔值）

trace 的 `legacy_consumers.fields` 每项是实际 key、type（boolean/integer/number/string/json_object）、critical、sites（盘点的 site_id）和本作 `valid_fixtures`。布尔必须覆盖 true/false，数字按本作 schema 覆盖合法非二值与 0/1 边界，不全游戏硬编码 45。每个实际读取点必须对应；键名运行时拼出来的读取点要先把真实有限范围展开到已审源码/配置，否则这种写法不通过。

原始报告 `legacy_consumer_observations`：

- 每个合法 fixture 恰好一条 `case:typed_upgrade`：key/fixture、`fixture_installed_before_entry:true`、实际 `read_sites`、同步布尔的 `sync_read.type/value`、`storage_before/storage_after/cold_storage_after`、`async_read.value`、`removed_keys:[]`、`errors:[]`、`business`。原值与无关已有值在迁移及冷重开后保留。
- 每键另附一条 `case:metadata_unavailable`，用该键首个合法 fixture，`metadata_status:unavailable`，仍有完整 typed 异步恢复、冷重开和开局观察。
- 每键一条 `case:unrecoverable`，写成“带默认值启动”：`outcome:"started_with_fallback"`、fixture 入口前种入、`storage_before/storage_after`、同步布尔 `sync_read`、`async_read.status` 为 error/timeout/unavailable/unreadable、`first_exception:null`、`loading_overlay_visible:false`、`removed_keys:[]`、其他键不变、`business` 证明进了玩法。

## 2026-11-12 之前的写法（只读旧回执时用）

之前每键的 `unrecoverable` 要求原值不动、零写入、可见恢复页（关键字段还要可信点击恢复），外加 `recovery_failure_observations` 三条（modal_fail、modal_reject、modal_no_callback）证明恢复页在系统弹窗失效时也能点。审计器仍认得这种证据，**已经签发的回执继续有效**；新核准不再接受，会提示改成上面的写法。写法二里只要还有一条旧式 `unrecoverable`，三条 modal 观察就仍然要齐。

这些记录仍由原 runner 首次实际重放，源/Native/runner 与规则指纹绑定；正式 writer 与交付只读核对。没有直接读取点的项目保持原 v3 范围；有新读取点或缺项时只补存储/启动节点，旧有效分支按真实依赖沿用，不重跑关卡/美术。

外来材料先按[接收他人包模式](external-package-handoff.md)登记、诊断和试玩；缺原回执不阻断接收，也不能解释成对方从未正式出包。下面的正式交付约束用于当前制作或修改后出包，不能反过来要求收件人先补齐对方所有历史材料。

## 最终文件与可交付结论不能混用

`upload_size_gate.inspect_zip` 仍是文件诊断；TikTok 最终命令 `inspect_final_zip` 在体积/CRC/宿主前提/CLI 后，还核同字节正式 writer 回执。缺失、伪造 passed 字段、改包后旧回执均拒绝；改名但同字节可在同目录按 SHA 找原正式回执。各项技术结果保留，失败不会被改成“包体超限”。

其 `passed` 仅表示最终文件前提齐全，`delivery_ready` 固定 false；真正交付仍走 `prepare_delivery.py` 复核当前启动、存储、已报问题及同版试玩，成功才生成 `delivery_ready:true` 交付记录，拒绝记录明确为 false。不能把体积/CLI 回执、广告矩阵或普通网页可玩改称完整验收。

“没有旧记录／不用旧记录／直接出包”不自动授权跳过本次启动检查：材料缺口由 Agent 恢复或补当前受影响证据；项目预处理脚本只能准备 Native，最终回到正式 writer 及 prepare_delivery。不能筛掉门禁错误、手工 zip 后贴通过报告，也不能为此伪造旧记录。明确要求仅诊断或未验候选时按实际边界交接，不宣称正常测试包或已修复；用户明确改变范围时保留原话与未完成项。

工具能约束受支持入口，不能禁止任意外部程序或不遵守规则的手工操作。保证范围是：上述缺证不能再在受支持流程中得到交付通过；本地模型也不保证所有真实 SDK/设备故障均已覆盖。
