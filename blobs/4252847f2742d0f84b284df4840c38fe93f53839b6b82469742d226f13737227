# 开工阶段的 Creator 迁移专检

适用原工程 Creator 2.0～2.3 且按引擎路线升到 2.4.15 的新英化。开工仍可先给用户原版试玩。批量英化接入用后续真正要用的迁移副本。普通 2.4、3.x 和已交付局部返工按各自现行流程走。

## 先确认迁移副本能干净开局

1. 从中文原工程复制工作副本。升级前运行下面的 `prepare`，在副本登记原版和目标编辑器。用本机 Creator 2.4.15 打开并保存该副本。
2. 从副本执行 `build`。工具先把工作副本路径解析为实际目录，再从该目录调用本机目标 Creator 生成 Web 基线。macOS 的 /var 临时目录别名在《勇往直前》上会使正常的相对导入回落，真实目录构建能从源头避免这次错误。以后这份迁移工程的构建也用 find_creator.py 给出的真实目录。用随包解析器读实际的 CommonJS 模块表。重点定位可复现的状态分裂，例如一个调用者写入共享节点，另一个因相对引用回落拿到另一份实例。单独存在相对引用不判错。无法读到支持的产物格式时先定位具体文件。
3. 遇到已确认问题，查看报告中模块、调用者和字段，修工作副本里的真实引用，确认目标唯一且大小写正确。只改对应引用和必须的配置。临时补丁可用来定位，完成后用同一构建入口重新导出。确认真实路径下仍有具体错误时再修改引用。检查器没有自动改脚本、缓存或导出文件的操作。
4. `smoke` 在同一份 Web 基线上用 Ego Lite 实际点一次原版 PLAY，观察到真实玩法节点激活或进入指定场景才记录通过。从本作场景、预制体和实际节点定位路径。节点路径相对于当前场景，走真实触点。玩法目标必须能区分点击前后。开始第 2 阶段时 `stage_timer.py stage 2` 读取现有记录和文件指纹。

```text
python3 <skills>/cocos-game-to-english/scripts/creator_migration.py prepare --original <原工程> --project <工作副本>
python3 <skills>/cocos-game-to-english/scripts/creator_migration.py build --project <工作副本>
python3 <skills>/cocos-game-to-english/scripts/creator_migration.py smoke --project <工作副本> --play-node <PLAY节点路径> --ready-node <开局后激活的节点路径>
```

切换场景的游戏可用 `--ready-scene <开局场景名>`。Windows 使用本机 `python` 或 `py -3`。Python、Node.js、Creator 2.4.15 和官方 Ego Lite 按开工环境检查在本机发现。解析器随完整英化包提供，路径含中文和空格也按参数传入。用现有阶段计时给 `build`、`smoke` 记时。首页和开局观察在一个 Ego TaskSpace 内完成，结束自动关闭。已经用该迁移 Web 作为中文原版候选时，沿用同一份导出。

## 沿用结果与跨电脑接手

`docs/english/creator-migration.json` 记录目标引擎、相关源码指纹、项目相对导出目录和 Web 指纹。在两个输入都能核对的电脑上，`check` 读回现有结果。文件仍一致时 `build` 沿用原构建，`smoke` 沿用同一条操作路线的通过结果。转交时保留这份记录和该 Web 基线。缺 Web 时在接收电脑重建本项所需的基线。

批量英化开始后沿用迁移基线的证明。仅改图或显示文案时，按现有美工和复验范围走。重新改变引擎、模块接线、脚本注册或构建配置时，先在受影响的第一份 Web 候选上运行 audit，只补受影响的实测。正式英文候选仍使用本版实际导出和原有试玩记录。
