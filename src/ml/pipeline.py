"""
ML Pipeline for Real Estate AVM.
Handles model training, evaluation, and prediction with full traceability.
"""

import os
import sys
from pathlib import Path
import pickle
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from sklearn.base import clone
from sklearn.model_selection import KFold, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    recall_score,
    r2_score,
)
import warnings
warnings.filterwarnings('ignore')

from src.backend.quality_assessment import (
    build_confidence_training_rows,
    build_training_quality_profiles,
    summarize_training_quality_profiles,
)
from src.config.province_config import SCOPE_DISTRICTS

# ==============================================================================
# GEOGRAPHIC SCOPE — Giữ nguyên 6 quận gốc (ML train trên 6 quận này)
# Mở rộng scope = retrain model → để sau khi có đủ dữ liệu
# ==============================================================================
ALLOWED_DISTRICTS = [
    ("Hà Nội", "Quận Cầu Giấy"),
    ("Hà Nội", "Quận Thanh Xuân"),
    ("Hà Nội", "Quận Đống Đa"),
    ("TP. Hồ Chí Minh", "Quận 7"),
    ("TP. Hồ Chí Minh", "Quận Bình Thạnh"),
    ("TP. Hồ Chí Minh", "Quận Tân Bình"),
]

# Try to import XGBoost
try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

# Try to import SHAP
try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False


