# 旧存档消费者与最终交付约束（2026-11-12）

适用于实际 Native 存在直接原始存档读取的游戏。R7 的旧声音键在主包脚本初始化时抛异常；正常新玩家与广告通过没有覆盖旧类型启动。通用要求不按键名、游戏名或“iOS”标签判断，而按实际消费者、schema、SDK语义和可观察结果判断。

## 制作端先处理恢复顺序

1. 盘点引擎首帧前、首页与 PLAY 依赖的实际存档读写；声明本作合法类型、边界与关键性。布尔开关、数值余额、字符串、JSON分别处理，不能把Boolean猜成0/1。模块顶层读取也属于消费者，不能只查场景start。
2. 需要恢复的旧值必须在对应消费者执行前完成有界typed异步确认；安装storage-guard不是恢复完成。现有`storage-guard.recoverTyped`接受显式schema，恢复后读回确认，再放行相关模块/迁移。不要把关键值猜成默认值；正常读取/显示不强制写回。
3. 非关键设置恢复失败时保留原值，隔离相关读写，在原入口提示/重试，让不依赖它的首页与玩法继续。关键余额/权益无法恢复时禁止不安全发奖、消费和覆盖，并提供实际可见、可点的恢复/退出。隔离与保档不等于游戏可玩，分别记录结果。
4. 不以调用showModal就认定Retry可见。对本作恢复机制验证系统弹窗fail、Promise拒绝与无回调；恢复画面必须实际可见并接受可信输入，Retry产生新请求。引擎未就绪时不得先在将用于WebGL的主画布取2D上下文；能力不足时保留失败边界。

## 检查端独立发现消费者

现有STORAGE-01 v3审计在核原始报告时调用`startup_storage_consumers.coverage_errors`，从当前Native业务JS的语法树重新发现直接`localStorage.getItem`、平台`getStorageSync`调用。覆盖cc.sys/globalThis/window、别名、括号属性、常量拼接和Cocos `require('cc')`/ESM sys导入；识别模块工厂顶层初始化。注释、字符串和被参数/局部对象遮蔽的同名对象不作为宿主读。

只跳过引擎目录；平台适配器仅排除语法可确认的原样getItem参数→getStorageSync委托，不按adapter/storage文件名整份豁免，合并业务包照查。动态键域保留为未解析并拒绝当前直接消费者证明；需把真实有限域展开到已审源码/配置并完善解析能力，不能删掉键或填“complete”。任意包装器、反射与SystemJS setter等未解析路径仍须沿用本作访问清单与审阅；此扫描不是全程序正确性证明。

只读盘点命令（不启动浏览器，不颁发运行通过）：

```sh
python3 -B <skills>/remake-core/scripts/startup_storage_consumers.py \
  --native <当前实际Native> --out <工程QA/legacy-consumers.json>
```

trace在原`native_storage_trace.v3`上增加`legacy_consumers.fields`；每项是实际key、type（boolean/integer/number/string/json_object）、critical、sites（上面扫描的site_id）和本作`valid_fixtures`。Boolean必须覆盖true/false，数字按本作schema覆盖合法非二值与0/1边界，不全游戏硬编码45。每个实际读取点必须对应，另一键的通过不能代替。

当前runner的原始报告增加`legacy_consumer_observations`：

