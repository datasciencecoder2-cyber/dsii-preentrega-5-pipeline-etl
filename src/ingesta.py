"""Etapa E — Extracción desde CSV y Excel con tipos definidos."""

from pathlib import Path
import pandas as pd


CAMPOS_TRANSACCIONES = {"id_transaccion", "id_producto", "cantidad", "fecha"}
CAMPOS_PRODUCTOS = {"id_producto", "nombre_producto", "precio_unitario"}


def cargar_fuentes(csv_path: Path, excel_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Carga fuentes y comprueba existencia y columnas mínimas."""
    if not csv_path.is_file():
        raise FileNotFoundError(f"No existe el CSV de transacciones: {csv_path}")
    if not excel_path.is_file():
        raise FileNotFoundError(f"No existe el Excel de productos: {excel_path}")

    # IDs siempre como texto: evita perder ceros a la izquierda.
    transacciones = pd.read_csv(
        csv_path,
        encoding="utf-8-sig",
        dtype={"id_transaccion": "string", "id_producto": "string"},
        low_memory=False,
    )
    productos = pd.read_excel(
        excel_path, sheet_name="Catalogo", engine="openpyxl",
        dtype={"id_producto": "string"},
    )
    if not CAMPOS_TRANSACCIONES.issubset(transacciones.columns):
        raise ValueError(f"Faltan columnas en transacciones: {CAMPOS_TRANSACCIONES - set(transacciones.columns)}")
    if not CAMPOS_PRODUCTOS.issubset(productos.columns):
        raise ValueError(f"Faltan columnas en productos: {CAMPOS_PRODUCTOS - set(productos.columns)}")
    return transacciones, productos
