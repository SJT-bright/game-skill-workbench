# 试玩链接交接前的真实鼠标检查（2026-11-16）

每次将游戏链接交给用户之前，必须用官方 Ego 独立空间中的真实浏览器鼠标输入完成：① 首页点击 PLAY/开始并观察实际进入玩法；② 按实际玩法点击、按住或拖动，观察发射、棋子移动、消除等业务变化。不得用 `Input.dispatchTouchEvent`、调用游戏函数、HTTP 200、桥接脚本存在或仅 `clicked` 回执代替。测试在同字节构建的新 origin 上执行，保护用户的存档和体力。Chrome 只作用户交接。

`serve_preview.py` 的用户交接模式（`--keep`、`--open`、`--idle-minutes 0`）和 `handoff_preview.py` 均调用 `preview_mouse_gate.py`。检查失败、未执行、没有 Ego、缺少操作计划或没有业务变化时阻止交接；不能把未测降为警告后给链接。只补本次开局与代表操作，不扩成全游戏回归。每次交接形成新观察，不用旧触摸通过或旧鼠标回执代替本次验证。

项目保存 `docs/playtest/mouse-plan.json`，或普通预览传 `--mouse-plan <计划.json>`。计划必须由当前 Agent 按真实画面和实际代码校准，表达式只读，不调用游戏控制方法或改存档。`ready` 包含加载和进入动画已结束、按钮已绑定；`started` 必须表示真正进入可操作玩法。`operation_state` 与 `operation_ok` 应绑定该操作的业务结果，不能只检查计时、随机动画或持续落砖的位置变化。

```json
{
  "schema": "preview_mouse_plan.v1",
  "ready": "!!cc.find('Canvas') && /* 实际首页可操作条件 */ true",
  "start": {"node": "Canvas/Home/BtnPlay"},
  "started": "/* 实际玩法已开始的只读条件 */ false",
  "operations": [{"node": "Canvas/Board/FirstPiece"}],
  "operation_state": "/* 实际发射数、棋盘或得分等只读结果 */ 0",
  "operation_ok": "/* 业务成功条件 */ false"
}
```

这只是字段示意，示例 false 条件不可用于签发通过。Cocos 节点目标转换为真实页面坐标；普通画布操作可使用 `{"click":[x,y]}`，拖动使用 `{"drag":[[x1,y1],[x2,y2]]}`，坐标以本次截图为准。最多 12 个代表动作，必要的界面等待可用动作的 `wait_ms`（不超过 3000 ms）。不能盲重试同一次失败动作。

内部服务恢复或手工续交链接，也先运行同一门禁：

```sh
python3 -B remake-core/scripts/preview_mouse_gate.py --url <隔离检查origin> --plan <项目计划> --out <新的结果.json>
```

结果保留真实鼠标事件计数、开局结果、操作前后业务状态、截图、计划和运行器哈希，以及测试空间关闭结果。物理手机与 TikTok 真广告继续单列，不能用浏览器鼠标通过宣称真机通过。

鼠标转触摸桥接必须在游戏脚本前保存浏览器原生 `Touch`、`TouchEvent`、`EventTarget.prototype.dispatchEvent` 和 `document.createEvent`，后续只用保存的引用。TikTok 适配器可能替换全局构造器、画布事件方法和 document 方法；游戏启动后再动态读取这些方法会丢失输入或生成假事件。普通网页、原生触摸、非画布广告控件、拖出画布与失焦取消必须保持原行为。桥接只注入 HTTP 预览响应，不写进游戏源码或平台 ZIP。
