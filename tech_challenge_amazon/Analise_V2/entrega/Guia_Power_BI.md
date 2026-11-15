# Tech Challenge Amazon | Guia de entrega

O projeto usa a base local `../base_dados/amazon.csv` e os critérios das páginas 2 a 7 do enunciado. O notebook `../Analise_Amazon.ipynb` documenta a preparação, a análise e os controles de qualidade. Os resultados retratam o catálogo da amostra.

## Abrir e salvar no Power BI

O Desktop abriu as cinco abas do projeto. A atualização no Desktop terminou com o erro interno “Referência de objeto não definida para uma instância de um objeto”. Os CSVs e os indicadores foram conferidos em Python. O PBIX e a conferência das interações dependem de concluir os passos abaixo em uma sessão funcional.

1. Abra `Amazon.pbip` no Power BI Desktop. Mantenha `Amazon.Report` e `Amazon.SemanticModel` próximos do arquivo.
2. Em **Transformar dados → Gerenciar parâmetros**, confira se `PastaDados` aponta para esta pasta de entrega, dentro de `dados_powerbi`. Ajuste o parâmetro se mover a pasta.
3. Feche e aplique. Clique em **Atualizar** para preencher o modelo de importação. Configure a conexão local caso o Desktop peça a credencial da fonte.
4. Confira os cartões e os filtros conforme a seção de validação abaixo.
5. Em **Arquivo → Salvar como**, escolha o tipo **Arquivo do Power BI (.pbix)** e salve como `Amazon.pbix`. Feche e reabra o arquivo salvo.

