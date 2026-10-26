#!/usr/bin/env python3
"""从 Openverse 搜索并下载可商用音频（不用注册、不用登录）。

Openverse 聚合了 Freesound、Jamendo、Wikimedia 等多个来源，
接口直接返回授权，所以只下载 CC0 / PDM / CC-BY。

用法：
  python3 fetch_openverse.py "button click" --category sound_effect --n 15
  python3 fetch_openverse.py "cute game music loop" --category music --n 10
  python3 fetch_openverse.py "coin" --dry-run         # 只列出，不下载
  python3 fetch_openverse.py --batch ../templates/needs_casual_puzzle.csv
       # 按需求表里每个 ID 的关键词批量搜索

环境变量 OPENVERSE_TOKEN（可选）：注册后的 token，可提高频率上限。
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (RAW, classify_license, known_urls, read_csv, record_credit,  # noqa: E402
                    record_skip, safe_name)

API = "https://api.openverse.org/v1/audio/"
UA = {"User-Agent": "GameAudioSkill/1.0 (casual game audio sourcing)"}


def search(q: str, category: str | None, n: int, allow_sa: bool) -> list[dict]:
    lic = "cc0,pdm,by" + (",by-sa" if allow_sa else "")
    params = {"q": q, "license": lic, "page_size": min(max(n * 2, 10), 50)}
    if category:
        params["category"] = category
    headers = dict(UA)
    tok = os.environ.get("OPENVERSE_TOKEN")
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    r = requests.get(API, params=params, headers=headers, timeout=30)
    if r.status_code == 429:
        print("  ⚠️ 触发频率限制，等 60 秒后重试")
        time.sleep(60)
        r = requests.get(API, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json().get("results", [])


def download(item: dict, sub: str, seen: set[str], allow_sa: bool) -> Path | None:
    url = item.get("url") or ""
    page = item.get("foreign_landing_url") or url
    title = item.get("title") or "untitled"
    lic = f"{item.get('license', '')} {item.get('license_version', '')}".strip()
    ok, _, why = classify_license(f"cc {lic}" if item.get("license") not in ("cc0", "pdm") else lic,
                                  allow_sa=allow_sa)
    if not ok:
        record_skip(page, title, why)
        return None
    if not url or page in seen or url in seen:
        return None
    ext = "." + (item.get("filetype") or Path(url).suffix.lstrip(".") or "mp3")
    dest_dir = RAW / "openverse" / sub
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{safe_name(title)}_{item.get('id', '')[:8]}{ext}"
    try:
        with requests.get(url, headers=UA, timeout=60, stream=True) as r:
            r.raise_for_status()
            with dest.open("wb") as f:
                for chunk in r.iter_content(65536):
                    f.write(chunk)
    except Exception as e:  # 单个失败不影响其他
        record_skip(page, title, f"下载失败：{e}")
        return None
    record_credit(dest, f"openverse/{item.get('source', '')}", title,
                  item.get("creator") or "", lic, item.get("license_url") or "", page)
    seen.add(page)
    return dest


def run_query(q: str, category: str | None, n: int, dry: bool, allow_sa: bool,
              sub: str, delay: float) -> int:
    print(f"🔎 {q}  ({category or '全部'})")
    try:
        items = search(q, category, n, allow_sa)
    except Exception as e:
        print(f"  ❌ 搜索失败：{e}")
        return 0
    seen = known_urls()
    got = 0
    for it in items:
        if got >= n:
            break
        dur = (it.get("duration") or 0) / 1000
        line = f"  - {it.get('title')} | {dur:.1f}s | {it.get('license')} | {it.get('source')}"
        if dry:
            print(line + f" | {it.get('foreign_landing_url')}")
            got += 1
            continue
        p = download(it, sub, seen, allow_sa)
        if p:
            print(line + "  ✅")
            got += 1
            time.sleep(delay)
    return got


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", nargs="?")
    ap.add_argument("--category", choices=["music", "sound_effect"], default=None)
    ap.add_argument("--n", type=int, default=10, help="每个关键词最多下载几个")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-sa", action="store_true", help="允许 CC-BY-SA（默认不允许）")
    ap.add_argument("--batch", help="needs.csv：按每个 ID 的关键词搜索")
    ap.add_argument("--delay", type=float, default=1.0)
    a = ap.parse_args()

    total = 0
    if a.batch:
        for row in read_csv(Path(a.batch)):
            cat = "music" if row.get("type") in ("bgm", "jingle") else "sound_effect"
            kws = [k.strip() for k in (row.get("keywords") or "").split("|") if k.strip()]
            n = max(int(row.get("count") or 5) // max(len(kws[:2]), 1), 2)
            for kw in kws[:2]:  # 每个 ID 取前两个关键词，避免请求过多
                total += run_query(kw, cat, n, a.dry_run, a.allow_sa, row["id"], a.delay)
    elif a.query:
        sub = a.category or "misc"
        total = run_query(a.query, a.category, a.n, a.dry_run, a.allow_sa, sub, a.delay)
    else:
        ap.error("需要关键词或 --batch")
    print(f"\n完成：{total} 个{'候选' if a.dry_run else '文件'}。下一步：python3 build_index.py")


if __name__ == "__main__":
    main()
