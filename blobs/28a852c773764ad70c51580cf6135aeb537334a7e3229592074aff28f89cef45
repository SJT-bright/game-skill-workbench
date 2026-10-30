# 资源清单完整性与已报告问题门禁

修订：`2026-10-26.package-gate-v2`。轻量writer、完整writer和最终交付入口共用`remake-core/scripts/package_obligations.py`。两条限制均在代码执行，不以文档里的“应当检查”代替；不增加全游戏CI或已批准美术复检。

## 资源清单从实际生产代码反查

执行共享`audit_runtime_resources.py`生成清单：

```sh
python <skills>/remake-core/scripts/audit_runtime_resources.py \
  --native <实际Native目录> --out <工程QA目录/resources-vN.json>
```

检查器使用随Skill提供的Acorn解析当前业务JS；特殊模块适配也必须经过原始业务源码的独立调用点核对，不能靠遮去整个模块漏掉未知调用。有限字面量、对象/数组映射、字符串拼接、模板、JSON数据域、bundle回调别名、循环和`loadDir`等受支持形式，从当前代码展开为`bundle/path/type`请求，再与实际bundle catalog及清单逐项核对。注释和字符串中的伪调用不计入。

- 清单中每行都合法但漏了一条实际请求，仍拒绝；新调用或映射值变化会重新派生请求，不继承旧的覆盖结论。
- 无法确定的真实资源动态输入、未知加载协议或逃逸的加载方法明确拒绝，并列出源码位置。同名`.load()`先核接收者：只有可证明的本地方法体或已知平台广告对象才与Cocos加载区分；本地方法体仍独立清点，改写/逃逸后不能沿用此结论。为实际有限数据域补解析适配/生产配置，不能写通配忽略、假列表或`passed:true`放行。
- v7.7：包里的 `main.js` 字节等于 `KIT_MANIFEST.json` 里平台包 `main.js` 的当前哈希或 `previous_sha256` 时，它的 `loadScript(settings.jsList)` 不算动态调用，生成的清单多一个 `script_files` 数组：jsList 里的每个脚本，加上 `main.js` require 的 `webp-decode-probe.js`，各带 sha256。写包入口核对这些文件都在、非空、字节没变，少列、多列、字节变了都拒绝；不是平台包 `main.js` 的包带 `script_files` 也拒绝。其他 `main.js` 照旧算动态调用。
- 这是静态有限域验证，不通过“把所有关卡玩一遍”收集路径。现有Cocos引擎内部、场景/原生加载和真实解码仍由所属启动/资源合同覆盖；不把静态清单称为任意JS全程序证明。
- 缓存只复用当前进程内、当前代码/数据域/解析器指纹相同的发现结果；每次仍核实际清单与catalog，不缓存跨版本通过章。 SystemJS通用分支按真实`cc`导入setter识别别名，不要求游戏具有Art模块或固定关数；项目专用展开必须额外匹配完整程序与其语义数据指纹。配置驱动的有限ID从当前绑定JsonAsset推导，不能只保留上次ID列表。文件存在/非空/路径及当前指纹检查在缓存外执行。

两个writer都传`--resource-manifest`；最终`prepare_delivery.py`同样必传。只运行只读`check_package.py`仍只是文件诊断，不能替代上述三处交付门禁。


### 已审资源配置的更新入口

更新已审有限域配置时，使用共享写入器，传完整配置和当前Native：

```bash
python3 <remake-core>/scripts/publish_resource_profile.py --profile <完整profile.json> --native <当前Native> --name <原配置ID>
```

它只替换目标条目，内嵌配置，保留已有约束并绑定当前语义JsonAsset；源码不符、需求不闭合、数据域变化或并发改写时拒绝写入。重复执行不制造新版本。生成器直接调用此入口，不在其后手写`profile_ref`或用旧快照覆盖整个登记文件。新增/变化有限域仍须按原要求审查；静态发布不代表游戏运行验收。

## 收到已报告问题先登记，不等打包时补记

项目问题记录固定在`<project>/docs/test/package-issues.jsonl`，配套`package-issues.head.json`保存事件链锚点。writer不提供另选空问题表或跳过问题历史的参数。

旧工程首次接入，先读取本作既有反馈/缺陷记录并登记未闭合问题；新项目无已报告问题时只初始化一次。缺历史不自动当作“没有问题”，已有任一历史文件不能重新初始化覆盖。

```sh
python <skills>/remake-core/scripts/package_issue_gate.py init --project <工程>
```

收到新的确定故障反馈，在修复之前保存原始描述、受影响生产文件、具体复验case及后置条件，然后登记。`targets`须覆盖该问题的实际生产依赖，不得只填入口而漏掉影响结果的数据表、桥接器或导入模块。然后执行：

```sh
python <skills>/remake-core/scripts/package_issue_gate.py report \
  --project <工程> --native <故障Native> --id <稳定问题ID> \
  --message '<反馈原话或准确描述>' --targets <实际业务.js> <相关数据.json> \
  --cases <case合同.json> --runner <已审阅的项目定点运行器.py或.cjs>
```

