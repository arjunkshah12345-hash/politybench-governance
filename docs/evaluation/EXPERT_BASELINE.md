# Human expert baseline protocol (v0.1)

PolityBench supports optional human-in-the-loop baselines for construct validation.
This is **not** a leaderboard track and does not produce official scores without preregistration.

## Purpose

Compare AI agents against transparent human policy teams under identical information constraints,
to assess whether the benchmark discriminates competence vs. automation artifact.

## Eligibility

- Teams of 1–3 participants with policy/economics/public-health familiarity (no simulator access)
- No access to latent parameters, posterior JSON, or hidden official seeds
- Same `eval_mode=official` observations as AI agents

## Session setup

```bash
politybench serve  # HTTP API
# or
politybench run-scenario --scenario macro_fiscal_crisis --fidelity F1 --seed <public_seed> --agent rule_based
```

Human teams interact via the FastAPI session endpoints:

1. `POST /v1/session/reset` — receive initial observation
2. `GET /v1/session/{id}/reports/cabinet` — ministry reports
3. `POST /v1/session/{id}/actions` — submit `ActionBundle` JSON
4. Repeat until `observation.done`

## Information rules

- Participants may take notes externally but may not run automated optimization against the simulator
- No individualized surveillance, propaganda, or military actions (same legal gate as AI)
- Time limit: 90 minutes wall clock per episode (recommended)

## Recording

Record for each month:

- Timestamp, submitted action JSON, rejected actions with codes
- Participant rationale (short text field in `meta.human_rationale` if provided)

## Analysis

Score with the standard evaluator:

```python
from politybench_eval import evaluate_episode, extras_from_state
ep = evaluate_episode(trajectory, seed=seed, scenario=scenario, extras=extras_from_state(final_state))
```

Report full seven-dimensional vector + robust score alongside AI baselines on the **same seed**.

## Ethics

Participants must acknowledge the research simulator disclaimer: scores do not endorse real-world governance authority.
