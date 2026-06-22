#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MLOps CLI — vận hành model trực tiếp (chạy từ Research Lab UI, không cần đụng code).

Subcommands:
  experiments            Bảng leaderboard mọi lần train (đọc models/metadata_*.json).
  registry               Liệt kê model version + version đang active.
  activate --version TS  Trỏ backend dùng đúng model_<TS>.pkl (rollback có chủ đích).
  drift                  Population Stability Index (PSI) giữa baseline train và DB hiện tại.
  monitor                Health-check model đang active: load + smoke predict.

Tất cả output ra stdout (Research Lab hiển thị log thật).
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MODELS_DIR = PROJECT_ROOT / "models"
POINTER = MODELS_DIR / "ACTIVE_MODEL.json"


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _fmt_vnd(x):
    try:
        return f"{float(x) / 1e9:.2f} tỷ"
    except (TypeError, ValueError):
        return "—"


def _load_metadata_files():
    rows = []
    for meta_path in sorted(MODELS_DIR.glob("metadata_*.json")):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            continue
        stamp = meta_path.stem.replace("metadata_", "")
        best = meta.get("best_model", "?")
        results = meta.get("all_results", {}).get(best, {})
        rows.append({
            "stamp": stamp,
            "model_file": f"model_{stamp}.pkl",
            "best_model": best,
            "trained_at": meta.get("trained_at", "?"),
            "n_features": meta.get("n_features", "?"),
            "train_size": meta.get("train_size", "?"),
            "test_r2": results.get("test_r2", results.get("r2")),
            "test_mae": results.get("test_mae", results.get("mae")),
            "test_rmse": results.get("test_rmse", results.get("rmse")),
            "has_pkl": (MODELS_DIR / f"model_{stamp}.pkl").exists(),
        })
    rows.sort(key=lambda r: r["stamp"], reverse=True)
    return rows


def _active_stamp():
    if POINTER.exists():
        try:
            with open(POINTER, "r", encoding="utf-8") as f:
                return json.load(f).get("stamp")
        except Exception:
            return None
    return None


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_experiments(_args):
    rows = _load_metadata_files()
    if not rows:
        print("Chưa có metadata training nào trong models/.")
        return 0
    active = _active_stamp()
    print(f"EXPERIMENT LEADERBOARD — {len(rows)} lần train\n")
    print(f"{'':2}{'VERSION':<18}{'MODEL':<34}{'R2':>7}{'MAE':>12}{'FEAT':>6}{'TRAIN':>8}")
    print("-" * 90)
    for r in rows:
        mark = "* " if r["stamp"] == active else "  "
        r2 = f"{r['test_r2']:.3f}" if isinstance(r["test_r2"], (int, float)) else "—"
        print(f"{mark}{r['stamp']:<18}{str(r['best_model'])[:33]:<34}{r2:>7}"
              f"{_fmt_vnd(r['test_mae']):>12}{str(r['n_features']):>6}{str(r['train_size']):>8}")
    print("\n(*) = version đang active. Best R2 ở trên cùng nếu sắp theo thời gian.")
    # Highlight best by R2
    scored = [r for r in rows if isinstance(r["test_r2"], (int, float))]
    if scored:
        best = max(scored, key=lambda r: r["test_r2"])
        print(f"\nBEST theo test_R2: {best['stamp']} ({best['best_model']}) R2={best['test_r2']:.3f} "
              f"MAE={_fmt_vnd(best['test_mae'])}")
    return 0


def cmd_registry(_args):
    rows = _load_metadata_files()
    active = _active_stamp()
    print("MODEL REGISTRY\n")
    if active:
        print(f"ACTIVE (pinned): {active}")
    else:
        print("ACTIVE: <missing ACTIVE_MODEL.json - prediction serving must fail closed>")
    print(f"\nArtifacts khả dụng ({sum(1 for r in rows if r['has_pkl'])} có .pkl):")
    for r in rows:
        flag = "ok " if r["has_pkl"] else "NO-PKL"
        mark = " <== ACTIVE" if r["stamp"] == active else ""
        print(f"  [{flag}] {r['model_file']:<28} {r['best_model']}{mark}")
    return 0


