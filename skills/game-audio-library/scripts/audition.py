#!/usr/bin/env python3
"""生成本地“试听选音”网页：每个音频 ID 一组候选，点一下就能听，勾选后导出 selection.csv。

  python3 audition.py --candidates candidates.csv --needs needs.csv
      → 生成 audition/index.html，用浏览器打开（脚本会自动打开）
  python3 audition.py --candidates candidates.csv --needs needs.csv --auto
      → 不打开网页，直接按得分自动选（用户不在时的快速模式），写 selection.csv

网页功能：
  - 试听时自动按响度补偿，候选之间音量一致，公平比较
  - 可以让选中的 BGM 在底下循环播放，边听背景音乐边试音效（判断混在一起好不好听）
  - 快捷键：↑/↓ 或 J/K 切换候选，空格播放，X 勾选/取消
  - 勾选状态自动保存；点“导出 selection.csv”下载结果
"""
from __future__ import annotations

import argparse
import html
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import read_csv, write_csv  # noqa: E402
from audio_identity import identity, family


TARGET_LUFS = {"sfx": -16.0, "jingle": -16.0, "bgm": -20.0}


def link_files(rows: list[dict], out: Path) -> None:
    media = out / "media"
    media.mkdir(parents=True, exist_ok=True)
    for i, r in enumerate(rows):
        src = Path(r["path"])
        dst = media / f"{i:04d}{src.suffix.lower()}"
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        try:
            os.symlink(src, dst)
        except OSError:
            shutil.copy2(src, dst)
        r["_src"] = f"media/{dst.name}"


def auto_select(cands: list[dict], needs: dict[str, dict], out: Path) -> None:
    """Prefer different content/families without downgrading semantic fit."""
    rows, used, used_families = [], set(), set()
    fallbacks = []
    for nid, need in needs.items():
        count = max(int(need.get('variants') or 1), 1)
        if need.get('gen') in {'pitch_var', 'pitch_steps'}:
            count = 1
        mine = sorted([c for c in cands if c['id'] == nid], key=lambda c:int(c['rank']))
        dedup, seen = [], set()
        for candidate in mine:
            asset = identity(candidate)
            if asset not in seen:
                seen.add(asset);dedup.append(candidate)
        mine = dedup
        def priority(row):
            try:
                return tuple(int(value) for value in row.get('fit_priority', '').split('|'))
            except ValueError:
                return (0, 0, 0)  # Existing/manual CSVs keep their rank ordering.
        if mine:
            best = max(priority(candidate) for candidate in mine)
            mine = [candidate for candidate in mine if priority(candidate) == best]
        if need['type'] == 'bgm':
            fresh = [c for c in mine if identity(c) not in used and family(c) not in used_families]
        else:
            fresh = [c for c in mine if identity(c) not in used]
        required = str(need.get('required', '')).lower() in {'yes', '1', 'true', '是'}
        if not required and not fresh:
            print(f'· {nid} 可选项没有同等匹配的新素材/曲目家族，跳过，不用旧曲变体冒充轮换')
            continue
        picked = (fresh + [c for c in mine if c not in fresh])[:count]
        if need['type'] == 'bgm':
            grouped, chosen_groups = [], set()
            for candidate in picked:
                if family(candidate) not in chosen_groups:
                    grouped.append(candidate);chosen_groups.add(family(candidate))
            picked = grouped
        if required and picked and not fresh:
            print(f'· {nid} 同等匹配素材不足，明确复用已有来源；需要补库，未降低主题/动作匹配')
        used.update(identity(c) for c in picked)
        used_families.update(family(c) for c in picked)
        for candidate in picked:
            rows.append({'id':nid, 'path':candidate['path'], 'asset_id':identity(candidate),
                         'family_id':family(candidate), 'match_mode':candidate.get('match_mode', 'legacy_rank')})
            if str(candidate.get('match_mode', '')).startswith('fallback_'):
                fallbacks.append(nid)
        if not picked:
            print(f'⚠️ {nid} 没有候选')
    write_csv(out, rows, ['id', 'path', 'asset_id', 'family_id', 'match_mode'])
    if fallbacks:
        print('· 题材素材不足、明确回退（不宣称题材覆盖）：' + ', '.join(dict.fromkeys(fallbacks)))
    print(f'✅ 自动选择完成：{out}（{len(rows)} 行）。下一步：python3 process_audio.py')


