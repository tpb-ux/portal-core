# Rascunhos de conteúdo próprio (fluxo de revisão)

Arquivos aqui **não são publicados**: o build só lê `content/`.

1. O rascunho é escrito aqui com `tipo: analise`, `status: rascunho` e só com dados verificáveis (fonte citada).
2. Na revisão, o revisor confere números e fontes, resolve ou remove todas as marcas `[[REVISÃO: ...]]`,
   preenche `autor` e `revisado_por` (slugs de `data/autores.yaml` com nome preenchido) e troca para `status: aprovado`.
3. O arquivo vai para `content/`. O build publica em `/analises/<slug>/`, indexável, com `NewsArticle`,
   `author`/`editor` do tipo `Person`, e entra no `sitemap-noticias.xml` por 48 h.
4. Se faltar aprovação, autor, revisor ou houver `[[REVISÃO`, o build retém a análise e avisa no log.
