#!/usr/bin/env python3
"""从 OpenGameArt 按标签和授权搜索、下载游戏音乐/音效（用 pip 包 oga）。

  pip3 install oga
  python3 fetch_oga.py --type music --tag happy --tag cute --n 8
  python3 fetch_oga.py --type sound --tag ui --n 10 --dry-run

只接受 CC0 / OGA-BY / CC-BY（CC-BY-SA、GPL 默认跳过）。下载前会逐个读取授权。
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import AUDIO_EXT, RAW, classify_license, known_urls, record_credit, record_skip  # noqa: E402

ROOT = RAW / "opengameart"


def oga(*args: str) -> str:
    r = subprocess.run(["oga", "--root-dir", str(ROOT), *args], capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:300])
    return r.stdout


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--type", choices=["music", "sound"], required=True)
    ap.add_argument("--tag", action="append", default=[], help="可重复；多个标签是“或”的关系")
    ap.add_argument("--license", default="cc0", help="传给 oga 的授权过滤，默认 cc0")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-sa", action="store_true")
    a = ap.parse_args()

    if not shutil.which("oga"):
        raise SystemExit("缺少 oga：pip3 install oga")
    ROOT.mkdir(parents=True, exist_ok=True)

    args = ["search", "--type", a.type, "--license", a.license]
    for t in a.tag:
        args += ["--tag", t]
    ids = [line.split()[0] for line in oga(*args).splitlines() if line.strip()]
    seen = known_urls()
    got = 0
    for asset_id in ids:
        if got >= a.n:
            break
        page = f"https://opengameart.org/content/{asset_id}"
        if page in seen:
            continue
        try:
            info = json.loads(oga("describe", asset_id, "--verbose").split("\n", 1)[-1])
        except Exception:
            info = {}
        lic = " / ".join(info.get("licenses", [])) or a.license
        ok, _, why = classify_license(lic, allow_sa=a.allow_sa)
        if not ok:
            record_skip(page, asset_id, why)
            continue
        print(f"  - {asset_id} | {lic} | {info.get('author', '')} | ♥{info.get('favorites', '?')}")
        if a.dry_run:
            got += 1
            continue
        before = {p for p in ROOT.rglob("*") if p.is_file()}
        try:
            oga("download", asset_id)
        except Exception as e:
            record_skip(page, asset_id, f"下载失败：{e}")
            continue
        new = [p for p in ROOT.rglob("*") if p.is_file() and p not in before]
        # zip 需要解压
        for z in [p for p in new if p.suffix.lower() == ".zip"]:
            from fetch_page import safe_extract
            new += safe_extract(z, z.parent / z.stem)
        n = 0
        for f in new:
            if f.suffix.lower() in AUDIO_EXT:
                record_credit(f, "opengameart", f"{asset_id} / {f.stem}", info.get("author", ""), lic, "", page)
                n += 1
        print(f"    ✅ {n} 个音频")
        got += 1
        time.sleep(1)
    print(f"\n完成：{got}。下一步：python3 build_index.py")


if __name__ == "__main__":
    main()
