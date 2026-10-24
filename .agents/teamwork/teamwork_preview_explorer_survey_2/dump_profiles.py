import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

profiles_path = Path(r"B:\ALL_TOOLS\CofiDocumentary\data\channel_profiles.json")
raw = json.loads(profiles_path.read_text(encoding="utf-8"))
profiles = raw.get("profiles", raw)

print("=== CHANNEL PROFILES ANALYSIS ===")
for p in profiles:
    pid = p.get("id")
    label = p.get("label")
    print(f"\n--- PROFILE {pid} ({label}) ---")
    keys = list(p.keys())
    print("Top-level keys:", keys)
    for k in ["id", "label", "market", "default_language", "default_duration_minutes", 
              "default_visual_strategy", "default_ai_media_mode", "default_ai_style_mode",
              "default_ai_custom_style", "dna_mode", "voice_and_structure", "allowed_topics",
              "forbidden_topics", "monetization_safety_policy", "reference_image_policy",
              "own_channel_ref", "competitor_refs"]:
        print(f"  {k}: {p.get(k)}")
    if p.get("default_creative_brief"):
        print("  default_creative_brief:", json.dumps(p["default_creative_brief"], ensure_ascii=False, indent=4))
    else:
        print("  default_creative_brief: NONE / MISSING")
    if p.get("editorial_dna"):
        print("  editorial_dna keys:", list(p["editorial_dna"].keys()))
        print("  editorial_dna summary:", {k: (v if not isinstance(v, (dict, list)) else f"<{type(v).__name__} len={len(v)}>") for k, v in p["editorial_dna"].items()})
    else:
        print("  editorial_dna: NONE / MISSING")
    print("  editing_dna:", p.get("editing_dna"))
    print("  self_learning_memory:", p.get("self_learning_memory"))
