#!/usr/bin/env bash
# Restore an encrypted OCI backup into a target Postgres (Supabase direct URI or local).
# Usage: ./scripts/restore_database.sh <object_name> <target_db_url>
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly BUCKET_NAME="${OCI_BACKUP_BUCKET:-zedapply-backups}"
readonly TMP_DIR="${BACKUP_TMP_DIR:-/tmp/zedapply-restore}"
readonly ENV_FILE="${BACKUP_ENV_FILE:-/etc/zedapply/backup.env}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck source=/dev/null
  set -a
  source "$ENV_FILE"
  set +a
fi

usage() {
  cat <<'EOF'
Usage: restore_database.sh <backup_object_name> <target_db_url>

  backup_object_name  e.g. zedapply_2026-05-25_02-30.sql.gz.enc (in OCI bucket)
  target_db_url       postgres://... or postgresql://... connection string

Environment (via BACKUP_ENV_FILE or shell):
  SUPABASE_DB_URL          optional; used only for display in warnings
  BACKUP_ENCRYPTION_KEY    required — same key used at backup time
  OCI_BACKUP_BUCKET        default: zedapply-backups

Example (local throwaway DB):
  ./scripts/restore_database.sh zedapply_2026-05-25_02-30.sql.gz.enc postgres://localhost:5432/test_restore
EOF
}

log() {
  printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { log "ERROR: missing command: $1"; exit 1; }
}

main() {
  if [[ $# -lt 2 ]]; then
    usage
    exit 1
  fi

  local object_name="$1"
  local target_url="$2"

  require_cmd oci
  require_cmd openssl
  require_cmd gunzip
  require_cmd psql

  if [[ -z "${BACKUP_ENCRYPTION_KEY:-}" ]]; then
    log "ERROR: BACKUP_ENCRYPTION_KEY is not set"
    exit 1
  fi

  mkdir -p "$TMP_DIR"
  local enc="${TMP_DIR}/${object_name}"
  local gz="${enc%.enc}"
  local sql="${gz%.gz}"

  cat <<EOF

╔══════════════════════════════════════════════════════════════════╗
║  DESTRUCTIVE DATABASE RESTORE                                    ║
║                                                                  ║
║  Backup object : ${object_name}
║  Target URL    : ${target_url}
║                                                                  ║
║  This will DROP and recreate objects in the target database.     ║
║  All existing data in the target will be overwritten.            ║
╚══════════════════════════════════════════════════════════════════╝

EOF

  read -r -p "Type YES to continue: " confirm
  if [[ "$confirm" != "YES" ]]; then
    log "Aborted (confirmation was not YES)."
    exit 1
  fi

  log "Downloading ${object_name} from ${BUCKET_NAME}..."
  oci os object get \
    --bucket-name "$BUCKET_NAME" \
    --name "$object_name" \
    --file "$enc"

  log "Decrypting..."
  openssl enc -d -aes-256-cbc -pbkdf2 \
    -in "$enc" \
    -out "$gz" \
    -pass "env:BACKUP_ENCRYPTION_KEY"

  log "Decompressing..."
  gunzip -f "$gz"

  log "Restoring into target (this may take several minutes)..."
  psql "$target_url" -v ON_ERROR_STOP=1 -f "$sql"

  rm -f "$enc" "$sql"
  log "Restore completed successfully."
}

main "$@"
