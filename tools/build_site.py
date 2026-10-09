#!/usr/bin/env python3
"""Build the companion website from the thesis sources.

    python3 tools/build_site.py --thesis ../master_thesis_non-euclidean

Reads the LaTeX chapter(s) listed in CHAPTERS and the matching .bib file
from the thesis repository and writes index.html from src/page.html.

Only the LaTeX subset used in the thesis is supported (sections, emph/textit/
textbf, cite, ref/cref, enumerate/itemize, historicalnote, quote, figure with
TikZ, tabular, inline and display math). Anything unknown is reported as a
warning so that it can be added here instead of silently disappearing.

TikZ figures cannot be converted automatically. Each figure label is drawn by
a hand-written SVG function in src/page.html (FIGS). tools/figures.lock.json
stores a hash of the TikZ code each drawing was made from; if the thesis
figure changes, the build warns and the page shows a note under the figure
until the drawing is updated and the lock refreshed (--accept-figures).
"""
import argparse, hashlib, html, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tikz2svg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Which thesis files feed which site tab. Only supervisor-approved files go here.
CHAPTERS = {
    "ch2": {"tex": "ch02_history_iter1.tex", "bib": "references_iter1.bib", "number": 2},
}

WARN = []
def warn(msg):
    WARN.append(msg)

# ----------------------------------------------------------------- utilities
def strip_comments(s):
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in s.split("\n"))

def balanced(s, i, open_="{", close="}"):
    """s[i] == open_; return (content, index after the closing brace)."""
    assert s[i] == open_, (s[i:i+30])
    depth = 0
    for j in range(i, len(s)):
        c = s[j]
        if c == "\\":
            continue
        if c == open_ and (j == 0 or s[j-1] != "\\"):
            depth += 1
        elif c == close and (j == 0 or s[j-1] != "\\"):
            depth -= 1
            if depth == 0:
                return s[i+1:j], j+1
    raise ValueError("unbalanced: " + s[i:i+60])

def opt_arg(s, i):
    """Optional [..] argument at s[i] (after whitespace)."""
    k = i
    while k < len(s) and s[k] in " \t\n":
        k += 1
    if k < len(s) and s[k] == "[":
        depth = 0
        for j in range(k, len(s)):
            if s[j] == "[": depth += 1
            elif s[j] == "]":
                depth -= 1
                if depth == 0:
                    return s[k+1:j], j+1
    return None, i

def req_arg(s, i):
    k = i
    while k < len(s) and s[k] in " \t\n":
        k += 1
    return balanced(s, k)

ROMAN = ["i","ii","iii","iv","v","vi","vii","viii","ix","x"]

# ----------------------------------------------------------------- bibliography
ACCENTS = {'"': {"a":"ä","o":"ö","u":"ü","A":"Ä","O":"Ö","U":"Ü","e":"ë","i":"ï"},
           "'": {"e":"é","a":"á","o":"ó","i":"í","u":"ú","E":"É"},
           "`": {"e":"è","a":"à","o":"ò","u":"ù"}}

def bib_text(s):
    s = re.sub(r"\{\\([\"'`])\{?(\w)\}?\}", lambda m: ACCENTS[m.group(1)].get(m.group(2), m.group(2)), s)
    s = re.sub(r"\\([\"'`])\{?(\w)\}?", lambda m: ACCENTS[m.group(1)].get(m.group(2), m.group(2)), s)
    s = re.sub(r"\\textit\{([^{}]*)\}", r"<i>\1</i>", s)
    s = re.sub(r"\\emph\{([^{}]*)\}", r"<i>\1</i>", s)
    s = s.replace("\\,", " ").replace("~", " ").replace("---", "—").replace("--", "–")
    s = s.replace("{", "").replace("}", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def parse_bib(text):
    entries = {}
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text):
        typ, key = m.group(1).lower(), m.group(2)
        i = m.end()
        fields = {}
        while True:
            fm = re.compile(r"\s*(\w+)\s*=\s*").match(text, i)
            if not fm:
                break
            name = fm.group(1).lower(); j = fm.end()
            if text[j] == "{":
                val, j = balanced(text, j)
            else:
                vm = re.compile(r'"([^"]*)"|(\w+)').match(text, j); val = vm.group(1) or vm.group(2); j = vm.end()
            fields[name] = val
            cm = re.compile(r"\s*,?").match(text, j); i = cm.end()
            if text[i:i+1] == "}" or i >= len(text):
                break
        entries[key] = {"type": typ, **fields}
    return entries

