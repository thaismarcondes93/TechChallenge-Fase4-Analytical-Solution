"""Funções de preparação usadas pelo notebook Analise_Amazon.ipynb.

O arquivo torna o notebook executável dentro da estrutura final do projeto,
sem depender de pastas ou módulos de versões anteriores.
"""
from types import SimpleNamespace
import re

import numpy as np
import pandas as pd


cfg = SimpleNamespace(
    RATING_BAIXO_Q=0.25,
    RATING_ALTO_Q=0.75,
    ENGAJ_BAIXO_Q=0.25,
    ENGAJ_ALTO_Q=0.75,
    FAIXAS_DESCONTO=[0.0, 0.2, 0.4, 0.6, 0.8],
    ROTULOS_DESCONTO=["1. 0-19%", "2. 20-39%", "3. 40-59%", "4. 60-79%", "5. 80% ou mais"],
    FAIXAS_PRECO=[0, 500, 2000, 5000],
    ROTULOS_PRECO=["1. Até 500", "2. 500-1.999", "3. 2.000-4.999", "4. 5.000 ou mais"],
    SEM_DADO="0. Sem dado",
    PALAVRAS_POSITIVAS={"great", "good", "excellent", "love", "loved", "perfect", "best", "worth", "value", "nice", "amazing", "fast", "easy", "sturdy", "durable", "recommend", "recommended", "happy", "satisfied", "awesome", "superb", "fantastic", "wonderful", "impressed", "smooth", "comfortable", "reliable", "useful", "helpful", "bright", "clear", "crisp"},
    PALAVRAS_NEGATIVAS={"bad", "poor", "worst", "waste", "broke", "broken", "stopped", "defective", "fake", "disappointed", "disappointing", "useless", "issue", "issues", "problem", "problems", "fail", "failed", "failure", "slow", "faulty", "damaged", "refund", "refunded", "flimsy", "loose", "overheating", "heating", "terrible", "horrible", "worthless", "scam", "returned", "noisy", "laggy", "drains"},
    TEMAS={
        "Qualidade e acabamento": ["quality", "build", "material", "sturdy", "flimsy", "finish"],
        "Durabilidade e defeitos": ["durab", "broke", "stopped working", "defect", "faulty", "damag", "died"],
        "Preço e custo-benefício": ["price", "money", "value", "worth", "cheap", "affordable", "budget", "expensive"],
        "Bateria e carregamento": ["batter", "charg", "backup"],
        "Instalação e facilidade de uso": ["install", "setup", "set up", "easy", "user friendly"],
        "Compatibilidade e conexão": ["compatib", "connect", "bluetooth", "wifi", "wi-fi", "usb", "port"],
        "Som, imagem e desempenho": ["sound", "bass", "audio", "picture", "display", "screen", "speed", "performance"],
        "Entrega, embalagem e atendimento": ["deliver", "packag", "seller", "customer service", "warranty", "refund", "replacement"],
    },
)

COLUNAS_OBRIGATORIAS = [
    "product_id", "product_name", "category", "discounted_price", "actual_price",
    "discount_percentage", "rating", "rating_count", "about_product",
    "review_title", "review_content",
]


def _para_numero(serie, remover):
    return pd.to_numeric(serie.astype("string").str.replace(remover, "", regex=True).str.strip(), errors="coerce").astype("float64")


def _embelezar(texto):
    if not isinstance(texto, str):
        return texto
    texto = texto.replace("&", " & ")
    return re.sub(r"\s+", " ", re.sub(r"(?<=[a-z])(?=[A-Z])", " ", texto)).strip()


def limpar_produtos(bruto):
    """Converte campos, cria categorias e faixas comerciais para uma linha por SKU."""
    df = bruto.copy()
    auditoria = {"linhas_brutas": int(len(df))}
    df["discounted_price"] = _para_numero(df["discounted_price"], r"[₹,\s]")
    df["actual_price"] = _para_numero(df["actual_price"], r"[₹,\s]")
    percentual = _para_numero(df["discount_percentage"], r"[%\s]")
    df["discount_percentage"] = percentual / 100
    df["rating"] = _para_numero(df["rating"], r"[,\s]").where(lambda s: s.between(1, 5))
    df["rating_count"] = _para_numero(df["rating_count"], r"[,\s]")
    auditoria["desconto_inconsistente_mais_de_2pp"] = int(((1 - df["discounted_price"] / df["actual_price"] - df["discount_percentage"]).abs() > 0.02).sum())
    partes = df["category"].fillna("").str.split("|")
    df["categoria_nivel1"] = partes.str[0].map(_embelezar)
    df["categoria_nivel2"] = partes.str[1].map(_embelezar)
    df["categoria_folha"] = partes.str[-1].map(_embelezar)
    fato = df.reset_index(drop=True).copy()
    fato["desconto_valor"] = fato["actual_price"] - fato["discounted_price"]
    desconto = pd.cut(fato["discount_percentage"], bins=cfg.FAIXAS_DESCONTO + [np.inf], right=False, labels=cfg.ROTULOS_DESCONTO)
    preco = pd.cut(fato["actual_price"], bins=cfg.FAIXAS_PRECO + [np.inf], right=False, labels=cfg.ROTULOS_PRECO)
    fato["faixa_desconto"] = desconto.astype(object).where(desconto.notna(), cfg.SEM_DADO)
    fato["faixa_preco"] = preco.astype(object).where(preco.notna(), cfg.SEM_DADO)
    return fato, pd.DataFrame(), auditoria


