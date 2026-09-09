#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="$project_dir/.env"

if [[ ! -f "$env_file" ]]; then
    echo "Missing $env_file" >&2
    exit 1
fi

read -r -s -p "Aliyun SMTP password: " smtp_password
echo
if [[ -z "$smtp_password" || "$smtp_password" == *$'\n'* || "$smtp_password" == *$'\r'* ]]; then
    echo "Password is empty or contains a newline." >&2
    exit 1
fi

backup="$env_file.backup.$(date +%Y%m%d-%H%M%S)"
cp -p "$env_file" "$backup"
temp_file="$(mktemp "$project_dir/.env.aliyun.XXXXXX")"
trap 'rm -f "$temp_file"; unset smtp_password' EXIT

grep -vE '^(MAIL_ENABLED|MAIL_PROVIDER|MAIL_SERVER|MAIL_PORT|MAIL_USERNAME|MAIL_PASSWORD|MAIL_FROM|MAIL_DAILY_LIMIT)=' "$env_file" > "$temp_file" || true
cat >> "$temp_file" <<'EOF'
MAIL_ENABLED=true
MAIL_PROVIDER=aliyun
MAIL_SERVER=smtpdm.aliyun.com
MAIL_PORT=465
MAIL_USERNAME=no-reply@notify.campusmatch.com.cn
MAIL_FROM=CampusMatch <no-reply@notify.campusmatch.com.cn>
MAIL_DAILY_LIMIT=2000
EOF
printf 'MAIL_PASSWORD=%s\n' "$smtp_password" >> "$temp_file"
chmod 600 "$temp_file"
mv -f "$temp_file" "$env_file"
unset smtp_password
trap - EXIT

echo "Aliyun mail configuration saved. Backup: $backup"
echo "Run: sudo systemctl restart campus-match"
