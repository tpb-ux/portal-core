---
titulo: Expediente
descricao: "Expediente do {{cfg.site_name}}: empresa responsável, CNPJ, endereço, responsável editorial e canais oficiais de contato."
schema: AboutPage
faqs:
  - {p: "Qual empresa é responsável pelo {{cfg.site_name}}?", r: "{{cfg.empresa.razao_social}}, inscrita no CNPJ {{cfg.empresa.cnpj}}."}
  - {p: "Qual é o endereço da empresa?", r: "{{cfg.empresa.endereco.logradouro}}, {{cfg.empresa.endereco.bairro}}, {{cfg.empresa.endereco.cidade}}-{{cfg.empresa.endereco.uf}}, CEP {{cfg.empresa.endereco.cep}}."}
  - {p: "Como entrar em contato?", r: "Pela página de contato. Pedidos de correção e de direito de resposta têm páginas próprias."}
  - {p: "O portal tem patrocínio ou anúncios?", r: "Não há conteúdo patrocinado. Se houver publicidade no futuro, ela será identificada e separada do conteúdo editorial."}
  - {p: "Onde estão as regras editoriais?", r: "Na política editorial, que descreve fontes, critérios de seleção, imparcialidade e correções."}
---
| | |
|---|---|
| **Empresa** | {{cfg.empresa.razao_social}} |
| **CNPJ** | {{cfg.empresa.cnpj}} |
| **Endereço** | {{cfg.empresa.endereco.logradouro}}, {{cfg.empresa.endereco.bairro}}, {{cfg.empresa.endereco.cidade}}-{{cfg.empresa.endereco.uf}}, CEP {{cfg.empresa.endereco.cep}} |
| **Responsável editorial** | {{cfg.responsavel_editorial}} |
| **E-mail** | {{cfg.empresa.email}} |

Canais: [contato](/contato/), [correções](/correcoes/), [direito de resposta](/direito-de-resposta/), [privacidade](/privacidade/).
