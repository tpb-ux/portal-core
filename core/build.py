"""Pipeline de build comum. O portal chama core.build.main(ROOT)."""
import datetime as dt, hashlib, html, importlib, json, re, shutil, sys
from email.utils import format_datetime
from pathlib import Path
import markdown, yaml
from .site import Site, E, slugify, fit
from . import saude, indexnow, autores, qualidade as Q

BRT = dt.timezone(dt.timedelta(hours=-3))

def load_posts(S):
    posts = []
    for f in sorted((S.ROOT / "content").glob("*.md")):
        _, fm, body = f.read_text(encoding="utf-8").split("---", 2)
        m = yaml.safe_load(fm); d = m["data"]
        if isinstance(d, str): d = dt.datetime.fromisoformat(d)
        if not isinstance(d, dt.datetime): d = dt.datetime.combine(d, dt.time(8))
        if d.tzinfo is None: d = d.replace(tzinfo=BRT)
        if m["editoria"] not in S.EDS: raise SystemExit(f"{f.name}: editoria inválida {m['editoria']}")
        if m.get("tipo") == "analise" and not str(m.get("imagem", "")).startswith("/static/img/"): m.update(imagem="/static/og-default.png", imagem_w=1200, imagem_h=630)
        elif not str(m.get("imagem", "")).startswith("/static/img/"): continue  # regra: só matéria com foto na fonte (capa: foto licenciada ou card próprio)
        slug = m.get("slug") or slugify(f.stem)
        url = f"/analises/{slug}/" if m.get("tipo") == "analise" else f"/{m['editoria']}/{slug}/"
        posts.append(dict(m, data=d, slug=slug, url=url, html=markdown.markdown(body, extensions=["extra"])))
    return sorted(posts, key=lambda p: p["data"], reverse=True)

def img(S, p, sizes="(max-width: 760px) 100vw, 300px", priority=False, cls=""):
    src = p["imagem"]; w, h = p.get("imagem_w", 1200), p.get("imagem_h", 630); th = src[:-5] + "-480.webp"
    load = 'fetchpriority="high" decoding="async"' if priority else 'loading="lazy" decoding="async"'
    return f'<img{f" class={chr(34)}{cls}{chr(34)}" if cls else ""} src="{src}" srcset="{S.PREFIX}{th} 480w, {S.PREFIX}{src} {w}w" sizes="{sizes}" width="{w}" height="{h}" alt="{E(p["titulo"])}" {load}>'

def card(S, p, h="h3"):
    return (f'<div class="card"><a href="{p["url"]}"><div class="thumb">{img(S, p)}<span class="badge">{E(S.EDS[p["editoria"]]["nome"])}</span></div>'
            f'<div class="in"><{h}>{E(p["titulo"])}</{h}><p>{E(p.get("resumo", ""))}</p><span class="more">{E(p.get("fonte", ""))} · {p["data"]:%d/%m %H:%M}</span></div></a></div>')

def sec(small, big, link=None, tag="h2"):
    t = f"<span>{E(small)}</span><strong>{E(big)}</strong>"
    return f'<{tag} class="st">{f"<a href={chr(34)}{link}{chr(34)}>{t}</a>" if link else t}</{tag}>'

def faq_editoria(S, e, ps):
    c = S.CFG; fts = sorted({p.get("fonte") for p in ps if p.get("fonte")}) or [f["nome"] for f in yaml.safe_load((S.ROOT / "feeds.yaml").read_text())["feeds"]][:5]
    return [(f"O que a editoria {e['nome']} do {c['site_name']} cobre?", E(e.get("descricao", f"Notícias de {e['nome']}."))),
            (f"De onde vêm as notícias de {e['nome']}?", f"De fontes públicas com feed aberto, como {E(', '.join(fts[:5]))}. Cada resumo leva link e crédito para o texto original."),
            ("As notícias são escritas por inteligência artificial?", "Não. Os resumos são extraídos automaticamente do feed público da fonte, sem reescrita por IA, e sempre linkam para a íntegra."),
            ("Com que frequência a página é atualizada?", "A coleta roda a cada 30 minutos. Só entram matérias com imagem própria da fonte e dentro dos filtros de relevância."),
            ("Como pedir correção ou remoção de um conteúdo?", 'Pela página de <a href="/correcoes/">correções</a> ou de <a href="/contato/">contato</a>. Pedidos de direito de resposta seguem a <a href="/direito-de-resposta/">política própria</a>.')]

