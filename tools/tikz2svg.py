"""Convert a simple TikZ picture to SVG.

Supported subset (what the thesis figures use): tikzpicture[scale=..], scopes
with xshift/yshift, \\draw \\fill \\filldraw \\clip \\path \\node, paths made of
coordinates, --, .. controls .., plot coordinates {..}, circle(..),
arc[start angle, end angle, radius], rectangle, cycle, inline node[..]{..},
options thick/very thick/line width, dashed/dotted, even odd rule,
fill=white / gray!NN / black, traj1col/2col/3col colours.

Anything else raises Unsupported; the site build then falls back to a
hand-drawn SVG (src/page.html, FIGS) or shows a "being redrawn" note.
Colours are theme variables, so figures work in light and dark mode.
"""
import math, re

class Unsupported(Exception):
    pass

PX = 100.0       # SVG units per cm before the picture's scale
FONT = 24        # label font size in SVG units (set per figure in convert)
LW = 1.0         # line-width multiplier (set per figure in convert)
PT = 0.0352778   # 1pt in cm

SYMBOLS = {r"\DD": "𝔻", r"\HH": "ℍ", r"\RR": "ℝ", r"\CC": "ℂ", r"\ell": "ℓ", r"\partial": "∂",
           r"\varphi": "φ", r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\delta": "δ",
           r"\Pi": "Π", r"\infty": "∞", r"\cdot": "·", r"\circ": "°"}

# ------------------------------------------------------------------ helpers
def num(expr):
    e = expr.strip()
    while e.startswith("{") and e.endswith("}"):
        e = e[1:-1].strip()
    if not re.fullmatch(r"[0-9eE+\-*/(). a-z]*", e):
        raise Unsupported("expression " + expr)
    env = {"cos": lambda d: math.cos(math.radians(d)), "sin": lambda d: math.sin(math.radians(d)),
           "tan": lambda d: math.tan(math.radians(d)), "sqrt": math.sqrt, "pi": math.pi}
    try:
        return float(eval(e, {"__builtins__": {}}, env))
    except Exception:
        raise Unsupported("expression " + expr)

def length(s):
    m = re.fullmatch(r"\s*(.+?)\s*(pt|cm|mm)?\s*", s)
    return num(m.group(1)) * {"pt": PT, "cm": 1.0, "mm": 0.1, None: 1.0}[m.group(2)]

def split_top(s, sep):
    out, depth, cur = [], 0, ""
    for c in s:
        if c in "([{": depth += 1
        elif c in ")]}": depth -= 1
        if c == sep and depth == 0:
            out.append(cur); cur = ""
        else:
            cur += c
    out.append(cur)
    return [x for x in out if x.strip()]

def parse_opts(s):
    opts = {}
    for part in split_top(s or "", ","):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1); opts[k.strip()] = v.strip()
        elif part:
            opts[part] = True
    return opts

def match_brace(s, j, o="{", c="}"):
    depth = 0
    for k in range(j, len(s)):
        if s[k] == o: depth += 1
        elif s[k] == c:
            depth -= 1
            if depth == 0: return k
    raise Unsupported("unbalanced " + o)

def read_coord(s, i):
    m = re.match(r"\s*\(", s[i:])
    if not m: raise Unsupported("expected coordinate at: " + s[i:i+30])
    a = i + m.end() - 1
    b = match_brace(s, a, "(", ")")
    parts = split_top(s[a+1:b], ",")
    if len(parts) != 2: raise Unsupported("coordinate (" + s[a+1:b] + ")")
    return (num(parts[0]), num(parts[1])), b + 1

def label_html(t):
    def math_part(m):
        x = m.group(1)
        for k, v in SYMBOLS.items(): x = x.replace(k, v)
        x = re.sub(r"\\[A-Za-z]+", "", x).replace("{", "").replace("}", "")
        return re.sub(r"([A-Za-z]+)", r'<tspan font-style="italic">\1</tspan>', x)
    t = re.sub(r"\$(.*?)\$", math_part, t.strip())
    t = re.sub(r"\\(small|footnotesize|bfseries|itshape|large)\b", "", t)
    return t.replace("{", "").replace("}", "").strip()

