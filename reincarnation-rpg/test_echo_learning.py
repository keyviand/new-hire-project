import tempfile
from pathlib import Path

from echo_learning import EchoQLearner


def main() -> None:
    learner = EchoQLearner(
        learning_rate=0.5,
        discount=0.9,
        epsilon=0.0,
        minimum_epsilon=0.0,
        epsilon_decay=1.0,
        seed=7,
    )
    learner.q_table["next"] = {"strike": 2.0, "retreat": -1.0}
    result = learner.learn(
        "current", "approach", 1.0, "next", ["strike", "retreat"]
    )
    assert abs(result - 1.4) < 1e-9

    learner.q_table["choice"] = {"strike": 4.0, "circle": 1.0}
    assert learner.choose_action("choice", ["strike", "circle"]) == "strike"

    policy = EchoQLearner(epsilon=0.0, minimum_epsilon=0.0, seed=3)
    for _ in range(40):
        policy.learn("close", "circle", 2.0, "close", ["circle", "power"])
        policy.learn("close", "power", -1.0, "close", ["circle", "power"])
    assert policy.choose_action("close", ["circle", "power"]) == "circle"

    terminal = learner.learn(
        "danger", "power", -10.0, "ignored", ["strike"], terminal=True
    )
    assert terminal == -5.0

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "echo_brain.json"
        saved = EchoQLearner(path, epsilon=0.2, seed=1)
        saved.learn("healthy|close", "circle", 3.0, "healthy|close", ["circle"])
        saved.save()
        restored = EchoQLearner(path, seed=1)
        assert restored.q_table == saved.q_table
        assert restored.updates == 1
        assert restored.total_reward == 3.0

    print("Echo Q-learning equation, policy choice, terminal reward, and persistence passed.")


if __name__ == "__main__":
    main()