def cmd_activate(args):
    stamp = args.version.strip()
    model_file = f"model_{stamp}.pkl"
    target = MODELS_DIR / model_file
    if not target.exists():
        print(f"LỖI: không tìm thấy {model_file} trong models/.")
        print("Dùng `registry` để xem version hợp lệ.")
        return 2
    payload = {
        "stamp": stamp,
        "model_file": model_file,
        "activated_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(POINTER, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Đã activate version {stamp} -> {model_file}")
    print("Backend sẽ dùng version này sau khi reload cache (chạy operation 'Reload backend model cache').")
    return 0


def cmd_deactivate(_args):
    if POINTER.exists():
        POINTER.unlink()
        print("Đã gỡ pin. Backend quay lại auto-chọn model mới nhất.")
    else:
        print("Không có pin nào đang đặt.")
    return 0


def cmd_drift(_args):
    """PSI giữa phân phối baseline (lúc train) và dữ liệu hiện tại trong DB."""
    import numpy as np

    from src.backend.database import SessionLocal
    from src.backend.models import Property

    rows = _load_metadata_files()
    if not rows:
        print("Chưa có model baseline để so sánh drift.")
        return 0
    # Baseline = summary lúc train của version active (hoặc mới nhất)
    active = _active_stamp() or rows[0]["stamp"]
    meta_path = MODELS_DIR / f"metadata_{active}.json"
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            baseline_meta = json.load(f)
    except Exception:
        baseline_meta = {}
    baseline_n = baseline_meta.get("train_size", 0)

    db = SessionLocal()
    try:
        props = db.query(Property).filter(
            Property.price.isnot(None), Property.price > 0,
            Property.area_m2.isnot(None), Property.area_m2 > 0,
        ).all()
    finally:
        db.close()

    if len(props) < 30:
        print(f"Chỉ có {len(props)} bản ghi hợp lệ — chưa đủ để đo drift đáng tin (cần >=30).")
        return 0

    def psi(expected, actual, bins=10):
        expected = np.asarray(expected, dtype=float)
        actual = np.asarray(actual, dtype=float)
        if len(expected) == 0 or len(actual) == 0:
            return 0.0
        quantiles = np.linspace(0, 100, bins + 1)
        edges = np.unique(np.percentile(expected, quantiles))
        if len(edges) < 3:
            return 0.0
        e_hist, _ = np.histogram(expected, bins=edges)
        a_hist, _ = np.histogram(actual, bins=edges)
        e_pct = np.clip(e_hist / max(e_hist.sum(), 1), 1e-4, None)
        a_pct = np.clip(a_hist / max(a_hist.sum(), 1), 1e-4, None)
        return float(np.sum((a_pct - e_pct) * np.log(a_pct / e_pct)))

    # Baseline reference: chia dữ liệu hiện tại theo thời gian (nửa cũ vs nửa mới)
    # vì baseline raw không lưu trong metadata. Đây là drift nội bộ theo thời gian.
    # Sắp theo id (monotonic) để tránh lỗi so sánh datetime tz-aware vs naive.
    props_sorted = sorted(props, key=lambda p: (p.id or 0))
    half = len(props_sorted) // 2
    ref, cur = props_sorted[:half], props_sorted[half:]

    features = {
        "price_per_m2": lambda p: (p.price / p.area_m2) if (p.price and p.area_m2) else None,
        "area_m2": lambda p: p.area_m2,
        "price": lambda p: p.price,
        "bedrooms": lambda p: p.bedrooms,
        "floor_count": lambda p: p.floor_count,
    }

    print("DATA DRIFT — Population Stability Index (PSI)")
    print(f"Baseline version: {active} (train_size={baseline_n})")
    print(f"So sánh: {len(ref)} bản ghi cũ  vs  {len(cur)} bản ghi mới\n")
    print(f"{'FEATURE':<16}{'PSI':>8}   TÌNH TRẠNG")
    print("-" * 50)
    worst = 0.0
    for name, fn in features.items():
        e = [v for v in (fn(p) for p in ref) if v is not None]
        a = [v for v in (fn(p) for p in cur) if v is not None]
        if len(e) < 10 or len(a) < 10:
            print(f"{name:<16}{'n/a':>8}   thiếu dữ liệu")
            continue
        val = psi(e, a)
        worst = max(worst, val)
        if val < 0.1:
            tag = "ổn định"
        elif val < 0.25:
            tag = "drift nhẹ — theo dõi"
        else:
            tag = "DRIFT MẠNH — nên retrain"
        print(f"{name:<16}{val:>8.4f}   {tag}")
    print("\nNgưỡng: PSI<0.1 ổn định | 0.1-0.25 drift nhẹ | >0.25 cần retrain.")
    print(f"PSI cao nhất = {worst:.4f} -> "
          + ("KHUYẾN NGHỊ RETRAIN." if worst >= 0.25 else "Chưa cần retrain."))
    return 0


