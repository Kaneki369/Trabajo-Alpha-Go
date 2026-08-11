

import csv
import statistics as stats

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def cargar_resultados(path="resultados_desempeno.csv"):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        filas = []
        for r in reader:
            filas.append({
                "simulaciones": int(r["simulaciones"]),
                "ganador": r["ganador"],
                "score_negro": float(r["score_negro"]),
                "score_blanco": float(r["score_blanco"]),
                "movimientos_totales": int(r["movimientos_totales"]),
                "tiempo_medio_decision_mcts_seg": float(r["tiempo_medio_decision_mcts_seg"]),
                "capturas_negro": int(r["capturas_negro"]),
                "capturas_blanco": int(r["capturas_blanco"]),
            })
        return filas


def construir_tabla_resumen(filas):
    niveles = sorted(set(f["simulaciones"] for f in filas))
    tabla = []
    for sim in niveles:
        grupo = [f for f in filas if f["simulaciones"] == sim]
        n = len(grupo)
        wins = sum(1 for f in grupo if f["ganador"] == "BLACK")
        winrate = wins / n * 100
        score_negro = stats.mean(f["score_negro"] for f in grupo)
        score_blanco = stats.mean(f["score_blanco"] for f in grupo)
        margen = stats.mean(f["score_negro"] - f["score_blanco"] for f in grupo)
        movimientos = stats.mean(f["movimientos_totales"] for f in grupo)
        tiempo = stats.mean(f["tiempo_medio_decision_mcts_seg"] for f in grupo)
        tiempo_sd = stats.pstdev(f["tiempo_medio_decision_mcts_seg"] for f in grupo) if n > 1 else 0.0
        capturas_negro = stats.mean(f["capturas_negro"] for f in grupo)
        capturas_blanco = stats.mean(f["capturas_blanco"] for f in grupo)

        tabla.append({
            "simulaciones": sim,
            "partidas": n,
            "winrate_pct": round(winrate, 1),
            "score_negro_prom": round(score_negro, 2),
            "score_blanco_prom": round(score_blanco, 2),
            "margen_prom": round(margen, 2),
            "movimientos_prom": round(movimientos, 2),
            "tiempo_prom_seg": round(tiempo, 3),
            "tiempo_desv_est": round(tiempo_sd, 3),
            "capturas_negro_prom": round(capturas_negro, 2),
            "capturas_blanco_prom": round(capturas_blanco, 2),
        })
    return tabla


def guardar_csv(tabla, path="tabla_resumen.csv"):
    fieldnames = list(tabla[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for fila in tabla:
            writer.writerow(fila)


def guardar_imagen(tabla, path="tabla_resumen.png"):
    encabezados = ["Simulaciones", "Winrate", "Score\nNegro", "Score\nBlanco",
                   "Margen", "Movim.\nprom.", "Tiempo/decisión\n(s)",
                   "Capturas\nNegro", "Capturas\nBlanco"]

    filas_texto = []
    for fila in tabla:
        filas_texto.append([
            str(fila["simulaciones"]),
            f"{fila['winrate_pct']:.0f}%",
            f"{fila['score_negro_prom']:.2f}",
            f"{fila['score_blanco_prom']:.2f}",
            f"{fila['margen_prom']:.2f}",
            f"{fila['movimientos_prom']:.2f}",
            f"{fila['tiempo_prom_seg']:.3f}",
            f"{fila['capturas_negro_prom']:.2f}",
            f"{fila['capturas_blanco_prom']:.2f}",
        ])

    n_filas = len(filas_texto)
    fig, ax = plt.subplots(figsize=(11, 1 + 0.6 * n_filas))
    ax.axis("off")

    tabla_mpl = ax.table(
        cellText=filas_texto,
        colLabels=encabezados,
        loc="center",
        cellLoc="center",
    )
    tabla_mpl.auto_set_font_size(False)
    tabla_mpl.set_fontsize(10)
    tabla_mpl.scale(1, 2.0)

    # Estilo: encabezado resaltado
    for col in range(len(encabezados)):
        celda = tabla_mpl[0, col]
        celda.set_facecolor("#2b6cb0")
        celda.set_text_props(color="white", weight="bold")

    # Filas alternadas para facilitar la lectura
    for fila_idx in range(1, n_filas + 1):
        color = "#f0f4f8" if fila_idx % 2 == 0 else "white"
        for col in range(len(encabezados)):
            tabla_mpl[fila_idx, col].set_facecolor(color)

    plt.title("Resumen de desempeño MCTS por nivel de simulaciones", fontsize=12, pad=14)
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


def main():
    filas = cargar_resultados("resultados_desempeno.csv")
    tabla = construir_tabla_resumen(filas)
    guardar_csv(tabla, "tabla_resumen.csv")
    guardar_imagen(tabla, "tabla_resumen.png")
    print("Archivos generados: tabla_resumen.csv, tabla_resumen.png")


if __name__ == "__main__":
    main()