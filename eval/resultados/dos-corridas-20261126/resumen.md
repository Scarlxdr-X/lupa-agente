# Resultados de la evaluación: dos corridas completas (26 de noviembre de 2026)

Suma de las dos corridas completas del banco de 12 tareas, con y sin skills (24 ejecuciones por configuración):

| Corrida | Carpetas | Sin skills | Con skills |
| --- | --- | --- | --- |
| 1 | `20261126-113653`, `20261126-115930`, `20261126-121012` | 67 % | 83 % |
| 2 | `20261126-130143`, `20261126-130724`, `20261126-131532` | 75 % | 92 % |

Se calculó con `lupa.evaluacion.resumir` sobre los `resultados.json` de las seis carpetas. La carpeta `combinado-20261126-132628` es la salida de la celda 7.4, que se queda con la ejecución más reciente de cada tarea (corrida 2).

Proveedor: gemini · Tareas: 24 por configuración

| Métrica | Sin skills | Con skills |
| --- | --- | --- |
| Tasa de éxito (total) | 71 % | 88 % |
| Éxito: simples | 75 % | 100 % |
| Éxito: varios pasos | 75 % | 100 % |
| Éxito: complejas | 62 % | 62 % |
| Uso correcto de tools | 64 % | 95 % |
| Pasos por tarea (promedio) | 8.9 | 7.8 |
| Errores de tools / recuperados | 12 / 12 | 6 / 6 |
| Tiempo por tarea (promedio) | 67 s | 84 s |
| Tokens por tarea (promedio) | 50,637 | 36,745 |

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
| M1 | Sin skills | sí | 8 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, calculadora | numero: ok (esperado ≈ -702,180.00) |
| M2 | Sin skills | sí | 8 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, ejecutar_python, consultar_dataset, ejecutar_python | numero: ok (esperado ≈ 4,292.27); contiene: ok (ok) |
| M3 | Sin skills | no | 12 | buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets | numero: falla (esperado ≈ 224,026,434,814.00) |
| M4 | Sin skills | sí | 6 | buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, ejecutar_python | dataset: ok (consultó ['32sa-8pi3']); grafica: ok (1 gráficas) |
| M1 | Con skills | sí | 11 | cargar_skill, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, cargar_skill, calculadora, calculadora, calculadora, cargar_skill | numero: ok (esperado ≈ -702,180.00) |
| M2 | Con skills | sí | 6 | cargar_skill, consultar_dataset, cargar_skill, cargar_skill, calculadora | numero: ok (esperado ≈ 4,292.27); contiene: ok (ok) |
| M3 | Con skills | sí | 12 | cargar_skill, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, cargar_skill, cargar_skill, consultar_dataset, ejecutar_python, ejecutar_python, cargar_skill | numero: ok (esperado ≈ 224,026,434,814.00) |
| M4 | Con skills | sí | 7 | cargar_skill, consultar_dataset, cargar_skill, cargar_skill, ejecutar_python, cargar_skill | dataset: ok (consultó ['32sa-8pi3']); grafica: ok (1 gráficas) |
| C1 | Sin skills | no | 15 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, ejecutar_python, ejecutar_python, consultar_dataset, consultar_dataset, consultar_dataset, ejecutar_python, ejecutar_python, ejecutar_python, calculadora | numero: falla (esperado ≈ 1,530,717,006,754.22); grafica: falla (0 gráficas) |
| C2 | Sin skills | sí | 12 | buscar_datasets, buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, calculadora, calculadora | numero: ok (esperado ≈ 241.87); numero: ok (esperado ≈ 261.19) |
| C3 | Sin skills | sí | 9 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, ejecutar_python, ejecutar_python, buscar_web, buscar_web | dataset: ok (consultó ['32sa-8pi3']); grafica: ok (1 gráficas); web: ok (usó buscar_web y citó enlaces) |
| C4 | Sin skills | sí | 10 | buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset | tools_exitosas: ok (ok); contiene: ok (ok) |
| C1 | Con skills | no | 12 | cargar_skill, consultar_dataset, consultar_dataset, cargar_skill, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, cargar_skill, cargar_skill, ejecutar_python, ejecutar_python | numero: falla (esperado ≈ 1,530,717,006,754.22); grafica: ok (1 gráficas) |
| C2 | Con skills | sí | 8 | cargar_skill, consultar_dataset, cargar_skill, calculadora, cargar_skill, ejecutar_python, cargar_skill | numero: ok (esperado ≈ 241.87); numero: ok (esperado ≈ 261.19) |
| C3 | Con skills | sí | 8 | cargar_skill, consultar_dataset, cargar_skill, ejecutar_python, cargar_skill, buscar_web, cargar_skill | dataset: ok (consultó ['32sa-8pi3']); grafica: ok (1 gráficas); web: ok (usó buscar_web y citó enlaces) |
| C4 | Con skills | no | 15 | cargar_skill, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, cargar_skill, cargar_skill, consultar_dataset | tools_exitosas: ok (ok); contiene: falla (faltan: ['datos.gov.co/d/']) |
| S1 | Sin skills | sí | 8 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset | numero: ok (esperado ≈ 4,409.15) |
| S2 | Sin skills | sí | 8 | buscar_datasets, consultar_dataset, consultar_dataset, ejecutar_python, consultar_dataset, consultar_dataset, ejecutar_python | numero: ok (esperado ≈ 3,881.44) |
| S3 | Sin skills | sí | 7 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset | numero: ok (esperado ≈ 893.00) |
| S4 | Sin skills | sí | 3 | buscar_datasets, buscar_datasets | contiene: ok (ok) |
| S1 | Con skills | sí | 9 | cargar_skill, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, cargar_skill | numero: ok (esperado ≈ 4,409.15) |
| S2 | Con skills | sí | 5 | cargar_skill, cargar_skill, consultar_dataset, cargar_skill | numero: ok (esperado ≈ 3,881.44) |
| S3 | Con skills | sí | 5 | cargar_skill, consultar_dataset, consultar_dataset, cargar_skill | numero: ok (esperado ≈ 893.00) |
| S4 | Con skills | sí | 4 | cargar_skill, buscar_datasets, cargar_skill | contiene: ok (ok) |
| M1 | Sin skills | sí | 6 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, calculadora | numero: ok (esperado ≈ -702,180.00) |
| M2 | Sin skills | sí | 11 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, ejecutar_python, ejecutar_python, consultar_dataset, ejecutar_python, ejecutar_python | numero: ok (esperado ≈ 4,292.27); contiene: ok (ok) |
| M3 | Sin skills | no | 15 | buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset | numero: falla (esperado ≈ 224,026,434,814.00) |
| M4 | Sin skills | sí | 6 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, ejecutar_python | dataset: ok (consultó ['32sa-8pi3']); grafica: ok (1 gráficas) |
| M1 | Con skills | sí | 10 | cargar_skill, consultar_dataset, consultar_dataset, cargar_skill, calculadora, calculadora, calculadora, calculadora, cargar_skill | numero: ok (esperado ≈ -702,180.00) |
| M2 | Con skills | sí | 6 | cargar_skill, consultar_dataset, cargar_skill, cargar_skill, calculadora | numero: ok (esperado ≈ 4,292.27); contiene: ok (ok) |
| M3 | Con skills | sí | 6 | cargar_skill, consultar_dataset, consultar_dataset, cargar_skill, consultar_dataset | numero: ok (esperado ≈ 224,026,434,814.00) |
| M4 | Con skills | sí | 6 | cargar_skill, consultar_dataset, cargar_skill, ejecutar_python, cargar_skill | dataset: ok (consultó ['32sa-8pi3']); grafica: ok (1 gráficas) |
| C1 | Sin skills | no | 11 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, ejecutar_python, ejecutar_python, calculadora, ejecutar_python | numero: falla (esperado ≈ 1,530,717,006,754.22); grafica: ok (1 gráficas) |
| C2 | Sin skills | no | 10 | buscar_datasets, buscar_datasets, buscar_web, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, ejecutar_python, calculadora | numero: ok (esperado ≈ 241.87); numero: falla (esperado ≈ 261.19) |
| C3 | Sin skills | sí | 8 | buscar_datasets, buscar_datasets, consultar_dataset, consultar_dataset, ejecutar_python, ejecutar_python, buscar_web | dataset: ok (consultó ['32sa-8pi3']); grafica: ok (1 gráficas); web: ok (usó buscar_web y citó enlaces) |
| C4 | Sin skills | sí | 15 | buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, consultar_dataset, ejecutar_python, consultar_dataset, ejecutar_python, ejecutar_python | tools_exitosas: ok (ok); contiene: ok (ok) |
| C1 | Con skills | no | 11 | cargar_skill, consultar_dataset, cargar_skill, consultar_dataset, consultar_dataset, consultar_dataset, cargar_skill, ejecutar_python, ejecutar_python, cargar_skill | numero: falla (esperado ≈ 1,530,717,006,754.22); grafica: ok (1 gráficas) |
| C2 | Con skills | sí | 8 | cargar_skill, consultar_dataset, cargar_skill, calculadora, cargar_skill, ejecutar_python, cargar_skill | numero: ok (esperado ≈ 241.87); numero: ok (esperado ≈ 261.19) |
| C3 | Con skills | sí | 9 | cargar_skill, consultar_dataset, cargar_skill, ejecutar_python, cargar_skill, buscar_web, buscar_web, cargar_skill | dataset: ok (consultó ['32sa-8pi3']); grafica: ok (1 gráficas); web: ok (usó buscar_web y citó enlaces) |
| C4 | Con skills | sí | 10 | cargar_skill, buscar_datasets, consultar_dataset, consultar_dataset, consultar_dataset, ejecutar_python, consultar_dataset, ejecutar_python, cargar_skill | tools_exitosas: ok (ok); contiene: ok (ok) |
