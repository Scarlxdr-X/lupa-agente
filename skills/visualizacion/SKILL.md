---
nombre: visualizacion
descripcion: Elegir y generar una gráfica clara, con título, ejes con unidades y fuente, a partir de una tabla consultada.
tools: [ejecutar_python]
---

# Visualización

## Cuándo usarlo
Cuando el usuario pide una gráfica, o cuando la respuesta tiene una serie de tiempo o una comparación de más de
tres categorías.

## Qué gráfica elegir
| Pregunta | Gráfica |
| --- | --- |
| ¿Cómo cambió algo en el tiempo? | Línea, con el tiempo en el eje x en orden |
| ¿Quién tiene más / menos? | Barras horizontales ordenadas de mayor a menor |
| Comparar dos grupos en varias categorías | Barras agrupadas |
| Distribución de una variable | Histograma |

Nunca tortas 3D. Máximo 10 a 12 categorías: agrupa el resto en "Otros".

## Plantilla
```python
import matplotlib.ticker as mticker

df = pd.read_csv('tabla_1.csv')
df['mes'] = pd.to_datetime(df['mes'])
df = df.sort_values('mes')

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(df['mes'], df['trm'], marker='o', linewidth=2)
ax.set_title('TRM promedio mensual, 2025')
ax.set_xlabel('Mes')
ax.set_ylabel('Pesos por dólar (COP)')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'.replace(',', '.')))
ax.grid(alpha=0.3)
fig.text(0.01, -0.02, 'Fuente: datos.gov.co, conjunto 32sa-8pi3', fontsize=8, color='gray')
plt.savefig('trm_mensual_2025.png', dpi=120, bbox_inches='tight')
print('Gráfica guardada')
```

## Reglas
- Nombre de archivo descriptivo (`contratos_valle_2025.png`, no `grafica.png`).
- Título que diga qué muestra; ejes con unidades; fuente en el pie.
- Cifras grandes en millones: divide y dilo en el eje (`Valor (miles de millones de COP)`).
- Barras horizontales para nombres largos (entidades); recorta nombres a ~40 caracteres.
- En el informe, menciona el archivo y qué debería notar el lector en la gráfica.
