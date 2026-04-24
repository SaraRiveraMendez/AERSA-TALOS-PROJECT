# REPORTE DE AUDITORÍA DE INVENTARIO

---

| | |
|---|---|
| **Empresa** | {{idempresa}} |
| **Sucursal** | {{idsucursal}} |
| **Almacén** | {{almacen_nombre}} |
| **Encargado de almacén** | {{almacen_encargado}} |
| **Auditor asignado** | {{idauditor}} |
| **Período auditado** | {{inventariomes_fecha}} |
| **Versión del inventario** | {{inventariomes_version}} |
| **Estatus** | {{inventariomes_estatus}} |
| **Fecha de generación** | {{inventariomes_createdat}} |
| **Última actualización** | {{inventariomes_updatedat}} |

---

## I. Resumen Ejecutivo

El presente reporte corresponde al cierre de inventario del período **{{inventariomes_fecha}}** para la sucursal **{{idsucursal}}**, almacén **{{almacen_nombre}}**. A continuación se presenta un análisis integral de los movimientos, diferencias y métricas estadísticas del período, con el propósito de apoyar la toma de decisiones del equipo auditor.

El inventario registra un valor físico total de **${{inventariomes_totalimportefisico}}**, con un balance neto de **${{inventariomes_total}}** considerando faltantes y sobrantes. El estatus actual del inventario es **{{inventariomes_estatus}}**.

---

## II. Indicadores Clave (KPIs)

| Indicador | Valor |
|---|---|
| Valor total del inventario físico | ${{inventariomes_totalimportefisico}} |
| Total alimentos | ${{inventariomes_finalalimentos}} |
| Total bebidas | ${{inventariomes_finalbebidas}} |
| Total misceláneos | ${{inventariomes_finalmiscelaneos}} |
| Total faltantes (importe) | ${{inventariomes_faltantes}} |
| Total sobrantes (importe) | ${{inventariomes_sobrantes}} |
| Balance neto (faltantes + sobrantes) | ${{inventariomes_total}} |
| Porcentaje de faltantes sobre inventario total | {{faltantes_pct}}% |
| Porcentaje de sobrantes sobre inventario total | {{sobrantes_pct}}% |
| Productos con diferencia negativa | {{count_faltantes}} productos |
| Productos con diferencia positiva | {{count_sobrantes}} productos |
| Productos sin diferencia (exactos) | {{count_exactos}} productos |
| Productos pendientes de revisión | {{count_sin_revisar}} productos |
| Tasa de revisión | {{tasa_revision}}% |

> **Nota metodológica:** El porcentaje de faltantes se calcula como `(inventariomes_faltantes / inventariomes_totalimportefisico) * 100`. El balance neto representa la diferencia absoluta entre lo teórico y lo físico en términos monetarios.

---

## III. Análisis Estadístico de Diferencias

Esta sección presenta los estadísticos descriptivos de las diferencias entre stock teórico y stock físico, expresadas tanto en unidades como en importe monetario.

### III.1 Estadísticos descriptivos — Diferencias en unidades

| Estadístico | Valor |
|---|---|
| Media de diferencias | {{diff_media}} unidades |
| Mediana de diferencias | {{diff_mediana}} unidades |
| Desviación estándar | {{diff_desviacion}} unidades |
| Valor mínimo (mayor faltante) | {{diff_min}} unidades |
| Valor máximo (mayor sobrante) | {{diff_max}} unidades |
| Rango intercuartílico (IQR) | {{diff_iqr}} unidades |

### III.2 Estadísticos descriptivos — Diferencias en importe ($)

| Estadístico | Valor |
|---|---|
| Media de diferencias en importe | ${{difimporte_media}} |
| Mediana de diferencias en importe | ${{difimporte_mediana}} |
| Desviación estándar en importe | ${{difimporte_desviacion}} |
| Valor mínimo (mayor faltante $) | ${{difimporte_min}} |
| Valor máximo (mayor sobrante $) | ${{difimporte_max}} |
| Suma total de diferencias absolutas | ${{difimporte_suma_abs}} |

### III.3 Distribución de diferencias por categoría

| Categoría | N productos | Media diferencia | Desv. estándar | Total importe diferencia |
|---|---|---|---|---|
| Alimentos | {{ali_n}} | {{ali_media_diff}} | {{ali_desv}} | ${{ali_total_diff}} |
| Bebidas | {{beb_n}} | {{beb_media_diff}} | {{beb_desv}} | ${{beb_total_diff}} |
| Misceláneos | {{misc_n}} | {{misc_media_diff}} | {{misc_desv}} | ${{misc_total_diff}} |

