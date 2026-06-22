from types import SimpleNamespace

from src.ml.pipeline import MLPipeline


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows
        self.ordered = False

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        self.ordered = True
        self._rows = sorted(self._rows, key=lambda row: row.id)
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows

    def query(self, _model):
        return _FakeQuery(self._rows)


def _property_row(index: int, evidence_tier: str = "E5"):
    return SimpleNamespace(
        id=index,
        property_type="apartment",
        province_city="Hà Nội",
        district="Quận Cầu Giấy",
        ward="Dịch Vọng",
        area_m2=72.0,
        bedrooms=2,
        bathrooms=2,
        floor_count=12,
        frontage_m=5.0,
        legal_status="full_ownership",
        furnishing="furnished",
        price=5_400_000_000 + index,
        price_per_m2=75_000_000,
        latitude=21.03,
        longitude=105.79,
        area_type="urban",
        data_origin_type="self_collected",
        record_status="active",
        verification_status="verified",
        evidence_tier=evidence_tier,
        source_name="field-survey",
        source_url="https://example.test/listing",
        source_page_title="Tin đã xác minh",
        source_collected_at=None,
        source_access_method="manual",
        source_screenshot_path=None,
        verification_note="Đã đối soát",
        verified_by="admin",
        verified_at=None,
        collected_by="field_agent",
        collected_at=None,
        collection_method="field_survey",
        field_note="Có ghi chú thực địa",
        evidence_photo_path="/evidence/photo.jpg",
        created_at=None,
        description="Bản ghi kiểm thử",
        noise_level=45.0,
        temperature=29.0,
        humidity=65.0,
        light_level=350.0,
        gps_lat=21.03,
        gps_lng=105.79,
        area_quality_score=8.5,
        image_url=None,
    )


def test_load_data_from_db_preserves_postgres_evidence_tier():
    rows = [_property_row(i, evidence_tier="E5") for i in range(50)]

    df, y = MLPipeline().load_data_from_db(_FakeSession(rows), include_self_collected=True)

    assert len(df) == 50
    assert len(y) == 50
    assert "evidence_tier" in df.columns
    assert set(df["evidence_tier"]) == {"E5"}


def test_load_data_from_db_orders_records_by_stable_property_id():
    rows = [_property_row(i) for i in reversed(range(50))]

    df, _ = MLPipeline().load_data_from_db(_FakeSession(rows), include_self_collected=True)

    assert df["id"].tolist() == list(range(50))


def test_split_manifest_records_exact_holdout_ids_and_checksums():
    pipeline = MLPipeline()
    pipeline.dataset_record_ids = [101, 102, 103, 104, 105]

    manifest = pipeline._build_split_manifest(
        train_indices=[0, 1],
        validation_indices=[2],
        test_indices=[3, 4],
    )

    assert manifest["train_record_ids"] == [101, 102]
    assert manifest["validation_record_ids"] == [103]
    assert manifest["test_record_ids"] == [104, 105]
    assert len(manifest["dataset_sha256"]) == 64
    assert len(manifest["test_sha256"]) == 64


def test_percentage_diagnostics_separate_typical_error_from_outliers():
    diagnostics = MLPipeline._percentage_error_diagnostics(
        y_true=[1_000_000_000, 2_000_000_000],
        y_pred=[1_500_000_000, 1_500_000_000],
    )

    assert diagnostics["mape_pct"] == 37.5
    assert diagnostics["median_ape_pct"] == 37.5
    assert round(diagnostics["wmape_pct"], 2) == 33.33
    assert diagnostics["price_bands"]["1-3B"]["count"] == 2
