# 隔离副本与输入证据

有本地 Web 导出、允许 QA 副本时使用。helper 只准备页面和接收被动日志，全部操作仍走 Ego Lite 官方 CLI。

```sh
python3 scripts/prepare_preview.py prepare \
  --web-root /absolute/path/to/exported-web \
  --entry game/index.html \
  --output /absolute/path/to/new-qa-run --start
```

复制到新目录，建立全源 SHA 清单，只在所选 HTML head 加观察器引用；其他脚本/引擎/场景/媒体字节相同。输出必须新建，服务仅127.0.0.1、新 origin 隔离原存档。server.json 是实际 URL/PID；events.jsonl 是浏览器 POST 的事件；instrumentation.json 绑定源/QA HTML。不要向交付包或游戏源注入。

观察器记 touch/pointer/mouse 阶段、触点 ID、client/screen、isTrusted、viewport/DPR/Canvas CSS rect、可见性和错误。移动限频、批量提交，不声称逐帧轨迹。监听 passive、不停止传播、不改存档、不调控制器。QA 标记 pointer-events:none、不参与布局。跨域 iframe 等另检查覆盖，不能称 Native 原始回调。

结束只停本轮 server.json 绑定的 PID，先核对命令/监听/目录。保留 HTML、清单、事件和截图后可删仅供测试的 Web 副本。

报告建议字段：target(name/url/version/source_manifest_sha256)、scope、mode、physical_device、environment(browser/viewport/dpr/device_type/canvas_css_rect/task_space_id/input_transport)、mobile_boot(configuration_order/reload_after_configuration/dom_capabilities/engine_capabilities/canvas_touch_listeners/status)、cases、unverified、unexpected_errors、overall。引擎能力和监听必须来自实际页面只读核验；未取得时标 unavailable，不复制预期值。

案例字段：id、status、expected、observed、Ego Lite actions、event_sequences、screenshots、pressed_feedback_observed。status 用 passed/failed/capability_unavailable/not_tested/blocked，不能模板默认通过。截图与事件用相对路径及 SHA；关键操作留 before/after。脚本核 SHA/结构，主 Agent 判读实际结果。

mode 允许 browser_touch_simulation/os_simulator/platform_remote_debug/physical_device。非物理手机 physical_device=false。只有声明范围全部实测且证据齐全才可 overall=passed，未测项仍显式列出。

clicked、HTTP200、截图存在、编译成功或测试替身均不等于触摸通过。UI 变了但无原始事件只报 UI 行为；DOM trusted touchstart/end 只证明浏览器收到输入，还需引擎触控能力、实际触摸监听/回调和业务状态变化。启动时仅注册鼠标的引擎可能靠兼容鼠标事件处理点按，不能把这种点按当引擎触屏通过。配置修正只证明环境已修正，拖动等案例仍须重新实测。多指、系统取消、真实广告没测就写没测。现有 Cocos 手机门禁仍需它自己的格式/绑定/真机证据。
