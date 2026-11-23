---
nombre: explorar_datos
descripcion: Encontrar el conjunto de datos correcto en datos.gov.co y entender sus columnas y valores antes de consultarlo.
tools: [buscar_datasets, consultar_dataset]
---

# Explorar datos

## Cuándo usarlo
Siempre que la pregunta necesite datos y todavía no sepas qué conjunto usar, o no conozcas sus columnas.

## Pasos
1. **Revisa primero la tabla de conjuntos verificados** (abajo). Si el tema está ahí, usa ese id directamente.
2. Si no está, llama a `buscar_datasets` con 2 a 4 palabras clave en español. Si no hay resultados, prueba sinónimos
   ("contratación" o "secop" en vez de "compras públicas"; "calidad del aire" o "pm2.5" en vez de "contaminación").
3. Elige el conjunto: entidad oficial, actualización reciente y columnas que respondan la pregunta. Si hay una
   versión "histórico" y otra "último mes", elige según el periodo que pide el usuario.
4. **No adivines valores de categorías.** Antes de filtrar por una columna de texto, mira sus valores reales:
   `consultar_dataset(dataset_id, select="columna, count(*) AS n", group="columna", order="n DESC", limit=20)`.
5. Anota nombre, id y enlace (`https://www.datos.gov.co/d/<id>`) para citarlos en el informe.

## Conjuntos verificados (probados el 20 de noviembre de 2026)

| Tema | id | Columnas clave | Cómo consultarlo |
| --- | --- | --- | --- |
| Contratos públicos (SECOP II) | `jbjy-vk9h` | nombre_entidad, departamento, ciudad, fecha_de_firma, valor_del_contrato, tipo_de_contrato, modalidad_de_contratacion, proveedor_adjudicado, objeto_del_contrato, estado_contrato | Es enorme: filtra SIEMPRE por fecha y por entidad o departamento, y agrupa en el servidor. Los nombres de entidad no están normalizados: usa `upper(nombre_entidad) like '%GOBERNACI%' AND departamento = 'Valle del Cauca'`. |
| TRM (dólar en pesos) | `32sa-8pi3` | valor, vigenciadesde, vigenciahasta | Una fila por periodo de vigencia (un fin de semana es una sola fila). TRM de un día D: `where="vigenciadesde <= 'D' AND vigenciahasta >= 'D'"`. Promedio mensual: `select="date_trunc_ym(vigenciadesde) AS mes, avg(valor) AS trm"`, `group="mes"`, `order="mes"`. |
| Resultados Saber 11 (2010-2022) | `kgxf-xxbe` | periodo (ej. '20194'), cole_depto_ubicacion (ej. 'VALLE'), cole_mcpio_ubicacion, cole_naturaleza ('OFICIAL' / 'NO OFICIAL'), punt_global, punt_matematicas, punt_ingles | Todos los puntajes son texto: `avg(punt_global::number)`. Año: `starts_with(periodo, '2019')`. |
| Tasas de interés de crédito (histórico) | `w9zh-vetq` | fecha_corte, tipo_de_cr_dito, producto_de_cr_dito, tasa_efectiva_promedio, montos_desembolsados | Los dos últimos meses están en `qzsc-9esp`. Pondera las tasas por monto si promedias. |
| Tasas de captación (CDT) | `axk9-g2nh` | fechacorte, tasa, descripcion, nombreentidad, monto | |

## Errores comunes
- **La consulta no devolvió filas**: casi siempre es un valor mal escrito (mayúsculas, tildes). Revisa los valores
  reales con el paso 4.
- **Fechas**: las columnas "Calendar date" se comparan con texto ISO: `'2025-01-01'` o `'2025-01-01T00:00:00'`.
  Un año completo: `between '2025-01-01T00:00:00' and '2025-12-31T23:59:59'`.
- **Números guardados como texto**: conviértelos en SoQL con `::number`.
- **Columnas bloqueadas**: las de datos personales (cédulas, cuentas, supervisores) no se pueden consultar; no insistas.
