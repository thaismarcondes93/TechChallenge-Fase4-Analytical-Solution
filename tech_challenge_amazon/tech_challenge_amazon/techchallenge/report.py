"""Gera, a partir dos resultados de `analyze.py`, dois textos em Markdown com os números reais:

  outputs/insights.md                  rascunho de insights, riscos, oportunidades e recomendações
  outputs/roteiro_video_preenchido.md  roteiro do vídeo de 7 minutos com os números preenchidos

São RASCUNHOS em linguagem de regra: cada frase decorre de um limiar explícito sobre os números.
A equipe deve ler, discordar, ajustar e assumir a autoria antes de apresentar.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as cfg


# ------------------------------------------------------------------ formatação pt-BR
def n_(x, d: int = 0) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "n/d"
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, d: int = 0) -> str:
    return "n/d" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{n_(x * 100, d)}%"


def nome(s, n: int = 60) -> str:
    s = str(s)
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def forca(r: float) -> str:
    a = abs(r)
    return "desprezível" if a < 0.1 else "fraca" if a < 0.3 else "moderada" if a < 0.5 else "forte"


def leitura(c: pd.Series, a: str, b: str) -> str:
    """Interpreta um coeficiente de Spearman com IC95% por bootstrap."""
    rho, lo, hi = c["spearman"], c["ic95_baixo"], c["ic95_alto"]
    if np.isnan(rho):
        return f"Amostra insuficiente para medir a relação entre {a} e {b}."
    base = f"ρ = {n_(rho, 2)} (IC95% {n_(lo, 2)} a {n_(hi, 2)}; n = {int(c['n'])})"
    if lo <= 0 <= hi:
        return f"{base}: não distinguível de zero, ou seja, **sem evidência de relação** entre {a} e {b} nesta base."
    sentido = "positiva" if rho > 0 else "negativa"
    extra = " Magnitude pequena demais para orientar uma decisão sozinha." if abs(rho) < 0.2 else ""
    return f"{base}: relação **{forca(rho)} e {sentido}** entre {a} e {b}.{extra}"


def tabela_md(df: pd.DataFrame, formatos: dict | None = None) -> str:
    formatos = formatos or {}
    cab = "| " + " | ".join(df.columns) + " |\n|" + "|".join(["---"] * len(df.columns)) + "|\n"
    linhas = []
    for _, r in df.iterrows():
        cel = []
        for c in df.columns:
            v = r[c]
            cel.append(formatos[c](v) if c in formatos else str(v))
        linhas.append("| " + " | ".join(cel) + " |")
    return cab + "\n".join(linhas) + "\n"


# ------------------------------------------------------------------ blocos
def _selecao(res: dict) -> dict:
    """Extrai os achados que alimentam insights, recomendações e roteiro."""
    k, par = res["kpis"], res["pareto"]
    cat = res["categorias"]
    cat_ok = cat[~cat["amostra_pequena"]]
    corr = res["correlacoes"].set_index("relacao")
    q = res["quadrantes"].set_index("quadrante")

    def _q(nm, col, padrao=0):
        return q.loc[nm, col] if nm in q.index else padrao

    t = res["temas"]
    t_ok = t[t["evidencia_suficiente"]]
    reclamacoes = t_ok[t_ok["lift_baixa_sobre_alta"] > 1.15].head(3)
    elogios = t_ok[t_ok["lift_baixa_sobre_alta"] < 0.87].sort_values("lift_baixa_sobre_alta").head(3)
    return dict(
        k=k, par=par, cat=cat, cat_ok=cat_ok, corr=corr, q=q, t=t, reclamacoes=reclamacoes, elogios=elogios,
        n_alerta=int(_q("Alerta", "n_produtos")), n_joia=int(_q("Joia escondida", "n_produtos")),
        n_estrela=int(_q("Estrela", "n_produtos")),
        av_alerta=float(_q("Alerta", "participacao_avaliacoes", 0.0)),
        av_joia=float(_q("Joia escondida", "participacao_avaliacoes", 0.0)),
        av_estrela=float(_q("Estrela", "participacao_avaliacoes", 0.0)),
        melhor_cat=cat_ok.sort_values("rating_ponderado", ascending=False).iloc[0] if len(cat_ok) else None,
        pior_cat=cat_ok.sort_values("rating_ponderado").iloc[0] if len(cat_ok) else None,
        lider_cat=cat.iloc[0],
    )


def _secao_visao_geral(s: dict) -> str:
    k, par = s["k"], s["par"]
    concentrada = par["produtos_para_80pct"] / par["n_com_avaliacoes"] < 0.35
    amplitude = k["rating_p90"] - k["rating_p10"]
    txt = f"""## 1. Visão geral do portfólio

