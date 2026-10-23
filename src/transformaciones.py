"""Etapa T — Limpieza, normalización, validación e integración."""

from __future__ import annotations

import re
import unicodedata

import pandas as pd

COLUMNAS_FINAL = [
    "id_transaccion", "fecha", "id_producto", "nombre_producto",
    "categoria", "cantidad", "precio_unitario", "total_venta",
    "canal", "region",
]
CRITICOS = [
    "id_transaccion", "fecha", "id_producto", "cantidad",
    "nombre_producto", "precio_unitario", "total_venta",
]


def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Uniforma cabeceras como snake_case y detecta colisiones."""
    copia = df.copy()
    nuevas = []
    for columna in copia.columns:
        sin_acentos = ''.join(
            caracter for caracter in unicodedata.normalize("NFKD", str(columna))
            if not unicodedata.combining(caracter)
        )
        nuevas.append(re.sub(r"[^a-zA-Z0-9]+", "_", sin_acentos).strip("_").lower())
    if len(set(nuevas)) != len(nuevas):
        raise ValueError("Dos columnas distintas se vuelven iguales tras normalizar nombres")
    copia.columns = nuevas
    return copia


def normalizar_id(serie: pd.Series) -> pd.Series:
    return serie.astype("string").str.strip().str.upper().replace("", pd.NA)


def validar_dataset(df: pd.DataFrame) -> None:
    """Detiene la carga ante datos incoherentes."""
    if df.empty:
        raise ValueError("Dataset final vacío")
    if list(df.columns) != COLUMNAS_FINAL:
        raise ValueError("El esquema final no coincide con el esperado")
    if df[CRITICOS].isna().any().any():
        raise ValueError("Hay nulos en campos críticos")
    if df["id_transaccion"].duplicated().any():
        raise ValueError("IDs de transacción repetidos en el resultado")
    if not pd.api.types.is_datetime64_any_dtype(df["fecha"]):
        raise ValueError("La fecha no se convirtió a datetime")
    if not ((df["cantidad"] * df["precio_unitario"]).round(2) == df["total_venta"]).all():
        raise ValueError("Los importes calculados no son consistentes")


def limpiar_y_transformar(
    transacciones: pd.DataFrame, productos: pd.DataFrame
) -> tuple[pd.DataFrame, dict]:
    """Deduplica, limpia nulos según su criticidad e integra fuentes (many-to-one)."""
    ventas = normalizar_columnas(transacciones)
    catalogo = normalizar_columnas(productos)
    resumen = {
        "filas_csv_original": len(ventas),
        "productos_excel_original": len(catalogo),
        "duplicados_exactos_eliminados": 0,
        "ventas_descartadas": {},
        "productos_descartados": {},
        "imputaciones": {},
    }

    # El mismo registro reimportado se elimina; si el ID coincide pero los
    # datos difieren, se detiene el proceso para investigar la inconsistencia.
    resumen["duplicados_exactos_eliminados"] = int(ventas.duplicated().sum())
    ventas = ventas.drop_duplicates().copy()

    # Catálogo de productos: no imputar IDs, nombres ni precios faltantes.
    catalogo["id_producto"] = normalizar_id(catalogo["id_producto"])
    catalogo["nombre_producto"] = catalogo["nombre_producto"].astype("string").str.strip().replace("", pd.NA)
    catalogo["precio_unitario"] = pd.to_numeric(catalogo["precio_unitario"], errors="coerce")
    producto_invalido = (
        catalogo["id_producto"].isna() | catalogo["nombre_producto"].isna()
        | catalogo["precio_unitario"].isna() | catalogo["precio_unitario"].le(0)
    )
    resumen["productos_descartados"]["sin_datos_criticos_o_precio_invalido"] = int(producto_invalido.sum())
    catalogo = catalogo.loc[~producto_invalido].copy()
    if catalogo["id_producto"].duplicated().any():
        raise ValueError("Catálogo con ID de producto duplicado")
    if "categoria" not in catalogo.columns:
        catalogo["categoria"] = pd.NA
    catalogo["categoria"] = catalogo["categoria"].astype("string").str.strip().replace("", pd.NA)
    resumen["imputaciones"]["categoria_no_informada"] = int(catalogo["categoria"].isna().sum())
    catalogo["categoria"] = catalogo["categoria"].fillna("Sin categoría")

    # Ventas: cantidades y fechas no se inventan porque son hechos del negocio.
    ventas["id_transaccion"] = ventas["id_transaccion"].astype("string").str.strip().replace("", pd.NA)
    ventas["id_producto"] = normalizar_id(ventas["id_producto"])
    ventas["cantidad"] = pd.to_numeric(ventas["cantidad"], errors="coerce")
    ventas["fecha"] = pd.to_datetime(
        ventas["fecha"].astype("string").str.strip(), format="%Y-%m-%d", errors="coerce"
    )
    for columna in ("canal", "region"):
        if columna not in ventas.columns:
            ventas[columna] = pd.NA
        ventas[columna] = ventas[columna].astype("string").str.strip().replace("", pd.NA)
        resumen["imputaciones"][f"{columna}_no_informado"] = int(ventas[columna].isna().sum())
        ventas[columna] = ventas[columna].fillna("No informado")

    reglas = [
        ("id_transaccion_o_producto_ausente", lambda d: d["id_transaccion"].isna() | d["id_producto"].isna()),
        ("cantidad_ausente_no_entera_o_no_positiva", lambda d: d["cantidad"].isna() | d["cantidad"].le(0) | d["cantidad"].mod(1).ne(0)),
        ("fecha_invalida_o_ausente", lambda d: d["fecha"].isna()),
    ]
    for motivo, regla in reglas:
        invalidas = regla(ventas)
        resumen["ventas_descartadas"][motivo] = int(invalidas.sum())
        ventas = ventas.loc[~invalidas].copy()
    ventas["cantidad"] = ventas["cantidad"].astype("int64")
    if ventas["id_transaccion"].duplicated().any():
        raise ValueError("ID de transacción duplicado con datos distintos")

    # Unión many_to_one: evita multiplicar las ventas por productos repetidos.
    integrado = ventas.merge(
        catalogo[["id_producto", "nombre_producto", "precio_unitario", "categoria"]],
        on="id_producto", how="left", validate="many_to_one", indicator=True,
    )
    faltantes = integrado.loc[integrado["_merge"] != "both", "id_producto"].unique().tolist()
    if faltantes:
        raise ValueError(f"Transacciones sin producto en catálogo: {faltantes}")
    integrado = integrado.drop(columns="_merge")
    integrado["precio_unitario"] = integrado["precio_unitario"].astype("float64")
    integrado["total_venta"] = (integrado["cantidad"] * integrado["precio_unitario"]).round(2)
    integrado = integrado[COLUMNAS_FINAL].sort_values(["fecha", "id_transaccion"]).reset_index(drop=True)
    validar_dataset(integrado)

    resumen.update({
        "productos_excel_validos": len(catalogo),
        "filas_finales": len(integrado),
        "nulos_criticos_finales": int(integrado[CRITICOS].isna().sum().sum()),
        "importe_total_ventas": round(float(integrado["total_venta"].sum()), 2),
        "fecha_es_datetime": True,
        "productos_distintos_vendidos": int(integrado["id_producto"].nunique()),
    })
    return integrado, resumen
