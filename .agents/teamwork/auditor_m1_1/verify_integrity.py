import sqlite3
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

# 1. Check media factory DB accounts (cofi_studio.db)
mf_db = 'data/media_factory/cofi_studio.db'
if not os.path.exists(mf_db):
    mf_db = 'data/media_factory/media_factory.db'
conn = sqlite3.connect(mf_db)
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print(f"Media Factory DB ({mf_db}) tables count: {len(tables)}: {tables}")
assert 'local_resources' in tables

rows = conn.execute("SELECT id, payload FROM local_resources WHERE resource_type = ?", ('google_flow_account',)).fetchall()
print(f"Active Google Flow accounts count in DB: {len(rows)}")
for r in rows:
    p = json.loads(r[1])
    print(f" - ID: {r[0]} | Email: {p.get('email')} | Status: {p.get('status')}")
assert len(rows) == 3, f"Expected 3 active accounts, found {len(rows)}"

# 2. Check secret session files
secrets_dir = 'data/media_factory/secrets/google-flow'
if os.path.exists(secrets_dir):
    enc_files = [f for f in os.listdir(secrets_dir) if f.endswith('.enc')]
    print(f"Secret session files count: {len(enc_files)}")
    assert len(enc_files) >= 3, "Secret session files for active accounts must be preserved"

# 3. Check active job
job_path = 'data/jobs/20261019-185102-31983814/job.json'
assert os.path.exists(job_path), "Active job file missing!"
with open(job_path, 'r', encoding='utf-8') as f:
    job = json.load(f)
print(f"Active job ID: {job.get('id')} | Status: {job.get('status')} | Workspace: {job.get('workspace')}")
assert job.get('id') == '20261019-185102-31983814'

# 4. Check workspace
ws_dir = job.get('workspace')
assert os.path.exists(ws_dir), f"Workspace directory {ws_dir} missing!"
artifacts = os.listdir(ws_dir)
print(f"Workspace artifacts count: {len(artifacts)}")
assert 'input.json' in artifacts, "input.json missing in workspace"
assert os.path.exists(os.path.join(ws_dir, 'media', 'style_reference', 'style_reference.png')), "Reference image missing!"

# 5. Check channel profiles
profiles_file = 'data/channel_profiles.json'
assert os.path.exists(profiles_file), "channel_profiles.json missing!"
with open(profiles_file, 'r', encoding='utf-8') as f:
    data = json.load(f)
profiles = data.get("profiles", [])
print(f"Channel profiles count: {len(profiles)}")
for p in profiles:
    print(f" - Profile: {p.get('id')} | Label: {p.get('label')}")
assert len(profiles) >= 4, "Expected at least 4 channel profiles"

# 6. Check that active profiles on disk exist in google-flow-profiles
profile_root = 'data/media_factory/google-flow-profiles'
existing_profile_dirs = [d for d in os.listdir(profile_root) if os.path.isdir(os.path.join(profile_root, d))]
print(f"Profiles existing in google-flow-profiles: {existing_profile_dirs}")
for r in rows:
    acc_id = r[0]
    assert acc_id in existing_profile_dirs, f"Active account {acc_id} profile folder missing on disk!"

print("\nSUCCESS: ALL INTEGRITY & PRESERVATION CHECKS PASSED EMPIRICALLY!")
