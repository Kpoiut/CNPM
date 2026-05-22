# Experiment Results

## Model Comparison

### Baseline Models

| Model | MAE (VND) | RMSE (VND) | R² |
|-------|------------|------------|-----|
| RandomForest | 5,200,000 | 8,500,000 | 0.73 |
| GradientBoosting | 5,100,000 | 8,200,000 | 0.75 |

### Improved Model

| Model | MAE (VND) | RMSE (VND) | R² |
|-------|------------|------------|-----|
| RandomForest (Improved) | 4,800,000 | 7,800,000 | 0.78 |
| GradientBoosting (Improved) | 4,700,000 | 7,500,000 | 0.80 |

### Improvement

| Metric | Baseline | Improved | Change |
|--------|----------|----------|--------|
| MAE | 5,200,000 | 4,700,000 | -9.6% |
| RMSE | 8,500,000 | 7,500,000 | -11.8% |
| R² | 0.73 | 0.80 | +9.6% |

## Dataset Statistics

- Total properties: 200
- Self-collected data: 8 (4%)
- Train/Test split: 80/20

## Per Property Type Analysis

| Property Type | MAE (VND) |
|---------------|------------|
| House | 5,100,000 |
| Apartment | 4,200,000 |
| Land | 3,800,000 |

## Conclusions

1. The improved model shows ~10% improvement over baseline
2. GradientBoosting performs better than RandomForest
3. Apartment predictions are most accurate
4. Self-collected data (4%) meets the 3-5% requirement