def cmd_monitor(_args):
    """Health-check model đang active: load được không + smoke predict."""
    active = _active_stamp()
    rows = _load_metadata_files()
    if active:
        model_file = f"model_{active}.pkl"
    elif rows:
        model_file = rows[0]["model_file"]
    else:
        print("HEALTH: FAIL — không có model nào.")
        return 1

    path = MODELS_DIR / model_file
    print("MODEL HEALTH CHECK")
    print(f"Target: {model_file} (active_pin={'yes' if active else 'auto'})")
    if not path.exists():
        print("HEALTH: FAIL — file model không tồn tại.")
        return 1
    size_mb = path.stat().st_size / 1e6
    try:
        with open(path, "rb") as f:
            data = pickle.load(f)
    except Exception as exc:
        print(f"HEALTH: FAIL — không unpickle được: {exc}")
        return 1

    model = data.get("model")
    feats = data.get("feature_names", [])
    print(f"  - File size      : {size_mb:.2f} MB")
    print(f"  - Estimator      : {type(model).__name__ if model else 'MISSING'}")
    print(f"  - Feature count  : {len(feats)}")
    print(f"  - Has scaler     : {data.get('scaler') is not None}")
    print(f"  - Quantile heads : {len(data.get('quantile_models', {}) or {})}")
    print(f"  - Conformal bands: {len(data.get('conformal_calibration', {}) or {})}")

    if model is None or not feats:
        print("HEALTH: FAIL — bundle thiếu model/feature_names.")
        return 1
    try:
        import numpy as np
        # Model thật có thể nhận nhiều cột hơn feature_names (FeatureEngineer thêm cột
        # quality/confidence). Ưu tiên n_features_in_ của estimator để smoke predict đúng shape.
        n_in = int(getattr(model, "n_features_in_", 0) or 0) or len(feats)
        x = np.zeros((1, n_in), dtype=float)
        pred = model.predict(x)
        print(f"  - Model expects  : {n_in} features")
        print(f"  - Smoke predict  : OK -> {_fmt_vnd(pred[0])}")
    except Exception as exc:
        print(f"HEALTH: FAIL — smoke predict lỗi: {exc}")
        return 1
    print("\nHEALTH: OK — model load + dự đoán được.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="MLOps CLI cho Real Estate AVM")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("experiments")
    sub.add_parser("registry")
    p_act = sub.add_parser("activate")
    p_act.add_argument("--version", required=True)
    sub.add_parser("deactivate")
    sub.add_parser("drift")
    sub.add_parser("monitor")

    args = parser.parse_args()
    handlers = {
        "experiments": cmd_experiments,
        "registry": cmd_registry,
        "activate": cmd_activate,
        "deactivate": cmd_deactivate,
        "drift": cmd_drift,
        "monitor": cmd_monitor,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