### III.4 Detección de valores atípicos (outliers)

Productos cuya diferencia en importe supera **2 desviaciones estándar** respecto a la media del período. Estos registros ameritan revisión prioritaria.

| Producto | Categoría | Diferencia (unidades) | Importe diferencia | Desviaciones sobre la media |
|---|---|---|---|---|
| {{producto_nombre}} | {{categoria_nombre}} | {{inventariomesdetalle_diferencia}} | ${{inventariomesdetalle_difimporte}} | {{zscore}} σ |

---

## IV. Alertas de Auditoría

Las alertas se clasifican en tres niveles de prioridad según el impacto económico y la naturaleza de la anomalía.

### IV.1 Prioridad Alta — Faltantes de alto impacto

Productos con diferencia negativa cuyo importe supera el **{{umbral_alto}}%** del valor promedio de diferencias del período.

| # | Producto | Categoría | Almacén | Stock Teórico | Stock Físico | Diferencia | Importe Diferencia | Costo Promedio |
|---|---|---|---|---|---|---|---|---|
| 1 | {{producto_nombre}} | {{categoria_nombre}} | {{almacen_nombre}} | {{inventariomesdetalle_stockteorico}} | {{inventariomesdetalle_stockfisico}} | {{inventariomesdetalle_diferencia}} | ${{inventariomesdetalle_difimporte}} | ${{inventariomesdetalle_costopromedio}} |

### IV.2 Prioridad Media — Sobrantes significativos

Productos con diferencia positiva que pueden indicar errores de captura, duplicidad de ingresos o problemas en el conteo físico.

| # | Producto | Categoría | Stock Teórico | Stock Físico | Diferencia | Importe Diferencia |
|---|---|---|---|---|---|---|
| 1 | {{producto_nombre}} | {{categoria_nombre}} | {{inventariomesdetalle_stockteorico}} | {{inventariomesdetalle_stockfisico}} | {{inventariomesdetalle_diferencia}} | ${{inventariomesdetalle_difimporte}} |

### IV.3 Prioridad Baja — Registros pendientes de revisión

Productos con `inventariomesdetalle_revisada = 0`. Su aprobación es requisito para cerrar el inventario.

| Producto | Unidad de medida | Aclaración registrada | Categoría de aclaración |
|---|---|---|---|
| {{producto_nombre}} | {{unidadmedida_nombre}} | {{inventariomesdetalle_aclaracion}} | {{inventariomesdetalle_categoriaaclaracion}} |

### IV.4 Productos dados de baja con movimientos activos

Productos con `producto_baja = 1` que registran ingresos o egresos en el período. Esto puede indicar un error de configuración o un movimiento no autorizado.

| Producto | Ingreso por compra | Egreso por venta | Reajuste |
|---|---|---|---|
| {{producto_nombre}} | ${{inventariomesdetalle_ingresocompra}} | ${{inventariomesdetalle_egresoventa}} | ${{inventariomesdetalle_reajuste}} |

---

## V. Desglose por Categoría

### V.1 Alimentos

| Producto | Unidad | Stock inicial | Stock teórico | Stock físico | Diferencia | Costo promedio | Importe físico | Importe diferencia |
|---|---|---|---|---|---|---|---|---|
| {{producto_nombre}} | {{unidadmedida_nombre}} | {{inventariomesdetalle_stockinicial}} | {{inventariomesdetalle_stockteorico}} | {{inventariomesdetalle_stockfisico}} | {{inventariomesdetalle_diferencia}} | ${{inventariomesdetalle_costopromedio}} | ${{inventariomesdetalle_importefisico}} | ${{inventariomesdetalle_difimporte}} |

**Subtotal alimentos:** ${{inventariomes_finalalimentos}}

### V.2 Bebidas

| Producto | Unidad | Rendimiento | Stock inicial | Stock teórico | Stock físico | Diferencia | Costo promedio | Importe físico | Importe diferencia |
|---|---|---|---|---|---|---|---|---|---|
| {{producto_nombre}} | {{unidadmedida_nombre}} | {{producto_rendimiento}} | {{inventariomesdetalle_stockinicial}} | {{inventariomesdetalle_stockteorico}} | {{inventariomesdetalle_stockfisico}} | {{inventariomesdetalle_diferencia}} | ${{inventariomesdetalle_costopromedio}} | ${{inventariomesdetalle_importefisico}} | ${{inventariomesdetalle_difimporte}} |

**Subtotal bebidas:** ${{inventariomes_finalbebidas}}

