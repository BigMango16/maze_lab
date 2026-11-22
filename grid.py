"""grid.py - представяне на лабиринта (решетка от клетки).

Всяка клетка е цяло число:
    WALL (-1)  - стена, не може да се премине;
    1          - обикновена клетка (цена за влизане 1);
    MUD (5)    - "кал", по-скъпа клетка (цена за влизане 5).
"""
import json

WALL = -1
FLOOR = 1
MUD = 5

# Съседи по 4 посоки: нагоре, надясно, надолу, наляво
DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))


class Grid:
    def __init__(self, width, height, fill=FLOOR):
        self.w = width
        self.h = height
        self.cells = [[fill] * width for _ in range(height)]

    # ----- основни операции -----
    def in_bounds(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def get(self, x, y):
        return self.cells[y][x]

    def set(self, x, y, value):
        self.cells[y][x] = value

    def passable(self, x, y):
        return self.in_bounds(x, y) and self.cells[y][x] != WALL

    def cost(self, cell):
        """Цена за влизане в клетката."""
        return self.cells[cell[1]][cell[0]]

    def neighbors(self, cell):
        x, y = cell
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if self.passable(nx, ny):
                yield (nx, ny)

    def free_count(self):
        return sum(1 for row in self.cells for c in row if c != WALL)

    def copy(self):
        g = Grid(self.w, self.h)
        g.cells = [row[:] for row in self.cells]
        return g

    def clear(self):
        self.cells = [[FLOOR] * self.w for _ in range(self.h)]

    # ----- запис/четене във файл -----
    def to_dict(self, start, goal):
        return {"w": self.w, "h": self.h, "start": list(start),
                "goal": list(goal), "cells": self.cells}

    @staticmethod
    def from_dict(data):
        g = Grid(data["w"], data["h"])
        g.cells = [list(r) for r in data["cells"]]
        return g, tuple(data["start"]), tuple(data["goal"])

    def save(self, path, start, goal):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(start, goal), f)

    @staticmethod
    def load(path):
        with open(path, encoding="utf-8") as f:
            return Grid.from_dict(json.load(f))
