#!/usr/bin/env python3
"""
Collect expert ratings: distribute properties to 3 experts,
track completion, aggregate median of medians, and save to DB.
Run: python scripts/pilot/collect_expert_ratings.py --status
     python scripts/pilot/collect_expert_ratings.py --aggregate
"""
import sys
sys.path.insert(0, ".")
import json, argparse, statistics
from src.backend.database import SessionLocal, init_db
from src.backend.models import ExpertProperty, ExpertRating, Property

def collect(status_only=False, aggregate_only=False):
    init_db()
    db = SessionLocal()

    try:
        if status_only:
            # Status report
            total = db.query(ExpertProperty).count()
            pending = db.query(ExpertProperty).filter(ExpertProperty.status == "pending").count()
            in_progress = db.query(ExpertProperty).filter(ExpertProperty.status == "in_progress").count()
            completed = db.query(ExpertProperty).filter(ExpertProperty.status == "completed").count()

            ratings_by_expert = {}
            for eid in ["expert_1", "expert_2", "expert_3"]:
                cnt = db.query(ExpertRating).filter(ExpertRating.expert_id == eid).count()
                ratings_by_expert[eid] = cnt

            print("=" * 60)
            print("EXPERT RATING COLLECTION STATUS")
            print("=" * 60)
            print(f"  Total properties in evaluation: {total}")
            print(f"  Status breakdown:")
            print(f"    Pending:     {pending}")
            print(f"    In progress: {in_progress}")
            print(f"    Completed:   {completed}")
            print(f"  Ratings by expert:")
            for eid, cnt in ratings_by_expert.items():
                print(f"    {eid}: {cnt} ratings")
            print(f"  Coverage: {completed}/{total} properties have 3 ratings")
            print()

            if completed > 0:
                # Show sample aggregated results
                completed_eps = db.query(ExpertProperty).filter(
                    ExpertProperty.status == "completed"
                ).limit(5).all()
                print("Sample aggregated results:")
                for ep in completed_eps:
                    ratings = db.query(ExpertRating).filter(
                        ExpertRating.property_id == ep.property_id
                    ).all()
                    mids = [r.expert_mid for r in ratings]
                    print(f"  Prop {ep.property_id}: expert_mid values = {[f'{m/1e9:.2f}B' for m in mids]}, "
                          f"aggregated_mid = {ep.aggregated_mid/1e9:.2f}B")
            print("=" * 60)
            return

        if aggregate_only:
            # Aggregate all completed properties
            eps = db.query(ExpertProperty).filter(ExpertProperty.status != "completed").all()
            updated = 0
            for ep in eps:
                all_ratings = db.query(ExpertRating).filter(
                    ExpertRating.property_id == ep.property_id
                ).all()
                if len(all_ratings) >= 1:
                    # Update counts
                    ep.ratings_collected = len(all_ratings)
                    if len(all_ratings) >= 3:
                        ep.status = "completed"
                        mids = sorted([r.expert_mid for r in all_ratings])
                        lows = sorted([r.expert_low for r in all_ratings])
                        highs = sorted([r.expert_high for r in all_ratings])
                        ep.aggregated_low = lows[len(lows)//2]
                        ep.aggregated_mid = mids[len(mids)//2]
                        ep.aggregated_high = highs[len(highs)//2]
                        confs = [r.confidence for r in all_ratings]
                        ep.aggregated_confidence = max(set(confs), key=confs.count)
                        updated += 1
                    elif len(all_ratings) > 0:
                        ep.status = "in_progress"
                    db.commit()

            print(f"[OK] Aggregated — {updated} properties finalized")
            return

        # Default: full report
        print("Run with --status or --aggregate")

    finally:
        db.close()


def generate_expert_csv():
    """Export CSV of properties for offline expert evaluation."""
    init_db()
    db = SessionLocal()

    try:
        eps = db.query(ExpertProperty).order_by(
            ExpertProperty.district, ExpertProperty.cluster_key
        ).all()

        prop_ids = [ep.property_id for ep in eps]
        props = {p.id: p for p in db.query(Property).filter(Property.id.in_(prop_ids)).all()}

        import csv
        output_path = "data/pilot/expert_evaluation_template.csv"
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "property_id", "district", "area_m2", "bedrooms",
                "listing_price", "listing_ppm", "source",
                "expert_1_low", "expert_1_mid", "expert_1_high", "expert_1_conf", "expert_1_comment",
                "expert_2_low", "expert_2_mid", "expert_2_high", "expert_2_conf", "expert_2_comment",
                "expert_3_low", "expert_3_mid", "expert_3_high", "expert_3_conf", "expert_3_comment",
            ])
            for ep in eps:
                p = props.get(ep.property_id)
                writer.writerow([
                    ep.property_id,
                    ep.district,
                    ep.area_m2,
                    ep.bedrooms,
                    p.price if p else "",
                    p.price_per_m2 if p else "",
                    p.source_name if p else "",
                    "", "", "", "", "",  # expert_1
                    "", "", "", "", "",  # expert_2
                    "", "", "", "", "",  # expert_3
                ])

        print(f"[OK] Exported {len(eps)} properties to {output_path}")
        print("  Fill in expert ratings, then run --aggregate after importing")
    finally:
        db.close()


def import_expert_csv(csv_path):
    """Import expert ratings from CSV file."""
    init_db()
    db = SessionLocal()

    import csv
    imported = 0
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            prop_id = int(row["property_id"])
            for expert_num in [1, 2, 3]:
                low_key = f"expert_{expert_num}_low"
                mid_key = f"expert_{expert_num}_mid"
                high_key = f"expert_{expert_num}_high"
                conf_key = f"expert_{expert_num}_conf"
                comment_key = f"expert_{expert_num}_comment"

                low = row.get(low_key, "")
                mid = row.get(mid_key, "")
                high = row.get(high_key, "")
                conf = row.get(conf_key, "medium") or "medium"
                comment = row.get(comment_key, "") or ""

                if not mid or not mid.strip():
                    continue  # Skip empty ratings

                # Check if already exists
                existing = db.query(ExpertRating).filter(
                    ExpertRating.property_id == prop_id,
                    ExpertRating.expert_id == f"expert_{expert_num}",
                ).first()

                if existing:
                    existing.expert_low = float(low) if low else existing.expert_low
                    existing.expert_mid = float(mid)
                    existing.expert_high = float(high) if high else existing.expert_high
                    existing.confidence = conf
                    existing.comment = comment
                    existing.source = "csv_import"
                else:
                    rating = ExpertRating(
                        property_id=prop_id,
                        expert_id=f"expert_{expert_num}",
                        expert_name=f"Chuyên gia {expert_num}",
                        expert_low=float(low) if low else 0,
                        expert_mid=float(mid),
                        expert_high=float(high) if high else 0,
                        confidence=conf,
                        comment=comment,
                        source="csv_import",
                    )
                    db.add(rating)

                imported += 1

    db.commit()

    # Update expert_property counts
    eps = db.query(ExpertProperty).all()
    for ep in eps:
        cnt = db.query(ExpertRating).filter(ExpertRating.property_id == ep.property_id).count()
        ep.ratings_collected = cnt
        ep.completed_count = cnt
        if cnt >= 3:
            ep.status = "completed"
            ratings = db.query(ExpertRating).filter(
                ExpertRating.property_id == ep.property_id
            ).all()
            mids = sorted([r.expert_mid for r in ratings])
            lows = sorted([r.expert_low for r in ratings])
            highs = sorted([r.expert_high for r in ratings])
            ep.aggregated_low = lows[len(lows)//2]
            ep.aggregated_mid = mids[len(mids)//2]
            ep.aggregated_high = highs[len(highs)//2]
            confs = [r.confidence for r in ratings]
            ep.aggregated_confidence = max(set(confs), key=confs.count)
        db.commit()

    db.close()
    print(f"[OK] Imported {imported} ratings from {csv_path}")
    collect(status_only=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Expert rating collection pipeline")
    parser.add_argument("--status", action="store_true", help="Show collection status")
    parser.add_argument("--aggregate", action="store_true", help="Aggregate ratings to expert_properties")
    parser.add_argument("--export-csv", action="store_true", help="Export template CSV")
    parser.add_argument("--import-csv", type=str, metavar="FILE", help="Import ratings from CSV")
    args = parser.parse_args()

    if args.status:
        collect(status_only=True)
    elif args.aggregate:
        collect(aggregate_only=True)
    elif args.export_csv:
        generate_expert_csv()
    elif args.import_csv:
        import_expert_csv(args.import_csv)
    else:
        parser.print_help()
        print()
        print("Workflow:")
        print("  1. python scripts/pilot/collect_expert_ratings.py --export-csv  # Export for offline")
        print("  2. Open paper/expert_evaluation_template.csv              # Expert fills in")
        print("  3. python scripts/pilot/collect_expert_ratings.py --import-csv FILE")
        print("  4. python scripts/pilot/collect_expert_ratings.py --status     # Check progress")
        print("  5. python scripts/pilot/collect_expert_ratings.py --aggregate    # Finalize")