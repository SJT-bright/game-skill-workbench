# 存档与启动按实际依赖沿用

首轮通过后准备局部返工，或接收已交付旧工程时使用。单入口写包规则见 [single-writer.md](single-writer.md)。本流程不生成完整美术回执，不录屏，也不重开无关玩法矩阵。

## 生产阶段形成一次可沿用证据

在首次真实存档批准、启动实跑通过时，保留该次 Source、Native、Web、原合同、原始报告与执行账本。对应 producer 已支持封存依赖范围；启动生产命令用 `--scope-web <实际同版Web>` 指明目标。

依赖提供者用现有 `project_qa.py register --reviewed` 机制登记在项目内：存档 validator ID 为 `storage_dependency_scope.v1`，启动为 `startup_dependency_scope.v1`。AI 读取实际 helper 和依赖后登记，不要求用户逐次批准。文件路径相对项目，依赖真实读取点、请求原件、入口及注册运行器；不能凭 `complete:true` 或图片后缀编造完备性。具体函数与返回字段以随包 helper 的校验和测试为准。

没有范围记录时，状态是 `scope_required` 或 `scope_mapping_required`，继续补依赖映射和原始材料。不能结束在“无法写包”，也不能自动跑全量游戏解决范围问题。若确实缺少不可恢复、只能由用户提供的原件，先完成其他独立工作，再列具体缺项。

## 旧报告在改动后导入

先从已交付 ZIP、原始源码 ZIP 或保留构建恢复旧基线，核对原回执中的哈希。原回执、原始观察、旧执行 key 和工具来源保持原样。用下列命令只读核准旧观察并封存，不启动原存档 runner 或浏览器：

```sh
python3 <skills>/remake-core/scripts/storage_scoped_reuse.py prepare \
  --report <原存档批准.json> --project <工程> --native <当前Native> \
  --baseline-native <匹配原回执的旧Native> --baseline-source <旧Source>

python3 <skills>/remake-core/scripts/startup_scoped_evidence.py approve \
  --project <工程> --native <旧Native> --source <旧Source> --web <旧Web> \
  --contract <原启动合同.json> --target-native <当前Native> --target-web <当前Web>
```

注册前由当前语义校验器核准原始证据、原执行和旧基线；注册后冻结原件、实际依赖、运行器、环境与工具身份。消费过程只读核对，不再次执行依赖 helper。不能重写旧 `native_tree_sha256`、源码哈希、通过标志或观察时间。

## 局部改动后的确定动作

- 实际读取集、请求域、运行器、环境和原件未变：沿用原检查 key、原时间与结果。
- 已证明不在该检查依赖范围的图片、声音等字节变化：不启动这项检查。
- 存档消费者、首帧/加载/触摸资源、配置、运行器或真实条件变化：只让对应检查记录失效；修复后补验独立受影响项。
- 新文件、未闭合动态请求或未知归属：先补实际范围，不能用全量执行作默认兜底。
- 原证据丢失或损坏：先恢复冻结原件；恢复不了则只补该项所需的新证据，不把其他通过项作废。

当前 Source、Native、Web 的身份单独记在迁移见证中。最终交付使用当前 Web 身份核对试玩；原合同仍保留原 SHA。清单顶部识别原构建归属，不等于整张清单通过；只有得到独立范围批准的存档或启动行可沿用其原绑定，其他行各自核对。

最终实际 ZIP 的主包/分包/总体积、CRC、配置与文件一致性每次交付仍新读一次。该轻量文件核对不授权重跑美术、声音或玩法。