O projeto usa o formato de relatório PBIR. Se o Desktop da sua máquina pedir suporte ao formato, consulte a documentação da Microsoft. [Formato PBIR](https://learn.microsoft.com/en-us/power-bi/developer/embedded/projects-enhanced-report-format)

## Montagem em um arquivo novo

Use estes passos se precisar reconstruir o relatório. As consultas em `Power_Query.m` são blocos individuais para o Editor Avançado. Crie `PastaDados` e as quatro consultas com os nomes indicados, e importe os CSVs preparados. Crie as medidas de `Medidas.dax` nas tabelas identificadas no arquivo. Em instalações que usam separadores DAX locais, confira se a fórmula espera vírgula ou ponto e vírgula. Aplique os formatos indicados nos comentários.

No modo Modelo, crie os relacionamentos ativos abaixo e selecione **Única** para a direção do filtro.

- `Fato_Produto[product_id]` (1) → `Fato_ProdutoTema[product_id]` (*).
- `Dim_Tema[tema]` (1) → `Fato_ProdutoTema[tema]` (*).
- `Parametros` fica desconectada e documenta os cortes.

Em **Classificar por coluna**, ordene `faixa_desconto` por `ordem_desconto`. Use percentuais e rupias indianas (INR) nos formatos do modelo. Use as abas nativas do relatório para navegação.

| Página | Visuais e campos | Interações e leitura |
|---|---|---|
| Visão executiva | Cartões de Produtos, Avaliações, Nota ponderada, Desconto médio e Alertas. Barras de Avaliações por `categoria_nivel1` e Produtos por `quadrante`. | Use `categoria_nivel1` na segmentação. Selecione uma barra e confira a mudança nos cartões e no outro gráfico. |
| Produtos e categorias | Barras de Produtos e Nota ponderada por `categoria_nivel1`. Tabela com `rotulo_produto`, categoria, quadrante, Avaliações, Nota média e Nota ajustada média. | Adicione segmentações de categoria e quadrante. Filtre Alerta e ordene a tabela por Avaliações. Use Joia escondida e ordene pela nota ajustada para a segunda leitura. |
| Preços e descontos | Cartões de Preço original médio, Preço final médio, Desconto médio e Correlação desconto e nota. Colunas de preços médios por `faixa_desconto`. Tabela por faixa com Produtos, Nota média e Avaliações medianas. | Use segmentações de categoria e faixa. Compare recortes e observe a quantidade de produtos antes de interpretar. |
| Customer Insights | Barras agrupadas por `Dim_Tema[tema]` com Nota alta por mil e Nota baixa por mil. Tabela com `rotulo_produto`, `grupo_nota`, `review_title` e `about_product`. | Adicione categoria e tema. A categoria filtra gráfico e tabela. O tema filtra o gráfico. A tabela apresenta produto, título agregado e descrição para contextualizar a amostra da categoria. |
| Recomendações | Caixa de texto com quatro ações e suas métricas de acompanhamento. | Use as abas para voltar aos recortes que sustentam as ações. |

Em **Formato → Editar interações**, confirme o ícone **Filtro** nas segmentações em relação aos visuais indicados. Ao comparar temas, mantenha as duas séries visíveis. A taxa divide as menções por mil palavras dentro do grupo de nota e da categoria selecionada.

## Validação

- Compare os cartões com a linha **Portfólio completo** de `validacao_indicadores.csv`. As contagens devem coincidir. Para médias, compare com tolerância equivalente à última casa exibida.
- Filtre **Electronics** na página executiva e compare com a linha dessa categoria no mesmo CSV. Limpe e confira o retorno ao total.
- Na página de produtos, filtre **Alerta** e verifique que as linhas têm esse quadrante. Confira a contagem contra a coluna `alerta` da referência correspondente.
- Na página comercial, selecione uma faixa e confira se preço e desconto mudam. Compare o Pearson sem filtros com a tabela da seção 4 do notebook.
- Em Customer Insights, selecione uma categoria e um tema e confira se as barras mudam. Compare a visão inicial com a tabela de taxas da seção 4.
- Salve, feche e reabra o PBIX e teste novamente navegação e um filtro.

## Dicionário de dados

| Tabela | Campos | Significado |
|---|---|---|
| Fato_Produto | `product_id`, `product_name`, `rotulo_produto` | SKU, nome e rótulo único que reúne nome e SKU. Uma linha por SKU. |
| Fato_Produto | `category`, `categoria_nivel1`, `categoria_nivel2`, `categoria_folha` | Caminho de categoria da linha eleita, nível principal, nível seguinte e última categoria. |
| Fato_Produto | `actual_price`, `discounted_price`, `desconto_valor` | Preço original, preço anunciado e diferença entre ambos em INR. |
| Fato_Produto | `discount_percentage`, `faixa_desconto`, `ordem_desconto`, `faixa_preco` | Desconto informado como fração, faixa, ordenação e faixa do preço original. |
| Fato_Produto | `rating`, `rating_count`, `rating_ajustado` | Nota de 1 a 5, contagem histórica e nota suavizada em direção à média global, ponderada pela evidência disponível. |
| Fato_Produto | `grupo_nota`, `grupo_engajamento`, `quadrante` | Faixas definidas por quantis. Alerta combina engajamento alto e nota baixa. Estrela combina ambos altos. Joia escondida combina nota alta e engajamento baixo. |
| Fato_Produto | `linhas_origem` | Quantidade de linhas no CSV associadas ao SKU. |
| Fato_Produto | `about_product`, `tem_descricao`, `review_title`, `tem_comentario` | Descrição truncada em 500 caracteres, indicador de descrição, títulos reunidos truncados em 300 caracteres e indicador de texto tokenizável. |
| Fato_Produto | `n_palavras`, `palavras_positivas`, `palavras_negativas`, `saldo_sentimento` | Tokens nos comentários, ocorrências léxicas positivas e negativas, e saldo entre −1 e 1 onde há termo do léxico. |
| Fato_ProdutoTema | `product_id`, `tema`, `mencoes` | Uma linha por SKU e tema, com ocorrências do dicionário. Um comentário pode conter mais de uma menção. |
| Dim_Tema | `tema`, `palavras_chave` | Nome do tema e radicais pesquisados. |
| Parametros | `parametro`, `valor`, `descricao` | Cortes do catálogo usados nos segmentos e no ajuste da nota. |

## Matriz do enunciado

| Critério da página 7 | Evidência |
|---|---|
| Compreensão do problema | Abertura do notebook e Visão executiva. |
| Preparação dos dados | Seções 1–3 e 5 do notebook. Auditoria dos nulos, conversões, colisões de ID, regra de seleção e testes de chaves. |
| Indicadores | Medidas DAX, cartões e arquivo de reconciliação. |
| Análise | Seção 4 do notebook e páginas Produtos e categorias e Preços e descontos. |
| Customer Insights | Seções 3–4 do notebook e página Customer Insights. |
| Dashboard | Cinco páginas, filtros de categoria e recortes específicos, relações e navegação. |
| Insights | Resultados da seção 4 e síntese no roteiro executivo. |
| Recomendações | Seção 6 do notebook e página Recomendações. |
| Vídeo executivo | Roteiro cronometrado nesta pasta. A gravação deve mostrar o relatório em operação. |

A granularidade e a falta de datas, pedidos, margens, impressões e notas individuais limitam as inferências sobre vendas, causalidade, visibilidade e sentimento por avaliação. A distribuição por categoria é desigual. Leia grupos pequenos junto com sua contagem de produtos.



