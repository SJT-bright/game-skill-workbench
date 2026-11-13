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
- 缓存只复用当前进程内、当前代码/数据域/解析器指纹相同的发现结果；每次仍核实际清单与catalog，不缓存跨版本通过章。 SystemJS通用分支按真实`cc`导入setter识别别名，不要求游戏具有Art模块或固定关数；项目专用展开必须额外匹配完整程序与其语义数据指纹。配置驱动的有限ID从当前绑定JsonAsset推导，不能只保留上次ID列表。文件存在/非空/路径及当前指纹检查在缓存外执行。 3.6/3.7 官方导出（R4K2）：import-map 的 `chunks:///<名>` 对到包内唯一一个字面量 `System.register("chunks:///<名>",…)` 的脚本，按本地模块继续扫；没人注册、被两个脚本注册、带 `..` 的照旧拒。scriptPackages 的 `../src/chunks/bundle.js` 按包根解析、文件必须在包内；模板的 `'plugin:': u=>{requirePlugin(u)}` 只在 `plugin:` 键下认。远程地址照旧拒。

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
  --cases <case合同.json> --runner <已审阅的项目定点运行器.py或.cjs> \
  --source local     # 手机上看到的：--source device --device-zip <手机上那个ZIP> --symptom '<看到了什么>' [--phone-error '<报错那一行>']
```

case合同示例（只是格式，实际字段和预期必须来自本游戏）：

```json
[{"id":"reward_once","assertions":[{"path":["reward_delta"],"op":"eq","value":1}]}]
```

运行器须实际执行当前Native的生产逻辑/加载/输入链并输出`{"observed":{...}}`，不能只输出预期数字或恒定pass。登记时固定运行器哈希，调用使用固定的解释器与`--native/--case`参数，不执行报告里提供的任意shell命令。新增运行器须先审阅实际调用目标；观察边界继续如实记录。

### 手机上看到的问题（v7.9，指尖麻将 v42～v57）

**2026-11-12补充：先对故障层。** 平台加载页尚无游戏画面时，存档读值/PLAY之后的受控回归不能关闭该手机问题。可能是包挂载或入口至首帧链，不能仅凭外观判定game.js绝未执行。依实际ENTRY/首帧/平台日志记录边界，读取真实上传版本；缺信息保持未知。适用Cocos2包用当前启动审计拦三种旧adapter前提，再做本作可选API差异对照。原症状未匹配、真机仍失败时，本地通过只保留本地范围；不重交同字节包当成修复。必须走当前writer与正式回执；局部维护、候选命名或draft试玩不能跳过本节已报问题门禁。诊断候选沿用下文defer-external的用户明确授权规则。

**先认包，再下结论**（音乐消消乐复盘 11-05）：拿到手机上那个 ZIP，第一步跑

```sh
python <skills>/remake-core/scripts/which_package.py --zip <手机上那个ZIP> --roots <这款游戏所有工程和交付文件夹> [--roots ...]
```

文件名和版本号都不算数：Saul 会把上传包改名（「音乐消消乐.zip」），两条版本线会同时叫 v30、v31。按字节找原件、按 Cocos 资源 uuid 找同一款游戏的全部包。结果里写着「放在 N 个地方 / 可能有两条以上的版本线」时，先弄清楚手机上那个是哪条线的哪一版，再修。不许说「这是旧包，换用 vX」，除非 which_package 找到了它的原件并且 vX 和它同一条线、更新。起因：11-04 手机报「安卓卡 99%」的是 Kiro 线最新的 v32，Codex 会话没认出来，说它是旧包、让用 Codex 线的 v31（v31 没有复活、x2 和新广告代码），v32 的这个问题也就没人修。

`report` 必须写 `--source device|local`。Saul 或测试的人在手机上看到的问题写 `device`，同时给：

- `--device-zip`：手机上跑的那个 ZIP 原件（不是重新出的包）。
- `--symptom`：手机上看到了什么，用报告人的话。
- `--phone-error`：手机上有报错就照抄那一行（vConsole、录屏里的红字）。
- case 里加 `"phone"` 断言：手机画面是什么样，例如首页显示着（`home_visible eq true`）。

复验时，失败的一方必须是这个 ZIP 原样解出来的目录，改过一个字节、重新出的包、自己造的反例都拒（复验前就拒，不浪费浏览器时间）。在这个包上，`"phone"` 断言必须成立（画面对上），手机报错那一行必须出现；修好的包上那一行不能再出现。对不上就说明电脑上复现的是另一个问题，要先找出测试环境和手机差在哪。

`check` 的结果多一项 `device_issues`，每条带一句中文 `line`，交付回复原样转给 Saul：对上报错的写「复现了手机上的画面和同一行报错」；手机上没报错的写「不能完全确定是同一个原因」。电脑上实在复现不出来、Saul 说先出测试包时，用 `defer-external`（`external_requirement: device_not_reproduced`，要他的原话），这条写「电脑上没复现，不能说修好了」。没有这条记录就一直拦包。

起因：这款游戏首页点不动的手机问题，Codex 三次（v43、v44、v45）都在电脑上修了另一个问题或一个自己造的条件，就报了「已修复」，从没对上手机那行报错 `No loading progress for 10 foreground seconds`。同一个 v57 包，「时钟跳 12 秒」报的是另一行错；「卡住 JS 12 秒」才出手机那一行和首页显示着点不动的画面。回归：`scripts/test_device_issue_repro.py`。

对依赖时序或页面重入的反馈，case 增加 `reached`，格式同 `assertions`。例如复验“弹窗关闭后首页点不动”，前提是本次弹窗已经关闭、首页按钮已显示；随后在画面上实点，结果是预期页面打开一次。前提须在故障版也能成立，不能把“按钮响应”同时写进前提。三组运行都须从真实事件观察到前提；动作已发出或预设标志不能充当到达。运行器从操作前到结果采集结束记录未处理异常及相关运行错误到 `errors`（无错误为 `[]`）；故障组只接受事先登记的目标报错（手机沿用原报错，本地异常本身就是故障时用 `negative_error` 精确登记首行）。能预期且被游戏正常处理的注入失败应单独记录。手机画面和原报错必须来自同一次故障运行。首次创建或修改用例时按用户操作选能区分该故障的可观察前提和结果，之后沿用既有依赖复用规则。

同一成功条件有多种失败表现时，用 case 的 `symptom` 记录报告中可观察的故障特征（格式同 `assertions`）。例如预期提交一次，用户报告提交两次，故障组须观察到两次；提交零次属于另一故障。修复及正常组须满足成功条件，且原症状消失。只有“发生／未发生”两种结果且已有断言足以区分时，可省略此字段。沿用同一次运行的观察。

## 定点复验通过才形成关闭事件

```sh
python <skills>/remake-core/scripts/package_issue_gate.py retest \
  --project <工程> --native <修复Native> --id <问题ID> \
  --negative-native <故障或可追溯受控反例目录> \
  --normal-native <正常对照目录> --out <新的局部复验目录>
