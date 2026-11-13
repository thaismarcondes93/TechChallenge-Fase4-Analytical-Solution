"""Testes de fumaça do pipeline, com dados SINTÉTICOS (nunca dados reais).

Rodar:  python -m unittest discover -s tests -v      (ou pelo Testing do VS Code)
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from techchallenge import analyze, gerar_power_query, prepare, report, sample_data


class TestPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        cls.csv = base / "amazon_sintetico.csv"
        sample_data.gerar(n_produtos=300).to_csv(cls.csv, index=False, encoding="utf-8-sig")
        cls.proc, cls.out = base / "processed", base / "outputs"
        cls.dados = prepare.executar(cls.csv, cls.proc, cls.out)
        cls.res = analyze.executar(cls.dados, cls.proc, cls.out)
        report.executar(cls.res, cls.out, arquivo_origem=cls.csv.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_um_registro_por_produto(self):
        fp = self.dados["Fato_Produto"]
        self.assertTrue(fp["product_id"].is_unique)
        self.assertEqual(len(fp), self.dados["qualidade"]["product_ids_unicos"])

    def test_tipos_e_faixas_validas(self):
        fp = self.dados["Fato_Produto"]
        self.assertTrue(fp["discount_percentage"].dropna().between(0, 1).all())
        self.assertTrue(fp["rating"].dropna().between(1, 5).all())
        self.assertTrue((fp["actual_price"].dropna() > 0).all())
        self.assertTrue((fp["desconto_valor"].dropna() >= 0).all())

    def test_valores_invalidos_viram_nulo_e_nao_zero(self):
        fp = self.dados["Fato_Produto"]
        # o "|" injetado pode estar em mais de uma linha (se a linha foi duplicada na amostra)
        self.assertGreaterEqual(self.dados["qualidade"]["rating_invalidos_texto"], 1)
        self.assertGreaterEqual(int(fp["rating"].isna().sum()), 1)
        self.assertFalse((fp["rating"] == 0).any())
        self.assertGreaterEqual(int(fp["rating_count"].isna().sum()), 1)

    def test_chaves_do_modelo_estrela(self):
        fp, ft, dt = (self.dados[k] for k in ("Fato_Produto", "Fato_ProdutoTema", "Dim_Tema"))
        self.assertTrue(set(ft["product_id"]) <= set(fp["product_id"]))
        self.assertTrue(set(ft["tema"]) == set(dt["tema"]))
        self.assertEqual(len(ft), len(fp) * len(dt))
        self.assertFalse(ft.duplicated(["product_id", "tema"]).any())

    def test_quadrantes_e_grupos(self):
        fp = self.dados["Fato_Produto"]
        self.assertTrue(set(fp["quadrante"]) <= {"Alerta", "Estrela", "Joia escondida", "Demais", "Sem dados"})
        alerta = fp[fp["quadrante"] == "Alerta"]
        self.assertTrue((alerta["grupo_nota"] == "Baixa").all())
        self.assertTrue((alerta["grupo_engajamento"] == "Alto").all())

    def test_rating_ajustado_puxa_para_a_media(self):
        fp = self.dados["Fato_Produto"].dropna(subset=["rating", "rating_count"])
        media = fp["rating"].mean()
        self.assertTrue(((fp["rating_ajustado"] - media).abs() <= (fp["rating"] - media).abs() + 1e-9).all())

    def test_arquivos_gerados(self):
        for f in [self.proc / "dados_powerbi.xlsx", self.out / "insights.md",
                  self.out / "roteiro_video_preenchido.md", self.out / "analise_resultados.xlsx",
                  self.out / "figures" / "03_quadrantes_engajamento_satisfacao.png"]:
            self.assertTrue(f.exists() and f.stat().st_size > 0, f)
        xl = pd.ExcelFile(self.proc / "dados_powerbi.xlsx")
        self.assertEqual(set(xl.sheet_names), {"Fato_Produto", "Fato_ProdutoTema", "Dim_Tema", "Parametros"})
        # números devem chegar ao Excel como números (sem texto com ₹ ou %)
        fp = xl.parse("Fato_Produto")
        self.assertTrue(pd.api.types.is_numeric_dtype(fp["actual_price"]))
        self.assertTrue(pd.api.types.is_numeric_dtype(fp["discount_percentage"]))

    def test_sem_graficos_com_falha(self):
        self.assertEqual([a for a in self.res["avisos"] if "falhou" in a], [])

    def test_correlacao_detecta_relacao_conhecida(self):
        rng = np.random.default_rng(0)
        x = pd.Series(rng.normal(size=400))
        c = analyze.correlacao(x, x * 2 + rng.normal(scale=0.5, size=400), repeticoes=200)
        self.assertGreater(c["spearman"], 0.8)
        self.assertGreater(c["ic95_baixo"], 0.7)
        indep = analyze.correlacao(x, pd.Series(rng.normal(size=400)), repeticoes=200)
        self.assertTrue(indep["ic95_baixo"] <= 0.0 <= indep["ic95_alto"])  # variáveis independentes: IC cobre zero

    def test_caractere_de_controle_nao_quebra_o_excel(self):
        # o gerador injeta "\x0b" em um product_name; sem saneamento o openpyxl levantaria IllegalCharacterError
        fp = pd.read_excel(self.proc / "dados_powerbi.xlsx", sheet_name="Fato_Produto")
        self.assertFalse(fp["product_name"].astype(str).str.contains("\x0b").any())

    def test_texto_sem_vazamento_de_virgula(self):
        # reviews com vírgulas internas não podem ser quebradas: 1 texto por produto
        t = self.dados["Texto_Produto"]
        self.assertTrue(t["product_id"].is_unique)


class TestPowerQuery(unittest.TestCase):
    def test_m_gerado_passa_na_checagem_estatica(self):
        m = gerar_power_query.gerar()
        self.assertEqual(gerar_power_query.checar_sintaxe_basica(m), [])
        self.assertEqual(m.count("// ===== CONSULTA"), 7)
        # dicionários vêm do config.py (fonte única da verdade)
        for tema in ("Durabilidade e defeitos", "Bateria e carregamento"):
            self.assertIn(tema, m)
        self.assertIn('"1. 0-19%"', m)

    def test_arquivo_versionado_esta_atualizado(self):
        from techchallenge import config as cfg
        atual = (cfg.ROOT / "powerbi" / "consultas_power_query.m").read_text(encoding="utf-8")
        self.assertEqual(atual, gerar_power_query.gerar(),
                         "Rode: python -m techchallenge.gerar_power_query (o config.py mudou)")


class TestBaseMinuscula(unittest.TestCase):
    """O pipeline não pode quebrar com poucos produtos (grupos vazios, categorias pequenas)."""

    def test_roda_com_poucos_produtos(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            csv = base / "mini.csv"
            sample_data.gerar(n_produtos=60, semente=3).to_csv(csv, index=False)
            dados = prepare.executar(csv, base / "p", base / "o")
            res = analyze.executar(dados, base / "p", base / "o")
            report.executar(res, base / "o")
            self.assertTrue((base / "o" / "insights.md").exists())


if __name__ == "__main__":
    unittest.main()
