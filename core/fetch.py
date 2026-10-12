#!/usr/bin/env python3
"""[portal-core] Coleta notícias de feeds RSS (sem IA) e gera content/*.md com resumo curto e link para a fonte.
Uso (na raiz do portal): python -m core.fetch [--max N] [--dry-run]"""
import argparse, datetime as dt, html, re, socket, time, unicodedata, urllib.request
from pathlib import Path
import io
import feedparser, yaml
from PIL import Image

socket.setdefaulttimeout(20)
ROOT = Path.cwd(); CONTENT = ROOT / "content"
_C = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
_F = yaml.safe_load((ROOT / "feeds.yaml").read_text(encoding="utf-8"))
UA = f"Mozilla/5.0 (compatible; {_C['site_name'].replace(' ', '')}Bot/1.0; +{_C['base_url']})"
BRT = dt.timezone(dt.timedelta(hours=-3))
KW = _F.get("palavras_editoria", {})
DEFAULT_ED = _F.get("editoria_padrao") or _C["editorias"][0]["slug"]

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

def slugify(s): return norm(s).replace(" ", "-")[:70].strip("-")

def classify(text):
    t = (text or "").lower(); best, score = DEFAULT_ED, 0
    for ed, words in KW.items():
        sc = sum(t.count(w) for w in words)
        if sc > score: best, score = ed, sc
    return best

LOGI = sorted({w for ws in KW.values() for w in ws} | set(_F.get("palavras_relevancia", [])))

def score(title, summ):
    t, s = (title or "").lower(), (summ or "").lower()
    return sum(3 for w in LOGI if w in t) + sum(1 for w in LOGI if w in s)

def blocked(cfg, src, link, title, summ, trusted=False):
    hay_src = f"{src} {link}".lower(); txt = f"{title} {summ}".lower()
    for b in cfg.get("bloqueio_fontes", []):
        if b.lower() in hay_src: return f"fonte bloqueada ({b})"
    # Feeds confiáveis (portais do setor): palavras bloqueadas valem só no título; o resumo de
    # matérias de carga costuma citar ônibus/passageiros de passagem (ex.: carga aérea, feira Fenatran).
    alvo = title.lower() if trusted else txt
    for b in cfg.get("bloqueio_palavras", []):  # início de palavra: "lula" não casa com "celular"
        if re.search(r"(?<!\w)" + re.escape(b.lower()), alvo):
            ctx = cfg.get("excecoes_contexto", {}).get(b)
            if ctx and any(c.lower() in txt for c in ctx): continue  # ex.: concessionária de rodovia/pedágio
            return f"palavra bloqueada ({b})"
    if trusted: return None
    sc = score(title, summ)
    if sc < cfg.get("nota_minima", 3): return f"nota {sc} < {cfg.get('nota_minima', 3)}"
    return None

def restrito(cfg, ed, title, summ):
    """Restrição temporária por editoria (ex.: período eleitoral): até a data, só passa item com termo exigido no título/resumo."""
    r = (cfg.get("restricao_editoria") or {}).get(ed)
    if not r or dt.date.today().isoformat() > str(r.get("ate", "")): return None
    t = f"{title} {summ}".lower()
    if any(re.search(r"(?<!\w)" + re.escape(w.lower()), t) for w in r.get("bloqueia", [])): return f"restrição temporária ({ed}): termo bloqueado"
    return None if any(w.lower() in t for w in r.get("exige", [])) else f"restrição temporária ({ed}) até {r['ate']}"

def revisar(cfg, remove=False):
    """Reaplica os filtros nas matérias já publicadas pelo coletor."""
    n = 0; trusted = {fd["nome"] for fd in cfg["feeds"] if fd.get("confiavel")}
    for f in sorted(CONTENT.glob("*.md")):
        fm = yaml.safe_load(f.read_text(encoding="utf-8").split("---", 2)[1]) or {}
        if fm.get("gerado_por") != "fetch.py": continue
        img = str(fm.get("imagem", ""))
        why = None if img.startswith("/static/img/") and not img.startswith("/static/img/editoria/") and (ROOT / img.lstrip("/")).exists() else "sem foto própria"
        why = why or blocked(cfg, fm.get("fonte", ""), fm.get("link", ""), fm.get("titulo", ""), fm.get("resumo", ""), fm.get("fonte") in trusted)
        why = why or restrito(cfg, fm.get("editoria"), fm.get("titulo", ""), fm.get("resumo", "")) or restrito(cfg, "*", fm.get("titulo", ""), fm.get("resumo", ""))
        if why:
            n += 1; print(f"- {f.name}: {why}")
            if remove:
                f.unlink()
                with REMOVED.open("a", encoding="utf-8") as r: r.write(fm.get("link", "") + "\n")
                rf = ROOT / "data" / "redirects.yaml"; rd = (yaml.safe_load(rf.read_text()) or {}) if rf.exists() else {}
                rd[f"/{fm.get('editoria')}/{f.stem}/"] = f"/{fm.get('editoria')}/"; rf.write_text(yaml.safe_dump(rd, allow_unicode=True), encoding="utf-8")
    print(f"{n} matéria(s) fora dos filtros{' removida(s)' if remove else ''}.")

