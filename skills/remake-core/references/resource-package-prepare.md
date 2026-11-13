# 资源整理时完成分包，首份 Native 校准实际字节

本流程属于首次完整制作或用户明确要求的整体现代化整理。普通旧游戏只修侧栏、换一处美工时，不因缺少本流程的新记录自动拆包，也不新增写包门禁。最终交付仍执行原有实际 ZIP 体积检查；这里不写诊断 ZIP、不运行游戏、浏览器、录屏或上传。

资源开始制作前先确定首屏依赖与整目录归属，广告与新增页面资源也一次纳入；美工按归属直接输出。调用的是实际准备工具，不能只运行估算后把报告当作分包已完成：

```sh
python3 -B "<skills>/remake-core/scripts/resource_package_prepare.py" prepare --project "<project>"
```

Python 接口：`prepare(project, plan=None, board='localize')`。`HOME` 是工程内 `.tiktok-kit/resource-package`，成功或已实施但仍有预算缺项的静态记录是 `prepared.json`；显式归属计划可放在 `docs/startup/resource-package-plan.json`。所有路径均相对工程，工具和平台零件从同包目录定位，换电脑无需旧用户名、旧绝对路径或作者的其他游戏。

此时实际执行以下内容：

- 复用 `first_screen.py` 的启动场景、首页、UUID 引用、组件脚本与路径加载闭包，以及 `audit_package_estimate.py` 的同一计量口径。
- 对 Cocos 2.4.x 的 `assets/resources` 设置 ByteDance **普通分包**。目录与各文件 `.meta`/UUID 保留；不移动所有图片；已合法的配置原字节沿用，其他平台 `compressionType` 和扩展字段保留。
- Cocos 2.4.15 使用本包 manifest 验证过的原始 kit `main.js` 及其直接依赖，沿用已有进度、重试、前台计时与资源加载链；自定义模板不能被静默覆盖。其他 2.4.x 保留同版本编辑器启动，不复制 2.4.15 模板，首份 Native 必须读实际启动链核准。
- 将**主包 4,000,000 字节**和**首屏 10 MiB（10,485,760 字节）**分别记录。kit 会在首屏前下载整个 `resources` 分包，因此不能因为改成分包就把它记为延后下载；其他首屏前的分包取并集一起计算。
- 普通分包没有被本工具错误套成每包 4 MB；独立分包的 4,000,000 字节与独立入口约束单独处理，不能把共享资源标成独立包以逃避主包计量。总包仍为 30,000,000 字节。

`resources` 太大时，当前 AI 根据报告中的具体目录与加载点补一个**整目录**延后归属，不要求用户再发“继续”，也不启动全量玩法或美术检查。例如：

```json
{
  "schema": "resource-package-plan.v1",
  "bundles": [],
  "deferred_groups": [
    {
      "source": "assets/resources/levels",
      "destination": "assets/levels",
      "name": "levels"
    }
  ]
}
```

工具会验证该目录不是首屏依赖，不包含脚本或场景，所有资源调用能确定归属；然后一次迁移目录及资源的全部原始 `.meta`，给目标目录设普通分包。已有 UUID 的序列化引用继续有效。只在 AST 识别的直接 `cc.resources.load/loadDir/preload/preloadDir` 和 `cc.loader.loadRes/loadResDir` 调用接入生成的 `ResourcePackageLoader`，该桥接实际调用现成 `ResLoader.loadBundle`，保留原类型、路径余段、完成回调和未迁移路径的原接收者。现成加载器负责同一 bundle 的并发合并、错误与前台重试；不会为每张图新写一套加载器。

已批准的整目录归属保存在记录里。此后新资源写入旧命名空间时，下一次准备沿用相同归属迁入目标目录，资源及 `.meta` 原字节保留。目标已有不同文件或 UUID 时返回精确冲突项，不覆盖已有资源。`deferred_groups` 只处理当前明确支持的调用；别名逃逸、未知动态路径、无完成回调、尚未映射的 TypeScript 资源调用、自定义启动返回 `mapping_required`，列出 `source/line/expression/required` 等具体缺项。**该状态是当前 AI 的定点修复任务，不是回合终点，不是等待用户批准，也不能转换成“从头重测”。** 当前 AI 补有限动态域或正确的同版本启动接入后，继续此静态资源步骤。

同一工程的准备操作使用跨进程 `project_lock`；一次冻结后的相同输入、相同归属和相同工具直接复用。记录绑定实际资源、脚本、配置、模板和用到的工具/零件，不因记录自身的写入反复触发准备。准备中途失败会恢复原有资源和目录 UUID；不把失败结果当作通过。

首次 Native 标准准备完成之后，读取实际产物进行一次字节校准：

```sh
python3 -B "<skills>/remake-core/scripts/resource_package_prepare.py" calibrate --project "<project>" --native "<native>"
```

Python 接口：`calibrate(project, native)`。它复用 `upload_size_gate.enforce`、`PackageView` 和 `pre_home_bytes` 读取真实主包、普通分包、独立分包、总包与首屏下载并集；核对实际配置中的计划分包及入口。源估计通过不等于 Native 通过。2.4.15 用精确 kit 身份证明启动链；其他 2.4.x 对保持的编辑器启动，当前支持 AST 确认的顶层主入口，以及 `resources` 平台分包成功回调进入实际 `cc.assetManager.loadBundle('resources', originalNext)` 的链。注释、死文本、单独出现函数名不算接入。复杂原版启动返回具体映射：由当前 AI 在同版本原始启动的成功续行点接入，不换引擎模板；该节点完成后再定点读取校准。

