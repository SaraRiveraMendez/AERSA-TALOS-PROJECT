# Limpieza de Base de Datos — AERSA TALOS
**Base de datos:** `talos_tecmty`  
**Archivo de vistas:** `/sql/view_clean_tables.sql`

---

## Contexto

TALOS es una plataforma SaaS de gestión de inventarios, compras y ventas para grupos restauranteros. Cada empresa cliente tiene su propio catálogo de productos, sucursales y almacenes dentro del sistema. La base `talos_tecmty` contiene datos reales de dos empresas con las que se está desarrollando el copiloto.

Este documento forma parte del proceso de construcción del copiloto. Antes de poder usar los datos para cualquier análisis (diferencias de inventario, costo potencial, variación de compras) fue necesario entender qué columnas y registros eran confiables y cuáles no. Aquí se documenta la lógica detrás de cada decisión de limpieza, los queries de diagnóstico que se corrieron, y cómo usar las vistas resultantes.

---

## Tablas disponibles en `talos_tecmty`

| Tabla | Descripción |
|---|---|
| `almacen` | Catálogo de almacenes por sucursal |
| `categoria` | Catálogo jerárquico de categorías de productos |
| `inventariomes` | Cabecera de cada inventario (fecha, almacén, totales) |
| `inventariomesdetalle` | Detalle producto a producto de cada inventario |
| `producto` | Catálogo propio de productos por empresa |
| `productotalos` | Catálogo homologado de productos entre empresas |
| `unidadmedida` | Catálogo de unidades de medida |

> **Nota:** Las tablas `requisicion` y `requisiciondetalle` (compras/traspasos) pertenecen a una base de datos histórica separada, no incluida en `talos_tecmty`.

---

## Diagnóstico — queries corridos y sus hallazgos

### 1. Nulos en `almacen`

```sql
SELECT
    COUNT(*) AS total_filas,
    SUM(CASE WHEN almacen_encargado IS NULL THEN 1 ELSE 0 END) AS nulos_encargado,
    SUM(CASE WHEN almacen_fechacreacion IS NULL THEN 1 ELSE 0 END) AS nulos_fechacreacion,
    SUM(CASE WHEN almacen_estatus IS NULL THEN 1 ELSE 0 END) AS nulos_estatus
FROM almacen;
```

**Resultado:**
```
total_filas | nulos_encargado | nulos_fechacreacion | nulos_estatus
18387       | 0               | 18387               | 0
```

**Hallazgo:** `almacen_fechacreacion` es 100% nula (columna sin uso real). `almacen_encargado` no tiene nulos pero el diccionario la marca como "sin uso actual".

---

### 2. Nulos en `producto`

```sql
SELECT
    COUNT(*) AS total_filas,
    SUM(CASE WHEN producto_descripcion IS NULL THEN 1 ELSE 0 END) AS nulos_descripcion,
    SUM(CASE WHEN producto_comentarioreceta IS NULL THEN 1 ELSE 0 END) AS nulos_comentarioreceta,
    SUM(CASE WHEN image_path IS NULL THEN 1 ELSE 0 END) AS nulos_image_path,
    SUM(CASE WHEN created_at IS NULL THEN 1 ELSE 0 END) AS nulos_created_at,
    SUM(CASE WHEN idimpuesto IS NULL THEN 1 ELSE 0 END) AS nulos_impuesto,
    SUM(CASE WHEN producto_baja = 1 THEN 1 ELSE 0 END) AS productos_dados_de_baja,
    SUM(CASE WHEN producto_oculto = 1 THEN 1 ELSE 0 END) AS productos_ocultos
FROM producto;
```

**Resultado:**
```
total_filas | nulos_descripcion | nulos_comentarioreceta | nulos_image_path | nulos_created_at | nulos_impuesto | productos_dados_de_baja | productos_ocultos
302325      | 302325            | 292260                 | 301743           | 273816           | 302312         | 19264                   | 6037
```

**Hallazgos:**
- `producto_descripcion`: 100% nula → eliminar
- `image_path`: 99.8% nula → eliminar
- `created_at`: 90% nula → eliminar
- `idimpuesto`: ~100% nula + el proveedor confirmó que está "en maduración" → eliminar
- `producto_comentarioreceta`: 96.7% nula → eliminar
- 19,264 productos dados de baja y 6,037 ocultos → filtrar del análisis

> **Nota importante:** El diccionario decía que la columna se llamaba `producto_comentario`, pero en la base real se llama `producto_comentarioreceta`. Asi que es mejor verificar con `SHOW COLUMNS` antes de escribir queries.

---

### 3. Nulos en `inventariomesdetalle`

