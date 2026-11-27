# Lupa: agente analista de datos abiertos de Colombia

Proyecto final de Inteligencia Artificial · Línea 4: Agentes inteligentes con tools y skills
Equipo: Adrián Campos, David Celorio y Martín Murillo

Lupa responde preguntas en español sobre los datos de [datos.gov.co](https://www.datos.gov.co): encuentra el conjunto de datos, lo consulta, lo analiza con código, hace gráficas, busca contexto en la web y entrega un informe con fuentes. Razona con un LLM y actúa a través de 6 tools; lo que sabe sobre cómo resolver cada tipo de tarea está en 5 skills que carga solo cuando los necesita.

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Scarlxdr-X/lupa-agente/blob/main/notebooks/02_demo_lupa.ipynb) · Documento de diseño: [docs/diseno.md](docs/diseno.md)

> **Ejemplo:** "¿Cuánto contrató la Gobernación del Valle del Cauca por SECOP II en 2025, por dependencia? Muestra una gráfica y busca si hubo noticias."
> Lupa carga el skill de exploración, consulta SECOP II agrupando en el servidor, grafica las 5 dependencias con mayor valor, busca noticias y responde con cifras, gráfica, enlaces y limitaciones.

## Inicio rápido

### En Google Colab (recomendado para la demo)

1. Abre `notebooks/02_demo_lupa.ipynb` en Colab.
2. En **Secretos** (icono de llave) crea `GEMINI_API_KEY` y `TAVILY_API_KEY` con acceso para el notebook.
3. Ejecuta las celdas en orden; la primera clona este repositorio.

### En local

```bash
git clone https://github.com/Scarlxdr-X/lupa-agente.git
cd lupa-agente
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env  → y pega tus claves
```

| Comando | Qué hace |
| --- | --- |
| `lupa-verificar --listar-modelos` | Comprueba las claves y que el LLM sabe pedir una tool |
| `lupa-preguntar "¿Cuál fue la TRM promedio de octubre de 2025?"` | Pregunta desde la terminal y muestra cada paso |
| `lupa-app` | Abre la interfaz web en http://127.0.0.1:7860 (`--share` para un enlace público) |
| `lupa-evaluar` | Corre el banco de 12 tareas con y sin skills y genera métricas y gráfica |
| `pytest` | Corre las 96 pruebas (sin internet ni cuota de API) |

### Claves

| Variable | Para qué | Dónde |
| --- | --- | --- |
| `GEMINI_API_KEY` | LLM principal (obligatoria) | https://aistudio.google.com/apikey |
| `TAVILY_API_KEY` | Búsqueda web | https://app.tavily.com |
| `GROQ_API_KEY` | LLM de respaldo (opcional) | https://console.groq.com/keys |

La API de datos.gov.co es pública y no necesita clave.

## Arquitectura

```text
Usuario ──► Interfaz Gradio ◄──► Ciclo del agente ◄──► LLM (Gemini; respaldo Groq)
                                  1. Razonar: el LLM elige tool o responde
                                  2. Actuar: se ejecuta la tool pedida ──► Tools ──► datos.gov.co, Tavily, Python local
                                  3. Observar: el resultado vuelve al historial
                                  (hasta que el LLM responde sin pedir tools; máximo 15 pasos)
```

- **Ciclo propio** (`src/lupa/agent/agente.py`): no usamos LangChain; el ciclo razonar → actuar → observar está escrito a mano y emite cada paso como evento para mostrar la traza en vivo.
- **Capa de LLM** (`src/lupa/llm/`): una interfaz común y un proveedor por servicio. Cambiar de modelo es cambiar una variable.
- **Memoria**: el agente recuerda las preguntas y respuestas anteriores de la conversación, pero no arrastra los resultados intermedios de las tools.

### Tools

| Tool | Qué hace | Servicio |
| --- | --- | --- |
| `buscar_datasets` | Busca conjuntos por palabras clave o id y devuelve sus columnas | Catálogo de datos.gov.co |
| `consultar_dataset` | Ejecuta consultas SoQL (agregando en el servidor) y guarda la tabla como CSV | API SODA de datos.gov.co |
| `ejecutar_python` | Corre pandas y matplotlib sobre las tablas, en un proceso aparte con tiempo límite | Local |
| `buscar_web` | Busca contexto y noticias con extractos y URL | Tavily |
| `calculadora` | Cuentas exactas sin `eval` (árbol sintáctico) | Local |
| `cargar_skill` | Devuelve el procedimiento completo de un skill | `skills/` |

Todas devuelven texto; si fallan, el error vuelve al LLM con instrucciones para corregirlo. `consultar_dataset` bloquea las columnas con datos personales (cédulas, cuentas bancarias, supervisores) y guarda las respuestas en caché para que la demo no dependa de la velocidad de la API.

### Skills

| Skill | Objetivo |
| --- | --- |
| `explorar_datos` | Encontrar el conjunto correcto y entender sus columnas; trae 5 conjuntos verificados |
| `analisis_estadistico` | Calcular cifras correctas y validar totales |
| `visualizacion` | Elegir y generar una gráfica clara con título, unidades y fuente |
| `investigacion_web` | Buscar contexto, citarlo y separar hechos de opiniones |
| `redaccion_informe` | Entregar conclusión, cifras, gráfica, fuentes y limitaciones |

El prompt de sistema solo lleva el nombre y la descripción de cada skill. El agente decide cuándo cargar uno con `cargar_skill` (carga progresiva), así el contexto se mantiene corto y los skills se editan sin tocar el código.

