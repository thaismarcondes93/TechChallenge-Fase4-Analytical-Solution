# Guia de montagem do dashboard no Power BI

Tempo estimado: 3 a 5 horas na primeira vez. O objetivo do desafio é **decisão, não quantidade de gráficos**:
cada visual abaixo responde a uma pergunta de negócio e, se não responder, pode ser cortado.

## 0. Escolha o caminho de dados

| | **Caminho A: Python → Excel → Power BI** | **Caminho B: tudo no Power Query** |
|---|---|---|
| O que é | `dados_powerbi.xlsx` já tratado pelo pipeline Python | Consultas M (`consultas_power_query.m`) leem o `amazon.csv` bruto |
| Testado? | **Sim**, com testes automáticos (dados sintéticos) | Só checagem estática de sintaxe; **valide os números** (seção 4) |
| Prós | Mais simples, sem risco de erro de M, sem problema de locale (Excel traz números tipados) | As transformações ficam **visíveis no .pbix** (critério "Preparação dos dados") |
| Colunas `quadrante`, `grupo_nota`, `rating_ajustado` | Já vêm prontas | Criar com `colunas_calculadas.dax` |

**Recomendação:** monte pelo **Caminho B** para que o avaliador veja as transformações no Power Query e use o
Caminho A como **gabarito** (compare os números na seção 4). Se o M der qualquer problema que consuma tempo,
volte ao Caminho A sem culpa e **descreva no vídeo** o tratamento feito em Python (mostre `qualidade_dados.json`).

## 1. Carregar os dados

**Caminho A:** Página Inicial → Obter dados → Pasta de Trabalho do Excel → `data/processed/dados_powerbi.xlsx`
→ marque `Fato_Produto`, `Fato_ProdutoTema`, `Dim_Tema` (e `Parametros`, opcional) → Carregar.

**Caminho B:** siga as instruções no topo de `powerbi/consultas_power_query.m` (parâmetro `CaminhoCSV`, 7 consultas).

Confira os tipos: `rating`, `discount_percentage`, preços → número decimal; `rating_count`, `n_palavras`,
`mencoes` → inteiro; `discount_percentage` com formato **porcentagem**.

## 2. Modelo de dados

Modelo → Exibição de modelo. Dois relacionamentos, ambos **um para muitos**, filtro em **uma direção**:

- `Fato_Produto[product_id]` (1) → `Fato_ProdutoTema[product_id]` (*)
- `Dim_Tema[tema]` (1) → `Fato_ProdutoTema[tema]` (*)

Depois:
1. Crie a hierarquia **Categoria** em `Fato_Produto`: `categoria_nivel1` > `categoria_nivel2` > `categoria_folha`.
2. Crie a tabela `_Medidas` (`_Medidas = {1}`) e cole as medidas de `medidas.dax` (uma por vez).
3. Caminho B: crie as 4 colunas de `colunas_calculadas.dax` em `Fato_Produto`.
4. Oculte colunas técnicas (`category`, `palavras_positivas`, `palavras_negativas`, `linhas_origem`, `product_link` se não usar).
5. Formatos: preços `#,0`; `rating` `0,0`; `rating_ajustado` `0,00`; medidas conforme o `// fmt:` de cada uma.
6. Aplique o tema: Exibição → Temas → Procurar temas → `powerbi/tema_techchallenge.json`.

## 3. Moeda e unidades

Os preços estão na moeda original do dataset (rupias indianas, **confirmar ao abrir o arquivo**). Escreva isso numa
legenda fixa em todas as páginas de preço: "Valores em ₹ (moeda original)". Não converta sem avisar.

## 4. Conferência: o dashboard tem que bater com o pipeline

Antes de montar as páginas, crie cartões e compare com `outputs/insights.md` (gerado com o **seu** CSV real):

| Cartão / medida | Compare com | Tolerância |
|---|---|---|
| Qtd Produtos, Qtd Categorias | seção 1 do `insights.md` | exato |
| Total Avaliações, Rating Ponderado, Desconto Médio | seção 1 | exato (arredondando) |
| Qtd Alerta, Qtd Estrelas, Qtd Joias Escondidas | seção 4 | exato |
| Rating Ponderado por categoria (matriz) | tabela da seção 2 | exato |
| Lift de cada tema | tabela da seção 5 | **Caminho A: exato. Caminho B: pequenas diferenças** (tokenização) |

Se algo não bater, a causa mais comum é: duplicatas de `product_id` não consolidadas, `rating_count` vazio virando zero,
ou percentual lido como inteiro (64 em vez de 0,64).

## 5. As cinco páginas

Padrões: título de cada visual **diz a conclusão** quando possível (use títulos dinâmicos `Título Alerta`);
no máximo 3 cores (verde = bom, vermelho = alerta, âmbar = oportunidade); fonte ≥ 10 pt.
Slicers comuns às páginas 1 a 4: `categoria_nivel1`, `faixa_preco`, `faixa_desconto`
(Exibição → **Sincronizar segmentações**).

### Página 1 · Visão Executiva — "qual o tamanho e a saúde do portfólio?"
| Visual | Campos |
|---|---|
| 7 cartões | Qtd Produtos, Qtd Categorias, Total Avaliações, Rating Ponderado, Desconto Médio, % Produtos Nota ≥ 4, Participação Top 10 Produtos |
| Barras horizontais | Eixo `categoria_nivel1`; Valor `Total Avaliações` (ordem decrescente) |
| Colunas (histograma) | Eixo `rating` agrupado em compartimentos de 0,2 (botão direito no campo → Novo grupo → Compartimento); Valor `Qtd Produtos` |
| Tabela Top 10 | `product_name`, `rating`, `rating_count`, `discount_percentage`; filtro de visual **Top N = 10 por `rating_ajustado`** |
| Cartão de texto | `Categoria Líder em Avaliações` |

