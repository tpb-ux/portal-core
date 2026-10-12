---
titulo: Metodologia
descricao: "Como o {{cfg.site_name}} coleta notícias e dados oficiais: frequência, filtros de qualidade, regras de imagem e critérios para indexar páginas."
faqs:
  - {p: "Com que frequência os dados são atualizados?", r: "As notícias são coletadas a cada 30 minutos. Bases oficiais são atualizadas uma vez por dia, e a data de coleta aparece em cada página."}
  - {p: "Como as notícias são selecionadas?", r: "Por filtros automáticos de relevância e de bloqueio. Só entram matérias com imagem própria da fonte."}
  - {p: "Os números são calculados pelo portal?", r: "Somas, médias e rankings são calculados a partir da base oficial citada, com o método descrito na página."}
  - {p: "Por que algumas páginas não aparecem no Google?", r: "Páginas sem conteúdo suficiente ficam fora do índice até ganharem dados reais. Elas continuam acessíveis pelos links internos."}
  - {p: "Usam inteligência artificial?", r: "Não. A coleta e os textos de dados são determinísticos, gerados a partir das fontes."}
---
- **Notícias:** feeds públicos selecionados, coletados a cada 30 minutos. Só entram itens com imagem própria. O resumo é um trecho do feed com link para a íntegra, e essas páginas não são indexadas.
- **Dados:** coletados de APIs oficiais abertas, versionados e com data de coleta. Nenhum número é inventado: campo sem dado verificado é omitido.
- **Qualidade:** página de dados com menos de 300 palavras ou sem 5 perguntas frequentes fica fora do índice. O site não é publicado se houver link interno quebrado.
- **Saúde do portal:** o arquivo público [saude.json](/saude.json) mostra a situação da coleta e dos feeds.
