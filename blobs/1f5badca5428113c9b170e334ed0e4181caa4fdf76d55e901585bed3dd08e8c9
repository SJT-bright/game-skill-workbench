#!/usr/bin/env python3
"""一条命令跑完整个音频流程（AI 优先用这个，不要自己重写脚本）。Windows / macOS 通用。

默认（自动选择，最快）：
    python audio_pipeline.py --project <游戏工程>
  · 素材库是空的：先自动下载 1 级免登录素材包（Kenney、Mixkit 等，只第一次）
  · 生成/读取需求表 → 本地库找候选 → 候选不够自动上网补（Openverse；有 FREESOUND_API_KEY 时也用 Freesound）
  · 按得分自动选 → 加工 → 生成音频配置、docs/audio/credits.csv
  · 工程里没有 GameAudioManager 时，按 Cocos 版本（2.4 / 3.x）复制播放代码

用户想自己试听挑选时：
    python audio_pipeline.py --project <游戏工程> --listen      # 生成并打开试听页
    （试听页导出 selection.csv 后，再运行一次不带 --listen 的命令即可接入）

其他：--redo 重新选；--no-fetch 不上网补；--style retro 像素/复古风；--engine 2.4|3.x 手动指定版本。
中间文件放在 <工程>/audio_work/：needs.csv、candidates.csv、selection.csv、audition/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import LIB, RAW, INDEX, AUDIO_EXT, detect_engine, have_ffmpeg, need_ffmpeg, open_file, read_csv, write_csv  # noqa: E402
from audio_identity import identity, family

TEMPLATE = HERE.parent / "templates" / "needs_casual_puzzle.csv"
CODE = {"3.x": (HERE.parent / "cocos3x", ("GameAudioManager.ts", "GameAudioButton.ts")),
        "2.4": (HERE.parent / "cocos24", ("GameAudioManager.js", "GameAudioButton.js"))}


def run(*args: str, cwd: Path) -> int:
    print("\n$ python " + " ".join(Path(args[0]).name if i == 0 else x for i, x in enumerate(args)))
    return subprocess.run([sys.executable, *args], cwd=cwd).returncode


def run_checked(*args: str, cwd: Path) -> None:
    code = run(*args, cwd=cwd)
    if code:
        raise SystemExit(f'{Path(args[0]).name} 失败（退出码 {code}）；已停止，不使用旧候选或旧选择继续加工')


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda:source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def commit_usage(proj: Path, needs: Path, selection: Path, receipt: Path, expected: dict) -> Path | None:
    """Record only sources whose current processing receipt and outputs verify."""
    try:
        doc = json.loads(receipt.read_text(encoding='utf-8'))
        if doc.get('schema') != 1 or doc.get('success') is not True or doc.get('project') != str(proj):
            raise ValueError('加工回执未成功或工程不匹配')
        for label, path in (('needs_sha256', needs), ('selection_sha256', selection)):
            if doc.get(label) != expected[label] or file_sha256(path) != expected[label]:
                raise ValueError('加工回执输入已变化：' + label)
        requested = {(row['id'], str(Path(row['path']).expanduser().resolve())) for row in read_csv(selection)}
        actual, output_owners = set(), {}
        sources = doc.get('sources')
        required = {row['id'] for row in read_csv(needs) if str(row.get('required', '')).lower() in {'yes', '1', 'true', '是'}}
        if not isinstance(sources, list):
            raise ValueError('加工回执缺少成功来源列表')
        if not sources:
            if required:
                raise ValueError('必需音频没有成功输出')
            print('· 本轮可选音频没有成功输出，未写使用历史')
            return None
        for entry in sources:
            key = (entry['id'], str(Path(entry['source_path']).expanduser().resolve()))
            if key not in requested:
                raise ValueError('加工回执包含未选择的来源')
            outputs, hashes = entry.get('outputs'), entry.get('output_sha256')
            if not isinstance(outputs, list) or not outputs or not isinstance(hashes, dict):
                raise ValueError('加工回执缺少实际输出与校验')
            for relative in outputs:
                path = (proj / relative).resolve()
                path.relative_to(proj)
                if Path(relative).is_absolute() or not path.is_file() or hashes.get(relative) != file_sha256(path):
                    raise ValueError('加工输出缺失、越界或内容不匹配：' + relative)
                if relative in output_owners and output_owners[relative] != key:
                    raise ValueError('不同来源宣称同一个加工输出：' + relative)
                output_owners[relative] = key
            actual.add(key)
        if not required <= {key[0] for key in actual}:
            raise ValueError('必需音频没有成功输出')
        by_path = {str(Path(row['path']).expanduser().resolve()):row for row in read_csv(INDEX)}
        if any(path not in by_path for _, path in actual):
            raise ValueError('成功来源已不在当前库索引，未记录历史')
        rows = [by_path[path] for path in sorted({path for _, path in actual})]
        payload = {'schema':2, 'project':str(proj), 'at':time.time(),
                   'paths':sorted({path for _, path in actual}),
                   'asset_ids':sorted({identity(row) for row in rows}),
                   'family_ids':sorted({family(row) for row in rows}),
                   'packs':sorted({row.get('source', '') + '/' + row.get('pack', '') for row in rows})}
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit('加工结果核验失败，不写使用历史：' + str(error))
    usage = LIB / 'usage'
    usage.mkdir(parents=True, exist_ok=True)
    record = usage / (hashlib.sha256(str(proj).encode()).hexdigest() + '.json')
    temp = record.with_suffix('.tmp')
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(record)
    return record


def install_code(proj: Path, engine: str) -> None:
    src_dir, names = CODE[engine]
    dst_dir = proj / "assets" / "scripts" / "audio"
    dst_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
        dst = dst_dir / name
        if dst.exists():
            print(f"· 已有 {dst.relative_to(proj)}，不覆盖")
            continue
        shutil.copy2(src_dir / name, dst)
        print(f"📄 已复制 {dst.relative_to(proj)}（Cocos {engine}）")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--style", choices=["cute", "retro", "any"], default="cute")
    ap.add_argument("--theme", help="Select a game theme (local-first); see sync_theme_library.py --list")
    ap.add_argument("--listen", action="store_true", help="生成试听页让用户挑（默认自动选）")
    ap.add_argument("--no-fetch", action="store_true", help="全流程只用本地库；空库和缺组件时停止，不下载或安装")
    ap.add_argument("--redo", action="store_true", help="忽略已有的 selection.csv，重新选")
    ap.add_argument("--packs", action="store_true", help="强制重新下载 1 级免登录素材包")
    ap.add_argument("--engine", choices=["auto", "2.4", "3.x"], default="auto")
    ap.add_argument("--no-code", action="store_true", help="不复制播放代码（工程已有合格的音频管理时用）")
    a = ap.parse_args()
    if a.no_fetch and a.packs:
        ap.error("--no-fetch 与 --packs 不能同时使用")
    if a.no_fetch and not read_csv(INDEX) and not any(path.suffix.lower() in AUDIO_EXT for path in RAW.rglob("*")):
        raise SystemExit("本地音效库为空；--no-fetch 不下载。请先安装本地音效库压缩包并建立索引")
    if a.no_fetch and not have_ffmpeg():
        raise SystemExit("本地缺少 ffmpeg/ffprobe；--no-fetch 不自动安装，请先完成本地依赖准备")

    proj = Path(a.project).expanduser().resolve()
    engine = detect_engine(proj) if a.engine == "auto" else a.engine
    need_ffmpeg()   # 没装会自动装，用户不用单独做准备
    work = proj / "audio_work"
    work.mkdir(parents=True, exist_ok=True)
    needs = work / "needs.csv"
    if not needs.exists():
        shutil.copy(TEMPLATE, needs)
        print(f"📝 已复制需求模板到 {needs}——AI 按玩法删掉用不到的行、补上缺的行后再继续")

    s = lambda name: str(HERE / name)  # noqa: E731
    selection = work / "selection.csv"
    cand = work / "candidates.csv"
    dl = Path.home() / "Downloads" / "selection.csv"
    # 试听页刚导出的结果在“下载”文件夹里：自动取回
    if not selection.exists() and dl.exists() and cand.exists() and dl.stat().st_mtime > cand.stat().st_mtime:
        shutil.move(str(dl), str(selection))
        print("📥 已从下载文件夹取回 selection.csv")
    if a.redo:
        selection.unlink(missing_ok=True)

    if not selection.exists():
        if a.theme:
            manifest = json.loads((HERE.parent / 'templates/theme-packs.json').read_text())
            if a.theme not in {t for p in manifest['packs'] for t in p['themes']}:
                raise SystemExit('Unknown --theme; use sync_theme_library.py --list')
            if not a.no_fetch:
                run_checked(s('sync_theme_library.py'), '--theme', a.theme, '--no-index', cwd=work)
            records = read_csv(needs)
            for row in records:
                row['themes'] = '|'.join(dict.fromkeys(filter(None, (row.get('themes', '')+'|'+a.theme).split('|'))))
                if row.get('type') == 'bgm':
                    row['tags'] = '|'.join(dict.fromkeys(filter(None, (row.get('tags','')+'|music|'+a.theme).split('|'))))
            if records: write_csv(needs, records, list(records[0]))
        if a.packs or (not a.no_fetch and not read_csv(INDEX)):
            print("📦 素材库还是空的：先下载 1 级免登录素材包（只需一次，之后所有游戏共用）")
            run_checked(s("fetch_page.py"), "--pack", "all", "--method", "page", "--priority", "1", cwd=work)
        run_checked(s("build_index.py"), cwd=work)
        run_checked(s("search_index.py"), "--needs", str(needs), "--out", "candidates.csv", "--style", a.style, "--project", str(proj), cwd=work)
        missing = work / "needs_missing.csv"
        if not a.no_fetch and missing.exists():
            run_checked(s("fetch_openverse.py"), "--batch", str(missing), cwd=work)
            if os.environ.get("FREESOUND_API_KEY"):
                run_checked(s("fetch_freesound.py"), "--batch", str(missing), cwd=work)
            missing.unlink(missing_ok=True)
            run_checked(s("build_index.py"), cwd=work)
            run_checked(s("search_index.py"), "--needs", str(needs), "--out", "candidates.csv", "--style", a.style, "--project", str(proj), cwd=work)

        if a.listen:
            run_checked(s("audition.py"), "--candidates", "candidates.csv", "--needs", str(needs), cwd=work)
            open_file(work / "audition" / "index.html")
            print("\n👉 在试听页选好后点“导出 selection.csv”（存到“下载”文件夹），然后再运行一次不带 --listen 的命令。")
            return
        run_checked(s("audition.py"), "--candidates", "candidates.csv", "--needs", str(needs), "--auto", cwd=work)

    receipt = work / 'process-result.json'
    expected = {'needs_sha256':file_sha256(needs), 'selection_sha256':file_sha256(selection)}
    receipt.unlink(missing_ok=True)  # A failed command cannot reuse an earlier success receipt.
    run_checked(s('process_audio.py'), '--needs', str(needs), '--selection', str(selection),
                '--project', str(proj), '--engine', engine, '--receipt', str(receipt), cwd=work)
    commit_usage(proj, needs, selection, receipt, expected)
    if not a.no_code:
        install_code(proj, engine)
    print("\n✅ 音频已接入（自动选择，建议有空时试听确认）。按 SKILL.md 的接入表调用播放方法，再按验收清单检查。")


if __name__ == "__main__":
    main()
