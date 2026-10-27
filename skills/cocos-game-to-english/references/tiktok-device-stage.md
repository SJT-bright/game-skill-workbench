# 上传 TikTok 后的真机测试：不在本 Skill 范围（用户 2026-10-21）

本 Skill **严格不做上传 TikTok 之后的测试**：不出真机清单、不要求用户扫码或录屏、不分析手机录屏、不跑 `check_known_issues.py --stage device`，也不因为"没有真机结果"而停下或问用户。用户说"打包"、拿到试玩链接和上传 ZIP，就是本 Skill 的终点。

所有测试都在浏览器手机模拟（Ego Lite）里做，见[四个阶段](stage-flow.md)。重点保证：

- 进得去游戏、加载不卡住、慢网下不被误判超时（[启动加载计时](startup-loading-timing.md)）；
- 每个按钮点了都有反应（[按钮不能"点了没反应"](replay-and-input-checks.md#五按钮不能点了没反应)）；
- 所有广告流程的每种结果都在浏览器广告模拟里实际触发过（[广告要做到](loading-and-ad-prevention.md#三广告要做到)）。

浏览器模拟证明不了：真实 TikTok 广告能不能填充、平台审核、真实手机的性能和刘海屏、TikTok 容器本身的下载速度。汇报时如实写"浏览器模拟（Google Chrome iPhone touch）已通过，未做 TikTok 真机测试"，不说"TikTok 上已验证"。用户自己上传后发现问题再发回来时，按普通 bug 修复：先在浏览器里复现，修好后只重测受影响部分。