def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    s = re.sub(r"(The post|O post)\b.*$", "", s, flags=re.S)
    return re.sub(r"\s+", " ", s).strip()

def short(s, n=260):
    if len(s) <= n: return s
    return s[:n].rsplit(" ", 1)[0].rstrip(",;:.-–[ ") + "…"

def og_image(url):
    if "news.google.com" in url: return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        h = urllib.request.urlopen(req, timeout=10).read(300000).decode("utf-8", "ignore")
        m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', h) or \
            re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image', h)
        return html.unescape(m.group(1)) if m and m.group(1).startswith("http") else None
    except Exception: return None

def feed_image(e):
    for k in ("media_content", "media_thumbnail"):
        for m in e.get(k) or []:
            if m.get("url", "").startswith("http"): return m["url"]
    for l in e.get("links", []):
        if l.get("rel") == "enclosure" and l.get("type", "").startswith("image"): return l["href"]
    m = re.search(r'<img[^>]+src=["\'](https?://[^"\']+)', (e.get("content") or [{}])[0].get("value", "") + e.get("summary", ""))
    return m.group(1) if m else None

REMOVED = ROOT / "data" / "removidos.txt"   # links rejeitados/removidos: nunca reimportar

IMG = ROOT / "static" / "img"

def save_image(url, slug):
    """Baixa a imagem, converte para WebP (1200px e 480px). Retorna dict de front matter ou None."""
    if not url or not url.startswith("http"): return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": url})
        data = urllib.request.urlopen(req, timeout=20).read(15_000_000)
        im = Image.open(io.BytesIO(data)); im.load()
        if im.width < 300: return None
        im = im.convert("RGB"); IMG.mkdir(parents=True, exist_ok=True)
        big = im if im.width <= 1200 else im.resize((1200, round(im.height * 1200 / im.width)), Image.LANCZOS)
        big.save(IMG / f"{slug}.webp", "WEBP", quality=80, method=6)
        im.resize((480, round(im.height * 480 / im.width)), Image.LANCZOS).save(IMG / f"{slug}-480.webp", "WEBP", quality=78, method=6)
        return {"imagem": f"/static/img/{slug}.webp", "imagem_w": big.width, "imagem_h": big.height, "imagem_origem": url}
    except Exception as ex:
        print(f"  ! imagem falhou ({url[:60]}): {ex}"); return None

def editoria_image(ed):
    return {"imagem": f"/static/img/editoria/{ed}.webp", "imagem_w": 1200, "imagem_h": 630}

def img_fm(info, src_name):
    out = [f"imagem: {q(info['imagem'])}", f"imagem_w: {info['imagem_w']}", f"imagem_h: {info['imagem_h']}"]
    if info.get("imagem_origem"): out += [f"imagem_credito: {q(src_name)}", f"imagem_origem: {q(info['imagem_origem'])}"]
    return "\n".join(out)

def migrar():
    """Converte matérias antigas (imagem remota/vazia) para WebP local ou imagem da editoria."""
    for f in sorted(CONTENT.glob("*.md")):
        raw = f.read_text(encoding="utf-8"); _, fm_txt, body = raw.split("---", 2)
        fm = yaml.safe_load(fm_txt) or {}
        if str(fm.get("imagem", "")).startswith("/static/img/"): continue
        info = save_image(fm.get("imagem", ""), f.stem)
        if not info: continue
        lines = [l for l in fm_txt.strip("\n").split("\n") if not l.startswith("imagem")]
        lines.insert(4, img_fm(info, fm.get("fonte", "")))
        f.write_text("---\n" + "\n".join(lines) + "\n---" + body, encoding="utf-8")
        print(f"~ {f.name}: {info['imagem']}")

def existing():
    links, titles = set(), set()
    if REMOVED.exists(): links |= {l.strip() for l in REMOVED.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}
    for f in CONTENT.glob("*.md"):
        fm = yaml.safe_load(f.read_text(encoding="utf-8").split("---", 2)[1]) or {}
        if fm.get("link"): links.add(fm["link"])
        titles.add(norm(fm.get("titulo", "")))
    return links, titles

