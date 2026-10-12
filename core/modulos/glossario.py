"""Módulo genérico de glossário: data/glossario.yaml (+ data/glossario/*.yaml) -> /glossario/ e /glossario/<termo>/.

Cada termo: termo, slug?, sigla?, categoria, resumo (1 frase, começa em minúscula: "é ..."), definicao (markdown),
contexto (markdown: contexto e exemplo), exemplos?, base_legal [{nome,url}], relacionados [slug],
sinonimos? (para o autolink), autolink? (false ou lista exata de variantes), imagem (chave de data/glossario_imagens.yaml),
faqs [{p,r}] (>= 5). Arquivos em data/glossario/ podem trazer `termos:` (novos) e `complementos:` ({slug: campos})
para completar termos existentes sem reescrevê-los.
"""
import datetime as dt, html as H, json, re, markdown, yaml
from pathlib import Path
from core.site import E, slugify


def carregar(root):
    root = Path(root); f = root / "data/glossario.yaml"
    if not f.exists(): return None, []
    G = yaml.safe_load(f.read_text(encoding="utf-8")); termos = list(G.get("termos") or []); comp = {}
    d = root / "data/glossario"
    for x in sorted(d.glob("*.yaml")) if d.exists() else []:
        y = yaml.safe_load(x.read_text(encoding="utf-8")) or {}
        termos += y.get("termos") or []; comp.update(y.get("complementos") or {})
    F = yaml.safe_load((root / "data/glossario_fontes.yaml").read_text(encoding="utf-8")) if (root / "data/glossario_fontes.yaml").exists() else {}
    for t in termos:
        t["slug"] = t.get("slug") or slugify(t["termo"])
        t.update({k: v for k, v in (comp.get(t["slug"]) or {}).items() if k not in t or not t[k]})
        for x in t.get("base_legal") or []:
            if str(x.get("url", "")).startswith("@"):
                if x["url"][1:] not in F: raise SystemExit(f"glossário: fonte desconhecida {x['url']} em {t['slug']}")
                x["url"] = F[x["url"][1:]]
    return G, termos