- **{n_(k['n_produtos'])} produtos únicos** em **{k['n_categorias']} categorias** (nível 1), somando **{n_(k['total_avaliacoes'])} avaliações**.
- **Satisfação:** nota média {n_(k['rating_medio'], 2)} (mediana {n_(k['rating_mediano'], 1)}; ponderada pelas avaliações {n_(k['rating_ponderado'], 2)}). {pct(k['pct_rating_ge_4'])} dos produtos têm nota ≥ 4,0 e {pct(k['pct_rating_lt_35'], 1)} têm nota < 3,5.
- **Preço e desconto:** desconto médio de {pct(k['desconto_medio'], 1)} (mediana {pct(k['desconto_mediano'], 1)}); preço médio original {n_(k['preco_medio_original'])} e com desconto {n_(k['preco_medio_final'])} (moeda original do dataset; confirmar), economia média {n_(k['economia_media'])} por produto.
"""
    if amplitude < 1.0:
        txt += (f"- **Notas concentradas:** 80% dos produtos estão entre {n_(k['rating_p10'], 1)} e {n_(k['rating_p90'], 1)}. "
                "Quando a nota varia pouco, cortes absolutos (como \"nota < 4\") separam pouco os produtos; "
                "por isso os grupos de nota usam quartis do próprio portfólio.\n")
    txt += f"""
