# Lupa: documento de diseño

Proyecto final de Inteligencia Artificial · Línea 4: Agentes inteligentes con tools y skills
Equipo: Adrián Campos, David Celorio y Martín Murillo · Noviembre de 2026

## Resumen

Lupa es un agente que responde preguntas en español sobre los datos abiertos de Colombia: encuentra el conjunto de datos en datos.gov.co, lo consulta, lo analiza con código, hace gráficas, busca contexto en la web y entrega un informe con fuentes. Razona con un LLM y actúa con 6 tools. Lo que sabe sobre cómo resolver cada tipo de tarea está en 5 skills que carga solo cuando los necesita. Se evalúa con un banco de 12 tareas, comparando el agente con skills contra el mismo agente sin ellos.

## Problema y contexto

Colombia publica 8.473 conjuntos de datos en datos.gov.co (según su catálogo el 20 de noviembre de 2026), pero sacarles provecho exige saber encontrarlos, consultarlos por API y analizarlos con SQL o Python.

- Quienes más los necesitan (ciudadanos, periodistas, veedurías, concejales, estudiantes) casi nunca tienen esas habilidades.
- El buscador del portal devuelve conjuntos de datos, no respuestas: el usuario igual tiene que descargar, filtrar, cruzar y graficar.
- Las preguntas reales tienen varios pasos. "¿Cuánto contrató tal entidad, en qué y fue noticia?" mezcla datos, cálculo y contexto.

Lupa cierra esa brecha: el usuario pregunta en lenguaje natural y el agente hace el trabajo técnico, mostrando cada paso para que el resultado se pueda verificar.

## Casos de uso

| # | Pregunta de ejemplo | Datos | Qué demuestra |
| --- | --- | --- | --- |
| 1 | ¿Cuánto contrató la Gobernación del Valle por SECOP II en 2025, por dependencia, y qué noticias hubo sobre eso? | SECOP II + web | Cadena completa: buscar, consultar, agrupar, graficar, investigar e informar |
| 2 | Grafica la TRM promedio mensual de 2025 y explica qué movió el dólar ese año | TRM + web | Serie de tiempo, gráfica y contexto con fuentes |
| 3 | Si compré 1.000 dólares el 2 de enero de 2025 y los vendí el 30 de diciembre, ¿cuánto gané o perdí en pesos? | TRM | Consulta puntual y cálculo exacto con la calculadora |
| 4 | Compara el puntaje global promedio de Saber 11 entre colegios oficiales y no oficiales del Valle | Saber 11 | Limpieza de datos: los puntajes vienen como texto |
| 5 | ¿Qué datos abiertos hay sobre calidad del aire en Bogotá? | Catálogo | Exploración de conjuntos que el agente no conocía |

