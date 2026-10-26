#!/usr/bin/env python3
"""从 Freesound 搜索并下载 CC0 音效（只要 CC0，最省心）。

需要一个免费 API key：https://freesound.org/apiv2/apply/
  export FREESOUND_API_KEY=你的key

默认下载“高音质 MP3 试听版”（preview-hq-mp3，约 128kbps），
对小游戏音效完全够用，而且不需要 OAuth 登录。
需要原始 WAV 时，在浏览器登录 Freesound 手动下载即可。

用法：
  python3 fetch_freesound.py "bubble pop" --n 10
  python3 fetch_freesound.py "ui click" --max-dur 1.5 --dry-run
  python3 fetch_freesound.py --batch ../templates/needs_casual_puzzle.csv
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RAW, known_urls, read_csv, record_credit, record_skip, safe_name  # noqa: E402

API = "https://freesound.org/apiv2/search/text/"
FIELDS = "id,name,username,license,url,duration,previews,avg_rating,num_downloads"


def search(key: str, q: str, n: int, max_dur: float) -> list[dict]:
    params = {
        "query": q,
        "filter": f'license:"Creative Commons 0" duration:[0 TO {max_dur}]',
        "fields": FIELDS,
        "sort": "rating_desc",      # 评分高的优先，质量更稳
        "page_size": min(max(n * 2, 10), 150),
        "token": key,
    }
    r = requests.get(API, params=params, timeout=30)
    if r.status_code == 429:
        print("  ⚠️ 频率限制，等 60 秒")
        time.sleep(60)
        r = requests.get(API, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("results", [])


def run_query(key: str, q: str, n: int, max_dur: float, dry: bool, sub: str, delay: float) -> int:
    print(f"🔎 {q}")
    try:
        items = search(key, q, n, max_dur)
    except Exception as e:
        print(f"  ❌ 搜索失败：{e}")
        return 0
    seen = known_urls()
    got = 0
    for it in items:
        if got >= n:
            break
        page = it.get("url", "")
        if page in seen:
            continue
        info = f"  - {it.get('name')} | {it.get('duration', 0):.2f}s | ★{it.get('avg_rating', 0):.1f} | {page}"
        if dry:
            print(info)
            got += 1
            continue
        mp3 = (it.get("previews") or {}).get("preview-hq-mp3")
        if not mp3:
            record_skip(page, it.get("name", ""), "没有试听文件")
            continue
        dest_dir = RAW / "freesound" / sub
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{safe_name(Path(it.get('name', 'x')).stem)}_{it['id']}.mp3"
        try:
            data = requests.get(mp3, timeout=60).content
            dest.write_bytes(data)
        except Exception as e:
            record_skip(page, it.get("name", ""), f"下载失败：{e}")
            continue
        record_credit(dest, "freesound", it.get("name", ""), it.get("username", ""),
                      "CC0", "https://creativecommons.org/publicdomain/zero/1.0/", page)
        print(info + "  ✅")
        got += 1
        time.sleep(delay)
    return got


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", nargs="?")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--max-dur", type=float, default=3.0, help="音效最长秒数")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--batch")
    ap.add_argument("--delay", type=float, default=1.0)
    a = ap.parse_args()

    key = os.environ.get("FREESOUND_API_KEY")
    if not key:
        raise SystemExit("缺少 FREESOUND_API_KEY。申请：https://freesound.org/apiv2/apply/")

    total = 0
    if a.batch:
        for row in read_csv(Path(a.batch)):
            if row.get("type") != "sfx":
                continue  # Freesound 只用来补音效
            kws = [k.strip() for k in (row.get("keywords") or "").split("|") if k.strip()]
            for kw in kws[:2]:
                total += run_query(key, kw, 4, a.max_dur, a.dry_run, row["id"], a.delay)
    elif a.query:
        total = run_query(key, a.query, a.n, a.max_dur, a.dry_run, "misc", a.delay)
    else:
        ap.error("需要关键词或 --batch")
    print(f"\n完成：{total}。下一步：python3 build_index.py")


if __name__ == "__main__":
    main()
