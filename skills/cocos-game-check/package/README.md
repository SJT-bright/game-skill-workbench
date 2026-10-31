# TikTok小游戏出包与交付

修订：`2026-10-27.modules-v6`。相关正文：[成品测试通过后自动出包](references/check-fix-package-loop.md)、[TikTok小游戏应用创建](references/tiktok-app-creation.md)、[上传后真机测试不在范围](references/tiktok-device-stage.md)。

本入口负责用户授权的测试包、上传ZIP与重新出包。只有真实Cocos Native构建可以生成平台ZIP；根目录直接包含game.js、game.json、project.config.json，不带外层文件夹、源码、Web套壳、套娃ZIP和QA跳关标记。成品制作流程通过后按当前合同连续出包；仅检测/评审/试玩遵守用户边界；本入口不授权平台上传或发布。

## 选择执行范围

| 当前任务 | 执行路线 |
|---|---|
| 新制作首次完整验收/明确完整重做 | 当前适用review通过后用共享 `make_tiktok_zip.py`；完整review与必要启动/存储门禁保留 |
| 已批准成品的局部修改或同版重出 | 使用[最终文件检查与轻量writer](../package-check/README.md)，沿用有效功能证据；仅补受影响问题，不重做已批准美术和无关游戏CI |
| 单独判断已有ZIP | `verify_native_zip.py <ZIP>`或最终检查器；只读诊断不等于已完成可交付门禁 |

共同策略见[执行去重](../test/references/review-execution-plan.md)。适用检查已通过、证据有效且无新改动/失败/疑点即停止，不因表格不同重复操作。

## 两条writer共用的必要门禁

- 当前目标App ID、真实Native根入口/引擎/adapter/分包、静态资源完整性和场景组件绑定。
- 固定未压缩限额：总包≤30,000,000、主包≤4,000,000、每个独立分包≤4,000,000字节，普通分包计总包。按 `upload_size_gate.py`执行；压缩后大小不能替代。
- [生产资源清单与已报告问题](../package-check/references/resource-and-reported-issues.md)：动态请求反查漏项，未知有限域明确拒绝；固定项目问题历史缺失/未复验/失败/相关证据失效拒绝。有效问题证据只读回相关文件，不重放无关矩阵。
- [当前Native启动与恢复](../startup/references/final-package-startup-gate.md)：HOME可操作→可信输入→玩法变化，故障后Retry产生新请求并恢复；同一次可信启动不在交付阶段再跑一遍。
- 最终ZIP CRC、安全路径、逐文件与Native同字节、独立带空格目录回解核对；发送前核实际交付路径。

先拒绝便宜、确定失败项，再运行必要启动/功能门禁。失败继续修复→重建→定点复验，不以中途报告等待下一句“继续”，也不为了变绿而删断言或改限额。项目专用运行器按[项目QA注册](../../remake-core/references/project-qa-registration.md)，路径、App ID与故障原件留项目。

## 正式writer命令

Creator 构建之前先跑 `python3 <skills>/remake-core/scripts/tiktok_finalize.py source --project <工程> --board remake|localize`；写包入口会先查源码段记录（K5），再在门禁之前自动跑产物段（装触摸、存档层、启动件、适配层、App ID，压缩 PNG），并用 K1～K5 确认，`--project` 必须给。游戏自己的打包步骤（例如 MabelsMeadow 的 `scripts/prepare-native-package.py` 把 `config/*.json` 放到包根）不是标准件，仍由这款游戏在写包入口之前对 `<Native>` 做完。收据是 schema 2、带 `finalize` 记录；v7.6 写包入口出的 ZIP 收据在 v7.7 不算官方入口，交付前用 v7.7 写包入口重新出。WebP 例外（只限 2.4）要给 `--keep-webp-exception <原因>`，原因和源码段用的一字不差，否则 K5 拒绝。规则见 [TikTok 固定适配·出包时怎么装](../references/tiktok-fixed-adaptation.md#出包时怎么装v77tiktok_finalize)。

```sh
python <skills>/remake-core/scripts/make_tiktok_zip.py \
  --native <Native> --app-id <目标AppID> --out <稳定交付目录/新版本.zip> \
  --project <工程> --web <同版Web> --build-tag <版本> --review <本轮review.json> \
  --resource-manifest <当前资源清单.json> --startup-contract <当前启动合同.json> \
  --loading-recovery-runtime <当前恢复索引.json>
```

完整制作的其他合同见[检查点](../../remake-core/references/execution-checkpoints.md)、[包形式](references/package-forms.md)。仅持有Native的维护输入使用已审阅的项目适配，不伪造源码或删门禁；新适配补充共同验证，旧项目兼容合同升级时保留。

## 交付

writer成功后按[最终交付核对](../package-check/README.md)对实际ZIP生成新回执，不重新手跑相同文件检查。最终回复主动给当前稳定ZIP可点击链接和同版本已启动的可点击试玩入口，默认不堆报告。原始材料、旧包、用户存档保持；本地结果不冒称设备/真实广告/平台通过。

同期广告模拟、制作统计、Credits和评价等规则按[当前合同](../../remake-core/references/current-contracts.md)选择相关正文，不复制事故全文。
