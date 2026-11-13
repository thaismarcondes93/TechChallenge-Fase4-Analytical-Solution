"""Gera powerbi/consultas_power_query.m a partir de config.py (Caminho B).

Objetivo: quem quiser que as TRANSFORMAÇÕES apareçam dentro do Power BI (critério "Preparação dos dados")
cola estas consultas no Editor Avançado. Como os dicionários e as faixas são gerados a partir do
mesmo config.py usado pelo Python, as duas versões não ficam divergentes.

AVISO HONESTO: o código Python foi testado automaticamente; o código M gerado aqui NÃO pôde ser executado
no ambiente de desenvolvimento (não há motor do Power Query). Há uma checagem estática de sintaxe nos testes,
mas a validação real é conferir os números no Power BI contra outputs/ (veja powerbi/GUIA_DASHBOARD.md).

Uso:  python -m techchallenge.gerar_power_query
"""
from __future__ import annotations

from pathlib import Path

from . import config as cfg


def _lista(itens) -> str:
    return "{" + ", ".join(f'"{i}"' for i in sorted(itens)) + "}"


def _faixas(coluna: str, limites: list[float], rotulos: list[str]) -> str:
    """if-else encadeado em M. `limites` = limites inferiores; a última faixa é aberta."""
    partes = [f'if [{coluna}] = null then "{cfg.SEM_DADO}"']
    for lim, rot in zip(limites[1:], rotulos[:-1]):
        partes.append(f'else if [{coluna}] < {lim} then "{rot}"')
    partes.append(f'else "{rotulos[-1]}"')
    return "\n            ".join(partes)


def _temas() -> str:
    linhas = []
    for tema, radicais in cfg.TEMAS.items():
        linhas.append(f'        {{"{tema}", {_lista(radicais)}}}')
    return ",\n".join(linhas)


