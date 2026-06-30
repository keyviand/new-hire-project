from __future__ import annotations

import math
import random

import pygame

from settings import COLORS, TILE_SIZE, WORLD_HEIGHT, WORLD_WIDTH


class World:
    def __init__(self, seed: int = 7331):
        self.seed = seed
        self.rng = random.Random(seed)
        self.tiles = [["grass" for _ in range(WORLD_WIDTH)] for _ in range(WORLD_HEIGHT)]
        self.spawn_tile = (8, 8)
        self.shrine_tile = (9, 7)
        self.quest_tile = (7, 8)
        self.chapter2_gate_tile = (42, 29)
        self.forge_tile = (11, 7)
        self.boss_tile = (53, 34)
        self.floor_portal_tile = (15, 9)
        self.floor_guardian_tile = (34, 12)
        self.floor2_camp_tile = (19, 5)
        self._generate()

    def _generate(self) -> None:
        for y in range(WORLD_HEIGHT):
            for x in range(WORLD_WIDTH):
                edge = min(x, y, WORLD_WIDTH - 1 - x, WORLD_HEIGHT - 1 - y)
                noise = (
                    math.sin(x * 0.31)
                    + math.cos(y * 0.27)
                    + math.sin((x + y) * 0.16)
                )
                if edge < 2 or noise < -2.0:
                    self.tiles[y][x] = "water"
                elif noise > 1.65 and self.rng.random() < 0.72:
                    self.tiles[y][x] = "forest"
                elif self.rng.random() < 0.025:
                    self.tiles[y][x] = "stone"

        # Village and roads.
        for y in range(5, 12):
            for x in range(4, 14):
                self.tiles[y][x] = "village" if (x + y) % 4 else "path"
        for x in range(8, WORLD_WIDTH - 4):
            self.tiles[9][x] = "path"
            if x % 9 == 0:
                self.tiles[8][x] = "path"
        for y in range(9, WORLD_HEIGHT - 4):
            self.tiles[y][28] = "path"

        # Clear several encounter regions.
        for cx, cy, radius in [(20, 16, 4), (39, 12, 4), (33, 30, 5), (50, 32, 4)]:
            for y in range(max(2, cy - radius), min(WORLD_HEIGHT - 2, cy + radius)):
                for x in range(max(2, cx - radius), min(WORLD_WIDTH - 2, cx + radius)):
                    if (x - cx) ** 2 + (y - cy) ** 2 <= radius**2:
                        self.tiles[y][x] = "grass"

        # Chapter 2: the Ashen Reach and the Obsidian Vault.
        for y in range(20, WORLD_HEIGHT - 2):
            for x in range(40, WORLD_WIDTH - 2):
                self.tiles[y][x] = "corruption" if (x + y) % 4 else "ash"
        for x in range(28, 44):
            self.tiles[29][x] = "path"
        for y in range(24, 41):
            for x in range(46, 58):
                edge = x in {46, 57} or y in {24, 40}
                self.tiles[y][x] = "stone" if edge else "dungeon"
        self.tiles[29][46] = "dungeon"
        for x in range(42, 47):
            self.tiles[29][x] = "corruption"
        for x, y in [(49, 27), (54, 27), (49, 38), (55, 37)]:
            self.tiles[y][x] = "lava"
        self.tiles[self.chapter2_gate_tile[1]][self.chapter2_gate_tile[0]] = "corruption"
        self.tiles[self.boss_tile[1]][self.boss_tile[0]] = "dungeon"

        # VRMMO Floor 1: Skyglass Fields and its guardian arena.
        for y in range(3, 19):
            for x in range(16, 40):
                self.tiles[y][x] = "skyfield" if (x + y) % 5 else "tower"
        for x in range(13, 20):
            self.tiles[9][x] = "path"
        for y in range(8, 14):
            self.tiles[y][34] = "tower"
        for y in range(8, 17):
            for x in range(30, 39):
                if x in {30, 38} or y in {8, 16}:
                    self.tiles[y][x] = "tower"
                else:
                    self.tiles[y][x] = "skyfield"
        self.tiles[12][30] = "skyfield"
        self.tiles[self.floor_portal_tile[1]][self.floor_portal_tile[0]] = "safe"
        self.tiles[self.floor_guardian_tile[1]][self.floor_guardian_tile[0]] = "skyfield"

    @property
    def pixel_width(self) -> int:
        return WORLD_WIDTH * TILE_SIZE

    @property
    def pixel_height(self) -> int:
        return WORLD_HEIGHT * TILE_SIZE

    def tile_at_pixel(self, x: float, y: float) -> str:
        tx, ty = int(x // TILE_SIZE), int(y // TILE_SIZE)
        if not (0 <= tx < WORLD_WIDTH and 0 <= ty < WORLD_HEIGHT):
            return "water"
        return self.tiles[ty][tx]

    def walkable_pixel(self, x: float, y: float) -> bool:
        return self.tile_at_pixel(x, y) not in {"water", "forest", "stone", "lava"}

    def spawn_position(self) -> pygame.Vector2:
        x, y = self.spawn_tile
        return pygame.Vector2((x + 0.5) * TILE_SIZE, (y + 0.5) * TILE_SIZE)

    @property
    def walkable_tile_count(self) -> int:
        return sum(
            tile not in {"water", "forest", "stone"}
            for row in self.tiles
            for tile in row
        )

    def random_walkable_tile(self, min_distance_from_spawn: float = 8) -> tuple[int, int]:
        sx, sy = self.spawn_tile
        for _ in range(5000):
            x = self.rng.randrange(3, WORLD_WIDTH - 3)
            y = self.rng.randrange(3, WORLD_HEIGHT - 3)
            if (
                self.tiles[y][x] in {"grass", "path"}
                and math.dist((x, y), (sx, sy)) >= min_distance_from_spawn
            ):
                return x, y
        return 20, 20

    def random_chapter2_tile(self) -> tuple[int, int]:
        for _ in range(2000):
            x = self.rng.randrange(41, WORLD_WIDTH - 3)
            y = self.rng.randrange(21, WORLD_HEIGHT - 3)
            if self.tiles[y][x] in {"corruption", "ash", "dungeon"}:
                return x, y
        return self.chapter2_gate_tile

    def chapter2_position(self) -> pygame.Vector2:
        x, y = self.chapter2_gate_tile
        return pygame.Vector2((x + 0.5) * TILE_SIZE, (y + 0.5) * TILE_SIZE)

    def floor_portal_position(self) -> pygame.Vector2:
        x, y = self.floor_portal_tile
        return pygame.Vector2((x + 0.5) * TILE_SIZE, (y + 0.5) * TILE_SIZE)

    def floor_guardian_position(self) -> pygame.Vector2:
        x, y = self.floor_guardian_tile
        return pygame.Vector2((x + 0.5) * TILE_SIZE, (y + 0.5) * TILE_SIZE)

    def is_safe_zone(self, x: float, y: float) -> bool:
        tile = self.tile_at_pixel(x, y)
        return tile in {"village", "safe"}

    def biome_at_pixel(self, x: float, y: float) -> str:
        tile = self.tile_at_pixel(x, y)
        if tile == "dungeon":
            return "vault"
        if tile in {"skyfield", "tower", "safe"}:
            return "floor1"
        if tile in {"corruption", "ash", "lava"}:
            return "ashen_reach"
        return "everdawn"

    def nearby_blocked(self, x: float, y: float, distance: float = 42) -> tuple[bool, bool, bool, bool]:
        return (
            not self.walkable_pixel(x, y - distance),
            not self.walkable_pixel(x, y + distance),
            not self.walkable_pixel(x - distance, y),
            not self.walkable_pixel(x + distance, y),
        )

    def draw(self, surface: pygame.Surface, camera: pygame.Vector2) -> None:
        start_x = max(0, int(camera.x // TILE_SIZE))
        start_y = max(0, int(camera.y // TILE_SIZE))
        end_x = min(WORLD_WIDTH, int((camera.x + surface.get_width()) // TILE_SIZE) + 2)
        end_y = min(WORLD_HEIGHT, int((camera.y + surface.get_height()) // TILE_SIZE) + 2)

        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile = self.tiles[y][x]
                rect = pygame.Rect(
                    x * TILE_SIZE - camera.x,
                    y * TILE_SIZE - camera.y,
                    TILE_SIZE + 1,
                    TILE_SIZE + 1,
                )
                color = COLORS.get(tile, COLORS["grass"])
                if tile == "grass" and (x * 17 + y * 13) % 5 == 0:
                    color = COLORS["grass_alt"]
                pygame.draw.rect(surface, color, rect)
                if tile == "forest":
                    pygame.draw.circle(surface, (30, 94, 58), rect.center, 18)
                elif tile == "stone":
                    pygame.draw.polygon(
                        surface,
                        (116, 124, 136),
                        [
                            (rect.centerx, rect.y + 8),
                            (rect.right - 8, rect.bottom - 10),
                            (rect.x + 8, rect.bottom - 7),
                        ],
                    )
                elif tile == "water":
                    yline = rect.y + 16 + ((x + y) % 3) * 7
                    pygame.draw.line(
                        surface, (62, 137, 177), (rect.x + 8, yline), (rect.right - 7, yline), 2
                    )
                elif tile == "corruption":
                    pygame.draw.circle(surface, (132, 72, 146), rect.center, 5)
                elif tile == "ash":
                    pygame.draw.line(surface, (111, 103, 112), rect.topleft, rect.bottomright, 2)
                elif tile == "dungeon":
                    pygame.draw.rect(surface, (72, 64, 82), rect, 2)
                elif tile == "lava":
                    pygame.draw.line(surface, (255, 136, 52), rect.midleft, rect.midright, 4)
                elif tile == "skyfield":
                    pygame.draw.circle(surface, (123, 208, 195), rect.center, 3)
                elif tile == "tower":
                    pygame.draw.rect(surface, (151, 164, 191), rect, 2)
                elif tile == "safe":
                    pygame.draw.circle(surface, (116, 241, 189), rect.center, 12, 2)

        self._draw_marker(surface, camera, self.quest_tile, COLORS["gold"], "!")
        self._draw_marker(surface, camera, self.shrine_tile, COLORS["ai"], "R")
        self._draw_marker(surface, camera, self.forge_tile, COLORS["elite"], "F")
        self._draw_marker(surface, camera, self.chapter2_gate_tile, COLORS["ai"], "II")
        self._draw_marker(surface, camera, self.floor_portal_tile, (83, 232, 255), "1")

    @staticmethod
    def _draw_marker(
        surface: pygame.Surface,
        camera: pygame.Vector2,
        tile: tuple[int, int],
        color: tuple[int, int, int],
        symbol: str,
    ) -> None:
        pos = pygame.Vector2(
            (tile[0] + 0.5) * TILE_SIZE, (tile[1] + 0.5) * TILE_SIZE
        ) - camera
        pygame.draw.circle(surface, color, pos, 18)
        font = pygame.font.Font(None, 25)
        text = font.render(symbol, True, (18, 20, 28))
        surface.blit(text, text.get_rect(center=pos))
