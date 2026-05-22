"""
Geometry Calculator — Production-grade parcel geometry analysis.

Novelty vs academic literature:
- Most AVM papers (Scopus/ISI) use only area_m2 as geometry feature.
- This engine computes polygon-derived metrics: nở hậu/thóp hậu scoring,
  neck (cổ chai) detection, irregularity index, buildable area estimation,
  and frontage-depth analysis from actual polygon vertices.

Key formulas:
  area = Shoelace formula on polygon vertices
  irregularity = 1 - (area / convex_hull_area)
  nở_hậu_score = rear_width / front_width (>1 = nở hậu)
  thóp_hậu_score = min_width / max_width (low = severe taper)
  neck_ratio = min_cross_section / max_cross_section
  buildable_area = area - setback_area - unbuildable_area
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class ParcelVertex:
    """A vertex in the parcel polygon."""
    lat: float
    lng: float

    def to_tuple(self) -> Tuple[float, float]:
        return (self.lat, self.lng)


@dataclass
class ParcelEdge:
    """An edge of the parcel polygon."""
    start: ParcelVertex
    end: ParcelVertex
    length_m: float
    azimuth_deg: float
    is_road_facing: bool = False
    road_class: Optional[str] = None  # MAIN_STREET|ALLEY_5M|...


@dataclass
class GeometryMetrics:
    """Computed geometry metrics for a parcel."""
    # Area
    area_polygon_m2: float = 0.0
    area_convex_hull_m2: float = 0.0

    # Shape scores (0-1)
    irregularity_score: float = 0.0      # 0=vuông, 1=rất méo
    convexity_ratio: float = 1.0         # area/convex_hull_area
    nö_hậu_score: float = 0.5           # >0.5 = nở hậu, <0.5 = thóp hậu
    thóp_hậu_score: float = 0.0         # 0=vuông, 1=thóp nặng
    squareness_score: float = 1.0        # How close to rectangle (1=perfect)

    # Dimensions
    frontage_total_m: float = 0.0
    depth_min_m: float = 0.0
    depth_max_m: float = 0.0
    depth_avg_m: float = 0.0
    depth_variation_pct: float = 0.0     # (max-min)/avg * 100
    frontage_depth_ratio: float = 0.0    # frontage/depth, optimal = 0.33-0.50

    # Neck detection (cổ chai)
    has_neck: bool = False
    neck_width_m: float = 0.0
    neck_ratio: float = 1.0             # min_width/max_width at neck

    # Taper classification
    taper_type: str = "uniform"          # uniform|nö_hậu|thóp_hậu|reverse_taper|irregular

    # Buildable area
    buildable_area_m2: float = 0.0
    buildable_ratio: float = 1.0         # buildable/total
    setback_front_m: float = 0.0
    setback_back_m: float = 0.0
    setback_side_m: float = 0.0

    # Special features
    corner_plot: bool = False
    road_facing_count: int = 1
    has_alley_branch: bool = False
    useless_area_m2: float = 0.0        # Phần đất không khai thác được

    # Edge data
    vertices_count: int = 0
    perimeter_m: float = 0.0
    edges: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "area_polygon_m2": round(self.area_polygon_m2, 2),
            "area_convex_hull_m2": round(self.area_convex_hull_m2, 2),
            "irregularity_score": round(self.irregularity_score, 4),
            "convexity_ratio": round(self.convexity_ratio, 4),
            "nö_hậu_score": round(self.nö_hậu_score, 4),
            "thóp_hậu_score": round(self.thóp_hậu_score, 4),
            "squareness_score": round(self.squareness_score, 4),
            "frontage_total_m": round(self.frontage_total_m, 2),
            "depth_min_m": round(self.depth_min_m, 2),
            "depth_max_m": round(self.depth_max_m, 2),
            "depth_avg_m": round(self.depth_avg_m, 2),
            "depth_variation_pct": round(self.depth_variation_pct, 2),
            "frontage_depth_ratio": round(self.frontage_depth_ratio, 4),
            "has_neck": self.has_neck,
            "neck_width_m": round(self.neck_width_m, 2),
            "neck_ratio": round(self.neck_ratio, 4),
            "taper_type": self.taper_type,
            "buildable_area_m2": round(self.buildable_area_m2, 2),
            "buildable_ratio": round(self.buildable_ratio, 4),
            "corner_plot": self.corner_plot,
            "road_facing_count": self.road_facing_count,
            "useless_area_m2": round(self.useless_area_m2, 2),
            "vertices_count": self.vertices_count,
            "perimeter_m": round(self.perimeter_m, 2),
        }


class GeometryCalculator:
    """
    Production-grade parcel geometry analysis engine.

    Differentiators vs academic AVM literature:
    1. Polygon-based analysis instead of scalar area_m2
    2. Neck (cổ chai) detection for irregular parcels
    3. Nở hậu / thóp hậu scoring from cross-section analysis
    4. Buildable area estimation with setback calculation
    5. Shape classification (uniform/taper/irregular)
    """

    # Earth radius in meters for Haversine
    EARTH_RADIUS_M = 6_371_000

    def compute(
        self,
        vertices: List[Tuple[float, float]],
        road_facing_edges: Optional[List[int]] = None,
        setback_front_m: float = 0.0,
        setback_back_m: float = 0.0,
        setback_side_m: float = 0.0,
    ) -> GeometryMetrics:
        """
        Compute all geometry metrics from polygon vertices.

        Args:
            vertices: List of (lat, lng) tuples forming closed polygon
            road_facing_edges: Indices of edges that face a road
            setback_front_m: Front setback requirement (meters)
            setback_back_m: Back setback requirement
            setback_side_m: Side setback requirement

        Returns:
            GeometryMetrics with all computed values
        """
        if not vertices or len(vertices) < 3:
            return GeometryMetrics()

        # Ensure polygon is closed
        if vertices[0] != vertices[-1]:
            vertices = vertices + [vertices[0]]

        metrics = GeometryMetrics()
        metrics.vertices_count = len(vertices) - 1  # exclude closing vertex

        # Convert to local Cartesian coordinates (meters) for computation
        local_coords = self._to_local_cartesian(vertices)

        # 1. Area (Shoelace formula)
        metrics.area_polygon_m2 = abs(self._shoelace_area(local_coords))

        # 2. Perimeter and edges
        edges_data = []
        total_perimeter = 0.0
        for i in range(len(local_coords) - 1):
            x1, y1 = local_coords[i]
            x2, y2 = local_coords[i + 1]
            length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            azimuth = math.degrees(math.atan2(x2 - x1, y2 - y1)) % 360
            is_road = (road_facing_edges and i in road_facing_edges)
            edges_data.append({
                "index": i,
                "length_m": round(length, 2),
                "azimuth_deg": round(azimuth, 1),
                "is_road_facing": is_road,
            })
            total_perimeter += length

        metrics.perimeter_m = total_perimeter
        metrics.edges = edges_data

        # 3. Convex hull and irregularity
        hull_coords = self._convex_hull(local_coords[:-1])
        metrics.area_convex_hull_m2 = abs(self._shoelace_area(
            hull_coords + [hull_coords[0]]
        ))
        if metrics.area_convex_hull_m2 > 0:
            metrics.convexity_ratio = metrics.area_polygon_m2 / metrics.area_convex_hull_m2
            metrics.irregularity_score = 1.0 - metrics.convexity_ratio
        else:
            metrics.convexity_ratio = 1.0
            metrics.irregularity_score = 0.0

        # 4. Frontage and depth analysis
        frontage_info = self._compute_frontage_depth(
            local_coords, road_facing_edges or [0]
        )
        metrics.frontage_total_m = frontage_info["frontage_m"]
        metrics.depth_min_m = frontage_info["depth_min_m"]
        metrics.depth_max_m = frontage_info["depth_max_m"]
        metrics.depth_avg_m = frontage_info["depth_avg_m"]
        if frontage_info["depth_avg_m"] > 0:
            metrics.depth_variation_pct = (
                (frontage_info["depth_max_m"] - frontage_info["depth_min_m"])
                / frontage_info["depth_avg_m"] * 100
            )
            metrics.frontage_depth_ratio = (
                frontage_info["frontage_m"] / frontage_info["depth_avg_m"]
            )

        # 5. Nở hậu / thóp hậu scoring
        taper_info = self._compute_taper(local_coords, road_facing_edges or [0])
        metrics.nö_hậu_score = taper_info["nö_hậu_score"]
        metrics.thóp_hậu_score = taper_info["thóp_hậu_score"]
        metrics.taper_type = taper_info["taper_type"]

        # 6. Neck (cổ chai) detection
        neck_info = self._detect_neck(local_coords)
        metrics.has_neck = neck_info["has_neck"]
        metrics.neck_width_m = neck_info["neck_width_m"]
        metrics.neck_ratio = neck_info["neck_ratio"]

        # 7. Squareness score
        metrics.squareness_score = self._compute_squareness(local_coords)

        # 8. Road facing and corner detection
        if road_facing_edges:
            metrics.road_facing_count = len(road_facing_edges)
            metrics.corner_plot = len(road_facing_edges) >= 2

        # 9. Buildable area estimation
        metrics.setback_front_m = setback_front_m
        metrics.setback_back_m = setback_back_m
        metrics.setback_side_m = setback_side_m
        buildable = self._estimate_buildable_area(
            metrics.area_polygon_m2,
            metrics.frontage_total_m,
            metrics.depth_avg_m,
            setback_front_m, setback_back_m, setback_side_m,
        )
        metrics.buildable_area_m2 = buildable["buildable_m2"]
        metrics.buildable_ratio = buildable["ratio"]
        metrics.useless_area_m2 = buildable["useless_m2"]

        return metrics

    def compute_from_simple(
        self,
        area_m2: float,
        frontage_m: float,
        depth_min_m: Optional[float] = None,
        depth_max_m: Optional[float] = None,
        corner_plot: bool = False,
        taper_type: Optional[str] = None,
    ) -> GeometryMetrics:
        """
        Compute geometry metrics from simple scalar inputs (no polygon).
        Used when user doesn't provide polygon vertices.
        """
        metrics = GeometryMetrics()
        metrics.area_polygon_m2 = area_m2
        metrics.frontage_total_m = frontage_m

        # Estimate depth
        if depth_min_m and depth_max_m:
            metrics.depth_min_m = depth_min_m
            metrics.depth_max_m = depth_max_m
            metrics.depth_avg_m = (depth_min_m + depth_max_m) / 2
        elif frontage_m > 0:
            estimated_depth = area_m2 / frontage_m
            metrics.depth_min_m = estimated_depth * 0.9
            metrics.depth_max_m = estimated_depth * 1.1
            metrics.depth_avg_m = estimated_depth
        else:
            side = math.sqrt(area_m2)
            metrics.depth_min_m = side
            metrics.depth_max_m = side
            metrics.depth_avg_m = side

        # Depth variation
        if metrics.depth_avg_m > 0:
            metrics.depth_variation_pct = (
                (metrics.depth_max_m - metrics.depth_min_m) /
                metrics.depth_avg_m * 100
            )
            metrics.frontage_depth_ratio = frontage_m / metrics.depth_avg_m

        # Taper classification
        if taper_type:
            metrics.taper_type = taper_type
            if taper_type == "nö_hậu":
                metrics.nö_hậu_score = 0.85
                metrics.thóp_hậu_score = 0.0
            elif taper_type == "thóp_hậu":
                metrics.nö_hậu_score = 0.0
                metrics.thóp_hậu_score = 0.7
            elif taper_type == "irregular":
                metrics.irregularity_score = 0.5
        else:
            # Infer from dimensions
            if depth_min_m and depth_max_m and depth_max_m > 0:
                ratio = depth_min_m / depth_max_m
                if ratio > 0.95:
                    metrics.taper_type = "uniform"
                    metrics.squareness_score = 0.95
                elif depth_min_m < depth_max_m * 0.7:
                    metrics.taper_type = "thóp_hậu"
                    metrics.thóp_hậu_score = 1.0 - ratio
                else:
                    metrics.taper_type = "uniform"
            else:
                metrics.taper_type = "uniform"

        # Corner plot
        metrics.corner_plot = corner_plot
        metrics.road_facing_count = 2 if corner_plot else 1

        # Squareness from frontage-depth ratio
        fdr = metrics.frontage_depth_ratio
        if 0.25 <= fdr <= 0.50:
            metrics.squareness_score = 0.95  # Optimal 1:2 to 1:4
        elif 0.15 <= fdr <= 0.65:
            metrics.squareness_score = 0.80
        else:
            metrics.squareness_score = max(0.3, 1.0 - abs(fdr - 0.33) * 2)

        return metrics

    # ─── Internal computation methods ──────────────────────────────────

    def _to_local_cartesian(
        self, vertices: List[Tuple[float, float]]
    ) -> List[Tuple[float, float]]:
        """Convert lat/lng to local cartesian (meters) relative to centroid."""
        if not vertices:
            return []

        # Centroid
        n = len(vertices)
        clat = sum(v[0] for v in vertices) / n
        clng = sum(v[1] for v in vertices) / n

        result = []
        for lat, lng in vertices:
            x = (lng - clng) * self.EARTH_RADIUS_M * math.cos(math.radians(clat)) * math.pi / 180
            y = (lat - clat) * self.EARTH_RADIUS_M * math.pi / 180
            result.append((x, y))
        return result

    def _shoelace_area(self, coords: List[Tuple[float, float]]) -> float:
        """Compute area using Shoelace formula."""
        n = len(coords)
        if n < 3:
            return 0.0
        area = 0.0
        for i in range(n - 1):
            area += coords[i][0] * coords[i + 1][1]
            area -= coords[i + 1][0] * coords[i][1]
        return area / 2.0

    def _convex_hull(
        self, points: List[Tuple[float, float]]
    ) -> List[Tuple[float, float]]:
        """Compute convex hull using Graham scan."""
        if len(points) < 3:
            return points[:]

        # Find the point with lowest y (then leftmost x)
        start = min(points, key=lambda p: (p[1], p[0]))

        def polar_angle(p):
            return math.atan2(p[1] - start[1], p[0] - start[0])

        sorted_points = sorted(points, key=polar_angle)

        stack = []
        for p in sorted_points:
            while len(stack) > 1 and self._cross(stack[-2], stack[-1], p) <= 0:
                stack.pop()
            stack.append(p)

        return stack

    def _cross(self, o, a, b) -> float:
        """Cross product of vectors OA and OB."""
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def _compute_frontage_depth(
        self,
        local_coords: List[Tuple[float, float]],
        road_edges: List[int],
    ) -> Dict:
        """Compute frontage and depth from polygon."""
        if len(local_coords) < 3:
            return {"frontage_m": 0, "depth_min_m": 0, "depth_max_m": 0, "depth_avg_m": 0}

        # Frontage = sum of road-facing edge lengths
        frontage = 0.0
        for idx in road_edges:
            if idx < len(local_coords) - 1:
                x1, y1 = local_coords[idx]
                x2, y2 = local_coords[idx + 1]
                frontage += math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

        if frontage == 0:
            # Fallback: use first edge
            if len(local_coords) >= 2:
                x1, y1 = local_coords[0]
                x2, y2 = local_coords[1]
                frontage = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

        # Depth = perpendicular distances from non-road vertices to frontage line
        if len(road_edges) > 0 and road_edges[0] < len(local_coords) - 1:
            fx1, fy1 = local_coords[road_edges[0]]
            fx2, fy2 = local_coords[road_edges[0] + 1]

            depths = []
            for i, (x, y) in enumerate(local_coords[:-1]):
                if i in road_edges:
                    continue
                # Perpendicular distance to frontage line
                line_len = math.sqrt((fx2 - fx1) ** 2 + (fy2 - fy1) ** 2)
                if line_len > 0:
                    dist = abs((fy2 - fy1) * x - (fx2 - fx1) * y + fx2 * fy1 - fy2 * fx1) / line_len
                    depths.append(dist)

            if depths:
                return {
                    "frontage_m": frontage,
                    "depth_min_m": min(depths),
                    "depth_max_m": max(depths),
                    "depth_avg_m": sum(depths) / len(depths),
                }

        # Fallback: estimate from area / frontage
        area = abs(self._shoelace_area(local_coords))
        est_depth = area / frontage if frontage > 0 else math.sqrt(area)
        return {
            "frontage_m": frontage,
            "depth_min_m": est_depth * 0.9,
            "depth_max_m": est_depth * 1.1,
            "depth_avg_m": est_depth,
        }

    def _compute_taper(
        self,
        local_coords: List[Tuple[float, float]],
        road_edges: List[int],
    ) -> Dict:
        """
        Compute nở hậu / thóp hậu score by measuring
        cross-section widths at front and rear.
        """
        if len(local_coords) < 4:
            return {"nö_hậu_score": 0.5, "thóp_hậu_score": 0.0, "taper_type": "uniform"}

        # Measure width at front (near road) and rear (far from road)
        front_edge_idx = road_edges[0] if road_edges else 0
        if front_edge_idx >= len(local_coords) - 1:
            front_edge_idx = 0

        fx1, fy1 = local_coords[front_edge_idx]
        fx2, fy2 = local_coords[front_edge_idx + 1]
        front_width = math.sqrt((fx2 - fx1) ** 2 + (fy2 - fy1) ** 2)

        # Find the rear edge (opposite side of polygon)
        n = len(local_coords) - 1
        rear_idx = (front_edge_idx + n // 2) % n
        rx1, ry1 = local_coords[rear_idx]
        rx2, ry2 = local_coords[(rear_idx + 1) % n]
        rear_width = math.sqrt((rx2 - rx1) ** 2 + (ry2 - ry1) ** 2)

        if front_width == 0:
            return {"nö_hậu_score": 0.5, "thóp_hậu_score": 0.0, "taper_type": "uniform"}

        ratio = rear_width / front_width

        if ratio > 1.15:
            # Nở hậu (rear wider than front)
            nö_hậu_score = min(1.0, ratio - 0.5)
            return {
                "nö_hậu_score": nö_hậu_score,
                "thóp_hậu_score": 0.0,
                "taper_type": "nö_hậu",
            }
        elif ratio < 0.85:
            # Thóp hậu (rear narrower than front)
            thóp_hậu_score = min(1.0, (1.0 - ratio))
            return {
                "nö_hậu_score": 0.0,
                "thóp_hậu_score": thóp_hậu_score,
                "taper_type": "thóp_hậu" if thóp_hậu_score < 0.5 else "reverse_taper",
            }
        else:
            # Uniform
            return {"nö_hậu_score": 0.5, "thóp_hậu_score": 0.0, "taper_type": "uniform"}

    def _detect_neck(self, local_coords: List[Tuple[float, float]]) -> Dict:
        """
        Detect neck (cổ chai) in the parcel — a narrow constriction.
        Uses cross-section sampling along the depth axis.
        """
        if len(local_coords) < 5:
            return {"has_neck": False, "neck_width_m": 0.0, "neck_ratio": 1.0}

        coords = local_coords[:-1]  # Remove closing vertex

        # Find bounding box
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        min_y, max_y = min(ys), max(ys)
        height = max_y - min_y

        if height <= 0:
            return {"has_neck": False, "neck_width_m": 0.0, "neck_ratio": 1.0}

        # Sample cross-section widths at multiple y-levels
        n_samples = min(20, max(5, len(coords)))
        widths = []
        for i in range(n_samples):
            y_level = min_y + (height * i / (n_samples - 1))
            width = self._cross_section_width(coords, y_level)
            if width > 0:
                widths.append(width)

        if len(widths) < 3:
            return {"has_neck": False, "neck_width_m": 0.0, "neck_ratio": 1.0}

        min_width = min(widths)
        max_width = max(widths)

        if max_width <= 0:
            return {"has_neck": False, "neck_width_m": 0.0, "neck_ratio": 1.0}

        neck_ratio = min_width / max_width

        # Neck detected if min_width is significantly less than max_width
        # AND the narrow point is NOT at the ends (which would be taper, not neck)
        min_idx = widths.index(min_width)
        is_interior = 1 < min_idx < len(widths) - 2

        has_neck = neck_ratio < 0.5 and is_interior

        return {
            "has_neck": has_neck,
            "neck_width_m": min_width,
            "neck_ratio": round(neck_ratio, 4),
        }

    def _cross_section_width(
        self, coords: List[Tuple[float, float]], y_level: float
    ) -> float:
        """Compute the width of polygon at a given y-level."""
        intersections = []
        n = len(coords)

        for i in range(n):
            x1, y1 = coords[i]
            x2, y2 = coords[(i + 1) % n]

            if (y1 <= y_level < y2) or (y2 <= y_level < y1):
                if y2 != y1:
                    t = (y_level - y1) / (y2 - y1)
                    x_intersect = x1 + t * (x2 - x1)
                    intersections.append(x_intersect)

        if len(intersections) >= 2:
            return max(intersections) - min(intersections)
        return 0.0

    def _compute_squareness(self, local_coords: List[Tuple[float, float]]) -> float:
        """
        Compute squareness score (how close to rectangle).
        Uses the ratio of area to bounding box area.
        """
        coords = local_coords[:-1]
        if len(coords) < 3:
            return 1.0

        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        bbox_area = (max(xs) - min(xs)) * (max(ys) - min(ys))

        if bbox_area <= 0:
            return 1.0

        polygon_area = abs(self._shoelace_area(local_coords))
        ratio = polygon_area / bbox_area

        return min(1.0, max(0.0, ratio))

    def _estimate_buildable_area(
        self,
        total_area: float,
        frontage: float,
        depth: float,
        setback_front: float,
        setback_back: float,
        setback_side: float,
    ) -> Dict:
        """Estimate buildable area after setbacks."""
        if total_area <= 0 or frontage <= 0 or depth <= 0:
            return {"buildable_m2": total_area, "ratio": 1.0, "useless_m2": 0.0}

        effective_frontage = max(0, frontage - 2 * setback_side)
        effective_depth = max(0, depth - setback_front - setback_back)
        buildable = effective_frontage * effective_depth

        # Can't exceed total area
        buildable = min(buildable, total_area)
        useless = total_area - buildable

        return {
            "buildable_m2": round(buildable, 2),
            "ratio": round(buildable / total_area, 4) if total_area > 0 else 1.0,
            "useless_m2": round(useless, 2),
        }
