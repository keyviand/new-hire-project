"""Train Echo quickly without drawing the game window."""

from __future__ import annotations

import argparse
from pathlib import Path

from entities import Hero, Treasure, make_boss, make_chapter2_enemy, make_enemy, make_floor_guardian
from settings import COLORS
from settings import TILE_SIZE
from learning_ai import LearningAdventurer
from world import World


ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=100_000)
    args = parser.parse_args()

    world = World()
    spawn = world.spawn_position()
    echo = LearningAdventurer(
        spawn.x, spawn.y, ROOT / "ai_brain_vrmmo.json"
    )
    party_member = Hero(x=spawn.x + 45, y=spawn.y, color=COLORS["player"])
    enemies = []
    for difficulty, count in [(1, 10), (2, 8), (3, 4)]:
        for _ in range(count):
            x, y = world.random_walkable_tile(8)
            enemies.append(make_enemy(x, y, difficulty))
    for _ in range(14):
        x, y = world.random_chapter2_tile()
        enemies.append(make_chapter2_enemy(x, y))
    enemies.append(make_boss(*world.boss_tile))
    enemies.append(make_floor_guardian(*world.floor_guardian_tile))
    treasures = []
    for index in range(10):
        x, y = world.random_walkable_tile(6)
        treasures.append(
            Treasure(
                x=(x + 0.5) * TILE_SIZE,
                y=(y + 0.5) * TILE_SIZE,
                kind="potion" if index % 3 == 0 else "chest",
            )
        )

    for step in range(1, args.steps + 1):
        # Alternate regions while emphasizing the new VRMMO floor.
        if step % 2500 == 1:
            if (step // 2500) % 5:
                position = world.floor_guardian_position()
                position.x -= 170
            else:
                position = world.spawn_position()
            echo.x, echo.y = position
            party_member.x, party_member.y = position.x + 45, position.y
            echo.stuck_anchor = position.copy()
        for enemy in enemies:
            enemy.update(0.12, echo, world)
        for treasure in treasures:
            treasure.update(0.12)
        party_member.x = echo.x + 45
        party_member.y = echo.y
        echo.update(0.12, world, enemies, treasures, party_member)
        if step % 10_000 == 0:
            echo.save()
            print(
                f"step {step:,} | episodes {echo.episodes} | kills {echo.kills} | "
                f"treasure {echo.treasure_collected} | states {len(echo.q)} | "
                f"VRMMO mastery {echo.vrmmo_mastery()['overall']:.1%}"
            )
    echo.save()
    print(f"Training complete. Brain saved to {echo.brain_path}")


if __name__ == "__main__":
    main()