校准记录是 `native-calibration.json`。同源码与同 Native 字节沿用，`sync --native` 与后续相同产物准备不会重复校准；变化时只重做实际受影响的资源/配置计量。这里的“校准”仅证明当前文件计量和受支持的静态启动依赖，不能写成真机、广告或平台上传通过。

四个 API 都返回稳定字段：`status`（`prepared` / `calibrated` / `mapping_required` / `needs_prepare`）、`passed`、`blocks`、`next_action`。只读 `consume_current(project)` 可用于阶段状态展示；它**不作为所有旧游戏的新写包门**。根流程在首次完整制作的资源阶段启用，在首份 Native 后调用校准；之后继续原有必要定点验证和最终 ZIP 轻量检查。


## Cocos3 的可完成路线与受审阅的实际引擎适配

`prepare` 对3.x 不再固定退出。它只读读取实际目录 `.meta` 中的 `userData.isBundle`、`bundleName` 与目标 `compressionType`（`bytedance-mini-game`，兼容已存在的 `bytedance` 字段），按实际普通分包归属计量，不写2.x配置、启动模板或资源桥接。已有合法配置与预算可直接登记为 `prepared`；若主包超限，当前AI修改实际3.x目录/构建配置和加载点，再调用即可完成，不会因为版本号永久卡在映射状态。场景选择不明确时在计划填写真实 `boot_scene`、`home_scene`，不会换引擎来绕过。

复杂的真实构建配置或动态资源域，复用现有 `project_qa` 注册方式。由当前AI审阅工程内适配器及其依赖，注册相对路径；这是已有授权范围内的工具代码身份登记，不是再次询问用户批准。新电脑重新读取同一份工程内manifest、审阅并登记，不引用旧电脑的信任文件。

```json
{
  "schema": "cocos_project_qa.v1",
  "validators": {
    "resource_package_adapter.v1": {
      "path": "qa/resource_package_adapter.py",
      "dependencies": []
    }
  }
}
```

使用 `project_qa.py register --project <project> --manifest <project>/qa/project-qa.json --reviewed`。适配器提供以下函数：

```python
def resource_package_adapter(*, project, phase, source_inventory, plan,
                             native_inventory, native_files):
    # Read the actual engine config/loading code; derive the finite dependency domain.
    # phase is "source" or "native"; native_files contains actual Native bytes.
    ...
```

返回契约 `schema: resource_package_adapter.v1`，必须包含：

- `source_inventory_sha256`：传入完整 `source_inventory` 的规范JSON摘要；规范为 `json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'` 的UTF-8字节。
- `basis`：实际配置与加载代码的推导说明；`unknown: []`。`passed: true`、文件存在或口头“已支持”不构成映射。
- `startup_bundles`：审阅后确定的有限启动依赖。工具仍会加入首页实际UUID依赖、实际静态启动加载与已解析的动态加载；不能漏掉它们来降低预算。
- `resolved_sites`：需要解析的动态点填写 `source`、`line`、`source_sha256`、有限 `bundles`。源码摘要必须等于当前实读字节；适配器变动、依赖变动或登记失效不能沿用。

构建器把分包配置保存在非标准字段时，适配器可补 `bundles`。每项给实际 `directory`、`name` 和 `config`；`config` 指定当前生产输入中的 `file`、`name_pointer`、`mode_pointer`、`enabled_pointer`，指针为明确的JSON路径数组。工具自己读取并核对实际值分别等于该bundle名称、`subpackage`、`true`；不是接收适配器自报通过。实际输入范围包含assets、settings、build-templates、profiles及工程版本文件，不接受无关“证据JSON”代替实际构建配置。

首份3.x Native 仍重新读取实际字节。核对 `game.json`、实际settings（含唯一hash文件名）、引擎分包名单、由bundle版本选择的实际config和实际预载并集。常规入口经AST验证主入口到实际引擎/应用/settings初始化链，注释或死文本不能证明接入。复杂启动也可由已登记的同一适配器提供 `phase="native"` 投影：必须绑定完整 `native_inventory_sha256`、`bootstrap_inputs` 中每个实际启动/设置/引擎文件摘要和 `startup_bundles`。非标准settings文件名还需 `settings_file`。工具再次核对实际文件、配置和预算，并要求启动集合覆盖实际预载；适配器必须从实际 `native_files` 推导，不能只拼接一组hash就声称运行成功。这里始终是受审阅的静态引擎依赖证明，不替代已有实际启动回执或真机验收。

## source finalize 之后只刷新证明

```python
result = resource_package_prepare.refresh_current(project)
```

CLI为 `resource_package_prepare.py refresh --project <project>`。这个入口在 `source/sync` 收齐实际生产改动之后更新资源归属与预算证明，**不写assets/settings/templates/profiles，也不重写既有first-screen/budget文档**，仅写 `.tiktok-kit/resource-package/prepared.json`。同一静态闭包只分析一次；没有source改动时直接沿用。若当前状态还需要移动目录、补分包配置或改启动，返回 `needs_prepare` 与准确文件/动作，保持当前生产文件原字节；当前AI应在下一次source finalize之前完成该定点准备，不得悄悄修改source后把旧Native当作同版产物。
