#!/usr/bin/env python3
"""把选好的素材加工成游戏可用的文件，并自动生成音频配置和授权记录。

  python3 process_audio.py --needs needs.csv --selection selection.csv --project /path/to/game

做的事情：
  音效   去首尾静音 → 去低频隆隆声 → 首尾极短淡入淡出（防爆音）→ 响度统一到 -16 LUFS
         → 限幅 -1.5 dB → 单声道 96k mp3
  短音乐 同上，保留立体声 128k
  BGM    可截短 → 无缝循环处理（尾部交叉淡入开头）→ 响度统一到 -20 LUFS → 立体声 128k
  变体   needs.csv 的 gen 列：
         pitch_var   一个音效自动生成 N 个微变调版本（随机播放，减少机械感）
         pitch_steps 一个音效生成 N 个逐级升半音的版本（连击用：sfx_combo_1..N）
         loop        BGM 做无缝循环处理
输出：
  assets/resources/audio/sfx/*.mp3、assets/resources/audio/bgm/*.mp3
  assets/scripts/audio/GameAudioConfig.ts（Cocos 3.x）或 GameAudioConfig.js（Cocos 2.4），自动生成，不要手改
  docs/audio/credits.csv（每个游戏内音频文件的来源与授权，门禁 AUDIO-02 读它）
  docs/audio/CREDITS.txt（需署名的素材，贴到游戏“关于/制作人员”页）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_index import analyze  # noqa: E402
from common import (classify_license, credits_by_file, detect_engine, need_ffmpeg,  # noqa: E402
                    read_csv, run_ffmpeg, write_csv)

SPEC = {
    "sfx":    {"lufs": -16.0, "ch": 1, "br": "96k",  "fade_in": 0.002, "fade_out": 0.012, "kb": 50},
    "jingle": {"lufs": -16.0, "ch": 2, "br": "128k", "fade_in": 0.002, "fade_out": 0.06,  "kb": 150},
    "bgm":    {"lufs": -20.0, "ch": 2, "br": "128k", "fade_in": 0.0,   "fade_out": 0.0,   "kb": 1600},
}
LIMIT = "alimiter=limit=0.84:attack=1:release=30:level=disabled"   # ≈ -1.5 dBTP


def gain_for(src: Path, target: float) -> float:
    """按响度对齐到目标值（短音效用 RMS 估算，见 build_index.analyze）。
    测不出来时退回到峰值归一 -6 dB。增益上限 +30 dB，防止把底噪放大。"""
    m = analyze(src)
    if m.get("lufs", -70) <= -60:
        return min(-6.0 - m.get("peak_db", -6.0), 30.0)
    return min(target - m["lufs"], 30.0)


def trim_filter(sfx: bool) -> str:
    if not sfx:
        return ""
    s = "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.005"
    return f"{s},areverse,{s},areverse,"


def process_one(src: Path, dst: Path, kind: str, pitch_ratio: float = 1.0,
                max_sec: float = 0.0, loop_xfade: float = 0.0) -> tuple[bool, str]:
    sp = SPEC[kind]
    tmp = dst.with_suffix(".tmp.wav")
    # 第 1 步：裁剪 / 变调 / 截短，输出无损中间文件
    chain = ["aresample=44100"]
    if pitch_ratio != 1.0:
        chain += [f"asetrate={44100 * pitch_ratio:.2f}", "aresample=44100", f"atempo={1 / pitch_ratio:.5f}"]
    chain.append(trim_filter(kind == "sfx").rstrip(",") or "anull")
    if kind != "bgm":
        chain.append("highpass=f=60")
    args = ["-i", str(src)]
    if max_sec:
        args += ["-t", f"{max_sec + loop_xfade:.3f}"]
    r = run_ffmpeg([*args, "-af", ",".join(c for c in chain if c), "-ac", str(sp["ch"]), str(tmp)])
    if r.returncode != 0:
        return False, r.stderr[-400:]

    # 第 2 步：BGM 无缝循环——把结尾 loop_xfade 秒交叉淡入到开头，循环点就听不出接缝
    if kind == "bgm" and loop_xfade > 0:
        dur = analyze(tmp).get("duration", 0)
        x = loop_xfade
        if dur > x * 4:
            body = dur - x
            looped = dst.with_suffix(".loop.wav")
            fc = (f"[0:a]atrim=0:{x},asetpts=PTS-STARTPTS,afade=t=in:d={x}[head];"
                  f"[1:a]atrim={body}:{dur},asetpts=PTS-STARTPTS,afade=t=out:d={x}[tail];"
                  f"[head][tail]amix=inputs=2:normalize=0[mix];"
                  f"[2:a]atrim={x}:{body},asetpts=PTS-STARTPTS[mid];"
                  f"[mix][mid]concat=n=2:v=0:a=1[out]")
            t = str(tmp)
            r = run_ffmpeg(["-i", t, "-i", t, "-i", t, "-filter_complex", fc, "-map", "[out]", str(looped)])
            if r.returncode == 0:
                looped.replace(tmp)
            else:
                looped.unlink(missing_ok=True)
                print(f"  ⚠️ {dst.name} 无缝循环处理失败，保留原样")

    # 第 3 步：淡入淡出 + 响度统一 + 限幅 + 编码 mp3
    dur = analyze(tmp).get("duration", 0)
    g = gain_for(tmp, sp["lufs"])
    post = []
    if sp["fade_in"]:
        post.append(f"afade=t=in:d={sp['fade_in']}")
    if sp["fade_out"] and dur > sp["fade_out"] * 3:
        post.append(f"afade=t=out:st={dur - sp['fade_out']:.4f}:d={sp['fade_out']}")
    post += [f"volume={g:.2f}dB", LIMIT]
    r = run_ffmpeg(["-i", str(tmp), "-af", ",".join(post), "-ac", str(sp["ch"]), "-ar", "44100",
                    "-c:a", "libmp3lame", "-b:a", sp["br"], "-map_metadata", "-1", str(dst)])
    tmp.unlink(missing_ok=True)
    if r.returncode != 0:
        return False, r.stderr[-400:]
    return True, ""


def js_config(entries: dict[str, dict]) -> str:
    """Cocos 2.4 用的 CommonJS 配置。"""
    def block(kinds: tuple[str, ...]) -> str:
        lines = []
        for k, e in entries.items():
            if e["kind"] in kinds:
                extra = ""
                if e.get("variants", 1) > 1:
                    extra += f", variants: {e['variants']}"
                if abs(e.get("volume", 1.0) - 1.0) > 1e-6:
                    extra += f", volume: {e['volume']}"
                lines.append(f"        {k}: {{ path: '{e['path']}'{extra} }},")
        return "\n".join(lines)
    return ("// ⚠️ 本文件由 process_audio.py 自动生成，不要手改。改音频请重新运行脚本。\n"
            "// path：resources 下路径，不带扩展名；volume：单个音频音量系数；variants：随机版本数（_1 _2 _3）\n"
            "module.exports = {\n    BGM: {\n" + block(("bgm", "jingle")) + "\n    },\n"
            "    SFX: {\n" + block(("sfx",)) + "\n    },\n};\n")


def ts_config(entries: dict[str, dict]) -> str:
    def block(name: str, kinds: tuple[str, ...]) -> str:
        lines = [f"export const {name}: Record<string, AudioEntry> = {{"]
        for k, e in entries.items():
            if e["kind"] in kinds:
                extra = ""
                if e.get("variants", 1) > 1:
                    extra += f", variants: {e['variants']}"
                if abs(e.get("volume", 1.0) - 1.0) > 1e-6:
                    extra += f", volume: {e['volume']}"
                lines.append(f"    {k}: {{ path: '{e['path']}'{extra} }},")
        lines.append("};")
        return "\n".join(lines)

    return ("// ⚠️ 本文件由 process_audio.py 自动生成，不要手改。改音频请重新运行脚本。\n\n"
            "export interface AudioEntry {\n"
            "    path: string;        // resources 下路径，不带扩展名\n"
            "    volume?: number;     // 单个音频音量系数，默认 1\n"
            "    variants?: number;   // 随机版本数量（文件名 _1 _2 _3）\n"
            "}\n\n" + block("BGM", ("bgm", "jingle")) + "\n\n" + block("SFX", ("sfx",)) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--receipt", help="供 pipeline 核验的本次加工结果 JSON")
    ap.add_argument("--needs", default="needs.csv")
    ap.add_argument("--selection", default="selection.csv")
    ap.add_argument("--project", default=".")
    ap.add_argument("--audio-dir", default="assets/resources/audio")
    ap.add_argument("--engine", choices=["auto", "2.4", "3.x"], default="auto")
    ap.add_argument("--config", help="默认 assets/scripts/audio/GameAudioConfig.ts（3.x）或 .js（2.4）")
    ap.add_argument("--credits-dir", default="docs/audio")
    ap.add_argument("--allow-sa", action="store_true", help="允许 CC-BY-SA（默认不用）")
    ap.add_argument("--budget-kb", type=int, default=5120, help="音频总大小预算")
    ap.add_argument("--allow-unknown", action="store_true", help="允许没有授权记录的文件（不推荐）")
    a = ap.parse_args()
    need_ffmpeg()
    def digest(path):
        h = hashlib.sha256()
        with Path(path).open("rb") as source:
            for chunk in iter(lambda: source.read(1024*1024), b""): h.update(chunk)
        return h.hexdigest()
    inputs = {"needs_sha256": digest(a.needs), "selection_sha256": digest(a.selection)}
    if a.receipt:
        Path(a.receipt).unlink(missing_ok=True)

    proj = Path(a.project).resolve()
    engine = detect_engine(proj) if a.engine == "auto" else a.engine
    if not a.config:
        a.config = "assets/scripts/audio/GameAudioConfig." + ("ts" if engine == "3.x" else "js")
    audio = proj / a.audio_dir
    needs = {n["id"]: n for n in read_csv(Path(a.needs))}
    sel = read_csv(Path(a.selection))
    credits = credits_by_file()
    picked: dict[str, list[Path]] = {}
    for s in sel:
        picked.setdefault(s["id"], []).append(Path(s["path"]))

    entries: dict[str, dict] = {}
    credit_rows, attribution_lines, warnings = [], [], []
    results, failures, succeeded_ids = [], [], set()
    for nid, files in picked.items():
        n = needs.get(nid)
        if not n:
            warnings.append(f"{nid} 不在 needs.csv 里，已跳过")
            continue
        kind = n["type"]
        sub = "sfx" if kind == "sfx" else "bgm"
        out_dir = audio / sub
        out_dir.mkdir(parents=True, exist_ok=True)
        for old in list(out_dir.glob(f"{nid}.mp3")) + list(out_dir.glob(f"{nid}_[0-9]*.mp3")):
            old.unlink()

        # 授权检查
        ok_files = []
        for f in files:
            cr = credits.get(str(f.resolve())) or credits.get(str(f))
            lic = cr["license"] if cr else "unknown"
            ok, attr, why = classify_license(lic, allow_sa=a.allow_sa)
            if not ok and not (a.allow_unknown and lic == "unknown"):
                warnings.append(f"{nid}：{f.name} 授权不合格（{why}），已跳过")
                continue
            ok_files.append(f)
            credit_rows.append({"source_path": str(f.resolve()), "id": nid, "file": f.name, "outputs": "", "source": cr.get("source", "") if cr else "",
                                "title": cr.get("title", "") if cr else "", "author": cr.get("author", "") if cr else "",
                                "license": lic, "license_url": cr.get("license_url", "") if cr else "", "url": cr.get("url", "") if cr else "",
                                "changes": "Game edit: trim/fades, loudness normalization, MP3 encoding; pitch/loop edits when requested",
                                "attribution": "yes" if attr else "no"})
            if attr and cr:
                line = f"\"{cr.get('title') or f.stem}\"" + (f" by {cr['author']}" if cr.get("author") else "")
                line += f" ({cr.get('url', '')}) — {lic} ({cr.get('license_url', '')})"
                line += " | Changes: trim/fades, loudness normalization, MP3 encoding; pitch/loop edits when requested"
                if "zapsplat" in lic.lower():
                    line = "Sound effects obtained from https://www.zapsplat.com"
                attribution_lines.append(line)
        if not ok_files:
            continue

        entry_keys_before = set(entries)
        required = (n.get("required") or "").lower() in ("yes", "1", "true", "是")
        gen = (n.get("gen") or "").strip()
        variants = max(int(n.get("variants") or 1), 1)
        max_sec = float(n.get("max_sec") or 0) if kind == "bgm" else 0.0
        xfade = 1.5 if gen == "loop" else 0.0
        vol = float(n.get("volume") or 1.0)
        jobs: list[tuple[Path, Path, float]] = []
        if gen == "pitch_var" and variants > 1:
            cents = [0, 70, -70, 140, -140, 200, -200][:variants]
            jobs = [(ok_files[0], out_dir / f"{nid}_{i + 1}.mp3", 2 ** (c / 1200)) for i, c in enumerate(cents)]
            entries[nid] = {"kind": kind, "path": f"audio/{sub}/{nid}", "variants": variants, "volume": vol}
        elif gen == "pitch_steps" and variants > 1:
            for i in range(variants):
                dst = out_dir / f"{nid}_{i + 1}.mp3"
                jobs.append((ok_files[0], dst, 2 ** (i / 12)))
                entries[f"{nid}_{i + 1}"] = {"kind": kind, "path": f"audio/{sub}/{nid}_{i + 1}", "volume": vol}
        elif len(ok_files) > 1:
            for i, f in enumerate(ok_files):
                jobs.append((f, out_dir / f"{nid}_{i + 1}.mp3", 1.0))
            entries[nid] = {"kind": kind, "path": f"audio/{sub}/{nid}", "variants": len(ok_files), "volume": vol}
        else:
            jobs.append((ok_files[0], out_dir / f"{nid}.mp3", 1.0))
            entries[nid] = {"kind": kind, "path": f"audio/{sub}/{nid}", "volume": vol}

        made = []
        job_errors = []
        expected_outputs = variants if gen in ("pitch_var", "pitch_steps") and variants > 1 else len(ok_files)
        for src, dst, ratio in jobs:
            ok, err = process_one(src, dst, kind, ratio, max_sec, xfade)
            if not ok:
                job_errors.append(f"{dst.name} 加工失败：{err}")
                continue
            relative = dst.relative_to(proj).as_posix()
            made.append(relative)
            source_path = str(src.resolve())
            result = next((r for r in results if r["id"] == nid and r["source_path"] == source_path), None)
            if result is None:
                result = {"id": nid, "source_path": source_path, "outputs": [], "output_sha256": {}}
                results.append(result)
            result["outputs"].append(relative)
            result["output_sha256"][relative] = digest(dst)
            kb = dst.stat().st_size / 1024
            if kb > SPEC[kind]["kb"]:
                failures.append(f"{dst.name} 有 {kb:.0f}KB，超过目标 {SPEC[kind]['kb']}KB")
            print(f"  ✅ {dst.relative_to(proj)}  {kb:.0f}KB")
        if len(made) != expected_outputs:
            job_errors.append(f"{nid} 需要 {expected_outputs} 个输出，实际成功 {len(made)} 个，变体未完整")
        if job_errors:
            if required:
                failures.extend(job_errors)
            else:
                warnings.extend(job_errors)
                # An optional random-variant entry cannot point at missing files.
                # Skip this optional need without interrupting required audio.
                for key in set(entries) - entry_keys_before:
                    entries.pop(key, None)
                results = [row for row in results if row["id"] != nid]
                credit_rows = [row for row in credit_rows if row["id"] != nid]
        elif made:
            succeeded_ids.add(nid)
        for row in credit_rows:
            if row["id"] == nid:
                row["outputs"] = ";".join(r for result in results if result["id"] == nid and result["source_path"] == row["source_path"] for r in result["outputs"])

    # 缺少的必需 ID
    for nid, n in needs.items():
        if (n.get("required") or "").lower() in ("yes", "1", "true", "是") and nid not in succeeded_ids:
            failures.append(f"必需的 {nid} 没有成功加工素材")

    cfg = proj / a.config
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(ts_config(entries) if engine == "3.x" else js_config(entries), encoding="utf-8")
    cdir = proj / a.credits_dir
    write_csv(cdir / "credits.csv", credit_rows,
              ["id", "outputs", "file", "source", "title", "author", "license", "license_url", "url", "attribution", "changes"])
    uniq = list(dict.fromkeys(attribution_lines))
    (cdir / "CREDITS.txt").write_text(
        ("Audio credits\n\n" + "\n".join(uniq) + "\n") if uniq else "所有音频都是免署名授权，不需要写制作人员名单。\n",
        encoding="utf-8")

    total = sum(p.stat().st_size for p in audio.rglob("*.mp3")) / 1024 if audio.exists() else 0
    bgm_kb = sum(p.stat().st_size for p in (audio / "bgm").glob("*.mp3")) / 1024 if (audio / "bgm").exists() else 0
    print(f"\n📦 音频总大小 {total:.0f}KB（预算 {a.budget_kb}KB），其中 BGM {bgm_kb:.0f}KB")
    if total > a.budget_kb:
        failures.append(f"音频超出预算 {total - a.budget_kb:.0f}KB：把 BGM 放进远程 Asset Bundle，或减少 BGM 数量/时长")
    print(f"📝 已生成 {cfg.relative_to(proj)}（Cocos {engine}）、{a.credits_dir}/credits.csv、CREDITS.txt")
    if uniq:
        print(f"⚠️ 有 {len(uniq)} 条素材需要署名，把 CREDITS.txt 的内容放进游戏的“关于/制作人员”页")
    if digest(a.needs) != inputs["needs_sha256"] or digest(a.selection) != inputs["selection_sha256"]:
        failures.append("加工过程中输入发生变化")
    if a.receipt:
        path = Path(a.receipt).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema": 1, "project": str(proj), **inputs, "success": not failures,
                   "sources": results, "errors": failures}
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        tmp.replace(path)
    for w in warnings + failures:
        print("⚠️ " + w)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
