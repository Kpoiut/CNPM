"""
Unit tests cho ComparableEngine.

Chạy: python -m pytest tests/unit/valuation/test_comparable_engine.py -v
"""

import pytest
from src.domain.comparable.engine import (
    ComparableEngine,
    ComparableCandidate,
    ComparableQuery,
)


class TestComparableEngine:

    @pytest.fixture
    def engine(self):
        return ComparableEngine()

    @pytest.fixture
    def sample_comparables(self):
        return [
            ComparableCandidate(
                legacy_id=1, asset_type="TOWNHOUSE", province_city="Hà Nội",
                district="Quận Cầu Giấy", ward="Xuân Thủy", area_m2=100.0,
                price=8_000_000_000, price_per_m2=80_000_000,
                evidence_tier="E1", latitude=21.0285, longitude=105.8542,
                floor=10, bedrooms=4, legal_status="FULL_OWNERSHIP",
                listing_date="2026-01-15"
            ),
            ComparableCandidate(
                legacy_id=2, asset_type="TOWNHOUSE", province_city="Hà Nội",
                district="Quận Cầu Giấy", ward="Dịch Vọng", area_m2=120.0,
                price=9_000_000_000, price_per_m2=75_000_000,
                evidence_tier="E2", latitude=21.0300, longitude=105.8550,
                floor=5, bedrooms=4, legal_status="FULL_OWNERSHIP",
                listing_date="2026-02-20"
            ),
            ComparableCandidate(
                legacy_id=3, asset_type="TOWNHOUSE", province_city="Hà Nội",
                district="Quận Thanh Xuân", ward=None, area_m2=80.0,
                price=5_200_000_000, price_per_m2=65_000_000,
                evidence_tier="E3", latitude=None, longitude=None,
                floor=3, bedrooms=3, legal_status="FULL_OWNERSHIP",
                listing_date="2025-06-10"
            ),
            ComparableCandidate(
                legacy_id=4, asset_type="TOWNHOUSE", province_city="TP. Hồ Chí Minh",
                district="Quận 7", ward=None, area_m2=110.0,
                price=8_800_000_000, price_per_m2=80_000_000,
                evidence_tier="E4", latitude=10.7290, longitude=106.6980,
                floor=8, bedrooms=4, legal_status="PENDING",
                listing_date="2024-12-01"
            ),
        ]

    def test_retrieval_returns_candidates(self, engine, sample_comparables):
        """Retrieval layer phải trả về candidates."""
        engine.db_loader = lambda q: sample_comparables
        query = ComparableQuery(
            asset_type="TOWNHOUSE", province_city="Hà Nội",
            district="Quận Cầu Giấy", area_m2=100.0,
            latitude=21.0285, longitude=105.8542,
        )
        results = engine.find_comparables(query)
        assert len(results) == 4

    def test_geo_proximity_scoring(self, engine, sample_comparables):
        """Geo proximity score phải cao hơn cho candidates gần hơn."""
        engine.db_loader = lambda q: sample_comparables
        query = ComparableQuery(
            asset_type="TOWNHOUSE", province_city="Hà Nội",
            district="Quận Cầu Giấy", area_m2=100.0,
            latitude=21.0285, longitude=105.8542,
        )
        results = engine.find_comparables(query)

        # Closest candidate (ID=1) phải có geo_proximity cao nhất
        closest = next(c for c in results if c.legacy_id == 1)
        farthest = next(c for c in results if c.legacy_id == 4)  # HCM
        assert closest.geo_proximity_score > farthest.geo_proximity_score

    def test_evidence_tier_ordering(self, engine, sample_comparables):
        """E1 phải được xếp trước E2, E3, E4."""
        engine.db_loader = lambda q: sample_comparables
        query = ComparableQuery(
            asset_type="TOWNHOUSE", province_city="Hà Nội",
            district="Quận Cầu Giấy", area_m2=100.0,
            latitude=21.0285, longitude=105.8542,
        )
        results = engine.find_comparables(query)

        # Sorted by tier then similarity
        assert results[0].evidence_tier == "E1"
        assert results[-1].evidence_tier in ("E3", "E4")

    def test_similarity_min_threshold(self, engine, sample_comparables):
        """Candidates có similarity < min_similarity phải được lọc ra."""
        engine.db_loader = lambda q: sample_comparables
        query = ComparableQuery(
            asset_type="TOWNHOUSE", province_city="Hà Nội",
            district="Quận Cầu Giấy", area_m2=100.0,
            latitude=21.0285, longitude=105.8542,
            min_similarity=0.70,  # Very high threshold
        )
        results = engine.find_comparables(query)
        for c in results:
            assert c.overall_similarity >= 0.70

    def test_max_count_limit(self, engine, sample_comparables):
        """Số lượng results không vượt quá max_count."""
        engine.db_loader = lambda q: sample_comparables
        query = ComparableQuery(
            asset_type="TOWNHOUSE", province_city="Hà Nội",
            district="Quận Cầu Giấy", area_m2=100.0,
            max_count=2,
        )
        results = engine.find_comparables(query)
        assert len(results) <= 2

    def test_geometry_similarity_favors_closer_area(self, engine, sample_comparables):
        """Candidates có area gần với target phải có geometry_score cao hơn."""
        engine.db_loader = lambda q: sample_comparables
        query = ComparableQuery(
            asset_type="TOWNHOUSE", province_city="Hà Nội",
            district="Quận Cầu Giấy", area_m2=100.0,
        )
        results = engine.find_comparables(query)

        # ID=1 (area=100, gap=0%) vs ID=2 (area=120, gap=20%) → comp_100.geometry_score > comp_120
        # comp_80 (area=80, gap=20%) = comp_120 geometry_score (same gap)
        comp_100 = next(c for c in results if c.legacy_id == 1)
        comp_120 = next(c for c in results if c.legacy_id == 2)
        comp_80 = next(c for c in results if c.legacy_id == 3)

        assert comp_100.geometry_score == 1.0  # Perfect match
        # comp_120 and comp_80 both have 20% gap → same score
        assert comp_120.geometry_score == comp_80.geometry_score
        assert comp_120.geometry_score < comp_100.geometry_score

    def test_explanation_generation(self, engine, sample_comparables):
        """Explanation phải chứa quality assessment."""
        engine.db_loader = lambda q: sample_comparables
        query = ComparableQuery(
            asset_type="TOWNHOUSE", province_city="Hà Nội",
            district="Quận Cầu Giấy", area_m2=100.0,
        )
        results = engine.find_comparables(query)
        explanation = engine.generate_explanation(query, results)

        assert "quality" in explanation
        assert "tier_distribution" in explanation
        assert explanation["tier_distribution"]["E1"] == 1
        assert explanation["tier_distribution"]["E2"] == 1

    def test_evidence_score_mapping(self, engine):
        """E1-E5 phải map đúng sang scores."""
        assert engine._evidence_score("E1") == 1.0
        assert engine._evidence_score("E2") == 0.85
        assert engine._evidence_score("E3") == 0.65
        assert engine._evidence_score("E4") == 0.35
        assert engine._evidence_score("E5") == 0.15
        assert engine._evidence_score("UNKNOWN") == 0.30

    def test_recency_score_favors_recent(self, engine):
        """Bản ghi gần đây phải có recency_score cao hơn."""
        from datetime import datetime, timedelta
        recent = (datetime.now() - timedelta(days=10)).isoformat()
        old = (datetime.now() - timedelta(days=500)).isoformat()

        assert engine._recency_score(recent) > engine._recency_score(old)

    def test_adjustment_normalization_area_gap(self, engine, sample_comparables):
        """Area gap adjustment phải được tính đúng."""
        engine.db_loader = lambda q: sample_comparables
        query = ComparableQuery(
            asset_type="TOWNHOUSE", province_city="Hà Nội",
            district="Quận Cầu Giấy", area_m2=100.0,
            latitude=21.0285, longitude=105.8542,
        )
        results = engine.find_comparables(query)

        # ID=1: area=100, same as target → no adjustment
        comp_100 = next(c for c in results if c.legacy_id == 1)
        assert abs(comp_100.price_adjustment_vnd) < 100_000  # Near zero (0% gap)

        # ID=2: area=120 vs target=100 → 20% gap → positive adjustment (bigger area = higher price)
        comp_120 = next(c for c in results if c.legacy_id == 2)
        assert comp_120.price_adjustment_vnd > 0  # 20% area gap → 6% price adjustment

        # ID=4: area=110 vs target=100 → 10% gap → positive adjustment
        comp_110 = next(c for c in results if c.legacy_id == 4)
        assert comp_110.price_adjustment_vnd > 0  # 10% area gap → 3% price adjustment

    def test_legal_comparability(self, engine):
        """Legal comparability scores phải đúng."""
        assert engine._legal_comparability(None, ComparableCandidate(
            legacy_id=1, asset_type="TOWNHOUSE", province_city="HN",
            district="Cầu Giấy", area_m2=100, price=8_000_000_000,
            price_per_m2=80_000_000, evidence_tier="E1", legal_status="FULL_OWNERSHIP"
        )) == 1.0

        assert engine._legal_comparability(None, ComparableCandidate(
            legacy_id=1, asset_type="TOWNHOUSE", province_city="HN",
            district="Cầu Giấy", area_m2=100, price=8_000_000_000,
            price_per_m2=80_000_000, evidence_tier="E1", legal_status="DISPUTE"
        )) == 0.10

        assert engine._legal_comparability(None, ComparableCandidate(
            legacy_id=1, asset_type="TOWNHOUSE", province_city="HN",
            district="Cầu Giấy", area_m2=100, price=8_000_000_000,
            price_per_m2=80_000_000, evidence_tier="E1", legal_status=None
        )) == 0.40

    def test_haversine_distance(self, engine):
        """Haversine phải tính khoảng cách đúng."""
        # Hanoi to Hanoi (same point) = 0
        dist = engine._haversine(21.0285, 105.8542, 21.0285, 105.8542)
        assert dist == 0.0

        # Roughly Hà Nội to TP.HCM ≈ 1150km
        dist_hn_hcm = engine._haversine(21.0285, 105.8542, 10.8231, 106.6297)
        assert 1100 < dist_hn_hcm < 1200

    def test_empty_candidates_returns_empty(self, engine):
        """Không có candidates → returns empty list."""
        engine.db_loader = lambda q: []
        query = ComparableQuery(
            asset_type="TOWNHOUSE", province_city="Hà Nội",
            district="Quận Cầu Giấy", area_m2=100.0,
        )
        results = engine.find_comparables(query)
        assert results == []
        explanation = engine.generate_explanation(query, results)
        assert explanation["quality"] == "low"

    def test_similarity_vs_adjustment_are_separate(self, engine, sample_comparables):
        """Similarity score và price adjustment phải là 2 lớp riêng biệt."""
        engine.db_loader = lambda q: sample_comparables
        query = ComparableQuery(
            asset_type="TOWNHOUSE", province_city="Hà Nội",
            district="Quận Cầu Giấy", area_m2=100.0,
            latitude=21.0285, longitude=105.8542,
        )
        results = engine.find_comparables(query)
        for c in results:
            # Overall similarity should be independent of adjustment
            # (e.g., E1 can have a big adjustment due to area gap)
            assert 0 <= c.overall_similarity <= 1