### Concentração do engajamento
- Os 10 produtos mais avaliados concentram **{pct(par['top10_participacao'], 1)}** das avaliações; os 10% mais avaliados, **{pct(par['top10pct_participacao'], 1)}**.
- São necessários **{par['produtos_para_50pct']} produtos** para chegar a 50% das avaliações e **{par['produtos_para_80pct']}** para chegar a 80%.
- Leitura: {'o engajamento é **concentrado** em poucos produtos (efeito Pareto): perder ou degradar esses itens tem impacto desproporcional.' if concentrada else 'o engajamento é relativamente **distribuído**; não há dependência extrema de poucos produtos.'}
"""
    return txt


def _secao_categorias(s: dict) -> str:
    cat = s["cat"].copy()
    tab = cat[["categoria_nivel1", "n_produtos", "total_avaliacoes", "participacao_avaliacoes", "rating_ponderado",
               "desconto_medio", "amostra_pequena"]].copy()
    tab.columns = ["Categoria", "Produtos", "Avaliações", "% das avaliações", "Nota ponderada", "Desconto médio", "Amostra pequena?"]
    txt = "## 2. Categorias\n\n" + tabela_md(tab, {
        "Produtos": lambda v: n_(v), "Avaliações": lambda v: n_(v), "% das avaliações": lambda v: pct(v, 1),
        "Nota ponderada": lambda v: n_(v, 2), "Desconto médio": lambda v: pct(v, 1),
        "Amostra pequena?": lambda v: "sim" if v else "não"})
    lider = s["lider_cat"]
    txt += f"\n- **Maior engajamento:** {lider['categoria_nivel1']} ({pct(lider['participacao_avaliacoes'], 1)} das avaliações, {n_(lider['n_produtos'])} produtos).\n"
    if s["melhor_cat"] is not None:
        m, p = s["melhor_cat"], s["pior_cat"]
        dif = m["rating_ponderado"] - p["rating_ponderado"]
        txt += (f"- **Maior satisfação** (categorias com ≥ {cfg.MIN_PRODUTOS_CATEGORIA} produtos): {m['categoria_nivel1']} ({n_(m['rating_ponderado'], 2)}). "
                f"**Menor:** {p['categoria_nivel1']} ({n_(p['rating_ponderado'], 2)}).\n")
        txt += (f"- A distância entre a melhor e a pior categoria é de **{n_(dif, 2)} ponto(s) de nota**"
                f"{'. É pequena: categoria, sozinha, explica pouco da satisfação.' if dif < 0.2 else '. É relevante e merece investigação.'}\n")
    peq = s["cat"][s["cat"]["amostra_pequena"]]["categoria_nivel1"].tolist()
    if peq:
        txt += f"- **Cuidado:** {', '.join(peq)} têm menos de {cfg.MIN_PRODUTOS_CATEGORIA} produtos; suas médias são instáveis.\n"
    return txt


def _secao_preco(res: dict, s: dict) -> str:
    c = s["corr"]
    tab = res["correlacoes"][["relacao", "n", "spearman", "ic95_baixo", "ic95_alto"]].copy()
    tab.columns = ["Relação", "n", "Spearman (ρ)", "IC95% inf.", "IC95% sup."]
    txt = "## 3. Preço → Desconto → Engajamento → Satisfação\n\n"
    txt += tabela_md(tab, {"n": lambda v: n_(v), "Spearman (ρ)": lambda v: n_(v, 2),
                           "IC95% inf.": lambda v: n_(v, 2), "IC95% sup.": lambda v: n_(v, 2)})
    txt += ("\nSpearman (correlação de postos) é robusto a outliers e a relações não lineares; o IC95% vem de "
            f"bootstrap com {cfg.BOOTSTRAP_REPETICOES} repetições. **Correlação não é causalidade.**\n\n")
    txt += f"- **Desconto × Nota:** {leitura(c.loc['Desconto x Nota'], 'desconto', 'nota')}\n"
    txt += f"- **Desconto × Engajamento:** {leitura(c.loc['Desconto x Engajamento (log avaliações)'], 'desconto', 'engajamento')}\n"
    txt += f"- **Preço × Desconto:** {leitura(c.loc['Preço original x Desconto'], 'preço original', 'desconto')}\n"
    txt += f"- **Engajamento × Nota:** {leitura(c.loc['Engajamento (log avaliações) x Nota'], 'engajamento', 'nota')}\n\n"
    f = res["faixas_desconto"].copy()
    tab = f[["faixa_desconto", "n_produtos", "rating_medio", "avaliacoes_mediana", "avaliacoes_total"]]
    tab.columns = ["Faixa de desconto", "Produtos", "Nota média", "Avaliações (mediana)", "Avaliações (total)"]
    txt += tabela_md(tab, {"Produtos": n_, "Nota média": lambda v: n_(v, 2),
                           "Avaliações (mediana)": n_, "Avaliações (total)": n_})
    return txt


def _lista_produtos(df: pd.DataFrame, n: int = 10) -> str:
    if df.empty:
        return "_Nenhum produto neste grupo._\n"
    t = df.head(n)[["product_name", "categoria_nivel1", "rating", "rating_count", "discount_percentage"]].copy()
    t["product_name"] = t["product_name"].map(nome)
    t.columns = ["Produto", "Categoria", "Nota", "Avaliações", "Desconto"]
    return tabela_md(t, {"Nota": lambda v: n_(v, 1), "Avaliações": n_, "Desconto": lambda v: pct(v)})


def _secao_quadrantes(res: dict, s: dict) -> str:
    p = res["parametros"]
    q = res["quadrantes"]
    tab = q[["quadrante", "n_produtos", "participacao_produtos", "participacao_avaliacoes", "rating_medio", "desconto_medio"]].copy()
    tab.columns = ["Quadrante", "Produtos", "% dos produtos", "% das avaliações", "Nota média", "Desconto médio"]
    txt = "## 4. Engajamento × Satisfação (quadrantes)\n\n"
    txt += (f"Definições (quartis do próprio portfólio): **engajamento alto** = ≥ {n_(p['engajamento_q_alto'])} avaliações; "
            f"**baixo** = ≤ {n_(p['engajamento_q_baixo'])}. **Nota baixa** = < {n_(p['rating_q_baixo'], 2)}; **alta** = ≥ {n_(p['rating_q_alto'], 2)}.\n\n")
    txt += tabela_md(tab, {"Produtos": n_, "% dos produtos": lambda v: pct(v, 1), "% das avaliações": lambda v: pct(v, 1),
                           "Nota média": lambda v: n_(v, 2), "Desconto médio": lambda v: pct(v, 1)})
    txt += (f"\n- **Alerta (alto engajamento, nota baixa):** {s['n_alerta']} produtos, {pct(s['av_alerta'], 1)} de todas as avaliações. "
            "Muita gente os avalia e a nota é ruim: é onde a insatisfação tem mais alcance.\n")
    txt += (f"- **Joias escondidas (nota alta, pouca visibilidade):** {s['n_joia']} produtos, só {pct(s['av_joia'], 1)} das avaliações. "
            "Têm boa nota entre quem os avaliou, mas poucas pessoas os avaliam.\n")
    txt += f"- **Estrelas (alto engajamento, nota alta):** {s['n_estrela']} produtos, {pct(s['av_estrela'], 1)} das avaliações: os ativos a proteger.\n\n"
    txt += "### Top 10 em Alerta (por nº de avaliações)\n\n" + _lista_produtos(res["lista_alerta"])
    txt += "\n### Top 10 Joias escondidas (por nota)\n\n" + _lista_produtos(res["lista_joias"])
    return txt


def _secao_customer(res: dict, s: dict) -> str:
    t = res["temas"].copy()
    sent = res["sentimento"]
    txt = "## 5. Customer Insights (o que as reviews dizem)\n\n"
    txt += (f"**Método:** as reviews de cada produto vêm concatenadas, então o texto é analisado **por produto**. "
            f"Compara-se produtos de nota **alta** (≥ {n_(res['parametros']['rating_q_alto'], 2)}; n = {res['n_grupo_alta']}) com produtos de nota **baixa** "
            f"(< {n_(res['parametros']['rating_q_baixo'], 2)}; n = {res['n_grupo_baixa']}). Temas são contados por dicionário de palavras (configurável em `config.py`) "
            "e normalizados por 1.000 palavras, para não favorecer produtos com mais reviews.\n\n")
    rho = sent["spearman_com_rating"]
    if not np.isnan(rho):
        validade = ("coerente com a nota (léxico útil para comparar grupos)" if rho >= 0.3
                    else "fraca: trate o sentimento como apoio, não como evidência")
        txt += f"**Validação do sentimento:** correlação entre o saldo de sentimento do texto e a nota do produto = {n_(rho, 2)} (n = {sent['n']}), {validade}.\n\n"
    tab = t[["tema", "por_mil_palavras_alta", "por_mil_palavras_baixa", "lift_baixa_sobre_alta", "pct_produtos_alta", "pct_produtos_baixa", "evidencia_suficiente"]].copy()
    tab.columns = ["Tema", "Menções/1.000 palavras (nota alta)", "Menções/1.000 palavras (nota baixa)", "Lift (baixa ÷ alta)",
                   "% produtos que citam (alta)", "% produtos que citam (baixa)", "Evidência suficiente?"]
    txt += tabela_md(tab, {tab.columns[1]: lambda v: n_(v, 1), tab.columns[2]: lambda v: n_(v, 1),
                           "Lift (baixa ÷ alta)": lambda v: n_(v, 2), tab.columns[4]: pct, tab.columns[5]: pct,
                           "Evidência suficiente?": lambda v: "sim" if v else "não"})
    txt += "\n"
    if len(s["reclamacoes"]):
        itens = "; ".join(f"**{r['tema']}** (lift {n_(r['lift_baixa_sobre_alta'], 2)}x)" for _, r in s["reclamacoes"].iterrows())
        txt += f"- **Temas mais associados a nota baixa:** {itens}.\n"
    else:
        txt += "- Nenhum tema aparece de forma claramente mais frequente nos produtos de nota baixa (com evidência suficiente).\n"
    if len(s["elogios"]):
        itens = "; ".join(f"**{r['tema']}** (lift {n_(r['lift_baixa_sobre_alta'], 2)}x)" for _, r in s["elogios"].iterrows())
        txt += f"- **Temas mais associados a nota alta:** {itens}.\n"
    pa, pb = res["palavras_alta"], res["palavras_baixa"]
    if len(pa) and len(pb):
        txt += f"- **Palavras mais típicas de nota alta:** {', '.join(pa['palavra'].head(10))}.\n"
        txt += f"- **Palavras mais típicas de nota baixa:** {', '.join(pb['palavra'].head(10))}.\n"
    ba, bb = res["bigramas_alta"], res["bigramas_baixa"]
    if len(ba) and len(bb):
        txt += f"- **Expressões frequentes (nota alta):** {', '.join(ba['bigrama'].head(8))}.\n"
        txt += f"- **Expressões frequentes (nota baixa):** {', '.join(bb['bigrama'].head(8))}.\n"
    txt += ("\n_Limites: o léxico não entende negação (\"not good\") nem ironia; a unidade é o produto, não a review; "
            "tema mencionado não é o mesmo que tema causador da nota._\n")
    return txt


def _riscos_oportunidades(res: dict, s: dict) -> tuple[list[str], list[str]]:
    k, par = s["k"], s["par"]
    c = s["corr"]
    riscos, oport = [], []
    if s["n_alerta"]:
        riscos.append(f"**Insatisfação com alcance:** {s['n_alerta']} produtos de alto engajamento têm nota baixa e somam {pct(s['av_alerta'], 1)} das avaliações.")
    if len(s["reclamacoes"]):
        r = s["reclamacoes"].iloc[0]
        riscos.append(f"**Tema recorrente de reclamação:** {r['tema']} aparece {n_(r['lift_baixa_sobre_alta'], 2)}x mais (por 1.000 palavras) nos produtos de nota baixa.")
    if par["produtos_para_80pct"] / par["n_com_avaliacoes"] < 0.35:
        riscos.append(f"**Dependência de poucos produtos:** {par['produtos_para_80pct']} produtos geram 80% das avaliações.")
    cat_ok = s["cat_ok"]
    if len(cat_ok):
        abaixo = cat_ok[cat_ok["rating_ponderado"] <= k["rating_ponderado"] - 0.1]
        if len(abaixo):
            riscos.append(f"**Categorias abaixo da média do portfólio (≥ 0,1 ponto):** {', '.join(abaixo['categoria_nivel1'])}.")
    if s["n_joia"]:
        oport.append(f"**Visibilidade a destravar:** {s['n_joia']} produtos com nota alta e pouca visibilidade ({pct(s['av_joia'], 1)} das avaliações).")
    d_nota, d_eng = c.loc["Desconto x Nota"], c.loc["Desconto x Engajamento (log avaliações)"]
    if k["desconto_medio"] >= 0.4 and d_nota["ic95_baixo"] <= 0 <= d_nota["ic95_alto"]:
        extra = (" nem com engajamento" if d_eng["ic95_baixo"] <= 0 <= d_eng["ic95_alto"] else "")
        oport.append(f"**Desconto sem retorno aparente:** desconto médio de {pct(k['desconto_medio'], 1)} e nenhuma relação detectável com a nota{extra}; há espaço para testar descontos menores.")
    if len(s["elogios"]):
        e = s["elogios"].iloc[0]
        oport.append(f"**Tema associado a boas notas:** {e['tema']} é proporcionalmente mais citado nos produtos mais bem avaliados (candidato a argumento de venda; validar com teste).")
    peq = s["cat"][s["cat"]["amostra_pequena"]]
    if len(peq):
        oport.append(f"**Categorias pouco exploradas:** {', '.join(peq['categoria_nivel1'])} têm poucos produtos; ampliar o mix exige antes validar demanda.")
    return riscos, oport


def _recomendacoes(res: dict, s: dict) -> list[tuple[str, str, str]]:
    k = s["k"]
    c = s["corr"]
    recs = []
    if s["n_alerta"]:
        top = ", ".join(nome(x, 40) for x in res["lista_alerta"]["product_name"].head(3))
        causa = f" Investigar primeiro o tema **{s['reclamacoes'].iloc[0]['tema']}**." if len(s["reclamacoes"]) else ""
        recs.append((f"Plano de correção para os produtos em Alerta (causa raiz, fornecedor, anúncio, imagens).{causa}",
                     f"{s['n_alerta']} produtos de alto engajamento e nota baixa, {pct(s['av_alerta'], 1)} das avaliações. Maiores: {top}.",
                     "Nota dos produtos em Alerta acima do corte de nota baixa; queda da menção ao tema crítico."))
    if s["n_joia"]:
        recs.append(("Dar visibilidade às Joias escondidas (destaque em busca e vitrines, cupons, campanhas de avaliação).",
                     f"{s['n_joia']} produtos com nota ≥ {n_(res['parametros']['rating_q_alto'], 2)} e até {n_(res['parametros']['engajamento_q_baixo'])} avaliações.",
                     "Crescimento de avaliações e de vendas desses itens, mantendo a nota."))
    d_nota = c.loc["Desconto x Nota"]
    if d_nota["ic95_baixo"] <= 0 <= d_nota["ic95_alto"]:
        recs.append(("Testar (A/B) descontos menos profundos nos itens Estrela e de alto engajamento; não usar desconto como remédio para nota baixa.",
                     f"Desconto médio de {pct(k['desconto_medio'], 1)} e relação com a nota não distinguível de zero (ρ = {n_(d_nota['spearman'], 2)}).",
                     "Margem por produto sobe sem queda de engajamento."))
    else:
        recs.append(("Revisar a política de descontos considerando a relação encontrada com a nota e com o engajamento.",
                     f"Desconto × nota: ρ = {n_(d_nota['spearman'], 2)} (IC95% {n_(d_nota['ic95_baixo'], 2)} a {n_(d_nota['ic95_alto'], 2)}).",
                     "Definir faixa de desconto-alvo por categoria e acompanhar nota e engajamento."))
    if len(s["elogios"]):
        e = s["elogios"].iloc[0]["tema"]
        recs.append((f"Levar o tema **{e}** para títulos, descrições e destaques de produtos, e usar os trechos das reviews como prova social.",
                     f"{e} é mais frequente nos produtos de nota alta (lift {n_(s['elogios'].iloc[0]['lift_baixa_sobre_alta'], 2)}x).",
                     "Taxa de conversão e taxa de avaliação por produto."))
    if len(s["reclamacoes"]) > 1:
        r = s["reclamacoes"].iloc[1]["tema"]
        recs.append((f"Criar checklist de qualidade e curadoria de fornecedores focado em **{r}**.",
                     f"Lift de {n_(s['reclamacoes'].iloc[1]['lift_baixa_sobre_alta'], 2)}x nos produtos de nota baixa.",
                     "Redução de menções ao tema e de devoluções."))
    peq = s["cat"][s["cat"]["amostra_pequena"]]
    if len(peq):
        recs.append(("Antes de decidir sobre categorias pequenas, ampliar a amostra de produtos e acompanhar a nota.",
                     f"{', '.join(peq['categoria_nivel1'])}: menos de {cfg.MIN_PRODUTOS_CATEGORIA} produtos.",
                     "Número de produtos por categoria e estabilidade da nota."))
    return recs


def _secao_riscos_recs(res: dict, s: dict) -> str:
    riscos, oport = _riscos_oportunidades(res, s)
    txt = "## 6. Riscos e oportunidades\n\n### Riscos\n" + "".join(f"- {r}\n" for r in riscos)
    txt += "\n### Oportunidades\n" + "".join(f"- {o}\n" for o in oport)
    recs = _recomendacoes(res, s)
    txt += "\n## 7. Recomendações candidatas\n\nCada recomendação tem um gatilho nos dados e um KPI de sucesso.\n\n"
    txt += "| Ação | Gatilho nos dados | KPI de sucesso |\n|---|---|---|\n"
    txt += "".join(f"| {a} | {g} | {kp} |\n" for a, g, kp in recs)
    return txt


def _secao_limites(res: dict) -> str:
    q = res.get("qualidade", {})
    txt = "## 8. Limitações e qualidade dos dados\n\n"
    txt += "- **Sem coluna de data:** não há análise de tendência ou sazonalidade.\n"
    txt += "- **Avaliações são proxy de engajamento/popularidade**, não de vendas ou receita.\n"
    txt += "- **Texto analisado por produto**, não por review (reviews concatenadas com vírgulas na origem).\n"
    txt += "- **Sentimento por léxico** (sem negação/ironia) e temas por dicionário: servem para comparar grupos, não como medida absoluta.\n"
    txt += "- **Correlação não é causalidade:** os achados de preço e desconto são associações.\n"
    txt += "- **Moeda:** os preços estão na moeda original do dataset (rupias, a confirmar); nenhuma conversão foi feita.\n"
    if q:
        txt += "\n### Qualidade dos dados\n\n"
        mapa = [("linhas_brutas", "Linhas no CSV"), ("product_ids_unicos", "Produtos únicos (product_id)"),
                ("linhas_duplicadas_de_product_id", "Linhas repetidas de product_id (consolidadas)"),
                ("rating_invalidos_texto", "Ratings com texto inválido (viraram nulo)"),
                ("produtos_sem_rating", "Produtos sem rating"), ("produtos_sem_rating_count", "Produtos sem rating_count"),
                ("conflitos_numericos_entre_duplicatas", "Conflitos numéricos entre linhas duplicadas"),
                ("desconto_inconsistente_mais_de_2pp", "Descontos inconsistentes com os preços (> 2 p.p.)")]
        txt += "| Verificação | Resultado |\n|---|---|\n" + "".join(f"| {r} | {n_(q[c])} |\n" for c, r in mapa if c in q)
    for a in res.get("avisos", []):
        txt += f"\n> Aviso do pipeline: {a}\n"
    return txt


# ------------------------------------------------------------------ roteiro do vídeo
def _roteiro(res: dict, s: dict) -> str:
    k, par, c = s["k"], s["par"], s["corr"]
    d_nota, d_eng = c.loc["Desconto x Nota"], c.loc["Desconto x Engajamento (log avaliações)"]
    riscos, oport = _riscos_oportunidades(res, s)
    rec = _recomendacoes(res, s)
    melhor, pior = s["melhor_cat"], s["pior_cat"]
    cat_txt = (f"{melhor['categoria_nivel1']} tem a maior satisfação ({n_(melhor['rating_ponderado'], 2)}) e {pior['categoria_nivel1']} a menor ({n_(pior['rating_ponderado'], 2)})"
               if melhor is not None else "[preencher com a leitura de categorias]")
    if d_nota["ic95_baixo"] <= 0 <= d_nota["ic95_alto"]:
        evitar = (f"Não usar desconto como substituto de qualidade: com desconto médio de {pct(k['desconto_medio'])}, "
                  "ele não está associado a clientes mais satisfeitos.")
    else:
        evitar = "[preencher: o que a equipe recomenda não fazer, à luz da relação desconto × nota]"
    rec_txt = "\n".join(f"{i}. {a} (gatilho: {g})" for i, (a, g, _) in enumerate(rec[:3], 1))
    recl = s["reclamacoes"].iloc[0]["tema"] if len(s["reclamacoes"]) else "[tema de reclamação]"
    elog = s["elogios"].iloc[0]["tema"] if len(s["elogios"]) else "[tema de elogio]"

    def concl(d, nm):
        return (f"não encontramos relação detectável entre {nm}" if d["ic95_baixo"] <= 0 <= d["ic95_alto"]
                else f"há uma relação {forca(d['spearman'])} ({n_(d['spearman'], 2)}) entre {nm}")

    return f"""# Roteiro do vídeo executivo (7 min): rascunho preenchido com os dados

