import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

profiles_path = Path(r"B:\ALL_TOOLS\CofiDocumentary\data\channel_profiles.json")
if profiles_path.exists():
    raw = json.loads(profiles_path.read_text(encoding="utf-8"))
    profiles = raw.get("profiles", raw) if isinstance(raw, dict) else raw
    print(f"Total channel profiles: {len(profiles)}")
    for p in profiles:
        print("\n============================================================")
        print(f"ID: {p.get('id')}")
        print(f"Label: {p.get('label')}")
        print(f"Market: {p.get('market')}, Language: {p.get('default_language')}")
        print(f"Duration: {p.get('default_duration_minutes')}")
        print(f"Visual Strategy: {p.get('default_visual_strategy')}")
        print(f"AI Media Mode: {p.get('default_ai_media_mode')}")
        print(f"DNA Mode: {p.get('dna_mode')}")
        print(f"Own Channel Ref: {p.get('own_channel_ref')}")
        print(f"Competitor Refs: {p.get('competitor_refs')}")
        print(f"Allowed Topics: {bool(p.get('allowed_topics'))} ({len(str(p.get('allowed_topics') or ''))} chars)")
        print(f"Forbidden Topics: {bool(p.get('forbidden_topics'))} ({len(str(p.get('forbidden_topics') or ''))} chars)")
        print(f"Monetization Policy: {bool(p.get('monetization_safety_policy'))}")
        print(f"Voice & Structure: {bool(p.get('voice_and_structure'))}")
        print(f"Reference Image Policy: {p.get('reference_image_policy')}")
        print(f"Default AI Style Mode: {p.get('default_ai_style_mode')}")
        print(f"Default AI Custom Style: {p.get('default_ai_custom_style')}")
        print(f"Has default_creative_brief: {bool(p.get('default_creative_brief'))}")
        if p.get('default_creative_brief'):
            print(f"  brief: {json.dumps(p['default_creative_brief'], ensure_ascii=False)}")
        print(f"Has editorial_dna: {bool(p.get('editorial_dna'))}")
        if p.get('editorial_dna'):
            print(f"  editorial_dna keys: {list(p['editorial_dna'].keys())}")
        print(f"Has editing_dna: {'editing_dna' in p} -> {bool(p.get('editing_dna'))}")
        if p.get('editing_dna'):
            print(f"  editing_dna: {json.dumps(p['editing_dna'], ensure_ascii=False)}")
        print(f"Has self_learning_memory: {'self_learning_memory' in p} -> {bool(p.get('self_learning_memory'))}")
        if p.get('self_learning_memory'):
            print(f"  self_learning_memory: {json.dumps(p['self_learning_memory'], ensure_ascii=False)}")
