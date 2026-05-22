#!/usr/bin/env python3
"""
Enhanced Prediction with Image Gallery and Source Attribution.
This module provides prediction results with property images and proper data provenance.
"""

from typing import List, Dict, Optional
from datetime import datetime


class PredictionWithImages:
    """
    Enhanced prediction result with images, source attribution, and provenance.
    Based on research paper methodologies for AVM (Automated Valuation Model).
    """

    def __init__(self, prediction_data: dict, property_images: List[dict], source_records: List[dict]):
        self.prediction = prediction_data
        self.images = property_images
        self.sources = source_records
        self.timestamp = datetime.now()

    def get_image_gallery(self) -> List[Dict]:
        """Return images for the predicted property."""
        return self.images

    def get_source_attribution(self) -> str:
        """
        Generate proper source attribution following academic standards.
        Format: (Author, Year) - Source Name
        """
        if not self.sources:
            return "Source: Derived from aggregated market data"

        attributions = []
        for source in self.sources[:3]:  # Top 3 sources
            author = source.get('source_name', 'Unknown')
            date = source.get('listing_date', '')[:4] if source.get('listing_date') else ''
            attributions.append(f"({author}, {date})" if date else f"({author})")

        return "Sources: " + "; ".join(attributions)

    def get_provenance_report(self) -> Dict:
        """
        Generate data provenance report following research standards.
        Tracks the entire data lineage from source to prediction.
        """
        return {
            "prediction_timestamp": self.timestamp.isoformat(),
            "model_version": self.prediction.get('model_version'),
            "model_algorithm": self.prediction.get('algorithm'),
            "training_data": {
                "total_records": self.prediction.get('total_train_records'),
                "verified_records": self.prediction.get('verified_train_records'),
                "self_collected_ratio": self.prediction.get('self_collected_ratio'),
                "date_range": {
                    "start": self.prediction.get('train_start_date'),
                    "end": self.prediction.get('train_end_date')
                }
            },
            "input_data": {
                "property_type": self.prediction.get('input_features', {}).get('property_type'),
                "location": self.prediction.get('input_features', {}).get('district'),
                "area": self.prediction.get('input_features', {}).get('area_m2'),
                "iot_data_available": bool(self.prediction.get('input_features', {}).get('noise_level'))
            },
            "comparable_properties": len(self.sources),
            "sources": [
                {
                    "id": s.get('id'),
                    "source": s.get('source_name'),
                    "similarity": s.get('similarity'),
                    "price": s.get('price')
                }
                for s in self.sources[:5]
            ],
            "feature_importance": self.prediction.get('feature_importance'),
            "confidence_metrics": {
                "confidence_score": self.prediction.get('confidence'),
                "confidence_interval": [
                    self.prediction.get('confidence_low'),
                    self.prediction.get('confidence_high')
                ],
                "price_per_m2": self.prediction.get('price_per_m2')
            }
        }

    def to_research_format(self) -> Dict:
        """
        Convert to research-ready format with proper citations and methodology.
        """
        return {
            "predicted_value": {
                "price": self.prediction.get('predicted_price'),
                "price_per_sqm": self.prediction.get('price_per_m2'),
                "currency": "VND",
                "confidence_interval": {
                    "lower": self.prediction.get('confidence_low'),
                    "upper": self.prediction.get('confidence_high'),
                    "confidence_level": self.prediction.get('confidence')
                }
            },
            "methodology": {
                "model_type": self.prediction.get('algorithm'),
                "model_version": self.prediction.get('model_version'),
                "features_used": self.prediction.get('features_used'),
                "preprocessing": self.prediction.get('preprocessing')
            },
            "data_provenance": self.get_provenance_report(),
            "source_attribution": self.get_source_attribution(),
            "images": self.images,
            "recommendation": self._generate_recommendation()
        }

    def _generate_recommendation(self) -> str:
        """Generate recommendation based on confidence and comparable data."""
        confidence = self.prediction.get('confidence', 0)
        num_comparables = len(self.sources)

        if confidence >= 0.85 and num_comparables >= 5:
            return "High confidence - Strong market evidence with multiple comparable properties"
        elif confidence >= 0.7 and num_comparables >= 3:
            return "Medium confidence - Moderate market evidence, recommend field verification"
        else:
            return "Low confidence - Limited data, field survey recommended"


def generate_comparable_report(comparables: List[dict]) -> str:
    """
    Generate a formatted comparable properties report.
    Following real estate valuation standards.
    """
    if not comparables:
        return "No comparable properties available for analysis."

    report = []
    report.append("=" * 60)
    report.append("COMPARABLE PROPERTIES ANALYSIS REPORT")
    report.append("=" * 60)
    report.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Number of Comparables: {len(comparables)}")
    report.append("")

    # Summary statistics
    prices = [c.get('price', 0) for c in comparables if c.get('price')]
    if prices:
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)

        report.append("PRICE SUMMARY:")
        report.append(f"  Average Price: {avg_price:,.0f} VND")
        report.append(f"  Min Price:    {min_price:,.0f} VND")
        report.append(f"  Max Price:    {max_price:,.0f} VND")
        report.append("")

    report.append("COMPARABLE PROPERTIES:")
    report.append("-" * 60)

    for i, comp in enumerate(comparables[:5], 1):
        report.append(f"\n{i}. Property #{comp.get('id')}")
        report.append(f"   Location: {comp.get('district')}")
        report.append(f"   Area: {comp.get('area_m2')} m²")
        report.append(f"   Price: {comp.get('price', 0):,.0f} VND")
        report.append(f"   Source: {comp.get('source_name')}")
        report.append(f"   Similarity: {(comp.get('similarity', 0) * 100):.1f}%")
        if comp.get('listing_date'):
            report.append(f"   Date: {comp.get('listing_date')[:10]}")

    report.append("")
    report.append("=" * 60)
    report.append("METHODOLOGY NOTE:")
    report.append("Comparables selected based on:")
    report.append("  - Property type match")
    report.append("  - Geographic proximity")
    report.append("  - Similar area (±20%)")
    report.append("  - Verification status (verified only)")
    report.append("=" * 60)

    return "\n".join(report)


def get_prediction_citation(prediction: dict) -> str:
    """
    Generate proper citation for the prediction result.
    Following academic citation format.
    """
    model = prediction.get('model_used', 'Unknown Model')
    version = prediction.get('model_version', 'N/A')
    date = prediction.get('trained_at', datetime.now().strftime('%Y-%m-%d'))

    return f"""
APA Format:
Real Estate AVM System. ({datetime.now().year}). {model} (Version {version}).
Retrieved from automated valuation model, trained on {prediction.get('total_train_records')} properties.
Data period: {prediction.get('train_start_date')} to {prediction.get('train_end_date')}.

BibTeX:
@misc{{avm_prediction_{datetime.now().strftime('%Y%m%d')},
  title={{Real Estate Price Prediction}},
  author={{AVM System}},
  year={{{datetime.now().year}}},
  note={{Model: {model}, Version: {version}, Trained: {date}}}
}}
"""


if __name__ == "__main__":
    # Demo usage
    sample_prediction = {
        "predicted_price": 7200000000,
        "price_per_m2": 60000000,
        "confidence": 0.88,
        "model_version": "v20260313",
        "algorithm": "GradientBoosting",
        "train_start_date": "2024-01-01",
        "train_end_date": "2026-03-13",
        "total_train_records": 2100
    }

    print(get_prediction_citation(sample_prediction))
