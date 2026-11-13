"""Preparação e tratamento dos dados (entregável: "Preparação e Tratamento dos Dados").

Entrada : amazon.csv bruto do Kaggle (um registro por linha de review agregada).
Saídas  : tabelas limpas, em estrela, prontas para o Power BI:
          - Fato_Produto       (1 linha por product_id)
          - Fato_ProdutoTema   (produto x tema, com contagem de menções)
          - Dim_Tema
          - Parametros         (cortes calculados, para documentar e auditar)
          - Texto_Produto      (texto agregado por produto; usado na análise, não vai ao Power BI)

Decisões metodológicas importantes (declarar no vídeo):
  * As colunas de review (user_id, review_id, review_title, review_content) trazem VÁRIAS reviews
    concatenadas na mesma célula, separadas por vírgula, e o texto das reviews também contém
    vírgulas. Separar por vírgula quebraria as reviews no meio. Por isso a análise de texto é feita
    POR PRODUTO (texto agregado), nunca por review individual.
  * rating e rating_count ausentes ou inválidos ficam nulos (nunca viram zero).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as cfg
from .util import sanear_para_excel

COLUNAS_OBRIGATORIAS = [
    "product_id", "product_name", "category", "discounted_price", "actual_price",
    "discount_percentage", "rating", "rating_count", "about_product",
    "review_title", "review_content",
]


# ----------------------------------------------------------------------------- leitura
def ler_csv_bruto(caminho: str | Path) -> pd.DataFrame:
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {caminho}\n"
            "Baixe o dataset em https://www.kaggle.com/datasets/karkavelrajaj/amazon-sales-dataset "
            "e salve como data/raw/amazon.csv (ou rode: python run_all.py --download)."
        )
    try:
        df = pd.read_csv(caminho, dtype=str, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(caminho, dtype=str, encoding="latin-1")
    df.columns = [c.strip() for c in df.columns]
    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltando:
        raise ValueError(f"Colunas obrigatórias ausentes no CSV: {faltando}. Colunas lidas: {list(df.columns)}")
    return df


# ----------------------------------------------------------------------------- conversões
def _para_numero(serie: pd.Series, remover: str) -> pd.Series:
    """Remove caracteres (regex `remover`) e converte para float; inválido vira NaN."""
    limpo = serie.astype("string").str.replace(remover, "", regex=True).str.strip()
    return pd.to_numeric(limpo, errors="coerce").astype("float64")


def _invalidos(bruto: pd.Series, convertido: pd.Series) -> int:
    """Quantos valores existiam no bruto mas não puderam ser convertidos."""
    return int((bruto.notna() & convertido.isna()).sum())


def _embelezar(texto):
    """'Computers&Accessories' -> 'Computers & Accessories'; 'HomeImprovement' -> 'Home Improvement'."""
    if not isinstance(texto, str):
        return texto
    t = texto.replace("&", " & ")
    t = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _tokens(texto: str) -> list[str]:
    return [t.strip("'") for t in re.findall(r"[a-z']{2,}", texto.lower())]


# ----------------------------------------------------------------------------- limpeza
def limpar_produtos(bruto: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Devolve (fato_produto_sem_texto_metrico, texto_produto, qualidade)."""
    q: dict = {"linhas_brutas": int(len(bruto))}
    df = bruto.copy()

    q["linhas_sem_product_id"] = int(df["product_id"].isna().sum())
    df = df[df["product_id"].notna()].copy()

    # --- conversões numéricas
    df["discounted_price"] = _para_numero(df["discounted_price"], r"[₹,\s]")
    df["actual_price"] = _para_numero(df["actual_price"], r"[₹,\s]")
    pct = _para_numero(df["discount_percentage"], r"[%\s]")
    q["discount_percentage_invalidos"] = _invalidos(df["discount_percentage"], pct)
    df["discount_percentage"] = pct / 100.0

    rating = _para_numero(df["rating"], r"[,\s]")
    q["rating_invalidos_texto"] = _invalidos(df["rating"], rating)  # ex.: o valor "|" do dataset
    df["rating"] = rating
    rcount = _para_numero(df["rating_count"], r"[,\s]")
    q["rating_count_invalidos_texto"] = _invalidos(df["rating_count"], rcount)
    df["rating_count"] = rcount

    # rating fora de 1 a 5 não faz sentido: anula
    fora = df["rating"].notna() & ~df["rating"].between(1, 5)
    q["rating_fora_de_1_a_5"] = int(fora.sum())
    df.loc[fora, "rating"] = np.nan

    # --- consistência: desconto informado vs. desconto recalculado pelos preços
    recalc = 1 - df["discounted_price"] / df["actual_price"]
    dif = (recalc - df["discount_percentage"]).abs()
    q["desconto_inconsistente_mais_de_2pp"] = int((dif > 0.02).sum())

    # --- categorias hierárquicas
    partes = df["category"].fillna("").str.split("|")
    df["categoria_nivel1"] = partes.str[0].map(_embelezar)
    df["categoria_nivel2"] = partes.str[1].map(_embelezar)
    df["categoria_folha"] = partes.str[-1].map(_embelezar)

    # --- 1 linha por produto
    q["product_ids_unicos"] = int(df["product_id"].nunique())
    q["linhas_duplicadas_de_product_id"] = int(len(df) - df["product_id"].nunique())
    g = df.groupby("product_id", sort=False)
    conflito = 0
    for col in ["discounted_price", "actual_price", "discount_percentage", "rating", "rating_count"]:
        conflito += int((g[col].nunique(dropna=True) > 1).sum())
    q["conflitos_numericos_entre_duplicatas"] = conflito

    escalares = ["product_name", "category", "categoria_nivel1", "categoria_nivel2", "categoria_folha",
                 "discounted_price", "actual_price", "discount_percentage", "rating", "rating_count",
                 "about_product"]
    for extra in ["product_link", "img_link"]:
        if extra in df.columns:
            escalares.append(extra)
    fato = g[escalares].first()
    fato["linhas_origem"] = g.size()

    juntar = lambda s: " | ".join(s.dropna().astype(str))  # noqa: E731
    texto = pd.DataFrame({
        "review_title": g["review_title"].agg(juntar),
        "review_content": g["review_content"].agg(juntar),
    })
    fato = fato.reset_index()
    texto = texto.reset_index()

    # --- derivados comerciais
    fato["desconto_valor"] = fato["actual_price"] - fato["discounted_price"]
    desc = pd.cut(fato["discount_percentage"], bins=cfg.FAIXAS_DESCONTO + [np.inf], right=False,
                  labels=cfg.ROTULOS_DESCONTO)
    fato["faixa_desconto"] = desc.astype(object).where(desc.notna(), cfg.SEM_DADO)
    preco = pd.cut(fato["actual_price"], bins=cfg.FAIXAS_PRECO + [np.inf], right=False,
                   labels=cfg.ROTULOS_PRECO)
    fato["faixa_preco"] = preco.astype(object).where(preco.notna(), cfg.SEM_DADO)

    q["produtos_sem_rating"] = int(fato["rating"].isna().sum())
    q["produtos_sem_rating_count"] = int(fato["rating_count"].isna().sum())
    q["produtos_sem_preco"] = int(fato["actual_price"].isna().sum())
    return fato, texto, q


