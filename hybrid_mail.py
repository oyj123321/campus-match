"""Resend-first routing with conservative, atomic rolling provider budgets."""

import time

import config as settings
from mail_operations import database, WINDOW


def reserve_provider():
    now = time.time()
    with database() as conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('''CREATE TABLE IF NOT EXISTS provider_sends (
            id INTEGER PRIMARY KEY, provider TEXT NOT NULL, created REAL NOT NULL,
            state TEXT NOT NULL DEFAULT 'sending')''')
        conn.execute('CREATE INDEX IF NOT EXISTS provider_created ON provider_sends(provider,created)')
        conn.execute('CREATE TABLE IF NOT EXISTS provider_meta (key TEXT PRIMARY KEY, value REAL NOT NULL)')
        conn.execute("INSERT OR IGNORE INTO provider_meta VALUES ('started', ?)", (now,))
        cutoff = conn.execute("SELECT value FROM provider_meta WHERE key='started'").fetchone()[0]
        # Old attempts lack a provider. Count against both until they age out;
        # omit the first current reservation, already counted by this router.
        legacy = conn.execute('''SELECT COUNT(*) FROM sends WHERE created > ? AND created < ?
            AND id != (SELECT MAX(id) FROM sends WHERE created < ?)''',
            (now - WINDOW, cutoff, cutoff)).fetchone()[0]
        for provider, ceiling in [('resend', settings.RESEND_DAILY_LIMIT),
                                  ('aliyun', settings.ALIYUN_DAILY_LIMIT)]:
            used = conn.execute('SELECT COUNT(*) FROM provider_sends WHERE provider=? AND created>?',
                                (provider, now - WINDOW)).fetchone()[0]
            if used + legacy < max(0, ceiling):
                row = conn.execute('INSERT INTO provider_sends(provider,created) VALUES (?,?)',
                                   (provider, now)).lastrowid
                return provider, row
    return None, None


def send(to_email, subject, html, config, text=None):
    from email_service import _send_resend, _send_smtp
    if not (config.get('resend_api_key') and settings.RESEND_FROM
            and config.get('username') and config.get('password') and settings.ALIYUN_FROM):
        return False, 'mail_hybrid_config_incomplete'
    provider, row = reserve_provider()
    if provider is None:
        return False, 'mail_quota_exhausted'
    transport = dict(config, provider=provider,
                     mail_from=settings.RESEND_FROM if provider == 'resend' else settings.ALIYUN_FROM)
    try:
        sender = _send_resend if provider == 'resend' else _send_smtp
        ok, info = sender(to_email, subject, html, transport, text)
    except Exception:
        ok, info = False, 'mail_transport_error'
    # Never resend after a transport error: acceptance may be ambiguous.
    with database() as conn:
        conn.execute('UPDATE provider_sends SET state=? WHERE id=?',
                     ('accepted' if ok else 'failed', row))
    return ok, info


def usage():
    with database() as conn:
        exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='provider_sends'").fetchone()
        rows = conn.execute('SELECT provider,COUNT(*) AS used FROM provider_sends WHERE created>? GROUP BY provider',
                            (time.time() - WINDOW,)).fetchall() if exists else []
    counts = {row['provider']: row['used'] for row in rows}
    return [dict(provider=name, used=counts.get(name.lower(), 0), limit=limit)
            for name, limit in [('Resend', settings.RESEND_DAILY_LIMIT), ('Aliyun', settings.ALIYUN_DAILY_LIMIT)]]
