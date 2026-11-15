// Crie uma consulta em branco por bloco e use o nome indicado.
// Crie PastaDados primeiro. Desative sua carga no modelo.

// PastaDados
"C:\Users\thais\OneDrive\Documentos\Pós -FIAP\Challenge 4\tech_challenge_amazon\Analise_V2\entrega\dados_powerbi" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

// Fato_Produto
let
    Fonte = Csv.Document(File.Contents(PastaDados & "\Fato_Produto.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Cabecalhos = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    Tipos = Table.TransformColumnTypes(Cabecalhos, {{"product_id", type text}, {"product_name", type text}, {"category", type text}, {"categoria_nivel1", type text}, {"categoria_nivel2", type text}, {"categoria_folha", type text}, {"faixa_desconto", type text}, {"faixa_preco", type text}, {"about_product", type text}, {"rotulo_produto", type text}, {"review_title", type text}, {"grupo_nota", type text}, {"grupo_engajamento", type text}, {"quadrante", type text}, {"actual_price", type number}, {"discounted_price", type number}, {"desconto_valor", type number}, {"discount_percentage", type number}, {"rating", type number}, {"rating_ajustado", type number}, {"saldo_sentimento", type number}, {"rating_count", Int64.Type}, {"linhas_origem", Int64.Type}, {"ordem_desconto", Int64.Type}, {"tem_descricao", Int64.Type}, {"n_palavras", Int64.Type}, {"palavras_positivas", Int64.Type}, {"palavras_negativas", Int64.Type}, {"tem_comentario", Int64.Type}}, "en-US")
in
    Tipos

// Fato_ProdutoTema
let
    Fonte = Csv.Document(File.Contents(PastaDados & "\Fato_ProdutoTema.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Cabecalhos = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    Tipos = Table.TransformColumnTypes(Cabecalhos, {{"product_id", type text}, {"tema", type text}, {"mencoes", Int64.Type}}, "en-US")
in
    Tipos

// Dim_Tema
let
    Fonte = Csv.Document(File.Contents(PastaDados & "\Dim_Tema.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Cabecalhos = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    Tipos = Table.TransformColumnTypes(Cabecalhos, {{"tema", type text}, {"palavras_chave", type text}}, "en-US")
in
    Tipos

// Parametros
let
    Fonte = Csv.Document(File.Contents(PastaDados & "\Parametros.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Cabecalhos = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
    Tipos = Table.TransformColumnTypes(Cabecalhos, {{"parametro", type text}, {"descricao", type text}, {"valor", type number}}, "en-US")
in
    Tipos
