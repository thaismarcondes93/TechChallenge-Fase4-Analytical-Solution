"""Utilidades compartilhadas."""
from __future__ import annotations

import pandas as pd
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE


def sanear_para_excel(df: pd.DataFrame) -> pd.DataFrame:
    """Remove caracteres de controle que o Excel/openpyxl não aceitam (comuns em texto de reviews)."""
    out = df.copy()
    for c in out.columns:
        if out[c].dtype == object or pd.api.types.is_string_dtype(out[c]):
            out[c] = out[c].map(lambda v: ILLEGAL_CHARACTERS_RE.sub("", v) if isinstance(v, str) else v)
    return out