class MLPipeline:
    """
    Machine Learning Pipeline for Real Estate Price Prediction.
    Supports multiple algorithms and provides full model versioning.
    """

    def __init__(self, model_dir: str = None):
        # Canonical model dir: PROJECT_ROOT/models (not src/models)
        import pathlib
        project_root = pathlib.Path(__file__).resolve().parent.parent.parent
        if model_dir is None:
            model_dir = project_root / "models"
        self.model_dir = str(model_dir)
        os.makedirs(model_dir, exist_ok=True)

        self.models = {}
        self.best_model = None
        self.best_model_name = None
        self.scaler = StandardScaler()
        self.feature_names = []
        self.metadata = {}
        self.is_fitted = False
        self.training_quality_profiles = []
        self.training_quality_summary = {}
        self.quantile_models = {}
        self.conformal_calibration = {}
        self.confidence_models = {}
        self.confidence_best_model = None
        self.confidence_best_model_name = None
        self.confidence_feature_names = []
        self.confidence_metadata = {}
        self.confidence_training_rows = []
        self.regression_confidence_signal = None

    def _build_features(self, prop) -> np.ndarray:
        """
        Build feature vector from a single Property ORM object.
        Produces 41 features matching the trained model.
        """
        area = float(prop.area_m2 or 80)
        bedrooms = int(prop.bedrooms or 0)
        bathrooms = int(prop.bathrooms or 0)
        floor_count = int(prop.floor_count or 1)
        frontage = float(prop.frontage_m or 5)
        lat = float(prop.latitude or 21.0)
        lng = float(prop.longitude or 105.8)
        ptype = str(prop.property_type or 'apartment').lower()
        province = str(prop.province_city or 'Hà Nội')

        def norm(val, mn, mx):
            return (val - mn) / (mx - mn + 1e-9) if mx != mn else 0.5

        feat = []
        # 1. Property features
        feat.append(norm(area, 15, 500))  # area_m2_norm
        feat.append(norm(bedrooms, 0, 6))  # bedrooms_norm
        feat.append(norm(bathrooms, 0, 4))  # bathrooms_norm
        feat.append(float(floor_count))  # floor_count
        feat.append(float(frontage))  # frontage_m

        # 2. Location
        feat.append(norm(lat, 10.5, 21.5))  # latitude_norm
        feat.append(norm(lng, 104.5, 107.0))  # longitude_norm

        # 3. Property type one-hot
        feat.append(1 if ptype in ('house', 'villa') else 0)  # is_house
        feat.append(1 if ptype == 'apartment' else 0)  # is_apartment
        feat.append(1 if ptype == 'land' else 0)  # is_land
        feat.append(1 if ptype == 'townhouse' else 0)  # is_townhouse
        feat.append(1 if ptype == 'villa' else 0)  # is_villa

        # 4. Province one-hot
        feat.append(1 if 'Hà Nội' in province else 0)  # province_HN
        feat.append(1 if 'Hồ Chí Minh' in province else 0)  # province_HCM
        feat.append(1 if 'Đà Nẵng' in province else 0)  # province_DN
        feat.append(1 if 'Hải Phòng' in province else 0)  # province_HP
        feat.append(1 if 'Cần Thơ' in province else 0)  # province_CT
        feat.append(1 if 'Bình Dương' in province else 0)  # province_BD

        # 5. IoT
        feat.append(norm(float(prop.noise_level or 50), 30, 80))  # noise_level_norm
        feat.append(norm(float(prop.temperature or 28), 20, 40))  # temperature_norm
        feat.append(norm(float(prop.humidity or 70), 40, 100))  # humidity_norm
        feat.append(norm(float(prop.light_level or 300), 100, 600))  # light_level_norm

        # 6. Distance to center
        if 'Hồ Chí Minh' in province:
            center = (10.78, 106.68)
        elif 'Hà Nội' in province:
            center = (21.03, 105.85)
        else:
            center = (lat, lng)
        dist = ((lat - center[0])**2 + (lng - center[1])**2)**0.5
        feat.append(norm(dist, 0, 2))  # distance_to_center

        # 7. Categorical encoded
        feat.append({'apartment': 0, 'townhouse': 1, 'house': 2, 'land': 3, 'villa': 4}.get(ptype, 0))  # area_type
        feat.append(1.0 if str(prop.legal_status or '').lower() == 'full_ownership' else 0.0)  # legal_status
        feat.append({'furnished': 1.0, 'semi_furnished': 0.5, 'unfurnished': 0.0}.get(
            str(prop.furnishing or 'unknown').lower(), 0.0))  # furnishing

        # 8. Province price mean (normalized)
        feat.append(0.9)  # province_price_mean

        # 9. Quality features — computed from real quality_assessment module
        evidence_tier = str(prop.evidence_tier or "E3")
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
            from src.backend.quality_assessment import build_training_quality_profiles

            record = {
                "id": prop.id,
                "property_type": ptype,
                "province_city": province,
                "district": prop.district,
                "data_origin_type": prop.data_origin_type,
                "verification_status": prop.verification_status,
                "evidence_tier": evidence_tier,
                "collection_method": prop.collection_method,
                "price": prop.price,
                "price_per_m2": prop.price_per_m2,
                "area_m2": prop.area_m2,
                "bedrooms": prop.bedrooms,
                "bathrooms": prop.bathrooms,
                "latitude": lat,
                "longitude": lng,
                "gps_lat": prop.gps_lat,
                "gps_lng": prop.gps_lng,
                "noise_level": prop.noise_level,
                "temperature": prop.temperature,
                "humidity": prop.humidity,
                "light_level": prop.light_level,
                "source_name": prop.source_name,
                "source_url": prop.source_url,
                "source_screenshot_path": prop.source_screenshot_path,
                "evidence_photo_path": prop.evidence_photo_path,
                "field_notes": prop.field_notes,
                "collected_by": prop.collected_by,
                "verified_by": prop.verified_by,
                "verified_at": prop.verified_at,
                "legal_status": prop.legal_status,
                "furnishing": prop.furnishing,
                "frontage_m": prop.frontage_m,
                "floor_count": prop.floor_count,
                "image_url": prop.image_url,
            }
            profiles = build_training_quality_profiles([record])
            if profiles:
                prof = profiles[0]
                rqs = float(prof["rqs"])
                provenance = float(prof["provenance_score"])
                verification = float(prof["verification_score"])
                market_anchor = float(prof["market_anchor_score"])
                timeliness = float(prof["timeliness_score"])
                training_w = float(prof["training_weight"])
                evidence_w = float(prof["evidence_weight"])
                anchor_flag = 1.0 if prof["anchor_flag"] else 0.0
                has_iot = 1.0 if prof["has_iot"] else 0.0
            else:
                raise ValueError("No profile returned")
        except Exception:
            tier_defaults = {
                "E5": dict(rqs=8.5, provenance=9.0, verification=9.0, market_anchor=9.5, timeliness=8.5, training_w=0.95, evidence_w=1.0),
                "E4": dict(rqs=7.0, provenance=7.5, verification=7.5, market_anchor=8.0, timeliness=7.5, training_w=0.80, evidence_w=0.85),
                "E3": dict(rqs=5.5, provenance=6.0, verification=6.0, market_anchor=6.5, timeliness=6.0, training_w=0.60, evidence_w=0.65),
                "E2": dict(rqs=3.5, provenance=4.0, verification=4.0, market_anchor=4.5, timeliness=4.0, training_w=0.30, evidence_w=0.45),
                "E1": dict(rqs=2.0, provenance=2.0, verification=2.0, market_anchor=2.2, timeliness=2.0, training_w=0.10, evidence_w=0.20),
            }
            d = tier_defaults.get(evidence_tier, tier_defaults["E3"])
            rqs, provenance, verification = d["rqs"], d["provenance"], d["verification"]
            market_anchor, timeliness, training_w = d["market_anchor"], d["timeliness"], d["training_w"]
            evidence_w = d["evidence_w"]
            anchor_flag = 1.0 if evidence_tier in ("E4", "E5") else 0.0
            has_iot = 1.0 if prop.noise_level is not None else 0.0

        # Z-score normalization matching FeatureEngineer._normalize
        # Using training-era statistics from quality_assessment module
        def znorm(val, mean, std):
            return (val - mean) / (std + 1e-9)

        feat.append(znorm(rqs, 5.5, 2.0))         # rqs_norm
        feat.append(znorm(provenance, 5.5, 2.0))   # provenance_score_norm
        feat.append(znorm(verification, 5.5, 2.0)) # verification_score_norm
        feat.append(znorm(market_anchor, 5.5, 2.5)) # market_anchor_score_norm
        feat.append(znorm(timeliness, 5.5, 2.0))   # timeliness_score_norm
        feat.append(znorm(training_w, 0.55, 0.25)) # training_weight_norm
        feat.append(znorm(evidence_w, 0.55, 0.25)) # evidence_weight_norm

        # Confidence features — tier-based defaults (no classifier at inference time)
        tier_conf_defaults = {
            "E5": dict(stage=7.0, pa=0.0, pb=0.0, pc=0.6, pd=0.4),
            "E4": dict(stage=6.2, pa=0.0, pb=0.1, pc=0.6, pd=0.3),
            "E3": dict(stage=5.5, pa=0.0, pb=0.1, pc=0.6, pd=0.3),
            "E2": dict(stage=4.5, pa=0.0, pb=0.1, pc=0.5, pd=0.4),
            "E1": dict(stage=3.5, pa=0.1, pb=0.1, pc=0.4, pd=0.5),
        }
        cd = tier_conf_defaults.get(evidence_tier, tier_conf_defaults["E3"])
        feat.append(cd["stage"])   # confidence_stage1_score_norm (no z-norm — model uses raw 0-10)
        feat.append(cd["pa"])       # confidence_prob_a_norm
        feat.append(cd["pb"])      # confidence_prob_b_norm
        feat.append(cd["pc"])      # confidence_prob_c_norm
        feat.append(cd["pd"])      # confidence_prob_d_norm

        # Override anchor_flag and has_iot with real values
        feat[-14] = anchor_flag  # anchor_flag_feature
        feat[-13] = has_iot      # has_iot_signal_feature

        # 10. Binary flags (anchor_flag and has_iot already set above)
        # Remaining binary/interaction/KNN features below

        # 11. Interaction features
        feat.append(float(bedrooms) * norm(area, 15, 500))  # area_bedrooms_interaction
        feat.append(float(floor_count) * norm(bedrooms, 0, 6))  # floor_bedrooms_interaction

        # 12. KNN density (approximate)
        feat.append(max(0, 1 - dist / 2))  # knn5_price_density
        feat.append(max(0, 1 - dist / 2) * 0.8)  # knn10_price_density

        # Pad to 53 features if model was trained with extra quality/confidence columns
        # (FeatureEngineer may see extra columns added by _append_quality_features)
        n_expected = self.feature_names.__len__() if self.feature_names else 53
        while len(feat) < n_expected:
            feat.append(0.0)
        return np.array(feat[:n_expected], dtype=np.float64)

    def load_data_from_db(self, db_session, include_self_collected: bool = True) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Load and prepare data from database.
        CHỈ lấy dữ liệu từ 6 quận được phép (ALLOWED_DISTRICTS).
        """
        from src.backend.models import Property
        from sqlalchemy import or_, and_

        # Build district filter
        district_filters = [
            and_(
                Property.province_city == prov,
                Property.district == district
            )
            for prov, district in ALLOWED_DISTRICTS
        ]

        query = db_session.query(Property).filter(
            or_(*district_filters),
            Property.record_status != "archived",
            Property.price.isnot(None),
            Property.price > 0,
            Property.area_m2.isnot(None),
            Property.area_m2 > 0
        )

        if not include_self_collected:
            query = query.filter(Property.data_origin_type != "self_collected")

        properties = query.all()

        if len(properties) < 50:
            raise ValueError(
                f"INSUFFICIENT_DATA: Chỉ có {len(properties)} bản ghi trong 6 quận được phép. "
                f"Cần tối thiểu 50 bản ghi để train ML model. "
                f"Hành động: python scripts/seed_data.py --seed-demo 30 "
                f"(hoặc: python scripts/seed_data.py --collect để thu thập dữ liệu thực)"
            )

        data = []
        for p in properties:
            record = {
                'id': p.id,
                'property_type': p.property_type,
                'province_city': p.province_city,
                'district': p.district,
                'ward': p.ward,
                'area_m2': p.area_m2,
                'bedrooms': p.bedrooms or 0,
                'bathrooms': p.bathrooms or 0,
                'floor_count': p.floor_count or 1,
                'frontage_m': p.frontage_m or 5,
                'legal_status': p.legal_status,
                'furnishing': p.furnishing,
                'price': p.price,
                'price_per_m2': p.price_per_m2,
                'latitude': p.latitude or 21.0,
                'longitude': p.longitude or 105.0,
                'area_type': p.area_type,
                'data_origin_type': p.data_origin_type,
                'record_status': p.record_status,
                'verification_status': p.verification_status,
                'source_name': p.source_name,
                'source_url': p.source_url,
                'source_page_title': p.source_page_title,
                'source_collected_at': p.source_collected_at,
                'source_access_method': p.source_access_method,
                'source_screenshot_path': p.source_screenshot_path,
                'verification_note': p.verification_note,
                'verified_by': p.verified_by,
                'verified_at': p.verified_at,
                'collected_by': p.collected_by,
                'collected_at': p.collected_at,
                'collection_method': p.collection_method,
                'field_note': p.field_note,
                'evidence_photo_path': p.evidence_photo_path,
                'created_at': p.created_at,
                'description': p.description,
                # IoT features
                'noise_level': p.noise_level,
                'temperature': p.temperature,
                'humidity': p.humidity,
                'light_level': p.light_level,
                'gps_lat': p.gps_lat,
                'gps_lng': p.gps_lng,
                'area_quality_score': p.area_quality_score,
                'image_url': p.image_url,
            }
            data.append(record)

        df = pd.DataFrame(data)
        y = df['price']

        return df, y

    def load_data_from_csv(self, csv_path: str) -> Tuple[pd.DataFrame, pd.Series]:
        """Load data from CSV file."""
        df = pd.read_csv(csv_path)
        y = df['price']
        return df, y

    def _append_quality_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Derive research-standard quality features for training.
        These become both extra model features and per-record sample weights.
        """
        quality_profiles = build_training_quality_profiles(df.to_dict("records"))
        self.training_quality_profiles = quality_profiles
        self.training_quality_summary = summarize_training_quality_profiles(quality_profiles)

        quality_frame = pd.DataFrame(
            [
                {
                    "rqs": profile["rqs"],
                    "training_weight": profile["training_weight"],
                    "provenance_score": profile["provenance_score"],
                    "verification_score": profile["verification_score"],
                    "market_anchor_score": profile["market_anchor_score"],
                    "timeliness_score": profile["timeliness_score"],
                    "evidence_weight": profile["evidence_weight"],
                    "anchor_flag_feature": 1 if profile["anchor_flag"] else 0,
                    "has_iot_signal_feature": 1 if profile["has_iot"] else 0,
                }
                for profile in quality_profiles
            ]
        )

        return pd.concat([df.reset_index(drop=True), quality_frame], axis=1)

    def _train_confidence_stage(self, df: pd.DataFrame, y: np.ndarray = None) -> pd.DataFrame:
        """
        Train stage-1 prediction-confidence classifier with the production P-CONF gate.

        P-CONF is not the same as data provenance. Its strongest guard is sample depth:
        A requires at least 800 effective near-comparable samples, B requires 300, and
        sparse cases are capped even when their source evidence is good.
        """
        confidence_rows = build_confidence_training_rows(df.to_dict("records"))
        self.confidence_training_rows = confidence_rows
        confidence_df = pd.DataFrame(confidence_rows)
        if confidence_df.empty:
            return df

        feature_cols = [
            "support_volume_score",
            "support_quality_score",
            "support_completeness_score",
            "support_anchor_share",
            "support_source_count",
            "support_volatility",
            "district_support_count",
            "province_support_count",
            "property_type_support_count",
            "effective_sample_size",
            "input_completeness_score",
            "input_iot_signal_count",
            "input_has_legal_status",
            "input_has_coordinates",
            "input_has_furnishing",
            "local_price_gap_ratio",
            "self_collected_hint",
        ]
        self.confidence_feature_names = feature_cols

        X_conf = confidence_df[feature_cols].fillna(0.0).astype(float).values

        def _gate_label(row) -> str:
            neff = float(row.get("effective_sample_size", 0.0) or 0.0)
            support_quality = float(row.get("support_quality_score", 0.0) or 0.0)
            completeness = float(row.get("support_completeness_score", 0.0) or 0.0)
            source_count = int(row.get("support_source_count", 0) or 0)
            volatility = float(row.get("support_volatility", 0.12) or 0.12)
            good_quality = support_quality >= 7.0 and completeness >= 6.5 and source_count >= 2
            stable_market = volatility <= 0.35
            if neff >= 800 and good_quality and stable_market:
                return "A"
            if neff >= 300 and support_quality >= 6.0 and source_count >= 2:
                return "B"
            if neff >= 100 or (neff >= 30 and support_quality >= 5.5):
                return "C"
            return "D"

        y_conf = confidence_df.apply(_gate_label, axis=1).astype(str).values
        confidence_df["pconf_gate_label"] = y_conf

        unique_labels, label_counts = np.unique(y_conf, return_counts=True)
        stratify_target = y_conf if len(unique_labels) > 1 and np.min(label_counts) >= 2 else None

        X_train, X_temp, y_train, y_temp = train_test_split(
            X_conf, y_conf, test_size=0.30, random_state=42, stratify=stratify_target,
        )
        temp_labels, temp_counts = np.unique(y_temp, return_counts=True)
        stratify_temp = y_temp if len(temp_labels) > 1 and np.min(temp_counts) >= 2 else None
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp, test_size=0.50, random_state=42, stratify=stratify_temp,
        )

        candidate_models = {
            "EntropyTree": DecisionTreeClassifier(
                criterion="entropy", max_depth=6, min_samples_split=20,
                min_samples_leaf=8, class_weight="balanced", random_state=42,
            ),
            "GiniTree": DecisionTreeClassifier(
                criterion="gini", max_depth=7, min_samples_split=18,
                min_samples_leaf=8, class_weight="balanced", random_state=42,
            ),
            "HybridConfidenceForest": RandomForestClassifier(
                n_estimators=180, max_depth=9, min_samples_split=16,
                min_samples_leaf=6, class_weight="balanced_subsample",
                random_state=42, n_jobs=1,
            ),
        }

        validation_results = {}
        trained_candidates = {}
        for name, model in candidate_models.items():
            model.fit(X_train, y_train)
            val_pred = model.predict(X_val)
            validation_results[name] = {
                "accuracy": float(accuracy_score(y_val, val_pred)),
                "precision_macro": float(precision_score(y_val, val_pred, average="macro", zero_division=0)),
                "recall_macro": float(recall_score(y_val, val_pred, average="macro", zero_division=0)),
                "f1_macro": float(f1_score(y_val, val_pred, average="macro", zero_division=0)),
            }
            trained_candidates[name] = model

        best_name = max(validation_results, key=lambda key: validation_results[key]["f1_macro"])
        best_model = trained_candidates[best_name]
        test_pred = best_model.predict(X_test)
        test_metrics = {
            "accuracy": float(accuracy_score(y_test, test_pred)),
            "precision_macro": float(precision_score(y_test, test_pred, average="macro", zero_division=0)),
            "recall_macro": float(recall_score(y_test, test_pred, average="macro", zero_division=0)),
            "f1_macro": float(f1_score(y_test, test_pred, average="macro", zero_division=0)),
        }

        final_model = clone(candidate_models[best_name])
        final_model.fit(X_conf, y_conf)
        self.confidence_best_model = final_model
        self.confidence_best_model_name = best_name
        self.confidence_models = trained_candidates

        class_score_map = {"A": 9.2, "B": 7.6, "C": 6.1, "D": 4.2}
        probabilities = final_model.predict_proba(X_conf)
        classes = list(final_model.classes_)
        stage_score = np.zeros(len(confidence_df), dtype=float)
        for idx, label in enumerate(classes):
            stage_score += probabilities[:, idx] * class_score_map.get(label, 5.5)

        confidence_augmented = pd.DataFrame({
            "confidence_stage1_score": np.round(stage_score, 4),
            "confidence_prob_a": np.round(probabilities[:, classes.index("A")], 4) if "A" in classes else np.zeros(len(confidence_df)),
            "confidence_prob_b": np.round(probabilities[:, classes.index("B")], 4) if "B" in classes else np.zeros(len(confidence_df)),
            "confidence_prob_c": np.round(probabilities[:, classes.index("C")], 4) if "C" in classes else np.zeros(len(confidence_df)),
            "confidence_prob_d": np.round(probabilities[:, classes.index("D")], 4) if "D" in classes else np.zeros(len(confidence_df)),
        })

        tree_model = final_model
        if hasattr(final_model, "estimators_") and final_model.estimators_:
            tree_model = final_model.estimators_[0]

        try:
            tree_rules = export_text(tree_model, feature_names=feature_cols, max_depth=4)
        except Exception:
            tree_rules = "Tree rules unavailable"

        label_distribution = {str(k): int(v) for k, v in zip(*np.unique(y_conf, return_counts=True))}
        self.confidence_metadata = {
            "stage_name": "P-CONF Prediction Confidence — sample-depth gated classifier",
            "best_model": best_name,
            "feature_names": feature_cols,
            "validation_results": validation_results,
            "test_metrics": test_metrics,
            "split_summary": {
                "train_size": int(len(X_train)),
                "validation_size": int(len(X_val)),
                "test_size": int(len(X_test)),
                "strategy": "70/15/15 holdout split",
            },
            "label_distribution": label_distribution,
            "tree_rules": tree_rules,
            "label_source": "P-CONF_sample_depth_gate_v2",
            "grade_policy": {
                "A": "effective_sample_size >= 800 plus good quality, multi-source support and stable market",
                "B": "effective_sample_size >= 300 plus acceptable quality and multi-source support",
                "C": "effective_sample_size >= 100, or >=30 with acceptable support quality",
                "D": "sparse support; prediction confidence must stay capped",
            },
        }

        return pd.concat([df.reset_index(drop=True), confidence_augmented], axis=1)

    def preprocess(self, df: pd.DataFrame, y: np.ndarray = None) -> np.ndarray:
        """
        Preprocess data and create features.
        Pass y for external confidence labels (OOF-based, no leakage).
        """
        from src.ml.feature_engineering import FeatureEngineer

        prepared_df = self._append_quality_features(df.copy())
        prepared_df = self._train_confidence_stage(prepared_df, y=y)
        self.regression_confidence_signal = prepared_df.get("confidence_stage1_score", pd.Series(np.zeros(len(prepared_df)))).values

        engineer = FeatureEngineer()
        engineer.fit(prepared_df)
        X = engineer.transform(prepared_df)
        self.feature_names = engineer.get_feature_names()

        return X

    def _fit_with_optional_weights(self, model, X_train, y_train, sample_weight=None):
        """Fit a model while gracefully handling estimators without sample_weight."""
        if sample_weight is None:
            model.fit(X_train, y_train)
            return
        try:
            model.fit(X_train, y_train, sample_weight=sample_weight)
        except TypeError:
            model.fit(X_train, y_train)

    def _weighted_cv_mae(self, model, X, y, sample_weight=None, folds: int = 5) -> Tuple[float, float]:
        """Cross-validation that respects research weights when supported."""
        splitter = KFold(n_splits=folds, shuffle=True, random_state=42)
        scores = []
        for train_idx, val_idx in splitter.split(X):
            candidate = clone(model)
            train_weights = sample_weight[train_idx] if sample_weight is not None else None
            val_weights = sample_weight[val_idx] if sample_weight is not None else None
            self._fit_with_optional_weights(candidate, X[train_idx], y[train_idx], train_weights)
            y_pred = candidate.predict(X[val_idx])
            mae = mean_absolute_error(y[val_idx], y_pred, sample_weight=val_weights)
            scores.append(mae)
        return float(np.mean(scores)), float(np.std(scores))

    def _build_conformal_calibration(self, y_true, y_pred, confidence_signal) -> Dict[str, Dict[str, float]]:
        """
        Group residual ratios by confidence band so interval width can be adapted later.
        """
        calibration: Dict[str, Dict[str, float]] = {}
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)
        confidence_signal = np.asarray(confidence_signal, dtype=float)

        residual_ratio = np.abs(y_true - y_pred) / np.maximum(np.abs(y_true), 1.0)
        for band, lower, upper in [
            ("A", 8.5, np.inf),
            ("B", 7.0, 8.5),
            ("C", 5.5, 7.0),
            ("D", -np.inf, 5.5),
        ]:
            mask = (confidence_signal >= lower) & (confidence_signal < upper)
            band_values = residual_ratio[mask]
            if len(band_values) == 0:
                calibration[band] = {"count": 0, "ratio_q90": 0.12, "ratio_median": 0.08}
                continue
            calibration[band] = {
                "count": int(len(band_values)),
                "ratio_q90": float(np.quantile(band_values, 0.90)),
                "ratio_median": float(np.median(band_values)),
            }
        return calibration

    def train(self, X: np.ndarray, y: np.ndarray, test_size: float = 0.15) -> Dict:
        """
        Train the price model with a full train/validation/test workflow.
        Stage 1 confidence outputs are already injected into X during preprocess.
        """
        print("\n" + "=" * 60)
        print("ML PIPELINE - RESEARCH TRAINING")
        print("=" * 60)

        sample_weight = None
        if self.training_quality_profiles:
            sample_weight = np.array([item["training_weight"] for item in self.training_quality_profiles], dtype=float)

        confidence_signal = self.regression_confidence_signal
        split_args = [X, y]
        if sample_weight is not None:
            split_args.append(sample_weight)
        if confidence_signal is not None:
            split_args.append(confidence_signal)

        split_result = train_test_split(*split_args, test_size=test_size, random_state=42)
        if sample_weight is not None and confidence_signal is not None:
            X_trainval, X_test, y_trainval, y_test, w_trainval, w_test, c_trainval, c_test = split_result
        elif sample_weight is not None:
            X_trainval, X_test, y_trainval, y_test, w_trainval, w_test = split_result
            c_trainval = None
            c_test = None
        else:
            X_trainval, X_test, y_trainval, y_test = split_result
            w_trainval = None
            w_test = None
            c_trainval = None
            c_test = None

        trainval_args = [X_trainval, y_trainval]
        if w_trainval is not None:
            trainval_args.append(w_trainval)
        if c_trainval is not None:
            trainval_args.append(c_trainval)

        trainval_split = train_test_split(*trainval_args, test_size=(0.15 / 0.85), random_state=42)
        if w_trainval is not None and c_trainval is not None:
            X_train, X_val, y_train, y_val, w_train, w_val, c_train, c_val = trainval_split
        elif w_trainval is not None:
            X_train, X_val, y_train, y_val, w_train, w_val = trainval_split
            c_train = None
            c_val = None
        else:
            X_train, X_val, y_train, y_val = trainval_split
            w_train = None
            w_val = None
            c_train = None
            c_val = None

        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        X_test_scaled = self.scaler.transform(X_test)
        X_trainval_scaled = self.scaler.transform(X_trainval)

        print(f"\nTraining data: {len(X_train)} samples")
        print(f"Validation data: {len(X_val)} samples")
        print(f"Test data: {len(X_test)} samples")
        print(f"Features: {X_train.shape[1]}")
        if self.training_quality_summary:
            print(f"Average RQS: {self.training_quality_summary.get('avg_rqs', 0):.2f}")
            print(f"Average training weight: {self.training_quality_summary.get('avg_training_weight', 0):.3f}")

        models = {
            "QualityWeightedRandomForest": RandomForestRegressor(
                n_estimators=260,
                max_depth=18,
                min_samples_split=4,
                min_samples_leaf=2,
                max_features="sqrt",
                bootstrap=True,
                random_state=42,
                n_jobs=1,
            ),
            "ReliabilityAwareGradientBoosting": GradientBoostingRegressor(
                n_estimators=260,
                max_depth=6,
                learning_rate=0.05,
                min_samples_split=5,
                subsample=0.85,
                random_state=42,
            ),
        }

        # XGBoost ENABLED (Round 22) — confidence stage now uses stored evidence_tier
        # instead of recomputed rule_grade → labels are cleaner → XGBoost should perform.
        if HAS_XGBOOST:
            models["ConfidenceWeightedXGBoost"] = xgb.XGBRegressor(
                n_estimators=260,
                max_depth=8,
                learning_rate=0.05,
                subsample=0.85,
                colsample_bytree=0.8,
                min_child_weight=3,
                gamma=0.1,
                reg_alpha=0.15,
                reg_lambda=1.2,
                max_delta_step=2,
                objective="reg:squarederror",
                tree_method="hist",
                random_state=42,
                n_jobs=-1,
            )

        validation_results = {}
        candidate_models = {}
        for name, model in models.items():
            print(f"\n--- Training {name} ---")
            self._fit_with_optional_weights(model, X_train_scaled, y_train, w_train)
            val_pred = model.predict(X_val_scaled)
            val_mae = mean_absolute_error(y_val, val_pred, sample_weight=w_val)
            val_rmse = np.sqrt(mean_squared_error(y_val, val_pred, sample_weight=w_val))
            val_r2 = r2_score(y_val, val_pred, sample_weight=w_val)
            cv_mae_mean, cv_mae_std = self._weighted_cv_mae(model, X_train_scaled, y_train, w_train)

            validation_results[name] = {
                "mae": float(val_mae),
                "rmse": float(val_rmse),
                "r2": float(val_r2),
                "cv_mae_mean": float(cv_mae_mean),
                "cv_mae_std": float(cv_mae_std),
            }
            candidate_models[name] = model

            print(f"  Validation MAE: {val_mae:,.0f} VND")
            print(f"  Validation RMSE: {val_rmse:,.0f} VND")
            print(f"  Validation R2: {val_r2:.4f}")
            print(f"  Weighted CV MAE: {cv_mae_mean:,.0f} (+/- {cv_mae_std:,.0f})")

        best_name = min(validation_results, key=lambda key: validation_results[key]["mae"])
        best_validation_model = candidate_models[best_name]
        val_pred = best_validation_model.predict(X_val_scaled)
        self.conformal_calibration = self._build_conformal_calibration(
            y_true=y_val,
            y_pred=val_pred,
            confidence_signal=c_val if c_val is not None else np.full(len(y_val), 6.0),
        )

        self.scaler.fit(X_trainval)
        X_trainval_scaled = self.scaler.transform(X_trainval)
        X_test_scaled = self.scaler.transform(X_test)

        self.models = {}
        for name, model in models.items():
            final_candidate = clone(model)
            self._fit_with_optional_weights(final_candidate, X_trainval_scaled, y_trainval, w_trainval)
            self.models[name] = final_candidate

        self.best_model = self.models[best_name]
        self.best_model_name = best_name

        test_pred = self.best_model.predict(X_test_scaled)

        # Robust metrics — less affected by outliers
        abs_errors = np.abs(y_test - test_pred)
        median_ae = float(np.median(abs_errors))

        # MAPE (only for records with realistic prices > 500M)
        mape_mask = y_test > 500_000_000
        if mape_mask.sum() > 0:
            mape = float(np.mean(np.abs(y_test[mape_mask] - test_pred[mape_mask]) / y_test[mape_mask])) * 100
        else:
            mape = None

        results = {
            name: validation_results[name].copy()
            for name in validation_results
        }
        results[best_name].update({
            "test_mae": float(mean_absolute_error(y_test, test_pred, sample_weight=w_test)),
            "test_median_ae": median_ae,
            "test_mape": mape,
            "test_rmse": float(np.sqrt(mean_squared_error(y_test, test_pred, sample_weight=w_test))),
            "test_r2": float(r2_score(y_test, test_pred, sample_weight=w_test)),
            "n_test": int(len(y_test)),
        })

        print(f"\n*** Best Model: {best_name} ***")
        print(f"    Validation MAE:  {results[best_name]['mae']:,.0f} VND")
        print(f"    Test MAE:      {results[best_name]['test_mae']:,.0f} VND")
        print(f"    Test MedianAE: {results[best_name]['test_median_ae']:,.0f} VND")
        if mape:
            print(f"    Test MAPE:     {results[best_name]['test_mape']:.1f}%")
        print(f"    Test R2:       {results[best_name]['test_r2']:.4f}")

        self.quantile_models = {
            "lower": GradientBoostingRegressor(
                loss="quantile",
                alpha=0.10,
                n_estimators=180,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.85,
                random_state=42,
            ),
            "upper": GradientBoostingRegressor(
                loss="quantile",
                alpha=0.90,
                n_estimators=180,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.85,
                random_state=42,
            ),
        }
        for quantile_name, quantile_model in self.quantile_models.items():
            self._fit_with_optional_weights(quantile_model, X_trainval_scaled, y_trainval, w_trainval)

        self.is_fitted = True
        self.metadata = {
            "training_standard": "CVX-BDS/IoT 1.1-VN Research Extension",
            "best_model": best_name,
            "all_results": results,
            "train_size": len(X_train),
            "validation_size": len(X_val),
            "test_size": len(X_test),
            "n_features": X_train.shape[1],
            "feature_names": self.feature_names,
            "trained_at": datetime.now().isoformat(),
            "training_quality_summary": self.training_quality_summary,
            "confidence_metadata": self.confidence_metadata,
            "conformal_calibration": self.conformal_calibration,
            "sample_weight_summary": {
                "min": float(np.min(sample_weight)) if sample_weight is not None else None,
                "max": float(np.max(sample_weight)) if sample_weight is not None else None,
                "mean": float(np.mean(sample_weight)) if sample_weight is not None else None,
            },
            "split_strategy": "70/15/15 holdout with validation-driven model selection",
            "interval_strategy": "quality-weighted point models + quantile interval heads + grouped conformal calibration",
            "training_flow_tree": {
                "name": "Research Training Pipeline",
                "children": [
                    {"name": "Dataset", "value": int(len(X))},
                    {"name": "Stage 1 - Confidence Classifier", "value": self.confidence_best_model_name or "pending"},
                    {"name": "Stage 2 - Price Interval Model", "value": best_name},
                    {"name": "Calibration", "value": "Grouped conformal by trust band"},
                ],
            },
        }

        return results

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions."""
        if not self.is_fitted:
            raise ValueError("Model not trained yet!")

        X_scaled = self.scaler.transform(X)
        return self.best_model.predict(X_scaled)

    def predict_with_confidence(self, X: np.ndarray) -> Dict:
        """
        Make predictions with confidence intervals.
        """
        if not self.is_fitted:
            raise ValueError("Model not trained yet!")

        X_scaled = self.scaler.transform(X)
        predictions = {name: model.predict(X_scaled) for name, model in self.models.items()}
        ensemble_pred = np.mean([pred for pred in predictions.values()], axis=0)

        if self.quantile_models:
            lower = self.quantile_models["lower"].predict(X_scaled)
            upper = self.quantile_models["upper"].predict(X_scaled)
            uncertainty = (upper - lower) / 2.0
        else:
            pred_array = np.column_stack([pred for pred in predictions.values()])
            uncertainty = np.std(pred_array, axis=1)
            margin = 1.96 * uncertainty
            lower = ensemble_pred - margin
            upper = ensemble_pred + margin

        return {
            'predicted_price': ensemble_pred,
            'confidence_low': lower,
            'confidence_high': upper,
            'model_predictions': predictions,
            'uncertainty': uncertainty
        }

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from best model."""
        if not self.is_fitted:
            return {}

        if hasattr(self.best_model, 'feature_importances_'):
            importances = self.best_model.feature_importances_
            return dict(zip(self.feature_names, importances.tolist()))
        return {}

    def explain_prediction(self, X_sample: np.ndarray) -> Dict:
        """
        Explain a single prediction using SHAP if available.
        """
        if not self.is_fitted:
            return {}

        result = {
            'feature_importance': self.get_feature_importance()
        }

        if HAS_SHAP:
            try:
                X_scaled = self.scaler.transform(X_sample.reshape(1, -1))
                explainer = shap.TreeExplainer(self.best_model)
                shap_values = explainer.shap_values(X_scaled)

                result['shap_values'] = shap_values[0].tolist()
                result['shap_available'] = True
            except Exception as e:
                print(f"SHAP error: {e}")
                result['shap_available'] = False

        return result

    def save(self, version: str = None):
        """Save model to disk."""
        if version is None:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")

        model_path = os.path.join(self.model_dir, f'model_{version}.pkl')
        metadata_path = os.path.join(self.model_dir, f'metadata_{version}.json')

        data = {
            'model': self.best_model,
            'models': self.models,
            'quantile_models': self.quantile_models,
            'conformal_calibration': self.conformal_calibration,
            'confidence_best_model': self.confidence_best_model,
            'confidence_best_model_name': self.confidence_best_model_name,
            'confidence_feature_names': self.confidence_feature_names,
            'confidence_metadata': self.confidence_metadata,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'metadata': self.metadata,
            'best_model_name': self.best_model_name,
            'training_quality_summary': self.training_quality_summary,
            'version': version,
            'trained_at': datetime.now().isoformat()
        }

        with open(model_path, 'wb') as f:
            pickle.dump(data, f)

        with open(metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=2)

        print(f"\nModel saved to: {model_path}")
        print(f"Metadata saved to: {metadata_path}")

        return model_path

    def load(self, version: str = None):
        """Load model from disk."""
        if version is None:
            # Find latest model by timestamp in filename (model_YYYYMMDD_HHMMSS.pkl)
            import re
            files = [f for f in os.listdir(self.model_dir) if f.startswith('model_') and f.endswith('.pkl')]
            if not files:
                raise FileNotFoundError("No model found")
            # Sort by timestamp: model_YYYYMMDD_HHMMSS.pkl or model_NAME.pkl
            def version_key(f):
                m = re.match(r'model_(\d{8}_\d{6})', f)
                return m.group(1) if m else '00000000_000000'  # non-timestamped last
            version = max(files, key=version_key).replace('model_', '').replace('.pkl', '')

        model_path = os.path.join(self.model_dir, f'model_{version}.pkl')

        with open(model_path, 'rb') as f:
            data = pickle.load(f)

        self.best_model = data['model']
        self.best_model_name = data.get('best_model_name', 'RandomForest')
        self.models = data.get('models', {self.best_model_name: self.best_model})
        self.quantile_models = data.get('quantile_models', {})
        self.conformal_calibration = data.get('conformal_calibration', {})
        self.confidence_best_model = data.get('confidence_best_model')
        self.confidence_best_model_name = data.get('confidence_best_model_name')
        self.confidence_feature_names = data.get('confidence_feature_names', [])
        self.confidence_metadata = data.get('confidence_metadata', {})
        self.scaler = data['scaler']
        # Feature names: use metadata if longer, else pickle, else extend to match model
        metadata_fn = data.get('metadata', {}).get('feature_names', [])
        pickle_fn = data.get('feature_names', [])
        stored_fn = metadata_fn if len(metadata_fn) >= len(pickle_fn) else pickle_fn
        # If model expects more features than we have names for, extend the list
        n_model = getattr(self.best_model, 'n_features_in_', None)
        if n_model and len(stored_fn) < n_model:
            stored_fn = stored_fn + [f'pad_{i}' for i in range(len(stored_fn), n_model)]
        self.feature_names = stored_fn
        self.metadata = data.get('metadata', {})
        self.training_quality_summary = data.get('training_quality_summary', {})
        self.is_fitted = True

        print(f"Model loaded from: {model_path}")

        return self


def train_model(include_self_collected: bool = True) -> Dict:
    """
    Main training function.
    """
    from src.backend.database import SessionLocal

    # Create pipeline
    pipeline = MLPipeline()

    # Load data
    db = SessionLocal()
    try:
        df, y = pipeline.load_data_from_db(db, include_self_collected)
        print(f"\nLoaded {len(df)} properties")
        print(f"  Self-collected: {(df['data_origin_type'] == 'self_collected').sum()}")
        print(f"  Public: {(df['data_origin_type'] == 'public_collected').sum()}")
    finally:
        db.close()

    # Preprocess (pass y for OOF-based confidence labels)
    X = pipeline.preprocess(df, y=y.values)

    # Train
    results = pipeline.train(X, y.values)

    # Save
    version = datetime.now().strftime("%Y%m%d_%H%M%S")
    pipeline.save(version)

    return results


if __name__ == "__main__":
    train_model()