Conjuntos verificados el 20 de noviembre de 2026: [SECOP II – Contratos Electrónicos](https://www.datos.gov.co/d/jbjy-vk9h) (`jbjy-vk9h`), [TRM](https://www.datos.gov.co/d/32sa-8pi3) (`32sa-8pi3`), [Resultados únicos Saber 11](https://www.datos.gov.co/d/kgxf-xxbe) (`kgxf-xxbe`) y [Tasas de interés activas por tipo de crédito – Histórico](https://www.datos.gov.co/d/w9zh-vetq) (`w9zh-vetq`).

## Alcance

**Hace:** busca conjuntos en el catálogo y los consulta por la API pública (sin clave); encadena búsqueda, consulta, análisis con código, gráfica, contexto web e informe; muestra cada paso y cita los conjuntos y páginas que usó.

**No hace (versión 1):** no descarga conjuntos completos (agrega en el servidor); no muestra datos personales (SECOP II publica cédulas y cuentas bancarias, y la tool de consulta las bloquea); no da recomendaciones financieras ni opiniones políticas; no guarda memoria entre sesiones.

## Arquitectura

Lupa sigue el patrón razonar, actuar y observar (ReAct): el LLM decide el siguiente paso, el ciclo ejecuta la tool que pidió y repite hasta tener la respuesta.

```text
Usuario ──► Interfaz Gradio ◄──► Ciclo del agente ◄──► LLM (Gemini; respaldo Groq)
                                  1. Razonar: el LLM elige una tool o responde
                                  2. Actuar: se ejecuta la tool pedida ──► Tools ──► datos.gov.co, Tavily, Python local
                                  3. Observar: el resultado vuelve al historial
                                                                         cargar_skill ──► skills/*/SKILL.md
```

El ciclo termina cuando el LLM responde sin pedir tools o al llegar a 15 pasos. Cada vuelta queda en una traza que muestra la interfaz y que usa la evaluación. El LLM nunca toca los datos directamente: solo ve lo que las tools le devuelven.

## Tools

| Tool | Qué hace | Servicio |
| --- | --- | --- |
| `buscar_datasets` | Busca conjuntos por palabras clave o id y devuelve id, nombre, entidad, fecha y columnas con tipo y descripción | Catálogo de datos.gov.co (`/api/catalog/v1`) |
| `consultar_dataset` | Ejecuta una consulta SoQL (select, where, group, order, limit), guarda la tabla como CSV y devuelve una muestra | API SODA (`/resource/<id>.json`) |
| `ejecutar_python` | Corre pandas y matplotlib sobre las tablas, en un proceso aparte con 60 s de límite | Local |
| `buscar_web` | Busca contexto o noticias y devuelve título, URL y extracto | Tavily |
| `calculadora` | Evalúa expresiones aritméticas exactas recorriendo el árbol sintáctico, sin `eval` | Local |
| `cargar_skill` | Devuelve el procedimiento completo de un skill | Carpeta `skills/` |

Lo que aprendimos probando la API, y que las tools y los skills manejan:

- La API agrega en el servidor (`sum`, `avg`, `count`, `date_trunc_ym`), así que no hay que traer las filas para sumar.
- Los filtros con `%` (como `like '%GOBERNACI%'`) fallan si no se codifican en la URL; `requests` lo hace si se pasan como parámetros.
- Los nombres no están normalizados: en SECOP II aparecen "GOBERNACION DEL VALLE" y "GOBERNACIÓN VALLE DEL CAUCA".
- Saber 11 guarda todos los puntajes como texto; se convierten con `::number`.
- SECOP II incluye cédulas y cuentas bancarias; `consultar_dataset` bloquea esas columnas en la consulta y en el resultado.

## Skills

| Skill | Objetivo | Tools que usa | Se activa cuando… |
| --- | --- | --- | --- |
| `explorar_datos` | Encontrar el conjunto correcto y entender sus columnas; trae 5 conjuntos verificados | `buscar_datasets`, `consultar_dataset` | la pregunta no dice qué conjunto usar |
| `analisis_estadistico` | Filtrar, limpiar, agregar y validar totales | `consultar_dataset`, `ejecutar_python`, `calculadora` | se piden cifras, comparaciones o tendencias |
| `visualizacion` | Elegir el tipo de gráfica y generarla con título, ejes, unidades y fuente | `ejecutar_python` | se pide una gráfica o hay una serie de tiempo o comparación |
| `investigacion_web` | Buscar contexto, citarlo y separar hechos de opiniones | `buscar_web` | se piden causas, explicaciones o noticias |
| `redaccion_informe` | Entregar hallazgo principal, cifras, gráfica, fuentes y limitaciones | ninguna | al cerrar cualquier tarea de varios pasos |

Carga progresiva:

1. El prompt del sistema solo trae el nombre y una línea de descripción de cada skill.
2. Cuando el agente decide que necesita uno, llama a `cargar_skill(nombre)`.
3. Esa tool devuelve las instrucciones completas (pasos, errores comunes, ejemplos) y el agente las sigue.

Cada skill vive en `skills/<nombre>/SKILL.md`: un encabezado YAML con nombre, descripción y tools, y el procedimiento en markdown. Así el contexto se mantiene corto, los skills se editan sin tocar el código y comparar el agente con y sin skills es tan simple como quitar `cargar_skill`.

## Evaluación

Como el agente no se entrena, su solidez técnica se demuestra midiendo: 12 tareas con respuesta verificada, corridas con y sin skills.

**Banco de tareas** (`eval/tareas.json`): 4 simples (un dato, una tool), 4 de varios pasos (consulta más cálculo o gráfica) y 4 complejas (varios skills, con web). La respuesta esperada de cada una se calcula en el momento con una consulta directa a la API, así no queda desactualizada.

| Métrica | Cómo se mide |
| --- | --- |
| Tasa de éxito | Tareas cuyas verificaciones pasan todas; las cifras con 1 % de tolerancia como máximo |
| Uso correcto de tools | Llamadas a una tool esperada (o a `cargar_skill`) sobre el total de llamadas |
| Pasos por tarea | Vueltas del ciclo del agente |
| Errores recuperados | Errores de una tool seguidos de un uso exitoso de la misma tool |
| Tiempo y tokens | Por tarea, leídos de la traza |

Configuraciones: A, agente sin skills (mismas tools, mismo modelo); B, agente con skills. Los resultados quedan en `eval/resultados/<fecha>/`.

## Stack

| Componente | Elección | Por qué |
| --- | --- | --- |
| Lenguaje | Python 3.10 o superior | Corre igual en Colab y en local |
| LLM principal | Gemini Flash vía `google-genai` | Capa gratuita y function calling nativo; el modelo se cambia en `.env` |
| LLM de respaldo | Groq vía la librería `openai` | Plan gratuito; sirve para cualquier API compatible con OpenAI |
| Búsqueda web | Tavily | 1.000 créditos gratis al mes |
| Datos | API SODA de datos.gov.co | Pública, sin clave |
| Análisis y gráficas | pandas y matplotlib | Estándar |
| Interfaz | Gradio | Muestra la traza del agente y corre dentro de Colab |
| Pruebas | pytest | 89 pruebas sin red ni cuota de API |

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| El LLM gratuito responde con error 429 o el modelo está saturado (503) | Cambio automático a modelos de Gemini de respaldo; reintentos con espera creciente; proveedor de respaldo (Groq) con una variable |
| La API de datos.gov.co está lenta o caída | Caché local de 24 horas, consultas filtradas, tiempo límite y video de respaldo |
| El código que genera el LLM falla o hace algo indebido | Proceso aparte con tiempo límite y carpeta propia; operaciones peligrosas rechazadas; el error vuelve al agente |
| El agente inventa cifras | Toda cifra sale de una tool; el informe cita conjunto y consulta; la evaluación mide exactitud |
| Datos sucios | Reglas escritas en los skills y conversión en pandas |
| Exposición de datos personales | Columnas bloqueadas en `consultar_dataset` |
| El ciclo no termina | Máximo de 15 pasos por pregunta |

## Equipo

| Persona | Responsable de | Apoya en |
| --- | --- | --- |
| Martín Murillo | Ciclo del agente, capa de LLM e integración | Skills |
| Adrián Campos | Tools y conexión con las APIs | Banco de evaluación |
| David Celorio | Interfaz, evaluación y pitch | Skills |