def institucional(S):
    """Páginas Markdown em nichos/<nicho>/paginas/*.md (front matter: titulo, descricao, faqs:[{p,r}]) com placeholders {{cfg.caminho}}."""
    out = []
    fs = {f.name: f for f in sorted((Path(__file__).parent / "paginas_padrao").glob("*.md"))}
    fs.update({f.name: f for f in sorted((S.ROOT / "nichos" / S.nicho / "paginas").glob("*.md"))})  # nicho sobrescreve o padrão
    def ph(t):
        def rep(m):
            v = S.CFG
            for k in m.group(1).split("."): v = (v or {}).get(k) if isinstance(v, dict) else None
            return str(v) if v not in (None, "") else "[[vazio]]"
        return re.sub(r"\{\{cfg\.([a-z_.]+)\}\}", rep, t)
    for f in [fs[k] for k in sorted(fs)]:
        _, fm, body = ph(f.read_text(encoding="utf-8")).split("---", 2)
        m = yaml.safe_load(fm); slug = m.get("slug", f.stem); path = f"/{slug}/"
        body = "\n".join(l for l in body.split("\n") if "[[vazio]]" not in l)  # linhas com campo vazio somem
        h = f'<article class="post"><h1>{E(m["titulo"])}</h1>{markdown.markdown(body, extensions=["extra"])}<p class="upd">Atualizado em {m.get("atualizado", dt.date.today().isoformat())}</p></article>'
        faqs = [(x["p"], x["r"]) for x in m.get("faqs", []) if "[[vazio]]" not in x["p"] + x["r"]]  # FAQ com campo vazio some
        S.write(path, S.page(m["titulo"] + " | " + S.CFG["site_name"], m["descricao"], path, h, faqs=faqs, crumbs=[(m["titulo"], path)],
                             jsonld={"@type": m.get("schema", "WebPage"), "name": m["titulo"], "url": S.BASE + path}), idx=m.get("indexavel", True), faq_min=m.get("faq_min"))
        out.append(path)
    return out

