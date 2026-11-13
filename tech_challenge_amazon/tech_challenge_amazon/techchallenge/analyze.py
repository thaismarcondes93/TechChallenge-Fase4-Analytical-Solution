"""Análises do Tech Challenge: indicadores, relação preço-desconto-engajamento-satisfação,
quadrantes, categorias e customer insights (temas, sentimento e palavras distintivas).

Tudo é calculado a partir das tabelas de `prepare.py`. Resultados:
  outputs/tables/*.csv       tabelas de resultado
  outputs/analise_resultados.xlsx
  outputs/figures/*.png      gráficos para usar no vídeo/relatório
"""
from __future__ import annotations

import re
import traceback
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from . import config as cfg  # noqa: E402
from .util import sanear_para_excel  # noqa: E402

COR = {"azul": "#1F3A5F", "verde": "#2A9D8F", "ambar": "#E9A23B", "vermelho": "#C8553D", "cinza": "#8A8F98",
       "claro": "#D9DEE5"}
COR_QUADRANTE = {"Estrela": COR["verde"], "Alerta": COR["vermelho"], "Joia escondida": COR["ambar"],
                 "Demais": COR["claro"], "Sem dados": COR["claro"]}

plt.rcParams.update({
    "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 110, "savefig.dpi": 150,
    "axes.titleweight": "bold", "axes.titlesize": 12, "axes.labelcolor": "#333333",
    "axes.edgecolor": "#888888", "xtick.color": "#444444", "ytick.color": "#444444",
})


# ======================================================================================
# utilidades
# ======================================================================================
def _carregar(dados: dict | None, pasta: Path) -> dict:
    if dados is not None:
        return dados
    lidas = {}
    for nome in ["Fato_Produto", "Fato_ProdutoTema", "Dim_Tema", "Parametros", "Texto_Produto"]:
        lidas[nome] = pd.read_csv(pasta / f"{nome.lower()}.csv", encoding="utf-8-sig")
    import json
    q = Path(cfg.OUTPUTS) / "qualidade_dados.json"
    lidas["qualidade"] = json.loads(q.read_text(encoding="utf-8")) if q.exists() else {}
    return lidas


