# Resultados de la evaluación (2026-11-26 13:26)

Proveedor: gemini · Tareas: 12 por configuración

| Métrica | Sin skills | Con skills |
| --- | --- | --- |
| Tasa de éxito (total) | 75 % | 92 % |
| Éxito: simples | 100 % | 100 % |
| Éxito: varios pasos | 75 % | 100 % |
| Éxito: complejas | 50 % | 75 % |
| Uso correcto de tools | 62 % | 95 % |
| Pasos por tarea (promedio) | 9.0 | 7.4 |
| Errores de tools / recuperados | 9 / 9 | 2 / 2 |
| Tiempo por tarea (promedio) | 57 s | 49 s |
| Tokens por tarea (promedio) | 54,536 | 33,112 |

## Detalle por tarea

| Tarea | Configuración | Éxito | Pasos | Tools | Chequeos |
| --- | --- | --- | --- | --- | --- |
| C1 | Con skills | no | 11 | cargar_skill, consultar_dataset, cargar_skill, consultar_dataset, consultar_dataset, consultar_dataset, cargar_skill, ejecutar_python, ejecutar_python, cargar_skill | numero: falla (esperado ≈ 1,530,717,006,754.22); grafica: ok (1 gráficas) |
| C2 | Con skills | sí | 8 | cargar_skill, consultar_dataset, cargar_skill, calculadora, cargar_skill, ejecutar_python, cargar_skill | numero: ok (esperado ≈ 241.87); numero: ok (esperado ≈ 261.19) |
| C3 | Con skills | sí | 9 | cargar_skill, consultar_dataset, cargar_skill, ejecutar_python, cargar_skill, buscar_web, buscar_web, cargar_skill | dataset: ok (consultó ['32sa-8pi3']); grafica: ok (1 gráficas); web: ok (usó buscar_web y citó enlaces) |
| C4 | Con skills | sí | 10 | cargar_skill, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, ejecutar_python, consultar_dataset, ejecutar_python, cargar_skill | tools_exitosas: ok (ok); contiene: ok (ok) |
| M1 | Con skills | sí | 10 | cargar_skill, consultar_dataset, consultar_dataset, cargar_skill, calculadora, calculadora, calculadora, calculadora, cargar_skill | numero: ok (esperado ≈ -702,180.00) |
| M2 | Con skills | sí | 6 | cargar_skill, consultar_dataset, cargar_skill, cargar_skill, calculadora | numero: ok (esperado ≈ 4,292.27); contiene: ok (ok) |
| M3 | Con skills | sí | 6 | cargar_skill, consultar_dataset, consultar_dataset, cargar_skill, consultar_dataset | numero: ok (esperado ≈ 224,026,434,814.00) |
| M4 | Con skills | sí | 6 | cargar_skill, consultar_dataset, cargar_skill, ejecutar_python, cargar_skill | dataset: ok (consultó ['32sa-8pi3']); grafica: ok (1 gráficas) |
| S1 | Con skills | sí | 9 | cargar_skill, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, cargar_skill | numero: ok (esperado ≈ 4,409.15) |
| S2 | Con skills | sí | 5 | cargar_skill, cargar_skill, consultar_dataset, cargar_skill | numero: ok (esperado ≈ 3,881.44) |
| S3 | Con skills | sí | 5 | cargar_skill, consultar_dataset, consultar_dataset, cargar_skill | numero: ok (esperado ≈ 893.00) |
| S4 | Con skills | sí | 4 | cargar_skill, buscar_datasets, cargar_skill | contiene: ok (ok) |
| C1 | Sin skills | no | 11 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, ejecutar_python, ejecutar_python, calculadora, ejecutar_python | numero: falla (esperado ≈ 1,530,717,006,754.22); grafica: ok (1 gráficas) |
| C2 | Sin skills | no | 10 | buscar_datasets, buscar_datasets, buscar_web, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, ejecutar_python, calculadora | numero: ok (esperado ≈ 241.87); numero: falla (esperado ≈ 261.19) |
| C3 | Sin skills | sí | 8 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, ejecutar_python, ejecutar_python, buscar_web | dataset: ok (consultó ['32sa-8pi3']); grafica: ok (1 gráficas); web: ok (usó buscar_web y citó enlaces) |
| C4 | Sin skills | sí | 15 | buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, ejecutar_python, consultar_dataset, ejecutar_python, ejecutar_python | tools_exitosas: ok (ok); contiene: ok (ok) |
| M1 | Sin skills | sí | 6 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, calculadora | numero: ok (esperado ≈ -702,180.00) |
| M2 | Sin skills | sí | 11 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, ejecutar_python, ejecutar_python, consultar_dataset, ejecutar_python, ejecutar_python | numero: ok (esperado ≈ 4,292.27); contiene: ok (ok) |
| M3 | Sin skills | no | 15 | buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset | numero: falla (esperado ≈ 224,026,434,814.00) |
| M4 | Sin skills | sí | 6 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, ejecutar_python | dataset: ok (consultó ['32sa-8pi3']); grafica: ok (1 gráficas) |
| S1 | Sin skills | sí | 8 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset | numero: ok (esperado ≈ 4,409.15) |
| S2 | Sin skills | sí | 8 | buscar_datasets, consultar_dataset, consultar_dataset, ejecutar_python, consultar_dataset, consultar_dataset, ejecutar_python | numero: ok (esperado ≈ 3,881.44) |
| S3 | Sin skills | sí | 7 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset | numero: ok (esperado ≈ 893.00) |
| S4 | Sin skills | sí | 3 | buscar_datasets, buscar_datasets | contiene: ok (ok) |
