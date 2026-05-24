#!/usr/bin/env bash
# Nightly Supabase pg_dump → gzip → AES-256-CBC → OCI Object Storage (zedapply-backups).
# Run on the OCI VM (same host as n8n-docker). Requires: pg_dump, gzip, openssl, oci CLI.
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly LOG_FILE="${BACKUP_LOG_FILE:-/var/log/zedapply-backup.log}"
readonly BUCKET_NAME="${OCI_BACKUP_BUCKET:-zedapply-backups}"
readonly BUCKET_PREFIX="${OCI_BACKUP_PREFIX:-zedapply}"
readonly TMP_DIR="${BACKUP_TMP_DIR:-/tmp/zedapply-backup}"
readonly ENV_FILE="${BACKUP_ENV_FILE:-/etc/zedapply/backup.env}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck source=/dev/null
  set -a
  source "$ENV_FILE"
  set +a
fi

log() {
  local level="$1"
  shift
  printf '%s [%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$level" "$*" | tee -a "$LOG_FILE"
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    log ERROR "Required command not found: $cmd"
    exit 1
  fi
}

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    log ERROR "Missing required environment variable: $name"
    exit 1
  fi
}

# Parse zedapply_YYYY-MM-DD_HH-MM.sql.gz.enc → epoch seconds (UTC).
backup_epoch() {
  local object_name="$1"
  local base="${object_name%.sql.gz.enc}"
  base="${base#${BUCKET_PREFIX}_}"
  local date_part="${base%%_*}"
  local time_part="${base#*_}"
  time_part="${time_part//-/:}"
  date -u -d "${date_part} ${time_part}:00" +%s 2>/dev/null || echo 0
}

is_monthly_backup() {
  local object_name="$1"
  [[ "$object_name" =~ _[0-9]{4}-[0-9]{2}-01_ ]]
}

apply_retention() {
  log INFO "Applying retention (30 daily + 12 monthly) on bucket ${BUCKET_NAME}"

  mapfile -t objects < <(
    oci os object list \
      --bucket-name "$BUCKET_NAME" \
      --prefix "${BUCKET_PREFIX}_" \
      --all \
      --output json 2>/dev/null | jq -r '.data[]?.name // empty' 2>/dev/null || true
  )

  if [[ ${#objects[@]} -eq 0 ]]; then
    log INFO "No existing backup objects; retention skipped"
    return 0
  fi

  local -a monthly=() daily=()
  local name epoch
  for name in "${objects[@]}"; do
    [[ "$name" == "${BUCKET_PREFIX}_"*".sql.gz.enc" ]] || continue
    epoch="$(backup_epoch "$name")"
    if is_monthly_backup "$name"; then
      monthly+=("${epoch}:${name}")
    else
      daily+=("${epoch}:${name}")
    fi
  done

  local -a keep=()
  if [[ ${#monthly[@]} -gt 0 ]]; then
    IFS=$'\n' sorted=($(printf '%s\n' "${monthly[@]}" | sort -t: -k1,1nr))
    local i=0
    for entry in "${sorted[@]}"; do
      [[ $i -ge 12 ]] && break
      keep+=("${entry#*:}")
      i=$((i + 1))
    done
  fi
  if [[ ${#daily[@]} -gt 0 ]]; then
    IFS=$'\n' sorted=($(printf '%s\n' "${daily[@]}" | sort -t: -k1,1nr))
    local j=0
    for entry in "${sorted[@]}"; do
      [[ $j -ge 30 ]] && break
      keep+=("${entry#*:}")
      j=$((j + 1))
    done
  fi

  local -A keep_set=()
  for name in "${keep[@]}"; do
    keep_set["$name"]=1
  done

  local deleted=0
  for name in "${objects[@]}"; do
    [[ "$name" == "${BUCKET_PREFIX}_"*".sql.gz.enc" ]] || continue
    if [[ -z "${keep_set[$name]:-}" ]]; then
      log INFO "Deleting expired backup: ${name}"
      oci os object delete \
        --bucket-name "$BUCKET_NAME" \
        --object-name "$name" \
        --force \
        >/dev/null
      deleted=$((deleted + 1))
    fi
  done
  log INFO "Retention complete (kept ${#keep[@]}, deleted ${deleted})"
}

main() {
  mkdir -p "$(dirname "$LOG_FILE")" "$TMP_DIR"
  touch "$LOG_FILE" 2>/dev/null || LOG_FILE="${TMP_DIR}/zedapply-backup.log"

  require_cmd pg_dump
  require_cmd gzip
  require_cmd openssl
  require_cmd oci
  require_cmd jq

  require_env SUPABASE_DB_URL
  require_env BACKUP_ENCRYPTION_KEY

  local timestamp
  timestamp="$(date -u '+%Y-%m-%d_%H-%M')"
  local object_name="${BUCKET_PREFIX}_${timestamp}.sql.gz.enc"
  local dump_sql="${TMP_DIR}/${object_name%.enc}"
  local dump_gz="${dump_sql}.gz"
  local dump_enc="${dump_gz}.enc"

  log INFO "Starting backup → ${object_name}"

  trap 'rm -f "${dump_sql}" "${dump_gz}" "${dump_enc}"' EXIT

  pg_dump "$SUPABASE_DB_URL" \
    --no-owner \
    --no-acl \
    --format=plain \
    --file="$dump_sql"

  gzip -9 "$dump_sql"
  openssl enc -aes-256-cbc -salt -pbkdf2 \
    -in "$dump_gz" \
    -out "$dump_enc" \
    -pass "env:BACKUP_ENCRYPTION_KEY"

  oci os object put \
    --bucket-name "$BUCKET_NAME" \
    --name "$object_name" \
    --file "$dump_enc" \
    --force

  log INFO "Uploaded ${object_name} to oci://${BUCKET_NAME}"

  apply_retention

  log INFO "Backup succeeded: ${object_name}"
}

main "$@"
