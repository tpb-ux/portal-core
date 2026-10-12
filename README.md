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

## Qualidade, indexação e conteúdo próprio

- **Unicidade** (`core/qualidade.py`): para cada família, mede a fração de 5-gramas (números normalizados) que aparecem em no máximo 10% das páginas da família. Páginas abaixo de `qualidade.corte_unicidade` (padrão 0,15) viram noindex e saem do sitemap. A semelhança média (Jaccard) e as medianas vão para o log do build e para `saude.json` (`qualidade`).
- **FAQ**: páginas pSEO (`qualidade.faq_pseo.prefixos`) ficam com até 3 perguntas, só as que trazem número. Hubs e glossário mantêm o FAQ completo.
- **Lançamento em ondas**: `indexacao.familias_noindex` deixa famílias inteiras em noindex (com `excecoes`). Para liberar a próxima onda, basta tirar a família da lista.
- **Imagens**: foto original da fonte em WebP, com o nome pelo slug da página, alt, crédito e link para a matéria original. `feeds.yaml: licencas_imagem` só refina o crédito (nome do fotógrafo) para as fontes com licença confirmada. `core/cards.py` e `migrar_cards()` ficam disponíveis, mas desligados.
- **robots.txt**: seções explícitas para buscadores, buscadores de IA e bots de treino (todos liberados). Com noindex global, fica `Disallow: /`.
- **Anti-rede** (`rede_dominios`): o build falha se o domínio de outro portal do mesmo dono aparecer no cabeçalho, rodapé ou menu, ou em mais de 5% das páginas.
- **Autores e análises**: `data/autores.yaml` (entradas sem nome ficam ocultas). Matérias próprias ficam em `drafts/` e só são publicadas com `status: aprovado`, autor e revisor cadastrados e nenhuma marca `[[REVISÃO]]` (ver `drafts/README.md`). Elas saem em `/analises/` como NewsArticle com autor e entram no `sitemap-noticias.xml`.
- **llms.txt** enxuto: identificação, política e hubs principais.

## Glossário e autolink

- `core.modulos.glossario`: lê `data/glossario.yaml` (header: `nome`, `categorias`, `faqs`, `termos`) e mescla `data/glossario/*.yaml` (`termos:` e `complementos: {slug: campos}`). URLs `@CHAVE` vêm de `data/glossario_fontes.yaml`.
- Cada verbete exige categoria, ≥5 FAQs, base legal com link oficial, relacionados existentes e imagem (`data/glossario_imagens.yaml` + `data/glossario_imagens/<chave>.webp`, licença livre, gera `<slug>.webp`, `-800` e `-480`). Falhas viram erro de build.
- Página: DefinedTerm + FAQPage + breadcrumb; hub com busca, categorias, A–Z e DefinedTermSet.
- `core/autolink.py` + bloco `autolink:` no config: links automáticos no build (ver comentário em config.yaml). Por termo: `autolink: false | [variantes]`, `autolink_sigla: false` para siglas ambíguas (PL, MP, MS, BC).
