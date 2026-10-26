"""音频模块公共工具：路径、授权判断、credits 记录、ffprobe/ffmpeg 封装。

所有脚本都 import 这个文件。素材库默认位置 ~/GameAudioLibrary，
可用环境变量 GAME_AUDIO_LIB 改路径。
"""
from __future__ import annotations

import csv
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

def library_root() -> Path:
    override = os.environ.get("GAME_AUDIO_LIB")
    if override:
        return Path(override).expanduser().resolve()
    config = Path.home() / ".game-audio-library" / "library.json"
    if config.exists():
        try:
            data = json.loads(config.read_text(encoding="utf-8"))
            value = data["library"]
            if data.get("schema") != 1 or not isinstance(value, str) or not value.strip():
                raise ValueError("invalid library config")
            target = Path(value).expanduser()
            if not target.is_absolute():
                raise ValueError("library path must be absolute")
            return target.resolve()
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise RuntimeError(f"音效库配置无效：{config}: {error}") from error
    return (Path.home() / "GameAudioLibrary").resolve()


LIB = library_root()
RAW = LIB / "raw"
AUTH = LIB / "auth"
CREDITS_MASTER = LIB / "credits_master.csv"
INDEX = LIB / "index.csv"
SKIPPED = LIB / "skipped.csv"

AUDIO_EXT = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aif", ".aiff", ".opus"}

CREDIT_FIELDS = ["file", "source", "title", "author", "license", "license_url",
                 "url", "attribution_required", "download_date"]

# ---------------------------------------------------------------- 授权

# 只要命中任意一个，直接拒绝
_DENY = [r"\bnc\b", r"non[- ]?commercial", r"noncommercial", r"personal use",
         r"editorial", r"\bnd\b", r"no[- ]?deriv", r"sampling\+", r"remarc"]

# 允许且不需要署名
_FREE = [r"\bcc0\b", r"public ?domain", r"\bpdm\b", r"pixabay", r"mixkit",
         r"kenney", r"sonniss", r"99sounds", r"bigsoundbank", r"royalty[- ]?free"]

# 允许但需要署名
_ATTR = [r"\bcc[- ]?by\b", r"oga[- ]?by", r"attribution", r"zapsplat",
         r"incompetech", r"soundimage", r"noiseforfun"]

_SA = [r"\bsa\b", r"share[- ]?alike"]


def classify_license(text: str, allow_sa: bool = False) -> tuple[bool, bool, str]:
    """返回 (是否允许, 是否需要署名, 原因)。

    不确定的一律拒绝，宁可少用，也不要用错。
    """
    t = (text or "").lower().replace("_", " ")
    if not t.strip():
        return False, False, "授权为空"
    for p in _DENY:
        if re.search(p, t):
            return False, False, f"禁止：{p}"
    if not allow_sa:
        for p in _SA:
            if re.search(p, t):
                return False, False, "CC-BY-SA 默认不用（加 --allow-sa 可放开）"
    for p in _FREE:
        if re.search(p, t):
            return True, False, "免署名"
    for p in _ATTR:
        if re.search(p, t):
            return True, True, "需署名"
    return False, False, f"未知授权：{text}"


# ---------------------------------------------------------------- credits

def _ensure_lib() -> None:
    for d in (RAW, AUTH):
        d.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def append_csv(path: Path, row: dict, fields: list[str]) -> None:
    new = not path.exists()
    # Portable libraries may carry extra attribution columns. Match their real
    # header rather than appending a short/reordered legacy row.
    if not new:
        with path.open(newline="", encoding="utf-8") as source:
            existing = next(csv.reader(source), [])
        if not existing or not set(fields).issubset(existing):
            raise ValueError(f"CSV header incompatible: {path}")
        fields = existing
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


def known_urls() -> set[str]:
    return {r.get("url", "") for r in read_csv(CREDITS_MASTER)}


def credits_by_file() -> dict[str, dict]:
    return {r["file"]: r for r in read_csv(CREDITS_MASTER)}


def record_credit(file: Path, source: str, title: str, author: str, license: str,
                  license_url: str, url: str) -> None:
    _, attr, _ = classify_license(license, allow_sa=True)
    append_csv(CREDITS_MASTER, {
        "file": str(file), "source": source, "title": title, "author": author,
        "license": license, "license_url": license_url, "url": url,
        "attribution_required": "yes" if attr else "no",
        "download_date": _dt.date.today().isoformat(),
    }, CREDIT_FIELDS)


