"""Home genérica: destaque + laterais, blocos por editoria, atalhos de dados (config.menu.barra) e FAQ (config.home_faqs)."""
from .site import E
def build(S, posts, card, sec, img, extra_html=""):
    c = S.CFG; body = f'<h1 class="sr-only">{E(c["site_name"])}: {E(c["tagline"])}</h1>'
    if posts:
        m = posts[0]; side = posts[1:5]
        body += (f'<div class="hero"><a class="hero-main" href="{m["url"]}"><div class="htxt"><div class="kick">Destaque <span>• {m["data"]:%d/%m/%Y}</span></div><h2>{E(m["titulo"])}</h2><p>{E(m.get("resumo", ""))}</p></div>'
                 f'{img(m, sizes="(max-width: 860px) 100vw, 660px", priority=True)}</a><div class="side">'
                 + "".join(f'<a class="mini" href="{p["url"]}">{img(p, sizes="96px")}<div><span class="kick">{E(S.EDS[p["editoria"]]["nome"])}</span><h3>{E(p["titulo"])}</h3></div></a>' for p in side) + "</div></div>")
    body += extra_html
    for s, e in S.EDS.items():
        ps = [p for p in posts if p["editoria"] == s][:4]
        if ps: body += f'<section class="blk">{sec("As últimas em", e["nome"], f"/{s}/")}<div class="grid">{"".join(card(p) for p in ps)}</div></section>'
    barra = (c.get("menu") or {}).get("barra", []) + (c.get("menu") or {}).get("referencia", [])
    if barra: body += '<section class="blk refbox"><h2 class="st"><span>Referência</span><strong>Dados e ferramentas</strong></h2><div class="chips">' + "".join(f'<a class="chip" href="{u}">{E(n)}</a>' for n, u in barra) + "</div></section>"
    faqs = [(x["p"], x["r"]) for x in c.get("home_faqs", [])]
    S.write("/", S.page(c.get("home_titulo", f"{c['site_name']}: {c['tagline']}"), c.get("descricao", c["tagline"]), "/", body, faqs=faqs,
                        jsonld=S.itemlist([(p["titulo"], p["url"]) for p in posts[:20]])), lastmod=posts[0]["data"].date().isoformat() if posts else None)
