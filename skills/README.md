# Skills

Cada skill es un procedimiento escrito que le enseña a Lupa a resolver un tipo de tarea con las tools.

| Skill | Objetivo | Tools |
| --- | --- | --- |
| `explorar_datos` | Encontrar el conjunto correcto y entender sus columnas (incluye 5 conjuntos verificados) | buscar_datasets, consultar_dataset |
| `analisis_estadistico` | Calcular cifras correctas y validar totales | consultar_dataset, ejecutar_python, calculadora |
| `visualizacion` | Generar gráficas claras con título, unidades y fuente | ejecutar_python |
| `investigacion_web` | Buscar contexto, citarlo y separar hechos de opiniones | buscar_web |
| `redaccion_informe` | Estructurar la respuesta final | (solo instrucciones) |

Formato de cada `SKILL.md`: un encabezado YAML con `nombre`, `descripcion` y `tools`, seguido del procedimiento en
markdown. El agente solo ve el nombre y la descripción; carga el resto con la tool `cargar_skill` cuando lo necesita.
Para agregar un skill basta con crear una carpeta nueva con su `SKILL.md`: no hay que tocar el código.
