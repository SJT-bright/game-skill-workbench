# 已有证据回流与隔离维护

`production_learning.py` 把每款游戏本轮已有的轻量问题、修复、续跑与计时记录汇成可携带经验包。游戏成功交付后调用一次非阻塞收集即可；它不运行游戏、检查器、Skill CI、完整美术回执、新复核表或录屏，不改原交付 record 与 ZIP，也不自动上传、安装或修改正式 Skill。关闭当前聊天后不会自主工作。换电脑时复制经验包，显式 `import` 到新电脑的维护工作区。

```python
from production_learning import collect_nonblocking
result = collect_nonblocking(
    project,
    record_paths=["docs/production/summary.json", "docs/checks/repair.json"],
    context={"delivery_ready": True, "final_zip_sha256": final_zip_sha256},
)
# 不用 result 成功与否决定游戏能否交付；所有正常失败 delivery_blocking=False。
```

调用者优先传本轮已写出的项目内 JSON/JSONL。未传时仅查看已存在的真实英化计时 `docs/timing/stage-timing.jsonl`、`docs/timing/timing-summary.json`、问题账本 `docs/test/package-issues.jsonl`，以及 `docs/production/accounting.jsonl`、`docs/production/summary.json`、`docs/checks/known-issues.json`、`docs/checks/delivery-continuation.json`、`docs/production-learning/proposals.json`，不递归搜其他游戏、聊天、素材或整份日志。项目外的正式交付记录不复制进来；只通过 `context` 传 readiness、64 位 ZIP SHA 和不含路径的可选 `build_tag`。上下文属于项目私有证据，不是规则。

收集最多 32 个现有记录、每个最多 4 MiB、总读入最多 8 MiB；读取本身有长度上限。超预算或缺文件记 `deferred` 及原因，留下本地 outbox 等待维护，不补测、不排常驻线程。显式 queue 使用 SQLite 立即尝试事务，锁占用直接 deferred；本地包已保存，当前游戏继续交付。路径拒绝越界和 symlink。出站包位于 `docs/production-learning/outbox/<内容ID>.json`，相同输入不重复建包；并发导入以内容 ID 唯一约束去重。

包里保存原记录 SHA、规范化后的项目私有证据及其独立 SHA。项目路径改成 `<project>`，外部绝对路径只保留不可执行的 `<external>` 标签；凭据字段不携带。规范化 SHA 不冒充原文件 SHA。失败、修复和正常反例都保留在原 payload；不会因为后来成功而擦除旧失败。`recorded_confirmed_fix` 必须同时有显式根因 ID、修复内容、不同的前后 SHA 和原记录中的 failure/fixed 结果；缺根因、差异或验证时只生成 `candidate_needs_cause_or_validation`。`prevention_stage` 只沿用原记录明确字段，不从标题或一句报错猜根因。计时原记录一并携带，不把一次读取耗时写成游戏测试耗时。

## 维护命令与状态

`TOOL` 为此 Skill 的 `scripts/production_learning.py`；`WORK` 是普通的本地维护目录，必须在正式 Skill 安装目录之外；`BASE` 是只读基线。普通游戏只调用 collect，不进入下面的维护流程。

```sh
python3 "$TOOL" collect --project "$PROJECT" --record docs/checks/repair.json
python3 "$TOOL" import --workspace "$WORK" --bundle "$PORTABLE_BUNDLE"
python3 "$TOOL" plan --workspace "$WORK" --base "$BASE" --out "$WORK/plan.json"
python3 "$TOOL" audit --workspace "$WORK" --base "$BASE" --plan "$WORK/plan.json"
```

collect 的退出码始终为 0，结果始终含 `delivery_blocking:false`，可返回 collected、unchanged、deferred、error。维护命令的候选阻断返回 2；这只是维护候选需要修订，不能反向阻断当前游戏。维护缺项通过 JSON findings 指向具体原因，不触发全量游戏重检。

规则提案使用 `production_learning_proposals.v1` 的 `rules` 数组；具体格式见同目录 `production-learning.schema.json`。每条规则必须带稳定 `id`、`revision`、`cause_key`、结构化适用轴与布尔条件、权威来源、status、supersedes、生产预防动作及 producer/consumer 节点、绑定证据与实际测试成本。通用 scope 只接受当前 catalog 已登记的轴和值；未知或项目专有范围保留为维护候选。规则 generalization 还须明确已审且私有字段已移除，不能把游戏名称、ID、金额或一款游戏的专用键自动变成共享要求。

