"""
go_logic.py
Motor de reglas del juego GO (Igo/Weiqi/Baduk).

Reglas implementadas:
- Colocación de piedras, captura de grupos sin libertades.
- Prohibición de jugadas suicidas (salvo que capturen).
- Regla de Ko simplificada (superko posicional de un solo paso:
  no se permite repetir la posición inmediatamente anterior).
- Paso (pass) y fin de partida por doble paso.
- Puntuación por área (Tromp-Taylor): piedras vivas en el tablero
  + territorio (regiones vacías rodeadas por un único color).

Este módulo NO depende de ninguna interfaz gráfica, para poder
reutilizarse tanto en la GUI como en el script de análisis de
rendimiento (analysis.py).
"""

from copy import deepcopy

EMPTY, BLACK, WHITE = 0, 1, 2


class IllegalMoveError(Exception):
    pass


class GoBoard:
    def __init__(self, size=9):
        self.size = size
        self.grid = [[EMPTY] * size for _ in range(size)]
        self.current_player = BLACK
        self.previous_grid = None      # para la regla de Ko (1 paso atrás)
        self.pass_count = 0
        self.history = []              # lista de (jugador, mov) para debug/replay
        self.captures = {BLACK: 0, WHITE: 0}  # piedras capturadas POR cada color
        self.game_over = False

    # ---------- utilidades básicas ----------

    def clone(self):
        """Clonación ligera: solo copia lo que realmente cambia entre
        jugadas (grid, jugador, previous_grid). Evita deepcopy del
        objeto completo (mucho más rápido, crítico para MCTS)."""
        new = GoBoard.__new__(GoBoard)
        new.size = self.size
        new.grid = [row[:] for row in self.grid]
        new.current_player = self.current_player
        new.previous_grid = self.previous_grid  # es inmutable en la práctica (se reemplaza, no se muta)
        new.pass_count = self.pass_count
        new.history = self.history  # no se necesita copiar para MCTS (solo lectura)
        new.captures = dict(self.captures)
        new.game_over = self.game_over
        return new

    def opponent(self, color):
        return WHITE if color == BLACK else BLACK

    def in_bounds(self, x, y):
        return 0 <= x < self.size and 0 <= y < self.size

    def neighbors(self, x, y):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny):
                yield nx, ny

    def get_group(self, x, y):
        """Devuelve (conjunto de coordenadas del grupo, conjunto de libertades)."""
        color = self.grid[x][y]
        if color == EMPTY:
            return set(), set()
        stack = [(x, y)]
        group = set()
        liberties = set()
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in group:
                continue
            group.add((cx, cy))
            for nx, ny in self.neighbors(cx, cy):
                if self.grid[nx][ny] == EMPTY:
                    liberties.add((nx, ny))
                elif self.grid[nx][ny] == color and (nx, ny) not in group:
                    stack.append((nx, ny))
        return group, liberties

    def legal_moves(self, color=None):
        """Lista de jugadas legales (x, y) para el color dado (sin incluir pass)."""
        color = color or self.current_player
        moves = []
        for x in range(self.size):
            for y in range(self.size):
                if self.grid[x][y] == EMPTY and self.is_legal(x, y, color):
                    moves.append((x, y))
        return moves

    # ---------- validación y ejecución de jugadas ----------

    def is_legal(self, x, y, color=None):
        """Versión optimizada: trabaja sobre una copia ligera del grid
        (listas de enteros) en vez de clonar el objeto GoBoard completo,
        lo cual es mucho más rápido y es el cuello de botella típico
        de MCTS en Python puro."""
        color = color or self.current_player
        if not self.in_bounds(x, y) or self.grid[x][y] != EMPTY:
            return False

        trial_grid = [row[:] for row in self.grid]
        trial_grid[x][y] = color
        opp = self.opponent(color)

        self._remove_dead_groups_on(trial_grid, opp)

        # Regla de suicidio
        _, liberties = self._group_on(trial_grid, x, y)
        if not liberties:
            return False

        # Regla de Ko simplificada
        if self.previous_grid is not None and trial_grid == self.previous_grid:
            return False

        return True

    def _group_on(self, grid, x, y):
        color = grid[x][y]
        if color == EMPTY:
            return set(), set()
        stack = [(x, y)]
        group, liberties = set(), set()
        n = self.size
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in group:
                continue
            group.add((cx, cy))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < n and 0 <= ny < n:
                    v = grid[nx][ny]
                    if v == EMPTY:
                        liberties.add((nx, ny))
                    elif v == color and (nx, ny) not in group:
                        stack.append((nx, ny))
        return group, liberties

    def _remove_dead_groups_on(self, grid, color):
        removed = 0
        seen = set()
        n = self.size
        for x in range(n):
            for y in range(n):
                if grid[x][y] == color and (x, y) not in seen:
                    group, liberties = self._group_on(grid, x, y)
                    seen |= group
                    if not liberties:
                        for gx, gy in group:
                            grid[gx][gy] = EMPTY
                        removed += len(group)
        return removed

    def _remove_dead_groups(self, color):
        """Elimina del tablero todos los grupos de `color` sin libertades.
        Devuelve el número de piedras capturadas."""
        removed = 0
        seen = set()
        for x in range(self.size):
            for y in range(self.size):
                if self.grid[x][y] == color and (x, y) not in seen:
                    group, liberties = self.get_group(x, y)
                    seen |= group
                    if not liberties:
                        for gx, gy in group:
                            self.grid[gx][gy] = EMPTY
                        removed += len(group)
        return removed

    def play(self, x, y):
        color = self.current_player
        if not self.is_legal(x, y, color):
            raise IllegalMoveError(f"Jugada ilegal en ({x},{y}) para color {color}")

        prev_snapshot = deepcopy(self.grid)
        self.grid[x][y] = color
        captured = self._remove_dead_groups(self.opponent(color))
        self.captures[color] += captured

        self.previous_grid = prev_snapshot
        self.history.append((color, (x, y)))
        self.pass_count = 0
        self.current_player = self.opponent(color)
        return captured

    def pass_move(self):
        self.previous_grid = deepcopy(self.grid)
        self.history.append((self.current_player, None))
        self.pass_count += 1
        self.current_player = self.opponent(self.current_player)
        if self.pass_count >= 2:
            self.game_over = True

    # ---------- puntuación (área, estilo Tromp-Taylor) ----------

    def score(self):
        """Devuelve (puntos_negro, puntos_blanco) usando puntuación por área:
        piedras en el tablero + territorio vacío rodeado por un único color."""
        black_score = 0
        white_score = 0
        visited = set()

        for x in range(self.size):
            for y in range(self.size):
                if self.grid[x][y] == BLACK:
                    black_score += 1
                elif self.grid[x][y] == WHITE:
                    white_score += 1
                elif (x, y) not in visited:
                    region, borders = self._flood_empty(x, y, visited)
                    if borders == {BLACK}:
                        black_score += len(region)
                    elif borders == {WHITE}:
                        white_score += len(region)
                    # si linda con ambos colores (o ninguno) es territorio neutral

        return black_score, white_score

    def _flood_empty(self, x, y, visited):
        stack = [(x, y)]
        region = set()
        borders = set()
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in region:
                continue
            region.add((cx, cy))
            visited.add((cx, cy))
            for nx, ny in self.neighbors(cx, cy):
                val = self.grid[nx][ny]
                if val == EMPTY and (nx, ny) not in region:
                    stack.append((nx, ny))
                elif val != EMPTY:
                    borders.add(val)
        return region, borders

    def winner(self):
        b, w = self.score()
        komi_adjusted_white = w + 6.5  # komi estándar (compensa la ventaja de salir primero)
        if b > komi_adjusted_white:
            return BLACK, b, komi_adjusted_white
        else:
            return WHITE, b, komi_adjusted_white
