---
nombre: analisis_estadistico
descripcion: Calcular cifras, comparaciones y tendencias correctas a partir de los datos consultados, validando los totales.
tools: [consultar_dataset, ejecutar_python, calculadora]
---

# Análisis estadístico

## Cuándo usarlo
Cuando la pregunta pide cifras: totales, conteos, promedios, comparaciones, rankings, variaciones o tendencias.

## Pasos
1. **Define la métrica antes de consultar**: qué se suma, cuenta o promedia; sobre qué filas (filtro); en qué periodo;
   agrupado por qué. Escríbela en una frase para ti.
2. **Agrega en el servidor**. Ejemplo para contratos por dependencia en 2025:
   ```
   consultar_dataset(
       dataset_id="jbjy-vk9h",
       select="nombre_entidad, count(*) AS contratos, sum(valor_del_contrato) AS total",
       where="departamento = 'Valle del Cauca' AND upper(nombre_entidad) like '%GOBERNACI%' AND fecha_de_firma between '2025-01-01T00:00:00' and '2025-12-31T23:59:59'",
       group="nombre_entidad",
       order="total DESC",
       limit=50)
   ```
3. Si necesitas cruzar, ordenar o derivar columnas, trae la tabla agregada y trabaja en `ejecutar_python`
   con `pd.read_csv('tabla_N.csv')`.
4. **Valida antes de responder**:
   - Que la consulta no llegó al límite de filas (si llegó, el total está incompleto).
   - Un total por una segunda vía: la suma de los grupos debe dar el total general sin agrupar.
   - Valores nulos, negativos o atípicos que distorsionen el promedio.
5. **Cuentas finales con `calculadora`**: diferencias, porcentajes, variaciones, conversiones de moneda.
   Variación porcentual = (nuevo − anterior) / anterior × 100.
6. **Reporta con unidades y periodo**: pesos colombianos (COP) en formato colombiano (1.234.567,89). En cifras
   grandes da también la versión corta: 483.350 millones o 483,4 mil millones (mil millones = 10^9; un billón
   colombiano = 10^12).

## Errores comunes
- Confundir número de contratos con valor de los contratos.
- Promediar promedios de grupos de distinto tamaño sin ponderar.
- Usar `fecha_de_inicio_del_contrato` cuando se pregunta por contratos firmados (`fecha_de_firma`).
- TRM: el promedio mensual con `avg(valor)` promedia periodos de vigencia, no días calendario. Dilo como
  limitación si la precisión importa.
- Redondear antes de calcular: calcula con los valores completos y redondea solo al final.
