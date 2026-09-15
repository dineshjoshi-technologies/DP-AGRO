# Phase 2 Per-Zone Governance Report

Generated: 2026-09-15T02:48:53.075187Z

```
============================================================
DPA-83 — Per-Zone Model Validation Report
Generated: 2026-09-15T02:48:53.075056Z
============================================================

GOVERNANCE THRESHOLDS:
  RMSE <= 0.15 t/ha
  MAE <= 0.1 t/ha
  R²  >= 0.85

ZONE RESULTS:
  zone-A:
    Samples:     50
    RMSE:        0.0375 t/ha
    MAE:         0.0191 t/ha
    R²:          0.9387
    Governance:  PASS
    Top features: rainfall_total_mm(29.864), soil_moisture_mean(0.749), ndvi_current(0.502), ndvi_trend(0.367), temp_max(0.268)

  zone-B:
    Samples:     50
    RMSE:        0.0195 t/ha
    MAE:         0.0108 t/ha
    R²:          0.9834
    Governance:  PASS
    Top features: rainfall_total_mm(106.185), ndvi_trend(2.457), temp_max(1.561), soil_moisture_mean(0.696), soil_moisture_std(0.672)

  zone-C:
    Samples:     50
    RMSE:        0.0192 t/ha
    MAE:         0.0109 t/ha
    R²:          0.9809
    Governance:  PASS
    Top features: rainfall_total_mm(72.868), soil_moisture_mean(1.269), soil_ec_mean(1.090), ndvi_current(0.975), soil_ph_mean(0.793)

  zone-D:
    Samples:     50
    RMSE:        0.0460 t/ha
    MAE:         0.0222 t/ha
    R²:          0.9053
    Governance:  PASS
    Top features: rainfall_total_mm(17.450), humidity_mean(0.351), ndvi_lag14(0.326), temp_max(0.177), ndvi_current(0.159)

============================================================
OVERALL: READY FOR PRODUCTION
============================================================
```

## Summary
- Training farms: 200 (50 per zone held-out validation)
- All four zones PASS governance (R² >= 0.85, RMSE <= 0.15 t/ha, MAE <= 0.10 t/ha)
- Negative R² in small test sets resolved: min_samples=30 gate + R² clamp + low-variance flag
- Drift monitoring integrated with retraining pipeline (RETRAIN triggers governance-gated training)
