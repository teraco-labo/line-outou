#!/usr/bin/env python3
"""てらこ図書館の index.html を library.json から作り直す（2026-10-10）。

  python3 tools/build_library.py            # index.html を作り直す
  python3 tools/build_library.py --lock     # 「スマホ教室てらこ」の段に鍵をかけて作る（library.json の lock_students を true にしたのと同じ）

決まり（藤崎さん 2026-10-10・メモリ project_library_shelf_policy）
- 並べ方は「講座の種類の段（公民館スマホ講座・パソコン講座・AI講座・スマホ教室てらこ）→ 対象の小見出し → 講座 → 回 × 種類」（2026-10-27 に対象別から講座別へ）
- 回ごとのボタンは いつも同じ順番：スライド → 復習テキスト → 動画（無いものは出さない）
- 図書館に出すのは生徒さんに見せてよい種類だけ（スライドの PDF・復習テキスト・動画）。
  投影用スライド・開催前チェック表・予備 PPTX・まだ授業でやっていない回は出さない（Teraco Shelf にだけある）
- 鍵：「スマホ教室てらこ」の段は、lock_students が true のとき中身を暗号化して students.lock に入れ、
  番号を入れたときだけブラウザの中で開く。番号は ~/.config/teraco/student_pass（1行）にだけ置く。
  鍵の方式は講師用（teacher/）と同じ PBKDF2 + AES-GCM。暗号化は tools/lock.mjs
"""
import html, json, os, re, subprocess, sys, tempfile
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
            # 2026-10-27 藤崎さん「スライドは確認用（ページ数が多い）、復習テキストに印刷用で書いちゃおう」
            btns.append(f'<a class="btn main" href="{e(ep["slides"])}"{ext(ep["slides"])}>スライド<small>確認用（見るだけ）</small></a>')
        if ep.get("text"):
            btns.append(f'<a class="btn" href="{e(ep["text"])}"{ext(ep["text"])}>復習テキスト<small>印刷用</small></a>')
        for i, v in enumerate(ep.get("videos", [])):
            label = "動画" if i == 0 else f"動画{i + 1}"
            btns.append(f'<a class="btn" href="{e(v["url"])}"{ext(v["url"])} title="{e(v.get("label"))}">{label}</a>')
        new = '<span class="badge new">新作</span>' if ep.get("new") else ""
        sub = f'<span class="s">{e(ep.get("sub"))}</span>' if ep.get("sub") else ""
        rows.append(f'<div class="ep"><span class="num">{e(ep["num"])}</span><div class="ep-main">'
                    f'<span class="t">{e(ep["title"])}</span>{new}{sub}<div class="btns">{"".join(btns)}</div></div></div>')
    tools = "".join(f'<a class="tool-note" href="{e(t["url"])}"{ext(t["url"])}><span>{e(t["label"])}</span><span class="arrow">→</span></a>'
                    for t in c.get("tools", []))
    return (f'<details class="acc" data-k="c-{e(c["title"])}"><summary>'
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


def short_label(label):
    """「第5回のゲーム用テンプレートを使う」→「第5回 ゲーム」。回の無いものは「テンプレート」。"""
    s = re.sub(r"(の頼み方)?(テンプレート|プロンプト)を(使う|作る)$", "", label)
    s = re.sub(r"(プロンプト)?(テンプレート)?$", "", s).rstrip("用の")
    s = s.replace("回の", "回 ").strip()
    return s or "テンプレート"


def links_html(no, archived=False):
    """いちばん下の「テンプレート/リンク集」（2026-10-13 藤崎さん「中にプロンプトテンプレートがある感じに、中も見やすく」）。
    archived=False は今の講座のテンプレート＋リンク、True は以前の講座のテンプレートだけ（保管庫のページ用。
    2026-10-27 藤崎さん「リンク集の中で以前の講座に回したものとセットのものは一緒に以前の講座へ」）。"""
    rows, n = [], 0
    for c in DATA["courses"]:
        if bool(c.get("archived")) != archived:
            continue
        tools = c.get("tools", [])
        if not tools:
            continue
        n += len(tools)
        btns = "".join(f'<a class="btn" href="{e(t["url"])}"{ext(t["url"])}>{e(short_label(t["label"]))}</a>' for t in tools)
        rows.append(f'<div class="tpl"><div class="name">{e(c["title"])}</div><div class="btns">{btns}</div></div>')
    body = f'<p class="sub-h">講座のプロンプトテンプレート</p><div class="panel">{"".join(rows)}</div>' if rows else ""
    for g in ([] if archived else DATA.get("links", [])):
        body += f'<p class="sub-h">{e(g["group"])}</p>'
        for it in g["items"]:
            n += 1
            body += (f'<a class="linkbar" href="{e(it["url"])}"{ext(it["url"]) if it["url"].startswith("http") else ""}>'
                     f'<span class="stitle">{e(it["title"])}</span><span class="note">{e(it.get("note"))}</span><span class="go">→</span></a>')
    return (f'<details class="group-acc"><summary><span class="group-no">{no:02d}</span>'
            f'<span class="group-name">{"以前の講座のテンプレート" if archived else "テンプレート/リンク集"}</span><span class="group-count">{n}件</span>'
            f'<span class="group-chev">▶</span></summary><div class="group-body">{body}</div></details>')


LOCK_ICON = ('<svg class="lock" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
             'stroke-linejoin="round"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>')


def n_slides(cs):
    """段の見出しの数：その段に置いてあるスライドの数（2026-10-27 藤崎さん「講座の数は、そのセクションに置いてあるすべてのスライドの数にして」）。"""
    return sum(1 for c in cs for ep in c.get("episodes", []) if ep.get("slides"))


def section(no, name, inner, count, lock=False):
    """お客さん向けの大きな段（2026-10-10 藤崎さん「図書館はお客さんが見るから、大きいセクションを」）。count はスライドの数。"""
    return (f'<details class="group-acc" data-k="s-{e(name)}"><summary><span class="group-no">{no:02d}</span>'
            f'<span class="group-name">{e(name)}{LOCK_ICON if lock else ""}</span>'
            f'<span class="group-count">スライド{count}</span><span class="group-chev">▶</span></summary>'
            f'<div class="group-body">{inner}</div></details>')


courses = DATA["courses"]
# 2026-10-27 藤崎さん「年代別（人別）になっているけど、講座別に変更しましょう」
# 段は講座の種類で分け、年齢・対象（audience）は段の中の小見出しにする
SECTIONS = ["スマホ講座", "パソコン講座", "AI講座", "スマホ教室てらこ"]   # 2026-10-27 公民館スマホ講座→スマホ講座
LOCKED = "スマホ教室てらこ"   # 鍵つきの段（番号は教室の皆さんに口頭で伝える）
AUD_LABEL = {"はじめての方へ": "はじめての方", "一般の方へ": "大人の方", "学生の方へ": "学生の方", "教室の生徒さんへ": "教室の生徒さん"}
ARCHIVE = "以前の講座"


def grp(key, cs):
    """並び替えのひとまとまり（この中で講座の順番を動かせる）。key は並びの保存に使う名前。"""
    return f'<div class="grp" data-g="{e(key)}">' + "".join(course_html(c) for c in cs) + "</div>"


def section_inner(cs, by_audience=True, sec=""):
    """段の中身。対象が2種類以上あるときだけ小見出し（年齢・対象別）を付ける。"""
    auds = list(dict.fromkeys(c["audience"] for c in cs))
    if len(auds) < 2 or not by_audience:
        return grp(sec, cs)
    return "".join(f'<p class="sub-h">{e(AUD_LABEL.get(a, a))}</p>' + grp(f"{sec}|{a}", [c for c in cs if c["audience"] == a])
                   for a in auds)


def in_archive(c):
    return bool(c.get("archived"))
parts, gate = [], ""
# 2026-10-27 藤崎さん「以前の講座というセクションも一覧とは別に下の方にあるといい」
# → 以前の講座はリンク集のさらに下に別の段で出す。教室の以前の講座は、鍵の段の中の「以前の講座」の小見出しに置く
for sec in SECTIONS:
    cs = [c for c in courses if c["section"] == sec and not in_archive(c)]
    old = [c for c in courses if c["section"] == sec and in_archive(c)]
    locked = LOCK and sec == LOCKED
    if not cs and not (locked and old):
        continue
    # 教室の段は対象の小見出しを付けない（教室の講座だけなので）
    inner = section_inner(cs, by_audience=sec != LOCKED, sec=sec)
    if locked:
        if old:
            inner += f'<p class="sub-h">{ARCHIVE}</p>' + grp(f"{sec}|{ARCHIVE}", old)
        (ROOT / "students.lock").write_text(lock_text(inner))
        (ROOT / "students-check.lock").write_text(lock_text("teraco-students-ok"))
        inner = ('<form class="gate" id="gate"><div class="gate-t">番号を入れると開きます</div>'
                 '<div class="row"><input id="pw" type="password" inputmode="numeric" autocomplete="current-password" aria-label="番号">'
                 '<button type="submit" id="go">開く</button></div><div class="msg" id="msg"></div></form><div id="locked"></div>')
    parts.append(section(len(parts) + 1, sec, inner, n_slides(cs + (old if locked else [])), lock=locked))
open_part = "".join(parts)
n_links = len(parts) + 1

# チャンネル登録のバナーは置かない（2026-10-27 藤崎さん「赤い YouTube のバナーはいらない。露骨すぎる。限定公開で見に来た人がいいなと思って登録してくれれば十分」）。動画の説明欄の一言だけにする
CHANNEL = ""
page = (ROOT / "tools/library_template.html").read_text(encoding="utf-8")
old_public = [c for c in courses if in_archive(c) and not (LOCK and c["section"] == LOCKED)]
old_part = ""
if old_public:
    oi = "".join(f'<p class="sub-h">{e(sec)}</p>' + grp(f"{ARCHIVE}|{sec}", [c for c in old_public if c["section"] == sec])
                 for sec in SECTIONS if any(c["section"] == sec for c in old_public))
    old_part = '<div class="old-wrap">' + section(n_links + 1, ARCHIVE, oi, n_slides(old_public)) + "</div>"
page = page.replace("{{COURSES}}", open_part).replace("{{GATE}}", gate).replace("{{LINKS}}", links_html(n_links) + old_part).replace("{{LOCK_SCRIPT}}", "true" if LOCK else "false").replace("{{CHANNEL}}", CHANNEL).replace("{{ORDER_URL}}", DATA.get("order_url", ""))
(ROOT / "index.html").write_text(page, encoding="utf-8")

# 保管庫のページ（以前の講座）。検索サイトに載せない（noindex）
arch = [c for c in courses if in_archive(c)]
if arch:
    ap = (ROOT / "tools/library_template.html").read_text(encoding="utf-8")
    ap = ap.replace("<head>", '<head>\n<meta name="robots" content="noindex,nofollow">', 1)
    ap = ap.replace("<title>てらこ図書館", "<title>てらこ図書館 保管庫", 1)
    ap = ap.replace("<h1>てらこ図書館</h1>", "<h1>てらこ図書館 保管庫</h1>", 1)
    ap = ap.replace("講座で使う教材を、いつでも読み返せます", "以前の講座の教材です（今の講座は図書館にあります）", 1)
    aparts = []
    for sec in SECTIONS:
        cs = [c for c in arch if c["section"] == sec]
        if cs:
            aparts.append(section(len(aparts) + 1, sec, section_inner(cs, sec=sec), n_slides(cs)))
    ap = (ap.replace("{{COURSES}}", "".join(aparts)).replace("{{GATE}}", "")
            .replace("{{LINKS}}", links_html(len(aparts) + 1, archived=True)).replace("{{CHANNEL}}", "").replace("{{ORDER_URL}}", "").replace("{{LOCK_SCRIPT}}", "false"))
    (ROOT / "archive.html").write_text(ap, encoding="utf-8")
    print(f"archive.html（保管庫）に 以前の講座 {len(arch)} を置きました")
print(f"index.html を作り直しました（講座 {len(courses)}・鍵 {'あり' if LOCK else 'なし'}）")
