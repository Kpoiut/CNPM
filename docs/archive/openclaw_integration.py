"""
OpenCLAW Integration for Real Estate AVM.
Provides AI-assisted model training, hyperparameter optimization, and insights.
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
import requests

# OpenCLAW API configuration
OPENCLAW_API_URL = os.environ.get('OPENCLAW_API_URL', 'https://api.openclaw.ai/v1')
OPENCLAW_API_KEY = os.environ.get('OPENCLAW_API_KEY', None)


class OpenCLAWClient:
    """
    OpenCLAW Client for AI-assisted ML operations.
    Provides hyperparameter optimization and model insights.
    """

    def __init__(self, api_key: str = None, api_url: str = None):
        self.api_key = api_key or OPENCLAW_API_KEY
        self.api_url = api_url or OPENCLAW_API_URL
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({'Authorization': f'Bearer {self.api_key}'})

    def is_available(self) -> bool:
        """Check if OpenCLAW API is available."""
        if not self.api_key:
            print("OpenCLAW: No API key configured. Using local ML instead.")
            return False
        try:
            response = self.session.get(f"{self.api_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

    def optimize_hyperparameters(self, model_type: str, X_train, y_train, metric: str = 'mae') -> Dict:
        """
        Request hyperparameter optimization from OpenCLAW.
        Falls back to local optimization if API unavailable.
        """
        if not self.is_available():
            return self._local_hyperopt(model_type, X_train, y_train, metric)

        try:
            response = self.session.post(
                f"{self.api_url}/optimize",
                json={
                    'model_type': model_type,
                    'metric': metric,
                    'n_trials': 50
                },
                timeout=60
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"OpenCLAW optimization failed: {e}")

        return self._local_hyperopt(model_type, X_train, y_train, metric)

    def _local_hyperopt(self, model_type: str, X_train, y_train, metric: str = 'mae') -> Dict:
        """
        Local hyperparameter optimization using grid search.
        """
        from sklearn.model_selection import cross_val_score

        print(f"Running local hyperparameter optimization for {model_type}...")

        if model_type == 'RandomForest':
            param_grid = {
                'n_estimators': [100, 150, 200],
                'max_depth': [15, 20, 25],
                'min_samples_split': [3, 5, 7],
                'min_samples_leaf': [1, 2, 3]
            }
            from sklearn.ensemble import RandomForestRegressor
            base_model = RandomForestRegressor(random_state=42, n_jobs=-1)

        elif model_type == 'GradientBoosting':
            param_grid = {
                'n_estimators': [100, 150, 200],
                'max_depth': [5, 6, 7, 8],
                'learning_rate': [0.05, 0.08, 0.1],
                'subsample': [0.7, 0.8, 0.9]
            }
            from sklearn.ensemble import GradientBoostingRegressor
            base_model = GradientBoostingRegressor(random_state=42)

        elif model_type == 'XGBoost':
            param_grid = {
                'n_estimators': [100, 150, 200],
                'max_depth': [6, 8, 10],
                'learning_rate': [0.05, 0.08, 0.1],
                'subsample': [0.7, 0.8, 0.9]
            }
            try:
                import xgboost as xgb
                base_model = xgb.XGBRegressor(random_state=42, n_jobs=-1)
            except:
                return {'error': 'XGBoost not available'}

        else:
            return {'error': f'Unknown model type: {model_type}'}

        # Simple grid search
        best_score = float('inf')
        best_params = {}

        for n_est in param_grid.get('n_estimators', [100]):
            for depth in param_grid.get('max_depth', [10]):
                try:
                    params = {'n_estimators': n_est, 'max_depth': depth}
                    if 'learning_rate' in param_grid:
                        params['learning_rate'] = param_grid['learning_rate'][0]
                    if 'subsample' in param_grid:
                        params['subsample'] = param_grid['subsample'][0]

                    model = base_model.__class__(**params)
                    scores = cross_val_score(model, X_train, y_train, cv=3, scoring='neg_mean_absolute_error', n_jobs=-1)
                    mae = -scores.mean()

                    if mae < best_score:
                        best_score = mae
                        best_params = params
                except:
                    continue

        return {
            'best_params': best_params,
            'best_mae': best_score,
            'optimization_method': 'local_grid_search'
        }

    def analyze_model(self, model, X_train, y_train) -> Dict:
        """
        Analyze model and provide insights.
        """
        insights = {
            'analysis_time': datetime.now().isoformat(),
            'model_type': type(model).__name__,
        }

        # Feature importance
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
            insights['top_features'] = sorted(
                enumerate(importances),
                key=lambda x: x[1],
                reverse=True
            )[:10]

        # Model-specific insights
        if 'RandomForest' in str(type(model)):
            insights['recommendations'] = [
                "RandomForest works well with mixed feature types",
                "Good for capturing non-linear relationships",
                "Less prone to overfitting with proper max_depth"
            ]
        elif 'GradientBoosting' in str(type(model)):
            insights['recommendations'] = [
                "GradientBoosting often outperforms RF on structured data",
                "Sensitive to hyperparameters",
                "Consider lower learning rate with more estimators"
            ]

        return insights

    def get_training_insights(self, results: Dict, data_info: Dict) -> Dict:
        """
        Get AI-generated insights about the training process.
        """
        insights = {
            'timestamp': datetime.now().isoformat(),
            'summary': []
        }

        # Data quality insights
        if data_info.get('sample_size', 0) < 1000:
            insights['summary'].append({
                'type': 'warning',
                'message': f"Dataset size ({data_info['sample_size']}) is relatively small. Consider collecting more data for better generalization."
            })

        # Self-collected ratio
        sc_ratio = data_info.get('self_collected_ratio', 0)
        if sc_ratio < 0.03:
            insights['summary'].append({
                'type': 'warning',
                'message': f"Self-collected data ratio ({sc_ratio:.1%}) is below recommended 5%. Consider increasing field survey data."
            })
        elif sc_ratio > 0.05:
            insights['summary'].append({
                'type': 'success',
                'message': f"Good self-collected data ratio ({sc_ratio:.1%}). IoT features will be meaningful."
            })

        # Model performance insights
        for model_name, metrics in results.items():
            r2 = metrics.get('r2', 0)
            if r2 > 0.85:
                insights['summary'].append({
                    'type': 'success',
                    'message': f"{model_name} achieved R² = {r2:.3f} - Excellent model fit"
                })
            elif r2 > 0.7:
                insights['summary'].append({
                    'type': 'info',
                    'message': f"{model_name} achieved R² = {r2:.3f} - Good model fit"
                })
            else:
                insights['summary'].append({
                    'type': 'warning',
                    'message': f"{model_name} achieved R² = {r2:.3f} - Consider feature engineering or more data"
                })

        return insights

    def generate_report(self, results: Dict, data_info: Dict, model_info: Dict) -> str:
        """
        Generate a comprehensive training report.
        """
        report = []
        report.append("=" * 60)
        report.append("REAL ESTATE AVM - MODEL TRAINING REPORT")
        report.append("=" * 60)
        report.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Data Summary
        report.append("\n\n--- DATA SUMMARY ---")
        report.append(f"Total samples: {data_info.get('sample_size', 0):,}")
        report.append(f"Self-collected: {data_info.get('self_collected_count', 0):,} ({data_info.get('self_collected_ratio', 0):.1%})")
        report.append(f"Public: {data_info.get('public_count', 0):,}")
        report.append(f"Features: {data_info.get('n_features', 0)}")

        # Model Results
        report.append("\n\n--- MODEL RESULTS ---")
        for model_name, metrics in results.items():
            report.append(f"\n{model_name}:")
            report.append(f"  MAE:  {metrics.get('mae', 0):,.0f} VND")
            report.append(f"  RMSE: {metrics.get('rmse', 0):,.0f} VND")
            report.append(f"  R²:   {metrics.get('r2', 0):.4f}")

        # Best Model
        best_model = min(results.items(), key=lambda x: x[1].get('mae', float('inf')))
        report.append(f"\n\nBest Model: {best_model[0]}")
        report.append(f"MAE: {best_model[1].get('mae', 0):,.0f} VND")

        # Insights
        insights = self.get_training_insights(results, data_info)
        if insights.get('summary'):
            report.append("\n\n--- AI INSIGHTS ---")
            for insight in insights['summary']:
                report.append(f"\n[{insight['type'].upper()}] {insight['message']}")

        return "\n".join(report)


# Singleton instance
_openclaw_client = None

def get_openclaw_client() -> OpenCLAWClient:
    """Get or create OpenCLAW client instance."""
    global _openclaw_client
    if _openclaw_client is None:
        _openclaw_client = OpenCLAWClient()
    return _openclaw_client


def optimize_model(model_type: str, X_train, y_train) -> Dict:
    """Quick hyperparameter optimization."""
    client = get_openclaw_client()
    return client.optimize_hyperparameters(model_type, X_train, y_train)


def get_training_insights(results: Dict, data_info: Dict) -> Dict:
    """Get AI insights for training results."""
    client = get_openclaw_client()
    return client.get_training_insights(results, data_info)


def generate_training_report(results: Dict, data_info: Dict, model_info: Dict = None) -> str:
    """Generate training report."""
    client = get_openclaw_client()
    return client.generate_report(results, data_info, model_info or {})
