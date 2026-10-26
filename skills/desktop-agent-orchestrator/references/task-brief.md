# 任务书与实时台账

每任务指定决策权、写入权、验收权。先有主线判断和固定规则，再派执行；不得把“自行研究完整实现”填进规则栏。不要复制整段历史或凭据。

## 桌面发送模板

```text
任务ID：{唯一ID}。你是{角色}，只执行本批，不向其他会话转派/开子代理。
项目/工作副本：{绝对路径}。输入manifest：{路径、SHA}。
主线已决定：{具体映射、方法、接口、状态、预期输出；B附规范路径/SHA}。
本批动作：{已定步骤/现成命令及完整参数}。
唯一可写：{明确文件/目录}。关键保护文件：{路径，只读}。
上游依赖/资源锁：{输入产物、Cocos工程/构建目录、应用会话}；浏览器空间由执行者自己新开（被占就开新的，不等待，开前 `browser_slots.py sweep --close`）。
输出/报告：{本批独占目录}，保存真实命令/退出码/原始结果、指纹与差异。
完成条件：{主线已定断言、正常/失败对照、实际环境}。
交回主线的情况：{新规则、需改保护文件、范围/接口变化、结果与预期不符}。
决策和最终验收都归主线。你只报告执行状态，不修改规范、门禁或断言以求通过；
QA不改业务，打包者不改产品/自批例外；未运行/未观察保留待验。
遇到新歧义停止有关写入并给原始事实，可继续其余已定独立项；不改其他任务、原档、
存档、共享Skill、模型/权限，不购买额度或替主线宣称整体完成。
```

提交后在同应用会话回读任务ID、消息和实际执行。已有草稿不得覆盖或发送；换确认空白的新工作会话。送达、开工、产物到达和验收分别记。

## 检查器任务JSON字段

- `run_id/task_id/task_type/role`：A01–A18、B01–B06或C01–C08；角色为intake/resources/ui/patch/build/qa/package_writer/package。package_writer只按冻结规范产包，package只独立核验；同A17分成两个任务/会话，生产者不能自验。受限搬字另用literal_copy/clear_text_ocr及literal角色，不把它们当语义判断。
- `steps/expected_outputs`：非空文字列表，分别列本批已定命令/动作和可验收输出；不能只给任务编号而无具体执行内容。
- `decision_owner/acceptance_owner`：都为main；`subdelegate`为false；`critical_logic`由主线判断，关键任务true或C会返回main_only。
- `project_root`：已存在的绝对工作目录；`write_paths`：本任务明确可写路径列表，无glob，不直接声明整项目可写。
- `input_ref`：包含path/sha256，指当前输入manifest；B及A06/07/08/17另有相同结构的 `spec_ref`，固定主线规范/映射或冻结产包范围。
- `change_tests`：显式bool，只有B06可为true；其断言已由主线决定，不允许删除/放宽旧断言。
- `resource_locks`：列表，A09须有creator:工程路径，A12须有service:目标服务，B05/运行时A13须有browser:唯一空间；同锁串行，另登记构建目录/origin/会话等实际共享资源。
- `capture_mode`：A13必填offline_assets或runtime_gui；前者只做原件/已有截图的离线采集，后者另需实际browser工具与锁，不以终端能力冒充GUI。
- `independent_of`：QA和包核验必须列不同的产物生产任务ID；不能用对应生产者同一会话签收。

会话身份由app+conversation组合定位；不同应用偶然相同的会话ID不混算。AStudio等非共享应用必须用自身容量组，不能借Grok等组扩容；名单外应用即使自称工具合格也不派。真正的共享应用族由主线按当前用户授权修改明确政策后登记。

## 实时台账JSON字段

本轮`activation`必填：`run_id`非空、`mode`为`desktop_multi`或`single`、`user_confirmed=true`、`authorization_ref`指当前人类选择或明确调动指令。任务run_id必须与本轮activation.run_id相同。新任务必须重新询问；仅引用本Skill/上一轮配置不算选择。未确认返回activation_required，single返回single_agent且不选任何应用。检查器只校验声明，主线仍核实际人类授权，不由执行者写true获得派发权。


`allowed_roots`由主线列本轮批准的工作副本及证据根；`protected_paths`列主线关键文件、原件及不许改的规范/断言；`evidence_roots`列执行者可写的证据/产物根。路径全部绝对，QA/package_writer/package/literal只可写该范围；生产者和独立核验者各用不同输出目录，核验者原ZIP只读。不能把整个交付目录授予任务。

检查器自动保护input_ref/spec_ref自身；主线另外把manifest指向的真实产品输入、冻结Native和待核ZIP加入protected_paths，不能仅保护manifest而放开实际产物。

`tasks`逐项记task_id/app/conversation/state/write_paths/resource_locks及送达/产物/验证来源。sent、running、artifact_ready、independent_review、needs_main_decision、rework、stopping、uncertain均保留相关租约，直到停写/交回已确认。

`apps`逐项记：

```text
id（仅workbuddy/astudio/workbuddy_ai/qoder_cn/qoder/opencode/grok）
app_path/bundle_id/conversation（真实完整路径、身份与目标会话）
roles/roles_approved（本轮主线核过的角色及true）
capabilities（实际已核files/edit/terminal/browser/trusted_touch/vision）
ui_readable/project_verified/tools_verified/model_verified/quota_ok（真实核对的bool）
capacity_group/configured_limit/global_occupied（同容量组全局占用，未知用null）
observed_at/observation_ref（有时区时间、对应原始观察文件或记录）
```

Qoder与CN同capacity_group=qoder且上限合计3；WorkBuddy与国际版不同组各3；AStudio/OpenCode各1、Grok桌面常规5最多6，后台单批默认3且总占用仍核。名单外应用不派。当前人类明确调整时，主线同步调度政策/工具再用，不由执行者改台账扩容。旧记录不保证当前空闲/免费。

默认机械检查只接受15分钟内通道观察；真正发送前仍核当前窗口/会话。台账字段是声明，不能证明用户操作没有改变状态，不能代替GUI送达或原始产物验收。

Grok后台记录transport=grok_cli及cli_ready；app_path是当前可执行CLI文件，conversation是实际UUID，observation_ref定位CLI/模型/回执核对；不强求Grok桌面窗口。其余六家transport=desktop并核当前窗口。

现成命令单独放代码块或独立最后一行，不在命令末尾附中英文句号/解释；UI发送后核真实消息原文。若固定命令因任务书标点出错，保留负例，由主线纠正具体命令，不改断言/门禁，不让执行者自行扩大修复。浏览器采证需要临时脚本/截图时，任务书事先列独占scratch目录及清理责任。
