"""Build site/data.js from the private Winterdeep knowledge base (run by hand on KriisPC; CI only deploys).

    python tools/build_data.py [--kb Y:/Claude/Winterdeep]

The repo is PUBLIC, so this script publishes campaign content only:
- no real names or usernames: players become their characters and the DM is "the DM" (the name list is private, see below);
- no transcripts, quotes, audio or group chat; no "who was present", "uncertain/misheard" or source notes;
- it fails if any blocked word survives (see BLOCK).
"""
import argparse, html, json, pathlib, re, sys

ap = argparse.ArgumentParser()
ap.add_argument("--kb", default=r"Y:\Claude\Winterdeep")
KB = pathlib.Path(ap.parse_args().kb)
OUT = pathlib.Path(__file__).resolve().parents[1] / "site" / "data.js"
SESSION_DATES = {f.stem for f in (KB / "sessions").glob("20*.md")}

# ---- privacy -------------------------------------------------------------
# Real names, usernames and other private words live OUTSIDE this public repo, in the private notes:
#   <kb>/.claude/publish_scrub.json = {"people": [[regex, replacement], ...], "block": "<regex of words that must never be published>"}
_priv = json.loads((KB / ".claude" / "publish_scrub.json").read_text(encoding="utf-8"))
PEOPLE = [tuple(p) for p in _priv["people"]]
BLOCK = re.compile(_priv["block"] + r"|transcript|Whisper", re.I)
DROP_SECTIONS = re.compile(r"^(quotes|uncertain|conflicts|group chat|recordings that are|sources|.*possibly misheard)", re.I)
DROP_LINES = re.compile(r"^\s*[-*]?\s*\**(sources?|length|timestamps|who seems present|source|correction|name note)\b|^>\s*\*\*(correction|name note|date uncertain)", re.I)


FIXUPS = [
    (r"Family name per \w+ \(2026-11-13, \"I think\"\); the notes write \"Neverwinter\", and in play it's heard as \"Neverember\"\.",
     "Family name as the players recall it; the notes also write \"Neverwinter\"."),
    (r"\s*\[(?:heard|Heard)\b[^\]]*\]", ""), (r"\s*\((?:heard|Heard|also heard)\b[^)]*\)", ""),
    (r"\s*\[\"[^\]]*\"(?:, \d{2}:\d{2}:\d{2})?\]", ""),            # ["player's take"]
    (r"\s*\((?:see|See) Uncertain\)", ""),
    (r";?\s*see `[^`]+`", ""), (r" \(including the Christmas/Santa one-shot, out of scope\)", " (including a Christmas one-shot)"), (r"\s*\*\(uncertain\)\*", " (uncertain)"),
    (r"\s*\((?:\d{2}:\d{2}:\d{2})[^)]*\)", ""),                      # (00:13:29–00:13:32)
    (r"\b\d{2}:\d{2}:\d{2}(?:\s*[–-]\s*\d{2}:\d{2}:\d{2})?", ""),     # stray timestamps
    (r"\(\s*[,;]?\s*\)", ""), (r"\[\s*[,;]?\s*\]", ""), (r"(?:,\s*){2,}", ", "), (r"\s+([,.;])", r"\1"),
    (r"\|\s*,\s*", "| "),
]


def scrub(t):
    for a, b in FIXUPS[:1] + PEOPLE + FIXUPS[1:]:
        t = re.sub(a, b, t)
    return t