case合同示例（只是格式，实际字段和预期必须来自本游戏）：

```json
[{"id":"reward_once","assertions":[{"path":["reward_delta"],"op":"eq","value":1}]}]
```

运行器须实际执行当前Native的生产逻辑/加载/输入链并输出`{"observed":{...}}`，不能只输出预期数字或恒定pass。登记时固定运行器哈希，调用使用固定的解释器与`--native/--case`参数，不执行报告里提供的任意shell命令。新增运行器须先审阅实际调用目标；观察边界继续如实记录。

## 定点复验通过才形成关闭事件

```sh
python <skills>/remake-core/scripts/package_issue_gate.py retest \
  --project <工程> --native <修复Native> --id <问题ID> \
  --negative-native <故障或可追溯受控反例目录> \
  --normal-native <正常对照目录> --out <新的局部复验目录>
```

只执行该问题登记的case：同一断言在当前版和正常对照通过，在故障对照上确实失败；缺观察、运行器崩溃或采集错误不能冒充故障复现。保存原始观察、实际生产文件与运行器哈希后，校验器才追加`retested`事件。受控反例的来源及构造保存在项目，不能冒称历史发布包。

出包时拒绝以下情况：问题仍只有报告事件、某case缺失/失败、原始证据变化、相关生产文件变化、运行器/校验器变化、手工写closed/pass、历史截断或锚点不符。与该问题无关的资源/文件变化不要求重新执行其运行器。

重新出包只读回有效定点证据和相关文件哈希，不重跑全部case、关卡或美术。相同问题、相同相对生产依赖字节、运行器、检查器、case与原始证据可在新候选目录复用；单纯换目录不要求重测。回执分别保留实际执行的原Native根和当前核对的候选根，不把复用写成已在新目录再次运行。原始执行产物、故障/正常对照仍须存在且哈希一致；不通过改路径、刷新哈希或补写passed续用旧观察。相关文件变化才重新执行该问题的case；不扩大为全游戏CI。当前最终Native的启动/恢复门禁仍由writer独立执行，不能用问题证据复用代替。问题模块改造导致目标文件迁移、运行器需要修正时，使用下述作用域修订保留原报告与断言；旧通过证据立即失效，只重跑该问题的case，不删历史绕过。

## 文件迁移或运行器修正

固定运行器哈希用于防止旧证据被新脚本冒用。需要修正运行器或迁移真实生产文件时，先审阅新的目标和运行器，再追加作用域修订：

```sh
python <skills>/remake-core/scripts/package_issue_gate.py revise-scope \
  --project <工程> --native <当前Native> --id <原问题ID> \
  --targets <更新后的真实生产文件> --runner <经审阅的新运行器.py或.cjs> \
  --message '<迁移或修正原因>'
```

原问题描述、case和后置条件保持不变，事件链保留原报告及修订原因；这一步本身不关闭问题。随后重新执行该问题的`retest`，仍须故障、修复及正常对照。禁止通过作用域修订删除case、减弱断言或复用修订前的通过证据。

## 发布前的短一致性锁

两个writer及最终回执写入前，短时间锁定本工程的问题记录，重新核资源清单、问题证据和Native字节。检查期间新增未闭合问题或清单/证据变化，拒绝发布。长时间启动/浏览器验证不持有该锁，也不影响其他工程。

哈希链限制误删、截断和脱离原记录的手改，并不构成对能任意改写全部文件者的安全隔离；未登记的人类反馈仍须由执行者及时登记。不能宣称程序能自动读懂所有聊天或保证所有未知问题永不出现。

回归：`scripts/test_resource_and_issue_obligations.py`，覆盖漏项、未知动态域、未复验、旧指纹、假pass、正常局部复验、无关变更复用，以及三个入口的拒绝接线。

资源类型仍按实际catalog核对；已核Cocos2/3引擎中`cc.TTFFont`和`cc.BitmapFont`继承`cc.Font`，基类请求可返回这两种真实字体子类；清单记录实际具体类型，图片/JSON等不相干类型仍拒绝，不用类名通配代替类型检查。

## 用户明确收窄到本地测试候选的外部验证范围（2026-10-26）

仅当用户明确说明原设备/旧档不可用，并明确要求依本地实测交当前测试候选时，可用`package_issue_gate.py defer-external --project <工程> --native <当前Native> --id <设备待验问题> --authorization <用户指令记录.json>`追加设备复验待验事件。授权记录使用`external_test_scope.v1`，保留原话、问题ID、`authority: explicit_current_user_instruction`、`scope: local_test_candidate_only`、`external_requirement: original_device_save_replay`及原因。该事件不关闭问题、不改原断言，回执列`pending_external_issues`；只对绑定的同一Native字节有效，授权/Native变化拒绝。不得自动推断用户同意，不用于跳过可执行本地产品故障、资源、启动恢复和最终字节门禁；无该明确用户指令仍按未闭合拒包。原设备实测后照原case正式复验。