```

只执行该问题登记的case：同一断言在当前版和正常对照通过，在故障对照上确实失败；缺观察、运行器崩溃或采集错误不能冒充故障复现。保存原始观察、实际生产文件与运行器哈希后，校验器才追加`retested`事件。受控反例的来源及构造保存在项目，不能冒称历史发布包。

出包时拒绝以下情况：问题仍只有报告事件、某case缺失/失败、原始证据变化、相关生产文件变化、运行器/校验器变化、手工写closed/pass、历史截断或锚点不符。与该问题无关的资源/文件变化不要求重新执行其运行器。

重新出包只读回有效定点证据和相关文件哈希，不重跑全部case、关卡或美术。相同问题、相同相对生产依赖字节、运行器、检查器、case与原始证据可在新候选目录复用；单纯换目录不要求重测。回执分别保留实际执行的原Native根和当前核对的候选根，不把复用写成已在新目录再次运行。原始执行产物、故障/正常对照仍须存在且哈希一致；不通过改路径、刷新哈希或补写passed续用旧观察。相关文件变化才重新执行该问题的case；不扩大为全游戏CI。当前最终 Native 的启动/恢复记录由 writer 单独核对其依赖和原始材料，只读消费，不再启动运行器；本问题的证据不替代对应启动/恢复记录。问题模块改造导致目标文件迁移、运行器需要修正时，使用下述作用域修订保留原报告与断言；旧通过证据立即失效，只重跑该问题的case，不删历史绕过。

## 按新设计作废旧问题（v7.8，总表 B32 a，supersede-by-design）

Saul 改了设计，旧问题登记的用例不再适用（例如结算 x2 和复活原来同一屏，现在定成两屏、每屏一个看广告按钮），旧问题永远复验不过。不许删历史、不许手写 pass，按下面两步做：

1. 按新设计登记新问题：`package_issue_gate.py report`，新的 ID、新的 case 和后置条件、新的运行器（和登记任何问题一样）。
2. 作废旧问题：

```sh
python <skills>/remake-core/scripts/package_issue_gate.py supersede --project <工程> \
  --id <旧问题ID> --by <新问题ID> --quote '<Saul 原话>' --date 2026-10-30 [--message '<新设计是什么>']
```

- Saul 原话、说这话的日期（YYYY-MM-DD，不能是将来）、已经登记的新问题 ID，缺一个就拒；新问题不能是旧问题自己，也不能是已经被作废的问题。手写进问题记录、缺这些字段的作废事件会让整份记录拒包。
- 旧问题的报告、case 和以前的证据都留在事件链里；作废后它不再拦包，也不能再 retest。新问题和其他问题一样，复验通过前照样拦包。写包回执的问题部分多一项 `superseded_issues`（旧 ID、新 ID、原话、日期）。
- 作废可以接着作废（新设计又改了：再登记一个，再 supersede 那个新问题）。
- v7.8 只加了这个事件，复验证明的检查规则没变：v7 到 v7.7.5 的 `package_issue_gate.py` 写的复验证明照样认，装上 v7.8 不用把已经关掉的问题重测一遍。

回归：`cocos-game-check/package-check/scripts/test_issue_supersede.py`。

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
