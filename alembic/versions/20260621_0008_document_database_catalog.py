"""Document production PostgreSQL catalog for pgAdmin.

Revision ID: 20260621_0008
Revises: 20260621_0007
Create Date: 2026-06-21
"""

from __future__ import annotations

from alembic import op


revision = "20260621_0008"
down_revision = "20260621_0007"
branch_labels = None
depends_on = None


TABLE_COMMENTS = {
    "public.properties": "Master dataset bất động sản đã chuẩn hóa; nguồn train/evaluation chính của AVM.",
    "public.valuation_runs": "Nguồn duy nhất lưu mọi lần dự đoán, account, input/output, model snapshot, feedback giá thật và trạng thái dùng lại cho training.",
    "public.model_versions": "Registry model production/candidate với MAE, MAPE, R2, trạng thái active và lineage training.",
    "public.training_runs": "Mỗi lần train/retrain ML có dataset snapshot, split manifest và artifact metadata.",
    "public.training_metrics": "Metric long-form theo split/metric để so sánh model công bằng.",
    "public.dataset_versions": "Snapshot dữ liệu train/evaluation với checksum và số lượng record đủ điều kiện.",
    "public.migration_rejected_rows": "Quarantine dữ liệu legacy không thỏa FK/constraint PostgreSQL; giữ để audit thay vì làm bẩn bảng chính.",
    "public.collection_sources": "Danh mục nguồn thu thập được phê duyệt, rate limit và trạng thái vận hành scraper.",
    "public.provenance_chains": "Chuỗi bằng chứng từng bước cho property: thu thập, parse, validate, enrich, verify.",
    "public.audit_logs": "Nhật ký thay đổi nghiệp vụ và bảo mật cho user, dữ liệu, model, feedback.",
    "public.auth_accounts": "Tài khoản đăng nhập và phân quyền user/admin.",
    "public.auth_account_sessions": "Access session đã hash token để revoke/logout có hiệu lực thật.",
    "public.auth_refresh_tokens": "Refresh token opaque đã hash, dùng để xoay vòng phiên an toàn.",
    "public.expert_properties": "Bất động sản được chọn cho expert evaluation/ground-truth review.",
    "public.expert_ratings": "Điểm đánh giá expert cho property, dùng kiểm định chất lượng model.",
    "public.buyer_requirements": "Nhu cầu người mua dùng cho supply-demand/equilibrium matching.",
    "public.matched_pairs": "Cặp listing-buyer matched để đo overlap cầu-cung.",
    "public.claims": "Community claim về dữ liệu/giá trị bất động sản cần kiểm chứng.",
    "public.claim_evidence": "Bằng chứng đi kèm community claim.",
    "public.community_comments": "Bình luận community có ràng buộc claim/user.",
    "public.challenges": "Yêu cầu phản biện claim và luồng tranh chấp dữ liệu.",
    "public.claim_court_sessions": "Phiên xét duyệt community claim.",
    "public.prediction_bonds": "Cam kết/đặt cọc dự đoán trong cơ chế community quality.",
    "public.coalition_flags": "Cờ phát hiện nhóm thao túng hoặc bất thường cộng đồng.",
    "public.ai_training_candidates": "Ứng viên dữ liệu từ community/feedback để xét đưa vào training sau kiểm duyệt.",
    "public.appeal_cases": "Hồ sơ khiếu nại quyết định kiểm duyệt dữ liệu/community.",
    "public.private_insights": "Insight riêng tư hoặc nhạy cảm, không dùng làm bảng public listing.",
    "public.reputation_ledger": "Sổ điểm uy tín user/community theo hành vi xác minh dữ liệu.",
}

VIEW_COMMENTS = {
    "management.model_registry": "View quản trị model version, active/candidate và metric chính.",
    "management.prediction_history": "View lịch sử dự đoán đọc được trong pgAdmin, hợp nhất account, input/output, feedback và model snapshot từ valuation_runs.",
    "management.property_dataset_full": "View đọc dataset property đầy đủ cho audit/quản trị.",
    "management.training_feedback_candidates": "Queue dữ liệu feedback đã verified, đủ input và đủ ngưỡng giá để retrain.",
    "management.training_history": "View lịch sử training run + dataset + metric.",
}


def _quote_comment(value: str) -> str:
    return value.replace("'", "''")


def upgrade() -> None:
    for qualified_name, comment in TABLE_COMMENTS.items():
        op.execute(f"COMMENT ON TABLE {qualified_name} IS '{_quote_comment(comment)}'")
    for qualified_name, comment in VIEW_COMMENTS.items():
        op.execute(f"COMMENT ON VIEW {qualified_name} IS '{_quote_comment(comment)}'")

    op.execute(
        """
        CREATE OR REPLACE VIEW management.database_catalog AS
        SELECT
            n.nspname AS schema_name,
            c.relname AS object_name,
            CASE c.relkind
                WHEN 'r' THEN 'table'
                WHEN 'v' THEN 'view'
                WHEN 'm' THEN 'materialized_view'
                ELSE c.relkind::text
            END AS object_type,
            c.reltuples::bigint AS estimated_rows,
            CASE WHEN c.relkind = 'r' THEN pg_total_relation_size(c.oid) ELSE NULL END AS total_bytes,
            obj_description(c.oid, 'pg_class') AS purpose
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname IN ('public', 'management')
          AND c.relkind IN ('r', 'v', 'm')
          AND c.relname NOT LIKE 'pg_%'
        ORDER BY
            CASE n.nspname WHEN 'public' THEN 1 WHEN 'management' THEN 2 ELSE 3 END,
            c.relname
        """
    )
    op.execute("COMMENT ON VIEW management.database_catalog IS 'Mục lục schema production cho pgAdmin: bảng/view đang phản ánh dữ liệu gì, loại object, row estimate và kích thước.'")
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'real_estate_avm_app') THEN
                GRANT SELECT ON management.database_catalog TO real_estate_avm_app;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS management.database_catalog")