TEMPLATE = r'''// =====================================================================================
// CONSULTAS POWER QUERY (M) - CAMINHO B  |  gerado por techchallenge/gerar_power_query.py
// NÃO EDITE AQUI os dicionários/faixas: edite techchallenge/config.py e gere de novo.
//
// COMO USAR
//  1. Página Inicial > Transformar dados. Crie um parâmetro de texto chamado CaminhoCSV com o
//     caminho completo do amazon.csv (ex.: C:\TechChallenge\data\raw\amazon.csv).
//  2. Para cada bloco "CONSULTA n" abaixo: Nova Fonte > Consulta em branco > Editor Avançado,
//     apague o conteúdo, cole o código do bloco e renomeie a consulta EXATAMENTE como no título.
//  3. Em Produtos_Raw, Texto_Produto, Sentimento_Produto e Temas_Palavras, desmarque
//     "Habilitar carga" (botão direito na consulta). Elas só servem de etapa intermediária.
//  4. Feche e aplicar. Depois crie os relacionamentos, as colunas de colunas_calculadas.dax
//     e as medidas de medidas.dax.
//  Se aparecer erro "Formula.Firewall": Arquivo > Opções > Segurança > Níveis de privacidade >
//  "Ignorar os níveis de privacidade". Pequenas diferenças nas contagens de palavras/menções
//  em relação ao Python são esperadas (tokenização diferente); as demais colunas devem bater.
// =====================================================================================


// ===== CONSULTA 1: Produtos_Raw =====
let
    Fonte = Csv.Document(File.Contents(CaminhoCSV), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promovido = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true])
in
    Promovido


// ===== CONSULTA 2: Texto_Produto =====
// Uma linha por produto, com todas as reviews juntas (as reviews vêm concatenadas e o texto contém
// vírgulas; por isso NÃO se separa por vírgula).
let
    Fonte = Table.SelectColumns(Produtos_Raw, {"product_id", "review_title", "review_content"}),
    ComId = Table.SelectRows(Fonte, each [product_id] <> null and [product_id] <> ""),
    Agrupado = Table.Group(ComId, {"product_id"}, {
        {"review_title", each Text.Combine(List.RemoveNulls([review_title]), " | "), type text},
        {"review_content", each Text.Combine(List.RemoveNulls([review_content]), " | "), type text}
    })
in
    Agrupado


// ===== CONSULTA 3: Sentimento_Produto =====
let
    Fonte = Texto_Produto,
    Pos = List.Buffer(@@POSITIVAS@@),
    Neg = List.Buffer(@@NEGATIVAS@@),
    Tokens = (txt as nullable text) as list =>
        List.Select(Text.SplitAny(Text.Lower(if txt = null then "" else txt), " .,;:!?()[]""|/-#(lf)#(cr)#(tab)"), each _ <> ""),
    Contar = (tokens as list, lex as list) as number =>
        List.Count(List.Select(tokens, each List.Contains(lex, _))),
    T = Table.AddColumn(Fonte, "tokens", each Tokens([review_content]), type list),
    NP = Table.AddColumn(T, "n_palavras", each List.Count([tokens]), Int64.Type),
    P = Table.AddColumn(NP, "palavras_positivas", each Contar([tokens], Pos), Int64.Type),
    N = Table.AddColumn(P, "palavras_negativas", each Contar([tokens], Neg), Int64.Type),
    S = Table.AddColumn(N, "saldo_sentimento", each
        let t = [palavras_positivas] + [palavras_negativas]
        in if t = 0 then null else ([palavras_positivas] - [palavras_negativas]) / t, type number),
    Final = Table.SelectColumns(S, {"product_id", "n_palavras", "palavras_positivas", "palavras_negativas", "saldo_sentimento"})
in
    Final


// ===== CONSULTA 4: Temas_Palavras =====
let
    Fonte = #table(type table [tema = text, palavras = list], {
@@TEMAS@@
    })
in
    Fonte


// ===== CONSULTA 5: Dim_Tema =====
let
    Fonte = Table.SelectColumns(Temas_Palavras, {"tema"})
in
    Fonte


// ===== CONSULTA 6: Fato_ProdutoTema =====
let
    Base = Table.SelectColumns(Texto_Produto, {"product_id", "review_content"}),
    Cruz = Table.AddColumn(Base, "t", each Temas_Palavras),
    Exp = Table.ExpandTableColumn(Cruz, "t", {"tema", "palavras"}),
    Cont = Table.AddColumn(Exp, "mencoes", each
        let txt = Text.Lower(if [review_content] = null then "" else [review_content])
        in List.Sum(List.Transform([palavras], (p) => List.Count(Text.PositionOf(txt, p, Occurrence.All)))), Int64.Type),
    Final = Table.SelectColumns(Cont, {"product_id", "tema", "mencoes"})
in
    Final


// ===== CONSULTA 7: Fato_Produto =====
let
    Fonte = Produtos_Raw,
    // --- funções de limpeza: valor inválido ou vazio vira null (nunca zero)
    Moeda = (t as nullable text) as nullable number =>
        let s = Text.Remove(if t = null then "" else t, {"₹", ",", " "})
        in if s = "" then null else try Number.From(s, "en-US") otherwise null,
    Pct = (t as nullable text) as nullable number =>
        let s = Text.Remove(if t = null then "" else t, {"%", " "})
        in if s = "" then null else try Number.From(s, "en-US") / 100 otherwise null,
    Num = (t as nullable text) as nullable number =>
        let s = Text.Remove(if t = null then "" else t, {",", " "})
        in if s = "" then null else try Number.From(s, "en-US") otherwise null,
    ComId = Table.SelectRows(Fonte, each [product_id] <> null and [product_id] <> ""),
    Tipado = Table.TransformColumns(ComId, {
        {"discounted_price", Moeda, type number},
        {"actual_price", Moeda, type number},
        {"discount_percentage", Pct, type number},
        {"rating", Num, type number},
        {"rating_count", Num, Int64.Type}}),
    // rating fora de 1 a 5 não faz sentido: vira null
    RatingValido = Table.TransformColumns(Tipado, {{"rating", each if _ <> null and (_ < 1 or _ > 5) then null else _, type number}}),
    // --- 1 linha por produto (a primeira ocorrência de cada product_id)
    Unicos = Table.Distinct(RatingValido, {"product_id"}),
    // --- categorias hierárquicas (a coluna original separa os níveis por barra vertical)
    N1 = Table.AddColumn(Unicos, "categoria_nivel1", each Text.Split([category], "|"){0}, type text),
    N2 = Table.AddColumn(N1, "categoria_nivel2", each try Text.Split([category], "|"){1} otherwise null, type text),
    Folha = Table.AddColumn(N2, "categoria_folha", each List.Last(Text.Split([category], "|")), type text),
    // --- derivados comerciais
    Valor = Table.AddColumn(Folha, "desconto_valor", each [actual_price] - [discounted_price], type number),
    FaixaDesc = Table.AddColumn(Valor, "faixa_desconto", each
            @@FAIXA_DESCONTO@@, type text),
    FaixaPreco = Table.AddColumn(FaixaDesc, "faixa_preco", each
            @@FAIXA_PRECO@@, type text),
    Resumo = Table.TransformColumns(FaixaPreco, {{"about_product", each if _ = null then "" else Text.Start(_, 500), type text}}),
    // --- métricas de texto
    Mescla = Table.NestedJoin(Resumo, {"product_id"}, Sentimento_Produto, {"product_id"}, "s", JoinKind.LeftOuter),
    Expandido = Table.ExpandTableColumn(Mescla, "s", {"n_palavras", "palavras_positivas", "palavras_negativas", "saldo_sentimento"}),
    Final = Table.SelectColumns(Expandido, {"product_id", "product_name", "category", "categoria_nivel1", "categoria_nivel2", "categoria_folha",
        "discounted_price", "actual_price", "desconto_valor", "discount_percentage", "faixa_desconto", "faixa_preco",
        "rating", "rating_count", "n_palavras", "palavras_positivas", "palavras_negativas", "saldo_sentimento",
        "about_product", "product_link"})
in
    Final
'''


