#!/usr/bin/env python3
"""てらこ図書館の index.html を library.json から作り直す（2026-10-10）。

  python3 tools/build_library.py            # index.html を作り直す
  python3 tools/build_library.py --lock     # 「教室の生徒さんへ」に鍵をかけて作る（library.json の lock_students を true にしたのと同じ）

決まり（藤崎さん 2026-10-10・メモリ project_library_shelf_policy）
- 並べ方は「対象の大きな段 → 講座 → 回 × 種類」（お客さんが見るので対象で分ける。Teraco Shelf は講座ごと＋印）
- 回ごとのボタンは いつも同じ順番：スライド → 復習テキスト → 動画（無いものは出さない）
- 図書館に出すのは生徒さんに見せてよい種類だけ（スライドの PDF・復習テキスト・動画）。
  投影用スライド・開催前チェック表・予備 PPTX・まだ授業でやっていない回は出さない（Teraco Shelf にだけある）
- 鍵：「教室の生徒さんへ」の講座は、lock_students が true のとき中身を暗号化して students.lock に入れ、
  番号を入れたときだけブラウザの中で開く。番号は ~/.config/teraco/student_pass（1行）にだけ置く。
  鍵の方式は講師用（teacher/）と同じ PBKDF2 + AES-GCM。暗号化は tools/lock.mjs
"""
import html, json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "library.json").read_text(encoding="utf-8"))
LOCK = DATA.get("lock_students") or "--lock" in sys.argv
AUD_ORDER = ["はじめての方へ", "学生の方へ", "一般の方へ", "教室の生徒さんへ"]
STUDENTS = "教室の生徒さんへ"
e = lambda s: html.escape(s or "", quote=True)


def ext(url):
    return ' target="_blank" rel="noopener"'


def course_html(c):
    eps = c.get("episodes", [])
    n_new = sum(1 for ep in eps if ep.get("new"))
    badge = "" if not n_new else ('<span class="badge new">新作</span>' if n_new == len(eps) else '<span class="badge new">新作あり</span>')
    rows = []
    for ep in eps:
        btns = []
        if ep.get("slides"):
            btns.append(f'<a class="btn main" href="{e(ep["slides"])}"{ext(ep["slides"])}>スライド</a>')
        if ep.get("text"):
            btns.append(f'<a class="btn" href="{e(ep["text"])}"{ext(ep["text"])}>復習テキスト</a>')
        for i, v in enumerate(ep.get("videos", [])):
            label = "動画" if i == 0 else f"動画{i + 1}"
            btns.append(f'<a class="btn" href="{e(v["url"])}"{ext(v["url"])} title="{e(v.get("label"))}">{label}</a>')
        new = '<span class="badge new">新作</span>' if ep.get("new") else ""
        sub = f'<span class="s">{e(ep.get("sub"))}</span>' if ep.get("sub") else ""
        rows.append(f'<div class="ep"><span class="num">{e(ep["num"])}</span><div class="ep-main">'
                    f'<span class="t">{e(ep["title"])}</span>{new}{sub}<div class="btns">{"".join(btns)}</div></div></div>')
    tools = "".join(f'<a class="tool-note" href="{e(t["url"])}"{ext(t["url"])}><span>{e(t["label"])}</span><span class="arrow">→</span></a>'
                    for t in c.get("tools", []))
    return (f'<details class="acc"><summary>'
            f'<span class="stitle">{e(c["title"])}{badge}</span><span class="count">{len(eps)}回</span><span class="chev">▶</span></summary>'
            f'<div class="acc-body">{"".join(rows)}{tools}</div></details>')


def lock_text(text):
    """text を番号で暗号化した .lock の中身（JSON 文字列）を返す。"""
    with tempfile.TemporaryDirectory() as d:
        src, out = Path(d) / "in.html", Path(d) / "out.lock"
        src.write_text(text, encoding="utf-8")
        subprocess.run(["node", str(ROOT / "tools/lock.mjs"), "--pass-file", os.environ.get("STUDENT_PASS_FILE", str(Path.home() / ".config/teraco/student_pass")),
                        str(src), str(out)], check=True)
        return out.read_text()


LOCK_ICON = ('<svg class="lock" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
             'stroke-linejoin="round"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>')


def section(no, name, inner, count, lock=False):
    """お客さん向けの大きな段（2026-10-10 藤崎さん「図書館はお客さんが見るから、大きいセクションを」）。"""
    return (f'<details class="group-acc"><summary><span class="group-no">{no:02d}</span>'
            f'<span class="group-name">{e(name)}{LOCK_ICON if lock else ""}</span>'
            f'<span class="group-count">{count}講座</span><span class="group-chev">▶</span></summary>'
            f'<div class="group-body">{inner}</div></details>')


courses = DATA["courses"]
parts, gate = [], ""
for no, aud in enumerate(AUD_ORDER, 1):
    cs = [c for c in courses if c["audience"] == aud]
    if not cs:
        continue
    inner = "".join(course_html(c) for c in cs)
    if LOCK and aud == STUDENTS:
        (ROOT / "students.lock").write_text(lock_text(inner))
        (ROOT / "students-check.lock").write_text(lock_text("teraco-students-ok"))
        inner = ('<form class="gate" id="gate"><div class="gate-t">番号を入れると開きます</div>'
                 '<div class="row"><input id="pw" type="password" inputmode="numeric" autocomplete="current-password" aria-label="番号">'
                 '<button type="submit" id="go">開く</button></div><div class="msg" id="msg"></div></form><div id="locked"></div>')
    parts.append(section(no, aud, inner, len(cs), lock=LOCK and aud == STUDENTS))
open_part = "".join(parts)
n_links = len(parts) + 1

page = (ROOT / "tools/library_template.html").read_text(encoding="utf-8")
page = page.replace("{{COURSES}}", open_part).replace("{{GATE}}", gate).replace("{{LINKS_NO}}", f"{n_links:02d}").replace("{{LOCK_SCRIPT}}", "true" if LOCK else "false")
(ROOT / "index.html").write_text(page, encoding="utf-8")
print(f"index.html を作り直しました（講座 {len(courses)}・鍵 {'あり' if LOCK else 'なし'}）")
