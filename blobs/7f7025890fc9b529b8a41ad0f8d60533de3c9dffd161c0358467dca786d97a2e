# 统一 Cocos 加载界面（用户 2026-10-26）

制作、英化、重塑、美工修改和成品维护中的所有开发者可控加载界面统一使用 Cocos 官方默认加载样式：官方 Cocos/Creator 标识、简洁中性背景和对应版本自带的加载/进度动画。不得使用游戏标题、游戏 Logo、角色、场景、主题插画、故事文案或自创的游戏专属 Loading。

覆盖冷启动、引擎后资源加载、分包/场景切换的完整加载页和失败重试页。局部按钮等待状态、正常游戏页面和宿主自身不可控制的加载画面不强行替换；不得宣称修改了宿主页面。

优先复用匹配 Creator 安装版的官方默认 splash 资源，单独随包携带，保持原始比例和透明边缘；不要生成仿制 Cocos Logo。此官方品牌界面是游戏主题美术/图片字规则的明确例外，不按游戏主题重新生图。Web 外壳、引擎内加载和 Native 资源加载使用同一视觉。

## 构建后处理与动画确认

制作与英化接线时检查实际生效的构建模板、定制 Web 模板、`post-build`/构建钩子和引擎内 Loading 场景。它们不得在导出后把游戏背景、标题 Logo、角色或自定义主题 spinner 写回加载页；只恢复 Web 的 `#splash`，却保留引擎后的游戏主题 Loading，也没有完成统一。修正在实际生成这些内容的源码/模板/后处理入口，不能只手改一次导出文件，让下一次构建又恢复旧画面。

使用当前 Creator 版本附带的官方加载资源与进度动画；版本未提供独立 spinner 时沿用其官方进度呈现，不为动画另造假 Cocos 标识。动画随真实加载推进，无法取得数值时使用不定进度；不得为了让动画可见而添加强制等待。需要观察短暂加载时，只在独立测试环境降低加载速度。

交试玩前从**全部后处理完成后的实际 Web/Native 候选**观察启动加载至首页的动态过程，以及本轮涉及的分包加载/Retry。确认 Cocos 官方画面覆盖实际等待阶段、动画/进度可更新、没有先闪游戏主题加载页再切 Cocos，也没有只贴静态 Cocos Logo 却保留游戏专属加载动画。沿用本轮启动/加载验证记录，不为此增加无关游戏CI；未运行的目标不写成已确认。

替换只改变呈现：保留真实加载任务、超时、取消、代次隔离、错误与可操作 Retry。进度必须来自真实进度；无法取得数值时用不定进度，不伪造百分比或固定延时。首页必需资源就绪且可操作后才撤下加载页，不因加载页统一而隐藏失败或提前 ready。

本轮修改范围内检查实际加载帧和失败重试帧，不只扫描文字；确认无游戏元素、官方标识无拉伸、Retry 有效，并确认首页→实际输入仍成立。已有成品仅复查受影响加载链，不重开已批准美术或完整CI。原始输入与旧包保留，新测试包仍走必要文件/配置/体积检查。


## 检查器实际入口

呈现例外由 [`official_loading.py`](../../../remake-core/scripts/official_loading.py) 共用核验，页面内容与亮度检查均消费同一证据。正常游戏页、局部等待和宿主页面不借此豁免；只改 `purpose`、页面名或通过标记无效。仍核原图清晰度、比例、可读性、越界、重叠及完整采集，缺证据不能通过。

沿用 `chrome_touch.py` 的 `dump_ui`：完整加载和失败重试均用 `kind: page`、`purpose: other`，每个精确状态覆盖原要求的两种手机比例，并登记 `docs/art/screens.json`。引擎前的默认 DOM `#splash` 或明确标识的 `[data-cocos-official-loading]` 由同一个 `ui_dump.js` 读取实际背景、Logo、文字和进度条；普通游戏 Canvas 不按 DOM splash 接管。此采集本身不证明官方身份。引擎内仍读真实 Cocos 节点。

采集后用下列命令绑定实际代码、包内官方原图、dump和配对截图。所有 `--source-file` 与 `--logo-asset` 都相对工程；`--dump` 可相对工程或用绝对路径。对正常与重试分别调用，多个同比例状态可重复 `--dump`：

```sh
python3 <Skill目录>/scripts/official_loading.py --project <工程> \
  --dump docs/test/<实际ui-dump文件>.json --logo-node <实际Logo节点路径> \
  --logo-asset assets/<官方原图>.png --creator-version <实际Creator版本> \
  --phase engine_resources --source-file assets/<实际加载实现>.ts
```

DOM默认背景 Logo 路径为 `DOMLoading/Logo`；普通IMG和Cocos节点用实际dump路径。冷启动用 `cold_start`、切场景用 `scene_switch`、失败重试用 `retry`；有当前 review binding 时同时传 `--binding review.json`。工具只记录来源与采集，不制造运行结果。采集后加载实现变更，重新采集并用 `--new-capture-set` 建新集合，旧记录自动按哈希归档，不能给旧截图换来源指纹。

只复查受影响加载链时运行实际入口：

```sh
python3 <Skill目录>/scripts/art_check.py --project <工程> \
  --loading-only --dumps <实际采集目录> --out <新报告目录>
```

它运行真实页面内容和亮度消费者，核已声明加载状态的双比例覆盖。输出 `audit_official_loading` 的 `stage: presentation`，**不是整套 ART-06、LOAD-03或功能验收通过**。完整美术仍走原 `art_check.py`；本例外不会删除加载帧、改变原阈值或重开已批准游戏美术。真实加载任务、进度、超时、取消、Retry、新旧请求隔离及首页真实输入仍由原启动/恢复门禁检查。

官方原图只按 [`official_loading_assets.json`](../../../remake-core/scripts/official_loading_assets.json) 中已核对的官方安装资源字节和版本识别，工程自行携带原图；不依赖维护者电脑的安装路径。新版本/不同官方资源须核其真实官方出处后扩充目录，未知来源不能填通过。最后仍看本轮实际加载帧和失败重试帧；自动像素检查不替代原人工观察。

原生图像上传后可能因 `CLEANUP_IMAGE_CACHE` 清空 `Image.src`，此后再读 `Image.width/height` 会得到零尺寸/NaN而让标识消失。上传前缓存尺寸，或使用上传后的稳定 Texture 尺寸；复验实际失败/Retry帧中的标识可见且节点尺寸有限，不能只凭图片已入包或 Web 标识可见放行。
