# Migração futura do Modal News para o portal-core

Decisão (12/10/2026): **o Modal News não foi alterado.** O portal-core é uma cópia derivada e generalizada do código dele (`build.py`, `fetch.py`, `saude.py`, `indexnow.py`, `tools/alerta.py`, `static/style.css`). Migrar agora seria arriscado, porque a VPS puxa o `main` a cada 30 minutos e o Modal News tem 8 módulos `paginas*.py` acoplados ao `build.py`.

## O que muda na migração
| Modal News hoje | portal-core |
|---|---|
| `build.py` monolítico (layout, menu e rodapé fixos com links de logística) | `core/site.py` + `core/build.py`; menu, rodapé e chips em `config.yaml` (`menu`, `rodape`) |
| `paginas*.py`, `glossario.py`, `relacionados.py`, `tarifas.py`, `faq_hubs.py` | `nichos/logistica/*.py` com `build(S)`; o FAQ é passado em `S.page(faqs=...)` |
| `KW`/`LOGI` fixos no `fetch.py` | `feeds.yaml`: `palavras_editoria`, `palavras_relevancia` |
| UA "ModalNewsBot" fixo | derivado de `site_name` e `base_url` |
| `THIN_FAMILIAS` fixo | toda família ≠ `paginas` passa pelo gate de 300 palavras |
| sitemaps listados à mão | um sitemap por `familia` registrada no `write()` |
| alerta em `alerta.md` (issue do GitHub) | `ALERTA.txt` (VPS) via `python -m core.alerta` |
| `saude.json` com `por_evento` schedule/dispatch | mesmo formato `saude-portal/1`; evento `cron` vindo de `PORTAL_EVENTO` |

## Passo a passo (em branch, nunca direto no main)
1. Branch `migra-core`; copiar `core/`, `ops/`, `build.py`, `fetch.py` do portal-core.
2. Mover cada `paginasN.py` para `nichos/logistica/`, trocando `B.page(...)`/`B.write(...)` pela API `S.page(..., faqs=, crumbs=)` + `S.write(..., familia=)`.
3. Levar para o `config.yaml`: menu, rodapé, chips da home, `home_faqs`, `palavras_*`.
4. Gerar `public/` no main e na branch e comparar: `diff -r` das URLs (mesmo conjunto), mesmos títulos/descrições/canonical, mesma contagem indexável (1.375 em 12/10/2026), 0 links quebrados, Lighthouse 100 numa amostra.
5. Só então fazer merge, fora do minuto 7/37, e conferir o próximo ciclo da VPS (`saude.json` e `ALERTA.txt`).
