---
name: cocos-tiktok-package-check
description: "已有Cocos Native或ZIP的最终文件检查、启动故障诊断及成品增量出包；新制作完整验收由打包主入口分流。"
---

# 最终Native/ZIP检查与成品增量出包

接在用户已授权的出包或具体启动故障维护之后。新制作完整验收由[打包主入口](../cocos-game-tiktok-package/SKILL.md)选择范围；本入口不重做全游戏玩法、美术或所有历史事故。只读检查已有ZIP仍可单独执行。

1. 锁当前Native、目标App ID、稳定新ZIP路径、项目与证据。按[检查合同](references/check-contract.md)先核根入口、原生坐标、引擎/adapter、分包/场景、资源、未压缩体积；[检查顺序](references/gate-order-and-identity.md)先拒绝确定错误。
2. 按[资源与历史问题门禁](references/resource-and-reported-issues.md)，运行当前生产调用清单反查。清单漏项、未知动态域、固定问题历史缺失、未复验/失败/失效拒包。相关问题有效时仅核证据与依赖，不重新跑该运行器。
3. 验[同版Native启动恢复](../cocos-game-to-english/references/final-package-startup-gate.md)，保留HOME→真实触摸→玩法变化及失败→Retry新请求→恢复。现有可信runner走[项目QA注册](../cocos-game-to-english/references/project-qa-registration.md)。
4. 轻量writer一次完成Native前检、必要启动、ZIP回读和原Native全字节；成功后不手动紧接着跑同一check_package。失败只修复对应链；具体WebP、触摸、资源路径等症状从[当前合同](../cocos-game-to-english/references/current-contracts.md)路由。
5. 最终交付对实际链接路径运行prepare_delivery；它核同版材料与字节，不再次执行相同启动runner。检查期间新增问题、清单/Native/证据变化拒绝发布。

```sh
python scripts/build_checked_zip.py --native <Native> --expected-app-id <ID> \
  --out <稳定新ZIP> --report <内部新报告.json> --project <工程> \
  --resource-manifest <当前资源清单.json> --startup-contract <当前启动合同.json> \
  --loading-recovery-runtime <当前恢复索引.json>
python scripts/prepare_delivery.py --zip <上述同一ZIP> --native <同一Native> \
  --expected-app-id <ID> --record <新交付回执.json> --project <工程> \
  --resource-manifest <同一资源清单.json> --startup-contract <同一启动合同.json> \
  --loading-recovery-runtime <同一恢复索引.json>
```

已报告拖动/音频问题另按[实际交互与声音](references/drag-audio-postconditions.md)带当前trace。启动/资源故障缺同版运行证据不得只用Web可玩、ZIP CRC或旧CI覆盖；定位首错和实际依赖，不在错误版本上刷长测。共享代码在相邻cocos-game-to-english/scripts，两个目录必须同级安装。

交稳定ZIP链接和必要说明，并给同版已启动的[固定手机预览](../cocos-game-to-english/references/user-phone-preview.md)。报告与故障原件留项目，不混进游戏包；不改变已批准美术，不自动上传平台。

同期广告模拟、制作统计、Credits和评价等规则按[当前合同](../cocos-game-to-english/references/current-contracts.md)选择相关正文，不复制事故全文。