def record_skip(url: str, title: str, reason: str) -> None:
    append_csv(SKIPPED, {"url": url, "title": title, "reason": reason,
                         "date": _dt.date.today().isoformat()},
               ["url", "title", "reason", "date"])


# ---------------------------------------------------------------- 文件名

def safe_name(s: str, maxlen: int = 80) -> str:
    s = re.sub(r"[^\w\-. ]+", "", s, flags=re.UNICODE).strip().replace(" ", "_")
    return (s or "untitled")[:maxlen]


# ---------------------------------------------------------------- ffmpeg

def add_known_tool_dirs() -> None:
    """把常见安装位置加进本进程的 PATH：刚用 winget/Homebrew 装完 ffmpeg 时不用重开终端。"""
    import glob
    dirs = []
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            dirs.append(os.path.join(local, "Microsoft", "WinGet", "Links"))
            dirs += glob.glob(os.path.join(local, "Microsoft", "WinGet", "Packages", "Gyan.FFmpeg*", "*", "bin"))
        dirs += [r"C:\ffmpeg\bin", r"C:\Program Files\ffmpeg\bin"]
    else:
        dirs += ["/opt/homebrew/bin", "/usr/local/bin"]
    current = os.environ.get("PATH", "").split(os.pathsep)
    extra = [d for d in dirs if os.path.isdir(d) and d not in current]
    if extra:
        os.environ["PATH"] = os.pathsep.join(extra + current)


def have_ffmpeg() -> bool:
    add_known_tool_dirs()
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def need_ffmpeg() -> None:
    """缺 ffmpeg 时自动运行 setup.py 安装一次；仍然没有才停下说明。"""
    if have_ffmpeg():
        return
    import sys
    print("🔧 第一次使用：正在自动安装 ffmpeg（只需一次）…")
    subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "setup.py")])
    if not have_ffmpeg():
        raise SystemExit("ffmpeg 自动安装没有成功：请把上面的提示发给 AI 处理"
                         "（macOS 需要 Homebrew；Windows 需要 winget 或手动下载 ffmpeg）")


def probe(path: Path) -> dict:
    """返回 duration / sample_rate / channels / size_kb。失败返回空 dict。"""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=sample_rate,channels", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=30).stdout
        j = json.loads(out or "{}")
        st = (j.get("streams") or [{}])[0]
        return {
            "duration": round(float(j.get("format", {}).get("duration", 0) or 0), 3),
            "sample_rate": int(st.get("sample_rate", 0) or 0),
            "channels": int(st.get("channels", 0) or 0),
            "size_kb": round(path.stat().st_size / 1024, 1),
        }
    except Exception:
        return {}


def run_ffmpeg(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-y", *args],
                          capture_output=True, text=True)


def today() -> str:
    return _dt.date.today().isoformat()


# ---------------------------------------------------------------- 工程与系统

def detect_engine(project: Path) -> str:
    """返回 '3.x' 或 '2.4'；判断不了就报错，让调用方用 --engine 指定，避免生成错版本的代码。"""
    pkg = project / "package.json"
    if pkg.is_file():
        try:
            v = str(json.loads(pkg.read_text(encoding="utf-8")).get("creator", {}).get("version", ""))
            if v.startswith("3"):
                return "3.x"
            if v.startswith("2"):
                return "2.4"
        except (ValueError, AttributeError):
            pass
    pj = project / "project.json"
    if pj.is_file():
        try:
            v = str(json.loads(pj.read_text(encoding="utf-8")).get("version", ""))
            if v.startswith("2"):
                return "2.4"
            if v.startswith("3"):
                return "3.x"
        except ValueError:
            pass
    if (project / "settings" / "v2").is_dir():
        return "3.x"
    if (project / "settings" / "project.json").is_file():
        return "2.4"
    raise SystemExit(f"认不出 {project} 的 Cocos 版本：请加 --engine 2.4 或 --engine 3.x")


def open_file(path: Path) -> None:
    """用系统默认程序打开（Windows / macOS / Linux 通用）。"""
    import webbrowser
    webbrowser.open(path.resolve().as_uri())