def names(field):
    out = []
    for n in re.split(r"\s+and\s+", field or ""):
        n = n.strip()
        if not n: continue
        if "," in n:
            last, first = [x.strip() for x in n.split(",", 1)]
        else:
            parts = n.split(); last, first = parts[-1], " ".join(parts[:-1])
        out.append((bib_text(last), bib_text(first)))
    return out

def label_for(e):
    ns = names(e.get("author")) or names(e.get("editor"))
    yy = (e.get("year") or "")[-2:]
    if len(ns) == 1:
        lab = ns[0][0][:3]
    elif len(ns) <= 4:
        lab = "".join(n[0][0] for n in ns)
    else:
        lab = "".join(n[0][0] for n in ns[:3]) + "+"
    return lab + yy

def fmt_names(ns):
    full = [(f + " " + l).strip() for l, f in ns]
    if len(full) <= 2: return " and ".join(full)
    return ", ".join(full[:-1]) + ", and " + full[-1]

def format_entry(e):
    t = e["type"]; parts = []
    if e.get("author"):
        parts.append(fmt_names(names(e["author"])) + ".")
    elif e.get("editor"):
        ns = names(e["editor"]); parts.append(fmt_names(ns) + (", eds." if len(ns) > 1 else ", ed."))
    title = bib_text(e.get("title", ""))
    if t in ("article", "incollection"):
        parts.append("“" + title + "”.")
    else:
        parts.append("<i>" + title.replace("<i>", '<span style="font-style:normal">').replace("</i>", "</span>") + "</i>.")
    if e.get("translator"):
        parts.append("Trans. by " + fmt_names(names(e["translator"])) + ".")
    if t == "article":
        j = "In: <i>" + bib_text(e.get("journal", "")) + "</i>"
        if e.get("series"): j += ", " + ordinal(e["series"]) + " ser."
        if e.get("volume"): j += " " + bib_text(e["volume"])
        if e.get("year"): j += " (" + e["year"] + ")"
        if e.get("pages"): j += ", pp. " + bib_text(e["pages"])
        parts.append(j + ".")
    elif t == "incollection":
        j = "In: <i>" + bib_text(e.get("booktitle", "")) + "</i>."
        if e.get("editor"): j += " Ed. by " + fmt_names(names(e["editor"])) + "."
        parts.append(j)
    if t != "article":
        if e.get("edition"): parts.append(bib_text(e["edition"]) + " ed.")
        if e.get("volume") and t != "article": parts.append("Vol. " + bib_text(e["volume"]) + ".")
        if e.get("series"): parts.append(bib_text(e["series"]) + ".")
        addr, pubn = bib_text(e.get("address", "")), bib_text(e.get("publisher", ""))
        pub = addr + ": " + pubn if addr and pubn else (addr or pubn)
        if e.get("note"): parts.append(bib_text(e["note"]) + ".")
        tail = (pub + ", " if pub else "") + e.get("year", "")
        if t == "incollection" and e.get("pages"): tail += ", pp. " + bib_text(e["pages"])
        parts.append(tail + ".")
    if t == "article" and e.get("note"): parts.append(bib_text(e["note"]) + ".")
    if e.get("isbn"): parts.append("ISBN: " + bib_text(e["isbn"]) + ".")
    if e.get("url"):
        u = html.escape(e["url"], quote=True)
        parts.append('URL: <a href="' + u + '" target="_blank" rel="noopener">' + html.escape(e["url"]) + '</a>' +
                     (" (visited on " + e["urldate"] + ")" if e.get("urldate") else "") + ".")
    if e.get("language", "").lower() == "russian": parts.append("In Russian.")
    return " ".join(p for p in parts if p.strip(". "))