共享提案必须包含至少一个 `role=prevention`、`operation=prepare/prevent` 的开工、source 或接入生产动作；仅增加 `run_check` 不算吸收经验。确实属于外部条件时，须用结构化 `prevention_limit` 写清不能生成时消除的原因、最早恢复节点、恢复/降级/有界重试方案。缺少这些信息仍是维护候选，不能增加游戏交付门槛。

合并键是明确的根因加适用范围和条件，标题不参与。相同原因范围的相同动作合并为一次；相同 revision 的相反内容不采用最后写入者。修订须显式 supersedes；越范围替代、循环替代、同条件相反动作、重叠范围的重复执行节点、缺原失败/修复/正常反例、假成功或无原记录支持的成本，都会阻断维护候选。named-check 的 producer 执行检查、writer consumer 读取记录是合法的不同 role，不算重复测试；consumer 不能改成执行检查来绕过治理。

内置 `assets/production-learning-policy.json` 绑定 catalog 版本和正式基线 ZIP SHA，永久保护四个已撤销行为 ID：`full_art_receipt`、`default_video_recording`、`blind_full_retest`、`alternate_writer`。不能用新标题、另一条规则或旧包复活这些行为。用户撤销记录在后续导入中继续保留；另起 ID但同范围复活同一动作也阻断。未知根因和验证不足不自动晋级，更不会自动安装到别人的电脑。

## 经过审查的隔离应用

plan 本身不是批准、CI 通过或正式发布。维护者审查具体差异后可创建 review：

```json
{
  "schema": "production_learning_review.v1",
  "approved": true,
  "scope": "isolated_candidate_only",
  "plan_sha256": "<plan.json实际文件SHA>",
  "base_identity": "<plan里的base_identity>",
  "approved_rule_ids": ["RULE.EXAMPLE"],
  "reviewer": "<本次实际维护者>"
}
```

```sh
python3 "$TOOL" apply --workspace "$WORK" --base "$BASE" --plan "$WORK/plan.json" --review "$WORK/review.json" --candidate "$WORK/candidates/reviewed"
```

每个变更包含项目无关的 Skill 相对 path、before_sha256、after_sha256 与确切 UTF-8 content；新文件的 before 为 null。只可写入 `WORK/candidates/<name>` 的新隔离副本，不能原地改 BASE 或任何正式安装目录。保护 catalog 和治理器本身的补丁不能由经验包覆盖。应用在队列事务锁内复核原 plan、review、完整 base、catalog 及队列，过时/并发变化明确拒绝；使用同一 plan 重入且产物字节未变时沿用，不重复应用。路径越界、symlink、同一路径相冲突的补丁、未审查或不相同的基线均拒绝。应用不会执行 payload 中的命令，也不会自动跑测试。

正式发版仍由维护入口完成：只测真实受影响的检查，保留原失败与有效正常对照，再核完整正式 ZIP 与授权安装点。apply 成功只表示得到可审查的隔离副本，不表示已经发布或安装。

## 跨版本生效规则与撤销索引

同包 `assets/production-learning-active.json` 是版本化 active registry。plan 总是先读取 BASE 中已审的完整规则语义、替代/撤销状态和最小证据索引，再与新 workspace 的 bundles 比较。换电脑或清空维护队列不会丢掉上一版的冲突、同义合并和禁止复活约束。已有机制的 BASE 缺 registry 时拒绝维护，不能当成首次空白状态重置；机制出现之前的旧正式基线只允许一次显式迁移为空 registry。

apply 由治理器生成新 registry 并写进隔离副本，经验 payload 不准直接覆盖它。registry 保存规则、明确的 producer/consumer/prevention 角色、scope、authority、supersedes、测试成本与原证据 hash、已审 outcome、来源 plan/review SHA；不会复制项目全日志、制造新的 passed observations 或把旧索引说成新实测。已应用的 patch 只保留历史 hash，不会在新 BASE 再执行一遍。producer 执行 named-check 与 writer 只消费已核记录的原则作为结构化 catalog 和 registry 约束随包保留。
