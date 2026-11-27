# Resultados de la evaluación (2026-11-26 13:26)

Proveedor: gemini · Tareas: 4 por configuración

| Métrica | Sin skills | Con skills |
| --- | --- | --- |
| Tasa de éxito (total) | 50 % | 75 % |
| Éxito: simples | — | — |
| Éxito: varios pasos | — | — |
| Éxito: complejas | 50 % | 75 % |
| Uso correcto de tools | 66 % | 91 % |
| Pasos por tarea (promedio) | 11.0 | 9.5 |
| Errores de tools / recuperados | 5 / 5 | 0 / 0 |
| Tiempo por tarea (promedio) | 78 s | 69 s |
| Tokens por tarea (promedio) | 72,666 | 53,118 |

## Detalle por tarea

| Tarea | Configuración | Éxito | Pasos | Tools | Chequeos |
| --- | --- | --- | --- | --- | --- |
| C1 | Sin skills | no | 11 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, ejecutar_python, ejecutar_python, calculadora, ejecutar_python | numero: falla (esperado ≈ 1,530,717,006,754.22); grafica: ok (1 gráficas) |
| C2 | Sin skills | no | 10 | buscar_datasets, buscar_datasets, buscar_web, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, ejecutar_python, calculadora | numero: ok (esperado ≈ 241.87); numero: falla (esperado ≈ 261.19) |
| C3 | Sin skills | sí | 8 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, ejecutar_python, ejecutar_python, buscar_web | dataset: ok (consultó ['32sa-8pi3']); grafica: ok (1 gráficas); web: ok (usó buscar_web y citó enlaces) |
| C4 | Sin skills | sí | 15 | buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, ejecutar_python, consultar_dataset, ejecutar_python, ejecutar_python | tools_exitosas: ok (ok); contiene: ok (ok) |
| C1 | Con skills | no | 11 | cargar_skill, consultar_dataset, cargar_skill, consultar_dataset, consultar_dataset, consultar_dataset, cargar_skill, ejecutar_python, ejecutar_python, cargar_skill | numero: falla (esperado ≈ 1,530,717,006,754.22); grafica: ok (1 gráficas) |
| C2 | Con skills | sí | 8 | cargar_skill, consultar_dataset, cargar_skill, calculadora, cargar_skill, ejecutar_python, cargar_skill | numero: ok (esperado ≈ 241.87); numero: ok (esperado ≈ 261.19) |
| C3 | Con skills | sí | 9 | cargar_skill, consultar_dataset, cargar_skill, ejecutar_python, cargar_skill, buscar_web, buscar_web, cargar_skill | dataset: ok (consultó ['32sa-8pi3']); grafica: ok (1 gráficas); web: ok (usó buscar_web y citó enlaces) |
| C4 | Con skills | sí | 10 | cargar_skill, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, ejecutar_python, consultar_dataset, ejecutar_python, cargar_skill | tools_exitosas: ok (ok); contiene: ok (ok) |
