# Reproducibility Guide

## How to Reproduce Baseline

### Prerequisites
- Python 3.8+
- Node.js 18+
- SQLite3

### Step 1: Clone and Setup Baselines

```bash
# Clone baselines
python scripts/setup_baselines.py

# Check external/baselines directory
ls external/baselines/
```

### Step 2: Install Dependencies

```bash
# Backend dependencies
pip install -r requirements.txt

# Frontend dependencies
cd frontend
npm install
```

### Step 3: Initialize Database and Seed Data

```bash
# Seed database with sample data (including 3-5% self-collected)
python scripts/seed_data.py --count 200 --ratio 0.04
```

### Step 4: Train Model

```bash
# Train the price prediction model
python scripts/train_model.py
```

### Step 5: Run Backend API

```bash
# Start FastAPI server
uvicorn src.backend.main:app --reload --host localhost --port 8000
```

### Step 6: Run Frontend

```bash
# In a new terminal
cd frontend
npm run dev
```

### Step 7: Test the System

1. Open http://localhost:3000
2. Try prediction
3. Check dataset statistics
4. Add self-collected data

## How to Run Improved System

The improved system includes:

1. **Enhanced Database Schema**: Added self-collected tracking (3-5%)
2. **REST API**: Full CRUD operations with validation
3. **React Frontend**: Professional UI with hierarchical location selection
4. **Model Improvements**: Additional features and better preprocessing

To run:

```bash
# Start backend
uvicorn src.backend.main:app --reload

# Start frontend (separate terminal)
cd frontend && npm run dev
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
DATABASE_URL=sqlite:///./real_estate_avm.db
API_HOST=localhost
API_PORT=8000
MODEL_PATH=./models/price_model.pkl
```

## Verification

Check if everything works:

```bash
# Check API health
curl http://localhost:8000/api/health

# Get dataset stats
curl http://localhost:8000/api/dataset/stats
```
