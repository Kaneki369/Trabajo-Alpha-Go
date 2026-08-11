"""
go_ai.py
IA para GO basada en Monte Carlo Tree Search (MCTS) puro (sin redes neuronales).

Por qué MCTS y no una réplica de AlphaGo:
------------------------------------------------
AlphaGo (Silver et al., 2016) combina:
  1) una red de política (policy network) entrenada por aprendizaje
     supervisado sobre partidas humanas y luego refinada con
     aprendizaje por refuerzo (self-play),
  2) una red de valor (value network) que estima la probabilidad de
     victoria de una posición,
  3) una búsqueda en árbol Monte Carlo (MCTS) que usa ambas redes
     para guiar y podar la exploración.

Entrenar redes de ese tipo requiere millones de partidas de
autojuego y GPUs/TPUs during días o semanas — inviable como parte de
este ejercicio. Lo que SÍ es totalmente factible y educativo es
implementar el componente de búsqueda (MCTS) que constituye el
"esqueleto" algorítmico de AlphaGo, usando play-outs aleatorios en
lugar de una red de valor entrenada (esto es, de hecho, cómo
funcionaban los programas de Go de nivel amateur fuerte ANTES de
AlphaGo, p. ej. Fuego, Pachi, MoGo).

Esta IA:
- Construye un árbol de búsqueda con selección UCB1.
- Expande nodos con jugadas legales.
- Simula partidas aleatorias hasta el final (o hasta un límite de
  profundidad) para estimar el valor de una posición.
- Retropropaga el resultado (victoria/derrota) por el árbol.
- Elige la jugada con más visitas (criterio estándar en MCTS, más
  robusto que elegir la de mayor win-rate).
"""

import math
import random
import time
from go_logic import GoBoard, BLACK, WHITE, EMPTY


class MCTSNode:
    __slots__ = ("board", "parent", "move", "children", "visits", "wins", "untried_moves", "color_to_move")

    def __init__(self, board, parent=None, move=None):
        self.board = board
        self.parent = parent
        self.move = move  # jugada que llevó a este nodo, None para pass, o (x,y)
        self.children = []
        self.visits = 0
        self.wins = 0.0
        self.color_to_move = board.current_player
        moves = board.legal_moves()
        moves.append(None)  # None representa "pasar"
        self.untried_moves = moves

    def ucb1_score(self, c=1.4142):
        if self.visits == 0:
            return float("inf")
        exploitation = self.wins / self.visits
        exploration = c * math.sqrt(math.log(self.parent.visits) / self.visits)
        return exploitation + exploration

    def best_child(self):
        return max(self.children, key=lambda n: n.ucb1_score())

    def most_visited_child(self):
        return max(self.children, key=lambda n: n.visits)


class MCTSPlayer:
    """
    Jugador de IA. `simulations` controla la fuerza vs. velocidad:
    más simulaciones -> mejor juego, pero más lento. Para 9x9 en
    Python puro, 300-800 simulaciones dan una respuesta en 1-4s
    aproximadamente en hardware moderno.
    """

    def __init__(self, color, simulations=400, max_playout_moves=None, time_limit=None):
        self.color = color
        self.simulations = simulations
        self.max_playout_moves = max_playout_moves
        self.time_limit = time_limit  # segundos, si se prefiere limitar por tiempo

    def choose_move(self, board: GoBoard):
        root = MCTSNode(board.clone())
        max_moves = self.max_playout_moves or (board.size * board.size * 2)

        start = time.time()
        sims_done = 0
        while sims_done < self.simulations:
            if self.time_limit and (time.time() - start) > self.time_limit:
                break
            self._run_one_simulation(root, max_moves)
            sims_done += 1

        if not root.children:
            return None  # no hay jugadas -> pasar

        best = root.most_visited_child()
        return best.move

    def _run_one_simulation(self, root, max_moves):
        node = root

        # 1) Selección: bajar por el árbol mientras no haya jugadas sin probar
        while not node.untried_moves and node.children:
            node = node.best_child()

        # 2) Expansión: probar una jugada nueva
        if node.untried_moves:
            move = node.untried_moves.pop(random.randrange(len(node.untried_moves)))
            child_board = node.board.clone()
            self._apply_move(child_board, move)
            child = MCTSNode(child_board, parent=node, move=move)
            node.children.append(child)
            node = child

        # 3) Simulación (playout aleatorio)
        result_color = self._random_playout(node.board.clone(), max_moves)

        # 4) Retropropagación
        while node is not None:
            node.visits += 1
            # el "wins" se cuenta desde la perspectiva del jugador que
            # mueve en el nodo PADRE (quien eligió esta jugada)
            mover = node.parent.color_to_move if node.parent else None
            if mover is not None and result_color == mover:
                node.wins += 1
            elif mover is not None and result_color != mover and result_color is not None:
                node.wins += 0
            node = node.parent

    def _apply_move(self, board, move):
        if move is None:
            board.pass_move()
        else:
            board.play(*move)

    def _random_playout(self, board, max_moves):
        """Juega aleatoriamente hasta que la partida termina o se alcanza
        max_moves. Optimización clave: en vez de enumerar TODAS las
        jugadas legales en cada paso (costoso, O(n^4)), se muestrean
        puntos vacíos al azar y se intenta jugarlos, con un número
        limitado de intentos antes de pasar. Esto es lo que hace viable
        MCTS en Python puro sobre tableros 9x9/13x13."""
        moves_played = 0
        n = board.size
        while not board.game_over and moves_played < max_moves:
            empties = [(x, y) for x in range(n) for y in range(n) if board.grid[x][y] == EMPTY]
            random.shuffle(empties)
            played = False
            for x, y in empties[:12]:  # probar como máx. 12 candidatos al azar
                if self._is_obvious_own_eye(board, (x, y)):
                    continue
                try:
                    board.play(x, y)
                    played = True
                    break
                except Exception:
                    continue
            if not played:
                board.pass_move()
            moves_played += 1

        black_score, white_score = board.score()
        white_adjusted = white_score + 6.5
        return BLACK if black_score > white_adjusted else WHITE

    def _is_obvious_own_eye(self, board, move):
        """Heurística simple: evita rellenar un punto rodeado en las 4
        direcciones por piedras propias (probable 'ojo' propio), lo cual
        casi nunca es una buena jugada y acelera/mejora los playouts."""
        x, y = move
        color = board.current_player
        neigh = list(board.neighbors(x, y))
        if len(neigh) < 2:
            return False
        return all(board.grid[nx][ny] == color for nx, ny in neigh)


class RandomPlayer:
    """IA trivial de referencia: juega una jugada legal al azar.
    Se usa como línea base en el análisis de rendimiento."""

    def __init__(self, color):
        self.color = color

    def choose_move(self, board: GoBoard):
        moves = board.legal_moves()
        if not moves:
            return None
        return random.choice(moves)
