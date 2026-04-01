# Coastal Dynamics — Vector vs Raster Validation

Steps: 10 | Tolerance: 0.05

## Runtime

| Substrate | ms/step | Speedup |
|---|---|---|
| Vector | 1352.2 | 1× |
| Raster | 68.7 | 19.7× |

## Accuracy

| Band | Match % | MAE | RMSE | Max err | N cells |
|---|---|---|---|---|---|
| uso | 96.40% | 0.160587 | 0.974555 | 8.000000 | 50496 |
| alt | 88.46% | 0.318868 | 1.056721 | 6.579384 | 50496 |
| solo | 99.37% | 0.035825 | 0.451616 | 6.000000 | 50496 |
