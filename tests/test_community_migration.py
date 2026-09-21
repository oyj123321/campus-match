import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask
from models import db
from scripts import migrate_community


class CommunityMigrationTests(unittest.TestCase):
    def test_backup_and_repeat_migration_preserve_users(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"existing.db"
            with closing(sqlite3.connect(path)) as con:
                con.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT)")
                con.execute("INSERT INTO users VALUES (7, 'existing user')")
                con.commit()
            app=Flask(__name__)
            app.config["SQLALCHEMY_DATABASE_URI"]="sqlite:///"+path.as_posix()
            db.init_app(app)
            with patch.object(migrate_community,"app",app), patch("builtins.print"):
                migrate_community.migrate()
                migrate_community.migrate()
            with closing(sqlite3.connect(path)) as con:
                self.assertEqual(con.execute("SELECT * FROM users").fetchall(),[(7,"existing user")])
                self.assertEqual(con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name LIKE 'community_%'").fetchone()[0],6)
            backups=list(Path(folder).glob("*.community-backup-*"))
            self.assertEqual(len(backups),2)
            with closing(sqlite3.connect(backups[0])) as con:
                self.assertEqual(con.execute("SELECT * FROM users").fetchall(),[(7,"existing user")])
            with app.app_context():
                db.engine.dispose()

    def test_missing_database_is_not_created(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"missing.db"
            app=Flask(__name__)
            app.config["SQLALCHEMY_DATABASE_URI"]="sqlite:///"+path.as_posix()
            db.init_app(app)
            with patch.object(migrate_community,"app",app):
                with self.assertRaises(SystemExit):
                    migrate_community.migrate()
            self.assertFalse(path.exists())
