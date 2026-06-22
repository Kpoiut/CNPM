from src.backend.api_v2.nova import fallback_response, project_fast_response


PROJECT_CONTEXT = {
    "project_snapshot": {
        "property_count": 3560,
        "scope": ["Cầu Giấy", "Thanh Xuân", "Đống Đa", "Quận 7", "Bình Thạnh", "Tân Bình"],
        "latest_model": "20260504_144753",
    },
    "auth_user": {"role": "guest"},
}


def test_nova_project_overview_handles_greeting_plus_project_question():
    response = project_fast_response(
        "chào Nova, dự án này đang làm gì?",
        PROJECT_CONTEXT.copy(),
        [],
    )

    assert response is not None
    assert "AVM production" in response
    assert "PostgreSQL/PostGIS" in response
    assert "valuation_runs" in response
    assert "20260504_144753" in response


def test_nova_fallback_explains_project_nature_without_llm_provider():
    response = fallback_response("dự án này bản chất là gì?", PROJECT_CONTEXT.copy())

    assert "hệ thống AVM production" in response
    assert "model registry" in response
    assert "lịch sử dự đoán" in response or "valuation_runs" in response


def test_nova_general_fallback_is_natural_not_canned():
    response = fallback_response("nói chuyện chút đi", PROJECT_CONTEXT.copy())

    assert "Tôi nghe bạn" not in response
    assert "mục tiêu" in response
