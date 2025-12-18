diff --git a/tetris.py b/tetris.py
new file mode 100644
index 0000000000000000000000000000000000000000..0bcaa1deb456b7875ae9985e42de710b4b5fda8b
--- /dev/null
+++ b/tetris.py
@@ -0,0 +1,295 @@
+import random
+import sys
+from typing import List, Tuple
+
+import pygame
+
+# Game configuration
+BLOCK_SIZE = 30
+COLUMNS = 10
+ROWS = 20
+PLAY_WIDTH = COLUMNS * BLOCK_SIZE
+PLAY_HEIGHT = ROWS * BLOCK_SIZE
+SIDE_PANEL = 180
+TOP_MARGIN = 60
+WINDOW_WIDTH = PLAY_WIDTH + SIDE_PANEL
+WINDOW_HEIGHT = PLAY_HEIGHT + TOP_MARGIN + 20
+FPS = 60
+
+# Define the shapes as rotation states of coordinate offsets
+SHAPES = {
+    "S": [
+        [(0, 0), (1, 0), (0, 1), (-1, 1)],
+        [(0, 0), (0, 1), (1, 1), (1, 2)],
+    ],
+    "Z": [
+        [(0, 0), (-1, 0), (0, 1), (1, 1)],
+        [(0, 0), (0, 1), (-1, 1), (-1, 2)],
+    ],
+    "I": [
+        [(0, 0), (-1, 0), (1, 0), (2, 0)],
+        [(0, -1), (0, 0), (0, 1), (0, 2)],
+    ],
+    "O": [
+        [(0, 0), (1, 0), (0, 1), (1, 1)],
+    ],
+    "J": [
+        [(0, 0), (-1, 0), (1, 0), (-1, 1)],
+        [(0, 0), (0, 1), (0, -1), (1, -1)],
+        [(0, 0), (-1, 0), (1, 0), (1, -1)],
+        [(0, 0), (0, 1), (0, -1), (-1, 1)],
+    ],
+    "L": [
+        [(0, 0), (-1, 0), (1, 0), (1, 1)],
+        [(0, 0), (0, 1), (0, -1), (1, 1)],
+        [(0, 0), (-1, 0), (1, 0), (-1, -1)],
+        [(0, 0), (0, 1), (0, -1), (-1, -1)],
+    ],
+    "T": [
+        [(0, 0), (-1, 0), (1, 0), (0, 1)],
+        [(0, 0), (0, 1), (0, -1), (1, 0)],
+        [(0, 0), (-1, 0), (1, 0), (0, -1)],
+        [(0, 0), (0, 1), (0, -1), (-1, 0)],
+    ],
+}
+
+SHAPE_COLORS = {
+    "S": (48, 199, 140),
+    "Z": (227, 90, 90),
+    "I": (55, 194, 238),
+    "O": (247, 211, 69),
+    "J": (76, 110, 245),
+    "L": (241, 160, 75),
+    "T": (186, 104, 201),
+}
+
+
+class Tetromino:
+    def __init__(self, shape: str):
+        if shape not in SHAPES:
+            raise ValueError(f"Unknown shape {shape}")
+        self.shape = shape
+        self.rotation = 0
+        self.position = (COLUMNS // 2, 0)
+
+    @property
+    def color(self) -> Tuple[int, int, int]:
+        return SHAPE_COLORS[self.shape]
+
+    def blocks(self, rotation: int | None = None, position: Tuple[int, int] | None = None) -> List[Tuple[int, int]]:
+        rot_index = rotation if rotation is not None else self.rotation
+        pos = position if position is not None else self.position
+        offsets = SHAPES[self.shape][rot_index % len(SHAPES[self.shape])]
+        return [(pos[0] + dx, pos[1] + dy) for dx, dy in offsets]
+
+
+class Board:
+    def __init__(self):
+        self.grid: List[List[Tuple[int, int, int] | None]] = [
+            [None for _ in range(COLUMNS)] for _ in range(ROWS)
+        ]
+        self.score = 0
+        self.level = 1
+        self.lines_cleared = 0
+
+    def inside_bounds(self, x: int, y: int) -> bool:
+        return 0 <= x < COLUMNS and y < ROWS
+
+    def collision(self, blocks: List[Tuple[int, int]]) -> bool:
+        for x, y in blocks:
+            if y < 0:
+                continue
+            if not self.inside_bounds(x, y) or self.grid[y][x] is not None:
+                return True
+        return False
+
+    def lock_piece(self, tetromino: Tetromino) -> None:
+        for x, y in tetromino.blocks():
+            if y < 0:
+                continue
+            self.grid[y][x] = tetromino.color
+        cleared = self.clear_lines()
+        self.lines_cleared += cleared
+        self.score += cleared * 100 * self.level
+        if self.lines_cleared // 10 >= self.level:
+            self.level += 1
+
+    def clear_lines(self) -> int:
+        remaining = [row for row in self.grid if any(cell is None for cell in row)]
+        cleared = ROWS - len(remaining)
+        for _ in range(cleared):
+            remaining.insert(0, [None for _ in range(COLUMNS)])
+        self.grid = remaining
+        return cleared
+
+    def draw(self, surface: pygame.Surface) -> None:
+        for y in range(ROWS):
+            for x in range(COLUMNS):
+                color = self.grid[y][x]
+                if color:
+                    pygame.draw.rect(
+                        surface,
+                        color,
+                        (x * BLOCK_SIZE, TOP_MARGIN + y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE),
+                    )
+                pygame.draw.rect(
+                    surface,
+                    (50, 50, 50),
+                    (x * BLOCK_SIZE, TOP_MARGIN + y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE),
+                    1,
+                )
+
+
+class Game:
+    def __init__(self):
+        pygame.init()
+        pygame.display.set_caption("Tetris")
+        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
+        self.clock = pygame.time.Clock()
+        self.board = Board()
+        self.current_piece = self._next_piece()
+        self.next_piece = self._next_piece()
+        self.drop_counter = 0
+        self.drop_speed = 48  # frames before auto-drop; decreases over time
+        self.running = True
+
+    def _next_piece(self) -> Tetromino:
+        return Tetromino(random.choice(list(SHAPES.keys())))
+
+    def reset(self) -> None:
+        self.board = Board()
+        self.current_piece = self._next_piece()
+        self.next_piece = self._next_piece()
+        self.drop_counter = 0
+        self.drop_speed = 48
+
+    def rotate_piece(self) -> None:
+        new_rotation = self.current_piece.rotation + 1
+        if not self.board.collision(self.current_piece.blocks(rotation=new_rotation)):
+            self.current_piece.rotation = new_rotation
+
+    def move_piece(self, dx: int) -> None:
+        new_pos = (self.current_piece.position[0] + dx, self.current_piece.position[1])
+        if not self.board.collision(self.current_piece.blocks(position=new_pos)):
+            self.current_piece.position = new_pos
+
+    def drop_piece(self) -> None:
+        new_pos = (self.current_piece.position[0], self.current_piece.position[1] + 1)
+        if not self.board.collision(self.current_piece.blocks(position=new_pos)):
+            self.current_piece.position = new_pos
+        else:
+            self.board.lock_piece(self.current_piece)
+            self.current_piece = self.next_piece
+            self.next_piece = self._next_piece()
+            if self.board.collision(self.current_piece.blocks()):
+                self.reset()
+
+    def hard_drop(self) -> None:
+        while not self.board.collision(self.current_piece.blocks(position=(self.current_piece.position[0], self.current_piece.position[1] + 1))):
+            self.current_piece.position = (
+                self.current_piece.position[0],
+                self.current_piece.position[1] + 1,
+            )
+        self.drop_piece()
+
+    def update(self) -> None:
+        self.drop_counter += 1
+        speed = max(10, self.drop_speed - (self.board.level - 1) * 3)
+        if self.drop_counter >= speed:
+            self.drop_piece()
+            self.drop_counter = 0
+
+    def draw_grid(self) -> None:
+        self.board.draw(self.screen)
+        for x, y in self.current_piece.blocks():
+            if y < 0:
+                continue
+            pygame.draw.rect(
+                self.screen,
+                self.current_piece.color,
+                (x * BLOCK_SIZE, TOP_MARGIN + y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE),
+            )
+            pygame.draw.rect(
+                self.screen,
+                (30, 30, 30),
+                (x * BLOCK_SIZE, TOP_MARGIN + y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE),
+                1,
+            )
+
+    def draw_side_panel(self) -> None:
+        font = pygame.font.SysFont("Arial", 20)
+        large = pygame.font.SysFont("Arial", 28, bold=True)
+
+        title = large.render("Next", True, (220, 220, 220))
+        self.screen.blit(title, (PLAY_WIDTH + 20, 20))
+
+        for block in self.next_piece.blocks(position=(COLUMNS + 2, 2)):
+            pygame.draw.rect(
+                self.screen,
+                self.next_piece.color,
+                (block[0] * BLOCK_SIZE, TOP_MARGIN + block[1] * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE),
+            )
+
+        info_lines = [
+            f"Score: {self.board.score}",
+            f"Level: {self.board.level}",
+            f"Lines: {self.board.lines_cleared}",
+            "",
+            "Controls:",
+            "Left/Right: Move",
+            "Up: Rotate",
+            "Down: Soft drop",
+            "Space: Hard drop",
+            "R: Restart",
+            "Esc: Quit",
+        ]
+        for idx, text in enumerate(info_lines):
+            label = font.render(text, True, (210, 210, 210))
+            self.screen.blit(label, (PLAY_WIDTH + 20, 120 + idx * 24))
+
+    def handle_events(self) -> None:
+        for event in pygame.event.get():
+            if event.type == pygame.QUIT:
+                self.running = False
+            elif event.type == pygame.KEYDOWN:
+                if event.key == pygame.K_ESCAPE:
+                    self.running = False
+                elif event.key == pygame.K_LEFT:
+                    self.move_piece(-1)
+                elif event.key == pygame.K_RIGHT:
+                    self.move_piece(1)
+                elif event.key == pygame.K_UP:
+                    self.rotate_piece()
+                elif event.key == pygame.K_DOWN:
+                    self.drop_piece()
+                elif event.key == pygame.K_SPACE:
+                    self.hard_drop()
+                elif event.key == pygame.K_r:
+                    self.reset()
+
+    def draw(self) -> None:
+        self.screen.fill((15, 15, 20))
+        pygame.draw.rect(
+            self.screen,
+            (200, 200, 200),
+            (0, TOP_MARGIN, PLAY_WIDTH, PLAY_HEIGHT),
+            2,
+        )
+        self.draw_grid()
+        self.draw_side_panel()
+        pygame.display.flip()
+
+    def run(self) -> None:
+        while self.running:
+            self.handle_events()
+            self.update()
+            self.draw()
+            self.clock.tick(FPS)
+
+
+if __name__ == "__main__":
+    try:
+        Game().run()
+    except KeyboardInterrupt:
+        pygame.quit()
+        sys.exit()
