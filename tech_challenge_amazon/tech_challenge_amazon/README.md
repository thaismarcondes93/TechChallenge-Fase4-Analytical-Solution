# Tech Challenge: Amazon Product Performance & Customer Insights

Pipeline em Python + guia de Power BI para o Tech Challenge de Data Analytics (POSTECH).
Ele transforma o `amazon.csv` do Kaggle em tabelas prontas para o Power BI, calcula indicadores e análises com números
reais, gera gráficos e **rascunhos** de insights, recomendações e roteiro do vídeo.

> **Pergunta central do desafio:** quais produtos, categorias e estratégias comerciais merecem mais atenção, e que
> oportunidades os dados mostram? Fio condutor: **Preço → Desconto → Engajamento → Satisfação**.

## O que está pronto e o que falta (leia antes)

| Item | Estado |
|---|---|
| Pipeline Python (limpeza, análises, gráficos, relatórios) | **Pronto e testado**: 14 testes automáticos, em pandas 2.2 e 3.0, com dados *sintéticos* |
| Resultados com os dados reais | **Falta rodar**: o Kaggle exige download; rodem `python run_all.py` com o CSV real |
| Medidas DAX, tema, guia do dashboard | Prontos (`powerbi/`); as medidas **não foram executadas no Power BI**: confiram na seção 4 do guia |
| Consultas Power Query (M) | Geradas do `config.py` com checagem estática de sintaxe; **não executadas** (sem motor do Power Query aqui) |
| Arquivo `.pbix` | **Falta montar** no Power BI Desktop (só ele gera esse formato). O guia diz campo a campo como |
| Vídeo | **Falta gravar**. `outputs/roteiro_video_preenchido.md` já vem com os números reais |

Os textos gerados (`insights.md`, roteiro) são **rascunhos baseados em regras**. Leiam, discordem, ajustem e assumam a autoria.

## Passo a passo (Windows, macOS ou Linux)

Pré-requisito: Python 3.10 ou superior e VS Code com a extensão Python.

```bash
# 1) abrir a pasta no VS Code:  File > Open Folder > tech_challenge_amazon
# 2) criar o ambiente virtual (terminal do VS Code)
python -m venv .venv
#    Windows (PowerShell):  .venv\Scripts\Activate.ps1
#    macOS/Linux:           source .venv/bin/activate
python -m pip install -r requirements.txt

# 3) testar a instalação com dados SINTÉTICOS (resultados NÃO são reais)
python run_all.py --sample --out outputs_sintetico --processed data/processed_sintetico

# 4) colocar o dataset real em data/raw/amazon.csv  (ver "Obter o dataset") e rodar
python run_all.py
```

No VS Code, o mesmo está em **Terminal > Run Task** (veja `.vscode/tasks.json`) e em **Run and Debug**.
Se o PowerShell bloquear a ativação do ambiente: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### Obter o dataset

- **Manual (mais simples):** abra <https://www.kaggle.com/datasets/karkavelrajaj/amazon-sales-dataset>, clique em *Download*,
  extraia e salve como `data/raw/amazon.csv`.