# ---- tiny markdown -> html ----------------------------------------------
def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"<i>\1</i>", s)
    s = re.sub(r"~~(.+?)~~", r"<s>\1</s>", s)
    s = re.sub(r"\[([^\]]+)\]\((?:\.\./)?sessions/(\d{4}-\d{2}-\d{2})\.md\)", r'<a href="#s-\2">\1</a>', s)
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)  # other relative links -> text
    # citations -> session links:  [ON 2025-06-12], [TX 2026-10-29 01:36:19], [ON 2025-10-16; 2026-01-02]
    def cite(m):
        body = m.group(1)
        body = re.sub(r"(\d{4}-\d{2}-\d{2})", r'<a href="#s-\1">\1</a>', body)
        body = re.sub(r"\b(\d{2}:\d{2}:\d{2})\b", "", body)
        body = re.sub(r"\bTX\b", "session", body).replace("ON ", "notes ").replace("AQ", "quest list")
        return f'<span class="cite">[{re.sub(r"\s+", " ", body).strip(" ,;")}]</span>'
    s = re.sub(r"\[((?:ON|TX|AQ|chat)\b[^\]]*)\]", cite, s)
    s = re.sub(r"\b(?:ON|TX) (\d{4}-\d{2}-\d{2})", r'<a href="#s-\1">\1</a>', s)  # bare refs in table cells
    # any other bare date that is a known session -> link (skip ones already inside a link)
    s = re.sub(r'(<a [^>]*>.*?</a>)|\b(\d{4}-\d{2}-\d{2})\b',
               lambda m: m.group(1) or (f'<a href="#s-{m.group(2)}">{m.group(2)}</a>' if m.group(2) in SESSION_DATES else m.group(2)), s)
    s = re.sub(r"\[(\d{2}:\d{2}:\d{2}(?:[–-]\d{2}:\d{2}:\d{2})?(?:, \d{2}:\d{2}:\d{2})*)\]", "", s)  # bare timestamps
    return s


def md(text):
    out, lines, i = [], text.splitlines(), 0
    def para(buf):
        if buf: out.append("<p>" + inline(" ".join(buf)) + "</p>")
    buf = []
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            para(buf); buf = []; i += 1; continue
        m = re.match(r"^(#{1,5})\s+(.*)", ln)
        if m:
            para(buf); buf = []
            lvl = min(len(m.group(1)) + 1, 5)
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>"); i += 1; continue
        if ln.startswith("|"):
            para(buf); buf = []
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            head, body = rows[0], [r for r in rows[1:] if not re.match(r"^:?-{2,}", r[0] or "--")]
            out.append('<div class="tbl"><table><thead><tr>' + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body) + "</tbody></table></div>")
            continue
        if ln.startswith(">"):
            para(buf); buf = []
            q = []
            while i < len(lines) and lines[i].startswith(">"):
                q.append(lines[i].lstrip("> ").rstrip()); i += 1
            out.append("<blockquote>" + inline(" ".join(q)) + "</blockquote>"); continue
        if re.match(r"^\s*([-*]|\d+[.)]|[a-z][.)]|[ivx]+[.)])\s+", ln):
            para(buf); buf = []
            stack = []  # (indent, tag)
            while i < len(lines) and (re.match(r"^\s*([-*]|\d+[.)]|[a-z][.)]|[ivx]+[.)])\s+", lines[i]) or (lines[i].startswith("  ") and lines[i].strip() and stack)):
                l = lines[i]
                m2 = re.match(r"^(\s*)([-*]|\d+[.)]|[a-z][.)]|[ivx]+[.)])\s+(.*)", l)
                if not m2:  # continuation line
                    out[-1] = out[-1][:-5] + " " + inline(l.strip()) + "</li>"; i += 1; continue
                ind, mark, txt = len(m2.group(1)), m2.group(2), m2.group(3)
                tag = "ol" if re.match(r"\d", mark) else "ul"
                while stack and stack[-1][0] > ind:
                    out.append(f"</{stack.pop()[1]}>")
                if not stack or stack[-1][0] < ind:
                    if stack and out[-1].endswith("</li>"):
                        out[-1] = out[-1][:-5]
                        stack.append((ind, tag + "|li"))
                    else:
                        stack.append((ind, tag))
                    out.append(f"<{tag}>")
                out.append("<li>" + inline(txt) + "</li>"); i += 1
            while stack:
                ind, tag = stack.pop()
                if tag.endswith("|li"):
                    out.append(f"</{tag[:2]}></li>")
                else:
                    out.append(f"</{tag}>")
            continue
        buf.append(ln.strip()); i += 1
    para(buf)
    return "\n".join(out)


# ---- section helpers -----------------------------------------------------
def sections(text):
    """Split on '## ' headings -> list of (title, body)."""
    parts = re.split(r"^## +(.*)$", text, flags=re.M)
    res = [("", parts[0])]
    for k in range(1, len(parts), 2):
        res.append((parts[k].strip(), parts[k + 1]))
    return res


def clean(text, keep_head=False):
    keep = []
    for title, body in sections(text):
        if not title:
            if keep_head: keep.append(body)
            continue
        if DROP_SECTIONS.match(title):
            continue
        keep.append(f"## {title}\n{body}")
    t = "\n".join(keep)
    t = "\n".join(l for l in t.splitlines() if not DROP_LINES.match(l))
    return scrub(t)


