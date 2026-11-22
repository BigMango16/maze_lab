"""generators.py - алгоритми за генериране на лабиринти.

Всички лабиринти имат нечетни размери: клетките с нечетни координати са
"стаи", а клетките между тях са стени, които се събарят.
"""
import random

from grid import Grid, WALL, FLOOR, MUD

# Стъпка от две клетки (стая -> съседна стая)
STEPS = ((0, -2), (2, 0), (0, 2), (-2, 0))


def _odd(n):
    return n if n % 2 == 1 else n + 1


def _empty_walls(w, h):
    return Grid(_odd(w), _odd(h), fill=WALL)


def _carve_between(g, a, b):
    """Събаря стената между две стаи a и b."""
    g.set((a[0] + b[0]) // 2, (a[1] + b[1]) // 2, FLOOR)
    g.set(*b, FLOOR)


def recursive_backtracker(w, h, rng=None):
    """DFS генератор: дълги криволичещи коридори."""
    rng = rng or random.Random()
    g = _empty_walls(w, h)
    start = (1, 1)
    g.set(*start, FLOOR)
    stack = [start]
    while stack:
        x, y = stack[-1]
        options = []
        for dx, dy in STEPS:
            nx, ny = x + dx, y + dy
            if 0 < nx < g.w - 1 and 0 < ny < g.h - 1 and g.get(nx, ny) == WALL:
                options.append((nx, ny))
        if options:
            nxt = rng.choice(options)
            _carve_between(g, (x, y), nxt)
            stack.append(nxt)
        else:
            stack.pop()
    return g


def randomized_prim(w, h, rng=None):
    """Алгоритъм на Прим: много къси задънени улици, "храстовиден" вид."""
    rng = rng or random.Random()
    g = _empty_walls(w, h)
    g.set(1, 1, FLOOR)
    frontier = []

    def add_frontier(x, y):
        for dx, dy in STEPS:
            nx, ny = x + dx, y + dy
            if 0 < nx < g.w - 1 and 0 < ny < g.h - 1 and g.get(nx, ny) == WALL:
                frontier.append(((x, y), (nx, ny)))

    add_frontier(1, 1)
    while frontier:
        i = rng.randrange(len(frontier))
        frontier[i], frontier[-1] = frontier[-1], frontier[i]
        src, dst = frontier.pop()
        if g.get(*dst) == WALL:
            _carve_between(g, src, dst)
            add_frontier(*dst)
    return g


def kruskal(w, h, rng=None):
    """Алгоритъм на Крускал със структура Union-Find."""
    rng = rng or random.Random()
    g = _empty_walls(w, h)
    rooms = [(x, y) for y in range(1, g.h, 2) for x in range(1, g.w, 2)]
    for r in rooms:
        g.set(*r, FLOOR)
    parent = {r: r for r in rooms}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]  # компресия на пътя
            a = parent[a]
        return a

    edges = []
    for (x, y) in rooms:
        if x + 2 < g.w:
            edges.append(((x, y), (x + 2, y)))
        if y + 2 < g.h:
            edges.append(((x, y), (x, y + 2)))
    rng.shuffle(edges)
    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
            _carve_between(g, a, b)
    return g


def random_obstacles(w, h, density=0.28, rng=None):
    """Отворено поле със случайни препятствия (не е "перфектен" лабиринт)."""
    rng = rng or random.Random()
    g = Grid(_odd(w), _odd(h))
    for y in range(g.h):
        for x in range(g.w):
            if rng.random() < density:
                g.set(x, y, WALL)
    g.set(1, 1, FLOOR)
    g.set(g.w - 2, g.h - 2, FLOOR)
    return g


def add_loops(g, fraction=0.1, rng=None):
    """Премахва част от вътрешните стени, за да се появят цикли.

    В "перфектен" лабиринт има само един път между две клетки и всички
    алгоритми намират един и същ път. С цикли има алтернативи и алгоритмите
    започват да се различават по качеството на пътя.
    """
    rng = rng or random.Random()
    candidates = []
    for y in range(1, g.h - 1):
        for x in range(1, g.w - 1):
            if g.get(x, y) != WALL:
                continue
            horiz = g.get(x - 1, y) != WALL and g.get(x + 1, y) != WALL
            vert = g.get(x, y - 1) != WALL and g.get(x, y + 1) != WALL
            if horiz or vert:
                candidates.append((x, y))
    rng.shuffle(candidates)
    for x, y in candidates[:int(len(candidates) * fraction)]:
        g.set(x, y, FLOOR)
    return g


def add_mud(g, patches=6, radius=3, rng=None):
    """Добавя кръгли петна "кал" (цена 5) - за взвешени графи."""
    rng = rng or random.Random()
    for _ in range(patches):
        cx, cy = rng.randrange(g.w), rng.randrange(g.h)
        for y in range(max(0, cy - radius), min(g.h, cy + radius + 1)):
            for x in range(max(0, cx - radius), min(g.w, cx + radius + 1)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2 and g.get(x, y) == FLOOR:
                    g.set(x, y, MUD)
    return g


GENERATORS = {
    "Backtracker": recursive_backtracker,
    "Prim": randomized_prim,
    "Kruskal": kruskal,
    "Случаен": random_obstacles,
}
