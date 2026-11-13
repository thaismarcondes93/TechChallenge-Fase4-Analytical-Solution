"""Executa o pipeline completo: (download opcional) -> preparação -> análise -> relatórios.

Exemplos:
    python run_all.py                          # usa data/raw/amazon.csv
    python run_all.py --download               # baixa do Kaggle e roda tudo
    python run_all.py --input caminho/outro.csv
    python run_all.py --sample                 # roda com DADOS SINTÉTICOS (só para testar a instalação)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from techchallenge import analyze, config as cfg, prepare, report


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):  # evita erro de acentos no terminal do Windows
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, default=cfg.ARQUIVO_PADRAO, help="CSV bruto (padrão: data/raw/amazon.csv)")
    ap.add_argument("--download", action="store_true", help="baixa o dataset do Kaggle antes de rodar")
    ap.add_argument("--sample", action="store_true",
                    help="gera e usa dados SINTÉTICOS (apenas para testar; não use os resultados como insight)")
    ap.add_argument("--out", type=Path, default=cfg.OUTPUTS, help="pasta de saída dos resultados")
    ap.add_argument("--processed", type=Path, default=cfg.DATA_PROCESSED, help="pasta das tabelas tratadas")
    a = ap.parse_args()

    entrada = a.input
    if a.sample:
        from techchallenge import sample_data
        entrada = cfg.DATA_RAW / "amazon_SINTETICO_apenas_teste.csv"
        entrada.parent.mkdir(parents=True, exist_ok=True)
        sample_data.gerar().to_csv(entrada, index=False, encoding="utf-8-sig")
        print("!!! MODO SINTÉTICO: os números NÃO são reais. Use só para testar a instalação. !!!")
    elif a.download:
        from techchallenge import download
        try:
            entrada = download.baixar(entrada)
        except SystemExit as exc:
            print(f"\nERRO: {exc}")
            return 1

    try:
        dados = prepare.executar(entrada, a.processed, a.out)
    except (FileNotFoundError, ValueError) as exc:  # erros esperados: mensagem curta, sem traceback
        print(f"\nERRO: {exc}")
        return 1
    res = analyze.executar(dados, a.processed, a.out)
    report.executar(res, a.out, arquivo_origem=entrada.name)
    print("\nPronto. Veja:")
    print(f"  {a.processed / 'dados_powerbi.xlsx'}   <- importar no Power BI")
    print(f"  {a.out / 'insights.md'}")
    print(f"  {a.out / 'roteiro_video_preenchido.md'}")
    print(f"  {a.out / 'figures'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
