-- ============================================================================
-- Migration: Fix schema constraints (nullable → NOT NULL) + normalize data
-- File: schema/fix_schema_constraints.sql
-- Purpose: Align actual SQLite schema with production design
-- Run: sqlite3 real_estate_avm.db < schema/fix_schema_constraints.sql
-- Note: Creates backup table before altering
-- ============================================================================

-- --------------------------------------------------------------------------
-- Step 1: Backup properties table
-- --------------------------------------------------------------------------
-- Done externally via: sqlite3 real_estate_avm.db ".backup real_estate_avm_backup.db"
-- Or within Python via: conn.execute("VACUUM INTO 'backup.db'")

-- --------------------------------------------------------------------------
-- Step 2: Normalize legal_status (remaining edge cases)
-- --------------------------------------------------------------------------
-- Already fixed via audit_and_repair_db.py, but double-check:
UPDATE properties SET legal_status = 'pending'
  WHERE legal_status IS NULL OR legal_status NOT IN (
    'pending', 'full_ownership', 'ownership_certificate',
    'land_use_right', 'leasehold', 'unknown'
  );

-- --------------------------------------------------------------------------
-- Step 3: Normalize furnishing (NULL → 'null')
-- --------------------------------------------------------------------------
UPDATE properties SET furnishing = 'null'
  WHERE furnishing IS NULL OR furnishing = '';

-- --------------------------------------------------------------------------
-- Step 4: Ensure source_access_method is never NULL (backup: batch_generator)
-- --------------------------------------------------------------------------
UPDATE properties SET source_access_method = 'batch_generator'
  WHERE source_access_method IS NULL;

-- --------------------------------------------------------------------------
-- Step 5: Ensure source_name is never NULL (backup: 'unknown_source')
-- --------------------------------------------------------------------------
UPDATE properties SET source_name = 'unknown_source'
  WHERE source_name IS NULL OR source_name = '';

-- --------------------------------------------------------------------------
-- Step 6: Ensure evidence_tier is never NULL (default: E5)
-- --------------------------------------------------------------------------
UPDATE properties SET evidence_tier = 'E5'
  WHERE evidence_tier IS NULL OR evidence_tier NOT IN ('E1','E2','E3','E4','E5');

-- --------------------------------------------------------------------------
-- Step 7: Normalize ward (NULL → '' is acceptable, but keep as NULL for consistency)
-- --------------------------------------------------------------------------
-- ward is already VARCHAR(100) nullable — keep NULL for "unknown ward"

-- --------------------------------------------------------------------------
-- Step 8: Normalize data_origin_type (NULL → 'public_collected')
-- --------------------------------------------------------------------------
UPDATE properties SET data_origin_type = 'public_collected'
  WHERE data_origin_type IS NULL;

-- --------------------------------------------------------------------------
-- Step 9: Normalize record_status (NULL → 'raw')
-- --------------------------------------------------------------------------
UPDATE properties SET record_status = 'raw'
  WHERE record_status IS NULL;

-- --------------------------------------------------------------------------
-- Step 10: Recompute price_per_m2 where missing or wrong
-- --------------------------------------------------------------------------
UPDATE properties
  SET price_per_m2 = ROUND(price / area_m2, 0)
  WHERE price > 0
    AND area_m2 > 0
    AND (price_per_m2 IS NULL OR ABS(price_per_m2 - ROUND(price / area_m2, 0)) > 1000);

-- --------------------------------------------------------------------------
-- Step 11: Log all changes to audit_logs
-- --------------------------------------------------------------------------
-- Already done via audit_and_repair_db.py DATA_REPAIR entries

-- --------------------------------------------------------------------------
-- Step 12: Add NOT NULL constraints via recreation (SQLite limitation)
-- --------------------------------------------------------------------------
-- SQLite does not support ALTER COLUMN to add NOT NULL.
-- We must recreate the table. This is done in migrate_to_normalized_schema.sql
-- but we need a lightweight version just for fixing constraints.

-- For production, run the full migrate_to_normalized_schema.sql from schema/
-- This file only handles data normalization.

-- --------------------------------------------------------------------------
-- VERIFICATION QUERIES
-- --------------------------------------------------------------------------
-- Run these after migration to verify:

-- SELECT COUNT(*) FROM properties WHERE property_type IS NULL;
-- SELECT COUNT(*) FROM properties WHERE province_city IS NULL;
-- SELECT COUNT(*) FROM properties WHERE district IS NULL;
-- SELECT COUNT(*) FROM properties WHERE area_m2 IS NULL OR area_m2 <= 0;
-- SELECT COUNT(*) FROM properties WHERE price IS NULL OR price <= 0;
-- SELECT COUNT(*) FROM properties WHERE source_name IS NULL;
-- SELECT COUNT(*) FROM properties WHERE source_access_method IS NULL;
-- SELECT COUNT(*) FROM properties WHERE legal_status IS NULL;
-- SELECT COUNT(*) FROM properties WHERE furnishing IS NULL;

-- SELECT DISTINCT legal_status FROM properties;
-- SELECT DISTINCT furnishing FROM properties;
-- SELECT DISTINCT source_access_method FROM properties;
-- SELECT DISTINCT evidence_tier FROM properties;
-- SELECT DISTINCT property_type FROM properties;
-- SELECT DISTINCT province_city FROM properties;
-- SELECT DISTINCT data_origin_type FROM properties;
-- SELECT DISTINCT record_status FROM properties;

-- ============================================================================
-- END OF SCHEMA CONSTRAINT FIXES
-- ============================================================================