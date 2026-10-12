"""Qualidade pós-build, genérica (qualquer portal estático):
- unicidade(): mede, por família de páginas pSEO, a fração de texto próprio de cada página
  (5-gramas que aparecem em no máximo 10% das páginas da família, com números normalizados)
  e devolve as páginas abaixo do corte (viram noindex,follow e saem do sitemap).
- similaridade(): Jaccard médio de 5-gramas numa amostra fixa por família (só medida, vai para o saude.json).
- robots_txt(): robots.txt com seções explícitas para buscadores e crawlers de IA (busca e treino).
- set_robots(): troca/insere a meta robots num HTML já gravado.
- anti_rede(): falha se links para portais da mesma rede aparecerem no layout (cabeçalho/rodapé) ou em
  muitas páginas (padrão de link de rede). Link editorial pontual no corpo é permitido.
Sem dependências além da biblioteca padrão."""
import collections, itertools, random, re
from pathlib import Path

_TAGS = re.compile(r"<(script|style)\b.*?</\1>|<[^>]+>", re.S)

def texto_main(h):
    m = re.search(r"<main\b.*?</main>", h, re.S)
    return _TAGS.sub(" ", m.group(0) if m else h)

def shingles(h, n=5):
    w = re.findall(r"\w+|#", re.sub(r"\d[\d.,]*", "#", texto_main(h).lower()))
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}

def unicidade(paginas, corte=0.15, cortes=None, min_familia=10, avaliar=None):
    """paginas: {familia: {path: html}} com TODAS as páginas da família (a frequência dos trechos é medida
    sobre a família inteira, o que torna o resultado estável entre builds). avaliar: conjunto de paths
    candidatos a índice (default: todos). Retorna (stats, abaixo) com abaixo = {path: fração}."""
    stats, abaixo = {}, {}
    for fam, ps in paginas.items():
        if len(ps) < min_familia: continue
        sh = {p: shingles(h) for p, h in ps.items()}
        n = len(sh); lim = max(2, n * 0.10)
        df = collections.Counter(x for s in sh.values() for x in s)
        fr = {p: (sum(1 for x in s if df[x] <= lim) / len(s) if s else 0.0) for p, s in sh.items() if avaliar is None or p in avaliar}
        if not fr: continue
        c = (cortes or {}).get(fam, corte)
        v = sorted(fr.values())
        q = lambda a: round(v[int(a * (len(v) - 1))], 3)
        baixo = {p: round(f, 3) for p, f in fr.items() if f < c}
        abaixo.update(baixo)
        stats[fam] = {"paginas": n, "avaliadas": len(fr), "corte": c, "texto_proprio_p10": q(.1), "texto_proprio_mediana": q(.5), "texto_proprio_p90": q(.9), "abaixo_do_corte": len(baixo)}
    return stats, abaixo

def similaridade(paginas, amostra=8, seed=1):
    """Jaccard médio de 5-gramas (números normalizados) entre pares de uma amostra fixa por família."""
    out = {}
    for fam, ps in paginas.items():
        if len(ps) < 3: continue
        ks = sorted(ps); random.Random(seed).shuffle(ks); ks = ks[:amostra]
        sh = [shingles(ps[k]) for k in ks]
        j = [len(a & b) / len(a | b) for a, b in itertools.combinations(sh, 2) if a | b]
        out[fam] = round(sum(j) / len(j), 3) if j else None
    return out

# Buscadores e crawlers de IA com seção explícita (todos liberados: maximizar presença em busca e IA)
BOTS = [
    ("Buscadores", ["Googlebot", "Googlebot-Image", "Googlebot-News", "Bingbot", "DuckDuckBot", "Applebot", "YandexBot"]),
    ("IA: busca e respostas com citação", ["OAI-SearchBot", "ChatGPT-User", "PerplexityBot", "Perplexity-User", "Claude-SearchBot", "Claude-User", "DuckAssistBot", "MistralAI-User"]),
    ("IA: treino e grounding de modelos", ["GPTBot", "Google-Extended", "ClaudeBot", "anthropic-ai", "Applebot-Extended", "CCBot", "Meta-ExternalAgent", "Amazonbot", "cohere-ai", "Bytespider"]),
]

def robots_txt(base, noindex=False, disallow=("/saude.json", "/busca/", "/*?utm_")):
    if noindex: return "# Prévia/pré-lançamento: nada é rastreado nem indexado.\nUser-agent: *\nDisallow: /\n"
    regras = "".join(f"Disallow: {d}\n" for d in disallow) + "Allow: /\n"
    out = ["# Política: buscadores e crawlers de IA (busca e treino) liberados, para maximizar presença e citações.", ""]
    for titulo, bots in BOTS:
        out.append(f"# {titulo}")
        out += [f"User-agent: {b}" for b in bots]
        out += [regras]
    out += ["# Demais robôs", "User-agent: *", regras, f"Sitemap: {base}/sitemap.xml", ""]
    return "\n".join(out)

ROBOTS_RE = re.compile(r'<meta name="robots" content="[^"]*">')

def set_robots(h, content):
    tag = f'<meta name="robots" content="{content}">'
    if ROBOTS_RE.search(h): return ROBOTS_RE.sub(tag, h, count=1)
    return h.replace('<meta name="description"', tag + '<meta name="description"', 1)

INDEX_ROBOTS = "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"

def anti_rede(out_dir, dominios, max_pct=5.0):
    """Erros se algum domínio da rede aparece no cabeçalho/rodapé ou em mais de max_pct% das páginas."""
    if not dominios: return [], {}
    fs = list(Path(out_dir).rglob("*.html")); cont = collections.Counter(); erros = []
    for f in fs:
        h = f.read_text(encoding="utf-8")
        layout = "".join(re.findall(r"<header\b.*?</header>|<footer\b.*?</footer>|<nav\b.*?</nav>", h, re.S))
        for d in dominios:
            if d in layout: erros.append(f"anti-rede: link para {d} no layout de {f.relative_to(out_dir)}"); break
        for d in dominios:
            if re.search(r'href="https?://(www\.)?' + re.escape(d), h): cont[d] += 1
    pct = {d: round(100 * cont[d] / max(1, len(fs)), 2) for d in dominios}
    erros += [f"anti-rede: {d} linkado em {p}% das páginas (máx. {max_pct}%)" for d, p in pct.items() if p > max_pct]
    return erros[:20], pct
