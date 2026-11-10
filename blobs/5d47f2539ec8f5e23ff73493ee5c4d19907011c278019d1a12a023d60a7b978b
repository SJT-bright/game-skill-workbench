# 上传兼容与首页两入口定点修复（11.17.15，Saul 2026-11-08）

用在两种情况：平台上传或审核退回、提示兼容问题；用户要求“参照鸽鸽小羊已上传成功的修复方式处理上传兼容”，或要求修个人主页回访、桌面快捷方式。只改这几处，不重做游戏。

## 一、上传兼容：写包时自动修

写包入口 native 段的最后一步 `upload_compat`（`remake-core/scripts/tiktok_finalize_steps/upload_compat.py`）会自动处理下面三个文件，其余文件保持原字节：

| 文件 | 做什么 |
|---|---|
| `game.json` | 所有分包 root 补齐末尾 `/`（`subpackages` 和 `subPackages` 都查；root 对应的文件夹必须真实存在） |
| `game.js` | 指向本地文件的 `require(...)` 核对后补 `./` 和实际扩展名，不限数量（`adapter-min.js` → `./adapter-min.js`、`./main` → `./main.js`、`./src/settings` → `./src/settings.js`）。包里找不到的引用只列出来，不猜 |
| `project.config.json` | `setting` 里 `es6: false`、`minified: true`、`urlCheck: true`；删掉旧的 `postcss` 和 `newFeature`。AppID、项目名和其他字段不动，保留原缩进 |

- 保留本游戏的分包、引擎启动结构、AppID 和其他必要配置，不整份照搬参考包的文件。
- Cocos 3.x 只报告 `es6`，不改；另外三项照改。目前还没有 3.x 包用 `es6: false` 上传成功过。
- 校准对象是鸽鸽小羊上传成功的包：对一份标准 Cocos 2.4 构建，修完后的 `game.js`、`game.json` 与它逐字一致，`project.config.json` 内容一致。第二次运行不再改动。
- 写包报告里 `upload_compat` 一行就是这三项的修改清单。

## 二、个人主页回访和桌面快捷方式

| 要求 | 做法 |
|---|---|
| 点击直接跳转 | 在同一次点按的回调里调用 `startEntranceMission` / `addShortcut`。已领取、体力满、没进度时都不拦，两个按钮始终可点 |
| 没有多余文字 | 不弹说明、不出 toast、不在按钮上写 “+N”“Collected”。用途和奖励画在图标美术里；已领取只用游戏美术风格的角标（`shortcutClaimedNode` / `profileClaimedNode`，可选）。平台缺能力、取消、失败、超时都安静结束，可以再点 |
| 冷启动也查资格 | 首页和存档准备好后读进入参数：`center` 只查 `getEntranceMissionReward`，`desktop_shortcut` 只查 `getShortcutMissionReward` |
| 防止重复发奖 | 只有 `canReceiveReward === true`，并且奖励和“已领取”在同一次存档写入成功，才算发奖。重开游戏、重复回调都不再发 |
| 普通切回前台 | 来源不是 `center` / `desktop_shortcut` 时不查资格、不弹任何回访提示 |
| 奖励和存档规则 | 沿用本游戏原有的奖励种类、数额和存档方式 |

2.4 新游戏的 `HomeGrowthEntries` / `MissionFlow` 已经按上表实现（平台包 Node 测试覆盖）。游戏自己写入口的旧游戏，按上表改原来的代码，不必换整套平台包。

## 三、只查这些

- **改动的入口**：两个入口各点一次，确认先发出对应导航；从 `center` 和 `desktop_shortcut` 各冷启动一次，各只发一次奖；普通切回前台一次，零查询、零提示；重开后不再发奖。
- **必要的启动**：冷启动进首页、开始一局、点一次 Retry 能进。
- **最终 ZIP**：分包和体积，写包入口自动查。

不重跑美工、中文专项和无关玩法。只有写包入口的返工范围（`--rework-of auto`）显示别的文件也变了，才补查那一部分。`upload_compat` 改的是代码和配置，返工范围会要求声明受影响检查，这里声明“启动”和“首页两入口”即可。

## 四、交付

1. **修改清单**：逐个文件写改了什么，内容来自写包报告的 `upload_compat` 一行和入口改动。
2. **测试包**：写包入口出的 ZIP 和 `.sha256`。
3. **同版试玩链接**：用同一份 Web 和 Native 起的试玩链接。