def gerar() -> str:
    txt = TEMPLATE
    txt = txt.replace("@@POSITIVAS@@", _lista(cfg.PALAVRAS_POSITIVAS))
    txt = txt.replace("@@NEGATIVAS@@", _lista(cfg.PALAVRAS_NEGATIVAS))
    txt = txt.replace("@@TEMAS@@", _temas())
    txt = txt.replace("@@FAIXA_DESCONTO@@", _faixas("discount_percentage", cfg.FAIXAS_DESCONTO, cfg.ROTULOS_DESCONTO))
    txt = txt.replace("@@FAIXA_PRECO@@", _faixas("actual_price", cfg.FAIXAS_PRECO, cfg.ROTULOS_PRECO))
    return txt


def _sem_comentarios(codigo: str) -> str:
    """Remove comentários // (fora de texto) linha a linha."""
    saida = []
    for linha in codigo.splitlines():
        dentro, cortar = False, None
        i = 0
        while i < len(linha):
            c = linha[i]
            if c == '"':
                if dentro and i + 1 < len(linha) and linha[i + 1] == '"':
                    i += 2
                    continue
                dentro = not dentro
            elif not dentro and linha.startswith("//", i):
                cortar = i
                break
            i += 1
        saida.append(linha if cortar is None else linha[:cortar])
    return "\n".join(saida)


def checar_sintaxe_basica(m: str) -> list[str]:
    """Checagem estática barata: delimitadores e aspas balanceados e estrutura let...in em cada consulta."""
    import re

    problemas = []
    pares = {")": "(", "}": "{", "]": "["}
    for bloco in m.split("// ===== CONSULTA")[1:]:
        titulo = bloco.splitlines()[0].strip()
        partes = re.split(r"\nlet\n", bloco, maxsplit=1)
        if len(partes) != 2:
            problemas.append(f"{titulo}: sem 'let'")
            continue
        codigo = _sem_comentarios(partes[1])
        if not re.search(r"\nin\n", codigo):
            problemas.append(f"{titulo}: sem 'in'")
        pilha, dentro, i = [], False, 0
        while i < len(codigo):
            c = codigo[i]
            if c == '"':
                if dentro and i + 1 < len(codigo) and codigo[i + 1] == '"':
                    i += 2
                    continue
                dentro = not dentro
            elif not dentro:
                if c in "({[":
                    pilha.append(c)
                elif c in pares and (not pilha or pilha.pop() != pares[c]):
                    problemas.append(f"{titulo}: fechamento '{c}' sem abertura")
            i += 1
        if dentro:
            problemas.append(f"{titulo}: aspas não fechadas")
        if pilha:
            problemas.append(f"{titulo}: delimitadores não fechados {pilha}")
        if "@@" in bloco:
            problemas.append(f"{titulo}: placeholder não substituído")
    return problemas


def main(destino: Path | None = None) -> Path:
    destino = destino or cfg.ROOT / "powerbi" / "consultas_power_query.m"
    m = gerar()
    problemas = checar_sintaxe_basica(m)
    if problemas:
        raise SystemExit("Problemas na geração do M:\n" + "\n".join(problemas))
    destino.write_text(m, encoding="utf-8")
    print(f"[power_query] {destino} gerado (checagem estática de sintaxe OK; 7 consultas)")
    return destino


if __name__ == "__main__":
    main()
