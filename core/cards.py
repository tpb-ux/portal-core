"""Card de capa próprio para matérias (sem foto de terceiros e sem IA): título, editoria, fonte e data
desenhados com Pillow. Grava <dest>.webp (1200x630) e <dest>-480.webp no mesmo caminho da foto antiga,
para que as URLs de imagem já publicadas continuem funcionando."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONTES = ["/usr/share/fonts/truetype/sand-box/google/Open Sans/OpenSans-VariableFont_wdth,wght.ttf",
          "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]

def _font(size, peso="Bold"):
    for f in FONTES:
        if Path(f).exists():
            try:
                ft = ImageFont.truetype(f, size)
                try: ft.set_variation_by_name(peso)
                except Exception: pass
                return ft
            except Exception: continue
    return ImageFont.load_default()

def _hex(c): c = c.lstrip("#"); return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))

def _quebra(d, txt, ft, larg, max_l):
    linhas, cur = [], ""
    for w in txt.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=ft) <= larg: cur = t
        else:
            if cur: linhas.append(cur)
            cur = w
    if cur: linhas.append(cur)
    if len(linhas) > max_l:
        linhas = linhas[:max_l]; l = linhas[-1]
        while d.textlength(l + "…", font=ft) > larg and " " in l: l = l.rsplit(" ", 1)[0]
        linhas[-1] = l + "…"
    return linhas

def card(dest, titulo, *, marca, editoria="", rodape="", cor="#C93D17", escuro="#2E333D"):
    """dest: caminho sem extensão ou com .webp. Retorna (w, h)."""
    dest = Path(str(dest)[:-5] if str(dest).endswith(".webp") else dest)
    W, H = 1200, 630; A, D = _hex(cor), _hex(escuro); L = (232, 234, 236)
    im = Image.new("RGB", (W, H), D); d = ImageDraw.Draw(im)
    tex = tuple(min(255, c + 8) for c in D)
    for i in range(-H, W, 60): d.line([(i, H), (i + H, 0)], fill=tex, width=18)
    d.rectangle([0, H - 14, W, H], fill=A); d.rectangle([70, 80, 80, 140], fill=A)
    d.text((100, 78), marca.upper(), font=_font(30), fill=A)
    if editoria: d.text((100, 116), editoria, font=_font(26, "Regular"), fill=L)
    for size, max_l in ((64, 4), (56, 5), (48, 6)):
        ft = _font(size, "ExtraBold"); ls = _quebra(d, titulo, ft, W - 200, max_l)
        if len(ls) <= max_l and len(ls) * size * 1.18 <= 360: break
    y = 190
    for l in ls: d.text((100, y), l, font=ft, fill=(255, 255, 255)); y += int(size * 1.18)
    if rodape: d.text((100, H - 70), rodape, font=_font(24, "Regular"), fill=L)
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(f"{dest}.webp", "WEBP", quality=82, method=6)
    im.resize((480, 252), Image.LANCZOS).save(f"{dest}-480.webp", "WEBP", quality=78, method=6)
    return W, H