```sql
SELECT
    COUNT(*) AS total_filas,
    SUM(CASE WHEN inventariomesdetalle_stockteorico IS NULL THEN 1 ELSE 0 END) AS nulos_stockteorico,
    SUM(CASE WHEN inventariomesdetalle_stockfisico IS NULL THEN 1 ELSE 0 END) AS nulos_stockfisico,
    SUM(CASE WHEN inventariomesdetalle_diferencia IS NULL THEN 1 ELSE 0 END) AS nulos_diferencia,
    SUM(CASE WHEN inventariomesdetalle_reajuste IS NULL THEN 1 ELSE 0 END) AS nulos_reajuste
FROM inventariomesdetalle;
```

**Resultado:**
```
total_filas | nulos_stockteorico | nulos_stockfisico | nulos_diferencia | nulos_reajuste
11772750    | 0                  | 151               | 19               | 0
```

**Hallazgo:** Los nulos son mínimos (151 y 19 sobre 11M de registros). Se manejan con `IFNULL(..., 0)` en las vistas en lugar de filtrarlos.

---

### 4. Distribución de estatus en `inventariomes`

```sql
SELECT inventariomes_estatus, COUNT(*) AS cantidad
FROM inventariomes
GROUP BY inventariomes_estatus;
```

**Resultado:**
```
inventariomes_estatus | cantidad
finalizado            | 73813
editando              | 363
aplicado              | 4976
terminado             | 293
```

**Hallazgo:** Los 363 inventarios en `editando` van de 2021 a 2026. Es decir, son registros abandonados a medias en distintos años, no inventarios activos, así que se excluyen del análisis.

---

### 5. Almacenes activos vs inactivos

```sql
SELECT almacen_estatus, COUNT(*) AS cantidad
FROM almacen
GROUP BY almacen_estatus;
```

**Resultado:**
```
almacen_estatus | cantidad
0               | 2835
1               | 15552
```

**Hallazgo:** 2,835 almacenes inactivos. Se excluyen explícitamente en `vw_inventariomes_limpio` mediante un JOIN con `almacen` filtrando `almacen_estatus = 1`.

---

### 6. Valores extremos en stock teórico

```sql
SELECT
    COUNT(*) AS total,
    MIN(inventariomesdetalle_stockteorico) AS min_teorico,
    MAX(inventariomesdetalle_stockteorico) AS max_teorico,
    AVG(inventariomesdetalle_stockteorico) AS avg_teorico,
    SUM(CASE WHEN inventariomesdetalle_stockteorico > 10000 THEN 1 ELSE 0 END) AS casos_extremos
FROM inventariomesdetalle;
```

**Resultado:**
```
total     | min_teorico    | max_teorico      | avg_teorico  | casos_extremos
11772750  | -937487.280576 | 999999999.999999 | 218.48       | 3521
```

---

### 7. Distribución detallada de valores extremos

```sql
SELECT
    SUM(CASE WHEN inventariomesdetalle_stockteorico < -1000 THEN 1 ELSE 0 END) AS negativos_extremos,
    SUM(CASE WHEN inventariomesdetalle_stockteorico < 0 THEN 1 ELSE 0 END) AS todos_negativos,
    SUM(CASE WHEN inventariomesdetalle_stockteorico = 0 THEN 1 ELSE 0 END) AS en_cero,
    SUM(CASE WHEN inventariomesdetalle_stockteorico > 10000 THEN 1 ELSE 0 END) AS mayores_10k,
    SUM(CASE WHEN inventariomesdetalle_stockteorico > 100000 THEN 1 ELSE 0 END) AS mayores_100k
FROM inventariomesdetalle;
```

**Resultado:**
```
negativos_extremos | todos_negativos | en_cero | mayores_10k | mayores_100k
7791               | 1535714         | 3360775 | 3521        | 53
```

**Hallazgo:** 28% de registros en cero (normal: productos sin movimientos), 13% negativos (posibles errores acumulados), 3,521 con valores mayores a 10,000 (datos corruptos), 53 con valores mayores a 100,000 (errores graves).

---

### 8. Top 10 valores más extremos (positivos)

```sql
SELECT
    idinventariomes,
    idproducto,
    inventariomesdetalle_stockteorico,
    inventariomesdetalle_stockfisico,
    inventariomesdetalle_diferencia
FROM inventariomesdetalle
ORDER BY inventariomesdetalle_stockteorico DESC
LIMIT 10;
```

**Resultado:**
```
idinventariomes | idproducto | stockteorico      | stockfisico | diferencia
113386          | 215125     | 999999999.999999  | 1.000       | -999999998.999999
62056           | 171369     | 999999986.999999  | 0.000       | -999999986.999999
118322          | 288406     | 116999903.000000  | 72.000      | -116999831.000000
111777          | 104460     | 11999992.000000   | 0.000       | -11999992.000000
108499          | 104460     | 11899998.000000   | 0.000       | -11899998.000000
...
```

