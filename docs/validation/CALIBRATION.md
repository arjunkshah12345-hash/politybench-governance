# Historical calibration & validation

## Greece (2009–2018)

| Phase | Years | Use |
|-------|-------|-----|
| Calibration | 2009–2013 | Parameter ensemble search / selection |
| Holdout | 2014–2018 | Report only — never used for fitting |

Command:

```bash
politybench calibrate --particles 48 --keep 12
politybench calibrate-smoke
```

Frozen artifact: `configs/ensembles/greece_posterior_v1.json`

Synthetic `macro_fiscal_crisis` scenarios sample elasticities from this posterior (counterfactual shocks remain generative — not a Greece replay).

## Japan GEJE (2011+)

| Phase | Years | Use |
|-------|-------|-----|
| Pre-event | 2010–2011Q1 | Structural check (damage ≈ 0) |
| Calibration | 2011–2013 | Rebuild-parameter ensemble |
| Holdout | 2014–2016 | Report only |

```bash
politybench calibrate --target japan --particles 48 --keep 12
```

Frozen artifact: `configs/ensembles/japan_geje_posterior_v1.json`  
Synthetic `compound_disaster` blends generative timing with calibrated intensity/rebuild priors.

## External trade & creditor negotiation

Strategic (non-tactical) module: tariffs, trade agreements, creditor program accept/counter/reject.
Affects partner demand, financing spreads, and export access. Options appear in `diplomatic_inbox`.

