#!/usr/bin/env python3
"""音频模块一次性环境准备（Windows / macOS / Linux 通用，重复运行没问题）。

  python setup.py              # 检查并安装 ffmpeg、Python 依赖，建立素材库目录
  python setup.py --browser    # 另外安装 Playwright 浏览器（只有要登录 Pixabay/itch 等网站时才需要）
  python setup.py --check      # 只检查，不安装

ffmpeg：macOS 用 Homebrew，Windows 用 winget（系统自带）。装完 ffmpeg 后，Windows 需要关掉终端再开一个新的。
素材库默认在 用户目录/GameAudioLibrary，可用环境变量 GAME_AUDIO_LIB 改位置。
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PY_DEPS = ["requests"]          # 必需
OPTIONAL_DEPS = ["oga"]         # 只有 fetch_oga.py 用，装不上不影响主流程


def pip_install(pkgs: list[str]) -> bool:
    base = [sys.executable, "-m", "pip", "install", "--user", "--upgrade", *pkgs]
    r = subprocess.run(base, capture_output=True, text=True)
    if r.returncode != 0 and "externally-managed" in (r.stderr + r.stdout):
        r = subprocess.run(base + ["--break-system-packages"], capture_output=True, text=True)
    if r.returncode != 0:
        print((r.stderr or r.stdout)[-600:])
    return r.returncode == 0


def install_ffmpeg() -> bool:
    if sys.platform == "darwin":
        if not shutil.which("brew"):
            print("❌ 没有 Homebrew：先按 https://brew.sh 安装，再重新运行本脚本")
            return False
        return subprocess.run(["brew", "install", "ffmpeg"]).returncode == 0
    if os.name == "nt":
        if not shutil.which("winget"):
            print("❌ 没有 winget：到 https://www.gyan.dev/ffmpeg/builds/ 下载 ffmpeg，解压后把 bin 文件夹加入 PATH")
            return False
        ok = subprocess.run(["winget", "install", "--id", "Gyan.FFmpeg", "-e",
                             "--accept-source-agreements", "--accept-package-agreements"]).returncode == 0
        if ok:
            print("ℹ️ ffmpeg 已安装（本次运行会自动找到它，不用重开终端）")
        return ok
    print("❌ Linux：请用系统包管理器安装 ffmpeg（例如 sudo apt install ffmpeg）")
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--browser", action="store_true", help="安装 Playwright 的 Chromium（登录型网站才需要）")
    ap.add_argument("--check", action="store_true", help="只检查，不安装")
    a = ap.parse_args()
    if sys.version_info < (3, 10):
        print("❌ 需要 Python 3.10 或更高版本")
        return 1
    problems = []

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from common import have_ffmpeg
    if have_ffmpeg():
        print("✅ ffmpeg 已就绪")
    elif a.check or not install_ffmpeg():
        problems.append("ffmpeg")

    missing = []
    for mod in PY_DEPS:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if not missing:
        print("✅ Python 依赖已就绪")
    elif a.check or not pip_install(missing):
        problems.append("Python 依赖：" + "、".join(missing))
    else:
        print("✅ 已安装 Python 依赖：" + "、".join(missing))

    if not a.check:
        for mod in OPTIONAL_DEPS:
            try:
                __import__(mod)
            except ImportError:
                print(("✅ 已安装可选依赖 " if pip_install([mod]) else "· 可选依赖没装上（不影响主流程）：") + mod)

    if a.browser and not a.check:
        try:
            __import__("playwright")
        except ImportError:
            if not pip_install(["playwright"]):
                problems.append("playwright")
        r = subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
        if r.returncode != 0:
            problems.append("Playwright 浏览器")

    lib = Path(os.environ.get("GAME_AUDIO_LIB", Path.home() / "GameAudioLibrary")).expanduser()
    if not a.check:
        for d in ("raw", "auth"):
            (lib / d).mkdir(parents=True, exist_ok=True)
    print(f"📁 素材库：{lib}")
    print("   可选：Freesound 免费 API key（https://freesound.org/apiv2/apply/），设成环境变量 FREESOUND_API_KEY"
          "（Windows：setx FREESOUND_API_KEY 你的key；macOS：写进 ~/.zshrc）")
    if problems:
        print("⚠️ 还没就绪：" + "；".join(problems))
        return 1
    print("✅ 环境就绪")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