# ------------------------------------------------------------------ picture
class Picture:
    def __init__(self, scale):
        self.scale = scale; self.items = []; self.bbox = [1e9, 1e9, -1e9, -1e9]; self.nclip = 0

    def P(self, x, y):
        X, Y = x * self.scale * PX, -y * self.scale * PX
        b = self.bbox
        b[0] = min(b[0], X); b[1] = min(b[1], Y); b[2] = max(b[2], X); b[3] = max(b[3], Y)
        return X, Y

    def svg(self, aria):
        x0, y0, x1, y1 = self.bbox; m = FONT * 1.5
        return ('<svg viewBox="%.1f %.1f %.1f %.1f" role="img" aria-label="%s">' % (x0 - m, y0 - m, x1 - x0 + 2*m, y1 - y0 + 2*m, aria)
                + "".join(self.items) + "</svg>")

def style(opts, kind):
    width = 0.4 * PT; stroke = "var(--fig-1)"; fill = "none"; extra = ""
    for k, v in opts.items():
        if k == "thick": width = 0.8 * PT
        elif k == "very thick": width = 1.2 * PT
        elif k == "ultra thick": width = 1.6 * PT
        elif k == "line width": width = length(v)
        elif k in ("traj1col", "traj2col", "traj3col"):
            stroke = {"traj1col": "var(--fig-1)", "traj2col": "var(--fig-2)", "traj3col": "var(--fig-3)"}[k]
        elif k in ("->", "<-", "<->", "-latex", "->>"):
            raise Unsupported("arrows")
    if kind in ("fill", "filldraw"):
        f = opts.get("fill") if isinstance(opts.get("fill"), str) else None
        if f is None:
            f = next((k for k in opts if re.match(r"(gray|black|white)\b", k)), "black")
        if f == "white": fill = "var(--sheet)"
        elif f == "black": fill = "var(--fig-1)"
        elif re.match(r"(gray|black)!\d+", f):
            pct = float(f.split("!")[1]); fill = "var(--fig-3)"; extra += ' fill-opacity="%.2f"' % min(1.0, pct / 100 * 1.2 + 0.05)
        else: raise Unsupported("fill " + f)
        if kind == "fill": stroke = "none"
    w = max(width * PX * 1.8, 1.4) * LW
    if "densely dotted" in opts or "dotted" in opts:
        extra += ' stroke-dasharray="0.1 %.1f" stroke-linecap="round"' % (w * 2.2)
    elif "dashed" in opts or "densely dashed" in opts:
        extra += ' stroke-dasharray="%.1f %.1f"' % (9 * LW, 7 * LW)
    if "even odd rule" in opts: extra += ' fill-rule="evenodd"'
    return stroke, fill, w, extra

NODE_DIR = {"left": (-1, 0, "end"), "right": (1, 0, "start"), "above": (0, -1, "middle"), "below": (0, 1, "middle"),
            "above left": (-1, -1, "end"), "above right": (1, -1, "start"),
            "below left": (-1, 1, "end"), "below right": (1, 1, "start")}

def add_node(pic, p, opts, text, sx, sy):
    X, Y = pic.P(p[0] + sx, p[1] + sy)
    size = FONT * (0.8 if "footnotesize" in str(opts.get("font", "")) else 1)
    bold = ' font-weight="600"' if "bfseries" in str(opts.get("font", "")) else ""
    dx, dy, anchor = 0, size * 0.35, "middle"
    for k, v in opts.items():
        if k in NODE_DIR:
            ox, oy, anchor = NODE_DIR[k]
            gap = size * 0.3 + (length(v) * pic.scale * PX if isinstance(v, str) else 0)
            dx = ox * gap
            dy = {-1: -gap, 0: size * 0.35, 1: gap + size * 0.75}[oy]
    pic.items.append('<text x="%.1f" y="%.1f" font-size="%.0f" text-anchor="%s" fill="var(--fig-1)"%s>%s</text>'
                     % (X + dx, Y + dy, size, anchor, bold, label_html(text)))

