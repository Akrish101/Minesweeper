"""
Tkinter Minesweeper (Python 3)
Clean GUI with difficulty 1–5 (wider boards)
Includes:
- Outer border
- Inner background colour panel
- Timer + Flag counter
- First click safe
- Dark mode toggle
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Set, Optional, Dict
import tkinter as tk
from tkinter import ttk, messagebox
import random
import time


Coord = Tuple[int, int]


@dataclass(frozen=True)
class GameConfig:
    rows: int
    cols: int
    mines: int


# Wider / more horizontal layout
DIFFICULTIES: Dict[int, GameConfig] = {
    1: GameConfig(rows=8,  cols=12, mines=14),
    2: GameConfig(rows=9,  cols=14, mines=22),
    3: GameConfig(rows=10, cols=18, mines=38),
    4: GameConfig(rows=12, cols=22, mines=60),
    5: GameConfig(rows=14, cols=26, mines=90),
}


class Minesweeper:
    def __init__(self, cfg: GameConfig, seed: Optional[int] = None) -> None:
        if cfg.mines >= cfg.rows * cfg.cols:
            raise ValueError("Number of mines must be less than total cells.")

        self.cfg = cfg
        self.rng = random.Random(seed)

        self.mines: Set[Coord] = set()
        self.adj: List[List[int]] = [[0] * cfg.cols for _ in range(cfg.rows)]
        self.revealed: Set[Coord] = set()
        self.flags: Set[Coord] = set()

        self._mines_placed = False
        self.game_over = False
        self.won = False
        self.start_time = time.time()

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.cfg.rows and 0 <= c < self.cfg.cols

    def neighbors(self, r: int, c: int) -> List[Coord]:
        out: List[Coord] = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if self.in_bounds(nr, nc):
                    out.append((nr, nc))
        return out

    def _place_mines_first_click_safe(self, safe: Coord) -> None:
        sr, sc = safe
        forbidden = set(self.neighbors(sr, sc))
        forbidden.add(safe)

        candidates = [(r, c) for r in range(self.cfg.rows) for c in range(self.cfg.cols)
                      if (r, c) not in forbidden]

        # If grid is tiny / mines are heavy, relax neighborhood exclusion automatically
        if len(candidates) < self.cfg.mines:
            candidates = [(r, c) for r in range(self.cfg.rows) for c in range(self.cfg.cols)
                          if (r, c) != safe]

        self.mines = set(self.rng.sample(candidates, self.cfg.mines))
        self._recompute_adjacency()
        self._mines_placed = True

    def _recompute_adjacency(self) -> None:
        self.adj = [[0] * self.cfg.cols for _ in range(self.cfg.rows)]
        for (r, c) in self.mines:
            for (nr, nc) in self.neighbors(r, c):
                self.adj[nr][nc] += 1

    def toggle_flag(self, r: int, c: int) -> None:
        if self.game_over or not self.in_bounds(r, c):
            return
        cell = (r, c)
        if cell in self.revealed:
            return
        if cell in self.flags:
            self.flags.remove(cell)
        else:
            self.flags.add(cell)

    def reveal(self, r: int, c: int) -> None:
        if self.game_over or not self.in_bounds(r, c):
            return

        cell = (r, c)
        if cell in self.flags or cell in self.revealed:
            return

        if not self._mines_placed:
            self._place_mines_first_click_safe(cell)

        if cell in self.mines:
            self.game_over = True
            self.won = False
            self.revealed.add(cell)
            return

        self._flood_reveal(cell)
        self._check_win()

    def _flood_reveal(self, start: Coord) -> None:
        stack = [start]
        while stack:
            cell = stack.pop()
            if cell in self.revealed or cell in self.flags:
                continue
            self.revealed.add(cell)
            r, c = cell
            if self.adj[r][c] == 0:
                for nb in self.neighbors(r, c):
                    if nb not in self.revealed and nb not in self.mines and nb not in self.flags:
                        stack.append(nb)

    def _check_win(self) -> None:
        total = self.cfg.rows * self.cfg.cols
        if len(self.revealed) == total - self.cfg.mines:
            self.game_over = True
            self.won = True

    def elapsed_seconds(self) -> int:
        return int(time.time() - self.start_time)


class MinesweeperGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Minesweeper")
        self.resizable(False, False)

        self.level_var = tk.IntVar(value=1)
        self.dark_var = tk.BooleanVar(value=False)

        self.status_var = tk.StringVar(value="Pick difficulty and start a new game.")
        self.timer_var = tk.StringVar(value="Time: 0s")
        self.flags_var = tk.StringVar(value="Flags: 0/0")

        self.game: Optional[Minesweeper] = None
        self.buttons: List[List[tk.Button]] = []
        self._timer_job: Optional[str] = None

        # Theme palettes
        self.THEME_LIGHT = {
            "root_bg": "#f2f2f2",
            "text": "#111111",
            "panel_bg": "#d9d9d9",
            "border": "#000000",
            "btn_hidden_bg": "#ececec",
            "btn_hidden_fg": "#111111",
            "btn_revealed_bg": "#cfcfcf",
            "btn_revealed_fg": "#111111",
            "btn_disabled_fg": "#111111",
        }
        self.THEME_DARK = {
            "root_bg": "#121212",
            "text": "#eaeaea",
            "panel_bg": "#1e1e1e",
            "border": "#444444",
            "btn_hidden_bg": "#2a2a2a",
            "btn_hidden_fg": "#eaeaea",
            "btn_revealed_bg": "#202020",
            "btn_revealed_fg": "#eaeaea",
            "btn_disabled_fg": "#eaeaea",
        }

        self._build_ui()
        self.apply_theme()  # set initial theme
        self.new_game()

    def theme(self) -> Dict[str, str]:
        return self.THEME_DARK if self.dark_var.get() else self.THEME_LIGHT

    def _build_ui(self) -> None:
        # Use tk.Frame for easier background control
        self.top = tk.Frame(self, padx=10, pady=10)
        self.top.grid(row=0, column=0, sticky="ew")

        tk.Label(self.top, text="Difficulty:").grid(row=0, column=0, padx=(0, 6))

        self.level_box = ttk.Combobox(self.top, values=[str(i) for i in range(1, 6)], width=3, state="readonly")
        self.level_box.grid(row=0, column=1, padx=(0, 10))
        self.level_box.current(0)
        self.level_box.bind("<<ComboboxSelected>>", self._on_level_changed)

        tk.Button(self.top, text="New Game", command=self.new_game).grid(row=0, column=2, padx=(0, 10))

        # Dark mode toggle (acts like a switch)
        self.dark_toggle = ttk.Checkbutton(self.top, text="Dark mode", variable=self.dark_var, command=self.apply_theme)
        self.dark_toggle.grid(row=0, column=3, padx=(0, 10))

        self.flags_label = tk.Label(self.top, textvariable=self.flags_var)
        self.flags_label.grid(row=0, column=4, padx=(0, 10))

        self.timer_label = tk.Label(self.top, textvariable=self.timer_var)
        self.timer_label.grid(row=0, column=5)

        self.status_label = tk.Label(self, textvariable=self.status_var, anchor="w", padx=10, pady=0)
        self.status_label.grid(row=1, column=0, sticky="ew", padx=0, pady=(0, 8))

        # Outer border
        self.board_border = tk.Frame(self, highlightthickness=3)
        self.board_border.grid(row=2, column=0, padx=15, pady=(0, 15))

        # Inner background panel
        self.board_background = tk.Frame(self.board_border, padx=12, pady=12)
        self.board_background.grid(row=0, column=0)

        # Board frame (grid)
        self.board_frame = tk.Frame(self.board_background)
        self.board_frame.grid(row=0, column=0)

    def _on_level_changed(self, _evt=None) -> None:
        try:
            self.level_var.set(int(self.level_box.get()))
        except ValueError:
            self.level_var.set(1)

    def apply_theme(self) -> None:
        t = self.theme()

        # Root + major frames
        self.configure(bg=t["root_bg"])
        self.top.configure(bg=t["root_bg"])
        self.status_label.configure(bg=t["root_bg"], fg=t["text"])
        self.flags_label.configure(bg=t["root_bg"], fg=t["text"])
        self.timer_label.configure(bg=t["root_bg"], fg=t["text"])

        # Border + panel
        self.board_border.configure(bg=t["border"], highlightbackground=t["border"], highlightcolor=t["border"])
        self.board_background.configure(bg=t["panel_bg"])
        self.board_frame.configure(bg=t["panel_bg"])

        # Try to nudge ttk widgets (combobox/checkbutton) to blend in
        style = ttk.Style(self)
        # Some platforms ignore these; it's still fine.
        style.configure("TCheckbutton", background=t["root_bg"], foreground=t["text"])
        style.configure("TCombobox", foreground=t["text"])

        # Update existing buttons if any
        self._refresh_board(force_theme=True)

    def new_game(self) -> None:
        if self._timer_job is not None:
            self.after_cancel(self._timer_job)
            self._timer_job = None

        try:
            lvl = int(self.level_var.get())
        except Exception:
            lvl = 1

        cfg = DIFFICULTIES.get(lvl, DIFFICULTIES[1])

        self.game = Minesweeper(cfg)
        self.status_var.set("Left click to reveal. Right click to flag.")
        self.timer_var.set("Time: 0s")
        self.flags_var.set(f"Flags: 0/{cfg.mines}")

        for child in self.board_frame.winfo_children():
            child.destroy()

        self.buttons = []
        for r in range(cfg.rows):
            row_buttons: List[tk.Button] = []
            for c in range(cfg.cols):
                btn = tk.Button(
                    self.board_frame,
                    width=2,
                    height=1,
                    font=("Segoe UI", 11),
                    relief="raised",
                    command=lambda rr=r, cc=c: self.on_left_click(rr, cc),
                )
                btn.grid(row=r, column=c, padx=1, pady=1)
                btn.bind("<Button-3>", lambda e, rr=r, cc=c: self.on_right_click(rr, cc))
                row_buttons.append(btn)
            self.buttons.append(row_buttons)

        self.apply_theme()
        self._tick_timer()

    def _tick_timer(self) -> None:
        if not self.game or self.game.game_over:
            return
        self.timer_var.set(f"Time: {self.game.elapsed_seconds()}s")
        self._timer_job = self.after(250, self._tick_timer)

    def on_left_click(self, r: int, c: int) -> None:
        if not self.game or self.game.game_over:
            return
        self.game.reveal(r, c)
        self._refresh_board()
        if self.game.game_over:
            self._end_game()

    def on_right_click(self, r: int, c: int) -> None:
        if not self.game or self.game.game_over:
            return
        self.game.toggle_flag(r, c)
        self._refresh_board()

    def _refresh_board(self, force_theme: bool = False) -> None:
        if not self.game or not self.buttons:
            return

        t = self.theme()
        cfg = self.game.cfg
        self.flags_var.set(f"Flags: {len(self.game.flags)}/{cfg.mines}")

        for r in range(cfg.rows):
            for c in range(cfg.cols):
                cell = (r, c)
                btn = self.buttons[r][c]

                # Base colors (theme)
                hidden_bg = t["btn_hidden_bg"]
                hidden_fg = t["btn_hidden_fg"]
                revealed_bg = t["btn_revealed_bg"]
                revealed_fg = t["btn_revealed_fg"]

                if cell in self.game.revealed:
                    btn.config(relief="sunken", state="disabled", bg=revealed_bg, fg=revealed_fg,
                               disabledforeground=t["btn_disabled_fg"], activebackground=revealed_bg)
                    if cell in self.game.mines:
                        btn.config(text="💣")
                    else:
                        n = self.game.adj[r][c]
                        btn.config(text="" if n == 0 else str(n))
                else:
                    # still hidden
                    btn.config(state="normal", relief="raised",
                               bg=hidden_bg, fg=hidden_fg, activebackground=hidden_bg)
                    btn.config(text="🚩" if cell in self.game.flags else "")

                if force_theme:
                    # Ensure theme colors apply even if state didn't change
                    btn.update_idletasks()

    def _end_game(self) -> None:
        if not self.game:
            return

        t = self.theme()
        cfg = self.game.cfg
        for r in range(cfg.rows):
            for c in range(cfg.cols):
                cell = (r, c)
                btn = self.buttons[r][c]
                btn.config(state="disabled", relief="sunken",
                           bg=t["btn_revealed_bg"], fg=t["btn_revealed_fg"],
                           disabledforeground=t["btn_disabled_fg"],
                           activebackground=t["btn_revealed_bg"])
                if cell in self.game.mines:
                    btn.config(text="💣")
                else:
                    n = self.game.adj[r][c]
                    btn.config(text="" if n == 0 else str(n))

        msg = "You won! " if self.game.won else "Boom! You hit a mine 💥"
        self.status_var.set(msg)
        messagebox.showinfo("Game Over", msg)


if __name__ == "__main__":
    app = MinesweeperGUI()
    app.mainloop()
