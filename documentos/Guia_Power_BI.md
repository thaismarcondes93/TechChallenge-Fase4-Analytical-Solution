# Guia do dashboard Power BI

Este guia documenta o dashboard final e os procedimentos de atualização. O notebook `../notebook/Analise_Amazon.ipynb` prepara as tabelas utilizadas no relatório e registra os controles de qualidade da base.

## Abrir e atualizar

1. Abra `../powerbi/Dashboard_Powerbi_Amazon.pbix` no Power BI Desktop.
2. Caso o Power BI solicite a localização da fonte, abra **Transformar dados → Gerenciar parâmetros**.
3. Ajuste `PastaDados` para a pasta `powerbi/dados_powerbi` deste projeto.
4. Clique em **Atualizar** e confirme que os cartões e os filtros respondem normalmente.
5. Salve o arquivo após qualquer alteração. Ao finalizar, feche e reabra o PBIX para confirmar a persistência do relatório.

As consultas usadas na atualização estão documentadas em `../powerbi/Power_Query.m`, e as medidas em `../powerbi/Medidas.dax`.

## Modelo de dados

O modelo possui as seguintes relações ativas, ambas com direção de filtro **Única**:

- `Fato_Produto[product_id]` (1) → `Fato_ProdutoTema[product_id]` (*).
- `Dim_Tema[tema]` (1) → `Fato_ProdutoTema[tema]` (*).

`Parametros` é uma tabela desconectada, utilizada para documentar os cortes analíticos. A coluna `faixa_desconto` deve ser classificada por `ordem_desconto`.

## Páginas e leituras

| Página | Conteúdo | Validação esperada |
|---|---|---|
| Visão executiva | Indicadores do portfólio, avaliações por categoria e produtos por quadrante. | O filtro de categoria altera os cartões e os gráficos. |
| Produtos e categorias | Volume de produtos por categoria, dispersão de engajamento × satisfação e tabela de produtos. | Os filtros de categoria e segmento alteram os três visuais. O eixo de avaliações do gráfico de dispersão usa escala logarítmica. |
| Preços e descontos | Cartões de preço, desconto e correlação; preços por faixa; dispersão de desconto × nota. | Os filtros de categoria e faixa de desconto alteram cartões e gráficos. A correlação deve ser lida como associação, não causalidade. |
| Customer Insights | Menções por mil palavras, por tema e grupo de nota, e produtos para leitura de contexto. | Categoria filtra gráfico e tabela. Ao selecionar um tema, o gráfico muda e a tabela mostra apenas produtos com menção ao tema. |
| Recomendações | Ações priorizadas com fato, ação e KPI. | As recomendações podem ser rastreadas às páginas analíticas anteriores. |

## Validação dos indicadores

- Compare os cartões da visão sem filtros com a linha **Portfólio completo** de `validacao_indicadores.csv`.
- Filtre **Electronics** e compare os indicadores com a linha correspondente do mesmo arquivo.
- Em Produtos e categorias, selecione **Alerta** e confirme que a tabela lista apenas esse segmento.
- Em Preços e descontos, selecione uma faixa e confirme a alteração nos cartões e na dispersão.
- Em Customer Insights, selecione uma categoria e depois um tema; confirme a atualização do gráfico e da tabela de contexto.

Os arquivos `auditoria.json` e `diagnostico_ausencias.csv` documentam os controles realizados durante o tratamento. As médias devem ser comparadas respeitando o arredondamento exibido no painel.

## Dicionário resumido

| Tabela | Finalidade |
|---|---|
| `Fato_Produto` | Uma linha por SKU com categoria, preços, desconto, nota, engajamento, segmento e campos de contexto. |
| `Fato_ProdutoTema` | Ocorrências de cada tema por SKU. |
| `Dim_Tema` | Temas e termos pesquisados. |
| `Parametros` | Cortes estatísticos usados na classificação dos produtos. |

## Limitações de interpretação

O conjunto de dados não possui vendas, margem, impressões, conversão ou datas. A quantidade de avaliações é usada como proxy de engajamento. As relações observadas são descritivas e não demonstram causalidade.
