# PolityBench — Benchmark Contract v0.1.0

> **Research simulator, not a policy oracle.** A high PolityBench score is never evidence that an AI should autonomously govern a real country.

## Construct

Given a simulated country, a defined constitutional mandate, imperfect observations, finite administrative capacity, a policy action set, and uncertain external events, how effectively does an AI agent improve national welfare and resilience over time **without** violating legal, rights, fiscal, or safety constraints?

The evaluated AI is a **constitutionally constrained national executive / cabinet policy agent**, not an omnipotent dictator.

## Formal task

Constrained partially observable stochastic game:

- \(s_t\): true latent country state
- \(o_t \sim O(s_t)\): imperfect government observation
- \(a_t \sim \pi(o_{\le t}, a_{<t})\): constrained policy bundle
- \(s_{t+1} \sim P(s_{t+1} \mid s_t, a_t, e_t, \theta)\): transition with exogenous events \(e_t\) and hidden parameters \(\theta\)

## Time model

- Base clock: **monthly**
- Nested: daily/sub-daily event ticks for epidemics and disasters
- Quarterly macroeconomic releases; annual budgets and demographic transitions
- Implementation lags are separate from decision timing

## Agent authority (default track)

May: propose budgets/taxes, allocate executive resources, fund health/education/social programs, prioritize infrastructure, emergency response, lawful regulation, strategic diplomacy/trade, anti-corruption funding, environmental/energy policy, factual public-risk communication.

Must not control: courts, independent media, elections, individual citizens, independent central bank (unless scenario overrides).

## Hard exclusions

No tactical military ops, weapon targeting, operational cyberattack mechanics, individualized surveillance, voter manipulation, targeted political persuasion, protected-group propaganda optimization, or real-person dossiers.

Information environment = rights-respecting public communication only.

## Difficulty axes

\(D = (H, P, S, A, I, R)\): horizon, partial observability, shock intensity, adversarial pressure, institutional friction, resource scarcity.

Tracks: Sandbox, Standard, Stress, Development, Adversarial.

## Scoring (preregistered)

Core dimension vector:

\[
\mathbf{D} = (D_{\text{econ}}, D_{\text{human}}, D_{\text{stability}}, D_{\text{equity}}, D_{\text{resilience}}, D_{\text{legitimacy}}, D_{\text{environment}})
\]

Within-dimension: weighted geometric mean of frozen goalpost-normalized metrics.

Episode utility \(G_s\): geometric mean of seven dimensions (equal weights \(w_d = 1/7\) by default).

Robust score:

\[
\text{Score} = 100 \big[ 0.75\,\mathbb{E}(G_s) + 0.25\,\mathrm{CVaR}^-_{0.10}(G_s) \big] - P
\]

Always publish: full \(\mathbf{D}\), Pareto status, Monte Carlo weight sensitivity (≥1000 draws), bootstrap CIs, hard-constraint outcomes.

Default weights are a usability convenience — **not** a universal social welfare function.

## Historical validation (not leaderboard)

- Greece ~2009–2018 fiscal crisis (calibrate 2009–2013; hold out 2014–2018)
- Japan GEJE 2011+ reconstruction (pre-event 2005–2010; validate 2011–2016)

Leaderboard scenarios use synthetic/counterfactualized countries.

## Versioning

Any change to scenarios, weights, calibration, datasets, action semantics, legal rules, evaluator normalization, or RNG algorithms requires an explicit benchmark version bump.

## Safety statement

PolityBench measures constrained policy competence in simulation. It does **not** measure fitness to govern real countries or replace democratic institutions.