def read(p):
    return (KB / p).read_text(encoding="utf-8")


# ---- STATE (overview) ----------------------------------------------------
state = read("STATE.md")
ov = []
for title, body in sections(state):
    if title.lower().startswith(("where the party", "party", "active quests", "resolved recently")):
        body = "\n".join(l for l in body.splitlines() if not re.search(r"\*\*DM:\*\*", l))
        ov.append(f"## {title}\n{body}")
    if title.lower().startswith("timeline"):
        timeline = scrub(body)
overview = md(scrub("\n".join(ov)))
asof = re.search(r"As of \*\*(.+?)\*\*", state).group(1)

# ---- party ---------------------------------------------------------------
roster = read("party/roster.md")
rows = re.findall(r"^\| (?!Character|---)(.+)\|$", roster, re.M)
party_rows = []
for r in rows:
    c = [x.strip() for x in r.split("|")]
    party_rows.append("| " + " | ".join(c[:4]) + " |")
cor_note = "*The travelling \"Cor Vulor\" was unmasked as the impostor Darinox on 2026-10-29; the real Cor is missing.*"
party_md = "| Character | Level | Race | Class |\n|---|---|---|---|\n" + "\n".join(party_rows).replace("~~Cor Vulor~~", "Cor Vulor *(see note)*") + "\n\n" + cor_note + "\n\n"
for title, body in sections(roster):
    if title.lower().startswith(("changes from", "as stated in play")):
        party_md += f"## {title.replace('(see those `sessions/` files)', '').replace(' (full detail with timestamps: `sessions/2026-11-12.md` > Character notes)', '')}\n{body}\n"
party = md(scrub(party_md))

# ---- world ---------------------------------------------------------------
def world(name):
    t = read(f"world/{name}.md")
    t = re.sub(r"^# .*\n", "", t)
    t = re.sub(r"^Citations as in.*$|^Citations: .*$", "", t, flags=re.M)
    t = re.sub(r"`(npcs|factions)\.md`", r"the  tab", t).replace("`sessions/`", "the Sessions tab")
    return md(clean(t, keep_head=True))
worldd = {k: world(k) for k in ("overview", "diary", "legend", "factions", "npcs", "places", "items", "lore")}

# ---- sessions ------------------------------------------------------------
sess = []
for f in sorted((KB / "sessions").glob("20*.md"), reverse=True):
    t = f.read_text(encoding="utf-8")
    d = f.stem
    rich = "## Summary" in t
    summ = re.search(r"\*\*Summary:\*\*\s*(.+)", t)
    if rich:
        s = re.search(r"## Summary\n(.+?)(?:\n## |\Z)", t, re.S).group(1).strip()
        summary = scrub(s)
    else:
        summary = scrub(summ.group(1)) if summ else ""
    body = clean(re.sub(r"^# .*\n", "", t))
    body = re.sub(r"^\*\*Summary:\*\*.*$", "", body, flags=re.M)
    body = re.sub(r"^## Summary\n.+?(?=^## |\Z)", "", body, flags=re.M | re.S)
    body = re.sub(r"^## Notes \([^)]*OneNote\)", "## Notes", body, flags=re.M)
    import datetime
    dt = datetime.date.fromisoformat(d)
    sess.append({"d": d, "day": dt.strftime("%a"), "full": rich, "sum": md(summary), "body": md(body),
                 "empty": summary.strip("() ").startswith("no notes") or summary.startswith("(one-letter")})

data = {"asof": asof, "overview": overview, "timeline": md(timeline), "party": party, "world": worldd, "sessions": sess}
js = "window.WD = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"
bad = sorted(set(m.group(0) for m in BLOCK.finditer(re.sub(r"<[^>]+>", " ", js))))
if bad:
    print("BLOCKED words in output:", bad)
    for m in list(BLOCK.finditer(js))[:12]:
        print("  ...", js[max(0, m.start() - 70):m.end() + 40].replace("\n", " "))
    sys.exit(1)
OUT.write_text(js, encoding="utf-8")
print(f"wrote {OUT} ({len(js)//1024} KB): {len(sess)} sessions, {sum(s['full'] for s in sess)} full recaps")