def ordinal(n):
    n = int(n); return str(n) + ({1: "st", 2: "nd", 3: "rd"}.get(n if n < 20 else n % 10, "th"))

def sort_key(e):
    ns = names(e.get("author")) or names(e.get("editor"))
    return (ns[0][0].lower() if ns else "", e.get("year", ""), bib_text(e.get("title", "")).lower())

# ----------------------------------------------------------------- LaTeX → HTML
class Chapter:
    def __init__(self, num, bib):
        self.num = num; self.bib = bib
        self.labels = {}          # label -> (text, anchor)
        self.cited = []
        self.figs = {}            # label -> tikz code
        self.sec = 0; self.sub = 0; self.fig = 0; self.hn = 0

    # ---- inline -------------------------------------------------------
    def cite(self, loc, keys):
        out = []
        for k in [k.strip() for k in keys.split(",")]:
            e = self.bib.get(k)
            if not e:
                warn("citation key not in bib: " + k); out.append("[" + k + "?]"); continue
            if k not in self.cited: self.cited.append(k)
            lab = e["_label"]
            text = "[" + lab + (", " + self.text(loc, math_ok=False) if loc else "") + "]"
            title = html.escape(re.sub("<[^>]+>", "", format_entry(e))[:180], quote=True)
            out.append('<a class="cite" href="#bib-' + lab + '" title="' + title + '">' + text.replace(" ", "&nbsp;") + "</a>")
        return ", ".join(out)

    def ref(self, label, cref):
        if label not in self.labels:
            warn("unresolved reference: " + label); return "??"
        text, anchor = self.labels[label]
        return '<a class="xref" href="#' + anchor + '">' + text + "</a>"

    def text(self, s, math_ok=True):
        """Convert a run of inline LaTeX to HTML."""
        out = []; i = 0
        while i < len(s):
            c = s[i]
            if c == "$" and math_ok:
                j = s.index("$", i + 1)
                out.append("$" + html.escape(s[i+1:j], quote=False) + "$"); i = j + 1; continue
            if c == "\\":
                m = re.compile(r"\\([A-Za-z]+)\*?|\\(.)").match(s, i)
                name = m.group(1) or m.group(2); j = m.end()
                if name in ("emph", "textit", "textbf", "textup", "textsf", "mbox"):
                    arg, j = req_arg(s, j); inner = self.text(arg, math_ok)
                    tag = {"emph": "em", "textit": "i", "textbf": "b"}.get(name)
                    out.append("<%s>%s</%s>" % (tag, inner, tag) if tag else inner); i = j; continue
                if name == "cite":
                    loc, j = opt_arg(s, j); keys, j = req_arg(s, j)
                    out.append(self.cite(loc, keys)); i = j; continue
                if name in ("ref", "cref", "Cref"):
                    lab, j = req_arg(s, j); out.append(self.ref(lab, name != "ref")); i = j; continue
                if name in ("TrajI", "TrajII", "TrajIII"):
                    n = {"TrajI": 1, "TrajII": 2, "TrajIII": 3}[name]
                    out.append('<span class="traj t%d">T%d</span>' % (n, n)); i = j
                    while i < len(s) and s[i] == ":": out.append(""); i += 1
                    continue
                if name == "ldots": out.append("…"); i = j; continue
                if name == ",": out.append("\u2009"); i = j; continue
                if name in (" ", "\n"): out.append(" "); i = j; continue
                if name in ("&", "%", "$", "#", "_"): out.append(html.escape(name)); i = j; continue
                if name in ("itshape", "small", "centering", "noindent"): i = j; continue
                if name == "label":
                    _, j = req_arg(s, j); i = j; continue
                warn("unknown command \\" + name + " (kept as text)")
                out.append(html.escape("\\" + name)); i = j; continue
            if s.startswith("---", i): out.append("—"); i += 3; continue
            if s.startswith("--", i): out.append("–"); i += 2; continue
            if s.startswith("``", i): out.append("“"); i += 2; continue
            if s.startswith("''", i): out.append("”"); i += 2; continue
            if c == "`": out.append("‘"); i += 1; continue
            if c == "'": out.append("’"); i += 1; continue
            if c == "~": out.append("\u00a0"); i += 1; continue
            if c in "{}": i += 1; continue
            if c in "<>&": out.append(html.escape(c)); i += 1; continue
            out.append(c); i += 1
        h = "".join(out)
        h = re.sub(r"[ \t\r\n]+", " ", h)
        # "Chapter 3" → link to that tab
        h = re.sub("Chapter[\u00a0 ](\\d)", lambda m: '<a class="xref" href="#ch%s">Chapter\u00a0%s</a>' % (m.group(1), m.group(1)), h)
        return h.strip(" ")

    # ---- blocks -------------------------------------------------------
    BLOCK_START = re.compile(r"\\(chapter|section|subsection)\*?\{|\\begin\{|\\\[")

    def first_pass(self, s):
        """Assign numbers to labels (sections, figures, notes, enumerate items)."""
        sec = sub = fig = hn = 0
        for m in re.finditer(r"\\(section|subsection)\*?\{|\\begin\{(figure|historicalnote|enumerate)\}", s):
            kind = m.group(1) or m.group(2)
            if kind == "section":
                sec += 1; sub = 0; anchor = "s%d-%d" % (self.num, sec); text = "Section %d.%d" % (self.num, sec)
                _, j = balanced(s, m.end() - 1)
                lm = re.compile(r"\s*\\label\{([^}]*)\}").match(s, j)
                if lm: self.labels[lm.group(1)] = (text, anchor)
            elif kind == "subsection":
                sub += 1; anchor = "s%d-%d-%d" % (self.num, sec, sub); text = "Section %d.%d.%d" % (self.num, sec, sub)
                _, j = balanced(s, m.end() - 1)
                lm = re.compile(r"\s*\\label\{([^}]*)\}").match(s, j)
                if lm: self.labels[lm.group(1)] = (text, anchor)
            elif kind == "figure":
                fig += 1; body, _ = self.env_body(s, m.start(), "figure")
                lm = re.search(r"\\label\{([^}]*)\}", body)
                if lm: self.labels[lm.group(1)] = ("Figure %d.%d" % (self.num, fig), "fig-%d-%d" % (self.num, fig))
            elif kind == "historicalnote":
                hn += 1; j = m.end()
                _, j = req_arg(s, j); lab, j = req_arg(s, j)
                self.labels["hn:" + lab] = ("Historical Note %d.%d" % (self.num, hn), "hn-" + lab)
            elif kind == "enumerate":
                body, _ = self.env_body(s, m.start(), "enumerate")
                opt, _ = opt_arg(body, 0)
                fmt = self.enum_format(opt)
                for n, item in enumerate(self.split_items(body), 1):
                    lm = re.match(r"\s*\\label\{([^}]*)\}", item)
                    if lm: self.labels[lm.group(1)] = (fmt(n), lm.group(1))

    def env_body(self, s, start, env):
        """s[start:] begins with \\begin{env}; return (body, end index)."""
        b = "\\begin{" + env + "}"; e = "\\end{" + env + "}"
        depth = 0; i = start
        while True:
            nb = s.find(b, i); ne = s.find(e, i)
            if nb != -1 and nb < ne:
                depth += 1; i = nb + len(b)
            else:
                depth -= 1
                if depth == 0:
                    return s[start + len(b):ne], ne + len(e)
                i = ne + len(e)

    @staticmethod
    def enum_format(opt):
        if not opt or "label=" not in opt:
            return lambda n: str(n) + "."
        m = re.search(r"label=(.*?)(,\s*\w+=|$)", opt, re.S)
        lab = m.group(1).strip()
        lab = re.sub(r"\\text(up|bf)\{(.*)\}", r"\2", lab)
        def f(n, lab=lab):
            return lab.replace("\\arabic*", str(n)).replace("\\roman*", ROMAN[n-1]).replace("{", "").replace("}", "")
        return f

    @staticmethod
    def split_items(body):
        body = re.sub(r"^\s*\[[^\]]*\]", "", body, count=1, flags=re.S)  # drop enumerate options
        parts = re.split(r"\\item\b", body)
        return parts[1:]

    def blocks(self, s):
        out = []; i = 0
        while i < len(s):
            ws = re.compile(r"\s*").match(s, i); i = ws.end()
            if i >= len(s): break
            m = self.BLOCK_START.match(s, i)
            if m:
                tok = m.group(0)
                if tok.startswith("\\chapter"):
                    title, j = balanced(s, m.end() - 1)
                    lm = re.compile(r"\s*\\label\{[^}]*\}").match(s, j); j = lm.end() if lm else j
                    out.append(("chapter", self.text(title))); i = j; continue
                if tok.startswith("\\section") or tok.startswith("\\subsection"):
                    kind = "section" if tok.startswith("\\section") else "subsection"
                    title, j = balanced(s, m.end() - 1)
                    lm = re.compile(r"\s*\\label\{([^}]*)\}").match(s, j)
                    label = lm.group(1) if lm else None; j = lm.end() if lm else j
                    out.append((kind, title, label)); i = j; continue
                if tok == "\\[":
                    j = s.index("\\]", i)
                    out.append(("displaymath", s[i+2:j].strip())); i = j + 2; continue
                env = re.compile(r"\\begin\{([^}]*)\}").match(s, i).group(1)
                body, j = self.env_body(s, i, env)
                out.append(("env", env, body)); i = j; continue
            # paragraph: up to blank line or a block start at the beginning of a line
            pm = re.compile(r"\n\s*\n|\n\s*(?=\\(?:begin\{|section|subsection|\[))|\\\[").search(s, i)
            j = pm.start() if pm else len(s)
            para = s[i:j].strip()
            if para:
                out.append(("para", para))
            i = j
        return out

    def render(self, s, overrides):
        self.first_pass(s)
        html_out = []; sec = sub = 0; fig = 0; hn = 0
        for b in self.blocks(s):
            kind = b[0]
            if kind == "chapter":
                html_out.append('<p class="eyebrow">Chapter %d</p>\n<h2 class="ch-title">%s</h2>' % (self.num, b[1]))
                if overrides.get("after_title_html"): html_out.append(overrides["after_title_html"])
            elif kind == "section":
                sec += 1; sub = 0
                html_out.append('<h2 class="sec" id="s%d-%d" data-key="%s"><span class="no">%d.%d</span>%s</h2>' %
                                (self.num, sec, html.escape(b[2] or b[1]), self.num, sec, self.text(b[1])))
            elif kind == "subsection":
                sub += 1
                html_out.append('<h3 id="s%d-%d-%d" data-key="%s"><span class="no">%d.%d.%d</span>%s</h3>' %
                                (self.num, sec, sub, html.escape(b[2] or re.sub(r"\\\w+|[{}`']", "", b[1]).strip()), self.num, sec, sub, self.text(b[1])))
            elif kind == "displaymath":
                html_out.append('<div class="math-display">$$' + html.escape(b[1], quote=False) + "$$</div>")
            elif kind == "para":
                h = self.text(b[1]); cls = ""
                plain = re.sub("<[^>]+>", "", h)
                for o in overrides.get("paragraphs", []):
                    if plain.startswith(o["starts_with"]):
                        h = o["html"]; plain = re.sub("<[^>]+>", "", h); break
                if plain.startswith("Note on this draft") or plain.startswith("(The next iteration"):
                    cls = ' class="draftnote"'
                html_out.append("<p%s>%s</p>" % (cls, h))
            elif kind == "env":
                env, body = b[1], b[2]
                if env == "figure":
                    fig += 1; html_out.append(self.figure(body, fig))
                elif env == "historicalnote":
                    hn += 1
                    title, j = req_arg(body, 0); lab, j = req_arg(body, j)
                    inner = "".join("<p>%s</p>" % self.text(p) for p in re.split(r"\n\s*\n", body[j:]) if p.strip())
                    html_out.append('<aside class="hnote" id="hn-%s">\n  <p class="hn-title">Historical Note %d.%d <em>%s</em></p>\n  %s\n</aside>' %
                                    (lab, self.num, hn, self.text(title), inner))
                elif env in ("enumerate", "itemize"):
                    html_out.append(self.listing(env, body))
                elif env == "quote":
                    html_out.append("<blockquote><p>%s</p></blockquote>" % self.text(body))
                elif env == "center":
                    html_out.append(self.center(body))
                else:
                    warn("unknown environment " + env + " (skipped)")
        return "\n\n".join(html_out)

    def listing(self, env, body):
        opt, _ = opt_arg(body, 0)
        items = self.split_items(body)
        if env == "itemize":
            return "<ul>\n" + "\n".join("  <li>%s</li>" % self.text(it) for it in items) + "\n</ul>"
        fmt = self.enum_format(opt)
        if opt and "\\roman*" in opt:
            return '<ol class="roman">\n' + "\n".join("  <li>%s</li>" % self.text(it) for it in items) + "\n</ol>"
        cls = "hyp" if opt and "textbf" in opt else "axioms"
        rows = []
        for n, it in enumerate(items, 1):
            lm = re.match(r"\s*\\label\{([^}]*)\}", it)
            idattr = ' id="%s"' % lm.group(1) if lm else ""
            rows.append('  <li%s><span class="lab">%s</span><span>%s</span></li>' % (idattr, fmt(n), self.text(it)))
        return '<ol class="%s">\n' % cls + "\n".join(rows) + "\n</ol>"

    def center(self, body):
        m = re.search(r"\\begin\{tabular\}", body)
        if not m:
            return "<p>%s</p>" % self.text(body)
        tb, _ = self.env_body(body, m.start(), "tabular")
        _, k = req_arg(tb, 0)  # column spec
        tb = tb[k:]
        tb = re.sub(r"\\(toprule|bottomrule)", "", tb)
        head, _, rest = tb.partition("\\midrule")
        def rows(t):
            return [r for r in (x.strip() for x in re.split(r"\\\\", t)) if r]
        def cells(r):
            return [self.text(c.strip()) for c in r.split("&")]
        th = "".join("<th>%s</th>" % re.sub("</?b>", "", c) for c in cells(rows(head)[0]))
        trs = "\n".join("    <tr>" + "".join("<td>%s</td>" % c for c in cells(r)) + "</tr>" for r in rows(rest))
        return ('<div class="table-wrap">\n<table>\n  <thead><tr>%s</tr></thead>\n  <tbody>\n%s\n  </tbody>\n</table>\n</div>' % (th, trs))

    def figure(self, body, n):
        cap_i = body.find("\\caption")
        caption = ""
        if cap_i != -1:
            caption, _ = req_arg(body, cap_i + len("\\caption"))
        lm = re.search(r"\\label\{([^}]*)\}", body)
        label = lm.group(1) if lm else "fig%d" % n
        tm = re.search(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", body, re.S)
        tikz = tm.group(0) if tm else ""
        aria = html.escape(re.sub("<[^>]+>", "", self.text(caption))[:140], quote=True)
        try:
            svg = tikz2svg.convert(tikz, aria, re.sub(r"\W", "", label))
            inner = '<div class="fig-wrap">' + svg + "</div>"          # converted automatically
        except tikz2svg.Unsupported as why:
            self.figs[label] = tikz                                    # needs the hand drawing in src/page.html
            self.why = getattr(self, "why", {}); self.why[label] = str(why)
            inner = '<div class="fig-wrap" data-fig="%s"%%(STALE:%s)s></div>' % (label, label)
        return ('<figure id="fig-%d-%d">\n  %s\n  <figcaption><b>Figure %d.%d</b> %s</figcaption>\n</figure>'
                % (self.num, n, inner, self.num, n, self.text(caption)))

    def bibliography(self, heading):
        es = sorted((self.bib[k] for k in self.cited), key=sort_key)
        rows = []
        for e in es:
            lab = e["_label"]
            rows.append('    <dt id="bib-%s">[%s]</dt>\n    <dd>%s</dd>' % (lab, lab, format_entry(e)))
        return ('<section class="bib" id="bibliography">\n  <h2 class="sec" id="s%d-bib">%s</h2>\n  <dl>\n%s\n  </dl>\n</section>'
                % (self.num, heading, "\n".join(rows)))

# ----------------------------------------------------------------- main
def tikz_hash(code):
    norm = re.sub(r"\s+", " ", strip_comments(code)).strip()
    return hashlib.sha256(norm.encode()).hexdigest()[:16]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thesis", required=True, help="path to the thesis repository")
    ap.add_argument("--accept-figures", action="store_true", help="record current TikZ hashes as drawn")
    ap.add_argument("--out", default=os.path.join(ROOT, "index.html"))
    a = ap.parse_args()

    page = open(os.path.join(ROOT, "src", "page.html"), encoding="utf-8").read()
    overrides = json.load(open(os.path.join(ROOT, "tools", "overrides.json"), encoding="utf-8"))
    lock_path = os.path.join(ROOT, "tools", "figures.lock.json")
    lock = json.load(open(lock_path)) if os.path.exists(lock_path) else {}

    for tab, cfg in CHAPTERS.items():
        tex = strip_comments(open(os.path.join(a.thesis, cfg["tex"]), encoding="utf-8").read())
        bib = parse_bib(open(os.path.join(a.thesis, cfg["bib"]), encoding="utf-8").read())
        seen = {}
        for k in sorted(bib, key=lambda k: sort_key(bib[k])):
            lab = label_for(bib[k]); seen[lab] = seen.get(lab, 0) + 1
            bib[k]["_label"] = lab
        dup = {l for l, c in seen.items() if c > 1}
        if dup:
            cnt = {}
            for k in sorted(bib, key=lambda k: sort_key(bib[k])):
                l = bib[k]["_label"]
                if l in dup:
                    bib[k]["_label"] = l + "abcdefgh"[cnt.get(l, 0)]; cnt[l] = cnt.get(l, 0) + 1
        ch = Chapter(cfg["number"], bib)
        ov = overrides.get(tab, {})
        body = ch.render(tex, ov) + "\n\n" + ch.bibliography(ov.get("bibliography_heading", "Bibliography"))
        stale = {}
        for label, code in ch.figs.items():
            h = tikz_hash(code)
            if a.accept_figures:
                lock[label] = h
            if lock.get(label) != h:
                stale[label] = True
                warn("figure %s cannot be converted automatically (%s) and its TikZ changed since the hand drawing was made: redraw it in src/page.html, then run with --accept-figures" % (label, ch.why.get(label, "")))
        body = re.sub(r"%\(STALE:([^)]*)\)s", lambda m: " data-fig-stale" if stale.get(m.group(1)) else "", body)
        marker = "<!--BUILD:%s-->" % tab.upper()
        assert marker in page, marker
        page = page.replace(marker, body)

    if a.accept_figures:
        json.dump(lock, open(lock_path, "w"), indent=2, sort_keys=True)
    head = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body style="margin:0">\n'
            '<!-- Generated by tools/build_site.py from the thesis sources. Do not edit by hand: edit src/page.html or the thesis. -->\n')
    open(a.out, "w", encoding="utf-8").write(head + page + "\n</body></html>\n")
    for w in dict.fromkeys(WARN):
        print("WARNING:", w, file=sys.stderr)
    print("wrote", a.out, "(%d warnings)" % len(set(WARN)))

if __name__ == "__main__":
    main()
