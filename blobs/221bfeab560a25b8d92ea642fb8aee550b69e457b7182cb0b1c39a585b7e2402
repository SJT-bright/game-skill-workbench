# 页面注册表 docs/logic/pages.json（总表 P19）

检查要的输入在做页面时就写进一份清单，其余的由脚本生成，**生成时必须用 `remake-core/scripts/page_registry.py make`，别手写** `docs/art/screens.json`、`docs/logic/flows.json` 的 page_flows、`docs/game_capabilities.json`、`qa/ad-regression.json` 的 `ad_entries` 和 `resume_play.pause_button`。

普查（2026-11-04）：检查输入缺失 20 条、输入被拒 29 条；割草广告入口清单为空、美人鱼没填暂停键，检查直接跳过。

## 什么时候写

- 每做一个页面或弹窗，就在 pages.json 加一行；开发版里 GameUIKit 每次 `popup()`、页面模板每次 `open()` 调用 `PageRegistry.record(...)`（`remake-core/assets/page-registry/PageRegistry.js`，钩子由 GameUIKit 那一批接上）。
- `ui_dump.js` 的每份 dump 带回 `pages`（运行时真打开过的页面）。`page_registry.py merge-dumps --project <工程> --dumps docs/test` 把它们标成 `seen_at_runtime`，并列出运行时打开了、pages.json 里却没有的页面（要补上再 make）。
- 改了页面就改 pages.json，再跑 `make`。`page_registry.py check` 发现生成文件被手改或过期就失败。

## 格式（schema pages.v1）

```json
{
  "schema": "pages.v1",
  "required_viewports": [{"name": "iphone14", "width": 390, "height": 844}, {"name": "iphone-se", "width": 375, "height": 667}],
  "adapter_js": {"request": "…看一次激励广告，发奖时调用 grant()…", "state": "…", "ready": "…", "exit": "…"},
  "no_ad_roles": {"revive": "这款没有失败状态"},
  "pages": [
    {"id": "home", "name": "首页", "kind": "home", "node": "Canvas/Home",
     "buttons": [{"id": "play", "node": "Canvas/Home/btn_play", "label": "PLAY", "to": "level"}]},
    {"id": "level", "name": "关卡", "kind": "gameplay", "pause": "Canvas/Level/HUD/btn_pause"},
    {"id": "result", "name": "结算", "kind": "popup", "close": "Canvas/Result/btn_close",
     "ad_entries": [{"id": "result_x2", "role": "double", "button": "Canvas/Result/btn_x2",
                     "states": [{"name": "after_win", "actions": [{"wait_node": "Canvas/Result/btn_x2"}]}]}]}
  ]
}
```

规则（`make` 当场拦，不等到检查）：至少一个 `kind: home`；弹窗必须有 `close`（节点路径，或 `{"none": "原因"}`）；关卡页必须有 `pause`（同上，英化固定入口第 9 项）；按钮的 `to` 要指向存在的页面；广告入口要有 `role`（double、revive、home_gift…）和 `button`；两种手机尺寸。`adapter_js` 只放广告回归要的几段页面 JavaScript（request、state、ready、exit 等），写一次。

## 生成什么

| 输出 | 内容 | 读它的检查 |
|---|---|---|
| `docs/art/screens.json` | 每页 id、name、kind、purpose；`runtime_verified` = 每页都 `seen_at_runtime` | art_check.py、audit_page_coverage.py、official_loading.py |
| `docs/logic/flows.json` | `page_flows`：每个跳页按钮一条、每个关闭键一条（测试员的状态保留）；新文件带 F01–F20 模板 | logic_check.py |
| `docs/game_capabilities.json` | pause_button、ad_entries、no_ad_roles（M 批 game_capabilities.py 的记录） | runtime_regression.py --capabilities |
| `qa/ad-regression.json` | ad_entries、resume_play.pause_button、ad_outcome.none（经 game_capabilities.fill_adapter）；手写的 request/state 等保留 | ad_regression.py、runtime_regression.py、check_package.py |
| `docs/logic/pages.generated.json` | 各输出的 SHA-256，`check` 用 | page_registry.py check |

## 检查侧

输入清单为空或缺项一律「未执行」（status `not_run`，退出 2），写明缺什么，不判通过、不静默跳过：`check_guard.inputs_not_run`（runtime_regression.py 的 `input_report`、check_package.py 的 `input_gate`、page_registry.py 都用它）。老游戏名单上的游戏只警告。状态词只认 `cocos-game-check/package-check/references/check-status.json`。
