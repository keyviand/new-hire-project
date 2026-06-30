import threading
import time

import coop_server
from network_client import CoopClient


def wait_for(predicate, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def main() -> None:
    coop_server.STATE = coop_server.CoopState(max_players=4)
    server = coop_server.ThreadingCoopServer(("127.0.0.1", 0), coop_server.CoopHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    first = CoopClient("127.0.0.1", port, "Ari")
    second = CoopClient("127.0.0.1", port, "Lyra")
    first.start()
    second.start()
    try:
        assert wait_for(lambda: first.connected and second.connected)
        assert wait_for(lambda: len(first.get_snapshot().get("players", [])) == 2)

        with coop_server.STATE.lock:
            player = coop_server.STATE.players[first.player_id]
            player["x"], player["y"] = coop_server.GUARDIAN_POSITION
        starting_hp = coop_server.STATE.guardian_hp
        first.attack_guardian(40)
        assert wait_for(lambda: coop_server.STATE.guardian_hp < starting_hp)
        assert coop_server.STATE.guardian_hp == starting_hp - 40

        first.set_state(x=-99999, y=99999, hp=100, max_hp=100, level=1)
        time.sleep(0.2)
        with coop_server.STATE.lock:
            player = coop_server.STATE.players[first.player_id]
            assert 0 <= player["x"] <= 60 * 48
            assert 0 <= player["y"] <= 44 * 48
        print("Two-client synchronization and authoritative combat checks passed.")
    finally:
        first.close()
        second.close()
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()

