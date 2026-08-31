# Finish PolityBench MVP remaining work

## Objective

Close all remaining MVP gaps from the original PolityBench spec: hidden official eval harness,
Gymnasium/PettingZoo adapters, pandemic validation scaffold, dashboard calibration/heatmap panels,
ODD+2D docs, expert baseline protocol, and safety red-team tests — with green CI.

## Original Request

Build PolityBench end-to-end research benchmark; continue with `/goal finish all that is remaining`.

## Intake Summary

- Input shape: `existing_plan`
- Audience: research users / benchmark operators
- Authority: `requested`
- Proof type: `test`
- Completion proof: pytest green; calibrate-smoke + benchmark-smoke pass; dashboard builds; private repo intact
- Likely misfire: marking complete after docs-only without adapters/harness
- Blind spots considered: Greece holdout RMSE not fully fixable in one pass; F3 remains scaffolding
- Existing plan facts: private repo `arjunkshah12345-hash/politybench-governance`; Greece/Japan posteriors frozen

## Goal Kind

`existing_plan`

## Current Tranche

RL adapters → hidden eval → pandemic validation → dashboard export → docs → safety tests → audit

## Non-Negotiable Constraints

- Private GitHub repo only
- Research simulator disclaimer preserved
- No tactical military / propaganda / surveillance actions
- Historical cases validation-only, not leaderboard

## Stop Rule

Stop when Judge audit sets `full_outcome_complete: true` after pytest + smoke + dashboard build pass.

## Canonical Board

`docs/goals/politybench-mvp/state.yaml`

## Run Command

```text
/goal Follow docs/goals/politybench-mvp/goal.md.
```
