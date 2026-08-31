# ODD+2D — PolityBench hybrid core (v0.1.0)

## 1. Purpose

Evaluate constrained AI executive policy under uncertainty in a hybrid national simulator.
PolityBench measures multi-dimensional welfare improvement under legal, fiscal, and rights
constraints — not fitness to replace democratic institutions.

## 2. Entities, state variables, and scales

| Entity | State variables | Scale |
|--------|-----------------|-------|
| Nation (singleton) | GDP flows, unemployment, inflation, debt, fiscal balances | Monthly national accounts |
| Regions | Damage, service continuity, displacement | Coarse regional aggregate |
| Household cohorts (F2+) | Income decile weights, trust | Weighted representative agents |
| Health system | Infected, beds, occupancy, vaccine coverage | Aggregate SEIR + capacity |
| Infrastructure | Power capacity/availability, damage fraction, backlog | Network proxy |
| Governance | Trust, misinformation pressure, corruption, admin capacity | [0,1] indices |
| External actors | Creditor stance, financing spread, diplomatic inbox | Message + latent stress |

## 3. Process overview and scheduling

**Monthly clock** (base tick):

1. Agent submits `ActionBundle` → **LegalGate** validates authority and safety exclusions
2. Accepted effects enter **ImplementationQueue** with configurable lag
3. Scheduled **shocks** fire (demand, export, epidemic, disaster, creditor pressure)
4. **Epidemic/disaster** substeps (daily ticks inside month when active)
5. **Macro SD update** (`step_macro`) with accounting identities enforced
6. **External/trade** tick for creditor negotiation and financing spreads
7. **Measurement layer** releases noisy, delayed observations

Nested clocks: daily epidemic ticks; quarterly macro releases in cabinet reports; annual demographics.

## 4. Design concepts

- **Partial observability**: agents see estimates, not latent elasticities or true shocks
- **Institutional friction**: legal rejections, implementation lags, administrative capacity
- **Accounting identities**: GDP identity, fiscal balance consistency (see `accounting/invariants.py`)
- **Generative shocks**: scenario RNG streams sample initial conditions and event timing
- **Multi-objective evaluation**: seven frozen goalpost-normalized dimensions + Pareto reporting
- **Common random numbers**: paired seeds for agent comparison

## 5. Initialization

`build_scenario(name, seed, fidelity, eval_mode)`:

- Draws initial macro/fiscal/governance state from `StreamBank(scenario_init)`
- Applies frozen posterior samples for macro (`greece_posterior_v1`), disaster (`japan_geje_posterior_v1`), or pandemic trust priors
- Sets horizon truncated by fidelity (F0≤24mo, F1≤60mo, F2/F3 full)

Official evaluation uses `eval_mode=official` (no `training_signals`); training mode exposes latent summaries for research ceilings only.

## 6. Input data

Dataset adapters under `packages/datasets/` with frozen manifests. Historical validation fixtures:

- Greece 2009–2018 (calibrate 2009–2013, hold out 2014–2018)
- Japan GEJE 2011+ (calibrate 2011–2013, hold out 2014–2016)
- Pandemic trust scaffold (synthetic wave shape, not country replay)

Restricted series are never redistributed; CI validates license metadata.

## 7. Submodels

| Module | Role |
|--------|------|
| `economy/macro.py` | Okun-style labor market, fiscal feedback, trust/misinformation |
| `population/households.py` | Weighted cohorts (F2+) |
| `measurement/observe.py` | Noisy releases, cabinet reports |
| `institutions/legal.py` | Safety exclusions, fiscal rules, capacity gate |
| `trade/external.py` | Creditor negotiation, tariffs, financing spread |
| `eval/hidden.py` | Official hidden seed bank |

## 8. Parameterization and ensembles

Structural elasticities sampled from frozen JSON posteriors (`configs/ensembles/`).
Calibration pipelines under `calibration/` fit on calibration windows only; holdout metrics published with limitations.

## 9. Known limitations (+2D)

**Model limitations:**

- Mesoscopic fidelity — not a DSGE or prefecture-resolved disaster model
- Simplified epidemic (aggregate SEIR) and disaster (damage fraction proxy)
- No firm-level credit network or supply-chain graph
- Greece holdout GDP RMSE remains material (~16 index points)

**Documentation limitations:**

- F3 increases household count but is not independently validated photorealism
- IMF WEO fixture is synthetic scaffold, not official redistribution
- Human expert baseline protocol is documented but not automated

**Do not overclaim**: publish validation failures; a high benchmark score is not evidence of real-world governing competence.

## 10. +2D extensions (ODD+2D)

- **Decision**: Agents are national executive/cabinet — not omnipotent dictators
- **Data**: Observations are measured with error and delay; training mode may expose summaries for ablation only