- 每个合法fixture恰好一条`case:typed_upgrade`，带key/fixture、`fixture_installed_before_entry:true`、实际`read_sites`、同步Boolean/歧义返回的`sync_read.type/value`、`storage_before/storage_after/cold_storage_after`、`async_read.value`、`removed_keys:[]`、`errors:[]`。原值与无关已有值在迁移及冷重开后保留；保值结论字段不能替代原始数据。
- 每键另附一条`case:metadata_unavailable`，使用该键首个合法fixture，记录SDK键信息不可用`metadata_status:unavailable`，仍有完整typed异步恢复、冷重开和开局观察。宿主默认补齐API不能充当此项命中。
- 每键一条`case:unrecoverable`，保留原值、零写入/零删除，记录实际异步error/timeout/unavailable/unreadable、有界退出遮罩及可见恢复。非关键字段附隔离后真实可玩及`isolated_consumer_writes:[]`；关键字段附零不安全发奖/消费、可信恢复输入及新请求。
- 正常typed恢复和非关键隔离结果均带既有`business`原始观察，走`startup_business_contract.validate_business`，核首页→真实触控→玩法变化；只记录home_ready不算开局。
- `recovery_failure_observations`分别记录modal_fail、modal_reject、modal_no_callback：真实注入命中、恢复界面可见、遮罩退出、无未处理异常、可信恢复输入，以及`action.attempt_after > action.attempt_before`。不得只报告SDK方法“调用成功”。

共享2.x `ad_regression/host.js`与3.x `runtime_regression/host3x/host.js`提供显式故障参数，均在游戏入口前生效，默认行为不变：

| 参数 | 实际模型 |
| --- | --- |
| `storage_seed=<URL编码JSON对象>` | 入口前安装本作合法类型fixture |
| `syncnumbool=all&async_storage=typed` | 同步数字返回Boolean，异步保留原始类型；不是Boolean转数字 |
| `storage_info=missing` / `throw` | 真正删去键信息方法，或调用时抛错 |
| `async_storage=error` / `hang` / `unavailable` | 异步fail、无回调、真正缺方法；`storage_fault_key=<key>`可将error/hang限定到该键 |
| `modal_fault=fail` / `reject` / `silent` | showModal回调失败、Promise拒绝、既无界面也无回调 |

读取宿主fault命中日志，并记录本作实际恢复、输入与新请求。query参数或宿主单元测试不能代替这些业务观察；它们也不等于真机SDK验收。不要用`reset=1`冷开代替保留旧fixture后的冷重开。原`numbool`诊断和missing默认行为保留，旧结果按原语义解释。

这些记录仍由原runner首次实际重放，源/Native/runner与规则指纹绑定；正式writer与交付只读核对。无直接原始消费者的项目保持原v3范围；有新消费者或缺项时只补对应storage/启动节点，旧有效分支按真实依赖沿用，不重跑关卡/美术。

外来材料先按[接收他人包模式](external-package-handoff.md)登记、诊断和试玩；缺原回执不阻断接收，也不能解释成对方从未正式出包。下面的正式交付约束用于当前制作或修改后出包，不能反过来要求收件人先补齐对方所有历史材料。

## 最终文件与可交付结论不能混用

`upload_size_gate.inspect_zip`仍是文件诊断；TikTok最终命令`inspect_final_zip`在体积/CRC/宿主前提/CLI后，还核同字节正式writer回执。缺失、伪造passed字段、改包后旧回执均拒绝；改名但同字节可在同目录按SHA找原正式回执。各项技术结果保留，失败不会被改成“包体超限”。

其`passed`仅表示最终文件前提齐全，`delivery_ready`固定false；真正交付仍走`prepare_delivery.py`复核当前启动、存储、已报问题及同版试玩，成功才生成`delivery_ready:true`交付记录，拒绝记录明确为false。不能把体积/CLI回执、广告矩阵或普通网页可玩改称完整验收。

“没有旧记录／不用旧记录／直接出包”不自动授权跳过本次启动检查：材料缺口由Agent恢复或补当前受影响证据；项目预处理脚本只能准备Native，最终回到正式writer及prepare_delivery。不能筛掉门禁错误、手工zip后贴通过报告，也不能为此伪造旧记录。明确要求仅诊断或未验候选时按实际边界交接，不宣称正常测试包或已修复；用户明确改变范围时保留原话与未完成项。

工具能约束受支持入口，不能禁止任意外部程序或不遵守规则的手工操作。保证范围是：上述缺证不能再在受支持流程中得到交付通过；本地模型也不保证所有真实SDK/设备故障均已覆盖。
