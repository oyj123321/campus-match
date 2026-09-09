# Resend-first mail

Enable this only after both providers have been verified. Keep the existing
`RESEND_API_KEY` and Aliyun SMTP password in the server `.env`, never in Git.
Set these values in that file (replace the Resend sender with your existing one):

```dotenv
MAIL_ENABLED=true
MAIL_PROVIDER=hybrid
RESEND_FROM=CampusMatch <hello@campusmatch.com.cn>
RESEND_DAILY_LIMIT=100
ALIYUN_FROM=CampusMatch <no-reply@notify.campusmatch.com.cn>
ALIYUN_DAILY_LIMIT=2000
MAIL_SERVER=smtpdm.aliyun.com
MAIL_PORT=465
MAIL_USERNAME=no-reply@notify.campusmatch.com.cn
```

Retain `MAIL_PASSWORD` (Aliyun SMTP password) and `RESEND_API_KEY`. Restart the
application after updating configuration. Do not run configure-aliyun-mail.sh
afterward: that script selects Aliyun-only mode. Roll back by setting
`MAIL_PROVIDER=aliyun` and restarting.

All transactional mail and the delayed queue use the same routing. The local
budget counts attempts, including failures, over a rolling 24 hours, not a
midnight reset. At the Resend limit, new mail goes to Aliyun. As older Resend
attempts age out, new mail uses Resend again. Existing total-budget protection
still reserves the last 15% for verification codes.

Provider rejection, monthly quotas, other applications sharing the API key,
and mail sent manually are not reconciled automatically. No transport error
triggers an immediate second send, because acceptance can be uncertain. Keep
the key dedicated to this installation and check both provider dashboards.
Aliyun's configured limit is a safety cap, not a free allowance.

The admin dashboard shows each provider's local attempts. Legacy records
without a provider count conservatively against both budgets for up to 24
hours, so the first switch can happen earlier. Preserve instance/mail_operations.db
across restarts and deployments. Use a single shared ledger for all workers.
