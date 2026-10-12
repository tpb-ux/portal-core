"""Autolink de glossário: a 1ª ocorrência de cada termo vira link para o verbete.

Regras: só texto dentro de <main>; nunca em títulos (h1-h6), links, código, botões, rótulos,
<summary>, <figcaption>, <nav>, scripts e atributos (alt, title...). Match por palavra inteira,
com sinônimos e plurais gerados; o termo mais longo vence ("emenda de relator" antes de "emenda").
Siglas só casam em maiúsculas exatas. Um link por termo, no máximo `maximo` por página, sem
o verbete linkar para si mesmo e sem repetir um link que a página já tem.

Formato de cada termo: {slug, termo, sigla?, sinonimos?: [..], autolink?: false | [variantes exatas]}.
"""
import html as _h, re

PREP = {"de", "da", "do", "das", "dos", "à", "às", "ao", "aos", "a", "e", "em", "no", "na", "por", "para", "com", "sem", "sobre", "entre", "contra"}
PULA = {"a", "h1", "h2", "h3", "h4", "h5", "h6", "code", "pre", "kbd", "samp", "script", "style", "button", "label", "summary", "figcaption", "nav", "select", "option", "textarea", "title", "svg", "time"}
VOID = {"br", "img", "hr", "input", "meta", "link", "source", "wbr", "col", "area", "base", "embed", "param", "track"}
TAG = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)\b[^>]*?(/?)>")


def plural(w):
    lw = w.lower()
    if lw.endswith("ão"): return w[:-2] + ("ões" if w[-2:].islower() else "ÕES")
    for a, b in (("al", "ais"), ("el", "éis"), ("ol", "óis"), ("ul", "uis"), ("il", "is")):
        if lw.endswith(a): return w[:-2] + b
    if lw.endswith("m"): return w[:-1] + "ns"
    if lw.endswith(("r", "z")): return w + "es"
    if lw.endswith("s") or lw.endswith("x"): return w
    if lw[-1:] in "aeiouáéíóúâêô": return w + "s"
    return w


def plural_expr(expr):
    """Pluraliza as palavras antes da primeira preposição: 'comissão parlamentar de inquérito' -> 'comissões parlamentares de inquérito'."""
    ws = expr.split(" "); out = []; done = False
    for w in ws:
        if not done and w.lower() in PREP and out: done = True
        out.append(w if done or "-" in w else plural(w))
    return " ".join(out)


def variantes(t):
    if t.get("autolink") is False: return []
    if isinstance(t.get("autolink"), list): base = list(t["autolink"])
    else:
        base = [t["termo"]] + list(t.get("sinonimos") or [])
    vs = set()
    for v in base:
        v = v.strip()
        if len(v) < 3: continue
        vs.add(v)
        if not isinstance(t.get("autolink"), list): vs.add(plural_expr(v))
    out = [(v, False) for v in vs]
    sg = t.get("sigla")
    if sg and t.get("autolink_sigla", True) and len(sg) >= 2:
        out.append((sg, True))
        if not sg.endswith("s"): out.append((sg + "s", True))
    return out


class Autolink:
    def __init__(self, termos, base="/glossario/", maximo=10, classe="gl-link"):
        self.base, self.maximo, self.classe = base, maximo, classe
        self.forms = {}  # forma em minúsculas -> (slug, forma, sigla?)
        self.nome = {}
        for t in termos:
            self.nome[t["slug"]] = t["termo"]
            for v, sig in variantes(t):
                k = v.lower()
                if k in self.forms and not sig and self.forms[k][2]: continue
                if k not in self.forms or sig: self.forms[k] = (t["slug"], v, sig)
        alts = sorted(self.forms.values(), key=lambda x: -len(x[1]))
        self.rx = re.compile(r"(?<![\w-])(" + "|".join(re.escape(f) for _, f, _ in alts) + r")(?![\w-])", re.I) if alts else None
        self.total = 0; self.paginas = 0

    def _ok(self, m):
        hit = self.forms.get(m.group(1).lower())
        if not hit: return None
        slug, forma, sig = hit
        if sig and m.group(1) != forma: return None  # sigla: só maiúsculas exatas
        return slug

    def aplicar(self, html, path):
        if not self.rx or "<main" not in html: return html, 0
        a, rest = html.split("<main", 1)
        i = rest.index(">") + 1
        mtag, main_rest = rest[:i], rest[i:]
        main, sep, tail = main_rest.partition("</main>")
        proprio = path[len(self.base):].strip("/") if path.startswith(self.base) else None
        ja = set(re.findall(re.escape(self.base) + r"([a-z0-9-]+)/", main))  # verbetes já linkados na página
        usados = set(ja) | ({proprio} if proprio else set()); n = 0
        out = []; pos = 0; pula = 0; pilha = []
        def texto(s):
            nonlocal n
            if pula or n >= self.maximo or not s.strip(): return s
            res = []; last = 0
            for m in self.rx.finditer(s):
                if n >= self.maximo: break
                slug = self._ok(m)
                if not slug or slug in usados: continue
                usados.add(slug); n += 1
                res.append(s[last:m.start()]); res.append(f'<a class="{self.classe}" href="{self.base}{slug}/" title="O que é {_h.escape(self.nome[slug])}?">{m.group(1)}</a>'); last = m.end()
            res.append(s[last:]); return "".join(res)
        for m in TAG.finditer(main):
            out.append(texto(main[pos:m.start()])); out.append(m.group(0)); pos = m.end()
            fech, nome, auto = m.group(1), m.group(2).lower(), m.group(3)
            if nome in VOID or auto: continue
            if nome in PULA:
                if fech:
                    if pula: pula -= 1
                else: pula += 1
        out.append(texto(main[pos:]))
        if n: self.total += n; self.paginas += 1
        return a + "<main" + mtag + "".join(out) + sep + tail, n