def busca(S):
    idx = [{"u": u, "t": m["title"], "d": m["desc"][:140]} for u, m in S.urls.items() if m["idx"]]
    (S.OUT / "busca.json").write_text(json.dumps(idx, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    js = ("<script>(function(){var q=new URLSearchParams(location.search).get('q')||'',i=document.getElementById('bq'),o=document.getElementById('br');i.value=q;"
          "function n(s){return s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase()}"
          f"fetch('{S.PREFIX}/busca.json').then(function(r){{return r.json()}}).then(function(d){{function run(){{var t=n(i.value).split(/\\s+/).filter(Boolean);if(!t.length){{o.innerHTML='';return}}"
          "var r=d.filter(function(x){var h=n(x.t+' '+x.d);return t.every(function(w){return h.indexOf(w)>=0})}).slice(0,50);"
          f"var P='{S.PREFIX}';o.innerHTML=r.length?r.map(function(x){{return '<li><a href=\"'+P+x.u+'\"><strong>'+x.t.replace(/</g,'&lt;')+'</strong></a><br><small>'+x.d.replace(/</g,'&lt;')+'</small></li>'}}).join(''):'<li>Nada encontrado.</li>'}}"
          "i.oninput=run;run()})})();</script>")
    b = f'<section class="blk"><h1>Buscar</h1><form role="search" action="/busca/"><label for="bq" class="sr-only">Buscar</label><input id="bq" name="q" type="search" placeholder="Nome, partido, termo..." class="bq"></form><ul id="br" class="res"></ul></section>{js}'
    S.write("/busca/", S.page(f"Buscar | {S.CFG['site_name']}", f"Busca interna do {S.CFG['site_name']}.", "/busca/", b, robots="noindex,follow"), idx=False)

def sitemaps(S, posts):
    fams = {}
    for u, m in S.urls.items():
        if m["idx"]: fams.setdefault(m["familia"], []).append(u)
    files = []
    if autores.sitemap_noticias(S, posts): files.append("sitemap-noticias.xml")
    for fam, us in sorted(fams.items()):
        rows = "".join(f"<url><loc>{S.BASE}{u}</loc>" + (f"<lastmod>{S.urls[u]['lastmod']}</lastmod>" if S.urls[u]["lastmod"] else "")
                       + (f"<image:image><image:loc>{S.BASE}{S.urls[u]['image']}</image:loc></image:image>" if S.urls[u]["image"] else "") + "</url>" for u in sorted(us))
        n = f"sitemap-{fam}.xml"; files.append(n)
        (S.OUT / n).write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">' + rows + "</urlset>", encoding="utf-8")
    (S.OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(f"<sitemap><loc>{S.BASE}/{f}</loc></sitemap>" for f in files) + "</sitemapindex>", encoding="utf-8")
    items = "".join(f"<item><title>{E(p['titulo'])}</title><link>{S.BASE}{p['url']}</link><guid>{S.BASE}{p['url']}</guid><pubDate>{format_datetime(p['data'])}</pubDate><description>{E(p.get('resumo', ''))}</description></item>" for p in posts[:30])
    (S.OUT / "rss.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>{E(S.CFG["site_name"])}</title><link>{S.BASE}/</link><description>{E(S.CFG["tagline"])}</description><language>pt-br</language>{items}</channel></rss>', encoding="utf-8")
    (S.OUT / "robots.txt").write_text(Q.robots_txt(S.BASE, S.NOINDEX))
    return files

def llms(S):
    """llms.txt enxuto (hubs, dados abertos, confiança). llms-full.txt mantém a lista completa de indexáveis."""
    hubs = [u for u, m in S.urls.items() if m["idx"] and u.count("/") == 2 and m["familia"] not in ("paginas", "artigos")]
    out = [f"# {S.CFG['site_name']}", "", f"> {S.CFG.get('descricao', S.CFG['tagline'])}", "", S.CFG.get("llms_intro", ""), "", "## Seções e dados", ""]
    for u in sorted(hubs): out.append(f"- [{S.urls[u]['title']}]({S.BASE}{u}): {S.urls[u]['desc']}")
    csvs = sorted((S.OUT / "dados").glob("*.csv")) if (S.OUT / "dados").exists() else []
    if csvs: out += ["", "## Dados abertos (CSV)", ""] + [f"- {S.BASE}/dados/{f.name}" for f in csvs]
    out += ["", "## Confiança", ""] + [f"- [{S.urls[u]['title']}]({S.BASE}{u})" for u in ("/sobre/", "/expediente/", "/politica-editorial/", "/metodologia/", "/correcoes/", "/dados/") if u in S.urls]
    out += ["", f"Lista completa: {S.BASE}/llms-full.txt · Sitemap: {S.BASE}/sitemap.xml", ""]
    sec = {}
    for u, m in S.urls.items():
        if m["idx"]: sec.setdefault("/" + u.strip("/").split("/")[0] + "/" if u != "/" else "/", []).append(u)
    full = out[:5] + ["## Todas as páginas indexáveis", ""]
    for u in sorted(u for u, m in S.urls.items() if m["idx"]): full.append(f"- [{S.urls[u]['title']}]({S.BASE}{u}): {S.urls[u]['desc']}")
    (S.OUT / "llms.txt").write_text("\n".join(out), encoding="utf-8"); (S.OUT / "llms-full.txt").write_text("\n".join(full) + "\n", encoding="utf-8")

RUNTIME = {"/saude.json"}  # gerados depois da checagem
HREF = re.compile(r"""(?:href|src)=["']([^"'#?]+)""")
def linkcheck(S):
    bad = {}
    for f in S.OUT.rglob("*.html"):
        src = "/" + f.relative_to(S.OUT).as_posix().replace("index.html", "")
        for h in HREF.findall(f.read_text(encoding="utf-8")):
            if h.startswith(S.BASE): h = h[len(S.BASE):] or "/"
            elif h.startswith("http") or h.startswith("//") or not h.startswith("/"): continue
            if S.PREFIX and h.startswith(S.PREFIX + "/"): h = h[len(S.PREFIX):]
            t = S.OUT / h.lstrip("/")
            if (t / "index.html").exists() or t.is_file() or h in RUNTIME: continue
            n, s0 = bad.get(h, (0, src)); bad[h] = (n + 1, s0)
    return bad

def quality(S):
    seen = {}
    for u, m in S.urls.items():
        if not m["idx"]: continue
        if m["title"] in seen: S.errors.append(f"título duplicado: {u} = {seen[m['title']]}")
        seen[m["title"]] = u
        if not (50 <= len(m["desc"]) <= 165): S.errors.append(f"{u}: descrição com {len(m['desc'])} caracteres (50–165)")

def unicidade(S):
    """Páginas pSEO (famílias fora de paginas/artigos, profundidade >= 2) com pouco texto próprio saem do índice."""
    qc = S.CFG.get("qualidade") or {}; fams = {}; cand = set()
    for u, m in S.urls.items():
        if m["familia"] in ("paginas", "artigos", "analises") or u.count("/") < 3: continue
        f = S.OUT / u.lstrip("/") / "index.html"
        if not f.exists(): continue
        fams.setdefault(m["familia"], {})[u] = f.read_text(encoding="utf-8")
        if m["idx"] or u in S.ondas: cand.add(u)  # páginas retidas por onda também são medidas
    stats, abaixo = Q.unicidade(fams, corte=qc.get("corte_unicidade", 0.15), cortes=qc.get("cortes_unicidade"), avaliar=cand)
    for u in abaixo:
        if u not in S.ondas: S.thin.add(u)
        S.urls[u]["idx"] = False
        if not S.NOINDEX:
            f = S.OUT / u.lstrip("/") / "index.html"; f.write_text(Q.set_robots(f.read_text(encoding="utf-8"), "noindex,follow"), encoding="utf-8")
    sim = Q.similaridade({k: {u: h for u, h in v.items() if u in cand and u not in abaixo} for k, v in fams.items()})
    return {"unicidade": stats, "noindex_por_unicidade": len(abaixo), "similaridade_jaccard5": sim}

def main(root):
    import os; os.chdir(root)
    S = Site(root)
    try:
        from . import fetch as _f
        n = _f.migrar_cards()
        if n: print(f"Imagens: {n} foto(s) sem licença confirmada trocadas por card próprio (mesmo caminho) ou crédito atualizado")
    except SystemExit: raise
    except Exception as ex: print("Imagens: migração não executada:", ex)
    AUT = autores.carregar(S)
    posts = [p for p in load_posts(S) if autores.publicavel(p, AUT)]
    if S.OUT.exists(): shutil.rmtree(S.OUT)
    core_static = Path(__file__).parent / "static"
    shutil.copytree(core_static, S.OUT / "static")
    for d in (S.ROOT / "static",):
        if d.exists(): shutil.copytree(d, S.OUT / "static", dirs_exist_ok=True)
    t = S.CFG.get("tema") or {}
    css = (S.OUT / "static/style.css").read_text(encoding="utf-8")
    css = css.replace("--a:#C93D17", f"--a:{t.get('cor', '#C93D17')}").replace("--a2:#A83212", f"--a2:{t.get('cor2', '#A83212')}").replace("--d:#2E333D", f"--d:{t.get('escuro', '#2E333D')}")
    (S.OUT / "static/style.css").write_text(css, encoding="utf-8"); S.css_v = hashlib.md5(css.encode()).hexdigest()[:10]
    if (S.OUT / "static/favicon.ico").exists(): shutil.copy(S.OUT / "static/favicon.ico", S.OUT / "favicon.ico")
    if S.CFG.get("cname") and not S.PREFIX: (S.OUT / "CNAME").write_text(S.CFG["cname"].strip() + "\n")
    S.posts = posts
    # artigos agregados: sempre noindex,follow (o ranking vem do conteúdo de referência)
    for p in posts:
        own = p.get("tipo") == "analise"
        if own:
            ld = {"@type": "NewsArticle", "headline": p["titulo"][:110], "description": p.get("resumo", ""), "image": [S.BASE + p["imagem"]], "datePublished": p["data"].isoformat(),
                  "dateModified": (p.get("atualizado") or p["data"]).isoformat() if hasattr(p.get("atualizado") or p["data"], "isoformat") else p["data"].isoformat(),
                  "articleSection": "Análises", "mainEntityOfPage": S.BASE + p["url"], "author": autores.person(S, AUT[p["autor"]]), "editor": autores.person(S, AUT[p["revisado_por"]]), "publisher": {"@id": S.BASE + "/#org"}}
            b = (f'<article class="post"><div class="kick"><a href="/analises/">Análises</a></div><h1>{E(p["titulo"])}</h1>'
                 f'<p class="meta">Por <a href="/autores/{p["autor"]}/">{E(AUT[p["autor"]]["nome"])}</a> · revisão de <a href="/autores/{p["revisado_por"]}/">{E(AUT[p["revisado_por"]]["nome"])}</a> · <time datetime="{p["data"].isoformat()}">{p["data"]:%d/%m/%Y %H:%M}</time></p>'
                 f'<p class="lead">{E(p.get("resumo", ""))}</p>{p["html"]}</article>')
            S.write(p["url"], S.page(p["titulo"], p.get("resumo", "") or p["titulo"], p["url"], b, og_img=S.BASE + p["imagem"], og_type="article", jsonld=ld,
                                     crumbs=[("Análises", "/analises/"), (p["titulo"][:60], p["url"])]), familia="analises", faq_min=0, lastmod=p["data"].date().isoformat(), image=p["imagem"])
            continue
        ld = {"@type": "NewsArticle", "headline": p["titulo"][:110], "description": p.get("resumo", ""), "image": [S.BASE + p["imagem"]],
              "datePublished": p["data"].isoformat(), "dateModified": p["data"].isoformat(), "articleSection": S.EDS[p["editoria"]]["nome"],
              "mainEntityOfPage": S.BASE + p["url"], "author": {"@type": "Organization", "name": p.get("fonte") or S.CFG["site_name"]}, "isBasedOn": p.get("link"),
              "publisher": {"@id": S.BASE + "/#org"}}
        cred = (f'<figcaption>Foto: {E(p["imagem_credito"])}' + (f' (<a href="{E(p["imagem_licenca"])}" target="_blank" rel="noopener">licença</a>)' if p.get("imagem_licenca") else "") + '</figcaption>') if p.get("imagem_credito") else ""
        b = (f'<article class="post"><div class="kick"><a href="/{p["editoria"]}/">{E(S.EDS[p["editoria"]]["nome"])}</a></div><h1>{E(p["titulo"])}</h1>'
             f'<p class="meta">Publicado em <time datetime="{p["data"].isoformat()}">{p["data"]:%d/%m/%Y %H:%M}</time>{" · Fonte: " + E(p["fonte"]) if p.get("fonte") else ""}</p>'
             f'<figure class="cover">{img(S, p, "(max-width: 800px) 100vw, 760px", True, "cover")}{cred}</figure>{p["html"]}</article>')
        S.write(p["url"], S.page(p["titulo"], p.get("resumo", "") or p["titulo"], p["url"], b, og_img=S.BASE + p["imagem"], og_type="article", jsonld=ld, robots="noindex,follow"), idx=False, familia="artigos")
    # módulos do nicho (antes da home, para a home poder linkar seus hubs)
    sys.path.insert(0, str(S.ROOT))
    S.modulos = {}
    for m in S.CFG.get("modulos", []):
        mod = importlib.import_module(m if "." in m else f"nichos.{S.nicho}.{m}")
        S.modulos[m] = mod.build(S) or {}
    institucional(S)
    autores.paginas(S, AUT)
    an = [p for p in posts if p.get("tipo") == "analise"]
    if an:
        S.write("/analises/", S.page(f"Análises | {S.CFG['site_name']}", f"Análises próprias do {S.CFG['site_name']} com dados oficiais, assinadas e revisadas, com fonte e método.", "/analises/",
                                     f'<section class="blk">{sec("Conteúdo próprio", "Análises", tag="h1")}<div class="grid">{"".join(card(S, p, "h2") for p in an)}</div></section>',
                                     crumbs=[("Análises", "/analises/")], jsonld=S.itemlist([(p["titulo"], p["url"]) for p in an])), familia="analises", faq_min=0)
    # editorias
    for s, e in S.EDS.items():
        ps = [p for p in posts if p["editoria"] == s]
        subs = "".join(f'<span class="chip">{E(x)}</span>' for x in e.get("sub", []))
        inner = "".join(card(S, p, "h2") for p in ps[:40]) or '<p class="vazio">Ainda não há matérias nesta editoria. A coleta automática roda a cada 30 minutos.</p>'
        b = f'<section class="blk">{sec("Editoria", e["nome"], tag="h1")}<p class="lead">{E(e.get("descricao", ""))}</p><div class="chips small">{subs}</div><div class="grid">{inner}</div></section>'
        S.write(f"/{s}/", S.page(f"{e['nome']}: notícias | {S.CFG['site_name']}", e.get("descricao", e["nome"]), f"/{s}/", b, faqs=faq_editoria(S, e, ps), crumbs=[(e["nome"], f"/{s}/")],
                                  jsonld=S.itemlist([(p["titulo"], p["url"]) for p in ps])), lastmod=(ps[0]["data"].date().isoformat() if ps else None))
    # home
    from . import home as core_home
    home = importlib.import_module(f"nichos.{S.nicho}.home") if (S.ROOT / "nichos" / S.nicho / "home.py").exists() else core_home
    home.build(S, posts, card=lambda p, h="h3": card(S, p, h), sec=sec, img=lambda p, **k: img(S, p, **k))
    busca(S)
    nf = f'<section class="blk"><h1>Página não encontrada</h1><p>O endereço não existe ou foi movido. Use a <a href="/busca/">busca</a> ou volte ao <a href="/">início</a>.</p></section>'
    (S.OUT / "404.html").write_text(S.page(f"Página não encontrada | {S.CFG['site_name']}", "Página não encontrada.", "/404.html", nf, robots="noindex").replace('href="/', f'href="{S.PREFIX}/').replace('src="/', f'src="{S.PREFIX}/'), encoding="utf-8")
    if S.CFG.get("indexnow_key"): (S.OUT / f"{S.CFG['indexnow_key']}.txt").write_text(S.CFG["indexnow_key"])
    S.qualidade = unicidade(S)
    erros_rede, pct_rede = Q.anti_rede(S.OUT, S.CFG.get("rede_dominios") or [])
    S.errors += erros_rede
    S.qualidade.update(faq_pseo=dict(S.faq_stats), rede_links_pct=pct_rede, ondas_noindex=len(S.ondas))
    quality(S)
    files = sitemaps(S, posts); llms(S)
    broken = linkcheck(S)
    for u, (n, src) in sorted(broken.items(), key=lambda x: -x[1][0])[:30]: print(f"LINK QUEBRADO {u} ({n}x, ex.: {src})")
    print("Unicidade: " + ", ".join(f"{k}: mediana {v['texto_proprio_mediana']}, {v['abaixo_do_corte']} abaixo" for k, v in S.qualidade["unicidade"].items()) + " · similaridade: " + ", ".join(f"{k}={v}" for k, v in S.qualidade["similaridade_jaccard5"].items()))
    if S.ondas: print(f"Ondas: {len(S.ondas)} página(s) em noindex por família ainda não liberada (config indexacao.familias_noindex)")
    if S.thin: print(f"Qualidade: {len(S.thin)} página(s) abaixo do mínimo de palavras em noindex: " + ", ".join(sorted(S.thin)[:8]))
    if S.errors:
        for e in S.errors[:40]: print("ERRO:", e)
    if broken or S.errors: sys.exit(f"ERRO: {len(broken)} destinos quebrados, {len(S.errors)} erros de qualidade")
    indexnow.diff(S)
    saude.build(S, posts)
    fam = {}
    for u, m in S.urls.items(): fam.setdefault(m["familia"], [0, 0])[0 if m["idx"] else 1] += 1
    print("Famílias (indexáveis/noindex):", ", ".join(f"{k}={v[0]}/{v[1]}" for k, v in sorted(fam.items())))
    print(f"OK: {len(S.urls)} páginas, {len(S.indexaveis())} indexáveis, {len(posts)} matérias, noindex_global={S.NOINDEX} -> {S.OUT}")