def q(s): return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--max", type=int); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--migrar-imagens", action="store_true")
    ap.add_argument("--revisar", action="store_true", help="lista matérias publicadas que violam os filtros")
    ap.add_argument("--remover", action="store_true", help="com --revisar, apaga essas matérias")
    a = ap.parse_args()
    cfg = yaml.safe_load((ROOT / "feeds.yaml").read_text(encoding="utf-8"))
    if a.migrar_imagens: return migrar()
    if a.revisar: return revisar(cfg, a.remover)
    limit = a.max or cfg.get("max_por_execucao", 12); per = cfg.get("max_por_feed", 3)
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=cfg.get("max_idade_dias", 3))
    CONTENT.mkdir(exist_ok=True); links, titles = existing(); new = 0; erros = []; feeds_st = []
    for fd in cfg["feeds"]:
        st_ = {"nome": fd["nome"], "url": fd["url"], "status": "ok", "itens": 0, "itens_com_imagem_no_feed": 0, "novas": 0, "descartadas_sem_foto": 0}; feeds_st.append(st_)
        try:
            raw = urllib.request.urlopen(urllib.request.Request(fd["url"], headers={"User-Agent": UA}), timeout=20).read()
            d = feedparser.parse(raw)
        except Exception as ex:
            print(f"! {fd['nome']}: erro {ex}"); erros.append({"feed": fd["nome"], "url": fd["url"], "erro": str(ex)[:120]}); st_.update(status="erro", erro=str(ex)[:120]); continue
        st_["itens"] = len(d.entries); st_["itens_com_imagem_no_feed"] = sum(1 for e in d.entries if feed_image(e))
        if not d.entries: print(f"! {fd['nome']}: sem itens"); erros.append({"feed": fd["nome"], "url": fd["url"], "erro": "sem itens"}); st_["status"] = "vazio"; continue
        if new >= limit: continue  # limite da execução: só registra a saúde do feed
        got = 0
        for e in d.entries:
            if got >= fd.get("max", per) or new >= limit: break
            link, title = e.get("link", "").strip(), clean(e.get("title", ""))
            src_name = fd["nome"]; gn = "news.google.com" in fd["url"]
            if gn:
                st = (e.get("source") or {}).get("title")
                if st:
                    src_name = st
                    title = re.sub(r"\s+-\s+" + re.escape(st) + r"\s*$", "", title)
            if len(title) < 25 or title.endswith("|"): continue
            if not link or not title or link in links or norm(title) in titles: continue
            tp = e.get("published_parsed") or e.get("updated_parsed")
            when = dt.datetime(*tp[:6], tzinfo=dt.timezone.utc) if tp else dt.datetime.now(dt.timezone.utc)
            if when < cutoff: continue
            summ = "" if gn else clean(e.get("summary", ""))
            if len(summ) < 40 or norm(summ).startswith(norm(title)[:40]):
                summ = f"{title}. Notícia publicada por {src_name}."
            why = blocked(cfg, src_name, link, title, "" if summ.startswith(title) else summ, fd.get("confiavel", False))
            if why: print(f"  x {title[:70]} ({src_name}): {why}"); continue
            resumo = short(summ)
            ed = fd.get("editoria") or classify(title + " " + summ)
            why = restrito(cfg, ed, title, summ) or restrito(cfg, "*", title, summ)
            if why: print(f"  x {title[:70]} ({src_name}): {why}"); continue
            when = when.astimezone(BRT).replace(microsecond=0)
            fn = CONTENT / f"{when:%Y-%m-%d}-{slugify(title)}.md"
            if fn.exists(): continue
            info = None if a.dry_run else (save_image(feed_image(e), fn.stem) or save_image(og_image(link), fn.stem))  # imagem do feed inválida -> tenta og:image
            if not info and not a.dry_run:  # só notícias com foto própria da fonte
                print(f"  - sem foto: {title[:60]}"); st_["descartadas_sem_foto"] += 1; continue
            body = (f"---\ntitulo: {q(title)}\ndata: {when.isoformat()}\neditoria: {ed}\nresumo: {q(resumo)}\n"
                    f"{img_fm(info, src_name)}\nfonte: {q(src_name)}\nlink: {q(link)}\ngerado_por: fetch.py\n---\n"
                    f"{resumo}\n\n**[Leia na íntegra em {src_name} →]({link})**\n\n"
                    f"<small>{_F.get("aviso_resumo", "Resumo automático a partir do feed público de {f}. Os direitos do conteúdo original pertencem à fonte.").format(f=src_name)}</small>\n")
            print(f"+ [{ed}] {title[:80]} ({src_name})")
            if not a.dry_run: fn.write_text(body, encoding="utf-8")
            links.add(link); titles.add(norm(title)); got += 1; new += 1; st_["novas"] += 1
    print(f"{new} matéria(s) nova(s).")
    if not a.dry_run:
        import json, os
        sf = ROOT / "data" / "saude_coleta.json"; old = json.loads(sf.read_text()) if sf.exists() else {}
        agora = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"); ev = os.environ.get("PORTAL_EVENTO") or os.environ.get("GITHUB_EVENT_NAME", "local")
        ult = old.get("ultimas_execucoes", {}); ult[ev] = agora
        sf.write_text(json.dumps({"hora": agora, "evento": ev, "run_id": os.environ.get("GITHUB_RUN_ID"), "novas": new, "erros": erros, "feeds": feeds_st,
                                  "ultimas_execucoes": ult}, ensure_ascii=False, indent=1), encoding="utf-8")

if __name__ == "__main__": main()
