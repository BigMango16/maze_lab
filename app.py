"""app.py - Maze Lab: интерактивен визуализатор на алгоритми за търсене на път.

Управление (има и бутони вдясно):
  Ляв бутон   - рисува с избрания инструмент (стена / кал)
  Десен бутон - трие
  Влачене на зеленото (старт) и червеното (цел) ги премества
  ИНТЕРВАЛ    - старт/пауза      N - една стъпка     R - рестарт на търсенето
  G           - нов лабиринт     C - изчисти         T - състезание (всички алгоритми)
  1-5         - избор на алгоритъм
  S / L       - запис / зареждане (maze.json)
  +/-         - скорост           ESC - изход от състезание / от програмата
"""
import os
import random
import sys
import time

import pygame

from algorithms import ALGORITHMS, DESCRIPTIONS, Searcher, run
from generators import GENERATORS, add_loops, add_mud
from grid import Grid, WALL, FLOOR, MUD

WIN_W, WIN_H = 1280, 760
AREA = pygame.Rect(15, 15, 905, 730)       # зона за решетката
PANEL_X = 940                              # лява граница на страничния панел

# ---------- цветове (тъмна тема) ----------
BG = (18, 20, 28)
CARD = (28, 32, 44)
FLOOR_C = (40, 45, 60)
WALL_C = (10, 11, 16)
MUD_C = (112, 78, 48)
FRONT_C = (92, 230, 140)
PATH_C = (255, 213, 74)
START_C = (60, 220, 120)
GOAL_C = (255, 85, 95)
TEXT = (232, 235, 245)
MUTED = (140, 148, 170)
ACCENT = (96, 140, 255)
ALGO_COLORS = {"BFS": (76, 139, 245), "DFS": (232, 113, 10), "Dijkstra": (147, 52, 230),
               "A*": (24, 160, 80), "Greedy": (217, 48, 37)}

SIZES = {"S": (21, 15), "M": (41, 31), "L": (61, 45)}


def make_font(size, bold=False):
    return pygame.font.SysFont("segoeui,arial,dejavusans,liberationsans,freesans", size, bold=bold)


def gradient(t):
    """Цвят за разширена клетка: t в [0,1] - от тъмно лилаво през синьо към циан."""
    t = max(0.0, min(1.0, t))
    stops = [(70, 30, 120), (50, 80, 200), (40, 190, 220)]
    a, b, u = (stops[0], stops[1], t * 2) if t < 0.5 else (stops[1], stops[2], (t - 0.5) * 2)
    return tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3))


class Button:
    def __init__(self, rect, label, action, group=None, color=ACCENT):
        self.rect = pygame.Rect(rect)
        self.label, self.action, self.group, self.color = label, action, group, color
        self.active = False

    def draw(self, surf, font, hover):
        col = self.color if self.active else (52, 58, 78)
        if hover and not self.active:
            col = (68, 76, 100)
        pygame.draw.rect(surf, col, self.rect, border_radius=8)
        img = font.render(self.label, True, TEXT)
        surf.blit(img, img.get_rect(center=self.rect.center))


