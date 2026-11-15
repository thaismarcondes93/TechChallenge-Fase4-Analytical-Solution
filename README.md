# Amazon Product Performance & Customer Insights

Solução analítica desenvolvida para o Tech Challenge — Fase 4 da Pós-Tech em Data Analytics da FIAP.

O projeto analisa o desempenho do portfólio da Amazon a partir de preços, descontos, avaliações e comentários de consumidores. A entrega reúne tratamento de dados, análise exploratória, Customer Insights e um dashboard interativo em Power BI.

> Pergunta de negócio: quais produtos, categorias e estratégias comerciais merecem maior atenção, e quais oportunidades podem ser identificadas a partir dos dados disponíveis?

## Contexto

Em marketplaces digitais, decisões sobre portfólio, precificação e experiência do cliente precisam ser orientadas por dados. A análise segue o fluxo:

**Preço → Desconto → Engajamento → Satisfação**

A quantidade de avaliações é utilizada como uma proxy de engajamento, enquanto a nota média e a nota ponderada representam a satisfação percebida dos consumidores.

## Principais resultados

| Indicador | Resultado |
|---|---:|
| Produtos analisados | 1.351 |
| Categorias de nível principal | 9 |
| Avaliações acumuladas | 23.802.463 |
| Nota média dos produtos | 4,09 |
| Nota ponderada por avaliações | 4,16 |
| Desconto médio informado | 46,7% |
| Produtos em Alerta | 21 |
| Produtos Estrela | 112 |
| Joias escondidas | 81 |

Entre os achados mais relevantes:

- A categoria **Electronics** concentra a maior parcela das avaliações do portfólio.
- Há 21 produtos com alto engajamento e nota baixa, classificados como **Alertas**.
- Há 81 produtos com nota alta e baixo engajamento, classificados como **Joias escondidas**.
- A relação entre desconto e nota é fraca e negativa na amostra (`r = -0,162`); portanto, descontos não devem ser interpretados como causa direta de satisfação.
- Temas como preço/custo-benefício e qualidade/acabamento aparecem com maior frequência relativa entre produtos de nota baixa.

## Dashboard

O dashboard em Power BI está organizado em cinco páginas:

1. **Visão executiva** — indicadores centrais do portfólio e visão geral por categoria.
2. **Produtos e categorias** — análise de engajamento e satisfação por produto, com identificação de Alertas, Estrelas e Joias escondidas.
3. **Preços e descontos** — comparação de preços, faixas de desconto e associação descritiva entre desconto e nota.
4. **Customer Insights** — comparação de temas dos comentários entre produtos de nota alta e baixa, com leitura de contexto.
5. **Recomendações** — ações priorizadas, evidências e indicadores sugeridos para acompanhamento.

## Recomendações de negócio

- Investigar produtos em Alerta, começando pelos itens com maior volume de avaliações.
- Testar maior exposição para produtos bem avaliados e pouco engajados.
- Avaliar descontos por categoria e faixa de preço com grupos de comparação.
- Validar temas recorrentes nos comentários antes de alterar cadastro, fornecedores ou políticas de qualidade.

## Metodologia

- Consolidação de uma linha por produto (`product_id`).
- Tratamento explícito de valores ausentes, inválidos e registros duplicados.
- Priorização de registros com dados comerciais válidos, nota válida e maior volume de avaliações.
- Cálculo de nota ponderada e nota ajustada para reduzir o peso de produtos com poucas avaliações em rankings.
- Classificação de produtos por quartis de nota e engajamento.
- Análise de comentários por produto, pois as avaliações originais estão concatenadas em um mesmo campo.
- Normalização de menções por mil palavras para comparar temas entre grupos com diferentes volumes de texto.
- Uso de correlação como análise descritiva, sem interpretação causal.

## Estrutura do projeto

```text
TechChallenge-Fase4-Analytical-Solution/
├── README.md
├── data/
│   └── amazon.csv                         # base original
├── notebook/
│   ├── Analise_Amazon.ipynb               # preparação, análise e exportação
│   └── analise_funcoes.py                 # funções usadas pelo notebook
├── powerbi/
│   ├── Dashboard_Powerbi_Amazon.pbix      # dashboard final
│   ├── dados_powerbi/                     # tabelas para atualização do PBIX
│   ├── Medidas.dax                        # medidas documentadas
│   └── Power_Query.m                      # consultas e parâmetro de fonte
├── documentos/
│   ├── Guia_Power_BI.md
│   ├── auditoria.json
│   ├── diagnostico_ausencias.csv
│   └── validacao_indicadores.csv
└── video/
    └── Roteiro_Video.md
```

## Como explorar a solução

### Notebook

Abra `notebook/Analise_Amazon.ipynb` a partir da pasta do projeto. Para executar a análise, instale as dependências:

```bash
pip install pandas numpy jupyter ipython
```

O notebook lê `data/amazon.csv`, realiza o diagnóstico e o tratamento dos dados e atualiza as tabelas em `powerbi/dados_powerbi/` e os arquivos de validação em `documentos/`.

### Power BI

Abra:

```text
powerbi/Dashboard_Powerbi_Amazon.pbix
```

Caso seja necessário atualizar os dados em outra máquina, ajuste o parâmetro `PastaDados` para a pasta `powerbi/dados_powerbi`. Os indicadores podem ser conferidos em `documentos/validacao_indicadores.csv`.

## Fonte de dados

A base utilizada é o [Amazon Sales Dataset](https://www.kaggle.com/datasets/karkavelrajaj/amazon-sales-dataset), disponibilizado no Kaggle.

## Limitações

- A base não possui datas, vendas, impressões, conversão ou margem.
- A quantidade de avaliações é uma proxy de engajamento, não uma medida direta de vendas.
- As conclusões sobre descontos são associativas; correlação não implica causalidade.
- Os comentários são analisados por produto, e não por avaliação individual.
- A identificação de temas utiliza um dicionário de termos em inglês e deve ser validada com leitura contextual dos comentários.

## Tecnologias

- Python
- Pandas e NumPy
- Jupyter Notebook
- Power BI Desktop
- DAX
- Power Query

---

Desenvolvido como parte do Tech Challenge — Fase 4 da Pós-Tech em Data Analytics — FIAP.