- **Automático:** `python run_all.py --download` (usa `kagglehub`; se pedir login, crie um token em
  <https://www.kaggle.com/settings> e defina `KAGGLE_USERNAME` e `KAGGLE_KEY`).

## O que cada execução gera

| Arquivo | Para quê |
|---|---|
| `data/processed/dados_powerbi.xlsx` | **Importar no Power BI** (Caminho A): `Fato_Produto`, `Fato_ProdutoTema`, `Dim_Tema`, `Parametros` |
| `data/processed/*.csv` | Mesmas tabelas em CSV, mais `texto_produto.csv` (texto agregado, usado só na análise) |
| `outputs/insights.md` | Rascunho de insights, riscos, oportunidades e recomendações, com números reais |
| `outputs/roteiro_video_preenchido.md` | Roteiro de 7 minutos, cronometrado, com os números preenchidos |
| `outputs/figures/*.png` | 7 gráficos (distribuições, categorias, quadrantes, desconto, mapa de calor, temas, palavras) |
| `outputs/analise_resultados.xlsx` e `outputs/tables/*.csv` | Todas as tabelas de resultado (correlações com IC95%, categorias, quadrantes, temas...) |
| `outputs/qualidade_dados.json` | Auditoria da limpeza: duplicatas, valores inválidos, nulos. **Abram este primeiro** |

## Do pipeline ao `.pbix`

1. Rode o pipeline com o CSV real e leia `outputs/qualidade_dados.json` e `outputs/insights.md`.
2. **Calibrem** o que for preciso em `techchallenge/config.py` (cortes de nota/engajamento, faixas de desconto e preço,
   dicionário de temas) olhando `outputs/figures`. Rodem de novo.
3. Se mudarem o `config.py`, regerem o M: `python -m techchallenge.gerar_power_query`.
4. Montem o dashboard seguindo `powerbi/GUIA_DASHBOARD.md` (dois caminhos de dados, modelo, 5 páginas, interatividade,
   **tabela de conferência** contra os números do pipeline).
5. Gravem o vídeo com `outputs/roteiro_video_preenchido.md` como base. Terminem respondendo: *quais são as principais
   mensagens que a liderança deve levar desta análise?*

## Decisões metodológicas (declarem no vídeo)

- **Texto analisado por produto, não por review.** No CSV, as reviews de um produto vêm concatenadas na mesma célula e o
  texto contém vírgulas; separar por vírgula quebraria reviews no meio.
- **Nulos continuam nulos.** `rating` inválido (ex.: o valor `|` conhecido do dataset) e `rating_count` vazio não viram zero.
- **Rating ajustado (bayesiano)** ordena rankings: nota 5,0 com 3 avaliações não vence 4,6 com 20 mil.
- **Grupos por quartis do próprio portfólio**, porque as notas costumam ficar numa faixa estreita e cortes absolutos
  (como "nota < 4") separam pouco.
- **Correlação de Spearman com IC95% por bootstrap.** Se o intervalo cobre zero, o texto diz "sem evidência de relação".
  Correlação não é causalidade.
- **Temas por dicionário, normalizados por 1.000 palavras**, para não favorecer produtos com mais reviews. Sentimento por
  léxico (sem negação/ironia): serve para comparar grupos, não como medida absoluta. O pipeline valida o léxico
  correlacionando-o com a nota.
- **Avaliações são proxy de engajamento**, não de vendas. Não há coluna de data: sem análise temporal.
- **Moeda:** valores na moeda original do dataset (rupias, confirmar). Nada é convertido.

## Testes

```bash
python -m unittest discover -s tests -v      # ou: Testing no VS Code
```

Cobrem: 1 linha por produto, tipos e faixas válidas, nulos preservados, chaves do modelo em estrela, coerência dos
quadrantes, rating ajustado, arquivos gerados, caracteres de controle no Excel, correlação/bootstrap, base minúscula e a
geração do M. **Todos usam dados sintéticos** (`techchallenge/sample_data.py`); nunca tirem conclusões deles.

## Solução de problemas

| Sintoma | Causa provável e solução |
|---|---|
| `FileNotFoundError: ... amazon.csv` | O CSV não está em `data/raw/`. Veja "Obter o dataset" |
| `ValueError: Colunas obrigatórias ausentes` | O CSV não é o do Kaggle indicado, ou o cabeçalho foi alterado |
| Acentos quebrados no terminal do Windows | Já tratado no `run_all.py`; se persistir, use o terminal do VS Code |
| `PermissionError` ao gravar `.xlsx` | O Excel/Power BI está com o arquivo aberto. Feche e rode de novo |
| Power BI lê `0.85` como `85` ou data | Importe o **.xlsx** (Caminho A), que já traz números tipados, e não os CSV |
| Gráfico vazio ou aviso "grupos pequenos" | Base muito reduzida ou cortes muito rígidos: ajuste `config.py` |
| M do Power Query dá erro | Use o Caminho A e descreva o tratamento no vídeo; ou compare consulta a consulta com `consultas_power_query.m` |

## Mapa: critérios de avaliação → onde está

| Critério | Onde |
|---|---|
| Compreensão do problema | Este README, `insights.md` seção 1, roteiro (0:00–0:45) |
| Preparação dos dados | `techchallenge/prepare.py`, `qualidade_dados.json`, `powerbi/consultas_power_query.m` |
| Indicadores | `powerbi/medidas.dax`, `outputs/tables/` |
| Análise | `techchallenge/analyze.py`, `insights.md` seções 2 a 4 |
| Customer Insights | `insights.md` seção 5, figuras 06 e 07, página 4 do dashboard |
| Dashboard | `powerbi/GUIA_DASHBOARD.md`, `tema_techchallenge.json` |
| Insights e Recomendações | `insights.md` seções 6 e 7 |
| Vídeo executivo | `outputs/roteiro_video_preenchido.md` |

## Estrutura

```
tech_challenge_amazon/
├── run_all.py                    # ponto de entrada
├── requirements.txt
├── techchallenge/
│   ├── config.py                 # cortes, faixas, léxicos e temas (calibre aqui)
│   ├── download.py               # download opcional do Kaggle
│   ├── prepare.py                # limpeza e modelo em estrela
│   ├── analyze.py                # indicadores, correlações, quadrantes, temas, gráficos
│   ├── report.py                 # insights.md e roteiro do vídeo
│   ├── gerar_power_query.py      # gera o M a partir do config.py
│   ├── sample_data.py            # dados SINTÉTICOS (só para testes)
│   └── util.py
├── powerbi/
│   ├── GUIA_DASHBOARD.md
│   ├── medidas.dax
│   ├── colunas_calculadas.dax    # só para o Caminho B
│   ├── consultas_power_query.m   # Caminho B (gerado)
│   └── tema_techchallenge.json
├── tests/
├── data/raw/                     # coloque amazon.csv aqui
├── data/processed/               # gerado
├── outputs/                      # gerado
└── .vscode/                      # tarefas, depuração e testes prontos
```
