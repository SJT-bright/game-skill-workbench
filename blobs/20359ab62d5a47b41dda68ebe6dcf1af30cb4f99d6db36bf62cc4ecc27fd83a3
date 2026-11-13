# 启动观察按实际依赖沿用

唯一节点是 `startup.native.renderer`，实际观察仍由已登记 runner 完成。写包和交付只消费它，不能为一个不相关资源变化再跑一次浏览器。

## 开工时一次准备，首个真实通过时自动冻结

在项目 QA manifest 的 `validators` 登记 `startup_dependency_scope.v1`。helper 使用项目相对路径、与实际 runner 同一份代码审核记录；用已有 `project_qa.py register --project <工程> --manifest <工程>/qa/manifest.json --reviewed` 登记，属于当前已授权制作工作，不新增用户确认。

该 helper 实现 `derive_startup_scope(*, native, source, web, proof, raw, binding, project)`。它必须从实际 runner 原始请求记录、资源 resolver 和测试场景推导完整请求域，覆盖入口、adapter、renderer、HOME、首次真实触控、Retry；核清网络请求、包内读取、分包、动态枚举与字体等真实消费者。不能只是返回 `complete:true` 或手填一组图片名单。

实际 renderer raw 引用 `startup_dependency_trace: {path, sha256}`；trace 保存原 `binding`、`native_tree_sha256`、`runner_sha256`、`coverage` 和 `native_reads`。helper 输出 `startup-read-scope.v1`，含同一个 `trace` 引用、`registered_runner`、`control_profile`、六项 `coverage`，以及 `inputs.native/source/web` 三组真实依赖路径。共用工具强制纳入所有代码、配置、原 proof 输入和实际读取资源，并保留所有文件名集合。未纳入的资源必须已由受审阅 helper 的实际请求域证明不属于这些已检查场景，不按后缀豁免。

首次实际启动检查命令带 `--scope-web <同版Web目录>`，真实通过、写出合同后自动执行 `startup_scoped_evidence.auto_approve`，冻结原观察、源码、Native、Web、原始回放和引用闭包。后续不需要重新执行 helper 或浏览器。缺少 scope/trace 时是当前启动节点的映射工作，由 AI 补齐实际依据；不能伪造请求记录，也不自动扩大成全量矩阵。

## 已通过旧游戏导入

```sh
python3 <skills>/remake-core/scripts/startup_scoped_evidence.py approve \
  --project <当前工程> --native <真实保留的旧Native> \
  --source <真实保留的旧源码> --web <真实保留的旧Web> \
  --contract <原启动合同.json> \
  --target-native <本轮实际Native> --target-web <本轮实际Web>
```

导入使用原 ledger 的实际冻结 renderer 输出，不凭通过字样。即使旧工具指纹不同，也用当前完整 renderer validator 重判原输出与保留旧产物；runner/profile/policy/环境和原始证据仍须匹配。原旧 key、工具指纹、时间与 JSON 不改，新 scope 批准独立保存。旧观察不满足当前语义、原件无法恢复或请求域未知时，定位到具体证据或映射，不把它记录为新游戏实测。

## 只读消费与修改路由

`consume(project, native, original_contract, current_binding=...)` 返回 `original_binding` 与实际当前源码/Native/Web 的 `current_binding`；只检查原冻结证据、当前依赖及身份。原合同 SHA 和原观察时间保持不变，同版试玩使用 `current_binding.web_tree_sha256`。原 proof 和当前产物不再靠伪造同一个整包 hash 对齐。

无关且已证明延后读取的资源只变字节时沿用；首帧实际读取图片、代码、配置、引擎、触摸链或运行条件变化，只让启动相关节点失效。新增/删除文件或未知归属先补映射，不全量兜底。同一当前候选已有真实失败时，失败优先于旧成功。scope 更新追加新的独立批准与历史指针，不覆盖旧观察。

此机制不把局部启动观察扩大成整款游戏、全部存档、真实广告或其他手机已通过。最终 ZIP 和同版试玩的实际文件检查仍逐次保留。
