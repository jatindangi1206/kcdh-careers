#!/bin/bash
# Run as root; configure /etc/kcdh-careers-backup.env first.
set -euo pipefail
umask 077
source /etc/kcdh-careers-backup.env
: "${BACKUP_S3_URI:?Set the private S3 bucket/prefix}"
: "${AWS_DEFAULT_REGION:?Set the AWS region}"
export AWS_DEFAULT_REGION
[[ "$BACKUP_S3_URI" == s3://* ]] || exit 1
command -v aws >/dev/null
exec 9>/run/lock/kcdh-careers-maintenance.lock
flock -n 9 || { echo "Maintenance in progress; backup skipped" >&2; exit 1; }
work=$(mktemp -d)
restart=0
cleanup() {
    if (( restart )); then systemctl start kcdh-careers; fi
    rm -rf "$work"
}
trap cleanup EXIT
git -C /srv/kcdh-careers rev-parse HEAD > "$work/release.txt"
# ponytail: brief nightly downtime for consistent files; online snapshots if uptime requires it.
restart=1
systemctl stop kcdh-careers
/srv/kcdh-careers/.venv/bin/python - <<'PY'
import json
from pathlib import Path
data = Path('/var/lib/kcdh-careers')
assert isinstance(json.loads((data / 'internships.json').read_text()), list)
assert isinstance(json.loads((data / 'auth.json').read_text())['users'], dict)
PY
tar -czf "$work/data.tar.gz" -C /var/lib/kcdh-careers internships.json auth.json -C "$work" release.txt
systemctl start kcdh-careers
restart=0
aws s3 cp "$work/data.tar.gz" "${BACKUP_S3_URI%/}/$(date -u +%Y%m%dT%H%M%SZ).tar.gz" --sse AES256 --only-show-errors
echo "Backup uploaded at $(date -u +%FT%TZ)"
