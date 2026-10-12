"""Alerta operacional sem rede: grava ALERTA.txt (vazio = sem alerta). Uso: python -m core.alerta [raiz] [passos_falhos...]"""
import datetime as dt, json, sys
from pathlib import Path
def main(root=".", falhos=()):
    R = Path(root); L = []
    s = json.loads((R / "data/saude.json").read_text()) if (R / "data/saude.json").exists() else {}
    lim = 24
    mr = (s.get("materias") or {}).get("mais_recente")
    if not mr: L.append("- Nenhuma matéria publicada.")
    elif mr["idade_horas"] > lim: L.append(f"- Matéria mais recente tem {mr['idade_horas']:.0f} h (limite {lim} h).")
    for f in (s.get("feeds") or {}).get("lista", []):
        if f.get("status") != "ok": L.append(f"- Feed {f['nome']}: {f.get('status')} {f.get('erro', '')}")
    for p in falhos: L.append(f"- Passo falhou: {p}")
    (R / "ALERTA.txt").write_text((f"Alerta {s.get('portal', '')} {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC\n" + "\n".join(L) + "\n") if L else "", encoding="utf-8")
    print("\n".join(L) or "Sem alertas")
if __name__ == "__main__": main(sys.argv[1] if len(sys.argv) > 1 else ".", sys.argv[2:])