## Evaluación

Como el agente no se entrena, su solidez se demuestra midiendo. `eval/tareas.json` tiene 12 tareas (4 simples, 4 de varios pasos y 4 complejas). Las respuestas esperadas **no están escritas a mano**: se calculan en el momento con una consulta directa a la API, así siguen siendo correctas aunque los datos se actualicen.

`lupa-evaluar` corre todas las tareas sin skills y con skills, y guarda en `eval/resultados/<fecha>/`:
- `resumen.md`: tasa de éxito total y por nivel, uso correcto de tools, pasos, errores recuperados, tiempo y tokens.
- `exito_por_nivel.png`: gráfica comparativa.
- `resultados.json`: el detalle de cada tarea, con las respuestas.

### Resultados (26 de noviembre de 2026)

Corrimos el banco completo **dos veces** con y sin skills: 24 ejecuciones por configuración. Las dos configuraciones corrieron una tras otra con la misma clave y la misma lista de modelos; por la cuota gratuita, en la segunda corrida casi todo lo respondió Gemini 3.5 Flash-Lite.

| Métrica | Sin skills | Con skills |
| --- | --- | --- |
| Tareas resueltas | 71 % (17 de 24) | **88 % (21 de 24)** |
| Tareas simples y de varios pasos | 75 % | **100 %** |
| Tareas complejas | 62 % | 62 % |
| Uso correcto de tools | 64 % | **95 %** |
| Pasos por tarea | 8,9 | 7,8 |
| Tokens por tarea | 50.637 | 36.745 (−27 %) |

- **Sin skills, el agente se equivoca de fuente o se rinde:** usó SECOP Integrado (que mezcla SECOP I y II) y contó 1.337 contratos en vez de 893; eligió un conjunto parcial de Saber 11; y en las dos corridas no logró encontrar los contratos de la Secretaría de Salud. Con skills fue directo a los conjuntos verificados.
- **Las tareas complejas no mejoraron.** La tarea C1 (“toda la Gobernación del Valle”) falló en las 4 ejecuciones: la Gobernación no es una sola entidad en SECOP II, y cada corrida decidió distinto qué dependencias sumar (de 1,27 a 1,90 billones, contra 1,53 con nuestro criterio). Las 5 dependencias principales sí salieron bien siempre.

Detalle: [resumen de las dos corridas](eval/resultados/dos-corridas-20261126/resumen.md) · [última corrida combinada](eval/resultados/combinado-20261126-132628/resumen.md) · [notebook ejecutado](notebooks/02_demo_lupa_ejecutado.ipynb).

## Estructura

```text
lupa-agente/
├── docs/diseno.md          documento de diseño
├── src/lupa/
│   ├── config.py           claves y parámetros (.env o secretos de Colab)
│   ├── llm/                interfaz común + Gemini + compatible con OpenAI (Groq)
│   ├── tools/              las 5 tools + registro y contexto compartido
│   ├── skills.py           carga de skills y tool cargar_skill
│   ├── agent/agente.py     ciclo del agente, traza y memoria
│   ├── ui/app.py           interfaz Gradio
│   ├── evaluacion.py       banco de tareas, verificación y métricas
│   ├── cli.py              lupa-preguntar
│   └── verificacion.py     lupa-verificar
├── skills/                 un SKILL.md por skill
├── eval/                   tareas.json, evaluar.py y resultados/
├── notebooks/              01_verificar_conexion.ipynb, 02_demo_lupa.ipynb
├── scripts/                atajos de línea de comandos
└── tests/                  96 pruebas con pytest
```

## Detalles técnicos que resolvimos

- **Firmas de pensamiento de Gemini 3**: al usar tools, Gemini exige recibir de vuelta su respuesta original con sus firmas; si se reconstruye a mano responde error 400. La capa de LLM guarda y reenvía la respuesta original, y agrupa en un solo mensaje los resultados de tools pedidas en paralelo.
- **Límites de la capa gratuita**: los errores 429 y 5xx se reintentan con espera creciente.
- **Cuota diaria vs. por minuto**: un error 429 de Gemini dice qué cuota se agotó. Si es la por minuto, Lupa espera los segundos que pide la API y repite con el mismo modelo; si es la diaria, deja ese modelo por el resto de la sesión; si se agotan todos, lo dice claramente en vez de reintentar en vano.
- **Modelos saturados**: si el modelo principal de Gemini responde 503 (alta demanda) o 429 (sin cuota), Lupa pasa solo al siguiente modelo de `LUPA_MODELOS_RESPALDO_GEMINI` sin perder la conversación. Como las firmas de pensamiento solo valen para el modelo que las creó, al cambiar se reenvían con el marcador `skip_thought_signature_validator` que indica la documentación de Gemini.
- **Datos reales, datos sucios**: nombres de entidades sin normalizar en SECOP II, puntajes guardados como texto en Saber 11 y filtros con `%` que deben codificarse en la URL. Los skills documentan cómo manejarlos.
- **Privacidad**: SECOP II publica cédulas y cuentas bancarias; Lupa no las consulta ni las muestra.

## Limitaciones conocidas

- Depende de la disponibilidad de datos.gov.co, Gemini y Tavily (la caché y el LLM de respaldo reducen el riesgo).
- La capa gratuita de Groq permite pocos tokens por minuto; con preguntas largas puede responder error 429.
- `ejecutar_python` es un entorno controlado para un proyecto académico, no un sandbox de producción.
