# 按题材下载与长期复用（2026-10-25）

素材与 Skill 分开保存。Skill 带下载清单、作者、原始页面、授权和源文件 SHA256；音频默认存入当前用户 `~/GameAudioLibrary`，可设置 `GAME_AUDIO_LIB`，或由离线安装器登记自选本地目录。没有写死开发者用户名，不需要复制登录凭据。已拿到音效库ZIP时先按 [离线安装与分享](portable-library.md) 安装，日常无需联网。

安装依赖按 `scripts/setup.py`；随后在本 Skill 目录运行：

```sh
python3 scripts/sync_theme_library.py --list
python3 scripts/sync_theme_library.py --theme all
# 只补一个题材，例如：
python3 scripts/sync_theme_library.py --theme scifi
# 新游戏按题材下载并选音（工程已有selection时不替换）：
python3 scripts/audio_pipeline.py --project /path/to/game --theme beach --no-fetch
```

支持的题材以 `templates/theme-packs.json` 为准，包括 puzzle、cozy、cooking、party、arcade、cute、pet、winter、farm、scifi、space、mechanical、retro、platformer、fantasy、adventure、magic、beach、town、management、mystery、water、slime、rain。这是选音方向，不表示每个题材都已有完整独立套装；例如 cooking 当前先补轻松配乐，不能把它当成完整厨房拟音库。

每次新游戏先判断题材、动作材质和情绪，再将所需题材写进 needs.csv 的 tags（用 `|` 分隔），BGM保留 music 标签，例如 `music|beach|management`；关键词写具体乐器和节奏。下载对应题材后再选音。不能所有游戏共用一份默认 needs。听感冲突时换作曲者、配器或声音材质，不能只换文件名或变调冒充新素材。已有跨游戏使用记录降权继续生效。

下载脚本逐包暂存并检查源文件哈希、ZIP安全路径、ffprobe可解码性；通过后才入库。downloads/<pack>.json 保存本机文件校验回执。重复运行校验通过会跳过下载，丢失文件会补回；已修改的本地文件不会覆盖。失败会非零退出并列出具体包；不把失败说成下载完成。网络失败后重跑即可，无需清空库。运行期间不要同时启动另一个入库脚本。

更新 Skill 时保留 `GameAudioLibrary`，在本地重新运行同一命令，新清单新增包会下载，旧包校验后复用。清单不变无需联网下载。新电脑可离线安装库ZIP；只在主动从原站补库时需要联网，日常选音使用本机库即可。各人的游戏使用历史留在自己的 usage/，不随 Skill 分享。

音频来自原站，Skill ZIP不附整份音频库。CC0 与带版本 CC-BY 素材的原作者详情页见清单；CC-BY 音乐需保留作者、授权链接，并沿用项目 CREDITS 输出流程。同步成功不等于已经人工试听；实际游戏仍应确认循环点、情绪、响度及动作对应。

自动候选只使用质量分至少70的素材；较低分的原始素材保留供复核，不用响度加工冒充已经修复削波。BGM类型明确的12秒以上短循环可进入候选，实际循环衔接仍需试听。标签按词边界和驼峰拆词，不把来源网站名或 winter 等词中的字母片段误判成动作标签。


扩充清单区分厨房/日常物件、木石金属、道具、动物与生物、环境氛围，以及休闲经营、咖啡爵士、卡通派对、农场探索和益智配乐。按每首曲目/录音的来源族映射去重，不把编码格式、循环版和慢速版算成新增原曲。鸟鸣氛围与长拟音保持 ambience/sfx，不因超过10秒就当BGM。混合风格包不能整包标为可爱休闲；不明确的题材不填虚假标签。

`sync_theme_library.py --cache-dir <已下载源缓存> --offline` 只复用与清单 SHA256 完全一致的原站源文件；缺少或不匹配时失败，不联网补。普通同步仍走原站与同样的完整校验。重复同步会补回已验证素材缺失的授权行，不以下载回执代替 credits。
