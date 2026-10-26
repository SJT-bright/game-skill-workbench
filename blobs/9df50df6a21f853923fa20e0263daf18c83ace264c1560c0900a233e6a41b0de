# 拖动与声音：验实际结果

文件可读、输入回执、物品跟手、音量值或 `playing=true` 都不足以证明功能正常。上次漏检来自未执行核心互动、未闭合已有失败，以及 Web 真正加载的 index.js 与 Native game.js 不同；不能把轻量文件 writer 扩写成游戏已可玩。

**默认检查项（2026-10-26）**：制作与完整逻辑检查主动执行，不等用户报错；拖动归 F13/R07，声音归 F10/R09。初轮尚未接入音频写明阶段，接入后交试玩前补验。局部任务仅核受影响机制；已通过且字节未变的结果不重复跑。成品试玩/直接出包沿用原制作验收，不能据本页重启无关CI；已报故障须定点闭合。

检查与修复使用以下实际结果判据：

- 从最终包回解，记录实际启动脚本与业务/音频模块 SHA；Web 补充验证先核真实加载的 index.js/引擎及与 Native 的差异，未运行 Native 的部分明确保留。两种手机比例真实拾取→拖出原节点→落到合法槽→棋盘/计数改变→正常结算；另测非法位置无变更、系统取消零提交、第二指不接管。区分 Cocos 节点因越界合成的 TOUCH_CANCEL 与原始系统 cancel（例如 getEventCode），拖影偏移不能改变落点判定。
- 经真实设置入口测音乐/音效各自 0/中档/满档、关/开、设置关闭与前后台恢复。采集实际输出 PCM/录音及能量变化；文件非静音、播放调用和参数不能代替实际输出。故障注入一个非必需音频失败和当前音乐失败；不能全局静音锁死，重新开启/重试须恢复并保留首个加载/播放错误。未定位手机独有根因时不把受控复现称为唯一根因。
- 保留旧版同判据失败、新版和正常对照原始记录。`scripts/audit_interaction_audio.py` 校验当前文件绑定、双比例动作结果、PCM及旧失败；已报告这两类故障时，writer 必传 `--interaction-audio-trace`。用旧失败、缺字段、过期生产 SHA 实际跑 writer，均须拒绝且无 ZIP；工具只核证据一致性，Codex仍审原始记录。未测不补 pass，失败继续修。该补充不触发无关全游戏 CI。

`sound_settings_trace.v1` 是已审 MergeShooter v78 采集器的专用声音设置合同，只有项目、Native 入口/音频适配/业务源码和采集脚本指纹全部匹配才适用；其中行数、行名与 PCM 标签不能推广到其他游戏。它保留该采集器的十一档、两类独立、开关/显示/有效增益、原故障、正常对照与真实输出判据，只覆盖声音设置，不替代拖动或其他音频加载故障的证据。其他工程使用原 `interaction_audio_trace.v1`；自报 schema 不能免除原适用检查。新 producer 须先证明对应原判据与源码绑定，再单独适配，不能复制私有字段凑通过。


## 默认记录与拒绝条件

`logic_check.py --init` 保留已有记录并补 R09=untested，不自动升级旧 pass。R07 的 `drag_applicable` 必须按实际输入清单声明：存在拖动则 `drag_samples` 在两种实际手机比例各有 `legal / system_cancel / invalid`；每条含 `viewport:[w,h]`、`trusted_touch:true`、`picked:true`、`held_after:false` 和业务 `before/after`。合法落点业务必须改变，原始系统取消及非法落点必须不变。不存在拖动用 `drag_applicable:false` 加 `drag_absence_reason` 说明，仍按原规则验证实际存在的触点归属。

R09 的 `audio_channels` 列本游戏实际的 music/sfx，缺少某类须在 `absent_channels` 写具体原因。`audio_samples` 在两比例对每类分别记录 `zero / mid / full / off / on`，字段为 `viewport`、`channel`、`mode`、`trusted_touch`、`signal_id`、`rms_samples`（至少3个真实输出采样窗口）。隔离另一类声音后采样；中档与满档比较同一已解码片段/位置，信号ID相同；不能比较任意两段不同音乐后声称音量生效。两个静音态归零，其余有输出，中档低于满档；启用原始记录的测量点须说明位于实际增益之后。

两项沿用 `flows.json` 的当前源码绑定、非空原始日志/PCM或录音文件及SHA，并在 observations 写实际加载脚本/引擎/adapter/业务指纹、触摸动作与状态结果。R09另记录两类独立、可选音频失败隔离、当前音频失败重试、设置关闭与前后台恢复。检查器 `logic_regressions.py` 每次回读记录与哈希：缺行、零输出、增益不改变输出、合法拖动无变化、取消误提交、旧绑定都拒绝；声明和数字不能替代Codex对原始证据及运行层的审阅。只测了Web就保留Native适配层缺口。
