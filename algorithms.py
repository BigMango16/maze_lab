"""algorithms.py - алгоритми за търсене на път в решетка.

Всеки алгоритъм е написан като генератор: след всяко "разширяване" на
клетка прави yield. Така графичното приложение може да го изпълнява
стъпка по стъпка (анимация), а бенчмаркът - наведнъж.

Реализирани алгоритми:
    BFS      - търсене в ширина (най-кратък път по брой стъпки);
    DFS      - търсене в дълбочина (намира път, но не непременно кратък);
    Dijkstra - най-евтин път при различни цени на клетките;
    A*       - Dijkstra + евристика (Манхатъново разстояние);
    Greedy   - алчно търсене само по евристиката (бързо, но неоптимално).
"""
import heapq
import time
from collections import deque
from itertools import count


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class SearchState:
    """Текущо състояние на търсенето (използва се и от анимацията)."""

    def __init__(self, name):
        self.name = name
        self.expanded = []        # клетки по реда на разширяване
        self.frontier = set()     # клетки, чакащи за разглеждане
        self.parent = {}          # за възстановяване на пътя
        self.done = False
        self.found = False
        self.path = []
        self.cost = 0             # сума от цените на клетките по пътя
        self.steps = 0            # брой стъпки по пътя

    @property
    def expanded_count(self):
        return len(self.expanded)


def _finish(state, grid, start, goal):
    state.done = True
    if goal in state.parent or goal == start:
        state.found = True
        path = [goal]
        while path[-1] != start:
            path.append(state.parent[path[-1]])
        path.reverse()
        state.path = path
        state.steps = len(path) - 1
        state.cost = sum(grid.cost(c) for c in path[1:])


def _bfs(grid, start, goal, st):
    queue = deque([start])
    seen = {start}
    st.frontier.add(start)
    while queue:
        cur = queue.popleft()
        st.frontier.discard(cur)
        st.expanded.append(cur)
        yield
        if cur == goal:
            return
        for nb in grid.neighbors(cur):
            if nb not in seen:
                seen.add(nb)
                st.parent[nb] = cur
                queue.append(nb)
                st.frontier.add(nb)


def _dfs(grid, start, goal, st):
    stack = [(start, None)]
    visited = set()
    st.frontier.add(start)
    while stack:
        cur, par = stack.pop()
        if cur in visited:
            continue
        visited.add(cur)
        if par is not None:
            st.parent[cur] = par
        st.frontier.discard(cur)
        st.expanded.append(cur)
        yield
        if cur == goal:
            return
        for nb in grid.neighbors(cur):
            if nb not in visited:
                stack.append((nb, cur))
                st.frontier.add(nb)


def _dijkstra(grid, start, goal, st):
    tie = count()
    dist = {start: 0}
    heap = [(0, next(tie), start)]
    closed = set()
    st.frontier.add(start)
    while heap:
        d, _, cur = heapq.heappop(heap)
        if cur in closed:
            continue
        closed.add(cur)
        st.frontier.discard(cur)
        st.expanded.append(cur)
        yield
        if cur == goal:
            return
        for nb in grid.neighbors(cur):
            nd = d + grid.cost(nb)
            if nb not in dist or nd < dist[nb]:
                dist[nb] = nd
                st.parent[nb] = cur
                heapq.heappush(heap, (nd, next(tie), nb))
                st.frontier.add(nb)


def _astar(grid, start, goal, st):
    tie = count()
    g = {start: 0}
    heap = [(manhattan(start, goal), manhattan(start, goal), next(tie), start)]
    closed = set()
    st.frontier.add(start)
    while heap:
        _, _, _, cur = heapq.heappop(heap)
        if cur in closed:
            continue
        closed.add(cur)
        st.frontier.discard(cur)
        st.expanded.append(cur)
        yield
        if cur == goal:
            return
        for nb in grid.neighbors(cur):
            ng = g[cur] + grid.cost(nb)
            if nb not in g or ng < g[nb]:
                g[nb] = ng
                st.parent[nb] = cur
                h = manhattan(nb, goal)
                # при равно f се предпочита клетка с по-малко h (по-близо до целта)
                heapq.heappush(heap, (ng + h, h, next(tie), nb))
                st.frontier.add(nb)


def _greedy(grid, start, goal, st):
    tie = count()
    heap = [(manhattan(start, goal), next(tie), start)]
    seen = {start}
    st.frontier.add(start)
    while heap:
        _, _, cur = heapq.heappop(heap)
        st.frontier.discard(cur)
        st.expanded.append(cur)
        yield
        if cur == goal:
            return
        for nb in grid.neighbors(cur):
            if nb not in seen:
                seen.add(nb)
                st.parent[nb] = cur
                heapq.heappush(heap, (manhattan(nb, goal), next(tie), nb))
                st.frontier.add(nb)


ALGORITHMS = {
    "BFS": _bfs,
    "DFS": _dfs,
    "Dijkstra": _dijkstra,
    "A*": _astar,
    "Greedy": _greedy,
}

# Кратко описание, показвано в приложението
DESCRIPTIONS = {
    "BFS": "Ширина: най-кратък по стъпки",
    "DFS": "Дълбочина: бърз, но дълъг път",
    "Dijkstra": "Най-евтин път, търси навсякъде",
    "A*": "Dijkstra + посока към целта",
    "Greedy": "Само евристика: бърз, но грешен",
}


class Searcher:
    """Обвивка, която върши търсенето стъпка по стъпка."""

    def __init__(self, name, grid, start, goal):
        self.grid, self.start, self.goal = grid, start, goal
        self.state = SearchState(name)
        self._gen = ALGORITHMS[name](grid, start, goal, self.state)

    def step(self):
        """Едно разширяване. Връща False, когато търсенето е приключило."""
        if self.state.done:
            return False
        try:
            next(self._gen)
            return True
        except StopIteration:
            _finish(self.state, self.grid, self.start, self.goal)
            return False

    def run_all(self):
        while self.step():
            pass
        return self.state


def run(name, grid, start, goal):
    """Изпълнява алгоритъм докрай. Връща (състояние, време в милисекунди)."""
    t0 = time.perf_counter()
    state = Searcher(name, grid, start, goal).run_all()
    return state, (time.perf_counter() - t0) * 1000.0