def metricas_de_texto(texto):
    positivos, negativos, palavras = [], [], []
    for conteudo in texto["review_content"].fillna(""):
        tokens = [t.strip("'") for t in re.findall(r"[a-z']{2,}", conteudo.lower())]
        palavras.append(len(tokens))
        positivos.append(sum(token in cfg.PALAVRAS_POSITIVAS for token in tokens))
        negativos.append(sum(token in cfg.PALAVRAS_NEGATIVAS for token in tokens))
    resultado = pd.DataFrame({"product_id": texto["product_id"], "n_palavras": palavras, "palavras_positivas": positivos, "palavras_negativas": negativos})
    total = resultado["palavras_positivas"] + resultado["palavras_negativas"]
    resultado["saldo_sentimento"] = (resultado["palavras_positivas"] - resultado["palavras_negativas"]) / total.where(total > 0)
    return resultado


def tabela_temas(texto):
    linhas = []
    for product_id, conteudo in zip(texto["product_id"], texto["review_content"].fillna("")):
        texto_minusculo = conteudo.lower()
        for tema, termos in cfg.TEMAS.items():
            linhas.append((product_id, tema, int(sum(texto_minusculo.count(termo) for termo in termos))))
    fato_tema = pd.DataFrame(linhas, columns=["product_id", "tema", "mencoes"])
    dim_tema = pd.DataFrame({"tema": list(cfg.TEMAS), "palavras_chave": [", ".join(termos) for termos in cfg.TEMAS.values()]})
    return fato_tema, dim_tema


def classificar(fato):
    resultado = fato.copy()
    nota, avaliacoes = resultado["rating"], resultado["rating_count"]
    media_geral, mediana_avaliacoes = nota.mean(), avaliacoes.median()
    resultado["rating_ajustado"] = ((avaliacoes / (avaliacoes + mediana_avaliacoes)) * nota + (mediana_avaliacoes / (avaliacoes + mediana_avaliacoes)) * media_geral).where(nota.notna() & avaliacoes.notna())
    nota_baixa, nota_alta = nota.quantile(cfg.RATING_BAIXO_Q), nota.quantile(cfg.RATING_ALTO_Q)
    eng_baixo, eng_alto = avaliacoes.quantile(cfg.ENGAJ_BAIXO_Q), avaliacoes.quantile(cfg.ENGAJ_ALTO_Q)
    resultado["grupo_nota"] = np.select([nota.isna(), nota < nota_baixa, nota >= nota_alta], ["Sem dados", "Baixa", "Alta"], default="Média")
    resultado["grupo_engajamento"] = np.select([avaliacoes.isna(), avaliacoes >= eng_alto, avaliacoes <= eng_baixo], ["Sem dados", "Alto", "Baixo"], default="Médio")
    resultado["quadrante"] = np.select([
        (resultado["grupo_nota"] == "Sem dados") | (resultado["grupo_engajamento"] == "Sem dados"),
        (resultado["grupo_nota"] == "Baixa") & (resultado["grupo_engajamento"] == "Alto"),
        (resultado["grupo_nota"] == "Alta") & (resultado["grupo_engajamento"] == "Alto"),
        (resultado["grupo_nota"] == "Alta") & (resultado["grupo_engajamento"] == "Baixo"),
    ], ["Sem dados", "Alerta", "Estrela", "Joia escondida"], default="Demais")
    parametros = pd.DataFrame([
        ("rating_medio_geral", media_geral, "Média simples de rating (C do rating ajustado)"),
        ("rating_count_mediano", mediana_avaliacoes, "Mediana de rating_count (m do rating ajustado)"),
        ("rating_q_baixo", nota_baixa, "Quantil inferior de rating"),
        ("rating_q_alto", nota_alta, "Quantil superior de rating"),
        ("engajamento_q_baixo", eng_baixo, "Quantil inferior de rating_count"),
        ("engajamento_q_alto", eng_alto, "Quantil superior de rating_count"),
    ], columns=["parametro", "valor", "descricao"])
    return resultado, parametros


prepare = SimpleNamespace(
    cfg=cfg,
    COLUNAS_OBRIGATORIAS=COLUNAS_OBRIGATORIAS,
    limpar_produtos=limpar_produtos,
    metricas_de_texto=metricas_de_texto,
    tabela_temas=tabela_temas,
    classificar=classificar,
)
