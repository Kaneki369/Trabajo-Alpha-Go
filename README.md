# Trabajo-Alpha-Go


# Go vs IA (MCTS) — Proyecto complet

Implementación de un tablero de Go jugable con interfaz gráfica, IA basada en
Monte Carlo Tree Search (MCTS), y un análisis de desempeño de esa IA.

Inspirado en el documental **"AlphaGo"** (2017): se replica el componente de
*búsqueda en árbol* que es el núcleo algorítmico compartido con AlphaGo
(selección con UCB1, expansión, simulación y retropropagación), pero usando
*playouts* aleatorios en vez de redes neuronales de política/valor entrenadas
por autojuego — eso último requeriría semanas de entrenamiento con GPUs, algo
fuera del alcance de este ejercicio, y se documenta explícitamente esa
diferencia en el informe de análisis.

## ¿Por qué Python?

- La **lógica del juego** (captura, ko, suicidio, puntuación por área) se
  expresa de forma clara y verificable con estructuras de datos simples
  (listas, conjuntos), ideal para razonar sobre reglas y para testear.
- **Tkinter** viene incluido en la instalación estándar de Python: interfaz
  gráfica funcional sin instalar dependencias extra.
- Para el **análisis de desempeño**, Python tiene el ecosistema más maduro
  (matplotlib, pandas, csv) para correr experimentos, medir tiempos y generar
  gráficos/reportes automáticamente, reutilizando exactamente el mismo motor
  de reglas y de IA que usa la interfaz — así el análisis mide lo que
  realmente se juega, no una versión aparte.

## Archivos

| Archivo | Contenido |
|---|---|
| `go_logic.py` | Motor de reglas: tablero, capturas, ko, suicidio, puntuación por área. |
| `go_ai.py` | IA `MCTSPlayer` (Monte Carlo Tree Search) y `RandomPlayer` (línea base). |
| `go_gui.py` | Interfaz gráfica en Tkinter para jugar contra la IA. |
| `analysis.py` | Script que corre experimentos y genera el informe de desempeño. |
| `resultados_desempeno.csv` | Datos crudos de las partidas de prueba. |
| `grafico_winrate.png`, `grafico_tiempos.png` ,`grafico_1000sims.png`, `tabla_resumen.png`  | Gráficos generados por el análisis. |
 | `tabla_resumen.csv `,`tabla_resumen.py` | Información para crear la tabla de análisis de desempeño

## Cómo jugar

```bash
python3 go_gui.py
```

Se abre una ventana donde puedes elegir tamaño de tablero (5/7/9/13),
la fuerza de la IA (número de simulaciones: a más simulaciones, más fuerte
pero más lenta) y con qué color jugar. Haz clic en una intersección para
colocar piedra; "Pasar" para pasar turno; "Rendirse" para terminar la
partida. El marcador usa puntuación por área con komi de 6.5 para blanco.

**Recomendación:** para partidas fluidas, usa 100–300 simulaciones en
tableros 9x9 (respuestas en 1–4 segundos). En 13x13, baja a 100 simulaciones
o la IA tardará bastante más por jugada (ver informe de desempeño).

## Cómo correr el análisis de desempeño

```bash
python3 analysis.py
```

Corre dos experimentos (IA vs jugador aleatorio con distintas simulaciones;
y escalabilidad del tiempo de decisión según el tamaño del tablero), e
imprime el progreso en consola. Al terminar regenera `informe_analisis.md`,
los `.png` y el `.csv`. Tarda entre 1 y 3 minutos según el hardware.


