# Architecture notes

## Coupling contract

| Layer | Owns | Hands off |
|-------|------|-----------|
| Macro SD | GDP identity, prices, debt stock, productivity | Employment rate, fiscal flows |
| Households | Weighted distributional cohorts | Aggregate consumption propensity via weights |
| Institutions | Authority, delays, rejections | Approved policy effects to queue |
| Events/networks | Disasters, epidemics, capacity queues | Damage fractions, occupancy, displacement |
| Measurement | Observation noise/delay/revision | Never latent θ or future shocks |

## Timestep

```mermaid
sequenceDiagram
  participant A as Agent
  participant G as Legal Gate
  participant Q as Impl Queue
  participant K as Kernel
  participant M as Measurement
  A->>G: ActionBundle
  G->>Q: Accepted effects + lag
  Q->>K: Due effects
  K->>K: Shocks / health / disaster / macro
  K->>M: True state
  M->>A: Imperfect observation
```

## RNG

`seed_m = SHA256(master, scenario, module, entity)` → independent NumPy Generator per module.