def parse_path(pic, s, sx, sy):
    """Return (svg path commands, inline nodes) for a TikZ path body."""
    d, nodes = [], []
    cur = start = None; line = False; i = 0
    def M(p): return "%.1f,%.1f" % pic.P(p[0] + sx, p[1] + sy)
    while True:
        while i < len(s) and s[i] in " \t\n": i += 1
        if i >= len(s): break
        r = s[i:]
        if r.startswith("--"):
            line = True; i += 2; continue
        if r.startswith("cycle"):
            d.append("Z"); cur = start; line = False; i += 5; continue
        if r.startswith("("):
            p, i = read_coord(s, i)
            if line and cur is not None: d.append("L" + M(p))
            else: d.append("M" + M(p)); start = p
            cur = p; line = False; continue
        m = re.match(r"\.\.\s*controls\s*", r)
        if m:
            c1, i = read_coord(s, i + m.end()); c2 = None
            m2 = re.match(r"\s*and\s*", s[i:])
            if m2: c2, i = read_coord(s, i + m2.end())
            m3 = re.match(r"\s*\.\.\s*", s[i:])
            if not m3: raise Unsupported("controls")
            p, i = read_coord(s, i + m3.end())
            d.append(("C" + M(c1) + " " + M(c2) + " " + M(p)) if c2 else ("Q" + M(c1) + " " + M(p)))
            cur = p; continue
        m = re.match(r"plot\s*(\[[^\]]*\])?\s*coordinates\s*\{", r)
        if m:
            a = i + m.end() - 1; b = match_brace(s, a); t = s[a+1:b]; q = 0; pts = []
            while t[q:].strip():
                p, q = read_coord(t, q); pts.append(p)
            for n, p in enumerate(pts):
                d.append(("L" if n or (line and cur is not None) else "M") + M(p))
            if start is None or not (line and cur is not None): start = pts[0]
            cur = pts[-1]; line = False; i = b + 1; continue
        m = re.match(r"circle\s*(\(([^()]*)\)|\[([^\]]*)\])", r)
        if m:
            rad = length(m.group(2)) if m.group(2) is not None else length(parse_opts(m.group(3))["radius"])
            X, Y = pic.P(cur[0] + sx, cur[1] + sy); R = rad * pic.scale * PX
            pic.P(cur[0] + sx - rad, cur[1] + sy - rad); pic.P(cur[0] + sx + rad, cur[1] + sy + rad)
            d.append("M%.1f,%.1f a%.1f,%.1f 0 1,0 %.1f,0 a%.1f,%.1f 0 1,0 %.1f,0" % (X - R, Y, R, R, 2*R, R, R, -2*R))
            i += m.end(); continue
        m = re.match(r"arc\s*\[([^\]]*)\]", r)
        if m:
            o = parse_opts(m.group(1)); a0, a1, rad = num(o["start angle"]), num(o["end angle"]), length(o["radius"])
            cx, cy = cur[0] - rad * math.cos(math.radians(a0)), cur[1] - rad * math.sin(math.radians(a0))
            n = max(8, int(abs(a1 - a0) / 3))
            for k in range(1, n + 1):
                a = math.radians(a0 + (a1 - a0) * k / n)
                d.append("L" + M((cx + rad * math.cos(a), cy + rad * math.sin(a))))
            cur = (cx + rad * math.cos(math.radians(a1)), cy + rad * math.sin(math.radians(a1)))
            i += m.end(); continue
        m = re.match(r"rectangle\s*", r)
        if m:
            p, i = read_coord(s, i + m.end()); a = cur
            d.append("M" + M(a) + " L" + M((p[0], a[1])) + " L" + M(p) + " L" + M((a[0], p[1])) + " Z")
            cur = p; continue
        m = re.match(r"node\s*(\[([^\]]*)\])?\s*\{", r)
        if m:
            a = i + m.end() - 1; b = match_brace(s, a)
            nodes.append((cur, parse_opts(m.group(2) or ""), s[a+1:b])); i = b + 1; continue
        raise Unsupported("path element: " + r[:40])
    return d, nodes

def convert(code, aria="Figure", prefix="fig"):
    """SVG string for a tikzpicture, or raise Unsupported.

    Run twice: first to measure the drawing, then with the label size and
    line widths set relative to its width (so text reads at ~14px when the
    figure is shown about 600px wide, as on the site)."""
    global FONT, LW
    FONT, LW = 24, 1.0
    first = _convert(code, aria, prefix)
    m = re.match(r'<svg viewBox="[^ ]+ [^ ]+ ([0-9.]+)', first)
    width = float(m.group(1))
    FONT = max(14.0, width * 0.025); LW = max(1.0, width / 900.0)
    return _convert(code, aria, prefix)

