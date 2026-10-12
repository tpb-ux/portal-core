"""Módulo genérico de glossário: data/glossario.yaml -> /glossario/, /glossario/<termo>/.
Cada termo: termo, sigla?, resumo (1 frase), definicao (markdown), base_legal [{nome,url}], exemplos?, relacionados [slug], faqs [{p,r}] (>=5)."""
import datetime as dt, re, markdown, yaml
from core.site import E, slugify

def build(S):
    f = S.ROOT / "data/glossario.yaml"
    if not f.exists(): return {}
    G = yaml.safe_load(f.read_text(encoding="utf-8")); termos = G["termos"]; nome = G.get("nome", "Glossário"); atual = str(G.get("atualizado", dt.date.today()))
    for t in termos: t["slug"] = t.get("slug") or slugify(t["termo"])
    by = {t["slug"]: t for t in termos}
    for t in termos:
        for r in t.get("relacionados", []):
            if r not in by: S.errors.append(f"glossário: {t['slug']} relaciona termo inexistente {r}")
    for t in termos:
        u = f"/glossario/{t['slug']}/"
        rel = [by[r] for r in t.get("relacionados", []) if r in by]
        bl = "".join(f'<li><a href="{x["url"]}" rel="noopener">{E(x["nome"])}</a></li>' for x in t.get("base_legal", []))
        ex = "".join(f"<li>{E(x)}</li>" for x in t.get("exemplos", []))
        sig = f" ({E(t['sigla'])})" if t.get("sigla") else ""
        h = (f'<article class="post"><div class="kick"><a href="/glossario/">{E(nome)}</a></div><h1>{E(t["termo"])}{sig}: o que é</h1>'
             f'<p class="snippet"><strong>{E(t["termo"])}</strong> {E(t["resumo"])}</p>{markdown.markdown(t["definicao"])}'
             + (f"<h2>Exemplos</h2><ul>{ex}</ul>" if ex else "") + (f"<h2>Base legal e fontes oficiais</h2><ul class=\"refs\">{bl}</ul>" if bl else "")
             + (f'<div class="relbox"><h2>Termos relacionados</h2><ul>' + "".join(f'<li><a href="/glossario/{r["slug"]}/">{E(r["termo"])}</a> {E(r["resumo"])}</li>' for r in rel) + "</ul></div>" if rel else "")
             + f'<p class="upd">Revisado em {atual}. Texto próprio do {E(S.CFG["site_name"])} com base nas normas citadas.</p></article>')
        ld = {"@type": "DefinedTerm", "name": t["termo"], "description": t["resumo"], "url": S.BASE + u, "inDefinedTermSet": S.BASE + "/glossario/", **({"termCode": t["sigla"]} if t.get("sigla") else {})}
        S.write(u, S.page(f"{t['termo']}: o que é e como funciona | {S.CFG['site_name']}", f"{t['termo']} {t['resumo']}", u, h,
                          faqs=[(x["p"], E(x["r"])) for x in t.get("faqs", [])], crumbs=[(nome, "/glossario/"), (t["termo"], u)], jsonld=ld), familia="glossario", lastmod=atual)
    letras = {}
    for t in sorted(termos, key=lambda x: slugify(x["termo"])): letras.setdefault(slugify(t["termo"])[0].upper(), []).append(t)
    nav = "".join(f'<a href="#l-{l}">{l}</a>' for l in letras)
    body = f'<section class="blk"><h1>{E(nome)}</h1><p class="lead">{E(G.get("descricao", ""))}</p><div class="letters">{nav}</div>' + "".join(
        f'<div class="az" id="l-{l}"><h2>{l}</h2><ul>' + "".join(f'<li><a href="/glossario/{t["slug"]}/"><strong>{E(t["termo"])}</strong> {E(t["resumo"][:90])}</a></li>' for t in ts) + "</ul></div>" for l, ts in letras.items()) + "</section>"
    faqs = [(x["p"], E(x["r"])) for x in G.get("faqs", [])]
    S.write("/glossario/", S.page(f"{nome}: {len(termos)} termos explicados | {S.CFG['site_name']}", G.get("descricao", nome), "/glossario/", body, faqs=faqs, crumbs=[(nome, "/glossario/")],
                                  jsonld={"@type": "DefinedTermSet", "name": nome, "url": S.BASE + "/glossario/", "hasDefinedTerm": [{"@type": "DefinedTerm", "name": t["termo"], "url": S.BASE + f"/glossario/{t['slug']}/"} for t in termos]}), lastmod=atual)
    return {"termos": termos}
