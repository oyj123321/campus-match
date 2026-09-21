"""Back up the configured SQLite database and create only the community tables.

Run with the service's Python environment from the deployed project.
"""
from datetime import datetime
from contextlib import closing
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import app
from models import (db, CommunityEntry, CommunityReaction, CommunityReport,
                    CommunityBan, CommunityLimit, CommunityAudit)

TABLES = [model.__table__ for model in (CommunityEntry, CommunityReaction, CommunityReport,
                                      CommunityBan, CommunityLimit, CommunityAudit)]


def migrate():
    with app.app_context():
        if db.engine.url.get_backend_name() != "sqlite":
            raise SystemExit("This migration helper requires SQLite. Back up other databases separately.")
        source = Path(db.engine.url.database)
        if not source.is_file():
            raise SystemExit(f"Existing database not found: {source}")
        backup = source.with_name(source.name + ".community-backup-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
        with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as original:
            if not original.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'").fetchone():
                raise SystemExit("No users table found; check DATABASE_URL before continuing.")
            with closing(sqlite3.connect(str(backup))) as saved:
                original.backup(saved)
        with db.engine.begin() as connection:
            db.metadata.create_all(bind=connection, tables=TABLES, checkfirst=True)
        print(f"Backup: {backup}")
        print("Community tables ready. Existing users and matching data unchanged.")


if __name__ == "__main__":
    migrate()
