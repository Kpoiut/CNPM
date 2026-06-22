"""Integration tests cho lịch sử dự đoán canonical trên PostgreSQL."""

from uuid import uuid4

from sqlalchemy import text

from src.backend.auth.models import User
from src.backend.models import ValuationRun


VALUATION_PAYLOAD = {
    "asset_type": "LAND_URBAN",
    "province_city": "Hà Nội",
    "district": "Quận Cầu Giấy",
    "ward": "Dịch Vọng",
    "area_m2": 96.0,
    "ownership_type": "FULL_OWNERSHIP",
    "road_class": "ALLEY_3M",
    "flood_risk": "none",
    "frontage_m": 5.2,
    "latitude": 21.0312,
    "longitude": 105.8011,
}


def test_authenticated_valuation_is_saved_to_account_history(authenticated_client, db_session):
    """Mỗi lần account dự đoán phải ghi vào valuation_runs và chỉ user đó đọc được."""
    client, user = authenticated_client

    other = User(
        username=f"it_other_{uuid4().hex[:10]}",
        email=f"it_other_{uuid4().hex[:10]}@example.test",
        hashed_password="test-hash",
        role="user",
        is_active=True,
    )
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    private_run = ValuationRun(
        request_id=f"it-private-{uuid4()}",
        source_endpoint="api_v2_valuation",
        account_id=other.id,
        model_name="ValuationEngine",
        request_status="completed",
        input_features_json={"district": "Quận Cầu Giấy"},
        feedback_verification_status="not_submitted",
        training_eligible=False,
    )
    db_session.add(private_run)
    db_session.commit()

    response = client.post("/api/v2/valuation", json=VALUATION_PAYLOAD)
    assert response.status_code == 200, response.text
    request_id = response.json()["run_id"]

    run = db_session.query(ValuationRun).filter(ValuationRun.request_id == request_id).one()
    assert run.account_id == user.id
    assert run.source_endpoint == "api_v2_valuation"
    assert run.input_features_json["district"] == "Quận Cầu Giấy"
    assert run.result_json["run_id"] == request_id
    assert run.feedback_verification_status == "not_submitted"
    assert run.training_exclusion_reason == "actual_price_feedback_missing"

    history = client.get("/api/v2/valuation/runs?limit=20")
    assert history.status_code == 200, history.text
    visible_ids = {item["request_id"] for item in history.json()["runs"]}
    assert request_id in visible_ids
    assert private_run.request_id not in visible_ids


def test_authenticated_pipeline_serializes_and_persists_runtime_details(authenticated_client, db_session):
    """Pipeline phải trả JSON hợp lệ và không ghi object runtime vào JSONB."""
    client, user = authenticated_client

    response = client.post("/api/v2/pipeline", json=VALUATION_PAYLOAD)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["pipeline_id"]
    for gate in payload["gates"]:
        assert all(not key.startswith("_") for key in gate["details"])

    run = db_session.query(ValuationRun).filter(
        ValuationRun.request_id == payload["pipeline_id"]
    ).one()
    assert run.account_id == user.id
    assert run.source_endpoint == "api_v2_pipeline"
    assert run.result_json["completeness"]["completeness_pct"] >= 0


def test_public_pipeline_does_not_create_anonymous_history(client, db_session):
    """Public prediction không tạo valuation_runs vô danh; lịch sử chỉ thuộc account."""
    response = client.post("/api/v2/pipeline", json=VALUATION_PAYLOAD)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["pipeline_id"]
    assert db_session.query(ValuationRun).filter(
        ValuationRun.request_id == payload["pipeline_id"]
    ).first() is None


def test_history_pagination_rejects_unbounded_limits(authenticated_client):
    """Failure path: limit âm, bằng 0 hoặc quá lớn không được chạm truy vấn DB."""
    client, _user = authenticated_client

    for invalid_limit in (-1, 0, 101):
        response = client.get(f"/api/v2/valuation/runs?limit={invalid_limit}")
        assert response.status_code == 422, response.text

    negative_offset = client.get("/api/v2/valuation/runs?offset=-1")
    assert negative_offset.status_code == 422, negative_offset.text


def test_user_feedback_waits_for_admin_before_training(authenticated_client, db_session):
    """Giá thật do user nhập phải chờ admin duyệt trước khi vào training queue."""
    client, _user = authenticated_client

    response = client.post("/api/v2/valuation", json=VALUATION_PAYLOAD)
    assert response.status_code == 200, response.text
    request_id = response.json()["run_id"]

    feedback = client.post(
        f"/api/v2/valuation/{request_id}/feedback",
        json={
            "actual_price_vnd": 7_800_000_000,
            "actual_price_source": "sale_contract",
            "evidence_ref": "HDMB-IT-001",
        },
    )
    assert feedback.status_code == 200, feedback.text
    assert feedback.json() == {
        "request_id": request_id,
        "feedback_verification_status": "pending_review",
        "training_eligible": False,
    }

    run = db_session.query(ValuationRun).filter(ValuationRun.request_id == request_id).one()
    assert run.actual_price_vnd == 7_800_000_000
    assert run.actual_price_source == "sale_contract"
    assert run.feedback_verification_status == "pending_review"
    assert run.training_eligible is False
    assert run.training_exclusion_reason == "feedback_pending_admin_verification"


def test_admin_verification_exposes_training_feedback_candidate(admin_client, db_session):
    """Admin duyệt feedback hợp lệ thì bản ghi xuất hiện ở management.training_feedback_candidates."""
    client, admin = admin_client
    request_id = f"it-feedback-{uuid4()}"
    run = ValuationRun(
        request_id=request_id,
        source_endpoint="api_v2_valuation",
        account_id=admin.id,
        model_name="ValuationEngine",
        request_status="completed",
        fair_market_value_vnd=7_500_000_000,
        actual_price_vnd=7_650_000_000,
        actual_price_source="notarized_contract",
        actual_price_evidence_ref="HDCC-IT-001",
        feedback_by_account_id=admin.id,
        feedback_verification_status="pending_review",
        input_features_json={
            "asset_type": "LAND_URBAN",
            "district": "Quận Cầu Giấy",
            "area_m2": 96.0,
        },
        training_eligible=False,
    )
    db_session.add(run)
    db_session.commit()

    response = client.post(
        f"/api/v2/valuation/{request_id}/feedback/verify",
        json={"approved": True},
    )
    assert response.status_code == 200, response.text
    assert response.json()["feedback_verification_status"] == "verified"
    assert response.json()["training_eligible"] is True

    candidate_count = db_session.execute(
        text(
            """
            SELECT count(*)
            FROM management.training_feedback_candidates
            WHERE request_id = :request_id
            """
        ),
        {"request_id": request_id},
    ).scalar_one()
    assert candidate_count == 1
