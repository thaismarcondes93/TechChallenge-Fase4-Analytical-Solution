"""Download opcional do dataset do Kaggle.

Requer `pip install kagglehub`. Para datasets públicos, o kagglehub costuma funcionar sem
configuração; se pedir autenticação, crie um token em https://www.kaggle.com/settings
(API > Create New Token) e defina as variáveis KAGGLE_USERNAME e KAGGLE_KEY, ou salve o
kaggle.json em ~/.kaggle/.

Alternativa 100% manual: abra
https://www.kaggle.com/datasets/karkavelrajaj/amazon-sales-dataset, clique em Download e
salve o arquivo como data/raw/amazon.csv.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from . import config as cfg


def baixar(destino: Path = cfg.ARQUIVO_PADRAO) -> Path:
    try:
        import kagglehub
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("kagglehub não instalado. Rode: pip install kagglehub "
                         "(ou baixe o CSV manualmente; veja o README).") from exc
    print(f"[download] baixando {cfg.KAGGLE_DATASET} ...")
    try:
        pasta = Path(kagglehub.dataset_download(cfg.KAGGLE_DATASET))
    except Exception as exc:  # rede, autenticação, dataset removido...
        raise SystemExit(
            f"Não foi possível baixar do Kaggle ({type(exc).__name__}). Baixe manualmente em "
            "https://www.kaggle.com/datasets/karkavelrajaj/amazon-sales-dataset e salve como "
            f"{destino}. Detalhe: {str(exc)[:200]}") from exc
    csvs = sorted(pasta.rglob("*.csv"))
    if not csvs:
        raise SystemExit(f"Nenhum CSV encontrado em {pasta}.")
    origem = next((c for c in csvs if c.name.lower() == "amazon.csv"), csvs[0])
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(origem, destino)
    print(f"[download] salvo em {destino}")
    return destino
