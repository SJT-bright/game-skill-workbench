# 独立音效库：一次安装，随 Skill 持续复用

音效库与 Skill 分开交付。音效库 ZIP 含原始声音、相对路径索引、作者许可表、SHA256 清单、署名说明与独立安装器；Skill 本身不嵌入大量音频文件。收到新版 Skill 后保留同一个本地素材库。收到新版音效库 ZIP 时运行同一安装命令，安装器复用相同声音并合并新增声音，不重置个人的 `usage/`、`auth/` 或游戏选音记录。

## 收件人安装

先安装 Python 3.9 或更新版本。解压整个音效库 ZIP，进入其中的 `GameAudioLibrary` 文件夹：

```sh
python3 install_audio_library.py --library "$HOME/GameAudioLibrary"
```

Windows 在该文件夹打开命令提示符：

```bat
py -3 install_audio_library.py --library "%USERPROFILE%\GameAudioLibrary"
```

可以把 `--library` 换成自己的持久目录，包括含空格的路径。安装器不联网、不安装 Python 依赖、不要求 Skill 已安装；也可直接把音效库 ZIP 作为第一个参数传入。`--no-activate` 表示仅安装，不改库配置。

成功安装后，安装器写入 `~/.game-audio-library/library.json`：

```json
{"schema": 1, "library": "/absolute/path/to/GameAudioLibrary"}
```

Skill 路径优先级为 `GAME_AUDIO_LIB` 环境变量、上述配置、默认 `~/GameAudioLibrary`。如果以前设置过环境变量，需要更新或取消旧变量，新配置才会被采用。

安装前先核全包 SHA256、成员闭合、相对路径与许可一致性；发现已有同路径、不同内容的声音时拒绝覆盖。已有索引与授权表改变前备份至 `.metadata-backups/`；`credits_master.csv:file` 与 `index.csv:path` 都改为收件电脑的真实绝对路径，先写授权表再写索引，最后才启用配置。完整来源与许可记录保存于 `.installed-bundles/<content_id>/`。失败时不写成功回执或启用新配置；新拷入但尚未登记的原始文件可在重新运行时校验复用。

从已解压目录安装时，安装完成后该目录的索引已转换为本机绝对路径。如果要再给别人，转发原来的 ZIP；不要把安装后的目录重新当作未安装离线包。对于已通过 SHA 验证、相同版本的 ZIP，重复安装不会重写个人记录。

## 制作可转发的离线包

只有明确核实可作为原始素材库再分发的 CC0、带版本 CC-BY 素材可入包，保持原质量门槛 `quality >= 70`。可以商用游戏不自动等于可以把原始声音当素材库转发；Pixabay、Mixkit、Sonniss 等普通 royalty-free 描述不会被当作本功能的再分发许可。

准备人工核实的来源 allowlist JSON：

```json
{
  "schema": 1,
  "sources": [
    {
      "prefix": "raw/source/verified_pack",
      "license": "CC0",
      "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
      "page": "https://original-author.example/pack",
      "author": "Original author",
      "proof": ["https://original-author.example/pack#license"],
      "license_files": ["raw/source/verified_pack/License.txt"]
    }
  ]
}
```

`prefix` 必须是库内 `raw/` 下的目录或精确文件前缀；规则按最长前缀匹配。`license_files` 可省略，只接受同一来源前缀内的实际文本许可文件；不会复制包内其他程序、网页缓存或宣传图片。CC-BY 需写版本，例如 `CC-BY 4.0`，并配对应官方许可 URL。原作者提供完整署名文字时保存在来源规则或逐文件 credits 的 `attribution` 字段，导出时保留。

```sh
python3 scripts/library_bundle.py \
  --library "$HOME/GameAudioLibrary" \
  --sources /path/to/verified-sources.json \
  --out /path/to/GameAudioLibrary-YYYYMMDD-HHMMSS.zip
```

源文件按原字节导出，不合成、不改速、不重编码。只改变跨 Windows 不合法或大小写冲突的相对文件名；`audio_id`、`family_id`、`themes` 等索引列保持原值。导出排除未核再分发许可、质量不足或许可表不一致的素材，并在 JSON 回执列出排除数量。缺失选中原文件、SHA 过期、导出期间源字节或索引变化会失败，不发不完整包。

ZIP 验证 CRC、成员与清单、每个原始声音 SHA256 后才交付，同目录生成 `.zip.sha256`；既有 ZIP 与校验文件不覆盖。接收人需保留选中 CC-BY 声音的作者、来源及许可署名；在本地库中存在的其他素材仍可供其原授权用途使用，不会因未入便携包而删除。

## 小范围验证

```sh
python3 scripts/test_library_bundle.py
```

合同在临时目录检查重定位、真实授权读取/重建索引、独立标准库安装、重复/增量安装、配置选择优先级、Windows 文件名、旧文件冲突、坏 SHA、成员穿越/重复/符号链接、未核再分发许可和并发写入。合成 WAV 只用于隔离测试，不作为素材扩充或真实试听证据。
