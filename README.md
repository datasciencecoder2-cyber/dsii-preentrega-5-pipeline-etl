# Data Science II — Pre-entrega 5
## Pipeline de ingesta y limpieza ETL (ventas)

Proyecto académico reproducible de **ETL modular con Pandas**, que reutiliza las fuentes ficticias de la **Pre-entrega 2** y agrega dos filas deliberadamente duplicadas al CSV para verificar el tratamiento de reingestas accidentales. No son datos reales de clientes.

## Arquitectura

```text
datos/transacciones.csv (50 filas) --\
                                   > [src/ingesta.py] → [src/transformaciones.py] → [src/carga.py]
datos/productos.xlsx (16 filas) ---/                                 ↓                    ↓
                                                         datos depurados (45)    salidas/ventas_limpias.parquet
                                                                                 salidas/reporte_calidad.json
main.py: orquesta el flujo en el orden Extracción → Transformación → Carga.
```

### E — Extracción

`src/ingesta.py` lee el CSV con `encoding="utf-8-sig"` y el catálogo Excel con `openpyxl`. Los IDs se leen como **texto** para conservar su formato, y se validan las columnas imprescindibles. El CSV incluye 48 registros originales de la práctica anterior y dos copias idénticas para ensayar la eliminación de duplicados.

### T — Transformación

`src/transformaciones.py`:

1. Normaliza nombres de columnas (minúsculas, sin tildes, `snake_case`).
2. Elimina **dos duplicados exactos** con `drop_duplicates()`. Si dos filas conservan el mismo identificador, pero con valores distintos, lanza un error en vez de borrar información sin investigar.
3. Normaliza IDs, fechas (`datetime64`), cantidades enteras y precios numéricos.
4. Trata **nulos críticos** sin inventar hechos: descarta una venta sin `id_producto`, una sin `cantidad` y otra con `fecha` inválida. Descarta un producto sin precio válido.
5. Imputa **nulos descriptivos**: `canal` y `region` → `No informado`; `categoria` → `Sin categoría`.
6. Une ventas + catálogo por `id_producto`, usando `validate="many_to_one"` para impedir multiplicación accidental de filas.
7. Calcula `total_venta = cantidad * precio_unitario`, verifica integridad y ordena de modo determinista.

### L — Carga

`src/carga.py` guarda las **45 ventas válidas** en `salidas/ventas_limpias.parquet`, vuelve a leer el archivo y valida el esquema y los nulos críticos. También genera `salidas/reporte_calidad.json` con conteos y totales.

**¿Por qué Parquet?** Es un formato **columnar** que, para volúmenes grandes, permite leer solo las variables requeridas, aprovechar compresión y conservar tipos de datos; es adecuado para pipelines analíticos y entrenamiento de modelos. En datasets muy pequeños, CSV puede resultar igual de conveniente; aquí usamos Parquet para ejercitar un estándar profesional.

## Estructura del repositorio

```text
.
├── main.py                       # Orquesta el ETL
├── src/
│   ├── __init__.py
│   ├── ingesta.py                 # Lectura de fuentes
│   ├── transformaciones.py        # Limpieza e integración
│   └── carga.py                   # Exportación y chequeos
├── datos/
│   ├── transacciones.csv          # Datos ficticios: 48 + 2 repetidas
│   └── productos.xlsx             # Catálogo ficticio: 16 filas
├── salidas/
│   ├── ventas_limpias.parquet     # Resultado final (incluido)
│   └── reporte_calidad.json       # Métricas del ETL
├── tests/
│   └── test_pipeline.py
├── evidencia/
│   └── validaciones.txt
├── requirements.txt
├── .gitignore
└── README.md
```

## Instalación y ejecución

Requisitos: **Python 3.10 o superior** y conexión a Internet para instalar dependencias por primera vez.

Desde una terminal situada en la carpeta del proyecto:

```powershell
py -m pip install -r requirements.txt
py main.py
py -m unittest discover -s tests -v
```

En macOS/Linux, reemplazar `py` por `python3`. `main.py` resuelve las rutas desde su propia ubicación, de manera que también funciona cuando se invoca desde otra carpeta.

Salida esperada:

```text
PRE-ENTREGA 5 — ETL COMPLETADO
Filas del CSV: 50
Duplicados exactos eliminados: 2
Ventas inválidas descartadas: 3
Ventas finales: 45
Nulos críticos finales: 0
Total de ventas: 30,889,500.00
Archivo generado: salidas/ventas_limpias.parquet
VALIDACIONES FINALES: OK
```

## Criterios de integridad y manejo de errores

- No se imputan importes de venta ni fechas (se evitaría fabricar operaciones inexistentes).
- Se validan cardinalidades en el cruce, IDs únicos y la fórmula de `total_venta`.
- Un producto ausente del catálogo o dos transacciones con mismo ID y datos diferentes detienen la ejecución con un mensaje explicativo.
- El reporte JSON permite auditar cuántas filas se descartan o imputan en cada etapa.
- Las pruebas se pueden ejecutar sin el motor Parquet; para **regenerar** el Parquet es obligatorio instalar `pyarrow` desde `requirements.txt`.

**Sobre el Parquet incluido:** procede del procesamiento verificado de los mismos 48 registros base en la Pre-entrega 2. Los dos duplicados añadidos en esta práctica se eliminan antes de procesar, por lo que las 45 filas finales son idénticas. El archivo puede regenerarse ejecutando `py main.py` con las dependencias instaladas. 

## Evaluación

La carpeta `evidencia` contiene la salida de pruebas ejecutadas localmente. **No se incluyen datos sensibles ni credenciales.**
