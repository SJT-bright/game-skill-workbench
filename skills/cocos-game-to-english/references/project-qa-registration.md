# 项目QA注册与可移植边界

共享Skill不保存游戏目录、App ID、已执行游戏证据或本机运行器路径。项目内 `qa/skill-qa.json` 使用 schema `cocos_project_qa.v1`，runners/reviews/validators/resource_scanners/resource_profiles/evidence_profiles/ui_runners 按需出现，所有代码和依赖路径均相对工程。工程搬家后，审阅真实文件并重新登记新位置；不需要修改共享Skill。

```json
{"schema":"cocos_project_qa.v1","runners":{"my-game-startup":{"path":"qa/startup.py","dependencies":["qa/host.js"],"timeout_seconds":120,"control_profile":"native_startup_controls.v1"}}}
```

主Agent审阅运行器确实执行当前Native入口、真实引擎与业务输入，并核对负例/修复/正常对照后，执行：

```sh
python <skills>/cocos-game-to-english/scripts/project_qa.py register --project <工程> --manifest <工程>/qa/skill-qa.json --reviewed
```

这是代码身份登记，不代表游戏、报告或平台验收通过。登记存于执行者自己的 `.codex/cocos-qa/trust.json`，不放入共享发行包；无shell、固定Python runner、固定参数、1..120秒上限保持。未登记、报告任意command、相关runner/dependency/合同变化、执行期间换Native仍拒绝。实际HOME→可信输入→玩法变化、加载恢复、原始证据与最终字节校验仍由原门禁执行。

新的项目review只可补充schema 3的共同检查，不替代或绕过它；writer补充亦不跳过共同持久化覆盖。新的validator补充真实引擎/输入等公共判据。运行器依赖按所属项核哈希，不因其他项目/不相关运行器改动重测；本页不触发全游戏CI。

旧安装的专款审计和绝对路径登记在升级时保存为本机私有兼容合同，保持原条件和负例；不把其通过材料传播到新项目，不导出旧账号/路径状态。它们不是新项目可声明的 `legacy_*` 开关。旧工程可逐步把适配整理进项目qa并重新审阅登记，历史证据保留。

动态资源域另存项目 `qa/resource-profiles.json`，以 `resource_profiles` 中的 `reviewed_resource_profiles.json`（或 `systemjs_finite_profiles.json` / `cocos2_finite_profiles.json`）项登记该相对文件，结构继续遵守资源审计合同；其引用的数据文件纳入dependencies。专用声音原始证据数据可用 `evidence_profiles` 的 `sound_settings_trace.v1` 项登记项目内JSON，JSON中不写project绝对路径。主Agent必须审阅生产字节、采集者、原始正负对照与限定范围；登记不放行旧证据。共享发行包不带任何项目的登记和报告。
