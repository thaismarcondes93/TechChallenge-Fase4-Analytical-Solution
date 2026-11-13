// =====================================================================================
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
    Pos = List.Buffer({"amazing", "awesome", "best", "bright", "clear", "comfortable", "crisp", "durable", "easy", "excellent", "fantastic", "fast", "good", "great", "happy", "helpful", "impressed", "love", "loved", "nice", "perfect", "recommend", "recommended", "reliable", "satisfied", "smooth", "sturdy", "superb", "useful", "value", "wonderful", "worth"}),
    Neg = List.Buffer({"bad", "broke", "broken", "damaged", "defective", "disappointed", "disappointing", "drains", "fail", "failed", "failure", "fake", "faulty", "flimsy", "heating", "horrible", "issue", "issues", "laggy", "loose", "noisy", "overheating", "poor", "problem", "problems", "refund", "refunded", "returned", "scam", "slow", "stopped", "terrible", "useless", "waste", "worst", "worthless"}),
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
        {"Qualidade e acabamento", {"build", "finish", "flimsy", "material", "quality", "sturdy"}},
        {"Durabilidade e defeitos", {"broke", "damag", "defect", "died", "durab", "faulty", "stopped working"}},
        {"Preço e custo-benefício", {"affordable", "budget", "cheap", "expensive", "money", "price", "value", "worth"}},
        {"Bateria e carregamento", {"backup", "batter", "charg"}},
        {"Instalação e facilidade de uso", {"easy", "install", "set up", "setup", "user friendly"}},
        {"Compatibilidade e conexão", {"bluetooth", "compatib", "connect", "port", "usb", "wi-fi", "wifi"}},
        {"Som, imagem e desempenho", {"audio", "bass", "display", "performance", "picture", "screen", "sound", "speed"}},
        {"Entrega, embalagem e atendimento", {"customer service", "deliver", "packag", "refund", "replacement", "seller", "warranty"}}
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
            if [discount_percentage] = null then "0. Sem dado"
            else if [discount_percentage] < 0.2 then "1. 0-19%"
            else if [discount_percentage] < 0.4 then "2. 20-39%"
            else if [discount_percentage] < 0.6 then "3. 40-59%"
            else if [discount_percentage] < 0.8 then "4. 60-79%"
            else "5. 80% ou mais", type text),
    FaixaPreco = Table.AddColumn(FaixaDesc, "faixa_preco", each
            if [actual_price] = null then "0. Sem dado"
            else if [actual_price] < 500 then "1. Até 500"
            else if [actual_price] < 2000 then "2. 500-1.999"
            else if [actual_price] < 5000 then "3. 2.000-4.999"
            else "4. 5.000 ou mais", type text),
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
