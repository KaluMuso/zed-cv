import os
import sys
import asyncio
from datetime import datetime, timezone
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv("apps/backend/.env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set in apps/backend/.env")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_duplicates():
    # Execute raw SQL using an RPC if possible, but since we can't easily,
    # we'll fetch jobs and group them locally.
    print("Fetching all jobs...")
    
    # Supabase limits responses, so we need to paginate or just use a query for dedupe_keys with count > 1
    # It's easier to do this in SQL. Let's use the execute_sql MCP instead, or we can just fetch all dedupe keys.
    # To avoid writing complex pagination, we'll assume there are at most 10,000 jobs.
    all_jobs = []
    offset = 0
    while True:
        res = supabase.table("jobs").select("id, dedupe_key, is_active, created_at").range(offset, offset + 999).execute()
        if not res.data:
            break
        all_jobs.extend(res.data)
        offset += len(res.data)
        print(f"Fetched {offset} jobs...")
        if len(res.data) < 1000:
            break
            
    print(f"Total jobs fetched: {len(all_jobs)}")
    
    groups = {}
    for job in all_jobs:
        dk = job.get("dedupe_key")
        if not dk:
            continue
        if dk not in groups:
            groups[dk] = []
        groups[dk].append(job)
        
    return {k: v for k, v in groups.items() if len(v) > 1}

def cleanup():
    duplicates = get_duplicates()
    print(f"Found {len(duplicates)} dedupe_keys with duplicates.")
    
    total_deleted = 0
    
    for dk, jobs in duplicates.items():
        # Sort jobs: active ones first, then by created_at desc
        jobs.sort(key=lambda x: (x["is_active"], x["created_at"]), reverse=True)
        
        # The first one is the one we keep
        to_keep = jobs[0]
        to_delete = jobs[1:]
        
        print(f"\nKey: {dk}")
        print(f"  Keeping: {to_keep['id']} (Active: {to_keep['is_active']}, Created: {to_keep['created_at']})")
        
        for d in to_delete:
            print(f"  Deleting: {d['id']} (Active: {d['is_active']}, Created: {d['created_at']})")
            # Delete from job_fingerprints first (cascade might not be configured)
            supabase.table("job_fingerprints").delete().eq("job_id", d['id']).execute()
            supabase.table("job_skills").delete().eq("job_id", d['id']).execute()
            res = supabase.table("jobs").delete().eq("id", d['id']).execute()
            if res.data:
                total_deleted += 1
                
    print(f"\nCleanup complete. Deleted {total_deleted} duplicate jobs.")

if __name__ == "__main__":
    cleanup()