### V.3 Misceláneos

| Producto | Unidad | Stock inicial | Stock teórico | Stock físico | Diferencia | Importe físico | Importe diferencia |
|---|---|---|---|---|---|---|---|
| {{producto_nombre}} | {{unidadmedida_nombre}} | {{inventariomesdetalle_stockinicial}} | {{inventariomesdetalle_stockteorico}} | {{inventariomesdetalle_stockfisico}} | {{inventariomesdetalle_diferencia}} | ${{inventariomesdetalle_importefisico}} | ${{inventariomesdetalle_difimporte}} |

**Subtotal misceláneos:** ${{inventariomes_finalmiscelaneos}}

---

## VI. Análisis de Movimientos del Período

### VI.1 Consolidado de movimientos por tipo

| Tipo de movimiento | Total unidades | Total importe estimado |
|---|---|---|
| Ingresos por compra | {{total_ingresocompra_u}} | ${{total_ingresocompra_imp}} |
| Ingresos por requisición | {{total_ingresorequisicion_u}} | ${{total_ingresorequisicion_imp}} |
| Egresos por requisición | {{total_egresorequisicion_u}} | ${{total_egresorequisicion_imp}} |
| Egresos por venta | {{total_egresoventa_u}} | ${{total_egresoventa_imp}} |
| Ingresos por orden de tablajería | {{total_ingresoordentablajeria_u}} | ${{total_ingresoordentablajeria_imp}} |
| Egresos por orden de tablajería | {{total_egresoordentablajeria_u}} | ${{total_egresoordentablajeria_imp}} |
| Egresos por devolución | {{total_egresodevolucion_u}} | ${{total_egresodevolucion_imp}} |
| Reajustes aplicados | {{total_reajuste_u}} | ${{total_reajuste_imp}} |

### VI.2 Detalle de movimientos por producto

| Producto | Ingreso compra | Ingreso req. | Egreso req. | Egreso venta | Ing. tablajería | Eg. tablajería | Devolución | Reajuste |
|---|---|---|---|---|---|---|---|---|
| {{producto_nombre}} | {{inventariomesdetalle_ingresocompra}} | {{inventariomesdetalle_ingresorequisicion}} | {{inventariomesdetalle_egresorequisicion}} | {{inventariomesdetalle_egresoventa}} | {{inventariomesdetalle_ingresoordentablajeria}} | {{inventariomesdetalle_egresoordentablajeria}} | {{inventariomesdetalle_egresodevolucion}} | {{inventariomesdetalle_reajuste}} |

### VI.3 Análisis de reajustes

Los reajustes representan correcciones manuales al inventario. Un volumen alto de reajustes puede indicar problemas sistemáticos en el conteo o en el proceso de requisiciones.

| Indicador | Valor |
|---|---|
| Total de productos con reajuste | {{count_reajustes}} |
| Suma de reajustes positivos | {{reajuste_positivo_sum}} |
| Suma de reajustes negativos | {{reajuste_negativo_sum}} |
| Producto con mayor reajuste absoluto | {{producto_max_reajuste}} |
| Proporción de productos reajustados | {{pct_reajustados}}% |

---

## VII. Rankings

### VII.1 Top 10 productos con mayor faltante en importe

| Posición | Producto | Categoría | Importe diferencia | % sobre total faltantes |
|---|---|---|---|---|
| 1 | {{producto_nombre}} | {{categoria_nombre}} | ${{inventariomesdetalle_difimporte}} | {{pct_sobre_faltantes}}% |

### VII.2 Top 10 productos con mayor valor de inventario físico

| Posición | Producto | Categoría | Stock físico | Costo promedio | Importe físico |
|---|---|---|---|---|---|
| 1 | {{producto_nombre}} | {{categoria_nombre}} | {{inventariomesdetalle_stockfisico}} | ${{inventariomesdetalle_costopromedio}} | ${{inventariomesdetalle_importefisico}} |

### VII.3 Top 10 productos con mayor rotación (egresos por venta)

| Posición | Producto | Categoría | Egreso por venta | Costo promedio | Importe estimado egreso |
|---|---|---|---|---|---|
| 1 | {{producto_nombre}} | {{categoria_nombre}} | {{inventariomesdetalle_egresoventa}} | ${{inventariomesdetalle_costopromedio}} | ${{egreso_importe_estimado}} |

---

## VIII. Visualizaciones

> Las siguientes gráficas deben generarse e insertarse por el sistema al momento de compilar el reporte.

