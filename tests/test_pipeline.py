"""Pruebas unitarias del pipeline (sin dependencia de pyarrow)."""
import unittest
from pathlib import Path
import pandas as pd

from src.ingesta import cargar_fuentes
from src.transformaciones import limpiar_y_transformar, normalizar_columnas, validar_dataset

ROOT = Path(__file__).resolve().parents[1]


class TestPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ventas, cls.productos = cargar_fuentes(
            ROOT / "datos" / "transacciones.csv", ROOT / "datos" / "productos.xlsx"
        )
        cls.resultado, cls.reporte = limpiar_y_transformar(cls.ventas, cls.productos)

    def test_01_entrada_y_duplicados(self):
        self.assertEqual(self.reporte["filas_csv_original"], 50)
        self.assertEqual(self.reporte["duplicados_exactos_eliminados"], 2)

    def test_02_nulos_criticos(self):
        self.assertEqual(self.reporte["nulos_criticos_finales"], 0)
        self.assertFalse(self.resultado.isna().any().any())

    def test_03_filas_finales(self):
        self.assertEqual(len(self.resultado), 45)
        self.assertEqual(sum(self.reporte["ventas_descartadas"].values()), 3)

    def test_04_fecha_es_datetime(self):
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(self.resultado["fecha"]))

    def test_05_llaves_unicas(self):
        self.assertFalse(self.resultado["id_transaccion"].duplicated().any())
        self.assertEqual(self.resultado["id_producto"].nunique(), 15)

    def test_06_importes_coherentes(self):
        self.assertTrue((
            (self.resultado["cantidad"] * self.resultado["precio_unitario"]).round(2)
            == self.resultado["total_venta"]
        ).all())
        self.assertAlmostEqual(self.resultado["total_venta"].sum(), 30889500.0)

    def test_07_columnas_normalizadas(self):
        ejemplo = pd.DataFrame({"ID Transacción": [1], "Región / Zona": ["AMBA"]})
        cols = normalizar_columnas(ejemplo).columns.tolist()
        self.assertEqual(cols, ["id_transaccion", "region_zona"])

    def test_08_un_producto_inexistente_bloquea_el_merge(self):
        alterada = self.ventas.copy()
        alterada.loc[alterada["id_transaccion"] == "T0001", "id_producto"] = "P999"
        with self.assertRaisesRegex(ValueError, "sin producto"):
            limpiar_y_transformar(alterada, self.productos)

    def test_09_id_duplicado_con_cambios_es_error(self):
        alterada = self.ventas.copy()
        nueva = alterada.iloc[[0]].copy()
        nueva["cantidad"] = 987
        alterada = pd.concat([alterada, nueva], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "duplicado con datos distintos"):
            limpiar_y_transformar(alterada, self.productos)

    def test_10_validacion_final(self):
        validar_dataset(self.resultado)

    def test_11_parquet_incluido_y_firma_correcta(self):
        parquet = ROOT / "salidas" / "ventas_limpias.parquet"
        self.assertTrue(parquet.exists())
        with parquet.open("rb") as f:
            self.assertEqual(f.read(4), b"PAR1")
            f.seek(-4, 2)
            self.assertEqual(f.read(4), b"PAR1")


if __name__ == "__main__":
    unittest.main()