PAGE = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>试听选音</title>
<style>
:root{--bg:#fff8f0;--card:#fff;--ink:#3b2f2f;--mute:#8a7b75;--acc:#ff7aa2;--acc2:#5bc0eb;--ok:#3cb371;--warn:#e8a33d}
*{box-sizing:border-box}body{margin:0;font:14px/1.5 -apple-system,"PingFang SC",sans-serif;background:var(--bg);color:var(--ink)}
header{position:sticky;top:0;z-index:5;background:#fff;border-bottom:2px solid #ffe1ea;padding:10px 16px;display:flex;gap:12px;flex-wrap:wrap;align-items:center}
header h1{font-size:17px;margin:0 8px 0 0}button,select{font:inherit;border:0;border-radius:10px;padding:7px 12px;cursor:pointer}
.primary{background:var(--acc);color:#fff;font-weight:600}.ghost{background:#ffe9f0;color:var(--ink)}
main{max-width:980px;margin:0 auto;padding:16px}
section{background:var(--card);border-radius:16px;margin:0 0 14px;padding:12px 14px;box-shadow:0 2px 8px #0000000d}
section h2{font-size:15px;margin:0 0 6px;display:flex;gap:8px;align-items:center}
.badge{font-size:12px;border-radius:8px;padding:1px 8px;background:#eef7fd;color:#2a7fb0}
.need{color:var(--mute);font-size:12px}.done{background:#e8f7ee;color:var(--ok)}
.row{display:grid;grid-template-columns:34px 1fr auto 26px;gap:10px;align-items:center;padding:6px 8px;border-radius:10px}
.row:hover{background:#fff4f7}.row.cur{outline:2px solid var(--acc2)}.row.sel{background:#fff0f5}
.play{width:34px;height:34px;border-radius:50%;background:var(--acc2);color:#fff;padding:0;font-size:14px}
.name{font-weight:600;word-break:break-all}.meta{color:var(--mute);font-size:12px}
.iss{color:var(--warn)}.attr{color:#c0392b;font-weight:600}
input[type=checkbox]{width:20px;height:20px;accent-color:var(--acc)}
.help{color:var(--mute);font-size:12px}
@media (max-width:600px){.row{grid-template-columns:34px 1fr 26px}.row .meta2{display:none}}
</style></head><body>
<header><h1>🎧 试听选音</h1>
<label>BGM 垫底 <select id="bed"><option value="">关</option></select></label>
<button class="ghost" id="autoBtn">每个 ID 自动选第 1 名</button>
<button class="primary" id="exportBtn">导出 selection.csv</button>
<span class="help">↑↓/J K 切换 · 空格播放 · X 勾选</span></header>
<main id="list"></main>
<script>
const DATA = __DATA__;
const NEEDS = __NEEDS__;
const KEY = "audition:" + __KEYNAME__;
let sel = {}; try { sel = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(sel)); } catch (e) {} };
const rows = []; let cur = 0; const player = new Audio(); const bed = new Audio(); bed.loop = true;
const gain = (lufs, type) => { const t = type === "bgm" ? -20 : -16; const g = Math.pow(10, (t - lufs) / 20); return Math.max(0.05, Math.min(1, g)); };
const list = document.getElementById("list");
const groups = {}; DATA.forEach(d => (groups[d.id] = groups[d.id] || []).push(d));
Object.keys(groups).forEach(id => {
  const n = NEEDS[id] || {}; const want = (n.gen === "pitch_var" || n.gen === "pitch_steps") ? 1 : Math.max(+n.variants || 1, 1);
  const sec = document.createElement("section");
  sec.innerHTML = `<h2>${id} <span class="badge">${groups[id][0].type}</span><span class="badge" id="cnt-${id}"></span></h2>
    <div class="need">${(n.notes || "")} ${(n.gen === "pitch_var" || n.gen === "pitch_steps") ? "（变体自动生成，只需选 1 个）" : (want > 1 ? `（需要 ${want} 个版本）` : "")}</div>`;
  groups[id].forEach(d => {
    const r = document.createElement("div"); r.className = "row"; const idx = rows.length; rows.push({ el: r, d, id, want });
    const key = id + "|" + d.path;
    r.innerHTML = `<button class="play">▶</button><div><div class="name">${d.name}</div>
      <div class="meta">${d.source}${d.pack ? " / " + d.pack : ""} · ${(+d.duration).toFixed(2)}s · ${(+d.lufs).toFixed(0)} LUFS · 质量 ${d.quality} · 得分 ${d.score}
      ${d.issues ? `<span class="iss"> · ${d.issues}</span>` : ""}</div></div>
      <div class="meta meta2">${d.license}${d.attribution === "yes" ? ' <span class="attr">需署名</span>' : ""}</div>
      <input type="checkbox" ${sel[key] ? "checked" : ""}>`;
    r.querySelector(".play").onclick = () => { cur = idx; play(); };
    r.querySelector("input").onchange = e => { cur = idx; sel[key] = e.target.checked; if (!e.target.checked) delete sel[key]; save(); refresh(); };
    r.onclick = e => { if (e.target.tagName === "DIV" || e.target.classList.contains("name")) { cur = idx; mark(); } };
    sec.appendChild(r);
  });
  list.appendChild(sec);
  if (groups[id][0].type === "bgm") groups[id].forEach(d => { const o = document.createElement("option"); o.value = d.src; o.textContent = id + " · " + d.name; document.getElementById("bed").appendChild(o); });
});
function mark() { rows.forEach((r, i) => r.el.classList.toggle("cur", i === cur)); rows[cur].el.scrollIntoView({ block: "nearest" }); }
function play() { const d = rows[cur].d; player.src = d.src; player.volume = gain(+d.lufs, d.type) * (bed.paused ? 1 : 1); player.currentTime = 0; player.play(); mark(); }
function refresh() {
  rows.forEach(r => r.el.classList.toggle("sel", !!sel[r.id + "|" + r.d.path]));
  Object.keys(groups).forEach(id => { const n = Object.keys(sel).filter(k => k.startsWith(id + "|")).length; const want = rows.find(r => r.id === id).want;
    const b = document.getElementById("cnt-" + id); b.textContent = `已选 ${n}/${want}`; b.classList.toggle("done", n >= want); });
}
document.getElementById("bed").onchange = e => { if (!e.target.value) { bed.pause(); return; } const d = DATA.find(x => x.src === e.target.value); bed.src = d.src; bed.volume = gain(+d.lufs, "bgm") * 0.5; bed.play(); };
document.getElementById("autoBtn").onclick = () => {
  const used = new Set(Object.keys(sel).map(k => k.slice(k.indexOf("|") + 1)));
  Object.keys(groups).forEach(id => { const want = rows.find(r => r.id === id).want; if (Object.keys(sel).some(k => k.startsWith(id + "|"))) return;
    const fresh = groups[id].filter(d => !used.has(d.path)); const pick = fresh.concat(groups[id].filter(d => used.has(d.path))).slice(0, want);
    pick.forEach(d => { sel[id + "|" + d.path] = true; used.add(d.path); }); });
  save(); rows.forEach(r => r.el.querySelector("input").checked = !!sel[r.id + "|" + r.d.path]); refresh(); };
document.getElementById("exportBtn").onclick = () => {
  const lines = ["id,path"]; Object.keys(sel).forEach(k => { const i = k.indexOf("|"); lines.push(k.slice(0, i) + ',"' + k.slice(i + 1).replace(/"/g, '""') + '"'); });
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([lines.join("\\n")], { type: "text/csv" })); a.download = "selection.csv"; a.click(); };
document.addEventListener("keydown", e => {
  if (e.target.tagName === "SELECT") return;
  if (e.key === "ArrowDown" || e.key === "j") { cur = Math.min(cur + 1, rows.length - 1); e.preventDefault(); play(); }
  else if (e.key === "ArrowUp" || e.key === "k") { cur = Math.max(cur - 1, 0); e.preventDefault(); play(); }
  else if (e.key === " ") { e.preventDefault(); player.paused ? play() : player.pause(); }
  else if (e.key === "x") { const c = rows[cur].el.querySelector("input"); c.checked = !c.checked; c.dispatchEvent(new Event("change")); }
});
mark(); refresh();
</script></body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidates", default="candidates.csv")
    ap.add_argument("--needs", default="needs.csv")
    ap.add_argument("--out", default="audition")
    ap.add_argument("--auto", action="store_true", help="不生成网页，按得分自动选，写 selection.csv")
    a = ap.parse_args()

    cands = read_csv(Path(a.candidates))
    needs = {n["id"]: n for n in read_csv(Path(a.needs))} if Path(a.needs).exists() else {}
    if not cands:
        raise SystemExit("候选为空，先运行 search_index.py")
    if a.auto:
        auto_select(cands, needs, Path("selection.csv"))
        return

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    link_files(cands, out)
    data = [{"id": c["id"], "type": c["type"], "path": c["path"], "src": c["_src"],
             "name": html.escape(c["name"]), "source": html.escape(c["source"]),
             "pack": html.escape(c.get("pack", "")), "duration": c["duration"] or 0,
             "lufs": c["lufs"] or -20, "quality": c["quality"], "score": c["score"],
             "issues": html.escape(c.get("issues", "")), "license": html.escape(c["license"]),
             "attribution": c["attribution"]} for c in cands]
    need_js = {k: {"variants": v.get("variants", "1"), "gen": v.get("gen", ""),
                   "notes": html.escape(v.get("notes", ""))} for k, v in needs.items()}
    page = (PAGE.replace("__DATA__", json.dumps(data, ensure_ascii=False))
                .replace("__NEEDS__", json.dumps(need_js, ensure_ascii=False))
                .replace("__KEYNAME__", json.dumps(str(Path.cwd()))))
    (out / "index.html").write_text(page, encoding="utf-8")
    print(f"✅ 试听页：{out / 'index.html'}")
    print("   用浏览器打开：" + str((out / "index.html").resolve()))
    print("   选好后点“导出 selection.csv”，把文件放到游戏项目目录，然后运行 process_audio.py")


if __name__ == "__main__":
    main()
