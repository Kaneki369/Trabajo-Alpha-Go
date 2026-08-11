"""
go_gui.py
Interfaz gráfica simple (Tkinter, sin dependencias externas) para jugar
al Go contra la IA MCTS implementada en go_ai.py.

Ejecutar con:  python3 go_gui.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading

from go_logic import GoBoard, BLACK, WHITE, EMPTY, IllegalMoveError
from go_ai import MCTSPlayer

MARGIN = 40
CELL = 42
STONE_R = 18
LABEL_OFFSET = 22  # distancia entre las etiquetas (letras/números) y el borde del tablero

# Letras estándar de Go: se salta la "I" para no confundir con el número 1
COLUMN_LETTERS = "ABCDEFGHJKLMNOPQRST"


class GoGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Go vs IA (MCTS)")

        self.board_size = 9
        self.simulations = 300
        self.human_color = BLACK
        self.ai = None
        self.board = None
        self.thinking = False

        self._build_controls()
        self._build_canvas()
        self.new_game()

    # ---------- construcción de la UI ----------

    def _build_controls(self):
        top = ttk.Frame(self.root, padding=8)
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(top, text="Tamaño tablero:").pack(side=tk.LEFT)
        self.size_var = tk.StringVar(value="9")
        size_box = ttk.Combobox(top, textvariable=self.size_var, values=["5", "7", "9", "13"],
                                 width=3, state="readonly")
        size_box.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(top, text="Fuerza IA (simulaciones):").pack(side=tk.LEFT)
        self.sims_var = tk.StringVar(value="300")
        sims_box = ttk.Combobox(top, textvariable=self.sims_var,
                                 values=["100", "300", "600", "1000"], width=5, state="readonly")
        sims_box.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(top, text="Juegas con:").pack(side=tk.LEFT)
        self.color_var = tk.StringVar(value="Negro")
        color_box = ttk.Combobox(top, textvariable=self.color_var,
                                  values=["Negro", "Blanco"], width=7, state="readonly")
        color_box.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(top, text="Nueva partida", command=self.new_game).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Pasar", command=self.human_pass).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Rendirse", command=self.human_resign).pack(side=tk.LEFT, padx=4)

        self.status_var = tk.StringVar(value="")
        ttk.Label(self.root, textvariable=self.status_var, padding=6).pack(side=tk.TOP, fill=tk.X)

    def _build_canvas(self):
        self.canvas = tk.Canvas(self.root, bg="#DCB35C")
        self.canvas.pack(side=tk.TOP, padx=10, pady=10)
        self.canvas.bind("<Button-1>", self.on_click)

    # ---------- gestión de partida ----------

    def new_game(self):
        self.board_size = int(self.size_var.get())
        self.simulations = int(self.sims_var.get())
        self.human_color = BLACK if self.color_var.get() == "Negro" else WHITE
        ai_color = WHITE if self.human_color == BLACK else BLACK

        self.board = GoBoard(self.board_size)
        self.ai = MCTSPlayer(ai_color, simulations=self.simulations)
        self.thinking = False

        size_px = MARGIN * 2 + CELL * (self.board_size - 1)
        self.canvas.config(width=size_px, height=size_px)

        self.draw_board()
        self.update_status()

        if self.human_color == WHITE:
            self.root.after(300, self.ai_move)

    def coord_to_pixel(self, x, y):
        return MARGIN + x * CELL, MARGIN + y * CELL

    def pixel_to_coord(self, px, py):
        x = round((px - MARGIN) / CELL)
        y = round((py - MARGIN) / CELL)
        return x, y

    def draw_board(self):
        self.canvas.delete("all")
        n = self.board_size
        for i in range(n):
            x0, y0 = self.coord_to_pixel(i, 0)
            x1, y1 = self.coord_to_pixel(i, n - 1)
            self.canvas.create_line(x0, y0, x1, y1)
            x0, y0 = self.coord_to_pixel(0, i)
            x1, y1 = self.coord_to_pixel(n - 1, i)
            self.canvas.create_line(x0, y0, x1, y1)

        self.draw_coordinates()

        for x in range(n):
            for y in range(n):
                v = self.board.grid[x][y]
                if v != EMPTY:
                    cx, cy = self.coord_to_pixel(x, y)
                    color = "black" if v == BLACK else "white"
                    outline = "black"
                    self.canvas.create_oval(cx - STONE_R, cy - STONE_R, cx + STONE_R, cy + STONE_R,
                                             fill=color, outline=outline, width=1)

    def draw_coordinates(self):
        """Dibuja las letras (columnas) arriba y los números (filas) a la
        izquierda del tablero, igual que en la transmisión de AlphaGo vs
        Lee Sedol. No modifica coord_to_pixel/pixel_to_coord, así que no
        afecta la detección de clics ni la lógica de juego."""
        n = self.board_size
        font = ("TkDefaultFont", 10, "bold")

        for x in range(n):
            px, _ = self.coord_to_pixel(x, 0)
            letter = COLUMN_LETTERS[x]
            self.canvas.create_text(px, MARGIN - LABEL_OFFSET, text=letter, font=font)

        for y in range(n):
            _, py = self.coord_to_pixel(0, y)
            # Numeración estilo tablero real: 1 arriba, aumentando hacia abajo
            number = y + 1
            self.canvas.create_text(MARGIN - LABEL_OFFSET, py, text=str(number), font=font)

    def update_status(self):
        turn = "Negro" if self.board.current_player == BLACK else "Blanco"
        b, w = self.board.score()
        msg = f"Turno: {turn}   |   Piedras en tablero -> Negro: {b}  Blanco: {w} (komi blanco +6.5)"
        if self.thinking:
            msg += "   |   La IA está pensando..."
        if self.board.game_over:
            winner, bscore, wscore = self.board.winner()
            wname = "Negro" if winner == BLACK else "Blanco"
            msg = f"Partida terminada. Ganador: {wname}  ({bscore:.1f} vs {wscore:.1f})"
        self.status_var.set(msg)

    # ---------- interacción ----------

    def on_click(self, event):
        if self.thinking or self.board.game_over:
            return
        if self.board.current_player != self.human_color:
            return
        x, y = self.pixel_to_coord(event.x, event.y)
        if not self.board.in_bounds(x, y):
            return
        try:
            self.board.play(x, y)
        except IllegalMoveError:
            messagebox.showinfo("Jugada ilegal", "Esa jugada no es legal (captura propia, ko, o casilla ocupada).")
            return
        self.draw_board()
        self.update_status()
        if not self.board.game_over:
            self.root.after(200, self.ai_move)

    def human_pass(self):
        if self.thinking or self.board.game_over:
            return
        if self.board.current_player != self.human_color:
            return
        self.board.pass_move()
        self.draw_board()
        self.update_status()
        if not self.board.game_over:
            self.root.after(200, self.ai_move)

    def human_resign(self):
        if messagebox.askyesno("Rendirse", "¿Seguro que quieres rendirte?"):
            self.board.game_over = True
            winner = "Blanco" if self.human_color == BLACK else "Negro"
            self.status_var.set(f"Te has rendido. Ganador: {winner}")

    def ai_move(self):
        if self.board.game_over:
            return
        self.thinking = True
        self.update_status()
        self.root.update_idletasks()

        def worker():
            move = self.ai.choose_move(self.board)
            self.root.after(0, lambda: self._apply_ai_move(move))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_ai_move(self, move):
        if move is None:
            self.board.pass_move()
        else:
            self.board.play(*move)
        self.thinking = False
        self.draw_board()
        self.update_status()


def main():
    root = tk.Tk()
    GoGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
