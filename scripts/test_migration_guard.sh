#!/usr/bin/env bash
# scripts/test_migration_guard.sh
# Tests the migration prefix collision logic under different scenarios.

set -euo pipefail

# 1. Setup a temporary directory for testing
TEST_DIR=$(mktemp -d -t migration-guard-test.XXXXXX)
echo "Setting up temp test directory at $TEST_DIR"

cleanup() {
  echo "Cleaning up $TEST_DIR"
  rm -rf "$TEST_DIR"
}
trap cleanup EXIT

cd "$TEST_DIR"

# 2. Initialize a dummy git repository
git init -b master
git config user.name "Test User"
git config user.email "test@example.com"

# Create migrations directory structure
mkdir -p infra/supabase/migrations

# Commit some initial migrations (including legacy duplicates 063/074)
touch infra/supabase/migrations/001_init.sql
touch infra/supabase/migrations/063_trusted.sql
touch infra/supabase/migrations/063_seed.sql
touch infra/supabase/migrations/074_billing.sql
touch infra/supabase/migrations/074_cv.sql
touch infra/supabase/migrations/107_dedupe.sql

git add .
git commit -m "initial commit"

# Define the migration guard logic as a function to test it easily
run_migration_guard() {
  local touched_files
  local touched_prefixes
  local collision_found=0
  
  # Diff against master branch
  touched_files=$(git diff --name-only master...HEAD -- 'infra/supabase/migrations/*.sql' || true)
  
  if [ -z "$touched_files" ]; then
    echo "No migrations touched. PASS."
    return 0
  fi
  
  touched_prefixes=""
  for f in $touched_files; do
    if [ -f "$f" ]; then
      prefix=$(basename "$f" | sed 's|^\([0-9]*\)_.*|\1|')
      touched_prefixes="$touched_prefixes $prefix"
    fi
  done
  
  touched_prefixes=$(echo "$touched_prefixes" | tr ' ' '\n' | grep -v '^$' | sort -u)
  
  for prefix in $touched_prefixes; do
    match_count=$(ls infra/supabase/migrations/${prefix}_*.sql 2>/dev/null | wc -l)
    if [ "$match_count" -gt 1 ]; then
      echo "Collision found for prefix $prefix! FAIL."
      collision_found=1
    fi
  done
  
  if [ "$collision_found" -ne 0 ]; then
    return 1
  fi
  echo "All checks passed. PASS."
  return 0
}

# Scenario A: Branch with no new migrations (should PASS)
echo "--- Scenario A: No migrations touched ---"
git checkout -b test/no-migrations
if run_migration_guard; then
  echo "Scenario A passed as expected."
else
  echo "Scenario A failed unexpectedly."
  exit 1
fi

# Scenario B: Branch with new non-colliding migration (should PASS)
echo "--- Scenario B: Non-colliding migration added ---"
git checkout master
git checkout -b test/non-colliding
touch infra/supabase/migrations/108_new_feature.sql
git add .
git commit -m "add non-colliding migration"
if run_migration_guard; then
  echo "Scenario B passed as expected."
else
  echo "Scenario B failed unexpectedly."
  exit 1
fi

# Scenario C: Branch with colliding migrations (should FAIL)
echo "--- Scenario C: Colliding migrations added ---"
git checkout master
git checkout -b test/colliding
touch infra/supabase/migrations/099_foo.sql
touch infra/supabase/migrations/099_bar.sql
git add .
git commit -m "add colliding migrations"
if ! run_migration_guard; then
  echo "Scenario C failed (caught collision) as expected."
else
  echo "Scenario C did not catch collision! FAIL."
  exit 1
fi

echo "All tests passed successfully!"
