#!/usr/bin/env python3
"""从“不用登录”的网页直接抓取音频 / zip 下载链接（Kenney、OpenGameArt、Mixkit、
BigSoundBank、incompetech、soundimage 等）。

两种用法：
  1) 按素材包清单（templates/packs.csv）里的 key 下载：
       python3 fetch_page.py --pack kenney_interface
       python3 fetch_page.py --pack all --method page --priority 1   # 一次下载所有 1 级包
  2) 任意网页（必须自己给出授权）：
       python3 fetch_page.py --url https://opengameart.org/content/xxx --license CC0 --source opengameart

zip 会自动解压，只保留音频文件和授权说明。每个文件都记进 credits_master.csv。
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (AUDIO_EXT, RAW, classify_license, known_urls, read_csv,  # noqa: E402
                    record_credit, record_skip, safe_name)

HERE = Path(__file__).resolve().parent
PACKS = HERE.parent / "templates" / "packs.csv"
UA = {"User-Agent": "Mozilla/5.0 GameAudioSkill/1.1"}
LINK_RE = re.compile(r'''(?:href|src|data-src|data-audio)\s*=\s*["']([^"'#]+?\.(?:zip|wav|mp3|ogg|flac)(?:\?[^"']*)?)["']''',
                     re.I)
LICENSE_NAMES = re.compile(r"(licen[cs]e|readme|credits?)\.(txt|md|html?)$", re.I)


def find_links(page_url: str) -> list[str]:
    html = requests.get(page_url, headers=UA, timeout=30).text
    links = []
    for m in LINK_RE.finditer(html):
        u = urljoin(page_url, m.group(1).replace("&amp;", "&"))
        if u not in links:
            links.append(u)
    # 同一个文件同时有 wav 和 mp3 时，只要 wav（音质更好）
    stems = {}
    for u in links:
        stem = Path(urlparse(u).path).stem.replace("-preview", "")
        ext = Path(urlparse(u).path).suffix.lower()
        if stem not in stems or (ext in (".zip", ".wav") and stems[stem][1] not in (".zip", ".wav")):
            stems[stem] = (u, ext)
    return [v[0] for v in stems.values()]


def safe_extract(zpath: Path, dest: Path) -> list[Path]:
    """只解压音频和授权文本，防止路径穿越。"""
    out = []
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            name = info.filename
            if info.is_dir() or name.startswith("__MACOSX"):
                continue
            p = Path(name)
            if p.is_absolute() or ".." in p.parts:
                continue
            if p.suffix.lower() not in AUDIO_EXT and not LICENSE_NAMES.search(p.name):
                continue
            target = dest / Path(*[safe_name(x, 120) for x in p.parts])
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, target.open("wb") as f:
                f.write(src.read())
            out.append(target)
    return out


def fetch(page_url: str, license: str, source: str, pack_name: str, author: str,
          max_files: int, delay: float) -> int:
    ok, _, why = classify_license(license)
    if not ok:
        print(f"  ⛔ 授权不符合（{why}），跳过：{page_url}")
        record_skip(page_url, pack_name, why)
        return 0
    print(f"📦 {pack_name}  ←  {page_url}")
    try:
        links = find_links(page_url)
    except Exception as e:
        print(f"  ❌ 打不开页面：{e}")
        return 0
    if not links:
        print("  ⚠️ 页面上没找到直接下载链接（可能需要登录或点按钮）→ 改用 browser_fetch.py")
        return 0
    seen = known_urls()
    dest_root = RAW / safe_name(source) / safe_name(pack_name)
    dest_root.mkdir(parents=True, exist_ok=True)
    got = 0
    for u in links[:max_files]:
        if u in seen:
            continue
        fname = safe_name(Path(urlparse(u).path).name, 120)
        tmp = dest_root / fname
        try:
            with requests.get(u, headers=UA, timeout=120, stream=True) as r:
                r.raise_for_status()
                with tmp.open("wb") as f:
                    for chunk in r.iter_content(1 << 16):
                        f.write(chunk)
        except Exception as e:
            record_skip(u, pack_name, f"下载失败：{e}")
            continue
        if tmp.suffix.lower() == ".zip":
            files = safe_extract(tmp, dest_root / tmp.stem)
            tmp.unlink(missing_ok=True)
            n = 0
            for f in files:
                if f.suffix.lower() in AUDIO_EXT:
                    record_credit(f, source, f"{pack_name} / {f.stem}", author, license, "", u)
                    n += 1
            print(f"  ✅ {fname}：解压出 {n} 个音频")
            got += n
        else:
            record_credit(tmp, source, f"{pack_name} / {tmp.stem}", author, license, "", u)
            print(f"  ✅ {fname}")
            got += 1
        time.sleep(delay)
    return got


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pack", help="packs.csv 里的 key，或 all")
    ap.add_argument("--method", default="page", help="配合 --pack all，只下这种方式的包")
    ap.add_argument("--priority", type=int, default=9, help="配合 --pack all，只下优先级 ≤ 这个数的包")
    ap.add_argument("--type", choices=["sfx", "music", "both"], help="配合 --pack all 过滤类型")
    ap.add_argument("--url")
    ap.add_argument("--license")
    ap.add_argument("--source", default="web")
    ap.add_argument("--author", default="")
    ap.add_argument("--max-files", type=int, default=40)
    ap.add_argument("--delay", type=float, default=2.0)
    a = ap.parse_args()

    total = 0
    if a.pack:
        packs = read_csv(PACKS)
        if a.pack == "all":
            sel = [p for p in packs if p["method"] == a.method and int(p["priority"]) <= a.priority
                   and (not a.type or p["type"] in (a.type, "both"))]
        else:
            sel = [p for p in packs if p["key"] == a.pack]
            if not sel:
                raise SystemExit(f"packs.csv 里没有 {a.pack}")
        for p in sel:
            if p["method"] != "page":
                print(f"↪ {p['key']} 需要 {p['method']} 方式，见 sources.md")
                continue
            total += fetch(p["page_url"], p["license"], p["source"], p["key"], p.get("author", ""),
                           a.max_files, a.delay)
    elif a.url:
        if not a.license:
            ap.error("用 --url 时必须给 --license（先在页面上确认授权）")
        total = fetch(a.url, a.license, a.source, safe_name(urlparse(a.url).path.strip("/").split("/")[-1]),
                      a.author, a.max_files, a.delay)
    else:
        ap.error("需要 --pack 或 --url")
    print(f"\n完成：{total} 个音频。下一步：python3 build_index.py")


if __name__ == "__main__":
    main()