class View:
    """Рисува решетка в правоъгълник. Пази кеширани слоеве за скорост."""

    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self.cell = 1
        self.ox = self.oy = 0
        self.base = self.vis = None
        self.drawn = 0          # колко от разширените клетки са нарисувани

    def layout(self, grid):
        self.cell = max(2, min(self.rect.w // grid.w, self.rect.h // grid.h))
        self.ox = self.rect.x + (self.rect.w - self.cell * grid.w) // 2
        self.oy = self.rect.y + (self.rect.h - self.cell * grid.h) // 2

    def to_cell(self, pos):
        x = (pos[0] - self.ox) // self.cell
        y = (pos[1] - self.oy) // self.cell
        return (x, y)

    def px(self, c):
        return (self.ox + c[0] * self.cell, self.oy + c[1] * self.cell)

    def rebuild(self, grid):
        self.layout(grid)
        size = (self.cell * grid.w, self.cell * grid.h)
        self.base = pygame.Surface(size)
        self.base.fill(FLOOR_C)
        gap = 1 if self.cell >= 6 else 0
        for y in range(grid.h):
            for x in range(grid.w):
                v = grid.get(x, y)
                if v == FLOOR:
                    continue
                col = WALL_C if v == WALL else MUD_C
                pygame.draw.rect(self.base, col, (x * self.cell, y * self.cell,
                                                  self.cell - gap, self.cell - gap))
        if gap:   # тънка решетка по светлите клетки
            for y in range(grid.h):
                for x in range(grid.w):
                    if grid.get(x, y) == FLOOR:
                        pygame.draw.rect(self.base, (34, 39, 53),
                                         (x * self.cell + self.cell - 1, y * self.cell, 1, self.cell))
        self.reset_vis(grid)

    def reset_vis(self, grid):
        self.vis = pygame.Surface((self.cell * grid.w, self.cell * grid.h), pygame.SRCALPHA)
        self.drawn = 0

    def sync(self, state, total):
        gap = 1 if self.cell >= 6 else 0
        while self.drawn < len(state.expanded):
            c = state.expanded[self.drawn]
            col = gradient(self.drawn / max(1, total * 0.9))
            pygame.draw.rect(self.vis, col, (c[0] * self.cell, c[1] * self.cell,
                                             self.cell - gap, self.cell - gap))
            self.drawn += 1

    def draw(self, surf, grid, state, start, goal, path_shown=0):
        surf.blit(self.base, (self.ox, self.oy))
        surf.blit(self.vis, (self.ox, self.oy))
        gap = 1 if self.cell >= 6 else 0
        if state is not None:
            for c in state.frontier:
                p = self.px(c)
                pygame.draw.rect(surf, FRONT_C, (p[0], p[1], self.cell - gap, self.cell - gap))
            for c in state.path[:path_shown]:
                p = self.px(c)
                pygame.draw.rect(surf, PATH_C, (p[0], p[1], self.cell - gap, self.cell - gap))
        for c, col in ((start, START_C), (goal, GOAL_C)):
            p = self.px(c)
            r = pygame.Rect(p[0], p[1], self.cell, self.cell)
            pygame.draw.rect(surf, col, r.inflate(self.cell // 3, self.cell // 3), border_radius=4)
            pygame.draw.rect(surf, (255, 255, 255), r.inflate(self.cell // 3, self.cell // 3), 1, border_radius=4)


class App:
    def __init__(self, headless=False):
        pygame.init()
        pygame.display.set_caption("Maze Lab - визуализатор на алгоритми за търсене на път")
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        self.clock = pygame.time.Clock()
        self.f_title = make_font(26, True)
        self.f_h = make_font(15, True)
        self.f = make_font(15)
        self.f_s = make_font(13)
        self.rng = random.Random()
        self.running = True

        self.size_key = "M"
        self.algo = "A*"
        self.gen_name = "Backtracker"
        self.tool = WALL
        self.speed = 0.55           # плъзгач 0..1
        self.loops = True
        self.mud_on = False

        self.view = View(AREA)
        self.mode = "single"        # или "race"
        self.playing = False
        self.acc = 0.0
        self.searcher = None
        self.final = None           # (брой разширени, ms) за текущото търсене
        self.path_shown = 0
        self.dragging = None        # "start" / "goal" / "paint" / "erase"
        self.race = []              # списък от (име, Searcher, View, final)
        self.race_order = []
        self.message = ""
        self.message_t = 0
        self.slider_rect = pygame.Rect(PANEL_X + 20, 586, 290, 14)
        self.build_buttons()
        self.new_maze()

    # ---------------- интерфейс ----------------
    def build_buttons(self):
        self.buttons = []
        x0, w = PANEL_X + 20, 290

        def row(y, labels, group, actions, cols, h=28):
            gap = 5
            bw = (w - gap * (cols - 1)) // cols
            for i, (lab, act) in enumerate(zip(labels, actions)):
                r = (x0 + (i % cols) * (bw + gap), y + (i // cols) * (h + gap), bw, h)
                col = ALGO_COLORS.get(lab, ACCENT) if group == "algo" else ACCENT
                b = Button(r, lab, act, group, col)
                b.key = lab
                self.buttons.append(b)

        algos = list(ALGORITHMS)
        row(102, algos, "algo", [lambda n=n: self.set_algo(n) for n in algos], 3)
        gens = list(GENERATORS)
        row(190, gens, "gen", [lambda n=n: self.set_gen(n) for n in gens], 2)
        row(276, ["Стена", "Кал", "Цикли", "Кал в лаб."], "tool",
            [lambda: self.set_tool(WALL), lambda: self.set_tool(MUD),
             self.toggle_loops, self.toggle_mud], 2)
        row(362, list(SIZES), "size", [lambda k=k: self.set_size(k) for k in SIZES], 3)
        row(414, ["▶ Старт / Пауза", "Стъпка", "Рестарт", "Нов лабиринт"], None,
            [self.toggle_play, self.single_step, self.restart, self.new_maze], 2, 32)
        row(492, ["Състезание (T)", "Изчисти", "Запази", "Зареди"], None,
            [self.toggle_race, self.clear_grid, self.save, self.load], 2, 28)

    def sync_buttons(self):
        for b in self.buttons:
            if b.group == "algo":
                b.active = b.key == self.algo
            elif b.group == "gen":
                b.active = b.key == self.gen_name
            elif b.group == "size":
                b.active = b.key == self.size_key
            elif b.group == "tool":
                b.active = ((b.key == "Стена" and self.tool == WALL) or
                            (b.key == "Кал" and self.tool == MUD) or
                            (b.key == "Цикли" and self.loops) or
                            (b.key == "Кал в лаб." and self.mud_on))
            elif b.label.startswith("Състезание"):
                b.active = self.mode == "race"

    def set_algo(self, n):
        self.algo = n
        self.restart()

    def set_gen(self, n):
        self.gen_name = n
        self.new_maze()

    def set_tool(self, t):
        self.tool = t

    def set_size(self, k):
        self.size_key = k
        self.new_maze()

    def toggle_loops(self):
        self.loops = not self.loops
        self.new_maze()

    def toggle_mud(self):
        self.mud_on = not self.mud_on
        self.new_maze()

    def flash(self, text):
        self.message, self.message_t = text, time.time()

    # ---------------- логика ----------------
    def new_maze(self):
        w, h = SIZES[self.size_key]
        gen = GENERATORS[self.gen_name]
        g = gen(w, h, self.rng)
        if self.loops and self.gen_name != "Случаен":
            add_loops(g, 0.12, self.rng)
        if self.mud_on:
            add_mud(g, max(3, g.w * g.h // 250), 3, self.rng)
        self.grid = g
        self.start, self.goal = (1, 1), (g.w - 2, g.h - 2)
        self.mode = "single"
        self.grid_changed()

    def clear_grid(self):
        self.grid.clear()
        self.mode = "single"
        self.grid_changed()

    def grid_changed(self):
        """Извиква се при всяка промяна на решетката."""
        self.view.rebuild(self.grid)
        self.searcher = None
        self.final = None
        self.path_shown = 0
        self.playing = False
        self.race = []
        if self.mode == "race":
            self.start_race()

    def restart(self):
        if self.mode == "race":
            self.start_race()
            return
        self.searcher = None
        self.final = None
        self.path_shown = 0
        self.playing = False
        self.view.reset_vis(self.grid)

    def ensure_searcher(self):
        if self.searcher is None:
            self.view.reset_vis(self.grid)
            self.searcher = Searcher(self.algo, self.grid.copy(), self.start, self.goal)
            st, ms = run(self.algo, self.grid, self.start, self.goal)
            self.final = (st.expanded_count, ms)
            self.path_shown = 0

    def toggle_play(self):
        if self.mode == "race":
            self.playing = not self.playing
            return
        self.ensure_searcher()
        if self.searcher.state.done:
            self.restart()
            self.ensure_searcher()
        self.playing = not self.playing

    def single_step(self):
        if self.mode == "race":
            self.advance_race(1)
            return
        self.ensure_searcher()
        self.playing = False
        self.searcher.step()

    def rate(self):
        """Разширявания в секунда (експоненциално от плъзгача)."""
        return 4 * (900 ** self.speed)

    # ---------- състезание ----------
    def toggle_race(self):
        if self.mode == "race":
            self.mode = "single"
            self.race = []
            self.playing = False
            return
        self.mode = "race"
        self.start_race()

    def start_race(self):
        self.race, self.race_order = [], []
        self.playing = False
        pw, ph = AREA.w // 3, AREA.h // 2
        for i, name in enumerate(ALGORITHMS):
            rect = pygame.Rect(AREA.x + (i % 3) * pw + 4, AREA.y + (i // 3) * ph + 30, pw - 8, ph - 38)
            v = View(rect)
            v.rebuild(self.grid)
            st, ms = run(name, self.grid, self.start, self.goal)
            self.race.append({"name": name, "s": Searcher(name, self.grid.copy(), self.start, self.goal),
                              "view": v, "ms": ms, "final": st, "shown": 0, "rank": None})

    def advance_race(self, n):
        for _ in range(n):
            for r in self.race:
                if not r["s"].state.done:
                    r["s"].step()
                    if r["s"].state.done:
                        r["rank"] = 1 + sum(1 for q in self.race if q["rank"] is not None)

    def update(self, dt):
        if self.mode == "race":
            if self.playing and self.race:
                self.acc += self.rate() * dt
                n = int(self.acc)
                self.acc -= n
                self.advance_race(min(n, 400))
            for r in self.race:
                st = r["s"].state
                r["view"].sync(st, self.grid.free_count())
                if st.done:
                    r["shown"] = min(len(st.path), r["shown"] + 3)
            return
        if self.searcher is not None:
            st = self.searcher.state
            if self.playing and not st.done:
                self.acc += self.rate() * dt
                n = int(self.acc)
                self.acc -= n
                for _ in range(min(n, 600)):
                    if not self.searcher.step():
                        break
            self.view.sync(st, self.grid.free_count())
            if st.done:
                self.playing = False
                self.path_shown = min(len(st.path), self.path_shown + 3)

    # ---------------- мишка и клавиатура ----------------
    def paint(self, cell, erase):
        x, y = cell
        if not self.grid.in_bounds(x, y) or cell in (self.start, self.goal):
            return
        new = FLOOR if erase else self.tool
        if self.grid.get(x, y) != new:
            self.grid.set(x, y, new)
            self.grid_changed_light()

    def grid_changed_light(self):
        self.view.rebuild(self.grid)
        self.searcher = None
        self.final = None
        self.path_shown = 0
        self.playing = False

    def handle(self, e):
        if e.type == pygame.QUIT:
            self.running = False
        elif e.type == pygame.MOUSEBUTTONDOWN:
            if self.slider_rect.inflate(0, 20).collidepoint(e.pos):
                self.dragging = "slider"
                self.set_slider(e.pos[0])
                return
            for b in self.buttons:
                if b.rect.collidepoint(e.pos):
                    b.action()
                    return
            if self.mode == "single" and AREA.collidepoint(e.pos):
                c = self.view.to_cell(e.pos)
                if e.button == 1 and c == self.start:
                    self.dragging = "start"
                elif e.button == 1 and c == self.goal:
                    self.dragging = "goal"
                elif e.button in (1, 3):
                    self.dragging = "erase" if e.button == 3 else "paint"
                    self.paint(c, e.button == 3)
        elif e.type == pygame.MOUSEBUTTONUP:
            self.dragging = None
        elif e.type == pygame.MOUSEMOTION and self.dragging:
            if self.dragging == "slider":
                self.set_slider(e.pos[0])
                return
            c = self.view.to_cell(e.pos)
            if not self.grid.in_bounds(*c):
                return
            if self.dragging in ("start", "goal"):
                other = self.goal if self.dragging == "start" else self.start
                if self.grid.get(*c) != WALL and c != other:
                    if self.dragging == "start":
                        self.start = c
                    else:
                        self.goal = c
                    self.grid_changed_light()
            else:
                self.paint(c, self.dragging == "erase")
        elif e.type == pygame.KEYDOWN:
            k = e.key
            if k == pygame.K_ESCAPE:
                if self.mode == "race":
                    self.toggle_race()
                else:
                    self.running = False
            elif k == pygame.K_SPACE:
                self.toggle_play()
            elif k == pygame.K_n:
                self.single_step()
            elif k == pygame.K_r:
                self.restart()
            elif k == pygame.K_g:
                self.new_maze()
            elif k == pygame.K_c:
                self.clear_grid()
            elif k == pygame.K_t:
                self.toggle_race()
            elif k == pygame.K_s:
                self.save()
            elif k == pygame.K_l:
                self.load()
            elif k in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                self.speed = min(1.0, self.speed + 0.05)
            elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.speed = max(0.0, self.speed - 0.05)
            elif pygame.K_1 <= k <= pygame.K_5:
                self.set_algo(list(ALGORITHMS)[k - pygame.K_1])

    def set_slider(self, mx):
        self.speed = max(0.0, min(1.0, (mx - self.slider_rect.x) / self.slider_rect.w))

    def save(self):
        self.grid.save("maze.json", self.start, self.goal)
        self.flash("Запазено в maze.json")

    def load(self):
        if not os.path.exists("maze.json"):
            self.flash("Няма maze.json")
            return
        self.grid, self.start, self.goal = Grid.load("maze.json")
        self.mode = "single"
        self.grid_changed()
        self.flash("Заредено от maze.json")

    # ---------------- рисуване ----------------
    def text(self, s, pos, font=None, color=TEXT):
        self.screen.blit((font or self.f).render(s, True, color), pos)

    def draw_panel(self):
        pygame.draw.rect(self.screen, CARD, (PANEL_X - 10, 10, WIN_W - PANEL_X, WIN_H - 20), border_radius=14)
        x = PANEL_X + 20
        self.text("MAZE LAB", (x, 22), self.f_title)
        self.text("Алгоритми за търсене на път", (x, 56), self.f_s, MUTED)
        self.text("АЛГОРИТЪМ", (x, 80), self.f_h, MUTED)
        self.text("ГЕНЕРАТОР НА ЛАБИРИНТ", (x, 170), self.f_h, MUTED)
        self.text("ИНСТРУМЕНТ / НАСТРОЙКИ", (x, 256), self.f_h, MUTED)
        self.text("РАЗМЕР", (x, 342), self.f_h, MUTED)
        self.text("УПРАВЛЕНИЕ", (x, 394), self.f_h, MUTED)
        self.text("СКОРОСТ", (x, 562), self.f_h, MUTED)
        self.sync_buttons()
        mp = pygame.mouse.get_pos()
        for b in self.buttons:
            b.draw(self.screen, self.f, b.rect.collidepoint(mp))
        # плъзгач
        r = self.slider_rect
        pygame.draw.rect(self.screen, (52, 58, 78), r, border_radius=7)
        pygame.draw.rect(self.screen, ACCENT, (r.x, r.y, int(r.w * self.speed), r.h), border_radius=7)
        pygame.draw.circle(self.screen, TEXT, (r.x + int(r.w * self.speed), r.centery), 10)
        self.text(f"{int(self.rate())} клетки/сек", (x, 608), self.f_s, MUTED)

        # статистика
        box = pygame.Rect(x, 636, 290, 100)
        pygame.draw.rect(self.screen, (22, 25, 35), box, border_radius=10)
        if self.mode == "race":
            self.text("Режим: СЪСТЕЗАНИЕ", (box.x + 12, box.y + 10), self.f_h, ACCENT)
            self.text("Пази се еднакъв брой разширявания", (box.x + 12, box.y + 40), self.f_s, MUTED)
            self.text("за всички. Печели най-малкото.", (box.x + 12, box.y + 60), self.f_s, MUTED)
        else:
            st = self.searcher.state if self.searcher else None
            self.text(DESCRIPTIONS[self.algo], (box.x + 12, box.y + 6), self.f_s, ALGO_COLORS[self.algo])
            exp = st.expanded_count if st else 0
            self.text(f"Разширени: {exp}", (box.x + 12, box.y + 32), self.f)
            if st and st.done:
                if st.found:
                    self.text(f"Път: {st.steps} ст. | цена {st.cost}", (box.x + 12, box.y + 56), self.f, PATH_C)
                    if self.final:
                        self.text(f"Време: {self.final[1]:.2f} ms", (box.x + 12, box.y + 78), self.f_s, MUTED)
                else:
                    self.text("НЯМА ПЪТ!", (box.x + 12, box.y + 56), self.f_h, GOAL_C)
            else:
                self.text("Натисни ИНТЕРВАЛ за старт", (box.x + 12, box.y + 60), self.f_s, MUTED)
        if self.message and time.time() - self.message_t < 2:
            self.text(self.message, (x, 742), self.f_s, FRONT_C)

    def draw_race(self):
        pw, ph = AREA.w // 3, AREA.h // 2
        free = self.grid.free_count()
        for i, r in enumerate(self.race):
            px, py = AREA.x + (i % 3) * pw, AREA.y + (i // 3) * ph
            pygame.draw.rect(self.screen, CARD, (px + 2, py + 2, pw - 4, ph - 4), border_radius=10)
            st = r["s"].state
            col = ALGO_COLORS[r["name"]]
            self.text(r["name"], (px + 12, py + 8), self.f_h, col)
            info = f"разш. {st.expanded_count}"
            if st.done:
                info += f" | път {st.steps}" if st.found else " | няма път"
            self.text(info, (px + 12 + 90, py + 9), self.f_s, MUTED)
            r["view"].draw(self.screen, self.grid, st, self.start, self.goal, r["shown"])
            if r["rank"] is not None:
                badge = pygame.Rect(px + pw - 54, py + 6, 42, 22)
                pygame.draw.rect(self.screen, col, badge, border_radius=11)
                lab = {1: "1-ви", 2: "2-ри", 3: "3-ти"}.get(r["rank"], f"{r['rank']}-ти")
                img = self.f_s.render(lab, True, (255, 255, 255))
                self.screen.blit(img, img.get_rect(center=badge.center))
        # табло в шестата клетка
        px, py = AREA.x + 2 * pw, AREA.y + ph
        pygame.draw.rect(self.screen, CARD, (px + 2, py + 2, pw - 4, ph - 4), border_radius=10)
        self.text("РАЗШИРЕНИ КЛЕТКИ", (px + 14, py + 10), self.f_h, MUTED)
        mx = max(1, max(r["s"].state.expanded_count for r in self.race))
        for j, r in enumerate(self.race):
            y = py + 44 + j * 52
            n = r["s"].state.expanded_count
            self.text(r["name"], (px + 14, y), self.f_s, TEXT)
            bar = pygame.Rect(px + 14, y + 20, int((pw - 90) * n / mx), 14)
            pygame.draw.rect(self.screen, ALGO_COLORS[r["name"]], bar, border_radius=7)
            self.text(str(n), (px + 20 + (pw - 90) * n // mx, y + 17), self.f_s, TEXT)
        self.text("ИНТЕРВАЛ - старт, N - стъпка, T/ESC - изход", (AREA.x + 12, AREA.bottom - 18), self.f_s, MUTED)

    def draw(self):
        self.screen.fill(BG)
        if self.mode == "race":
            self.draw_race()
        else:
            pygame.draw.rect(self.screen, CARD, AREA.inflate(8, 8), border_radius=12)
            st = self.searcher.state if self.searcher else None
            self.view.draw(self.screen, self.grid, st, self.start, self.goal, self.path_shown)
        self.draw_panel()
        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            for e in pygame.event.get():
                self.handle(e)
            self.update(dt)
            self.draw()
        pygame.quit()


def main():
    App().run()


if __name__ == "__main__":
    main()
