# Evaluación

- `tareas.json`: 12 tareas (4 simples, 4 de varios pasos, 4 complejas). Cada una trae sus verificaciones; las cifras
  esperadas se calculan en el momento con una consulta directa a datos.gov.co.
- `evaluar.py`: corre el banco con y sin skills (`python eval/evaluar.py` o `lupa-evaluar`).
- `resultados/<fecha>/`: `resumen.md`, `exito_por_nivel.png` y `resultados.json` de cada corrida.

Tipos de verificación: `numero` (la cifra aparece en la respuesta, con tolerancia), `contiene`, `grafica`, `web`
(usó buscar_web y citó enlaces), `dataset` (consultó el conjunto correcto) y `tools_exitosas`.