### Página 2 · Produtos e Categorias — "onde há engajamento com nota baixa e nota alta com pouca visibilidade?"
| Visual | Campos |
|---|---|
| **Dispersão (visual principal)** | X `rating_count` (**escala logarítmica**: Formatar eixo X → Tipo de escala → Log); Y `rating`; Legenda `quadrante`; Detalhes `product_name`; Tamanho `discounted_price` (média). Cores por categoria: Alerta vermelho, Estrela verde, Joia escondida âmbar, Demais cinza |
| Matriz | Linhas: hierarquia **Categoria**; Valores: `Qtd Produtos`, `Total Avaliações` (barras de dados), `Rating Ponderado` (escala de cor), `Desconto Médio` |
| Tabela "Alerta" | Filtro de visual `quadrante = Alerta`; Top N 15 por `rating_count`; campos: nome, categoria, nota, avaliações, desconto. Título: `Título Alerta` |
| Tabela "Joias" | Filtro `quadrante = Joia escondida`; Top N 15 por `rating`. Título: `Título Joias` |
| Caixa de texto | "Categorias com menos de 10 produtos têm médias instáveis" (liste as que aparecerem em `outputs/tables/categorias.csv` com `amostra_pequena = True`) |

### Página 3 · Preços e Estratégia Comercial — "descontar mais traz mais satisfação ou engajamento?"
| Visual | Campos |
|---|---|
| Colunas + linha | Eixo `faixa_desconto`; Colunas `Avaliações Medianas`; Linha (eixo secundário) `Rating Médio`. Mostre rótulos de dados |
| Dispersão desconto × nota | X `discount_percentage`; Y `rating`; Detalhes `product_id`; Analytics → **Linha de tendência** |
| Dispersão desconto × engajamento | X `discount_percentage`; Y `rating_count` (escala log); Detalhes `product_id` |
| Matriz (mapa de calor) | Linhas `faixa_preco`; Colunas `faixa_desconto`; Valores `Rating Médio` (formatação condicional por escala de cor **com valores fixos**: mínimo = média − 0,5, máximo = média + 0,5, para não exagerar diferenças pequenas) e `Qtd Produtos` |
| Cartões | `Correlação Desconto × Nota`, `Correlação Desconto × Engajamento`, `Economia Média`, `Preço Médio Original`, `Preço Médio Final` |
| Caixa de texto | `Texto Correlação Desconto × Nota` (medida) + "Correlação não é causalidade" |

Leia a correlação com o IC95% do Python (`outputs/tables/correlacoes.csv`): se o intervalo cobre zero, **não afirme relação**.

### Página 4 · Customer Insights — "o que os clientes elogiam e do que reclamam?"
| Visual | Campos |
|---|---|
| Barras agrupadas | Eixo `Dim_Tema[tema]`; Valores `Menções por Mil Palavras (Nota Alta)` e `(Nota Baixa)` |
| Barras de Lift | Eixo `Dim_Tema[tema]`; Valor `Lift Tema (Baixa ÷ Alta)`; ordem decrescente; Analytics → **Linha constante = 1** |
| Matriz | Linhas `categoria_nivel1`; Colunas `Dim_Tema[tema]`; Valores `Menções por Mil Palavras` (escala de cor) |
| Barras | Eixo `categoria_nivel1`; Valor `Saldo de Sentimento Médio` |
| Tabela de produtos | Filtro `grupo_nota = Baixa`; campos: `product_name`, `rating`, `saldo_sentimento`, `review_title` |
| Imagem | `outputs/figures/07_palavras_distintivas.png` (Inserir → Imagem), no lugar de uma nuvem de palavras (o texto completo não entra no modelo) |
| Caixa de texto (método) | "Texto analisado por produto (reviews concatenadas); temas por dicionário; sentimento por léxico: compara grupos, não mede o absoluto" |

### Página 5 · Recomendações — "o que fazemos na segunda-feira?"
- Quatro blocos de texto no formato **Fato → Por que importa → Ação → KPI**, escritos a partir da seção 7 de `outputs/insights.md` **depois que vocês a revisarem**.
- Reaproveite as tabelas Alerta e Joias da página 2 (Top 10).
- Botão "Voltar ao início".

## 6. Interatividade

1. **Navegação:** botões (Inserir → Botões → Navegador de páginas) no topo de todas as páginas.
2. **Limpar filtros:** crie um Indicador (Exibição → Indicadores) com o estado sem filtros e associe a um botão.
3. **Drill-through "Ficha do produto":** nova página; campo de drill-through `product_name`; cartões `rating`, `rating_count`,
   `discount_percentage`, `discounted_price`, `quadrante`, `saldo_sentimento`; caixa com `about_product`; tabela `Dim_Tema` × `mencoes`.
4. **Dica de ferramenta (tooltip) de página** para a dispersão da página 2, mostrando a ficha resumida ao passar o mouse.
5. **Editar interações** (Formato → Editar interações) para que a dispersão da página 2 filtre as tabelas, mas as tabelas não filtrem de volta.

## 7. Checklist antes de gravar o vídeo

- [ ] Conferência da seção 4 feita; números iguais aos do `insights.md`.
- [ ] Nenhum visual sem título claro; nenhum eixo truncado sem aviso; cores com significado fixo.
- [ ] Moeda e limitações declaradas.
- [ ] Todos os filtros e botões funcionam; "Limpar filtros" volta ao estado inicial.
- [ ] Arquivo salvo como `.pbix` e testado em outra máquina (ou ao menos fechado e reaberto).
