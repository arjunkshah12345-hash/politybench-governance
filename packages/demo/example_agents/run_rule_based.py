"""Example agents entrypoint."""

from politybench_api import PolityEnv, get_baseline, run_episode


def main():
    env = PolityEnv("compound_disaster", fidelity="F0", seed=123)
    out = run_episode(env, get_baseline("rule_based"))
    print(len(out["trajectory"]), out["manifest"]["trajectory_hash"][:12])


if __name__ == "__main__":
    main()
