"""Автоматични тестове (unittest). Пускане:  python -m unittest -v"""
import random
import unittest

from grid import Grid, WALL, MUD
from generators import (recursive_backtracker, randomized_prim, kruskal,
                        random_obstacles, add_loops, add_mud)
from algorithms import ALGORITHMS, run


def reachable(g, start):
    seen, stack = {start}, [start]
    while stack:
        for nb in g.neighbors(stack.pop()):
            if nb not in seen:
                seen.add(nb)
                stack.append(nb)
    return seen


class TestGenerators(unittest.TestCase):
    def test_perfect_mazes_are_spanning_trees(self):
        # В перфектен лабиринт всички свободни клетки са свързани и
        # няма цикли: ребрата = клетките - 1.
        for gen in (recursive_backtracker, randomized_prim, kruskal):
            for seed in range(5):
                g = gen(21, 15, random.Random(seed))
                free = [(x, y) for y in range(g.h) for x in range(g.w)
                        if g.get(x, y) != WALL]
                edges = sum(len(list(g.neighbors(c))) for c in free) // 2
                self.assertEqual(len(reachable(g, (1, 1))), len(free), gen.__name__)
                self.assertEqual(edges, len(free) - 1, gen.__name__)

    def test_odd_dimensions(self):
        g = recursive_backtracker(20, 10)
        self.assertEqual((g.w % 2, g.h % 2), (1, 1))

    def test_loops_add_cycles(self):
        g = recursive_backtracker(21, 15, random.Random(1))
        before = g.free_count()
        add_loops(g, 0.3, random.Random(2))
        self.assertGreater(g.free_count(), before)


class TestAlgorithms(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(42)

    def test_all_find_path_in_perfect_maze(self):
        g = kruskal(25, 25, self.rng)
        s, t = (1, 1), (g.w - 2, g.h - 2)
        for name in ALGORITHMS:
            st, _ = run(name, g, s, t)
            self.assertTrue(st.found, name)
            self.assertEqual(st.path[0], s)
            self.assertEqual(st.path[-1], t)

    def test_path_is_valid(self):
        g = add_loops(recursive_backtracker(31, 21, self.rng), 0.2, self.rng)
        s, t = (1, 1), (g.w - 2, g.h - 2)
        for name in ALGORITHMS:
            st, _ = run(name, g, s, t)
            for a, b in zip(st.path, st.path[1:]):
                self.assertEqual(abs(a[0] - b[0]) + abs(a[1] - b[1]), 1)
                self.assertNotEqual(g.get(*b), WALL)

    def test_optimal_algorithms_agree_unweighted(self):
        for seed in range(15):
            rng = random.Random(seed)
            g = add_loops(recursive_backtracker(31, 21, rng), 0.15, rng)
            s, t = (1, 1), (g.w - 2, g.h - 2)
            steps = {n: run(n, g, s, t)[0].steps for n in ("BFS", "Dijkstra", "A*")}
            self.assertEqual(len(set(steps.values())), 1, steps)

    def test_dijkstra_equals_astar_weighted_and_bfs_not_better(self):
        for seed in range(15):
            rng = random.Random(seed)
            g = add_mud(add_loops(recursive_backtracker(31, 21, rng), 0.3, rng), 8, 3, rng)
            s, t = (1, 1), (g.w - 2, g.h - 2)
            d = run("Dijkstra", g, s, t)[0].cost
            a = run("A*", g, s, t)[0].cost
            b = run("BFS", g, s, t)[0].cost
            self.assertEqual(d, a)
            self.assertGreaterEqual(b, d)

    def test_astar_expands_not_more_than_dijkstra_on_open_grid(self):
        g = Grid(41, 41)
        s, t = (0, 0), (40, 40)
        a = run("A*", g, s, t)[0].expanded_count
        d = run("Dijkstra", g, s, t)[0].expanded_count
        self.assertLess(a, d)

    def test_no_path(self):
        g = Grid(9, 9)
        for y in range(9):
            g.set(4, y, WALL)           # плътна стена по средата
        for name in ALGORITHMS:
            st, _ = run(name, g, (0, 0), (8, 8))
            self.assertTrue(st.done)
            self.assertFalse(st.found, name)
            self.assertEqual(st.path, [])

    def test_start_equals_goal(self):
        g = Grid(5, 5)
        for name in ALGORITHMS:
            st, _ = run(name, g, (2, 2), (2, 2))
            self.assertTrue(st.found)
            self.assertEqual(st.steps, 0)

    def test_greedy_never_better_than_optimal(self):
        for seed in range(15):
            rng = random.Random(seed)
            g = random_obstacles(31, 21, 0.25, rng)
            s, t = (1, 1), (g.w - 2, g.h - 2)
            opt = run("Dijkstra", g, s, t)[0]
            gr = run("Greedy", g, s, t)[0]
            self.assertEqual(opt.found, gr.found)
            if opt.found:
                self.assertGreaterEqual(gr.cost, opt.cost)


class TestSaveLoad(unittest.TestCase):
    def test_roundtrip(self):
        import os, tempfile
        g = add_mud(kruskal(15, 11, random.Random(3)), 3, 2, random.Random(4))
        path = os.path.join(tempfile.mkdtemp(), "m.json")
        g.save(path, (1, 1), (13, 9))
        g2, s, t = Grid.load(path)
        self.assertEqual(g.cells, g2.cells)
        self.assertEqual((s, t), ((1, 1), (13, 9)))


if __name__ == "__main__":
    unittest.main()
