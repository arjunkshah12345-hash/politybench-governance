# ODD outline — PolityBench hybrid core (v0.1)

## 1. Purpose
Evaluate constrained AI executive policy under uncertainty in a hybrid national simulator.

## 2. Entities
- Nation (singleton stocks/flows)
- Regions
- Weighted household cohorts
- Ministries/institutions (abstract capacity & leakage)
- External actors (messages / shocks)

## 3. Process overview
Monthly tick: legal gate → implementation queue → scheduled shocks → epidemic/disaster substeps → macro SD update → measurement release.

## 4. Design concepts
Partial observability; institutional constraints; accounting identities; generative shocks; multi-objective evaluation.

## 5. Initialization
Scenario builders sample initial conditions + hidden elasticities from named RNG streams; optional official-fixture baselines.

## 6. Input data
See dataset manifests; Greece/Japan validation use open fixtures / adapters.

## 7. Submodels
Documented in `packages/core-sim/politybench_core/economy/macro.py` and related modules.

## 8. Known limitations
Mesoscopic fidelity; simplified epidemic/disaster; not a full firm credit network; validation RMSE remains material — publish failures, do not overclaim.