def _imagem(S, t, IMG, cache):
    """Foto livre (Wikimedia Commons) recortada 16:9, gravada como /static/img/glossario/<slug>.webp (+ -800, -480)."""
    k = t.get("imagem"); meta = IMG.get(k) if k else None
    src = S.ROOT / "data/glossario_imagens" / f"{k}.webp"
    if not meta or not src.exists(): S.errors.append(f"glossário: {t['slug']} sem imagem válida ({k})"); return None
    from PIL import Image
    dest = S.OUT / "static/img/glossario"; dest.mkdir(parents=True, exist_ok=True)
    for w in (1200, 800, 480):
        nome = f"{t['slug']}{'' if w == 1200 else '-' + str(w)}.webp"; c = cache / f"{k}-{w}.webp"
        if not c.exists() or c.stat().st_mtime < src.stat().st_mtime:
            im = Image.open(src).convert("RGB"); W, Hh = im.size; th = W * 9 // 16
            if th <= Hh: top = int((Hh - th) * meta.get("foco", 0.5)); im = im.crop((0, top, W, top + th))
            else: tw = Hh * 16 // 9; left = (W - tw) // 2; im = im.crop((left, 0, left + tw, Hh))
            im.resize((w, w * 9 // 16), Image.LANCZOS).save(c, "WEBP", quality={1200: 72, 800: 66, 480: 66}[w], method=6)
        (dest / nome).write_bytes(c.read_bytes())
    return meta


def build(S):
    G, termos = carregar(S.ROOT)
    if not G: return {}
    nome = G.get("nome", "Glossário"); atual = str(G.get("atualizado", dt.date.today()))
    cats = {c["slug"]: c for c in G.get("categorias", [])}
    IMG = yaml.safe_load((S.ROOT / "data/glossario_imagens.yaml").read_text(encoding="utf-8")) if (S.ROOT / "data/glossario_imagens.yaml").exists() else {}
    cache = S.ROOT / "data/cache/glossario"; cache.mkdir(parents=True, exist_ok=True)
    by = {}
    for t in termos:
        if t["slug"] in by: S.errors.append(f"glossário: slug duplicado {t['slug']}")
        by[t["slug"]] = t
    for t in termos:
        for r in t.get("relacionados", []):
            if r not in by: S.errors.append(f"glossário: {t['slug']} relaciona termo inexistente {r}")
        if t.get("categoria") not in cats: S.errors.append(f"glossário: {t['slug']} sem categoria válida ({t.get('categoria')})")
        if len(t.get("faqs", [])) < 5: S.errors.append(f"glossário: {t['slug']} com {len(t.get('faqs', []))} FAQs (mínimo 5)")
        if not t.get("base_legal"): S.errors.append(f"glossário: {t['slug']} sem base legal")
    S.gl_stats = {"termos": len(termos), "por_categoria": {}, "palavras": [], "faqs": 0}
    for t in termos:
        u = f"/glossario/{t['slug']}/"; c = cats.get(t.get("categoria"), {"nome": "", "slug": ""})
        rel = [by[r] for r in t.get("relacionados", []) if r in by]
        bl = "".join(f'<li><a href="{E(x["url"])}" target="_blank" rel="noopener">{E(x["nome"])}</a></li>' for x in t.get("base_legal", []))
        ex = "".join(f"<li>{markdown.markdown(x)[3:-4]}</li>" for x in t.get("exemplos", []))
        sig = f" ({E(t['sigla'])})" if t.get("sigla") else ""
        meta = _imagem(S, t, IMG, cache); fig = ""; img_url = None
        if meta:
            img_url = f"/static/img/glossario/{t['slug']}.webp"
            alt = f"{meta['descricao']}. Imagem ilustrativa do verbete {t['termo']}"
            lic = f'<a href="{E(meta["licenca_url"])}" target="_blank" rel="noopener">{E(meta["licenca"])}</a>' if meta.get("licenca_url") else E(meta["licenca"])
            fig = (f'<figure class="cover"><img class="cover" src="{img_url}" srcset="/static/img/glossario/{t["slug"]}-480.webp 480w, /static/img/glossario/{t["slug"]}-800.webp 800w, {img_url} 1200w" sizes="(max-width: 800px) 100vw, 760px" '
                   f'width="1200" height="675" alt="{E(alt)}" fetchpriority="high" decoding="async">'
                   f'<figcaption>Foto: <a href="{E(meta["pagina"])}" target="_blank" rel="noopener">{E(meta["autor"])}</a>, {lic}, via Wikimedia Commons</figcaption></figure>')
        h = (f'<article class="post gl"><div class="kick"><a href="/glossario/#cat-{c["slug"]}">{E(c["nome"])}</a></div><h1>{E(t["termo"])}{sig}: o que é</h1>'
             f'<p class="snippet"><strong>{E(t["termo"])}</strong> {E(t["resumo"])}</p>{fig}<h2>O que é</h2>{markdown.markdown(t["definicao"])}'
             + (f'<h2>Contexto e exemplo</h2>{markdown.markdown(t["contexto"])}' if t.get("contexto") else "")
             + (f"<ul>{ex}</ul>" if ex else "")
             + (f'<h2>Base legal e fontes oficiais</h2><ul class="refs">{bl}</ul>' if bl else "")
             + (f'<div class="relbox"><h2>Termos relacionados</h2><ul>' + "".join(f'<li><a href="/glossario/{r["slug"]}/">{E(r["termo"])}</a> {E(r["resumo"][:110])}</li>' for r in rel) + "</ul></div>" if rel else "")
             + f'<p class="upd">Revisado em {"/".join(reversed(atual.split("-")))}. Texto próprio do {E(S.CFG["site_name"])} com base nas normas citadas; não substitui a leitura do texto oficial.</p></article>')
        ld = {"@type": "DefinedTerm", "@id": S.BASE + u + "#termo", "name": t["termo"], "description": (t["termo"] + " " + t["resumo"]), "url": S.BASE + u,
              "inDefinedTermSet": {"@type": "DefinedTermSet", "@id": S.BASE + "/glossario/#set", "name": nome, "url": S.BASE + "/glossario/"},
              **({"termCode": t["sigla"]} if t.get("sigla") else {}), **({"image": S.BASE + img_url} if img_url else {}),
              **({"alternateName": [x for x in ([t["sigla"]] if t.get("sigla") else []) + list(t.get("sinonimos") or [])]} if (t.get("sigla") or t.get("sinonimos")) else {})}
        faqs = [(x["p"], E(x["r"])) for x in t.get("faqs", [])]
        S.write(u, S.page(f"{t['termo']}{' (' + t['sigla'] + ')' if t.get('sigla') else ''}: o que é e como funciona | {S.CFG['site_name']}", f"{t['termo']} {t['resumo']}", u, h,
                          faqs=faqs, crumbs=[(nome, "/glossario/"), (c["nome"], f"/glossario/#cat-{c['slug']}"), (t["termo"], u)], jsonld=ld,
                          og_img=(S.BASE + img_url) if img_url else None), familia="glossario", lastmod=atual, image=img_url)
        S.gl_stats["por_categoria"][c["nome"]] = S.gl_stats["por_categoria"].get(c["nome"], 0) + 1
        S.gl_stats["faqs"] += len(faqs)
        S.gl_stats["palavras"].append(len(re.sub(r"<[^>]+>", " ", h).split()) + sum(len((a + " " + b).split()) for a, b in faqs))
    # hub: busca, categorias e índice A-Z
    def li(t, resumo=True):
        k = " ".join([t["termo"], t.get("sigla", ""), " ".join(t.get("sinonimos") or [])]).lower()
        return f'<li data-k="{E(k)}"><a href="/glossario/{t["slug"]}/"><strong>{E(t["termo"])}{" (" + E(t["sigla"]) + ")" if t.get("sigla") else ""}</strong>' + (f' {E(t["resumo"][:96].rstrip())}…' if resumo else "") + "</a></li>"
    ordem = sorted(termos, key=lambda x: slugify(x["termo"]))
    chips = "".join(f'<a class="chip" href="#cat-{s}">{E(c["nome"])} <span class="n">{sum(1 for t in termos if t.get("categoria") == s)}</span></a>' for s, c in cats.items())
    blocos = "".join(f'<div class="az glcat" id="cat-{s}"><h2>{E(c["nome"])}</h2><p class="lead small">{E(c.get("descricao", ""))}</p><ul>' + "".join(li(t) for t in ordem if t.get("categoria") == s) + "</ul></div>" for s, c in cats.items())
    letras = {}
    for t in ordem: letras.setdefault(slugify(t["termo"])[0].upper(), []).append(t)
    nav = "".join(f'<a href="#l-{l}">{l}</a>' for l in letras)
    az = "".join(f'<div class="az glaz" id="l-{l}"><h3>{l}</h3><ul>' + "".join(li(t, False) for t in ts) + "</ul></div>" for l, ts in letras.items())
    js = ("<script>(function(){var q=document.getElementById('glq'),n=document.getElementById('gln');if(!q)return;"
          "function f(s){return s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase()}"
          "q.addEventListener('input',function(){var v=f(q.value.trim()),c=0;document.querySelectorAll('.glcat li,.glaz li').forEach(function(li){var ok=!v||f(li.getAttribute('data-k')+' '+li.textContent).indexOf(v)>-1;li.hidden=!ok;if(ok&&li.closest('.glcat'))c++});"
          "document.querySelectorAll('.glcat,.glaz').forEach(function(d){d.hidden=!d.querySelector('li:not([hidden])')});n.textContent=v?c+' termo(s) encontrado(s)':''})})();</script>")
    body = (f'<section class="blk"><h1>{E(nome)}: {len(termos)} termos explicados</h1><p class="lead">{E(G.get("descricao", ""))}</p>'
            f'<form class="glbusca" role="search" onsubmit="return false"><label for="glq">Buscar no glossário</label><input id="glq" type="search" placeholder="Ex.: emenda de relator, ADPF, quociente" autocomplete="off"><span id="gln" aria-live="polite"></span></form>'
            f'<h2 class="glh">Categorias</h2><div class="chips glchips">{chips}</div>{blocos}'
            f'<h2 class="glh" id="az">Índice de A a Z</h2><div class="letters">{nav}</div>{az}</section>{js}')
    faqs = [(x["p"], E(x["r"])) for x in G.get("faqs", [])]
    S.write("/glossario/", S.page(f"{nome}: {len(termos)} termos explicados | {S.CFG['site_name']}", G.get("descricao", nome), "/glossario/", body, faqs=faqs, crumbs=[(nome, "/glossario/")],
                                  jsonld={"@type": "DefinedTermSet", "@id": S.BASE + "/glossario/#set", "name": nome, "url": S.BASE + "/glossario/",
                                          "hasDefinedTerm": [{"@type": "DefinedTerm", "@id": S.BASE + f"/glossario/{t['slug']}/#termo", "name": t["termo"], "url": S.BASE + f"/glossario/{t['slug']}/"} for t in termos]}), lastmod=atual)
    return {"termos": termos}
