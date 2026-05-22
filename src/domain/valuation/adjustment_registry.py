"""
Adjustment Registry — Bảng đăng ký tất cả adjustment factors.

Mỗi factor được định nghĩa với:
- factor_code: unique identifier
- layer: MARKET | FIT
- asset_types: loại tài sản áp dụng
- delta_reference: % adjustment tham chiếu
- confidence_base: confidence mặc định
- rationale_template: template cho explanation
- evidence_requirement: nguồn bằng chứng tối thiểu

Tất cả delta được tính theo VND/m² hoặc % tổng giá.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


class AdjustmentLayer(str, Enum):
    MARKET = "MARKET"
    FIT = "FIT"


class FactorGroup(str, Enum):
    L1_LEGAL = "L1_LEGAL"
    L2_GEOMETRY = "L2_GEOMETRY"
    L3_ACCESS = "L3_ACCESS"
    L4_ENVIRONMENT = "L4_ENVIRONMENT"
    L5_BUILDING = "L5_BUILDING"
    L6_VIEW_ORIENTATION = "L6_VIEW_ORIENTATION"
    F1_FENG_SHUI = "F1_FENG_SHUI"
    F2_SPIRITUAL = "F2_SPIRITUAL"
    F3_FAMILY = "F3_FAMILY"
    F4_INVESTMENT = "F4_INVESTMENT"


@dataclass
class Adjustment:
    """Một adjustment factor."""
    factor_code: str
    layer: AdjustmentLayer
    group: FactorGroup
    asset_types: Set[str]  # Loại tài sản áp dụng. Empty = tất cả.
    delta_pct_base: float  # Base delta (%). Positive = thêm vào giá.
    confidence_base: float   # Confidence mặc định (0-1)
    rationale_template: str  # Template cho human-readable explanation
    evidence_requirement: str  # Nguồn bằng chứng tối thiểu
    applicable_conditions: Dict[str, any] = field(default_factory=dict)
    # delta_reference: nếu per_m2 thì tính theo VND/m², nếu null thì % tổng giá
    delta_type: str = "pct_total"  # "pct_total" | "vnd_per_m2"


# =============================================================================
# FACTOR REGISTRY — Tất cả 40+ factors cho alpha
# =============================================================================

FACTOR_REGISTRY: Dict[str, Adjustment] = {

    # ─────────────────────────────────────────────────────────────────────────
    # L1: LEGAL & PLANNING (MARKET)
    # ─────────────────────────────────────────────────────────────────────────
    "LEGAL_FULL": Adjustment(
        factor_code="LEGAL_FULL",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L1_LEGAL,
        asset_types={"APARTMENT", "TOWNHOUSE", "VILLA", "LAND"},
        delta_pct_base=0.04,
        confidence_base=0.90,
        rationale_template="Pháp lý đầy đủ: {certificate_type}, không tranh chấp.",
        evidence_requirement="Sổ đỏ photo hoặc xác minh thực địa",
        delta_type="pct_total",
    ),
    "LEGAL_LURC": Adjustment(
        factor_code="LEGAL_LURC",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L1_LEGAL,
        asset_types={"LAND", "LAND"},
        delta_pct_base=0.00,
        confidence_base=0.85,
        rationale_template="Giấy phép sử dụng đất: {certificate_type}.",
        evidence_requirement="LURC document",
        delta_type="pct_total",
    ),
    "LEGAL_PENDING": Adjustment(
        factor_code="LEGAL_PENDING",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L1_LEGAL,
        asset_types={"APARTMENT", "TOWNHOUSE", "VILLA", "LAND"},
        delta_pct_base=-0.08,
        confidence_base=0.75,
        rationale_template="Pháp lý đang chờ cấp, không thể giao dịch ngay.",
        evidence_requirement="Xác minh thực địa",
        delta_type="pct_total",
    ),
    "LEGAL_DISPUTE": Adjustment(
        factor_code="LEGAL_DISPUTE",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L1_LEGAL,
        asset_types={"APARTMENT", "TOWNHOUSE", "VILLA", "LAND"},
        delta_pct_base=-0.15,
        confidence_base=0.85,
        rationale_template="Đang có tranh chấp pháp lý: {dispute_type}.",
        evidence_requirement="Xác minh tòa án hoặc chính quyền",
        delta_type="pct_total",
    ),
    "LEGAL_MORTGAGE": Adjustment(
        factor_code="LEGAL_MORTGAGE",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L1_LEGAL,
        asset_types={"APARTMENT", "TOWNHOUSE", "VILLA", "LAND"},
        delta_pct_base=-0.05,
        confidence_base=0.80,
        rationale_template="Tài sản đang thế chấp ngân hàng {bank}.",
        evidence_requirement="Xác minh ngân hàng",
        delta_type="pct_total",
    ),
    "PLANNING_ROAD_EXPAND": Adjustment(
        factor_code="PLANNING_ROAD_EXPAND",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L1_LEGAL,
        asset_types={"TOWNHOUSE", "LAND", "LAND"},
        delta_pct_base=-0.12,
        confidence_base=0.75,
        rationale_template="Quy hoạch mở đường rộng {width}m, ảnh hưởng diện tích.",
        evidence_requirement="Quy hoạch 1/500 hoặc quy hoạch đô thị",
        delta_type="pct_total",
    ),
    "PLANNING_SETBACK": Adjustment(
        factor_code="PLANNING_SETBACK",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L1_LEGAL,
        asset_types={"TOWNHOUSE", "LAND"},
        delta_pct_base=-0.06,
        confidence_base=0.75,
        rationale_template="Lộ giới trước nhà {width}m theo quy hoạch, giảm diện tích xây dựng.",
        evidence_requirement="Quy hoạch đô thị",
        delta_type="pct_total",
    ),
    "PLANNING_GREEN": Adjustment(
        factor_code="PLANNING_GREEN",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L1_LEGAL,
        asset_types={"APARTMENT", "TOWNHOUSE", "LAND"},
        delta_pct_base=0.03,
        confidence_base=0.65,
        rationale_template="Quy hoạch khu cây xanh/rong quanh, cải thiện môi trường.",
        evidence_requirement="Quy hoạch đô thị",
        delta_type="pct_total",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # L2: GEOMETRY & SHAPE (MARKET — chỉ LAND)
    # ─────────────────────────────────────────────────────────────────────────
    "GEOM_NÖHẬU": Adjustment(
        factor_code="GEOM_NÖHẬU",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L2_GEOMETRY,
        asset_types={"LAND"},
        delta_pct_base=0.04,
        confidence_base=0.70,
        rationale_template="Đất vuông vắn, tỷ lệ frontage/depth {ratio:.1f}:1 trong ngưỡng tối ưu 1:2~1:3.",
        evidence_requirement="Sơ đồ hiện trạng hoặc đo đạc",
        delta_type="pct_total",
    ),
    "GEOM_THOP_HAU": Adjustment(
        factor_code="GEOM_THOP_HAU",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L2_GEOMETRY,
        asset_types={"LAND"},
        delta_pct_base=-0.06,
        confidence_base=0.65,
        rationale_template="Đất thóp hậu nhẹ: chiều rộng tối thiểu {min_width}m so với trung bình {avg_width}m.",
        evidence_requirement="Sơ đồ hiện trạng",
        delta_type="pct_total",
    ),
    "GEOM_THOP_HAU_SEVERE": Adjustment(
        factor_code="GEOM_THOP_HAU_SEVERE",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L2_GEOMETRY,
        asset_types={"LAND"},
        delta_pct_base=-0.12,
        confidence_base=0.65,
        rationale_template="Đất thóp hậu nặng: bị thắt cả hai đầu, khó xây dựng tối ưu.",
        evidence_requirement="Sơ đồ hiện trạng",
        delta_type="pct_total",
    ),
    "GEOM_TAPER_MINOR": Adjustment(
        factor_code="GEOM_TAPER_MINOR",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L2_GEOMETRY,
        asset_types={"LAND"},
        delta_pct_base=-0.03,
        confidence_base=0.55,
        rationale_template="Đất hình côn nhẹ: {taper_pct}% so với hình vuông.",
        evidence_requirement="Sơ đồ hiện trạng",
        delta_type="pct_total",
    ),
    "GEOM_CORNER_PLOT": Adjustment(
        factor_code="GEOM_CORNER_PLOT",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L2_GEOMETRY,
        asset_types={"LAND"},
        delta_pct_base=0.06,
        confidence_base=0.70,
        rationale_template="Đất góc với {count} mặt tiền, thuận tiện kinh doanh và đi lại.",
        evidence_requirement="Sơ đồ hiện trạng",
        delta_type="pct_total",
    ),
    "DEPTH_60_PLUS": Adjustment(
        factor_code="DEPTH_60_PLUS",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L2_GEOMETRY,
        asset_types={"LAND"},
        delta_pct_base=-0.04,
        confidence_base=0.55,
        rationale_template="Đất quá sâu ({depth}m), khó khai thác hiệu quả.",
        evidence_requirement="Sơ đồ hiện trạng",
        delta_type="pct_total",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # L3: ACCESS & LOCATION (MARKET)
    # ─────────────────────────────────────────────────────────────────────────
    "ACCESS_MAIN_STREET": Adjustment(
        factor_code="ACCESS_MAIN_STREET",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L3_ACCESS,
        asset_types={"TOWNHOUSE", "LAND", "HOUSE", "VILLA"},
        delta_pct_base=0.10,
        confidence_base=0.90,
        rationale_template="Mặt đường chính rộng {width}m, ô tô ra vào dễ dàng.",
        evidence_requirement="Khảo sát thực địa",
        delta_type="pct_total",
    ),
    "ACCESS_ALLEY_5M": Adjustment(
        factor_code="ACCESS_ALLEY_5M",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L3_ACCESS,
        asset_types={"TOWNHOUSE", "LAND", "HOUSE"},
        delta_pct_base=0.03,
        confidence_base=0.85,
        rationale_template="Hẻm rộng 5m, ô tô vào được.",
        evidence_requirement="Khảo sát thực địa",
        delta_type="pct_total",
    ),
    "ACCESS_ALLEY_3M": Adjustment(
        factor_code="ACCESS_ALLEY_3M",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L3_ACCESS,
        asset_types={"TOWNHOUSE", "LAND", "HOUSE"},
        delta_pct_base=0.00,
        confidence_base=0.80,
        rationale_template="Hẻm 3m, xe máy vào thoải mái, ô tô hạn chế.",
        evidence_requirement="Khảo sát thực địa",
        delta_type="pct_total",
    ),
    "ACCESS_ALLEY_2M": Adjustment(
        factor_code="ACCESS_ALLEY_2M",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L3_ACCESS,
        asset_types={"TOWNHOUSE", "LAND", "HOUSE"},
        delta_pct_base=-0.08,
        confidence_base=0.80,
        rationale_template="Hẻm hẹp 2m, xe máy khó luồn lách, ô tô không vào được.",
        evidence_requirement="Khảo sát thực địa",
        delta_type="pct_total",
    ),
    "ACCESS_ALLEY_1M": Adjustment(
        factor_code="ACCESS_ALLEY_1M",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L3_ACCESS,
        asset_types={"TOWNHOUSE", "LAND", "HOUSE"},
        delta_pct_base=-0.14,
        confidence_base=0.75,
        rationale_template="Hẻm rất hẹp dưới 1m, chỉ đi bộ, khó vận chuyển.",
        evidence_requirement="Khảo sát thực địa",
        delta_type="pct_total",
    ),
    "ACCESS_DEAD_END": Adjustment(
        factor_code="ACCESS_DEAD_END",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L3_ACCESS,
        asset_types={"TOWNHOUSE", "LAND", "HOUSE"},
        delta_pct_base=-0.04,
        confidence_base=0.70,
        rationale_template="Hẻm cụt, không lối thoát, bất tiện khi cần ra vào nhiều.",
        evidence_requirement="Bản đồ hoặc khảo sát",
        delta_type="pct_total",
    ),
    "ACCESS_ALLEY_BRANCH": Adjustment(
        factor_code="ACCESS_ALLEY_BRANCH",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L3_ACCESS,
        asset_types={"TOWNHOUSE", "LAND"},
        delta_pct_base=-0.03,
        confidence_base=0.60,
        rationale_template="Hẻm có nhánh phụ {count} điểm, phức tạp đi lại.",
        evidence_requirement="Bản đồ hoặc khảo sát",
        delta_type="pct_total",
    ),
    "DIST_METRO_500M": Adjustment(
        factor_code="DIST_METRO_500M",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L3_ACCESS,
        asset_types={"APARTMENT"},
        delta_pct_base=0.08,
        confidence_base=0.85,
        rationale_template="Cách ga metro gần nhất {distance}m, kết nối giao thông tốt.",
        evidence_requirement="Bản đồ metro hoặc Google Maps",
        delta_type="pct_total",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # L4: ENVIRONMENT & HAZARD (MARKET)
    # ─────────────────────────────────────────────────────────────────────────
    "ENV_FLOOD_NONE": Adjustment(
        factor_code="ENV_FLOOD_NONE",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L4_ENVIRONMENT,
        asset_types=set(),  # tất cả
        delta_pct_base=0.03,
        confidence_base=0.80,
        rationale_template="Không có lịch sử ngập lụt, cao độ an toàn.",
        evidence_requirement="Khảo sát thực địa hoặc bản đồ ngập",
        delta_type="pct_total",
    ),
    "ENV_FLOOD_MINOR": Adjustment(
        factor_code="ENV_FLOOD_MINOR",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L4_ENVIRONMENT,
        asset_types=set(),
        delta_pct_base=-0.06,
        confidence_base=0.75,
        rationale_template="Ngập nhẹ theo mùa mỗi năm {freq}, cần lưu ý.",
        evidence_requirement="Lịch sử ngập hoặc bản đồ ngập",
        delta_type="pct_total",
    ),
    "ENV_FLOOD_SEVERE": Adjustment(
        factor_code="ENV_FLOOD_SEVERE",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L4_ENVIRONMENT,
        asset_types=set(),
        delta_pct_base=-0.16,
        confidence_base=0.85,
        rationale_template="Khu vực ngập nặng/thường xuyên theo {source}, rủi ro cao.",
        evidence_requirement="Bản đồ ngập chính thức hoặc ghi nhận thực địa",
        delta_type="pct_total",
    ),
    "ENV_CEMETERY_200M": Adjustment(
        factor_code="ENV_CEMETERY_200M",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L4_ENVIRONMENT,
        asset_types={"APARTMENT", "TOWNHOUSE", "VILLA"},
        delta_pct_base=-0.04,
        confidence_base=0.70,
        rationale_template="Cách nghĩa trang {distance}m, có ảnh hưởng tâm linh và thực.",
        evidence_requirement="Bản đồ",
        delta_type="pct_total",
    ),
    "ENV_LANDFILL_500M": Adjustment(
        factor_code="ENV_LANDFILL_500M",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L4_ENVIRONMENT,
        asset_types={"APARTMENT", "TOWNHOUSE", "LAND"},
        delta_pct_base=-0.03,
        confidence_base=0.70,
        rationale_template="Cách bãi rác/khu xử lý chất thải {distance}m, mùi và vệ sinh ảnh hưởng.",
        evidence_requirement="Bản đồ hoặc khảo sát",
        delta_type="pct_total",
    ),
    "NOISE_DAY_65DB": Adjustment(
        factor_code="NOISE_DAY_65DB",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L4_ENVIRONMENT,
        asset_types={"APARTMENT", "TOWNHOUSE"},
        delta_pct_base=-0.05,
        confidence_base=0.75,
        rationale_template="Tiếng ồn ngày trung bình {db}dB vượt ngưỡng thoải mái (65dB), ảnh hưởng sinh hoạt.",
        evidence_requirement="IoT sensor hoặc đo đạc thực địa",
        delta_type="pct_total",
    ),
    "NOISE_NIGHT_55DB": Adjustment(
        factor_code="NOISE_NIGHT_55DB",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L4_ENVIRONMENT,
        asset_types={"APARTMENT", "TOWNHOUSE"},
        delta_pct_base=-0.07,
        confidence_base=0.75,
        rationale_template="Tiếng ồn đêm {db}dB vượt ngưỡng ngủ (55dB), ảnh hưởng sức khỏe.",
        evidence_requirement="IoT sensor hoặc đo đạc thực địa",
        delta_type="pct_total",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # L5: BUILDING QUALITY (MARKET — nhà và căn hộ)
    # ─────────────────────────────────────────────────────────────────────────
    "BLDG_NEW_5Y": Adjustment(
        factor_code="BLDG_NEW_5Y",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L5_BUILDING,
        asset_types={"TOWNHOUSE", "VILLA", "HOUSE"},
        delta_pct_base=0.06,
        confidence_base=0.80,
        rationale_template="Nhà xây dựng {year} ({age} năm), còn mới, ít chi phí bảo trì.",
        evidence_requirement="Biên nhận, hóa đơn thuế, hoặc ước lượng",
        delta_type="pct_total",
    ),
    "BLDG_OLD_20Y": Adjustment(
        factor_code="BLDG_OLD_20Y",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L5_BUILDING,
        asset_types={"TOWNHOUSE", "VILLA", "HOUSE"},
        delta_pct_base=-0.08,
        confidence_base=0.70,
        rationale_template="Nhà xây dựng {year} ({age} năm), cần tu sửa đáng kể.",
        evidence_requirement="Kiểm tra thực địa hoặc ước lượng",
        delta_type="pct_total",
    ),
    "BLDG_FLOORS_EXCEED": Adjustment(
        factor_code="BLDG_FLOORS_EXCEED",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L5_BUILDING,
        asset_types={"TOWNHOUSE", "VILLA", "HOUSE"},
        delta_pct_base=-0.10,
        confidence_base=0.85,
        rationale_template="Số tầng {count} vượt quy hoạch cho phép ({allowed}), rủi ro pháp lý.",
        evidence_requirement="Quy hoạch đô thị hoặc kiểm tra thực địa",
        delta_type="pct_total",
    ),
    "BLDG_ATTIC": Adjustment(
        factor_code="BLDG_ATTIC",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L5_BUILDING,
        asset_types={"TOWNHOUSE", "VILLA", "HOUSE"},
        delta_pct_base=0.03,
        confidence_base=0.65,
        rationale_template="Có áp mái sử dụng được, tăng diện tích sinh hoạt.",
        evidence_requirement="Kiểm tra thực địa",
        delta_type="pct_total",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # L6: VIEW & ORIENTATION (MARKET — chỉ căn hộ)
    # ─────────────────────────────────────────────────────────────────────────
    "APT_VIEW_RIVER": Adjustment(
        factor_code="APT_VIEW_RIVER",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L6_VIEW_ORIENTATION,
        asset_types={"APARTMENT"},
        delta_pct_base=0.10,
        confidence_base=0.80,
        rationale_template="View sông rộng thoáng, premium đáng kể cho tầm nhìn.",
        evidence_requirement="Ảnh chụp thực địa hoặc 3D model",
        delta_type="pct_total",
    ),
    "APT_VIEW_CITY": Adjustment(
        factor_code="APT_VIEW_CITY",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L6_VIEW_ORIENTATION,
        asset_types={"APARTMENT"},
        delta_pct_base=0.04,
        confidence_base=0.65,
        rationale_template="View thành phố nhìn toàn cảnh đô thị.",
        evidence_requirement="Ảnh chụp thực địa",
        delta_type="pct_total",
    ),
    "APT_NO_VIEW": Adjustment(
        factor_code="APT_NO_VIEW",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L6_VIEW_ORIENTATION,
        asset_types={"APARTMENT"},
        delta_pct_base=-0.08,
        confidence_base=0.75,
        rationale_template="Không có view (hướng tường kề tường, bị che hoàn toàn), ảnh hưởng đáng kể.",
        evidence_requirement="Ảnh chụp hoặc địa chỉ cụ thể",
        delta_type="pct_total",
    ),
    "APT_FLOOR_HIGH_15P": Adjustment(
        factor_code="APT_FLOOR_HIGH_15P",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L6_VIEW_ORIENTATION,
        asset_types={"APARTMENT"},
        delta_pct_base=0.06,
        confidence_base=0.80,
        rationale_template="Tầng cao {floor}, view tốt hơn, ít ồn, giá premium.",
        evidence_requirement="Số tầng từ chủng từ/căn hộ",
        delta_type="pct_total",
    ),
    "APT_FLOOR_LOW_3M": Adjustment(
        factor_code="APT_FLOOR_LOW_3M",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L6_VIEW_ORIENTATION,
        asset_types={"APARTMENT"},
        delta_pct_base=-0.05,
        confidence_base=0.75,
        rationale_template="Tầng thấp dưới tầng 3, nhiều bụi, ồn, bảo mật kém hơn.",
        evidence_requirement="Số tầng từ chủng từ",
        delta_type="pct_total",
    ),
    "APT_TRASH_NEAR": Adjustment(
        factor_code="APT_TRASH_NEAR",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L6_VIEW_ORIENTATION,
        asset_types={"APARTMENT"},
        delta_pct_base=-0.03,
        confidence_base=0.70,
        rationale_template="Căn hộ nằm gần phòng rác, có mùi và tiếng ồn từ hoạt động rác.",
        evidence_requirement="Sơ đồ tầng hoặc kiểm tra thực địa",
        delta_type="pct_total",
    ),
    "APT_CORE_ADJACENT": Adjustment(
        factor_code="APT_CORE_ADJACENT",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L6_VIEW_ORIENTATION,
        asset_types={"APARTMENT"},
        delta_pct_base=-0.04,
        confidence_base=0.70,
        rationale_template="Căn hộ liền kề lõi kỹ thuật (thang máy/M&E), có tiếng ồn và rung động.",
        evidence_requirement="Sơ đồ tầng",
        delta_type="pct_total",
    ),
    "APT_SUNLIGHT_WEST_STRONG": Adjustment(
        factor_code="APT_SUNLIGHT_WEST_STRONG",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L6_VIEW_ORIENTATION,
        asset_types={"APARTMENT"},
        delta_pct_base=-0.04,
        confidence_base=0.70,
        rationale_template="Hướng Tây hứng nắng chiều gay gắt, nhiệt độ trong nhà cao, tốn điện.",
        evidence_requirement="Hướng nhà + mùa/hè",
        delta_type="pct_total",
    ),
    "APT_VENTILATION_POOR": Adjustment(
        factor_code="APT_VENTILATION_POOR",
        layer=AdjustmentLayer.MARKET,
        group=FactorGroup.L6_VIEW_ORIENTATION,
        asset_types={"APARTMENT"},
        delta_pct_base=-0.04,
        confidence_base=0.70,
        rationale_template="Bố trí cửa-không thoáng, thông gió kém, ẩm mốc.",
        evidence_requirement="Sơ đồ căn hộ + kiểm tra thực địa",
        delta_type="pct_total",
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    # L7 FIT LAYER — Phong thủy (F1), Tâm linh (F2), Gia đình (F3), Đầu tư (F4)
    # ═══════════════════════════════════════════════════════════════════════════════
    # F1: Feng Shui adjustments — orientation, shape harmony
    "FIT_ORIENTATION_NORTH": Adjustment(
        factor_code="FIT_ORIENTATION_NORTH",
        layer=AdjustmentLayer.FIT,
        group=FactorGroup.F1_FENG_SHUI,
        asset_types={"TOWNHOUSE", "VILLA", "HOUSE"},
        delta_pct_base=0.03,
        confidence_base=0.70,
        rationale_template="Hướng Bắc — theo phong thủy Việt Nam, hướng sinh khí.",
        evidence_requirement="La bàn đo hướng",
        delta_type="pct_total",
    ),
    "FIT_ORIENTATION_SOUTH": Adjustment(
        factor_code="FIT_ORIENTATION_SOUTH",
        layer=AdjustmentLayer.FIT,
        group=FactorGroup.F1_FENG_SHUI,
        asset_types={"TOWNHOUSE", "VILLA", "HOUSE"},
        delta_pct_base=0.02,
        confidence_base=0.70,
        rationale_template="Hướng Nam — hướng nhiệt, tượng trưng danh vọng.",
        evidence_requirement="La bàn đo hướng",
        delta_type="pct_total",
    ),
    "FIT_ORIENTATION_EAST": Adjustment(
        factor_code="FIT_ORIENTATION_EAST",
        layer=AdjustmentLayer.FIT,
        group=FactorGroup.F1_FENG_SHUI,
        asset_types={"TOWNHOUSE", "VILLA", "HOUSE", "LAND"},
        delta_pct_base=0.04,
        confidence_base=0.72,
        rationale_template="Hướng Đông — hướng mặt trời mọc, sinh khí dồi dào.",
        evidence_requirement="La bàn đo hướng",
        delta_type="pct_total",
    ),
    "FIT_ORIENTATION_BAD": Adjustment(
        factor_code="FIT_ORIENTATION_BAD",
        layer=AdjustmentLayer.FIT,
        group=FactorGroup.F1_FENG_SHUI,
        asset_types={"TOWNHOUSE", "VILLA", "HOUSE"},
        delta_pct_base=-0.02,
        confidence_base=0.65,
        rationale_template="Hướng Tây Nam hoặc Đông Bắc — hướng hung khí trong phong thủy.",
        evidence_requirement="La bàn đo hướng",
        delta_type="pct_total",
    ),
    "FIT_LAND_SHAPE_HARMONY": Adjustment(
        factor_code="FIT_LAND_SHAPE_HARMONY",
        layer=AdjustmentLayer.FIT,
        group=FactorGroup.F1_FENG_SHUI,
        asset_types={"LAND"},
        delta_pct_base=0.02,
        confidence_base=0.65,
        rationale_template="Đất vuông hoặc hình tròn — tượng trưng tài lộc.",
        evidence_requirement="Sơ đồ hiện trạng",
        delta_type="pct_total",
    ),

    # F2: Spiritual adjustments — house number, floor number, birth date
    "FIT_FLOOR_NUMBER_LUCKY": Adjustment(
        factor_code="FIT_FLOOR_NUMBER_LUCKY",
        layer=AdjustmentLayer.FIT,
        group=FactorGroup.F2_SPIRITUAL,
        asset_types={"APARTMENT"},
        delta_pct_base=0.015,
        confidence_base=0.60,
        rationale_template="Tầng số may mắn theo phong thủy: tầng 8, 9, 6.",
        evidence_requirement="Số tầng từ quản lý tòa nhà",
        delta_type="pct_total",
    ),
    "FIT_HOUSE_NUMBER_AUSPICIOUS": Adjustment(
        factor_code="FIT_HOUSE_NUMBER_AUSPICIOUS",
        layer=AdjustmentLayer.FIT,
        group=FactorGroup.F2_SPIRITUAL,
        asset_types={"TOWNHOUSE", "HOUSE"},
        delta_pct_base=0.02,
        confidence_base=0.60,
        rationale_template="Số nhà có chữ số mang ý nghĩa may mắn (8, 9, 6).",
        evidence_requirement="Địa chỉ thực tế",
        delta_type="pct_total",
    ),

    # F3: Family adjustments — bedroom/bathroom balance
    "FIT_BEDROOM_BALANCE": Adjustment(
        factor_code="FIT_BEDROOM_BALANCE",
        layer=AdjustmentLayer.FIT,
        group=FactorGroup.F3_FAMILY,
        asset_types={"TOWNHOUSE", "VILLA", "HOUSE"},
        delta_pct_base=0.02,
        confidence_base=0.65,
        rationale_template="Số phòng ngủ cân đối với số thành viên gia đình.",
        evidence_requirement="Thông tin gia đình từ người dùng",
        delta_type="pct_total",
    ),
    "FIT_KITCHEN_EXISTS": Adjustment(
        factor_code="FIT_KITCHEN_EXISTS",
        layer=AdjustmentLayer.FIT,
        group=FactorGroup.F3_FAMILY,
        asset_types={"TOWNHOUSE", "VILLA", "HOUSE"},
        delta_pct_base=0.015,
        confidence_base=0.60,
        rationale_template="Có bếp riêng phù hợp với gia đình Việt.",
        evidence_requirement="Kiểm tra thực địa",
        delta_type="pct_total",
    ),

    # F4: Investment adjustments — liquidity, growth potential, rental yield
    "FIT_LIQUIDITY_HIGH": Adjustment(
        factor_code="FIT_LIQUIDITY_HIGH",
        layer=AdjustmentLayer.FIT,
        group=FactorGroup.F4_INVESTMENT,
        asset_types={"APARTMENT", "TOWNHOUSE"},
        delta_pct_base=0.03,
        confidence_base=0.70,
        rationale_template="BĐS thanh khoản cao — dễ bán, dễ cho thuê.",
        evidence_requirement="Dữ liệu thị trường thứ cấp",
        delta_type="pct_total",
    ),
    "FIT_LIQUIDITY_LOW": Adjustment(
        factor_code="FIT_LIQUIDITY_LOW",
        layer=AdjustmentLayer.FIT,
        group=FactorGroup.F4_INVESTMENT,
        asset_types={"VILLA", "LAND"},
        delta_pct_base=-0.02,
        confidence_base=0.65,
        rationale_template="BĐS thanh khoản thấp — khó bán nhanh, thời gian chờ dài.",
        evidence_requirement="Dữ liệu thị trường thứ cấp",
        delta_type="pct_total",
    ),
    "FIT_GROWTH_METRO": Adjustment(
        factor_code="FIT_GROWTH_METRO",
        layer=AdjustmentLayer.FIT,
        group=FactorGroup.F4_INVESTMENT,
        asset_types={"TOWNHOUSE", "APARTMENT"},
        delta_pct_base=0.04,
        confidence_base=0.75,
        rationale_template="Gần metro tương lai — tiềm năng tăng giá cao.",
        evidence_requirement="Quy hoạch metro đã phê duyệt",
        delta_type="pct_total",
    ),
    "FIT_GROWTH_NEWTOWN": Adjustment(
        factor_code="FIT_GROWTH_NEWTOWN",
        layer=AdjustmentLayer.FIT,
        group=FactorGroup.F4_INVESTMENT,
        asset_types={"TOWNHOUSE", "LAND"},
        delta_pct_base=0.03,
        confidence_base=0.70,
        rationale_template="Trong khu đô thị mới — hạ tầng đang phát triển nhanh.",
        evidence_requirement="Quy hoạch đô thị",
        delta_type="pct_total",
    ),
    "FIT_YIELD_RENTAL": Adjustment(
        factor_code="FIT_YIELD_RENTAL",
        layer=AdjustmentLayer.FIT,
        group=FactorGroup.F4_INVESTMENT,
        asset_types={"APARTMENT"},
        delta_pct_base=0.02,
        confidence_base=0.65,
        rationale_template="Căn hộ cho thuê tốt — tỷ lệ lấp đầy cao trong khu vực.",
        evidence_requirement="Dữ liệu rental market",
        delta_type="pct_total",
    ),
}


class AdjustmentRegistry:
    """
    Registry quản lý tất cả adjustment factors.
    Cung cấp lookup, filtering, và validation.
    """

    def __init__(self):
        self._registry: Dict[str, Adjustment] = FACTOR_REGISTRY

    def get(self, factor_code: str) -> Optional[Adjustment]:
        return self._registry.get(factor_code)

    def list_all(self) -> List[Adjustment]:
        return list(self._registry.values())

    def list_market_factors(self) -> List[Adjustment]:
        return [a for a in self._registry.values() if a.layer == AdjustmentLayer.MARKET]

    def list_fit_factors(self) -> List[Adjustment]:
        return [a for a in self._registry.values() if a.layer == AdjustmentLayer.FIT]

    def list_by_asset_type(self, asset_type: str) -> List[Adjustment]:
        return [
            a for a in self._registry.values()
            if not a.asset_types or asset_type in a.asset_types
        ]

    def list_by_layer(self, layer: AdjustmentLayer) -> List[Adjustment]:
        return [a for a in self._registry.values() if a.layer == layer]

    def list_by_group(self, group: FactorGroup) -> List[Adjustment]:
        return [a for a in self._registry.values() if a.group == group]

    def is_registered(self, factor_code: str) -> bool:
        return factor_code in self._registry

    def validate_factor_code(self, factor_code: str) -> bool:
        """Validate rằng factor_code hợp lệ theo taxonomy."""
        return self.is_registered(factor_code)

    def get_applicable_factors(
        self,
        asset_type: str,
        layer: Optional[AdjustmentLayer] = None,
    ) -> List[Adjustment]:
        """Lấy danh sách factors áp dụng cho một loại tài sản."""
        factors = [
            a for a in self._registry.values()
            if not a.asset_types or asset_type in a.asset_types
        ]
        if layer:
            factors = [f for f in factors if f.layer == layer]
        return factors
