import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from pathlib import Path

ROOT = Path("B:/ALL_TOOLS/CofiDocumentary")
profiles_file = ROOT / "data" / "channel_profiles.json"
jobs_dir = ROOT / "data" / "jobs"

data = json.loads(profiles_file.read_text(encoding="utf-8"))
profiles = {p["id"]: p for p in data.get("profiles", [])}
required_profile_ids = [
    "channel-1e24de3ab5",
    "channel-e544a64b7c",
    "channel-aa913eb90d",
    "channel-f6ec4dfff3",
]

print("=" * 60)
print(f"CHANNEL PROFILES VERIFICATION (Total: {len(profiles)})")
print("=" * 60)
for pid in required_profile_ids:
    if pid not in profiles:
        print(f"FAILED: {pid} missing from channel_profiles.json")
    else:
        p = profiles[pid]
        dna = p.get("editing_dna")
        brief = p.get("default_creative_brief")
        strat = p.get("visual_strategy")
        slm = p.get("self_learning_memory")
        print(f"PASS: {pid} -> label: {p.get('label')[:40]}...")
        print(f"      editing_dna: {bool(dna)} (version: {dna.get('version') if isinstance(dna, dict) else None})")
        print(f"      default_creative_brief: {bool(brief)} (strategy: {brief.get('visual_strategy') if isinstance(brief, dict) else None})")
        print(f"      visual_strategy: {strat}")
        print(f"      self_learning_memory: {bool(slm)}")

print("\n" + "=" * 60)
print("JOBS STORAGE VERIFICATION")
print("=" * 60)
required_job_ids = [
    "20261018-223750-3aecfbcd",
    "20261017-164519-fd65f7e1",
]
job_dirs = [d for d in jobs_dir.iterdir() if d.is_dir()]
print(f"Total job directories: {len(job_dirs)}")
for jid in required_job_ids:
    jpath = jobs_dir / jid / "job.json"
    if not jpath.exists():
        print(f"FAILED: Job {jid} not found at {jpath}")
    else:
        jdata = json.loads(jpath.read_text(encoding="utf-8"))
        print(f"PASS: Job {jid} -> title: {jdata.get('title')[:40]}...")
        print(f"      channel_profile_id: {jdata.get('channel_profile_id')}")
        print(f"      visual_strategy: {jdata.get('visual_strategy')}")
        print(f"      has editing_dna: {bool(jdata.get('editing_dna'))}")
        print(f"      has creative_brief: {bool(jdata.get('creative_brief'))}")

print("\n" + "=" * 60)
print("RADAR DATABASE VERIFICATION")
print("=" * 60)
import sqlite3
radar_db_path = Path(r"B:\ALL_TOOLS\CofiRadar\data\cofi-radar.db")
if not radar_db_path.exists():
    print(f"FAILED: Radar DB does not exist at {radar_db_path}")
else:
    conn = sqlite3.connect(radar_db_path)
    cur = conn.cursor()
    cur.execute("SELECT count(name) FROM sqlite_master WHERE type='table'")
    t_count = cur.fetchone()[0]
    print(f"PASS: cofi-radar.db exists, table count: {t_count}")
    for tbl in ["channels", "videos"]:
        try:
            cur.execute(f"SELECT count(*) FROM {tbl}")
            cnt = cur.fetchone()[0]
            print(f"      Table '{tbl}' row count: {cnt}")
        except Exception as e:
            print(f"      Table '{tbl}' check error: {e}")
    conn.close()
