import asyncio
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from websockets.asyncio.client import connect
from browser_server import BrowserWorldState


ROOT = Path(__file__).resolve().parent
HTTP_PORT = 18080


async def browser_clients() -> None:
    async with connect(f"ws://127.0.0.1:{HTTP_PORT}/ws") as first, connect(
        f"ws://127.0.0.1:{HTTP_PORT}/ws"
    ) as second:
        await first.send(json.dumps({"type": "join", "name": "Ari"}))
        welcome_one = json.loads(await first.recv())
        await second.send(json.dumps({"type": "join", "name": "Lyra"}))
        welcome_two = json.loads(await second.recv())
        assert welcome_one["type"] == "welcome"
        assert welcome_two["type"] == "welcome"
        assert "Infinity" not in json.dumps(welcome_one)
        await first.send(
            json.dumps(
                {
                    "type": "state",
                    "x": 410,
                    "y": 410,
                    "hp": 100,
                    "max_hp": 100,
                    "level": 2,
                }
            )
        )
        snapshot = json.loads(await first.recv())
        assert len(snapshot["players"]) == 2
        assert snapshot["players"][0]["mana"] == 40
        assert snapshot["players"][0]["max_mana"] == 40
        assert snapshot["players"][0]["quest_target"] == 5
        assert snapshot["guardian"]["hp"] == 850
        assert len(snapshot["monsters"]) >= 10
        assert snapshot["echo"]["hp"] > 0
        assert set(snapshot["echo_progress"]) >= {
            "overall", "exploration", "monsters", "combat", "boss", "support"
        }
        assert snapshot["unique_encounter"]["unlocked"] is False
        assert snapshot["players"][0]["evolution_rank"] == "Reborn Wanderer"

        for x in (445, 480, 515, 550, 585):
            await first.send(
                json.dumps(
                    {
                        "type": "state",
                        "x": x,
                        "y": 430,
                        "hp": 100,
                        "max_hp": 100,
                        "level": 1,
                    }
                )
            )
            snapshot = json.loads(await first.recv())
        monster = snapshot["monsters"][0]
        starting_hp = monster["hp"]
        await first.send(
            json.dumps(
                {"type": "attack", "target_id": monster["id"], "damage": 20}
            )
        )
        snapshot = json.loads(await first.recv())
        updated = next(item for item in snapshot["monsters"] if item["id"] == monster["id"])
        assert updated["hp"] < starting_hp
        await first.send(json.dumps({"type": "skill"}))
        snapshot = json.loads(await first.recv())
        me = next(item for item in snapshot["players"] if item["id"] == welcome_one["player_id"])
        assert me["mana"] < me["max_mana"]


def main() -> None:
    evolution_state = BrowserWorldState(4)
    evolution_welcome = evolution_state.join("EvolutionTester")
    evolution_id = evolution_welcome["player_id"]
    with evolution_state.lock:
        evolution_player = evolution_state.players[evolution_id]
        for monster in evolution_state.monsters[:5]:
            evolution_state._defeat_monster(monster, evolution_player)
        assert evolution_player["devourer_unlocked"] is True
        assert evolution_player["evolution_rank"] == "Essence Adept"
        skill_target = evolution_state.monsters[5]
        evolution_player["x"], evolution_player["y"] = skill_target["x"], skill_target["y"]
        evolution_player["hp"] = 40
        skill_starting_hp = skill_target["hp"]
    evolution_state.use_devourer_skill(evolution_id)
    assert evolution_player["mana"] == 15
    assert evolution_player["hp"] > 40
    assert skill_target["hp"] < skill_starting_hp
    with evolution_state.lock:
        evolution_player["quest_completions"] = 2
    evolution_state.tick(0.05)
    unique = next(monster for monster in evolution_state.monsters if monster["unique"])
    assert unique["active"] is True
    assert evolution_state.unique_encounter["unlocked"] is True
    with evolution_state.lock:
        forged = evolution_state._new_item(5, 2)
        evolution_player["inventory"].append(forged)
    evolution_state.equip_item(evolution_id, forged["id"])
    assert evolution_player["equipment"][forged["slot"]]["id"] == forged["id"]
    with evolution_state.lock:
        evolution_player["x"], evolution_player["y"] = evolution_state.NPCS[1]["x"], evolution_state.NPCS[1]["y"]
        evolution_player["gold"] = 100
    evolution_state.interact(evolution_id)
    assert evolution_player["gold"] == 25
    with evolution_state.lock:
        evolution_player["x"], evolution_player["y"] = evolution_state.chests[0]["x"], evolution_state.chests[0]["y"]
    evolution_state.interact(evolution_id)
    assert evolution_player["dungeon_chests"] == 1

    with tempfile.TemporaryDirectory() as directory:
        save_path = Path(directory) / "characters.json"
        saved_state = BrowserWorldState(4, save_path)
        saved_welcome = saved_state.join("PersistentHero", "Spellblade")
        saved_id = saved_welcome["player_id"]
        saved_state.players[saved_id]["gold"] = 321
        saved_state.leave(saved_id)
        restored_state = BrowserWorldState(4, save_path)
        restored = restored_state.join("PersistentHero", "Vanguard")
        restored_player = restored_state.players[restored["player_id"]]
        assert restored_player["gold"] == 321
        assert restored_player["style"] == "Spellblade"

    state = BrowserWorldState(4)
    welcome = state.join("BossTester")
    player_id = welcome["player_id"]
    with state.lock:
        player = state.players[player_id]
        player["x"], player["y"] = state.guardian["x"], state.guardian["y"]
    while not state.floor_cleared:
        with state.lock:
            state.players[player_id]["last_attack"] = 0
        state.attack_guardian(player_id, {"damage": 120})
    assert state.guardian["floor"] == 1
    assert state.guardian["next_spawn_seconds"] == 0
    state.next_guardian_at = time.monotonic() - 0.01
    state.tick(0.05)
    assert state.guardian["floor"] == 2
    assert "Nyxara" in state.guardian["name"]
    assert state.guardian["hp"] == 1250

    process = subprocess.Popen(
        [
            sys.executable,
            "browser_server.py",
            "--host",
            "127.0.0.1",
            "--port",
            str(HTTP_PORT),
            "--no-save",
        ],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(80):
            try:
                html = urllib.request.urlopen(
                    f"http://127.0.0.1:{HTTP_PORT}", timeout=1
                ).read().decode()
                if "Everdawn Online" in html:
                    assert "Devourer Pulse" in html
                    assert 'id="character-panel"' in html
                    break
            except OSError:
                time.sleep(0.05)
        else:
            raise AssertionError("Browser server did not start")
        asyncio.run(browser_clients())
        print("Browser page and two WebSocket client checks passed.")
    finally:
        process.terminate()
        process.wait(timeout=5)


if __name__ == "__main__":
    main()
