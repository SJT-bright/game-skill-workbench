#!/usr/bin/env python3
"""给手动下载的素材登记授权（种子下的 Sonniss、浏览器里手点下载的包等）。

先把文件放进 ~/GameAudioLibrary/raw/<来源>/<包名>/，然后：
  python3 add_credit.py ~/GameAudioLibrary/raw/sonniss/GDC2026_UI --source sonniss \
      --license "Sonniss GDC royalty-free" --url https://sonniss.com/gameaudiogdc
  python3 add_credit.py ~/GameAudioLibrary/raw/itch/cute_loops --source itch \
      --license CC0 --author "作者名" --url https://xxx.itch.io/cute-loops

会把文件夹里所有音频登记进 credits_master.csv（已登记过的跳过）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import AUDIO_EXT, classify_license, credits_by_file, record_credit  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder")
    ap.add_argument("--source", required=True)
    ap.add_argument("--license", required=True)
    ap.add_argument("--author", default="")
    ap.add_argument("--url", required=True, help="素材包页面（以后查授权用）")
    ap.add_argument("--license-url", default="")
    a = ap.parse_args()

    ok, attr, why = classify_license(a.license, allow_sa=True)
    if not ok:
        raise SystemExit(f"⛔ 这个授权不能商用：{why}")
    done = credits_by_file()
    n = 0
    for f in sorted(Path(a.folder).expanduser().resolve().rglob("*")):
        if f.is_file() and f.suffix.lower() in AUDIO_EXT and str(f) not in done:
            record_credit(f, a.source, f.stem, a.author, a.license, a.license_url, a.url)
            n += 1
    print(f"✅ 登记 {n} 个文件（{'需要署名' if attr else '免署名'}）。下一步：python3 build_index.py")


if __name__ == "__main__":
    main()