# ----------------------------------------------------------------------------- texto
def metricas_de_texto(texto: pd.DataFrame) -> pd.DataFrame:
    """Sentimento por léxico (palavra inteira) e contagem de palavras, por produto."""
    pos, neg, nwords = [], [], []
    for t in texto["review_content"].fillna(""):
        toks = _tokens(t)
        nwords.append(len(toks))
        pos.append(sum(w in cfg.PALAVRAS_POSITIVAS for w in toks))
        neg.append(sum(w in cfg.PALAVRAS_NEGATIVAS for w in toks))
    out = pd.DataFrame({
        "product_id": texto["product_id"],
        "n_palavras": nwords,
        "palavras_positivas": pos,
        "palavras_negativas": neg,
    })
    total = out["palavras_positivas"] + out["palavras_negativas"]
    saldo = (out["palavras_positivas"] - out["palavras_negativas"]) / total.where(total > 0)
    out["saldo_sentimento"] = saldo  # -1 (só negativo) a +1 (só positivo); NaN se não houve palavra do léxico
    return out


def tabela_temas(texto: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    linhas = []
    for pid, t in zip(texto["product_id"], texto["review_content"].fillna("")):
        low = t.lower()
        for tema, radicais in cfg.TEMAS.items():
            linhas.append((pid, tema, int(sum(low.count(r) for r in radicais))))
    fato_tema = pd.DataFrame(linhas, columns=["product_id", "tema", "mencoes"])
    dim_tema = pd.DataFrame({
        "tema": list(cfg.TEMAS.keys()),
        "palavras_chave": [", ".join(v) for v in cfg.TEMAS.values()],
    })
    return fato_tema, dim_tema


# ----------------------------------------------------------------------------- classificações
def classificar(fato: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rating ajustado, grupos de nota/engajamento e quadrante. Devolve (fato, parametros)."""
    f = fato.copy()
    r, v = f["rating"], f["rating_count"]

    media_geral = r.mean()
    m = v.median()
    ajustado = (v / (v + m)) * r + (m / (v + m)) * media_geral
    f["rating_ajustado"] = ajustado.where(r.notna() & v.notna())

    q_rb, q_ra = r.quantile(cfg.RATING_BAIXO_Q), r.quantile(cfg.RATING_ALTO_Q)
    q_eb, q_ea = v.quantile(cfg.ENGAJ_BAIXO_Q), v.quantile(cfg.ENGAJ_ALTO_Q)

    f["grupo_nota"] = np.select(
        [r.isna(), r < q_rb, r >= q_ra], ["Sem dados", "Baixa", "Alta"], default="Média")
    f["grupo_engajamento"] = np.select(
        [v.isna(), v >= q_ea, v <= q_eb], ["Sem dados", "Alto", "Baixo"], default="Médio")

    cond = [
        (f["grupo_nota"] == "Sem dados") | (f["grupo_engajamento"] == "Sem dados"),
        (f["grupo_engajamento"] == "Alto") & (f["grupo_nota"] == "Baixa"),
        (f["grupo_engajamento"] == "Alto") & (f["grupo_nota"] == "Alta"),
        (f["grupo_engajamento"] == "Baixo") & (f["grupo_nota"] == "Alta"),
    ]
    f["quadrante"] = np.select(cond, ["Sem dados", "Alerta", "Estrela", "Joia escondida"], default="Demais")

    parametros = pd.DataFrame([
        ("rating_medio_geral", media_geral, "Média simples de rating (C do rating ajustado)"),
        ("rating_count_mediano", m, "Mediana de rating_count (m do rating ajustado)"),
        ("rating_q_baixo", q_rb, f"Quantil {cfg.RATING_BAIXO_Q:.0%} de rating: abaixo = grupo_nota Baixa"),
        ("rating_q_alto", q_ra, f"Quantil {cfg.RATING_ALTO_Q:.0%} de rating: a partir daqui = grupo_nota Alta"),
        ("engajamento_q_baixo", q_eb, f"Quantil {cfg.ENGAJ_BAIXO_Q:.0%} de rating_count: até aqui = Baixo"),
        ("engajamento_q_alto", q_ea, f"Quantil {cfg.ENGAJ_ALTO_Q:.0%} de rating_count: a partir daqui = Alto"),
    ], columns=["parametro", "valor", "descricao"])
    return f, parametros


# ----------------------------------------------------------------------------- saída
def _gravar_excel(tabelas: dict[str, pd.DataFrame], caminho: Path) -> None:
    from openpyxl.styles import Font, PatternFill

    with pd.ExcelWriter(caminho, engine="openpyxl") as xw:
        for nome, tab in tabelas.items():
            sanear_para_excel(tab).to_excel(xw, sheet_name=nome[:31], index=False)
            ws = xw.sheets[nome[:31]]
            ws.freeze_panes = "A2"
            for cel in ws[1]:
                cel.font = Font(name="Arial", bold=True, color="FFFFFF")
                cel.fill = PatternFill("solid", fgColor="1F3A5F")
            for col in ws.columns:
                largura = max(len(str(c.value)) if c.value is not None else 0 for c in list(col)[:200])
                ws.column_dimensions[col[0].column_letter].width = min(max(largura + 2, 10), 60)


def executar(arquivo: str | Path = cfg.ARQUIVO_PADRAO,
             saida: str | Path = cfg.DATA_PROCESSED,
             pasta_outputs: str | Path = cfg.OUTPUTS) -> dict[str, pd.DataFrame]:
    saida, pasta_outputs = Path(saida), Path(pasta_outputs)
    saida.mkdir(parents=True, exist_ok=True)
    pasta_outputs.mkdir(parents=True, exist_ok=True)

    print(f"[prepare] lendo {arquivo}")
    bruto = ler_csv_bruto(arquivo)
    fato, texto, qualidade = limpar_produtos(bruto)
    metricas = metricas_de_texto(texto)
    fato = fato.merge(metricas, on="product_id", how="left")
    fato, parametros = classificar(fato)
    fato_tema, dim_tema = tabela_temas(texto)

    # campos de texto curtos para tooltips no Power BI (o texto completo fica fora do modelo)
    fato["about_product"] = fato["about_product"].fillna("").str.slice(0, 500)
    fato = fato.merge(texto[["product_id", "review_title"]].assign(
        review_title=lambda d: d["review_title"].fillna("").str.slice(0, 300)), on="product_id", how="left")

    ordem = ["product_id", "product_name", "category", "categoria_nivel1", "categoria_nivel2", "categoria_folha",
             "discounted_price", "actual_price", "desconto_valor", "discount_percentage", "faixa_desconto",
             "faixa_preco", "rating", "rating_count", "rating_ajustado", "grupo_nota", "grupo_engajamento",
             "quadrante", "n_palavras", "palavras_positivas", "palavras_negativas", "saldo_sentimento",
             "linhas_origem", "about_product", "review_title"]
    ordem += [c for c in ["product_link", "img_link"] if c in fato.columns]
    fato = fato[ordem]
    fato["rating_count"] = fato["rating_count"].astype("Int64")

    qualidade.update({
        "produtos_finais": int(len(fato)),
        "categorias_nivel1": int(fato["categoria_nivel1"].nunique()),
        "produtos_por_categoria_nivel1": fato["categoria_nivel1"].value_counts().to_dict(),
    })

    tabelas = {"Fato_Produto": fato, "Fato_ProdutoTema": fato_tema, "Dim_Tema": dim_tema,
               "Parametros": parametros}
    for nome, tab in {**tabelas, "Texto_Produto": texto}.items():
        tab.to_csv(saida / f"{nome.lower()}.csv", index=False, encoding="utf-8-sig")
    # Excel é o formato recomendado para o Power BI: números já tipados, sem problema de locale.
    _gravar_excel(tabelas, saida / "dados_powerbi.xlsx")
    (pasta_outputs / "qualidade_dados.json").write_text(
        json.dumps(qualidade, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[prepare] produtos: {len(fato)} | categorias: {fato['categoria_nivel1'].nunique()} | "
          f"sem rating: {qualidade['produtos_sem_rating']} | sem rating_count: {qualidade['produtos_sem_rating_count']}")
    print(f"[prepare] gravado em {saida}")
    return {**tabelas, "Texto_Produto": texto, "qualidade": qualidade}  # type: ignore[dict-item]


if __name__ == "__main__":
    executar()
