# Baseline Comparison Plan

## Overview
This document outlines the baseline models used in the Real Estate AVM project and how they are compared.

## Baseline Models Used

### Baseline A: California Housing Price Prediction
- **Repository**: https://github.com/nitish9413/CALIFORNIA-HOUSING-PRICE-PREDICTION
- **License**: Apache-2.0
- **Purpose**: Primary ML baseline using sklearn for housing price prediction
- **Implementation**: Reusable pipeline structure with data ingestion, transformation, training, evaluation

### Baseline B: House Price Prediction (Flask)
- **Repository**: https://github.com/MdJafirAshraf/House-price-prediction-using-flask
- **License**: MIT
- **Purpose**: Flask API reference for model deployment
- **Implementation**: Simple Flask app with model prediction endpoint

### Baseline C: MLOps House Price Predictor
- **Repository**: https://github.com/mlopsbootcamp/house-price-predictor
- **License**: MIT
- **Purpose**: Project structure reference for MLOps
- **Implementation**: Organized folder structure with separate data/, models/, src/ directories

## Original Code vs Extended Code

### Code from Baselines (Original)
- `external/baselines/california-housing-price-prediction/*` - Full original code
- `external/baselines/house-price-prediction-flask/*` - Full original code
- `external/baselines/mlops-house-price-predictor/*` - Full original code

### Extended Code (New Development)
- `src/backend/database.py` - New database configuration
- `src/backend/models.py` - New SQLAlchemy models with self-collected fields
- `src/backend/main.py` - New FastAPI application
- `scripts/seed_data.py` - New data seeding with 3-5% self-collected
- `scripts/train_model.py` - New model training script
- `scripts/evaluate_model.py` - New model evaluation
- `scripts/import_csv.py` - New CSV import functionality
- `scripts/export_self_collected.py` - New export functionality
- `frontend/*` - Complete React frontend

## Comparison Metrics

| Metric | Baseline | Improved |
|--------|----------|----------|
| MAE | ~5,000,000 VND | Target: <4,500,000 VND |
| RMSE | ~8,000,000 VND | Target: <7,000,000 VND |
| R2 | ~0.75 | Target: >0.80 |

## Testing Plan
1. Run baseline model on test data
2. Train improved model with enhanced features
3. Compare metrics side-by-side
4. Document improvements in docs/experiment_results.md