**Figura 1. Composición del inventario físico por categoría**
Gráfica de pastel: proporción de alimentos, bebidas y misceláneos sobre el total.
```
[GRÁFICA: PIE — inventariomes_finalalimentos / inventariomes_finalbebidas / inventariomes_finalmiscelaneos]
```

**Figura 2. Faltantes vs Sobrantes**
Gráfica de barras comparando el importe total de faltantes contra sobrantes.
```
[GRÁFICA: BAR — inventariomes_faltantes vs inventariomes_sobrantes]
```

**Figura 3. Distribución de diferencias en importe (histograma)**
Muestra la frecuencia de diferencias por rango de importe. Permite identificar si las diferencias se concentran en productos específicos o son generalizadas.
```
[GRÁFICA: HISTOGRAMA — inventariomesdetalle_difimporte, bins=10]
```

**Figura 4. Top 10 productos con mayor diferencia en importe**
Gráfica de barras horizontales, ordenada de mayor a menor faltante.
```
[GRÁFICA: BAR HORIZONTAL — top 10 inventariomesdetalle_difimporte DESC]
```

**Figura 5. Proporción de productos por estado de revisión**
Gráfica de dona: revisados vs pendientes.
```
[GRÁFICA: DONUT — inventariomesdetalle_revisada = 1 vs = 0]
```

**Figura 6. Mapa de calor de movimientos por tipo y categoría**
Cruce entre tipo de movimiento (compra, venta, requisición, tablajería, devolución) y categoría de producto (alimentos, bebidas, misceláneos). Útil para identificar en qué categoría se concentra la actividad.
```
[GRÁFICA: HEATMAP — tipo_movimiento × categoria_nombre, valor = importe estimado]
```

---

## IX. Validación de Catálogo TALOS

Productos en el catálogo TALOS que aún no han sido validados (`productotalos_validado = 0` o `producto_validado = 0`). Su validación es necesaria para garantizar la integridad del catálogo.

| Producto TALOS | Categoría | Subcategoría | Unidad de medida | Visible en sistema |
|---|---|---|---|---|
| {{producto_nombre}} | {{idcategoria}} | {{idsubcategoria}} | {{unidadmedida_nombre}} | {{producto_visible}} |

**Total productos pendientes de validación:** {{count_pendientes_validacion}}

---

## X. Aclaraciones y Justificaciones Registradas

| Producto | Diferencia (unidades) | Importe diferencia | Aclaración | Categoría de aclaración |
|---|---|---|---|---|
| {{producto_nombre}} | {{inventariomesdetalle_diferencia}} | ${{inventariomesdetalle_difimporte}} | {{inventariomesdetalle_aclaracion}} | {{inventariomesdetalle_categoriaaclaracion}} |

**Total de aclaraciones registradas:** {{count_aclaraciones}}
**Porcentaje de diferencias con aclaración:** {{pct_aclaradas}}%

> Un porcentaje bajo de aclaraciones frente a un alto número de diferencias puede indicar falta de seguimiento por parte del encargado de almacén.

---

## XI. Archivos del Inventario

| Documento | Ruta o referencia |
|---|---|
| Reporte Excel (versión final) | {{inventariomes_xls}} |
| Reporte PDF (versión final) | {{inventariomes_pdf}} |
| Reporte Excel (versión inicial) | {{inventariomes_xls_inicial}} |
| Reporte PDF (versión inicial) | {{inventariomes_pdf_inicial}} |

---

## XII. Conclusiones y Recomendaciones

Con base en el análisis del período **{{inventariomes_fecha}}**, se destacan los siguientes puntos:

1. **Nivel de exactitud del inventario:** {{tasa_exactitud}}% de los productos no presentaron diferencias. {{conclusion_exactitud}}
2. **Concentración de faltantes:** El {{pct_top10_faltantes}}% del importe total de faltantes se concentra en los 10 productos listados en la Sección VII.1. {{conclusion_concentracion}}
3. **Tasa de revisión:** {{tasa_revision}}% de los registros fueron marcados como revisados. {{conclusion_revision}}
4. **Volumen de reajustes:** Se aplicaron reajustes al {{pct_reajustados}}% de los productos. {{conclusion_reajustes}}
5. **Aclaraciones:** El {{pct_aclaradas}}% de las diferencias cuenta con una aclaración registrada. {{conclusion_aclaraciones}}

---

*Documento generado automáticamente por el sistema TALOS — Módulo de Generación de Reportes (API #2)*
*Periodicidad: semanal — cada fin de semana*
*Para consultas sobre este reporte, contactar al auditor asignado: {{idauditor}}*