**Hallazgo crítico:** `idproducto = 104460` aparece 11 veces con stocks de millones, lo que parece ser un error sistémico acumulado en lugar de un error puntual.

---

### 9. Top 10 valores más extremos (negativos)

```sql
SELECT
    idinventariomes,
    idproducto,
    inventariomesdetalle_stockteorico,
    inventariomesdetalle_stockfisico,
    inventariomesdetalle_diferencia
FROM inventariomesdetalle
ORDER BY inventariomesdetalle_stockteorico ASC
LIMIT 10;
```

**Resultado:**
```
idinventariomes | idproducto | stockteorico    | stockfisico | diferencia
85174           | 238235     | -937487.280576  | 5.000       | 937492.280576
55143           | 157866     | -640314.003455  | 8.300       | 640322.303455
15321           | 82865      | -251609.187500  | 0.000       | 251618.515625
...
```

---

### 10. Productos con stock corrupto

```sql
SELECT
    idproducto,
    COUNT(*) AS veces,
    MAX(inventariomesdetalle_stockteorico) AS stock_max,
    GROUP_CONCAT(DISTINCT idinventariomes ORDER BY idinventariomes) AS inventarios_afectados
FROM inventariomesdetalle
WHERE inventariomesdetalle_stockteorico > 100000
GROUP BY idproducto
ORDER BY veces DESC, stock_max DESC;
```

**Resultado (29 productos):**
```
idproducto | veces | stock_max         | inventarios_afectados
215125     | 1     | 999999999.999999  | 113386
171369     | 1     | 999999986.999999  | 62056
288406     | 1     | 116999903.000000  | 118322
104460     | 11    | 11999992.000000   | 99990,104056,104129,105351,...
110565     | 8     | 260280.000000     | ...
...
```

**Hallazgo:** 29 productos con stock mayor a 100,000 unidades, lo cual parece estar fuera de rango para cualquier restaurante. `idproducto = 104460` es el más preocupante ya que aparece en 11 inventarios distintos con stocks de millones, lo que indica un error acumulado en su historial de movimientos, no un error puntual. Estos registros quedan marcados con `flag_outlier = 1` en la vista.

---

### 11. Impacto de los filtros de limpieza

```sql
-- Solo excluir extremos (±10,000)
SELECT COUNT(*) AS registros_limpios
FROM inventariomesdetalle
WHERE inventariomesdetalle_stockteorico BETWEEN -10000 AND 10000;
-- Resultado: 11,769,021

-- Excluir extremos + inventarios en "editando"
SELECT COUNT(*) AS registros_limpios
FROM inventariomesdetalle imd
JOIN inventariomes im ON imd.idinventariomes = im.idinventariomes
WHERE im.inventariomes_estatus IN ('finalizado', 'aplicado', 'terminado')
AND imd.inventariomesdetalle_stockteorico BETWEEN -10000 AND 10000;
-- Resultado: 11,455,135
```

**Conclusión:** Se pierde solo el 2.7% de los datos al aplicar todos los filtros.

---

## Decisiones de diseño

### Por qué vistas y no tablas nuevas
Las vistas leen siempre los datos más recientes de las tablas originales. Si se actualiza la base, las vistas se actualizan automáticamente.

### Por qué marcar outliers con flags en lugar de filtrarlos
Los registros con `flag_outlier = 1` son datos corruptos, pero podrían ser útiles para auditorías o investigaciones internas. Al marcarlos en lugar de eliminarlos, quien consuma las vistas decide en cada query si los incluye o no, sin perder información para siempre.

### Por qué `IFNULL(..., 0)` en lugar de filtrar nulos
Los 151 nulos en `stockfisico` y 19 en `diferencia` son una fracción insignificante de 11M de registros. Reemplazarlos con 0 es más seguro que eliminar filas que podrían tener otros campos válidos.

### Por qué excluir `editando`
Los 363 inventarios en `editando` van desde 2021. Eesto indica que son registros que quedaron incompletos y nunca se finalizaron. Incluirlos puede contaminar los análisis de diferencias de inventario con datos a medias.

---

## Lógica del stock teórico

El stock teórico se calcula internamente solo para calcular el `flag_stockteorico_no_cuadra` en `vw_inventariomesdetalle_limpio`, no se expone como columna:

```
stock_teorico =
    stock_inicial
  + ingreso_compra
  + ingreso_requisicion
  + ingreso_orden_tablajeria
  - egreso_venta
  - egreso_requisicion
  - egreso_orden_tablajeria
  - egreso_devolucion
  + reajuste
```

Si `flag_stockteorico_no_cuadra = 1`, significa que el valor guardado en la BD no coincide con lo que dan los movimientos — señal de algún error en el registro de movimientos.

