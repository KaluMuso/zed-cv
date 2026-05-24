#!/usr/bin/env bash
# Weekly smoke: download latest backup, restore to staging Supabase, run a query, tear down.
# Skips quietly when STAGING_SUPABASE_DB_URL is unset (see docs/disaster_recovery.md).
set -euo pipefail

readonly LOG_FILE="${BACKUP_LOG_FILE:-/var/log/zedapply-backup.log}"
readonly BUCKET_NAME="${OCI_BACKUP_BUCKET:-zedapply-backups}"
readonly BUCKET_PREFIX="${OCI_BACKUP_PREFIX:-zedapply}"
readonly ENV_FILE="${BACKUP_ENV_FILE:-/etc/zedapply/backup.env}"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck source=/dev/null
  set -a
  source "$ENV_FILE"
  set +a
fi

log() {
  printf '%s [test-restore] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" | tee -a "$LOG_FILE"
}

alert_kaluba() {
  local message="$1"
  local phone="${ADMIN_ALERT_PHONE:-+260761359005}"
  local waha_url="${WAHA_API_URL:-http://127.0.0.1:3000}"
  local waha_key="${WAHA_API_KEY:-}"

  if [[ -z "$waha_key" ]]; then
    log "WARN: WAHA_API_KEY unset — cannot send failure alert"
    return 0
  fi

  local chat_id="${phone//+/}@c.us"
  if command -v curl >/dev/null 2>&1; then
    curl -sf -X POST "${waha_url}/api/sendText" \
      -H "X-Api-Key: ${waha_key}" \
      -H "Content-Type: application/json" \
      -d "{\"chatId\":\"${chat_id}\",\"text\":\"${message}\",\"session\":\"default\"}" \
      >/dev/null || log "WARN: WAHA alert curl failed"
  fi
}

latest_backup_object() {
  oci os object list \
    --bucket-name "$BUCKET_NAME" \
    --prefix "${BUCKET_PREFIX}_" \
    --all \
    --output json 2>/dev/null \
    | jq -r '[.data[]? | select(.name != null)] | sort_by(.["time-created"]) | reverse | .[0].name // empty' 2>/dev/null
}

main() {
  if [[ -z "${STAGING_SUPABASE_DB_URL:-}" ]]; then
    log "SKIP: STAGING_SUPABASE_DB_URL not set — weekly test-restore disabled (TODO in docs)"
    exit 0
  fi

  local latest
  latest="$(latest_backup_object)"
  if [[ -z "$latest" || "$latest" == "null" ]]; then
    log "ERROR: No backup objects found in ${BUCKET_NAME}"
    alert_kaluba "ZedApply backup test-restore FAILED: no objects in ${BUCKET_NAME}."
    exit 1
  fi

  log "Testing restore of ${latest} → staging project"

  if ! printf 'YES\n' | "${SCRIPT_DIR}/restore_database.sh" "$latest" "$STAGING_SUPABASE_DB_URL"; then
    log "ERROR: restore_database.sh failed"
    alert_kaluba "ZedApply backup test-restore FAILED for ${latest}. Check ${LOG_FILE} on OCI."
    exit 1
  fi

  if ! psql "$STAGING_SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -c \
    "SELECT COUNT(*) AS user_count FROM public.users;"; then
    log "ERROR: post-restore smoke query failed"
    alert_kaluba "ZedApply backup test-restore FAILED: smoke query on staging after ${latest}."
    exit 1
  fi

  log "Test-restore succeeded (smoke query OK). Staging DB was overwritten — re-run only on disposable staging."
}

main "$@"