> Gerado em {date.today():%d/%m/%Y}. Os números vêm do pipeline; revisem a redação, ensaiem com cronômetro e usem os gráficos de `outputs/figures` ou o dashboard.

**0:00–0:45 · Contexto do problema** *(abertura / página Visão Executiva)*
Somos o time de Data Analytics e recebemos uma pergunta da liderança: quais produtos, categorias e estratégias comerciais merecem mais atenção, e que oportunidades os dados mostram? Analisamos {n_(k['n_produtos'])} produtos em {k['n_categorias']} categorias, seguindo a cadeia preço, desconto, engajamento e satisfação, e usamos o texto das reviews para explicar o que os números não explicam.

**0:45–1:30 · Principais indicadores** *(página Visão Executiva)*
O portfólio soma {n_(k['total_avaliacoes'])} avaliações, com nota média de {n_(k['rating_medio'], 2)} (ponderada: {n_(k['rating_ponderado'], 2)}) e desconto médio de {pct(k['desconto_medio'])}. Os 10 produtos mais avaliados concentram {pct(par['top10_participacao'])} do engajamento. A categoria líder em avaliações é {s['lider_cat']['categoria_nivel1']}.

**1:30–3:00 · Principais insights** *(páginas Produtos e Categorias, Preços e Estratégia)*
1. Engajamento × satisfação: {s['n_alerta']} produtos têm alto engajamento e nota baixa (Alerta), e respondem por {pct(s['av_alerta'], 1)} das avaliações; já {s['n_joia']} produtos têm nota alta e pouca visibilidade (Joias escondidas).
2. Preço e desconto: {concl(d_nota, 'desconto e nota')}, e {concl(d_eng, 'desconto e engajamento')}. Com desconto médio de {pct(k['desconto_medio'])}, isso sugere que descontar mais não está comprando satisfação nem, necessariamente, engajamento. Atenção: correlação não é causalidade.
3. Categorias: {cat_txt}.

