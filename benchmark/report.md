# Coastal Dynamics Validation Report

**Steps:** 10 | **Tolerance:** 0.05

## Runtime

| Substrate | ms/step | Speedup |
|---|---|---|
| Vector | 1697.1 | 1.0× |
| Raster | 60.2 | 28.2× |

## Accuracy

| Band | Match % | MAE | RMSE | Max err | N cells |
|---|---|---|---|---|---|
| alt | 99.88% | 0.000848 | 0.004720 | 0.127818 | 97309 |
| solo | 10.06% | nan | nan | nan | 97309 |
| uso | 100.00% | 0.000000 | 0.000000 | 0.000000 | 97309 |
