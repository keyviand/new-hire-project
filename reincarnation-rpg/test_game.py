from pathlib import Path
import tempfile

from entities import Hero, Treasure, make_boss, make_chapter2_enemy, make_enemy, make_floor_guardian
from learning_ai import ACTIONS, LearningAdventurer
from settings import TILE_SIZE
from world import World


def main() -> None:
    world = World()
    spawn = world.spawn_position()
    assert world.walkable_pixel(spawn.x, spawn.y)
    assert world.biome_at_pixel(*world.chapter2_position()) == "ashen_reach"
    boss = make_boss(*world.boss_tile)
    assert boss.boss and boss.chapter == 2 and boss.max_hp >= 600
    chapter2_enemy = make_chapter2_enemy(*world.random_chapter2_tile())
    assert chapter2_enemy.chapter == 2
    guardian = make_floor_guardian(*world.floor_guardian_tile)
    assert guardian.floor_boss and guardian.boss and guardian.max_hp >= 800
    assert world.is_safe_zone(*world.floor_portal_position())

    hero = Hero(x=spawn.x, y=spawn.y, color=(0, 0, 0))
    original_attack = hero.attack
    hero.level = 5
    message = hero.reincarnate(spawn)
    assert hero.rebirths == 1
    assert hero.attack > original_attack
    assert "Reborn" in message

    with tempfile.TemporaryDirectory() as directory:
        brain = Path(directory) / "brain.json"
        echo = LearningAdventurer(spawn.x, spawn.y, brain)
        enemy = make_enemy(10, 10)
        treasure = Treasure(11 * TILE_SIZE, 11 * TILE_SIZE)
        state = echo.state(world, [enemy], [treasure])
        assert len(echo.values(state)) == len(ACTIONS)
        assert len(ACTIONS) == 14
        echo.update(0.2, world, [enemy], [treasure])
        breakdown = echo.mastery_breakdown(world)
        assert set(breakdown) == {
            "overall", "exploration", "knowledge", "tactics", "combat", "treasure"
        }
        assert all(0 <= value <= 1 for value in breakdown.values())
        chapter2 = echo.chapter2_mastery()
        assert all(0 <= value <= 1 for value in chapter2.values())
        vrmmo = echo.vrmmo_mastery()
        assert all(0 <= value <= 1 for value in vrmmo.values())
        assert "party_guard" in ACTIONS and "combo_with_player" in ACTIONS
        assert "focus_boss" in ACTIONS and "guard" in ACTIONS
        assert echo.action_counts
        assert echo.lifetime_visited
        echo.x = 0
        echo.y = 0
        events = echo.update(0.2, world, [], [])
        assert echo.position.distance_to(spawn) < 1
        assert echo.rescues == 1
        assert any("stuck" in event for event in events)

        echo.x, echo.y = spawn
        echo.stuck_anchor = spawn.copy()
        echo.stuck_seconds = 8.95
        events = echo.update(0.2, world, [], [])
        assert echo.rescues == 2
        assert any("stuck" in event for event in events)
        echo.save()
        assert brain.exists()
        restored = LearningAdventurer(spawn.x, spawn.y, brain)
        assert restored.action_counts == echo.action_counts
        assert restored.lifetime_visited == echo.lifetime_visited

    hero.void_cores = 10
    result = hero.upgrade_equipment()
    assert hero.weapon_level == 1
    assert "upgraded" in result
    hero.sword_mastery = 50
    hero.parry_window = 0.25
    assert hero.parry_window > 0

    print("World, reincarnation, and learning AI checks passed.")


if __name__ == "__main__":
    main()