def correlacao(x: pd.Series, y: pd.Series, repeticoes: int = cfg.BOOTSTRAP_REPETICOES,
               semente: int = cfg.SEMENTE) -> dict:
    """Pearson, Spearman e IC95% do Spearman por bootstrap."""
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    n = len(d)
    vazio = {"n": n, "pearson": np.nan, "spearman": np.nan, "ic95_baixo": np.nan, "ic95_alto": np.nan}
    if n < 30 or d["x"].nunique() < 2 or d["y"].nunique() < 2:
        return vazio
    xr, yr = d["x"].rank().to_numpy(), d["y"].rank().to_numpy()
    rho = float(np.corrcoef(xr, yr)[0, 1])
    rng = np.random.default_rng(semente)
    idx = rng.integers(0, n, size=(repeticoes, n))
    xs, ys = xr[idx], yr[idx]
    xs = xs - xs.mean(axis=1, keepdims=True)
    ys = ys - ys.mean(axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = (xs * ys).sum(axis=1) / np.sqrt((xs ** 2).sum(axis=1) * (ys ** 2).sum(axis=1))
    lo, hi = np.nanpercentile(r, [2.5, 97.5])
    return {"n": n, "pearson": float(d["x"].corr(d["y"])), "spearman": rho,
            "ic95_baixo": float(lo), "ic95_alto": float(hi)}


def _tokens(texto: str) -> list[str]:
    return [t.strip("'") for t in re.findall(r"[a-z']{3,}", str(texto).lower())]


def _contar_palavras(textos) -> Counter:
    c: Counter = Counter()
    for t in textos:
        c.update(w for w in _tokens(t) if w not in cfg.STOPWORDS)
    return c


def _contar_bigramas(textos) -> Counter:
    c: Counter = Counter()
    for t in textos:
        toks = [w for w in _tokens(t)]
        for a, b in zip(toks, toks[1:]):
            if a not in cfg.STOPWORDS and b not in cfg.STOPWORDS:
                c[f"{a} {b}"] += 1
    return c


def palavras_distintivas(textos_alta, textos_baixa, minimo: int = 15, topn: int = 15,
                         alpha: float = 0.5) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Log-odds suavizado: palavras mais típicas de produtos de nota alta vs. nota baixa."""
    ca, cb = _contar_palavras(textos_alta), _contar_palavras(textos_baixa)
    vocab = [w for w in set(ca) | set(cb) if ca[w] + cb[w] >= minimo]
    colunas = ["palavra", "score", "contagem_alta", "contagem_baixa"]
    if not vocab:
        return pd.DataFrame(columns=colunas), pd.DataFrame(columns=colunas)
    na, nb = sum(ca[w] for w in vocab), sum(cb[w] for w in vocab)
    v = len(vocab)
    linhas = []
    for w in vocab:
        s = np.log((ca[w] + alpha) / (na + alpha * v)) - np.log((cb[w] + alpha) / (nb + alpha * v))
        linhas.append((w, float(s), ca[w], cb[w]))
    t = pd.DataFrame(linhas, columns=colunas).sort_values("score", ascending=False)
    return t.head(topn).reset_index(drop=True), t.tail(topn).sort_values("score").reset_index(drop=True)


def _agregar_categoria(fp: pd.DataFrame, chave: str) -> pd.DataFrame:
    tmp = fp.assign(_w=fp["rating"] * fp["rating_count"],
                    _wc=fp["rating_count"].where(fp["rating"].notna()))
    ag = tmp.groupby(chave).agg(
        n_produtos=("product_id", "nunique"),
        total_avaliacoes=("rating_count", "sum"),
        rating_medio=("rating", "mean"),
        rating_ajustado_medio=("rating_ajustado", "mean"),
        desconto_medio=("discount_percentage", "mean"),
        preco_medio_original=("actual_price", "mean"),
        preco_medio_final=("discounted_price", "mean"),
        sentimento_medio=("saldo_sentimento", "mean"),
        _w=("_w", "sum"), _wc=("_wc", "sum"),
    )
    ag["rating_ponderado"] = ag["_w"] / ag["_wc"].where(ag["_wc"] > 0)
    ag = ag.drop(columns=["_w", "_wc"]).reset_index()
    ag["participacao_avaliacoes"] = ag["total_avaliacoes"] / ag["total_avaliacoes"].sum()
    ag["amostra_pequena"] = ag["n_produtos"] < cfg.MIN_PRODUTOS_CATEGORIA
    return ag.sort_values("total_avaliacoes", ascending=False).reset_index(drop=True)


# ======================================================================================
# cálculo principal
# ======================================================================================
def calcular(dados: dict) -> dict:
    fp = dados["Fato_Produto"].copy()
    fp["rating_count"] = pd.to_numeric(fp["rating_count"], errors="coerce").astype("float64")
    texto = dados["Texto_Produto"][["product_id", "review_content"]]
    tema_long = dados["Fato_ProdutoTema"]
    par = dict(zip(dados["Parametros"]["parametro"], dados["Parametros"]["valor"]))
    res: dict = {"avisos": [], "parametros": par, "qualidade": dados.get("qualidade", {})}

    # ---------------------------------------------------------------- KPIs e Pareto
    valido = fp.dropna(subset=["rating", "rating_count"])
    k = {
        "n_produtos": int(len(fp)),
        "n_categorias": int(fp["categoria_nivel1"].nunique()),
        "total_avaliacoes": float(fp["rating_count"].sum()),
        "rating_medio": float(fp["rating"].mean()),
        "rating_mediano": float(fp["rating"].median()),
        "rating_ponderado": float((valido["rating"] * valido["rating_count"]).sum() / valido["rating_count"].sum()),
        "desconto_medio": float(fp["discount_percentage"].mean()),
        "desconto_mediano": float(fp["discount_percentage"].median()),
        "preco_medio_original": float(fp["actual_price"].mean()),
        "preco_medio_final": float(fp["discounted_price"].mean()),
        "economia_media": float(fp["desconto_valor"].mean()),
        "pct_rating_ge_4": float((fp["rating"] >= 4).sum() / fp["rating"].notna().sum()),
        "pct_rating_lt_35": float((fp["rating"] < 3.5).sum() / fp["rating"].notna().sum()),
        "rating_min": float(fp["rating"].min()), "rating_max": float(fp["rating"].max()),
        "rating_p10": float(fp["rating"].quantile(0.10)), "rating_p90": float(fp["rating"].quantile(0.90)),
    }
    res["kpis"] = k

    ordenado = fp["rating_count"].dropna().sort_values(ascending=False).to_numpy()
    acum = np.cumsum(ordenado) / ordenado.sum()
    n = len(ordenado)
    res["pareto"] = {
        "top10_participacao": float(ordenado[:10].sum() / ordenado.sum()),
        "top10pct_participacao": float(ordenado[: max(1, int(round(n * 0.10)))].sum() / ordenado.sum()),
        "produtos_para_50pct": int(np.searchsorted(acum, 0.5) + 1),
        "produtos_para_80pct": int(np.searchsorted(acum, 0.8) + 1),
        "n_com_avaliacoes": n,
        "curva": acum,
    }

    # ---------------------------------------------------------------- categorias
    res["categorias"] = _agregar_categoria(fp, "categoria_nivel1")
    sub = _agregar_categoria(fp, "categoria_nivel2")
    res["subcategorias"] = sub[sub["n_produtos"] >= cfg.MIN_PRODUTOS_CATEGORIA].reset_index(drop=True)

    # ---------------------------------------------------------------- preço, desconto, engajamento, satisfação
    fp["log_avaliacoes"] = np.log1p(fp["rating_count"])
    pares = [
        ("Desconto x Nota", fp["discount_percentage"], fp["rating"]),
        ("Desconto x Engajamento (log avaliações)", fp["discount_percentage"], fp["log_avaliacoes"]),
        ("Preço original x Nota", fp["actual_price"], fp["rating"]),
        ("Preço original x Desconto", fp["actual_price"], fp["discount_percentage"]),
        ("Engajamento (log avaliações) x Nota", fp["log_avaliacoes"], fp["rating"]),
    ]
    linhas = []
    for nome, x, y in pares:
        c = correlacao(x, y)
        linhas.append({"relacao": nome, **c})
    res["correlacoes"] = pd.DataFrame(linhas)

    lc = []
    for cat, g in fp.groupby("categoria_nivel1"):
        if len(g) >= cfg.MIN_PRODUTOS_CATEGORIA:
            c = correlacao(g["discount_percentage"], g["rating"], repeticoes=300)
            lc.append({"categoria_nivel1": cat, **c})
    res["correlacao_desconto_nota_por_categoria"] = pd.DataFrame(lc)

    def _faixa(chave: str) -> pd.DataFrame:
        base = fp[fp[chave] != cfg.SEM_DADO]
        return base.groupby(chave).agg(
            n_produtos=("product_id", "nunique"), rating_medio=("rating", "mean"),
            rating_mediano=("rating", "median"), avaliacoes_total=("rating_count", "sum"),
            avaliacoes_mediana=("rating_count", "median"), desconto_medio=("discount_percentage", "mean"),
            preco_medio_original=("actual_price", "mean")).reset_index()

    res["faixas_desconto"] = _faixa("faixa_desconto")
    res["faixas_preco"] = _faixa("faixa_preco")
    base = fp[(fp["faixa_desconto"] != cfg.SEM_DADO) & (fp["faixa_preco"] != cfg.SEM_DADO)]
    res["heatmap_rating"] = base.pivot_table(index="faixa_preco", columns="faixa_desconto", values="rating",
                                              aggfunc="mean")
    res["heatmap_n"] = base.pivot_table(index="faixa_preco", columns="faixa_desconto", values="product_id",
                                         aggfunc="nunique").fillna(0).astype(int)

    # ---------------------------------------------------------------- quadrantes
    q = fp.groupby("quadrante").agg(
        n_produtos=("product_id", "nunique"), total_avaliacoes=("rating_count", "sum"),
        rating_medio=("rating", "mean"), desconto_medio=("discount_percentage", "mean"),
        preco_medio_final=("discounted_price", "mean")).reset_index()
    q["participacao_produtos"] = q["n_produtos"] / q["n_produtos"].sum()
    q["participacao_avaliacoes"] = q["total_avaliacoes"] / q["total_avaliacoes"].sum()
    res["quadrantes"] = q

    cols = ["product_id", "product_name", "categoria_nivel1", "rating", "rating_count", "rating_ajustado",
            "discount_percentage", "discounted_price", "saldo_sentimento"]
    if "product_link" in fp.columns:
        cols.append("product_link")
    res["lista_alerta"] = (fp[fp["quadrante"] == "Alerta"].sort_values(["rating_count"], ascending=False)[cols]
                           .head(15).reset_index(drop=True))
    res["lista_joias"] = (fp[fp["quadrante"] == "Joia escondida"].sort_values(["rating", "rating_count"],
                          ascending=[False, False])[cols].head(15).reset_index(drop=True))
    res["lista_estrelas"] = (fp[fp["quadrante"] == "Estrela"].sort_values("rating_ajustado", ascending=False)[cols]
                             .head(15).reset_index(drop=True))
    res["top_engajamento"] = fp.sort_values("rating_count", ascending=False)[cols].head(15).reset_index(drop=True)

    # ---------------------------------------------------------------- customer insights
    s = fp[["rating", "saldo_sentimento"]].dropna()
    res["sentimento"] = {"n": int(len(s)),
                         "spearman_com_rating": float(s["rating"].rank().corr(s["saldo_sentimento"].rank()))
                         if len(s) > 30 else np.nan}
    res["sentimento_categoria"] = (fp.groupby("categoria_nivel1").agg(
        n_produtos=("product_id", "nunique"), saldo_sentimento_medio=("saldo_sentimento", "mean"))
        .reset_index().sort_values("saldo_sentimento_medio"))

    n_alta, n_baixa = int((fp["grupo_nota"] == "Alta").sum()), int((fp["grupo_nota"] == "Baixa").sum())
    res["n_grupo_alta"], res["n_grupo_baixa"] = n_alta, n_baixa
    if min(n_alta, n_baixa) < cfg.MIN_PRODUTOS_GRUPO_TEXTO:
        res["avisos"].append(f"Grupos de nota muito pequenos para texto (alta={n_alta}, baixa={n_baixa}).")

    tf = tema_long.merge(fp[["product_id", "grupo_nota", "n_palavras", "categoria_nivel1"]], on="product_id")
    linhas = []
    for tema, sub_t in tf.groupby("tema"):
        reg = {"tema": tema, "mencoes_total": int(sub_t["mencoes"].sum()),
               "mencoes_por_mil_palavras_geral": float(sub_t["mencoes"].sum() / sub_t["n_palavras"].sum() * 1000)}
        for g, rot in [("Alta", "alta"), ("Baixa", "baixa")]:
            x = sub_t[sub_t["grupo_nota"] == g]
            palavras = x["n_palavras"].sum()
            reg[f"mencoes_{rot}"] = int(x["mencoes"].sum())
            reg[f"por_mil_palavras_{rot}"] = float(x["mencoes"].sum() / palavras * 1000) if palavras else np.nan
            reg[f"pct_produtos_{rot}"] = float((x["mencoes"] > 0).mean()) if len(x) else np.nan
        reg["lift_baixa_sobre_alta"] = (reg["por_mil_palavras_baixa"] / reg["por_mil_palavras_alta"]
                                        if reg["por_mil_palavras_alta"] else np.nan)
        reg["evidencia_suficiente"] = bool(min(reg["mencoes_alta"], reg["mencoes_baixa"]) >= cfg.MIN_MENCOES_TEMA)
        linhas.append(reg)
    res["temas"] = pd.DataFrame(linhas).sort_values("lift_baixa_sobre_alta", ascending=False).reset_index(drop=True)

    tc = tf.groupby(["categoria_nivel1", "tema"]).agg(m=("mencoes", "sum"), p=("n_palavras", "sum")).reset_index()
    tc["mencoes_por_mil_palavras"] = tc["m"] / tc["p"].where(tc["p"] > 0) * 1000
    res["tema_por_categoria"] = tc.pivot(index="categoria_nivel1", columns="tema",
                                         values="mencoes_por_mil_palavras").reset_index()

    ids_alta = set(fp.loc[fp["grupo_nota"] == "Alta", "product_id"])
    ids_baixa = set(fp.loc[fp["grupo_nota"] == "Baixa", "product_id"])
    t_alta = texto.loc[texto["product_id"].isin(ids_alta), "review_content"].fillna("")
    t_baixa = texto.loc[texto["product_id"].isin(ids_baixa), "review_content"].fillna("")
    res["palavras_alta"], res["palavras_baixa"] = palavras_distintivas(t_alta, t_baixa)

    def _top(c: Counter, nome: str, n: int = 20) -> pd.DataFrame:
        return pd.DataFrame(c.most_common(n), columns=[nome, "contagem"])

    res["palavras_frequentes_alta"] = _top(_contar_palavras(t_alta), "palavra")
    res["palavras_frequentes_baixa"] = _top(_contar_palavras(t_baixa), "palavra")
    res["bigramas_alta"] = _top(_contar_bigramas(t_alta), "bigrama", 15)
    res["bigramas_baixa"] = _top(_contar_bigramas(t_baixa), "bigrama", 15)
    return res


# ======================================================================================
# gráficos
# ======================================================================================
def _salvar(fig, caminho: Path) -> None:
    fig.tight_layout()
    fig.savefig(caminho, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _fmt_milhar(x, _=None) -> str:
    if x >= 1e6:
        return f"{x / 1e6:.1f}M"
    if x >= 1e3:
        return f"{x / 1e3:.0f}k"
    return f"{x:.0f}"


def g_distribuicoes(fp, res, pasta: Path):
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    r = fp["rating"].dropna()
    ax[0].hist(r, bins=np.arange(r.min() - 0.05, r.max() + 0.15, 0.1), color=COR["azul"], edgecolor="white")
    ax[0].axvline(r.median(), color=COR["ambar"], lw=2, label=f"mediana {r.median():.1f}".replace(".", ","))
    ax[0].set(title="Distribuição das notas", xlabel="Nota (rating)", ylabel="Nº de produtos")
    ax[0].legend(frameon=False)
    v = fp["rating_count"].dropna()
    v = v[v > 0]
    ax[1].hist(np.log10(v), bins=30, color=COR["verde"], edgecolor="white")
    ax[1].set(title="Distribuição do engajamento", xlabel="Nº de avaliações (escala log10)", ylabel="Nº de produtos")
    ax[1].set_xticks(np.log10([10, 100, 1e3, 1e4, 1e5]))
    ax[1].set_xticklabels(["10", "100", "1k", "10k", "100k"])
    acum = res["pareto"]["curva"]
    ax[2].plot(np.arange(1, len(acum) + 1) / len(acum) * 100, acum * 100, color=COR["azul"], lw=2)
    ax[2].axhline(80, color=COR["cinza"], ls="--", lw=1)
    ax[2].set(title="Concentração das avaliações (Pareto)", xlabel="% de produtos (do mais ao menos avaliado)",
              ylabel="% acumulado de avaliações")
    n80 = res["pareto"]["produtos_para_80pct"]
    x80 = n80 / len(acum) * 100
    ax[2].plot([x80], [80], marker="o", color=COR["ambar"], zorder=5)
    ax[2].annotate(f"{n80} produtos ({x80:.0f}%)\n= 80% das avaliações", xy=(x80, 80),
                   xytext=(min(x80 + 15, 55), 45), arrowprops={"arrowstyle": "->", "color": COR["cinza"]},
                   color="#333333")
    _salvar(fig, pasta / "01_distribuicoes.png")


def g_categorias(fp, res, pasta: Path):
    c = res["categorias"].sort_values("total_avaliacoes")
    fig, ax = plt.subplots(1, 2, figsize=(13, max(3.5, 0.5 * len(c) + 1.5)), sharey=True)
    cores = [COR["cinza"] if p else COR["azul"] for p in c["amostra_pequena"]]
    ax[0].barh(c["categoria_nivel1"], c["total_avaliacoes"], color=cores)
    ax[0].xaxis.set_major_formatter(plt.FuncFormatter(_fmt_milhar))
    ax[0].set(title="Engajamento: total de avaliações", xlabel="Avaliações")
    for i, (tot, n) in enumerate(zip(c["total_avaliacoes"], c["n_produtos"])):
        ax[0].text(tot, i, f"  n={n}", va="center", fontsize=8, color="#444444")
    lo, hi = c["rating_ponderado"].min(), c["rating_ponderado"].max()
    ax[1].scatter(c["rating_ponderado"], c["categoria_nivel1"], s=90, color=cores, zorder=3)
    ax[1].axvline(res["kpis"]["rating_ponderado"], color=COR["ambar"], ls="--", lw=1.5, zorder=1,
                  label="média do portfólio")
    ax[1].grid(axis="x", color=COR["claro"], lw=0.8, zorder=0)
    ax[1].set_xlim(max(0, lo - 0.15), min(5, hi + 0.15))
    ax[1].set(title="Satisfação: nota ponderada pelas avaliações", xlabel="Nota ponderada (eixo não começa em zero)")
    ax[1].legend(frameon=False, fontsize=8, loc="lower right")
    for i, v in enumerate(c["rating_ponderado"]):
        ax[1].text(v, i + 0.28, f"{v:.2f}".replace(".", ","), ha="center", fontsize=8, color="#444444")
    fig.suptitle(f"Categorias (cinza = menos de {cfg.MIN_PRODUTOS_CATEGORIA} produtos; cuidado ao comparar)",
                 fontsize=10, color="#555555")
    _salvar(fig, pasta / "02_categorias.png")


def g_quadrantes(fp, res, pasta: Path):
    d = fp.dropna(subset=["rating", "rating_count"]).copy()
    rng = np.random.default_rng(1)
    d["_y"] = d["rating"] + rng.uniform(-0.02, 0.02, len(d))  # jitter só para visualização
    p = res["parametros"]
    fig, ax = plt.subplots(figsize=(10, 6))
    for nome in ["Demais", "Estrela", "Joia escondida", "Alerta"]:
        s = d[d["quadrante"] == nome]
        ax.scatter(s["rating_count"], s["_y"], s=22 if nome == "Demais" else 34, alpha=0.5 if nome == "Demais" else 0.85,
                   color=COR_QUADRANTE[nome], label=f"{nome} ({len(s)})", edgecolor="white", linewidth=0.3)
    ax.set_xscale("log")
    for xv in (p["engajamento_q_baixo"], p["engajamento_q_alto"]):
        ax.axvline(xv, color=COR["cinza"], ls=":", lw=1)
    for yv in (p["rating_q_baixo"], p["rating_q_alto"]):
        ax.axhline(yv, color=COR["cinza"], ls=":", lw=1)
    ax.set(title="Engajamento × Satisfação por produto", xlabel="Nº de avaliações (escala log)",
           ylabel="Nota (com leve ruído visual)")
    ax.legend(frameon=False, loc="lower right")
    _salvar(fig, pasta / "03_quadrantes_engajamento_satisfacao.png")


def g_desconto(fp, res, pasta: Path):
    d = fp.dropna(subset=["rating", "discount_percentage"])
    corr = res["correlacoes"].iloc[0]
    fig, ax = plt.subplots(1, 2, figsize=(14, 5))
    ax[0].scatter(d["discount_percentage"] * 100, d["rating"], s=16, alpha=0.35, color=COR["azul"])
    f = res["faixas_desconto"]
    centros = (np.array(cfg.FAIXAS_DESCONTO) + np.array(cfg.FAIXAS_DESCONTO[1:] + [1.0])) / 2 * 100
    mapa = dict(zip(cfg.ROTULOS_DESCONTO, centros))
    ax[0].plot([mapa[x] for x in f["faixa_desconto"]], f["rating_medio"], color=COR["ambar"], marker="o", lw=2.5,
               label="média por faixa")
    rho = f"{corr['spearman']:+.2f}".replace(".", ",")
    ax[0].set(title=f"Desconto × Nota (Spearman = {rho}; n = {int(corr['n'])})", xlabel="Desconto (%)", ylabel="Nota")
    ax[0].legend(frameon=False)
    x = np.arange(len(f))
    ax[1].bar(x, f["avaliacoes_mediana"], 0.6, color=COR["verde"], label="Avaliações (mediana por produto)")
    ax[1].set_ylabel("Avaliações (mediana por produto)")
    ax[1].set_ylim(0, f["avaliacoes_mediana"].max() * 1.3)
    ax[1].set_xticks(x)
    ax[1].set_xticklabels([f"{r}\n(n={n})" for r, n in zip(f["faixa_desconto"], f["n_produtos"])], fontsize=8)
    ax2 = ax[1].twinx()
    ax2.plot(x, f["rating_medio"], color=COR["azul"], marker="o", lw=2.5, label="Nota média (eixo à direita)")
    for xi, v in zip(x, f["rating_medio"]):
        ax2.text(xi, v + 0.01, f"{v:.2f}".replace(".", ","), ha="center", fontsize=8, color=COR["azul"])
    ax2.set_ylim(max(0, f["rating_medio"].min() - 0.3), min(5, f["rating_medio"].max() + 0.3))
    ax2.set_ylabel("Nota média (eixo não começa em zero)")
    ax2.spines["right"].set_visible(True)
    ax[1].set_title("Faixas de desconto: engajamento e satisfação")
    h1, l1 = ax[1].get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax[1].legend(h1 + h2, l1 + l2, frameon=False, loc="upper center", ncol=2, fontsize=8)
    _salvar(fig, pasta / "04_desconto_nota_engajamento.png")


def g_heatmap(fp, res, pasta: Path):
    h, n = res["heatmap_rating"], res["heatmap_n"]
    if h.empty:
        return
    fig, ax = plt.subplots(figsize=(9, 4.5))
    m = h.where(n >= cfg.MIN_PRODUTOS_CELULA)
    centro = res["kpis"]["rating_medio"]  # escala fixa (±0,5 em torno da média) para não exagerar diferenças pequenas
    im = ax.imshow(m.to_numpy(dtype=float), cmap="RdYlGn", aspect="auto", vmin=centro - 0.5, vmax=centro + 0.5)
    ax.set_xticks(range(len(h.columns)))
    ax.set_xticklabels(h.columns, fontsize=8)
    ax.set_yticks(range(len(h.index)))
    ax.set_yticklabels(h.index, fontsize=8)
    for i in range(h.shape[0]):
        for j in range(h.shape[1]):
            v, c = h.iloc[i, j], n.iloc[i, j]
            if c >= cfg.MIN_PRODUTOS_CELULA and not np.isnan(v):
                ax.text(j, i, f"{v:.2f}\nn={c}".replace(".", ","), ha="center", va="center", fontsize=8)
            else:
                ax.text(j, i, f"n={c}", ha="center", va="center", fontsize=7, color="#999999")
    ax.set(title=f"Nota média por faixa de preço × desconto (células com n < {cfg.MIN_PRODUTOS_CELULA} omitidas)",
           xlabel="Faixa de desconto", ylabel="Faixa de preço original")
    ax.spines[:].set_visible(False)
    fig.colorbar(im, ax=ax, label="Nota média")
    _salvar(fig, pasta / "05_heatmap_preco_desconto.png")


def g_temas(fp, res, pasta: Path):
    t = res["temas"].dropna(subset=["lift_baixa_sobre_alta"]).sort_values("lift_baixa_sobre_alta")
    if t.empty:
        return
    y = np.arange(len(t))
    fig, ax = plt.subplots(1, 2, figsize=(14, max(3.5, 0.55 * len(t) + 1.5)), sharey=True)
    ax[0].barh(y - 0.2, t["por_mil_palavras_alta"], 0.4, color=COR["verde"], label="Produtos de nota ALTA")
    ax[0].barh(y + 0.2, t["por_mil_palavras_baixa"], 0.4, color=COR["vermelho"], label="Produtos de nota BAIXA")
    ax[0].set_yticks(y)
    ax[0].set_yticklabels(t["tema"])
    ax[0].set(title="Menções por 1.000 palavras de review", xlabel="Menções / 1.000 palavras")
    ax[0].legend(frameon=False, fontsize=8)
    cores = [COR["vermelho"] if (l > 1 and e) else COR["cinza"] for l, e in zip(t["lift_baixa_sobre_alta"], t["evidencia_suficiente"])]
    ax[1].barh(y, t["lift_baixa_sobre_alta"], color=cores)
    ax[1].axvline(1, color="#333333", lw=1)
    for yi, v in zip(y, t["lift_baixa_sobre_alta"]):
        ax[1].text(v, yi, f" {v:.2f}x".replace(".", ","), va="center", fontsize=8, color="#444444")
    ax[1].set(title="Lift: o tema aparece mais na nota BAIXA? (1 = igual)", xlabel="Lift (baixa ÷ alta)")
    fig.suptitle("Temas nas reviews (análise por produto; cinza = pouca evidência ou lift ≤ 1)", fontsize=10, color="#555555")
    _salvar(fig, pasta / "06_temas_reviews.png")


def g_palavras(fp, res, pasta: Path):
    a, b = res["palavras_alta"], res["palavras_baixa"]
    if a.empty or b.empty:
        return
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    ax[0].barh(a["palavra"][::-1], a["score"][::-1], color=COR["verde"])
    ax[0].set(title="Palavras típicas de produtos de nota ALTA", xlabel="log-odds (alta vs. baixa)")
    ax[1].barh(b["palavra"][::-1], -b["score"][::-1], color=COR["vermelho"])
    ax[1].set(title="Palavras típicas de produtos de nota BAIXA", xlabel="log-odds (baixa vs. alta)")
    _salvar(fig, pasta / "07_palavras_distintivas.png")


GRAFICOS = [g_distribuicoes, g_categorias, g_quadrantes, g_desconto, g_heatmap, g_temas, g_palavras]


# ======================================================================================
# saída
# ======================================================================================
def _gravar_resultados(res: dict, out: Path) -> None:
    from openpyxl.styles import Font, PatternFill

    tabelas = {k: v for k, v in res.items() if isinstance(v, pd.DataFrame)}
    (out / "tables").mkdir(parents=True, exist_ok=True)
    for nome, tab in tabelas.items():
        tab.to_csv(out / "tables" / f"{nome}.csv", index=nome.startswith("heatmap"), encoding="utf-8-sig")
    with pd.ExcelWriter(out / "analise_resultados.xlsx", engine="openpyxl") as xw:
        for nome, tab in tabelas.items():
            sanear_para_excel(tab).to_excel(xw, sheet_name=nome[:31], index=nome.startswith("heatmap"))
            ws = xw.sheets[nome[:31]]
            ws.freeze_panes = "A2"
            for cel in ws[1]:
                cel.font = Font(name="Arial", bold=True, color="FFFFFF")
                cel.fill = PatternFill("solid", fgColor="1F3A5F")
            for col in ws.columns:
                larg = max(len(str(c.value)) if c.value is not None else 0 for c in list(col)[:100])
                ws.column_dimensions[col[0].column_letter].width = min(max(larg + 2, 10), 50)


def executar(dados: dict | None = None, processed_dir: str | Path = cfg.DATA_PROCESSED,
             out_dir: str | Path = cfg.OUTPUTS) -> dict:
    out = Path(out_dir)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    dados = _carregar(dados, Path(processed_dir))
    print("[analyze] calculando indicadores e análises")
    res = calcular(dados)
    fp = dados["Fato_Produto"].copy()
    fp["rating_count"] = pd.to_numeric(fp["rating_count"], errors="coerce").astype("float64")
    for fn in GRAFICOS:
        try:
            fn(fp, res, out / "figures")
        except Exception as exc:  # um gráfico com problema não deve derrubar o pipeline
            res["avisos"].append(f"Gráfico {fn.__name__} falhou: {exc}")
            traceback.print_exc()
    _gravar_resultados(res, out)
    print(f"[analyze] tabelas, planilha e gráficos gravados em {out}")
    return res


if __name__ == "__main__":
    executar()
