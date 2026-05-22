"""
Feature Engineering Pipeline for Real Estate AVM.
Handles all feature extraction and transformation for ML models.
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json

from src.config.province_config import (
    CANONICAL_PROVINCES,
    normalize_province,
    CENTER_COORDS as CANONICAL_CENTER_COORDS,
    BASE_PRICES_PER_M2,
    get_base_price_per_m2,
)


class FeatureEngineer:
    """
    Feature Engineering for Real Estate Price Prediction.
    Transforms raw property data into ML-ready features.
    """

    def __init__(self):
        self.feature_names = []
        self.encoders = {}
        self.scaler = None
        self.feature_stats = {}
        self._knn_data = None  # (lat, lng, ppm2) triples for KNN lookup

    def fit(self, df: pd.DataFrame) -> 'FeatureEngineer':
        """
        Fit the feature engineer on training data.
        Computes statistics needed for transformation.
        """
        df = df.copy()

        # Store feature statistics
        self.feature_stats = {
            'area_m2': {
                'mean': df['area_m2'].mean(),
                'std': df['area_m2'].std(),
                'min': df['area_m2'].min(),
                'max': df['area_m2'].max()
            },
            'bedrooms': {
                'mean': df['bedrooms'].mean(),
                'std': df['bedrooms'].std(),
            },
            'bathrooms': {
                'mean': df['bathrooms'].mean(),
                'std': df['bathrooms'].std(),
            },
            'latitude': {
                'mean': df['latitude'].mean(),
                'std': df['latitude'].std(),
            },
            'longitude': {
                'mean': df['longitude'].mean(),
                'std': df['longitude'].std(),
            },
            # Interaction features
            'area_bedrooms': {
                'mean': (df['area_m2'] * df['bedrooms'].fillna(1)).mean(),
                'std': (df['area_m2'] * df['bedrooms'].fillna(1)).std() or 1.0,
            },
            'floor_bedrooms': {
                'mean': (df['floor_count'].fillna(1) * df['bedrooms'].fillna(1)).mean(),
                'std': (df['floor_count'].fillna(1) * df['bedrooms'].fillna(1)).std() or 1.0,
            },
        }

        # Build KNN reference data for spatial price density features
        # Only use verified records with lat/lng
        if 'price_per_m2' in df.columns and 'latitude' in df.columns:
            knn_df = df.dropna(subset=['latitude', 'longitude', 'price_per_m2'])
            self._knn_data = knn_df[['latitude', 'longitude', 'price_per_m2']].values
        else:
            self._knn_data = None

        optional_numeric = [
            'noise_level',
            'temperature',
            'humidity',
            'light_level',
            'rqs',
            'provenance_score',
            'verification_score',
            'market_anchor_score',
            'timeliness_score',
            'training_weight',
            'evidence_weight',
            'confidence_stage1_score',
            'confidence_prob_a',
            'confidence_prob_b',
            'confidence_prob_c',
            'confidence_prob_d',
        ]
        for col in optional_numeric:
            if col in df.columns:
                self.feature_stats[col] = {
                    'mean': df[col].fillna(df[col].mean()).mean(),
                    'std': df[col].fillna(df[col].mean()).std() or 1.0,
                }

        # Encode categorical features
        categorical_cols = ['property_type', 'province_city', 'district', 'legal_status', 'furnishing']
        for col in categorical_cols:
            if col in df.columns:
                unique_vals = df[col].fillna('unknown').unique()
                self.encoders[col] = {val: idx for idx, val in enumerate(unique_vals)}

        # Store property type prices for target encoding (use defaults if not available)
        if 'price_per_m2' in df.columns:
            self.feature_stats['province_price_mean'] = df.groupby('province_city')['price_per_m2'].mean().to_dict()
            self.feature_stats['district_price_mean'] = df.groupby('district')['price_per_m2'].mean().to_dict()
            self.feature_stats['property_type_price_mean'] = df.groupby('property_type')['price_per_m2'].mean().to_dict()
        else:
            # Default values for prediction — use TOWNHOUSE as general fallback
            self.feature_stats['province_price_mean'] = {
                prov: prices.get('TOWNHOUSE', 30_000_000)
                for prov, prices in BASE_PRICES_PER_M2.items()
            }
            self.feature_stats['district_price_mean'] = {}
            self.feature_stats['property_type_price_mean'] = {
                'house': 25000000, 'apartment': 22000000, 'land': 15000000,
                'townhouse': 28000000, 'villa': 40000000
            }

        return self

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """
        Transform raw data into feature matrix with property-type-aware masking.

        Per RICS AVM Standard: irrelevant features are zeroed per property type
        to prevent noise from degrading model accuracy in heterogeneous markets.
        """
        from src.domain.property_types import get_zero_mask, to_canonical

        df = df.copy()
        features = []

        # ── Pre-compute type masks for all rows ──────────────────────────────
        # Normalize property_type to canonical key (LAND, TOWNHOUSE, etc.)
        canonical_types = (
            df['property_type']
            .fillna('townhouse')
            .str.lower()
            .apply(lambda x: to_canonical(x).value)
        )
        zero_masks = canonical_types.apply(get_zero_mask)

        def _norm(col, name):
            """Normalize + apply type mask (zero if masked)."""
            raw = self._normalize(col.fillna(self.feature_stats.get(name, {}).get('mean', 0)), name)
            return raw

        def _masked_norm(col, name):
            """Normalize but zero out if feature is masked for this type."""
            raw = self._normalize(col.fillna(self.feature_stats.get(name, {}).get('mean', 0)), name)
            return raw

        # 1. Property Features (with type masking)
        features.append(_norm(df['area_m2'], 'area_m2'))
        # bedrooms: zero for LAND
        raw_bed = self._normalize(df['bedrooms'].fillna(2), 'bedrooms')
        features.append(np.where(canonical_types == 'LAND', 0.0, raw_bed))
        # bathrooms: zero for LAND
        raw_bath = self._normalize(df['bathrooms'].fillna(1), 'bathrooms')
        features.append(np.where(canonical_types == 'LAND', 0.0, raw_bath))
        # floor_count: zero for LAND
        raw_floor = df['floor_count'].fillna(1).values
        features.append(np.where(canonical_types == 'LAND', 0.0, raw_floor))
        # frontage_m: keep (relevant for LAND and BUILDING), zero for APARTMENT
        raw_front = df['frontage_m'].fillna(5).values
        features.append(np.where(canonical_types == 'APARTMENT', 0.0, raw_front))

        # 2. Location Features
        features.append(self._normalize(df['latitude'].fillna(21.0), 'latitude'))
        features.append(self._normalize(df['longitude'].fillna(105.0), 'longitude'))

        # 3. Property Type One-Hot
        for ptype in ['house', 'apartment', 'land', 'townhouse', 'villa']:
            features.append((df['property_type'] == ptype).astype(int).values)

        # 4. Province One-Hot (top provinces from canonical config)
        top_provinces = [p for p in CANONICAL_PROVINCES if p in CANONICAL_CENTER_COORDS]
        for province in top_provinces:
            features.append((df['province_city'] == province).astype(int).values)

        # 5. IoT Features (if available)
        if 'noise_level' in df.columns:
            noise = df['noise_level'].fillna(50)
            features.append(self._normalize(noise, 'noise_level'))
        else:
            features.append(np.zeros(len(df)))

        if 'temperature' in df.columns:
            temp = df['temperature'].fillna(28)
            features.append(self._normalize(temp, 'temperature'))
        else:
            features.append(np.zeros(len(df)))

        if 'humidity' in df.columns:
            humidity = df['humidity'].fillna(70)
            features.append(self._normalize(humidity, 'humidity'))
        else:
            features.append(np.zeros(len(df)))

        if 'light_level' in df.columns:
            light = df['light_level'].fillna(500)
            features.append(self._normalize(light, 'light_level'))
        else:
            features.append(np.zeros(len(df)))

        # 6. Distance Features (computed from lat/lng)
        # Use canonical center_coords from province_config
        distances_to_center = []
        default_center = CANONICAL_CENTER_COORDS.get("Hà Nội", (21.0, 105.0))
        for idx, row in df.iterrows():
            raw_province = row.get('province_city', 'Hà Nội')
            province = normalize_province(raw_province) or "Hà Nội"
            center = CANONICAL_CENTER_COORDS.get(province, default_center)
            lat = row.get('latitude', 21.0)
            lng = row.get('longitude', 105.0)
            dist = self._haversine(center[0], center[1], lat, lng)
            distances_to_center.append(dist)

        features.append(np.array(distances_to_center))

        # 7. Area Type Features
        area_type_map = {'urban_center': 3, 'urban_fringe': 2, 'suburban': 1, 'rural': 0}
        area_types = df['area_type'].map(area_type_map).fillna(1).values
        features.append(area_types)

        # 8. Legal Status Features
        legal_map = {'ownership_certificate': 4, 'land_use_right_certificate': 3, 'pending': 1, 'other': 2}
        legal = df['legal_status'].map(legal_map).fillna(2).values
        features.append(legal)

        # 9. Furnishing Features — zero for LAND (land has no interior)
        furnish_map = {'furnished': 3, 'semi_furnished': 2, 'unfurnished': 0}
        raw_furnish = df['furnishing'].map(furnish_map).fillna(1).values
        features.append(np.where(canonical_types == 'LAND', 0.0, raw_furnish))

        # 10. Target Encoding Features (mean price per m2 by category)
        # Normalize province names before lookup to fix "Ha Noi" vs "Hà Nội" mismatch
        normalized_provinces = df['province_city'].apply(normalize_province)
        province_price = normalized_provinces.map(
            self.feature_stats.get('province_price_mean', {})
        ).fillna(df['price_per_m2'].mean() if 'price_per_m2' in df.columns else 30000000)
        features.append(self._normalize(province_price, 'province_price'))

        # 11. Research-grade reliability features
        research_numeric_cols = [
            'rqs',
            'provenance_score',
            'verification_score',
            'market_anchor_score',
            'timeliness_score',
            'training_weight',
            'evidence_weight',
            'confidence_stage1_score',
            'confidence_prob_a',
            'confidence_prob_b',
            'confidence_prob_c',
            'confidence_prob_d',
        ]
        for col in research_numeric_cols:
            if col in df.columns:
                features.append(self._normalize(df[col].fillna(self.feature_stats.get(col, {}).get('mean', 0)), col))
            else:
                features.append(np.zeros(len(df)))

        if 'anchor_flag_feature' in df.columns:
            features.append(df['anchor_flag_feature'].fillna(0).astype(float).values)
        else:
            features.append(np.zeros(len(df)))

        if 'has_iot_signal_feature' in df.columns:
            features.append(df['has_iot_signal_feature'].fillna(0).astype(float).values)
        else:
            features.append(np.zeros(len(df)))

        # 12. Interaction features (Round 22: explicit interactions for tree models)
        area_bed = (df['area_m2'].fillna(50) * df['bedrooms'].fillna(1)).values
        floor_bed = (df['floor_count'].fillna(1) * df['bedrooms'].fillna(1)).values
        features.append(self._normalize_interaction(area_bed, 'area_bedrooms'))
        floor_bed_std = self.feature_stats.get('floor_bedrooms', {}).get('std', 1) or 1
        features.append((floor_bed - self.feature_stats.get('floor_bedrooms', {}).get('mean', floor_bed.mean()) / floor_bed_std))

        # 13. Spatial KNN price density (Round 22: captures local micro-market conditions)
        if self._knn_data is not None and len(self._knn_data) > 5:
            knn5 = self._knn_price_neighbors(df, k=5)
            knn10 = self._knn_price_neighbors(df, k=10)
            features.append(knn5)
            features.append(knn10)
        else:
            features.append(np.zeros(len(df)))
            features.append(np.zeros(len(df)))

        return np.column_stack(features)

    def _knn_price_neighbors(self, df: pd.DataFrame, k: int) -> np.ndarray:
        """Compute avg price/m2 of K nearest neighbors in lat/lng space."""
        if self._knn_data is None or len(self._knn_data) < k:
            return np.zeros(len(df))
        ref_coords = self._knn_data[:, :2].astype(float)
        ref_prices = self._knn_data[:, 2].astype(float)
        coords = df[['latitude', 'longitude']].fillna(21.0).values.astype(float)
        results = np.zeros(len(df))
        R = 6371.0
        for i in range(len(df)):
            lat_i, lng_i = coords[i]
            dlat = np.radians(ref_coords[:, 0] - lat_i)
            dlon = np.radians(ref_coords[:, 1] - lng_i)
            a = (np.sin(dlat / 2) ** 2 +
                 np.cos(np.radians(lat_i)) * np.cos(np.radians(ref_coords[:, 0])) * np.sin(dlon / 2) ** 2)
            c = 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
            distances = R * c
            k_actual = min(k, len(distances) - 1)
            nearest_idx = np.argpartition(distances, k_actual)[:k_actual]
            results[i] = ref_prices[nearest_idx].mean()
        return results

    def _normalize_interaction(self, values: np.ndarray, name: str) -> np.ndarray:
        """Normalize an interaction feature using fit statistics."""
        stats = self.feature_stats.get(name, {})
        mean = stats.get('mean', np.nanmean(values))
        std = stats.get('std', 1.0)
        if std == 0 or np.isnan(std):
            std = 1.0
        return (values - mean) / std

    def _normalize(self, series: pd.Series, feature_name: str) -> np.ndarray:
        """Normalize a feature using z-score normalization."""
        stats = self.feature_stats.get(feature_name, {'mean': series.mean(), 'std': series.std()})
        mean_value = stats.get('mean', series.mean())
        std = stats.get('std', 1)
        if pd.isna(mean_value):
            mean_value = 0
        if pd.isna(std) or std == 0:
            std = 1
        return ((series.fillna(mean_value) - mean_value) / std).values

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate haversine distance in km."""
        R = 6371  # Earth radius in km
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        return R * c

    def get_feature_names(self) -> List[str]:
        """Return list of feature names."""
        names = [
            'area_m2_norm', 'bedrooms_norm', 'bathrooms_norm', 'floor_count', 'frontage_m',
            'latitude_norm', 'longitude_norm'
        ]

        # Property types
        names.extend(['is_house', 'is_apartment', 'is_land', 'is_townhouse', 'is_villa'])

        # Provinces
        names.extend(['province_HN', 'province_HCM', 'province_DN', 'province_HP', 'province_CT', 'province_BD'])

        # IoT
        names.extend(['noise_level_norm', 'temperature_norm', 'humidity_norm', 'light_level_norm'])

        # Distance
        names.append('distance_to_center')

        # Other
        names.extend(['area_type', 'legal_status', 'furnishing', 'province_price_mean'])

        # Research-grade data trust features
        names.extend([
            'rqs_norm',
            'provenance_score_norm',
            'verification_score_norm',
            'market_anchor_score_norm',
            'timeliness_score_norm',
            'training_weight_norm',
            'evidence_weight_norm',
            'confidence_stage1_score_norm',
            'confidence_prob_a_norm',
            'confidence_prob_b_norm',
            'confidence_prob_c_norm',
            'confidence_prob_d_norm',
            'anchor_flag_feature',
            'has_iot_signal_feature',
            # Interaction features (Round 22)
            'area_bedrooms_interaction',
            'floor_bedrooms_interaction',
            # Spatial KNN price density (Round 22)
            'knn5_price_density',
            'knn10_price_density',
        ])

        return names


def create_features_from_properties(properties: List[Dict]) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Create feature matrix and target vector from property records.
    """
    df = pd.DataFrame(properties)

    # Target: price
    y = df['price'].values

    # Features
    engineer = FeatureEngineer()
    engineer.fit(df)
    X = engineer.transform(df)
    feature_names = engineer.get_feature_names()

    return X, y, feature_names
