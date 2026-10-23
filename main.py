"""Punto de entrada del pipeline ETL — Data Science II, Pre-entrega 5.

Ejecutar desde cualquier directorio: python main.py
"""

from pathlib import Path
from src.ingesta import cargar_fuentes
from src.transformaciones import limpiar_y_transformar
from src.carga import guardar_resultados

RAIZ = Path(__file__).resolve().parent


def main() -> None:
    """Ejecuta Extracción → Transformación → Carga con validaciones."""
    ventas, productos = cargar_fuentes(
        RAIZ / "datos" / "transacciones.csv", RAIZ / "datos" / "productos.xlsx"
    )
    df_final, resumen = limpiar_y_transformar(ventas, productos)
    destino = RAIZ / "salidas" / "ventas_limpias.parquet"
    guardar_resultados(df_final, resumen, destino, RAIZ / "salidas" / "reporte_calidad.json")

    print("PRE-ENTREGA 5 — ETL COMPLETADO")
    print(f"Filas del CSV: {resumen['filas_csv_original']}")
    print(f"Duplicados exactos eliminados: {resumen['duplicados_exactos_eliminados']}")
    print(f"Ventas inválidas descartadas: {sum(resumen['ventas_descartadas'].values())}")
    print(f"Ventas finales: {resumen['filas_finales']}")
    print(f"Nulos críticos finales: {resumen['nulos_criticos_finales']}")
    print(f"Total de ventas: {resumen['importe_total_ventas']:,.2f}")
    print(f"Archivo generado: {destino.relative_to(RAIZ)}")
    print("VALIDACIONES FINALES: OK")


if __name__ == "__main__":
    main()
