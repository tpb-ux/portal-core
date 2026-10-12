# portal-core

Núcleo comum dos portais estáticos (Modal News, Estrato e os próximos): gerador Python, SEO técnico, schema, sitemaps por família, busca estática, `llms.txt`, IndexNow, saúde editorial (`saude.json`, formato `saude-portal/1`), coletor RSS sem IA (só matérias com foto própria) e operação em VPS.

## Estrutura
```
core/            # comum (não editar por portal; corrigir aqui e propagar)
  site.py        # Site: config, layout, page(), write(), FAQ/breadcrumb/tabela, gates de qualidade
  build.py       # pipeline: artigos, módulos, institucionais, editorias, home, busca, sitemaps, robots, llms, linkcheck, IndexNow, saúde
  fetch.py       # coletor RSS (feeds.yaml): filtros, foto própria (feed ou og:image), WebP, restrição temporária por editoria
  home.py        # home genérica (o nicho pode ter nichos/<n>/home.py)
  modulos/glossario.py  # glossário genérico a partir de data/glossario.yaml
  paginas_padrao/*.md   # sobre, expediente, contato, termos, privacidade, correções, direito de resposta, metodologia, política editorial
  saude.py indexnow.py alerta.py static/style.css
nichos/<nicho>/  # módulos do segmento: build(S) por família pSEO; paginas/*.md sobrescrevem as padrão
ops/             # ciclo.sh (VPS), portal.env.example, nginx.conf.example
tools/novo_portal.py
```

## Gates de qualidade (o build falha)
- link interno quebrado (inclui `src`), URL duplicada;
- página indexável com menos de 5 FAQs (`qualidade.min_faqs`);
- título duplicado entre indexáveis; descrição fora de 50–165 caracteres.
Páginas de famílias pSEO com menos de 300 palavras viram `noindex,follow` e saem do sitemap e da busca.

## Pré-lançamento
`noindex_global: true` (ou `PORTAL_NOINDEX=1`) põe `noindex,nofollow` em tudo, `robots.txt` com `Disallow: /` e desliga o IndexNow. `PORTAL_BASE_URL` gera prévia com prefixo (ex.: GitHub Pages `usuario.github.io/repo`).

## Novo portal
`python tools/novo_portal.py ../novo --nome "Nome" --dominio nome.com.br --nicho segmento`, depois: editorias/menu/empresa no `config.yaml`, feeds testados no `feeds.yaml`, logo em `static/`, módulos em `nichos/<segmento>/`.

## Operação (VPS)
Ver `ops/`. Cron nos minutos 7 e 37: `git fetch` + merge de `origin/main`, coleta, build, `rsync` para o webroot, IndexNow (se não for prévia), commit local dos dados e `ALERTA.txt`.

Migração do Modal News para este núcleo: ver `MIGRACAO_MODALNEWS.md`.
