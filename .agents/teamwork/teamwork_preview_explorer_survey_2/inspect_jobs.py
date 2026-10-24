import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

jobs_dir = Path(r"B:\ALL_TOOLS\CofiDocumentary\data\jobs")
job_files = list(jobs_dir.glob("*/job.json"))
print(f"Total jobs found in {jobs_dir}: {len(job_files)}")

for jf in sorted(job_files, key=lambda p: p.parent.name, reverse=True):
    job_id = jf.parent.name
    try:
        data = json.loads(jf.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error reading {jf}: {e}")
        continue
    
    print("\n============================================================")
    print(f"Job ID: {job_id}")
    print(f"Title: {data.get('title')}")
    print(f"Market: {data.get('market')}, Language: {data.get('language')}")
    print(f"Status: {data.get('status')}, Current Phase: {data.get('current_phase')}")
    print(f"Visual Strategy: {data.get('visual_strategy')}")
    print(f"AI Media Mode: {data.get('ai_media_mode')}")
    print(f"Channel Profile ID: {data.get('channel_profile_id')}")
    print(f"Channel Plan Item ID: {data.get('channel_plan_item_id')}")
    print(f"Has Channel Snapshot: {bool(data.get('channel_profile_snapshot'))}")
    if data.get('channel_profile_snapshot'):
        snap = data['channel_profile_snapshot']
        print(f"  Snapshot ID: {snap.get('id')}, Label: {snap.get('label')}")
    print(f"Has Production Recipe: {bool(data.get('production_recipe'))}")
    if data.get('production_recipe'):
        print(f"  Production Recipe keys: {list(data['production_recipe'].keys())}")
    print(f"Has editing_dna: {'editing_dna' in data} -> {bool(data.get('editing_dna'))}")
    if data.get('editing_dna'):
        print(f"  editing_dna: {json.dumps(data['editing_dna'], ensure_ascii=False)}")
    print(f"Workspace: {data.get('workspace')}")
    ws_path = Path(data.get('workspace') or "")
    if ws_path.exists():
        ws_files = [f.name for f in ws_path.iterdir() if f.is_file()]
        print(f"  Workspace files ({len(ws_files)}): {ws_files[:10]}")
    else:
        print(f"  Workspace path does not exist on disk: {ws_path}")
