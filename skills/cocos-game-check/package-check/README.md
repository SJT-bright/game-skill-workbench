# 最终Native/ZIP检查与成品增量出包

2026-11-11：当前完整制作的六标准广告与新增UI由两写包入口和最终ZIP共享门禁自动核，缺任何一类都不能以扩展顶替；检查用 `check_package.py --project <实际工程>`，规则及阶段范围见[六标准制作](../../remake-core/references/ad-standard-six.md)。

**接收他人包（2026-11-12）**：用户声明同事/别人发来的成品时，按[团队交接](../../remake-core/references/external-package-handoff.md)使用`game_handoff.py receive`，无原回执也能先接收、诊断与同版试玩；`intake_passed`不是`delivery_ready`。完整制作交接附测试ZIP、源码ZIP、试玩及`game_handoff.py export`证据ZIP，原writer回执可跨电脑按哈希核验。

**旧记录缺失不等于当前验收豁免（2026-11-12）**：按[消费者与交付约束](../../remake-core/references/startup-storage-consumer-gate.md)只补缺失的当前启动/存储证据。项目脚本只准备Native；最终writer与prepare_delivery不能被手工ZIP及体积/CLI绿灯替代。最终文件检查拒绝无同字节正式writer回执，失败继续修具体节点。

**拒绝后继续执行（2026-11-11）**。当轮已授权的写包与交付遇到失败时，读取原错误并修复具体节点，沿用未受影响的有效证据，再回原入口续跑到同版交付。只补验真实改动或缺证项；不要停在“ZIP 尚未生成”或等待用户再次说继续。

**测试包与同版试玩链接同发（用户 2026-11-07）**。只要交付含游戏测试包，同一回复须给出 ZIP 和已启动、可打开的同版手机试玩链接。跳过美术、重发、改名同样适用，用户明确说本次不用链接时按其指示。仅有 ZIP 只算出包，交付未完成。正式交付用 `prepare_delivery.py --preview-url` 回读手机入口与脚本，并用启动合同的 Web 指纹校验正在服务的快照，任何一项失败都不写交付回执。

接在用户已授权的出包或具体启动故障维护之后。新制作完整验收由[打包主入口](../package/README.md)选择范围；本入口不重做全游戏玩法、美术或所有历史事故。只读检查已有ZIP仍可单独执行。

**交付前无例外复查（含 TikTok CLI）**：每次要给测试包，先按[最终 ZIP 分包体积复查](references/fresh-upload-size.md)生成本次新回执；包括现成、旧、外来、同版重发和仅改名包。`prepare_delivery` 自动先跑这一项，其他 CI 仍可按原规则复用；用户仅索取已有文件时直接运行共享 `upload_size_gate.py`，不得只算 ZIP CRC/哈希。

1. 锁当前Native、目标App ID、稳定新ZIP路径、项目与证据。按[检查合同](references/check-contract.md)先核根入口、原生坐标、引擎/adapter、分包/场景、资源、未压缩体积；[检查顺序](references/gate-order-and-identity.md)先拒绝确定错误。
2. 按[资源与历史问题门禁](references/resource-and-reported-issues.md)，运行当前生产调用清单反查。清单漏项、未知动态域、固定问题历史缺失、未复验/失败/失效拒包。相关问题有效时仅核证据与依赖，不重新跑该运行器。
3. 验[同版Native启动恢复](../startup/references/final-package-startup-gate.md)，保留HOME→真实触摸→玩法变化及失败→Retry新请求→恢复。现有可信runner走[项目QA注册](../../remake-core/references/project-qa-registration.md)。
4. 轻量writer一次完成Native前检、必要启动、ZIP回读和原Native全字节；成功后不手动紧接着跑同一check_package。失败只修复对应链；具体WebP、触摸、资源路径等症状从[当前合同](../../remake-core/references/current-contracts.md)路由。
5. 最终交付对实际链接路径运行prepare_delivery；它核同版材料与字节，不再次执行相同启动runner。检查期间新增问题、清单/Native/证据变化拒绝发布。

```sh
python scripts/build_checked_zip.py --native <Native> --expected-app-id <ID> \
  --out <稳定新ZIP> --report <内部新报告.json> --project <工程> \
  --resource-manifest <当前资源清单.json> --startup-contract <当前启动合同.json> \
  --loading-recovery-runtime <当前恢复索引.json>
python scripts/prepare_delivery.py --zip <上述同一ZIP> --native <同一Native> \
  --expected-app-id <ID> --record <新交付回执.json> --project <工程> \
  --resource-manifest <同一资源清单.json> --startup-contract <同一启动合同.json> \
  --loading-recovery-runtime <同一恢复索引.json> \
  --preview-url <已启动的同版手机试玩URL>
```

已报告拖动/音频问题另按[实际交互与声音](references/drag-audio-postconditions.md)带当前trace。启动/资源故障缺同版运行证据不得只用Web可玩、ZIP CRC或旧CI覆盖；定位首错和实际依赖，不在错误版本上刷长测。共享代码在相邻remake-core/scripts，两个目录必须同级安装。

交稳定ZIP链接和必要说明，并给同版已启动的[固定手机预览](../../remake-core/references/user-phone-preview.md)。报告与故障原件留项目，不混进游戏包；不改变已批准美术，不自动上传平台。

同期广告模拟、制作统计、Credits和评价等规则按[当前合同](../../remake-core/references/current-contracts.md)选择相关正文，不复制事故全文。

先用手机试玩入口以 `--snapshot` 启动或复用同版服务。仅索取已有 ZIP 时仍须重跑分包体积复查，同时用 `python scripts/verify_delivery_preview.py --preview-url <链接> --web-sha256 <已与该ZIP绑定的Web构建指纹>` 核验试玩。Web 指纹来自同版构建记录，不能从待验链接倒填。两项通过后同一回复附两个链接。
