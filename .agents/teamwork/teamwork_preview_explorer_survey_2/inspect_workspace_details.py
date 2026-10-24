import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

for job_id in ["20261018-223750-3aecfbcd", "20261017-164519-fd65f7e1", "20261017-003022-ecb75736", "20261015-014818-f0fdc122"]:
    ws = Path(r"B:\ALL_TOOLS\CofiDocumentary\workspaces") / job_id
    print(f"\n==================== JOB {job_id} WORKSPACE ====================")
    cb_path = ws / "creative_brief.json"
    if cb_path.exists():
        cb = json.loads(cb_path.read_text(encoding="utf-8"))
        print(f"creative_brief.json keys: {list(cb.keys())}")
        print(f"  narrative_angle: {cb.get('narrative_angle')}")
        print(f"  writing_style: {cb.get('writing_style')}")
        print(f"  hook_archetype: {cb.get('hook_archetype')}")
        print(f"  editing_archetypes: {cb.get('editing_archetypes')}")
        print(f"  custom_rules: {cb.get('custom_rules')}")
    else:
        print("creative_brief.json NOT found")
        
    ec_path = ws / "edit_checkpoint.json"
    if ec_path.exists():
        ec = json.loads(ec_path.read_text(encoding="utf-8"))
        print(f"edit_checkpoint.json keys: {list(ec.keys())}")
        if "edit_recipe" in ec:
            print(f"  edit_recipe: {json.dumps(ec['edit_recipe'], ensure_ascii=False)[:300]}")
        if "dna" in ec or "style" in ec or "recipe" in ec:
            print(f"  dna/style/recipe: {list(ec.keys())}")
    else:
        print("edit_checkpoint.json NOT found")
