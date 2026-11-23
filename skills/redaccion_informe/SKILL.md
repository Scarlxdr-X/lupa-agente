---
nombre: redaccion_informe
descripcion: Redactar la respuesta final como un informe breve, con la conclusión primero, cifras, gráfica, fuentes y limitaciones.
tools: []
---

# Redacción del informe

## Cuándo usarlo
Al cerrar cualquier tarea de varios pasos. Para preguntas de un solo dato, responde en 2 o 3 líneas con la cifra
y la fuente, sin secciones.

## Estructura (markdown)

**Respuesta:** una o dos frases con la cifra principal, su unidad y su periodo.

### Hallazgos
- De 2 a 5 viñetas con cifras en formato colombiano (1.234.567), unidades y periodo.

### Gráfica
- El nombre del archivo generado y qué debe notar el lector (la interfaz la muestra al lado).

### Contexto
- Solo si hubo búsqueda web: los factores encontrados, cada uno con su enlace.

### Fuentes
- Cada conjunto de datos usado: nombre, id y enlace `https://www.datos.gov.co/d/<id>`.
- Cada página web citada: título y enlace.

### Limitaciones
- De 1 a 3 viñetas: fecha de corte de los datos, nombres de entidades no normalizados, aproximaciones usadas.

## Reglas
- Ninguna cifra sin una tool que la respalde. Si no pudiste obtener un dato, dilo.
- Escribe los pesos sin el signo $: "702.180 pesos" o "COP 4.409,15". El signo $ se confunde con fórmulas
  matemáticas y daña el formato de la respuesta.
- Nunca incluyas datos personales (cédulas, cuentas, nombres de funcionarios).
- No des recomendaciones financieras ni opiniones políticas: describe lo que muestran los datos.
- Español claro, sin jerga técnica (no hables de SoQL ni de tools). Unas 250 palabras como máximo, salvo que el
  usuario pida más detalle.
