# Resultados de la evaluación (2026-11-26 12:10)

Proveedor: gemini · Tareas: 4 por configuración

| Métrica | Sin skills | Con skills |
| --- | --- | --- |
| Tasa de éxito (total) | 75 % | 100 % |
| Éxito: simples | — | — |
| Éxito: varios pasos | 75 % | 100 % |
| Éxito: complejas | — | — |
| Uso correcto de tools | 49 % | 90 % |
| Pasos por tarea (promedio) | 8.5 | 9.0 |
| Errores de tools / recuperados | 1 / 1 | 2 / 2 |
| Tiempo por tarea (promedio) | 56 s | 87 s |
| Tokens por tarea (promedio) | 42,240 | 39,634 |

## Detalle por tarea

| Tarea | Configuración | Éxito | Pasos | Tools | Chequeos |
| --- | --- | --- | --- | --- | --- |
| M1 | Sin skills | sí | 8 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, calculadora | numero: ok (esperado ≈ -702,180.00) |
| M2 | Sin skills | sí | 8 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, ejecutar_python, consultar_dataset, ejecutar_python | numero: ok (esperado ≈ 4,292.27); contiene: ok (ok) |
| M3 | Sin skills | no | 12 | buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets | numero: falla (esperado ≈ 224,026,434,814.00) |
| M4 | Sin skills | sí | 6 | buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, ejecutar_python | dataset: ok (consultó ['32sa-8pi3']); grafica: ok (1 gráficas) |
| M1 | Con skills | sí | 11 | cargar_skill, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, cargar_skill, calculadora, calculadora, calculadora, cargar_skill | numero: ok (esperado ≈ -702,180.00) |
| M2 | Con skills | sí | 6 | cargar_skill, consultar_dataset, cargar_skill, cargar_skill, calculadora | numero: ok (esperado ≈ 4,292.27); contiene: ok (ok) |
| M3 | Con skills | sí | 12 | cargar_skill, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, cargar_skill, cargar_skill, consultar_dataset, ejecutar_python, ejecutar_python, cargar_skill | numero: ok (esperado ≈ 224,026,434,814.00) |
| M4 | Con skills | sí | 7 | cargar_skill, consultar_dataset, cargar_skill, cargar_skill, ejecutar_python, cargar_skill | dataset: ok (consultó ['32sa-8pi3']); grafica: ok (1 gráficas) |
