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

Pre-event 2010–2011Q1 → event injection → 2011–2016 reconstruction shape vs public scaffold.

## Rule

`verification ≠ calibration ≠ validation`. Failed fits are published in result JSONs.
