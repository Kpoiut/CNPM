#!/usr/bin/env python3
"""
STEP 1: Backup database before destructive operations.
Creates a timestamped backup copy.
"""
import shutil, os, sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "real_estate_avm.db"
BACKUP_DIR = Path(__file__).parent.parent / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

ts = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = BACKUP_DIR / f"real_estate_avm_backup_{ts}.db"

print(f"Backing up database...")
print(f"  Source:  {DB_PATH}")
print(f"  Backup:  {backup_path}")

shutil.copy2(DB_PATH, backup_path)
print(f"  Size:    {os.path.getsize(backup_path) / 1024 / 1024:.1f} MB")

# Verify backup
conn = sqlite3.connect(backup_path)
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM properties")
total = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM provenance_chains")
chains = c.fetchone()[0]
conn.close()

print(f"\nBackup verified:")
print(f"  Properties: {total}")
print(f"  Provenance chains: {chains}")
print(f"\nBackup complete: {backup_path}")
