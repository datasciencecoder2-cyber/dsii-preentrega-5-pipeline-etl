"""Etapa L — Almacenamiento Parquet y reporte reproducible de calidad."""

from pathlib import Path
import json
import pandas as pd

from src.transformaciones import CRITICOS, validar_dataset


def guardar_resultados(df: pd.DataFrame, reporte: dict, parquet: Path, reporte_json: Path) -> None:
    """Escribe y vuelve a leer Parquet para validar el resultado persistido."""
    validar_dataset(df)
    parquet.parent.mkdir(parents=True, exist_ok=True)
    reporte_json.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_parquet(parquet, engine="pyarrow", index=False, compression="snappy")
        verificado = pd.read_parquet(parquet, engine="pyarrow")
    except ImportError as error:
        raise RuntimeError("Falta pyarrow. Instalá las dependencias con pip install -r requirements.txt") from error
    if len(verificado) != len(df) or verificado[CRITICOS].isna().any().any():
        raise ValueError("Parquet escrito no supera la validación de filas y nulos")
    if list(verificado.columns) != list(df.columns):
        raise ValueError("El Parquet no conserva el esquema previsto")

    reporte_json.write_text(json.dumps(reporte, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

