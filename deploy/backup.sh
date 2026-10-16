#!/bin/sh
set -eu
cd "$(dirname "$0")"
backup_dir="${BACKUP_DIR:?Set an absolute backup destination}"
mkdir -p "$backup_dir"
umask 077
backup_file="$backup_dir/promt-market-$(date -u +%Y%m%dT%H%M%SZ).dump"
docker compose exec -T db pg_dump -U promt -d promt_market -Fc > "$backup_file.tmp"
test -s "$backup_file.tmp"
mv "$backup_file.tmp" "$backup_file"
printf '%s\n' "Backup completed"
