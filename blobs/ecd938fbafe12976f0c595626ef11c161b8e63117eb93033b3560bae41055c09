#!/usr/bin/env python3
"""用浏览器（Playwright）在需要登录的网站搜索、下载：Pixabay、itch.io、ZapSplat、
99Sounds(Gumroad)、Freesound 原始文件等。

登录只做一次：浏览器资料保存在 ~/GameAudioLibrary/auth/<site>/，之后自动保持登录。

  python3 browser_fetch.py login pixabay            # 弹出浏览器，你手动登录，回终端按回车
  python3 browser_fetch.py search pixabay-sfx "bubble pop" --n 20
  python3 browser_fetch.py search pixabay-music "cute game loop"
  python3 browser_fetch.py search itch "cute music pack"
       # 搜索结果写到 ~/GameAudioLibrary/candidates_web.csv（标题 + 链接），先给用户挑
  python3 browser_fetch.py download <页面链接> [<页面链接> ...] --site pixabay
  python3 browser_fetch.py download --from-csv picked.csv   # 列 url,site

规则：每次下载间隔 5 秒；单次最多 30 个；itch.io 会自动读取页面上的授权，
不可商用的会跳过。网站改版导致按钮找不到时，脚本会截图到 auth/debug/，
由 AI 根据截图修改 PRE_CLICK / DL_TEXT 里的按钮文字。
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote, urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (AUTH, LIB, RAW, append_csv, classify_license, known_urls,  # noqa: E402
                    read_csv, record_credit, record_skip, safe_name)

try:
    from playwright.sync_api import TimeoutError as PWTimeout
    from playwright.sync_api import sync_playwright
except ImportError:
    raise SystemExit("缺少 playwright：运行 python scripts/setup.py --browser")

SITES = {
    "pixabay": {"login": "https://pixabay.com/accounts/login/",
                "license": "Pixabay Content License"},
    "itch": {"login": "https://itch.io/login", "license": None},          # 从页面读取
    "zapsplat": {"login": "https://www.zapsplat.com/login/",
                 "license": "ZapSplat Standard License (attribution: zapsplat.com)"},
    "freesound": {"login": "https://freesound.org/home/login/", "license": None},
    "gumroad": {"login": "https://gumroad.com/login", "license": "Royalty-free (99Sounds)"},
}
SEARCH_URL = {
    "pixabay-sfx": "https://pixabay.com/sound-effects/search/{q}/",
    "pixabay-music": "https://pixabay.com/music/search/{q}/",
    "itch": "https://itch.io/search?q={q}",
    "itch-free-music": "https://itch.io/game-assets/free/tag-music",       # 浏览，忽略关键词
    "itch-free-sfx": "https://itch.io/game-assets/free/tag-sound-effects",
    "zapsplat": "https://www.zapsplat.com/?s={q}",
}
RESULT_LINK = {
    "pixabay-sfx": re.compile(r"/sound-effects/[\w-]+-\d+/?$"),
    "pixabay-music": re.compile(r"/music/[\w-]+-\d+/?$"),
    "itch": re.compile(r"^https://[\w-]+\.itch\.io/[\w-]+/?$"),
    "itch-free-music": re.compile(r"^https://[\w-]+\.itch\.io/[\w-]+/?$"),
    "itch-free-sfx": re.compile(r"^https://[\w-]+\.itch\.io/[\w-]+/?$"),
    "zapsplat": re.compile(r"/music/[\w-]+/?$|/sound-effect-category/"),
}
# 先点这些按钮进入下载页（不期待下载），再点 DL_TEXT 里的按钮下载。网站改版时改这里。
PRE_CLICK = {
    "itch": ["Download Now", "No thanks, just take me to the downloads"],
    "gumroad": ["I want this!"],
}
DL_TEXT = {
    "pixabay": ["Free Download", "Download"],
    "itch": ["Download"],
    "zapsplat": ["Download WAV", "Download MP3", "Download"],
    "freesound": ["Download"],
    "gumroad": ["Download"],
}
CANDIDATES = LIB / "candidates_web.csv"


def ctx(p, site: str, headless: bool = False):
    profile = AUTH / site
    profile.mkdir(parents=True, exist_ok=True)
    kw = dict(user_data_dir=str(profile), headless=headless, accept_downloads=True,
              viewport={"width": 1280, "height": 900})
    try:
        return p.chromium.launch_persistent_context(channel="chrome", **kw)  # 优先用本机 Chrome，更不容易被拦
    except Exception:
        return p.chromium.launch_persistent_context(**kw)


def site_of(key: str) -> str:
    return key.split("-")[0]


def cmd_login(site: str) -> None:
    with sync_playwright() as p:
        c = ctx(p, site)
        page = c.new_page()
        page.goto(SITES[site]["login"])
        input(f"在弹出的浏览器里登录 {site}，完成后回到这里按回车…")
        c.close()
    print(f"✅ 登录状态已保存：{AUTH / site}")


def cmd_search(key: str, q: str, n: int) -> None:
    site = site_of(key)
    url = SEARCH_URL[key].format(q=quote(q.replace(" ", "+") if key.startswith("pixabay") else q))
    with sync_playwright() as p:
        c = ctx(p, site)
        page = c.new_page()
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(3):  # 往下滚，加载更多结果
            page.mouse.wheel(0, 4000)
            page.wait_for_timeout(1200)
        rows, seen = [], set()
        for a in page.query_selector_all("a[href]"):
            href = a.get_attribute("href") or ""
            full = urljoin(page.url, href)
            if not RESULT_LINK[key].search(full) or full in seen:
                continue
            seen.add(full)
            title = (a.inner_text() or "").strip().split("\n")[0][:80] or Path(full.rstrip("/")).name
            rows.append({"query": q, "site": site, "title": title, "url": full})
            if len(rows) >= n:
                break
        c.close()
    for r in rows:
        append_csv(CANDIDATES, r, ["query", "site", "title", "url"])
        print(f"  - {r['title']}  {r['url']}")
    print(f"\n{len(rows)} 条已写入 {CANDIDATES}。挑好后：python3 browser_fetch.py download --from-csv picked.csv")


def read_itch_license(page) -> str:
    """itch.io 页面的 More information 区域里有 'Asset license' 一行；没有就读简介。"""
    try:
        more = page.query_selector("text=More information")
        if more:
            more.click()
            page.wait_for_timeout(500)
        cell = page.query_selector("tr:has(td:text-is('Asset license')) td:nth-child(2)")
        if cell:
            return cell.inner_text().strip()
    except Exception:
        pass
    body = (page.inner_text("body") or "").lower()
    for kw in ["cc0", "creative commons zero", "public domain", "royalty free", "royalty-free",
               "free for commercial", "commercial use", "cc-by", "cc by", "attribution"]:
        if kw in body:
            if "non-commercial" in body or "non commercial" in body or "personal use only" in body:
                return "non-commercial (页面提到非商用)"
            return kw
    return ""


def click_and_download(page, site: str, dest: Path) -> list[Path]:
    for text in PRE_CLICK.get(site, []):
        el = page.get_by_text(text, exact=False)
        if el.count():
            try:
                el.first.click(timeout=5000)
                page.wait_for_timeout(2500)
            except Exception:
                pass
    saved: list[Path] = []
    for text in DL_TEXT[site]:
        btns = page.get_by_role("link", name=re.compile(text, re.I))
        if btns.count() == 0:
            btns = page.get_by_role("button", name=re.compile(text, re.I))
        for i in range(min(btns.count(), 10)):
            try:
                with page.expect_download(timeout=20000) as dl:
                    btns.nth(i).click()
                d = dl.value
                target = dest / safe_name(d.suggested_filename, 120)
                d.save_as(str(target))
                saved.append(target)
                time.sleep(2)
            except PWTimeout:
                page.wait_for_timeout(1000)
            except Exception:
                pass
        if saved:
            break
    return saved


def cmd_download(urls: list[tuple[str, str]], license_override: str | None, max_n: int) -> None:
    seen = known_urls()
    done = 0
    by_site: dict[str, list[str]] = {}
    for u, s in urls:
        by_site.setdefault(s, []).append(u)
    with sync_playwright() as p:
        for site, lst in by_site.items():
            c = ctx(p, site)
            page = c.new_page()
            for url in lst:
                if done >= max_n:
                    print(f"⏸ 已到单次上限 {max_n}，剩下的下次再下")
                    break
                if url in seen:
                    print(f"  · 已下载过：{url}")
                    continue
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(2500)
                title = safe_name(page.title().split("|")[0].split(" by ")[0])
                lic = license_override or SITES[site]["license"] or (read_itch_license(page) if site == "itch" else "")
                ok, _, why = classify_license(lic)
                if not ok:
                    print(f"  ⛔ {title}：{why}")
                    record_skip(url, title, why)
                    continue
                dest = RAW / site / title
                dest.mkdir(parents=True, exist_ok=True)
                files = click_and_download(page, site, dest)
                if not files:
                    dbg = AUTH / "debug"
                    dbg.mkdir(parents=True, exist_ok=True)
                    shot = dbg / f"{title}.png"
                    page.screenshot(path=str(shot), full_page=True)
                    print(f"  ❌ 没找到下载按钮，截图：{shot}")
                    continue
                for f in files:
                    if f.suffix.lower() == ".zip":
                        from fetch_page import safe_extract
                        for x in safe_extract(f, dest / f.stem):
                            record_credit(x, site, f"{title} / {x.stem}", "", lic, "", url)
                        f.unlink(missing_ok=True)
                    else:
                        record_credit(f, site, title, "", lic, "", url)
                print(f"  ✅ {title}（{len(files)} 个文件，授权：{lic}）")
                done += 1
                time.sleep(5)
            c.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s1 = sub.add_parser("login"); s1.add_argument("site", choices=list(SITES))
    s2 = sub.add_parser("search"); s2.add_argument("where", choices=list(SEARCH_URL)); s2.add_argument("query")
    s2.add_argument("--n", type=int, default=20)
    s3 = sub.add_parser("download"); s3.add_argument("urls", nargs="*")
    s3.add_argument("--site", choices=list(SITES)); s3.add_argument("--from-csv")
    s3.add_argument("--license", help="手动指定授权（确认过页面时用）")
    s3.add_argument("--max", type=int, default=30)
    a = ap.parse_args()

    if a.cmd == "login":
        cmd_login(a.site)
    elif a.cmd == "search":
        cmd_search(a.where, a.query, a.n)
    else:
        pairs = [(u, a.site) for u in a.urls]
        if a.from_csv:
            pairs += [(r["url"], r["site"]) for r in read_csv(Path(a.from_csv))]
        if not pairs or any(s is None for _, s in pairs):
            ap.error("需要链接和 --site，或 --from-csv（列：url,site）")
        cmd_download(pairs, a.license, a.max)


if __name__ == "__main__":
    main()
