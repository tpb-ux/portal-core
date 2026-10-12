#!/usr/bin/env python3
"""Cria um portal novo a partir do portal-core.
Uso: python tools/novo_portal.py <pasta-destino> --nome "Nome" --dominio exemplo.com.br --nicho meu_nicho
Copia core/, ops/, build.py, fetch.py e requirements; gera config.yaml, feeds.yaml e nichos/<nicho>/ a partir do exemplo (noindex_global: true)."""
import argparse, secrets, shutil
from pathlib import Path
R = Path(__file__).resolve().parent.parent
a = argparse.ArgumentParser(); a.add_argument("dest"); a.add_argument("--nome", required=True); a.add_argument("--dominio", required=True); a.add_argument("--nicho", required=True)
x = a.parse_args(); D = Path(x.dest); D.mkdir(parents=True, exist_ok=False)
for f in ("core", "ops"): shutil.copytree(R / f, D / f, ignore=shutil.ignore_patterns("__pycache__"))
for f in ("build.py", "fetch.py", "requirements.txt", ".gitignore"): shutil.copy(R / f, D / f)
(D / "nichos").mkdir(); (D / "nichos/__init__.py").touch(); shutil.copytree(R / "nichos/exemplo", D / "nichos" / x.nicho, ignore=shutil.ignore_patterns("__pycache__"))
for d in ("content", "data", "static"): (D / d).mkdir(exist_ok=True)
cfg = (R / "config.yaml").read_text(encoding="utf-8").replace("Portal Exemplo", x.nome).replace("exemplo.com.br", x.dominio).replace("nicho: exemplo", f"nicho: {x.nicho}").replace("modulos: [exemplo]", "modulos: [exemplo]")
cfg = cfg.replace('indexnow_key: ""', f'indexnow_key: "{secrets.token_hex(16)}"')
(D / "config.yaml").write_text(cfg, encoding="utf-8"); shutil.copy(R / "feeds.yaml", D / "feeds.yaml")
print(f"Portal criado em {D}. Próximos passos: editar config.yaml (editorias, menu, empresa), feeds.yaml (testar cada feed), static/logo.svg, e escrever os módulos em nichos/{x.nicho}/.")
