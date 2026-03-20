# Coastal Dynamics — Vector vs Raster Validation

Steps: 5 | Tolerance: 0.05

## Runtime

| Substrate | ms/step | Speedup |
|---|---|---|
| Vector | 990.9 | 1× |
| Raster | 51.3 | 19.3× |

## Accuracy

| Band | Match % | MAE | RMSE | Max err | N cells |
|---|---|---|---|---|---|
| uso | 100.00% | 0.000000 | 0.000000 | 0.000000 | 50496 |
| alt | 100.00% | 0.000037 | 0.000593 | 0.025994 | 50496 |
| solo | 100.00% | 0.000000 | 0.000000 | 0.000000 | 50496 |
