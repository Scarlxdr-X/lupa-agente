# Resultados de la evaluación (2026-11-26 13:07)

Proveedor: gemini · Tareas: 4 por configuración

| Métrica | Sin skills | Con skills |
| --- | --- | --- |
| Tasa de éxito (total) | 100 % | 100 % |
| Éxito: simples | 100 % | 100 % |
| Éxito: varios pasos | — | — |
| Éxito: complejas | — | — |
| Uso correcto de tools | 74 % | 100 % |
| Pasos por tarea (promedio) | 6.5 | 5.8 |
| Errores de tools / recuperados | 2 / 2 | 2 / 2 |
| Tiempo por tarea (promedio) | 28 s | 39 s |
| Tokens por tarea (promedio) | 26,052 | 20,476 |

## Detalle por tarea

| Tarea | Configuración | Éxito | Pasos | Tools | Chequeos |
| --- | --- | --- | --- | --- | --- |
| S1 | Sin skills | sí | 8 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset | numero: ok (esperado ≈ 4,409.15) |
| S2 | Sin skills | sí | 8 | buscar_datasets, consultar_dataset, consultar_dataset, ejecutar_python, consultar_dataset, consultar_dataset, ejecutar_python | numero: ok (esperado ≈ 3,881.44) |
| S3 | Sin skills | sí | 7 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset | numero: ok (esperado ≈ 893.00) |
| S4 | Sin skills | sí | 3 | buscar_datasets, buscar_datasets | contiene: ok (ok) |
| S1 | Con skills | sí | 9 | cargar_skill, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, cargar_skill | numero: ok (esperado ≈ 4,409.15) |
| S2 | Con skills | sí | 5 | cargar_skill, cargar_skill, consultar_dataset, cargar_skill | numero: ok (esperado ≈ 3,881.44) |
| S3 | Con skills | sí | 5 | cargar_skill, consultar_dataset, consultar_dataset, cargar_skill | numero: ok (esperado ≈ 893.00) |
| S4 | Con skills | sí | 4 | cargar_skill, buscar_datasets, cargar_skill | contiene: ok (ok) |