---

## Vistas creadas

### `vw_producto_limpio`
Catálogo de productos activos y visibles. Excluye dados de baja (`producto_baja = 1`) y ocultos (`producto_oculto = 1`). Elimina columnas 100% nulas o sin uso.

**Uso:**
```sql
SELECT * FROM vw_producto_limpio WHERE idempresa = 915;
```

---

### `vw_inventariomes_limpio`
Cabeceras de inventario en estatus válido. Excluye inventarios en `editando` (abandonados) y almacenes inactivos (`almacen_estatus = 0`).

**Uso:**
```sql
SELECT * FROM vw_inventariomes_limpio
WHERE idsucursal = 1509
  AND inventariomes_fecha BETWEEN '2025-01-01' AND '2025-12-31';
```

---

### `vw_inventariomesdetalle_limpio`
Detalle de inventario con:
- Valores nulos reemplazados por 0
- Flags para detectar registros sospechosos

**Flags disponibles:**

| Flag | Valor 1 significa |
|---|---|
| `flag_stockteorico_no_cuadra` | El stock teórico en BD no coincide con los movimientos |
| `flag_outlier` | Stock, diferencia o reajuste mayor a ±10,000 |
| `flag_costopromedio_cero` | No hay costo promedio, por lo que no se puede calcular importe |
| `flag_fisico_cero_teorico_positivo` | El sistema tiene stock pero no se contó físicamente |

**Uso típico (análisis limpio):**
```sql
SELECT * FROM vw_inventariomesdetalle_limpio
WHERE flag_outlier = 0
  AND flag_costopromedio_cero = 0;
```

**Uso para auditoría (ver registros sospechosos):**
```sql
SELECT * FROM vw_inventariomesdetalle_limpio
WHERE flag_stockteorico_no_cuadra = 1;
```

---

### `vw_categoria_limpia`
Catálogo de categorías y subcategorías. No requería filtros porque estaba limpia de origen.

**Uso:**
```sql
SELECT * FROM vw_categoria_limpia WHERE categoria_almacenable = 1;
```

---

## Cómo combinar las vistas para análisis

### Diferencias de inventario por sucursal y producto
```sql
SELECT
    im.idsucursal,
    im.inventariomes_fecha,
    p.producto_nombre,
    c.categoria_nombre,
    imd.stockteorico_bd,
    imd.stockfisico,
    imd.diferencia_bd,
    imd.costopromedio,
    imd.difimporte_bd
FROM vw_inventariomesdetalle_limpio imd
JOIN vw_inventariomes_limpio im ON im.idinventariomes = imd.idinventariomes
JOIN vw_producto_limpio p ON p.idproducto = imd.idproducto
LEFT JOIN vw_categoria_limpia c ON c.idcategoria = p.idcategoria
WHERE im.idsucursal = 1509
  AND imd.flag_outlier = 0
  AND imd.flag_costopromedio_cero = 0
ORDER BY ABS(imd.difimporte_bd) DESC;
```

### Productos físicos en cero pero con stock teórico positivo
```sql
SELECT
    im.idsucursal,
    im.inventariomes_fecha,
    p.producto_nombre,
    imd.stockteorico_bd,
    imd.stockfisico
FROM vw_inventariomesdetalle_limpio imd
JOIN vw_inventariomes_limpio im ON im.idinventariomes = imd.idinventariomes
JOIN vw_producto_limpio p ON p.idproducto = imd.idproducto
WHERE imd.flag_fisico_cero_teorico_positivo = 1
  AND imd.flag_outlier = 0;
```

### Validar si el stock teórico cuadra con los movimientos
```sql
SELECT
    imd.idinventariomes,
    p.producto_nombre,
    imd.stockteorico_bd,
    imd.stockteorico_recalculado,
    ROUND(imd.stockteorico_bd - imd.stockteorico_recalculado, 4) AS diferencia_calculo
FROM vw_inventariomesdetalle_limpio imd
JOIN vw_producto_limpio p ON p.idproducto = imd.idproducto
WHERE imd.flag_stockteorico_no_cuadra = 1
LIMIT 100;
```
---

## Cómo correr las vistas

Las vistas están definidas en `/sql/view_clean_tables.sql`. Para crearlas o actualizarlas corre desde la terminal:

```bash
mysql -u USER -p DATABASE < PATH_DEL_ARCHIVO_CON_LAS_VISTAS
```

Ejemplo:
```bash
mysql -u root -p talos_tecmty < /sql/view_clean_tables.sql
```

Te pedirá la contraseña de MySQL. Todas las vistas usan `CREATE OR REPLACE` por lo que se pueden volver a correr sin problema si se hacen cambios.