"""Persistent rolling mail budget and a queue containing no verification codes."""

import hashlib
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from config import BASE_DIR, RESEND_DAILY_LIMIT

LEDGER_PATH = Path(BASE_DIR) / 'instance' / 'mail_operations.db'
WINDOW = 86400


@contextmanager
def database():
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(LEDGER_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS sends (
                id INTEGER PRIMARY KEY, created REAL NOT NULL, kind TEXT NOT NULL,
                domain TEXT NOT NULL, state TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS sends_created ON sends(created);
            CREATE TABLE IF NOT EXISTS pending (
                key TEXT PRIMARY KEY, recipient TEXT NOT NULL, created REAL NOT NULL,
                state TEXT NOT NULL DEFAULT 'pending'
            );
            CREATE TABLE IF NOT EXISTS receipts (key TEXT PRIMARY KEY, created REAL NOT NULL);
        ''')
        with conn:
            yield conn
    finally:
        conn.close()


def reserve(kind, domain):
    with database() as conn:
        conn.execute('BEGIN IMMEDIATE')
        used = conn.execute('SELECT COUNT(*) FROM sends WHERE created > ?', (time.time() - WINDOW,)).fetchone()[0]
        ceiling = max(0, RESEND_DAILY_LIMIT)
        if kind != 'verification':
            ceiling = int(ceiling * .85)
        if used >= ceiling:
            return None
        return conn.execute('INSERT INTO sends(created,kind,domain,state) VALUES (?,?,?,?)',
                            (time.time(), kind, domain, 'sending')).lastrowid


def finish(row_id, ok):
    with database() as conn:
        conn.execute('UPDATE sends SET state=? WHERE id=?', ('accepted' if ok else 'failed', row_id))


def dispatch(to_email, subject, html, config, text, sender, kind):
    # Match enrollment uses UTC calendar weeks; identical next-week mail is new.
    year, week, _ = datetime.fromtimestamp(time.time(), timezone.utc).isocalendar()
    key = hashlib.sha256((f'{year}-W{week}\n{kind}\n' + to_email + '\n' + subject + '\n' + html).encode()).hexdigest()
    try:
        if kind != 'verification':
            with database() as conn:
                conn.execute('DELETE FROM receipts WHERE created < ?', (time.time() - 7 * WINDOW,))
                if conn.execute('SELECT 1 FROM receipts WHERE key=?', (key,)).fetchone():
                    return True, 'sent'
        if kind == 'match':
            with database() as conn:
                existing = conn.execute('SELECT state FROM pending WHERE key=?', (key,)).fetchone()
                if existing:
                    if existing[0] == 'sent':
                        return True, 'sent'
                    if existing[0] in ('pending', 'processing'):
                        return False, 'mail_queued'
                    return False, 'mail_queue_' + existing[0]
        row_id = reserve(kind, to_email.rsplit('@', 1)[-1])
        if row_id is None:
            if kind == 'match':
                with database() as conn:
                    conn.execute('INSERT OR IGNORE INTO pending(key,recipient,created) VALUES (?,?,?)',
                                 (key, to_email, time.time()))
                return False, 'mail_queued'
            return False, 'mail_quota_exhausted'
        try:
            ok, info = sender(to_email, subject, html, config, text)
        except Exception:
            ok, info = False, 'mail_transport_error'
        finish(row_id, ok)
        if ok and kind != 'verification':
            with database() as conn:
                conn.execute('INSERT OR REPLACE INTO receipts(key,created) VALUES (?,?)', (key, time.time()))
        return ok, info
    except (sqlite3.Error, OSError):
        return False, 'mail_ledger_unavailable'


def drain(config, sender, limit=10):
    if not config.get('enabled') or config.get('provider') != 'resend':
        return
    from models import User
    from html import escape
    for _ in range(limit):
        with database() as conn:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute("UPDATE pending SET state='expired',recipient='' WHERE state='pending' AND created < ?",
                         (time.time() - 7 * WINDOW,))
            row = conn.execute("SELECT * FROM pending WHERE state='pending' ORDER BY created LIMIT 1").fetchone()
            if row is None:
                return
            conn.execute("UPDATE pending SET state='processing' WHERE key=?", (row['key'],))
        user = User.query.filter_by(email=row['recipient'], email_verified=True).first()
        if user is None:
            with database() as conn:
                conn.execute("UPDATE pending SET state='canceled',recipient='' WHERE key=?", (row['key'],))
            continue
        row_id = reserve('match', row['recipient'].rsplit('@', 1)[-1])
        if row_id is None:
            with database() as conn:
                conn.execute("UPDATE pending SET state='pending' WHERE key=?", (row['key'],))
            return
        body = 'CampusMatch：你有一条延后发送的匹配通知，请登录查看当前结果：' + config.get('public_url', '').rstrip('/') + '/matches'
        try:
            ok, _ = sender(row['recipient'], 'CampusMatch - 匹配结果提醒', '<p>' + escape(body) + '</p>', config, body)
        except Exception:
            ok = False
        finish(row_id, ok)
        with database() as conn:
            conn.execute("UPDATE pending SET state=?,recipient='' WHERE key=?", ('sent' if ok else 'failed', row['key']))


def summary():
    now = time.time()
    with database() as conn:
        rows = conn.execute('SELECT * FROM sends WHERE created > ? ORDER BY created DESC', (now - WINDOW,)).fetchall()
        pending = conn.execute("SELECT COUNT(*) FROM pending WHERE state='pending'").fetchone()[0]
        stalled = conn.execute("SELECT COUNT(*) FROM pending WHERE state='failed' OR (state='processing' AND created < ?)", (now - 300,)).fetchone()[0]
    used = len(rows)
    failed = sum(row['state'] == 'failed' or (row['state'] == 'sending' and row['created'] < now - 300) for row in rows)
    return dict(used=used, remaining=max(0, RESEND_DAILY_LIMIT-used), limit=RESEND_DAILY_LIMIT,
                pending=pending, failed=failed, stalled=stalled,
                warning=used >= int(RESEND_DAILY_LIMIT * .7),
                protected=used >= int(RESEND_DAILY_LIMIT * .85), recent=[dict(row) for row in rows[:12]])
