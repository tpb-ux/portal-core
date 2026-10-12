"""Autores (schema Person), análises próprias com fluxo de revisão e sitemap de notícias.
data/autores.yaml: entradas sem nome ficam ocultas (nenhuma página /autores/ nem Person é publicado).
Análise (content/*.md com tipo: analise) só vai ao ar com status: aprovado, autor e revisado_por cadastrados
e sem marcas [[REVISÃO]]. Rascunhos ficam em drafts/ (o build não lê)."""
import datetime as dt
import yaml
from .site import E

def carregar(S):
    f = S.ROOT / "data" / "autores.yaml"
    lst = (yaml.safe_load(f.read_text(encoding="utf-8")) or {}).get("autores", []) if f.exists() else []
    return {a["slug"]: a for a in lst if a.get("slug") and (a.get("nome") or "").strip()}

def person(S, a):
    p = {"@type": "Person", "@id": f"{S.BASE}/autores/{a['slug']}/#pessoa", "name": a["nome"], "url": f"{S.BASE}/autores/{a['slug']}/", "worksFor": {"@id": S.BASE + "/#org"}}
    if a.get("cargo"): p["jobTitle"] = a["cargo"]
    if a.get("foto"): p["image"] = S.BASE + a["foto"]
    sa = [x for x in a.get("sameAs") or [] if x]
    if sa: p["sameAs"] = sa
    return p

def publicavel(p, au):
    if p.get("tipo") != "analise": return True
    ok = p.get("status") == "aprovado" and p.get("autor") in au and p.get("revisado_por") in au and "[[REVIS" not in p.get("html", "")
    if not ok: print(f"Análise retida (sem aprovação/autor/revisor ou com marca de revisão): {p.get('titulo', '')[:70]}")
    return ok

def paginas(S, au):
    if not au: return []
    for a in au.values():
        u = f"/autores/{a['slug']}/"
        b = (f'<article class="post"><h1>{E(a["nome"])}</h1>' + (f'<p class="meta">{E(a["cargo"])}</p>' if a.get("cargo") else "") + (f'<p>{E(a["bio"])}</p>' if a.get("bio") else "")
             + "".join(f'<p><a href="{E(x)}" rel="me noopener" target="_blank">{E(x)}</a></p>' for x in a.get("sameAs") or [] if x) + "</article>")
        S.write(u, S.page(f"{a['nome']} | {S.CFG['site_name']}", (a.get("bio") or f"{a['nome']}, {a.get('cargo', 'autor')} do {S.CFG['site_name']}, com as análises assinadas.")[:160], u, b,
                          crumbs=[("Autores", "/autores/"), (a["nome"], u)], jsonld={"@type": "ProfilePage", "mainEntity": person(S, a)}), faq_min=0)
    b = '<article class="post"><h1>Autores e editores</h1><ul>' + "".join(f'<li><a href="/autores/{a["slug"]}/">{E(a["nome"])}</a>{(" · " + E(a["cargo"])) if a.get("cargo") else ""}</li>' for a in au.values()) + "</ul></article>"
    S.write("/autores/", S.page(f"Autores | {S.CFG['site_name']}", f"Quem escreve e revisa o conteúdo próprio do {S.CFG['site_name']}: jornalistas, editores e revisores.", "/autores/", b, crumbs=[("Autores", "/autores/")]), faq_min=0)
    return list(au)

def sitemap_noticias(S, posts):
    agora = dt.datetime.now(dt.timezone.utc)
    own = [p for p in posts if p.get("tipo") == "analise" and agora - p["data"] <= dt.timedelta(hours=48) and S.urls.get(p["url"], {}).get("idx")]
    rows = "".join(f"<url><loc>{S.BASE}{p['url']}</loc><news:news><news:publication><news:name>{E(S.CFG['site_name'])}</news:name><news:language>pt</news:language></news:publication>"
                   f"<news:publication_date>{p['data'].isoformat()}</news:publication_date><news:title>{E(p['titulo'])}</news:title></news:news></url>" for p in own)
    (S.OUT / "sitemap-noticias.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">' + rows + "</urlset>", encoding="utf-8")
    return len(own)
