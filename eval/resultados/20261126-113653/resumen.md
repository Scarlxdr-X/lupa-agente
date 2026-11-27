# Resultados de la evaluación (2026-11-26 11:59)

Proveedor: gemini · Tareas: 4 por configuración

| Métrica | Sin skills | Con skills |
| --- | --- | --- |
| Tasa de éxito (total) | 50 % | 100 % |
| Éxito: simples | 50 % | 100 % |
| Éxito: varios pasos | — | — |
| Éxito: complejas | — | — |
| Uso correcto de tools | 66 % | 100 % |
| Pasos por tarea (promedio) | 6.2 | 4.8 |
| Errores de tools / recuperados | 0 / 0 | 1 / 1 |
| Tiempo por tarea (promedio) | 101 s | 220 s |
| Tokens por tarea (promedio) | 22,967 | 15,202 |

## Detalle por tarea

| Tarea | Configuración | Éxito | Pasos | Tools | Chequeos |
| --- | --- | --- | --- | --- | --- |
| S1 | Sin skills | sí | 8 | buscar_datasets, buscar_datasets, consultar_dataset, ejecutar_python, consultar_dataset, ejecutar_python, consultar_dataset | numero: ok (esperado ≈ 4,409.15) |
| S2 | Sin skills | sí | 7 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, calculadora | numero: ok (esperado ≈ 3,881.44) |
| S3 | Sin skills | no | 8 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset | numero: falla (esperado ≈ 893.00) |
| S4 | Sin skills | no | 2 | buscar_datasets | contiene: falla (faltan: ['kgxf-xxbe']) |
| S1 | Con skills | sí | 6 | cargar_skill, consultar_dataset, consultar_dataset, consultar_dataset, cargar_skill | numero: ok (esperado ≈ 4,409.15) |
| S2 | Con skills | sí | 6 | cargar_skill, cargar_skill, consultar_dataset, consultar_dataset, cargar_skill | numero: ok (esperado ≈ 3,881.44) |
| S3 | Con skills | sí | 4 | cargar_skill, consultar_dataset, cargar_skill | numero: ok (esperado ≈ 893.00) |
| S4 | Con skills | sí | 3 | cargar_skill, buscar_datasets | contiene: ok (ok) |