def _convert(code, aria, prefix):
    m = re.search(r"\\begin\{tikzpicture\}(\[([^\]]*)\])?", code)
    if not m: raise Unsupported("no tikzpicture")
    pic = Picture(num(parse_opts(m.group(2)).get("scale", "1")))
    body = code[m.end():code.rindex("\\end{tikzpicture}")]
    body = re.sub(r"(?<!\\)%.*", "", body)
    body = expand_foreach(body)
    body = re.sub(r"\\begin\{scope\}(\[([^\]]*)\])?", lambda mm: "\\SCOPE{" + (mm.group(2) or "") + "};", body)
    body = body.replace("\\end{scope}", "\\ENDSCOPE;")
    stack = [{"sx": 0.0, "sy": 0.0, "groups": 0}]
    for st in (x.strip() for x in split_top(body, ";")):
        top = stack[-1]
        if st.startswith("\\SCOPE{"):
            so = parse_opts(st[7:-1])
            # a scope's xshift/yshift is scaled by the picture's scale, like TikZ does
            stack.append({"sx": top["sx"] + (length(so["xshift"]) if "xshift" in so else 0),
                          "sy": top["sy"] + (length(so["yshift"]) if "yshift" in so else 0), "groups": 1})
            pic.items.append("<g>"); continue
        if st == "\\ENDSCOPE":
            pic.items.append("</g>" * stack.pop()["groups"]); continue
        mm = re.match(r"\\(draw|fill|filldraw|clip|path|node)\b\s*(\[)?", st)
        if not mm: raise Unsupported("statement: " + st[:40])
        kind = mm.group(1); rest = st[mm.end(1):].lstrip(); opts = {}
        if rest.startswith("["):
            b = match_brace(rest, 0, "[", "]"); opts = parse_opts(rest[1:b]); rest = rest[b+1:]
        sx, sy = top["sx"], top["sy"]
        if kind == "node":
            ma = re.match(r"\s*at\s*", rest)
            if not ma: raise Unsupported("node without at")
            p, j = read_coord(rest, ma.end()); t = rest[j:].strip()
            if not (t.startswith("{") and t.endswith("}")): raise Unsupported("node text")
            add_node(pic, p, opts, t[1:-1], sx, sy); continue
        d, nodes = parse_path(pic, rest, sx, sy)
        if kind == "clip":
            pic.nclip += 1; cid = "%s-clip%d" % (prefix, pic.nclip)
            pic.items.append('<clipPath id="%s"><path d="%s"/></clipPath><g clip-path="url(#%s)">' % (cid, " ".join(d), cid))
            top["groups"] += 1; continue
        if d:
            stroke, fill, w, extra = style(opts, kind)
            if kind == "path": stroke = "none"
            pic.items.append('<path d="%s" stroke="%s" stroke-width="%.1f" fill="%s" stroke-linejoin="round"%s/>'
                             % (" ".join(d), stroke, w, fill, extra))
        for p, no, t in nodes:
            add_node(pic, p, no, t, sx, sy)
    pic.items.append("</g>" * (stack[0]["groups"]))
    return pic.svg(aria)


def expand_foreach(body):
    """Expand \\foreach \\a/\\b in {x1/y1, x2/y2} {statements} (or a single statement)."""
    for _ in range(20):
        m = re.search(r"\\foreach\s*((?:\\[A-Za-z]+/?)+)\s*in\s*\{", body)
        if not m: return body
        names = re.findall(r"\\[A-Za-z]+", m.group(1))
        a = m.end() - 1; b = match_brace(body, a)
        items = [x.strip() for x in split_top(body[a+1:b], ",")]
        k = b + 1
        while body[k] in " \t\n": k += 1
        if body[k] == "{":
            e = match_brace(body, k); block = body[k+1:e]; end = e + 1
        else:
            e = k
            depth = 0
            while not (body[e] == ";" and depth == 0):
                if body[e] in "([{": depth += 1
                elif body[e] in ")]}": depth -= 1
                e += 1
            block = body[k:e+1]; end = e + 1
        out = []
        for it in items:
            vals = [v.strip() for v in split_top(it, "/")] if len(names) > 1 else [it]
            if len(vals) != len(names): raise Unsupported("foreach item " + it)
            text = block
            for n, v in sorted(zip(names, vals), key=lambda t: -len(t[0])):
                if v.startswith("{") and v.endswith("}"): v = v[1:-1]
                text = re.sub(re.escape(n) + r"(?![A-Za-z])", lambda _m, v=v: v, text)
            out.append(text)
        body = body[:m.start()] + "\n".join(out) + body[end:]
    raise Unsupported("nested foreach")
