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


def test_nova_budget_detail_followup_uses_latest_budget_context():
    context = {
        **PROJECT_CONTEXT,
        "recent_messages": [
            {"role": "user", "text": "tôi cần nhà giá 2 tỷ tốt nhất"},
            {"role": "assistant", "text": "Gợi ý với khoảng 2 tỷ ở Quận 7..."},
            {"role": "user", "text": "còn 8 tỷ thì sao"},
        ],
    }

    response = project_fast_response("cho tôi toàn bộ thông tin chi tiết", context, [])

    assert response is not None
    assert "8.00 tỷ" in response
    assert "nhà phố tốt" in response
    assert "đừng kỳ vọng nhà phố rộng" not in response
    assert "Gợi ý chi tiết" in response
    assert "Xin chào" not in response
