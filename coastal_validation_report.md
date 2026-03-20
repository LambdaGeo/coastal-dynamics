# Coastal Dynamics — Vector vs Raster Validation

Steps: 5 | Tolerance: 0.05

## Runtime

| Substrate | ms/step | Speedup |
|---|---|---|
| Vector | 897.8 | 1× |
| Raster | 61.6 | 14.6× |

## Accuracy

| Band | Match % | MAE | RMSE | Max err | N cells |
|---|---|---|---|---|---|
| uso | 100.00% | 0.000000 | 0.000000 | 0.000000 | 50496 |
| alt | 100.00% | 0.000037 | 0.000593 | 0.025994 | 50496 |
| solo | 100.00% | 0.000000 | 0.000000 | 0.000000 | 50496 |
