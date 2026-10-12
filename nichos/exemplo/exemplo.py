"""Módulo de exemplo: modelo de família pSEO. Copie para nichos/<seu-nicho>/<familia>.py e liste em config.yaml > modulos.
Contrato: build(S) gera páginas com S.page(..., faqs=[>=5], crumbs=[...], jsonld=...) e S.write(url, html, familia=..., lastmod=...).
O core cuida de: noindex abaixo de 300 palavras, erro se indexável com <5 FAQs, título duplicado, link quebrado, sitemap por família, busca, llms.txt."""
from core.site import E
ITENS = [{"slug": "exemplo-a", "nome": "Exemplo A", "valor": 10}, {"slug": "exemplo-b", "nome": "Exemplo B", "valor": 20}]
def build(S):
    for it in ITENS:
        u = f"/exemplos/{it['slug']}/"
        body = f'<article class="post"><h1>{E(it["nome"])}</h1><p class="snippet">{E(it["nome"])} tem valor {it["valor"]} (fonte: dataset oficial, data de coleta).</p></article>'
        faqs = [(f"Pergunta {i} sobre {it['nome']}?", "Resposta com dado e fonte.") for i in range(1, 6)]
        S.write(u, S.page(f"{it['nome']}: dados oficiais", f"Dados oficiais de {it['nome']} com fonte, data de coleta e perguntas frequentes.", u, body,
                          faqs=faqs, crumbs=[("Exemplos", "/exemplos/"), (it["nome"], u)]), familia="exemplos")
    S.write("/exemplos/", S.page("Exemplos: índice", "Índice da família de exemplo, com links para todas as páginas e perguntas frequentes.", "/exemplos/",
                                 '<section class="blk"><h1>Exemplos</h1><ul>' + "".join(f'<li><a href="/exemplos/{i["slug"]}/">{E(i["nome"])}</a></li>' for i in ITENS) + "</ul></section>",
                                 faqs=[(f"Pergunta {i}?", "Resposta.") for i in range(1, 6)], crumbs=[("Exemplos", "/exemplos/")]), familia="exemplos")
