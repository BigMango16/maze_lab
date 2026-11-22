"""benchmark.py - сравнително изследване на алгоритмите за търсене на път.

Пускане:  python benchmark.py
Резултатите се записват в папка results/ като CSV файлове и графики (PNG).
Всички експерименти ползват фиксирани seed стойности -> повторяеми са.

Експерименти:
  1. Мащабиране - как растат разширените клетки и времето с размера.
  2. Плътност на препятствията - колко често има път и колко струва търсенето.
  3. Кал (различни цени) - колко пъти BFS и Greedy дават по-скъп път.
  4. Генератори - как видът на лабиринта влияе върху търсенето.
"""
import csv
import os
import random
import statistics as st

from algorithms import ALGORITHMS, run
from generators import (recursive_backtracker, randomized_prim, kruskal,
                        random_obstacles, add_loops, add_mud)

OUT = "results"
REPS = 30                    # повторения за всяка точка
NAMES = list(ALGORITHMS)


def ends(g):
    return (1, 1), (g.w - 2, g.h - 2)


def write_csv(name, header, rows):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def exp_scaling():
    """Експеримент 1: размер на лабиринта (с 10% цикли)."""
    rows = []
    for size in (21, 41, 61, 81, 101, 141):
        acc = {n: {"exp": [], "ms": [], "steps": []} for n in NAMES}
        for seed in range(REPS):
            rng = random.Random(seed)
            g = add_loops(recursive_backtracker(size, size, rng), 0.10, rng)
            s, t = ends(g)
            for n in NAMES:
                state, ms = run(n, g, s, t)
                acc[n]["exp"].append(state.expanded_count)
                acc[n]["ms"].append(ms)
                acc[n]["steps"].append(state.steps)
        for n in NAMES:
            rows.append([size, n, round(st.mean(acc[n]["exp"]), 1),
                         round(st.mean(acc[n]["ms"]), 3),
                         round(st.mean(acc[n]["steps"]), 1)])
    write_csv("scaling.csv", ["size", "algorithm", "expanded", "ms", "path_steps"], rows)
    return rows


def exp_density():
    """Експеримент 2: плътност на препятствията (51x51)."""
    rows = []
    for dens in (0.10, 0.20, 0.30, 0.35, 0.40, 0.45):
        acc = {n: {"exp": [], "found": 0} for n in NAMES}
        for seed in range(REPS):
            rng = random.Random(1000 + seed)
            g = random_obstacles(51, 51, dens, rng)
            s, t = ends(g)
            for n in NAMES:
                state, _ = run(n, g, s, t)
                acc[n]["exp"].append(state.expanded_count)
                acc[n]["found"] += state.found
        for n in NAMES:
            rows.append([dens, n, round(st.mean(acc[n]["exp"]), 1),
                         round(100 * acc[n]["found"] / REPS, 1)])
    write_csv("density.csv", ["density", "algorithm", "expanded", "found_percent"], rows)
    return rows


def exp_mud():
    """Експеримент 3: кал. Колко % по-скъп е пътят спрямо Dijkstra."""
    rows = []
    for patches in (0, 4, 8, 16, 24):
        extra = {n: [] for n in NAMES}
        subopt = {n: 0 for n in NAMES}
        for seed in range(REPS):
            rng = random.Random(2000 + seed)
            g = add_loops(recursive_backtracker(61, 61, rng), 0.25, rng)
            add_mud(g, patches, 4, rng)
            s, t = ends(g)
            best = run("Dijkstra", g, s, t)[0].cost
            for n in NAMES:
                c = run(n, g, s, t)[0].cost
                extra[n].append(100.0 * (c - best) / best)
                subopt[n] += c > best
        for n in NAMES:
            rows.append([patches, n, round(st.mean(extra[n]), 2),
                         round(100 * subopt[n] / REPS, 1)])
    write_csv("mud.csv", ["mud_patches", "algorithm", "extra_cost_percent", "suboptimal_percent"], rows)
    return rows


def exp_generators():
    """Експеримент 4: видове генератори (61x61, 10% цикли)."""
    gens = {"Backtracker": recursive_backtracker, "Prim": randomized_prim, "Kruskal": kruskal}
    rows = []
    for gname, gen in gens.items():
        acc = {n: {"exp": [], "steps": []} for n in NAMES}
        for seed in range(REPS):
            rng = random.Random(3000 + seed)
            g = add_loops(gen(61, 61, rng), 0.10, rng)
            s, t = ends(g)
            for n in NAMES:
                state, _ = run(n, g, s, t)
                acc[n]["exp"].append(state.expanded_count)
                acc[n]["steps"].append(state.steps)
        for n in NAMES:
            rows.append([gname, n, round(st.mean(acc[n]["exp"]), 1),
                         round(st.mean(acc[n]["steps"]), 1)])
    write_csv("generators.csv", ["generator", "algorithm", "expanded", "path_steps"], rows)
    return rows


def plot_all(scaling, density, mud, gens):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib не е инсталиран - графиките се пропускат (pip install matplotlib)")
        return
    colors = {"BFS": "#4c8bf5", "DFS": "#e8710a", "Dijkstra": "#9334e6",
              "A*": "#188038", "Greedy": "#d93025"}

    def lines(ax, rows, xi, yi, xlabel, ylabel, title, log=False):
        for n in NAMES:
            pts = [(r[xi], r[yi]) for r in rows if r[1] == n]
            ax.plot(*zip(*pts), marker="o", label=n, color=colors[n], lw=2)
        ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title)
        ax.grid(alpha=.3); ax.legend()
        if log:
            ax.set_yscale("log")

    fig, ax = plt.subplots(figsize=(7, 4.2))
    lines(ax, scaling, 0, 2, "Страна на лабиринта (клетки)", "Средно разширени клетки",
          "Експеримент 1: разширени клетки спрямо размера")
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_scaling_expanded.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.2))
    lines(ax, scaling, 0, 3, "Страна на лабиринта (клетки)", "Средно време (ms)",
          "Експеримент 1: време спрямо размера")
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_scaling_time.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.2))
    lines(ax, density, 0, 2, "Плътност на препятствията", "Средно разширени клетки",
          "Експеримент 2: плътност на препятствията")
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_density_expanded.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.2))
    lines(ax, density, 0, 3, "Плътност на препятствията", "% случаи с намерен път",
          "Експеримент 2: има ли път изобщо")
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_density_found.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.2))
    lines(ax, mud, 0, 2, "Брой петна кал", "Среден % по-скъп път от оптималния",
          "Експеримент 3: цена на пътя при кал")
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_mud.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.2))
    gnames = ["Backtracker", "Prim", "Kruskal"]
    wdt = 0.16
    for i, n in enumerate(NAMES):
        vals = [next(r[2] for r in gens if r[0] == g and r[1] == n) for g in gnames]
        ax.bar([k + (i - 2) * wdt for k in range(3)], vals, wdt, label=n, color=colors[n])
    ax.set_xticks(range(3)); ax.set_xticklabels(gnames)
    ax.set_ylabel("Средно разширени клетки"); ax.set_title("Експеримент 4: генератори")
    ax.legend(); ax.grid(alpha=.3, axis="y")
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_generators.png", dpi=150); plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    print("Експеримент 1/4: мащабиране..."); sc = exp_scaling()
    print("Експеримент 2/4: плътност...");   de = exp_density()
    print("Експеримент 3/4: кал...");        mu = exp_mud()
    print("Експеримент 4/4: генератори..."); ge = exp_generators()
    plot_all(sc, de, mu, ge)
    print("Готово. Виж папка", OUT)


if __name__ == "__main__":
    main()
