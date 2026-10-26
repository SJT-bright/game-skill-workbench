# game.json 缺失与主动交付闭环

## 症状与判别

平台报 `Pack Error: packer.Pack: parseAndValidateOutputResult: unsuccess error_message=Cannot find game.json in the project source. Please make sure game.json exists.`，表明上传解析时未找到所需入口。不能仅凭这一句断言是哪种包，也不能认定所有此类错误都属于同一游戏。先锁定实际上传文件与最终交付链接的 SHA、游戏和版本；截图名称与当前项目不一致时保留区别。

按中央目录定位：

- 源码根 `project.json + assets`：用对应 Creator 导出目标 bytedance 小游戏；不是在源码根手写空 game.json。
- Web `index.html`：重建目标小游戏，改扩展名或补空 JSON 无效。
- 完整 Native 被外层目录包住：使用已验证 writer 从实际 Native 根内容出包，不压外层文件夹。
- Native 根确实缺文件/大小写错误/配置不可读：修源模板与目标构建，重建后核 `game.js`、`game.json`、`project.config.json` 及可达依赖。
- 本地根文件正确但平台仍拒绝：先核用户实际选择的文件是否与交付相同，再定位平台解析证据；不能反复发送同一个未经核对的旧包。

## 已有能力与新增缺口

共享 `verify_native_zip.py` 原本已有根文件、外层文件夹、Web误投、源码/桥接禁止、依赖和体积检查。最终文件检查要实际作用于发出的 ZIP，文档写了有检查并不能覆盖交付时链接错指。`prepare_delivery.py` 复用 `check_package.check` 对回复将引用的最终路径检查，要求与原构建全量一致，保存该路径/SHA/字节/链接。回执是本地生成证据，不能证明客户端点过下载或平台已接收；回复必须实际包含输出链接，不只生成回执。

## 本次过程与改正（2026-10-25）

1. 前次用户索取刚提供文件，回复了微信 temp/drag 源码 ZIP 链接，未复制到稳定位置；本次该源路径已不存在。这个链接不是可长期下载交付，也不是 TikTok Native 测试包。不能声称仍有原 ZIP 或把重新压缩的源码冒称原件。
2. 用户提供平台 game.json 缺失截图，要求主动发包也纳入测试包 Skill。截图的名称不能代替 ZIP 指纹，无法仅凭截图建立具体上传文件与本聊天原包的字节对应关系。
3. Grok 文字读取实际请求返回服务不可用，主 Agent 直接核对原图，保留失败记录，不称 Grok 成功。
4. 使用保留的 v5r17 隔离源码，由本机 Creator 2.4.15 从2.4.10工程导出 bytedance；沿用工程已有目标App ID，不改线上配置、不上传平台。首轮最终 writer 拒绝未压缩总量30,947,551字节，不能绕过；后续无损压缩保持逐像素一致，再走同一 writer。最终结果与版本指纹以项目回执为准，不把旧 r16 通过记录用作 r17 证据。
5. 当前测试包生成后主动在回复给出稳定交付目录的实际 ZIP；仅交当前正确包及必要说明。保留旧输入和用户试玩，不重跑无关CI或已确认美术检查。

## 可复用交付操作

```sh
python3 scripts/prepare_delivery.py --zip /stable/delivery/Game_TikTok_test_vN.zip --native /actual/build/bytedance --expected-app-id ID --record /project/evidence/delivery-vN.json \
  --project /project --resource-manifest /project/evidence/resources-vN.json \
  --startup-contract /project/evidence/startup-vN.json --loading-recovery-runtime /project/evidence/recovery-vN.json
```

内部回执留工程，不装进上传 ZIP。发送后若移动、替换或重建文件，重新执行并使用新回执；不能复用旧 SHA。若要同时交源码，用独立链接明确标识，主测试包链接仍指已验证的 Native ZIP。此步骤不自动授权平台上传或给别人发消息。