**3:00–4:30 · Demonstração do dashboard** *(navegar ao vivo)*
Filtrar por categoria e mostrar tudo reagindo; clicar num ponto do quadrante Alerta e abrir a ficha do produto (drill-through); alternar faixas de desconto; usar o botão de limpar filtros.

**4:30–5:30 · Customer Insights** *(página Customer Insights)*
O tema proporcionalmente mais frequente nos produtos bem avaliados é **{elog}**; nos produtos de nota baixa, é **{recl}**. Explicar a limitação: análise por produto e dicionário de palavras, que serve para comparar grupos.

**5:30–6:30 · Recomendações** *(página Recomendações)*
{rec_txt}

**6:30–7:00 · Conclusão executiva: principais mensagens para a liderança**
1. **Onde está o risco:** {(riscos[0] if riscos else '[preencher]').replace('**', '')}
2. **Onde está a oportunidade:** {(oport[0] if oport else '[preencher]').replace('**', '')}
3. **O que evitar:** {evitar}
"""


def executar(res: dict, out_dir: str | Path = cfg.OUTPUTS, arquivo_origem: str = "amazon.csv") -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    s = _selecao(res)
    cab = (f"# Insights: Amazon Product Performance & Customer Insights\n\n"
           f"> **Rascunho gerado automaticamente** em {date.today():%d/%m/%Y} a partir de `{arquivo_origem}`. "
           "Cada frase decorre de um limiar explícito sobre os números; leiam, questionem e ajustem antes de apresentar.\n\n")
    corpo = "\n".join([_secao_visao_geral(s), _secao_categorias(s), _secao_preco(res, s), _secao_quadrantes(res, s),
                       _secao_customer(res, s), _secao_riscos_recs(res, s), _secao_limites(res)])
    (out / "insights.md").write_text(cab + corpo, encoding="utf-8")
    (out / "roteiro_video_preenchido.md").write_text(_roteiro(res, s), encoding="utf-8")
    print(f"[report] insights.md e roteiro_video_preenchido.md gravados em {out}")
