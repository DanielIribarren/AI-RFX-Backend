"""
One-shot migration runner.
Reads SUPABASE_URL + SUPABASE_ANON_KEY from .env and executes a SQL file
via the Supabase REST /rpc or direct postgrest rpc call.

Usage:
    python run_migration.py migrations/20260320_budy_phase1_foundation.sql
    python run_migration.py migrations/20260320_budy_phase1_storage_and_rls.sql
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sql_file = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if not sql_file or not sql_file.exists():
    print(f"Usage: python run_migration.py <sql_file>")
    sys.exit(1)

sql = sql_file.read_text()

# Use supabase-py to get a connected client and execute via rpc
from supabase import create_client

url = os.environ["SUPABASE_URL"]
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_ANON_KEY"]

print(f"Connecting to {url}")
print(f"Using key role: {'service_role' if 'service_role' in key else 'anon'}")
print(f"Executing: {sql_file.name} ({len(sql)} chars)\n")

client = create_client(url, key)

# Split on semicolons to run statement-by-statement through the REST API
# Actually, use the pg connection directly via supabase postgrest execute
# The cleanest approach: call the execute RPC
try:
    result = client.rpc("exec_sql", {"query": sql}).execute()
    print("✅ Migration complete via exec_sql RPC")
    print(result)
except Exception as e:
    print(f"exec_sql RPC not available, trying statement-by-statement via postgrest...")
    # Fallback: split and run each DDL statement individually is not possible
    # via REST. Print instructions instead.
    print(f"\nDirect execution failed: {e}")
    print("\n" + "="*60)
    print("MANUAL EXECUTION REQUIRED")
    print("="*60)
    print("Go to: https://supabase.com/dashboard/project/mjwnmzdgxcxubanubvms/sql/new")
    print(f"Paste the contents of: {sql_file}")
    print("="*60)
    sys.exit(1)
