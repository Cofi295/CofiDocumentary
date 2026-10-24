import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

jobs_dir = Path(r"B:\ALL_TOOLS\CofiDocumentary\data\jobs")
job_ids = ["20261018-223750-3aecfbcd", "20261017-164519-fd65f7e1", "20261017-003022-ecb75736", "20261015-014818-f0fdc122"]

print("=== JOBS DEEP ANALYSIS ===")
for jid in job_ids:
    jpath = jobs_dir / jid / "job.json"
    if not jpath.exists():
        print(f"Missing {jpath}")
        continue
    job = json.loads(jpath.read_text(encoding="utf-8"))
    print(f"\n--- JOB {jid} ---")
    print(f"Title: {job.get('title')}")
    print(f"Status: {job.get('status')}")
    print(f"Market: {job.get('market')}, Language: {job.get('language')}")
    print(f"visual_strategy: {job.get('visual_strategy')}")
    print(f"ai_media_mode: {job.get('ai_media_mode')}")
    print(f"channel_profile_id: {job.get('channel_profile_id')}")
    print(f"playbook_id: {job.get('playbook_id')}")
    print(f"Has creative_brief: {bool(job.get('creative_brief'))}")
    if job.get('creative_brief'):
        print("  job.json creative_brief:", json.dumps(job['creative_brief'], ensure_ascii=False, indent=2))
    print(f"Has channel_profile_snapshot: {bool(job.get('channel_profile_snapshot'))}")
    if job.get('channel_profile_snapshot'):
        print("  channel_profile_snapshot:", json.dumps(job['channel_profile_snapshot'], ensure_ascii=False, indent=2))
    print(f"Has production_recipe: {bool(job.get('production_recipe'))}")
    if job.get('production_recipe'):
        print("  target_duration_sec:", job['production_recipe'].get('target_duration_sec'))
        print("  target_scene_count:", job['production_recipe'].get('target_scene_count'))
    print(f"Has editing_dna: {job.get('editing_dna')}")
