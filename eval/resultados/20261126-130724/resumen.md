# Resultados de la evaluación (2026-11-26 13:15)

Proveedor: gemini · Tareas: 4 por configuración

| Métrica | Sin skills | Con skills |
| --- | --- | --- |
| Tasa de éxito (total) | 75 % | 100 % |
| Éxito: simples | — | — |
| Éxito: varios pasos | 75 % | 100 % |
| Éxito: complejas | — | — |
| Uso correcto de tools | 47 % | 95 % |
| Pasos por tarea (promedio) | 9.5 | 7.0 |
| Errores de tools / recuperados | 2 / 2 | 0 / 0 |
| Tiempo por tarea (promedio) | 66 s | 39 s |
| Tokens por tarea (promedio) | 64,890 | 25,743 |

## Detalle por tarea

| Tarea | Configuración | Éxito | Pasos | Tools | Chequeos |
| --- | --- | --- | --- | --- | --- |
| M1 | Sin skills | sí | 6 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, calculadora | numero: ok (esperado ≈ -702,180.00) |
| M2 | Sin skills | sí | 11 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, ejecutar_python, ejecutar_python, consultar_dataset, ejecutar_python, ejecutar_python | numero: ok (esperado ≈ 4,292.27); contiene: ok (ok) |
| M3 | Sin skills | no | 15 | buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset | numero: falla (esperado ≈ 224,026,434,814.00) |
| M4 | Sin skills | sí | 6 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, ejecutar_python | dataset: ok (consultó ['32sa-8pi3']); grafica: ok (1 gráficas) |
| M1 | Con skills | sí | 10 | cargar_skill, consultar_dataset, consultar_dataset, cargar_skill, calculadora, calculadora, calculadora, calculadora, cargar_skill | numero: ok (esperado ≈ -702,180.00) |
| M2 | Con skills | sí | 6 | cargar_skill, consultar_dataset, cargar_skill, cargar_skill, calculadora | numero: ok (esperado ≈ 4,292.27); contiene: ok (ok) |
| M3 | Con skills | sí | 6 | cargar_skill, consultar_dataset, consultar_dataset, cargar_skill, consultar_dataset | numero: ok (esperado ≈ 224,026,434,814.00) |
| M4 | Con skills | sí | 6 | cargar_skill, consultar_dataset, cargar_skill, ejecutar_python, cargar_skill | dataset: ok (consultó ['32sa-8pi3']); grafica: ok (1 gráficas) |
