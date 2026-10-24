from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


def sync_glabs_accounts():
    appdata = Path(r"C:\Users\koing\AppData\Roaming\G-Labs Automation")
    auth_multi_file = appdata / "auth_session_multi.json"
    project_cache_file = appdata / "project_cache.json"
    browser_profiles_dir = appdata / "browser_profiles"

    db_path = Path("data/media_factory/cofi_studio.db")
    if not db_path.is_file():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    if not auth_multi_file.is_file():
        print(f"Error: G-Labs auth file not found at {auth_multi_file}")
        sys.exit(1)

    with open(auth_multi_file, "r", encoding="utf-8") as f:
        glabs_accounts = json.load(f)

    project_cache = {}
    if project_cache_file.is_file():
        with open(project_cache_file, "r", encoding="utf-8") as f:
            project_cache = json.load(f)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Load existing cofi accounts to avoid duplicate emails
    cursor.execute("SELECT id, payload FROM local_resources WHERE resource_type='google_flow_account'")
    existing_rows = cursor.fetchall()
    existing_by_email: dict[str, tuple[str, dict]] = {}
    for row_id, raw_payload in existing_rows:
        try:
            payload = json.loads(raw_payload)
            email = str(payload.get("email") or "").strip().lower()
            if email:
                existing_by_email[email] = (row_id, payload)
        except Exception:
            pass

    now = datetime.now(timezone.utc).isoformat()
    synced_count = 0
    updated_count = 0

    print(f"Found {len(glabs_accounts)} accounts in G-Labs.")

    for item in glabs_accounts:
        email = str(item.get("email") or "").strip()
        if not email:
            continue
        email_lower = email.lower()

        raw_tier = str(item.get("tier") or "FREE").upper()
        if "ULTRA" in raw_tier:
            tier = "ultra"
            credits = int(item.get("credits") or 24900)
            video_enabled = True
        elif "PRO" in raw_tier:
            tier = "pro"
            credits = int(item.get("credits") or 1000)
            video_enabled = True
        else:
            tier = "free"
            credits = int(item.get("credits") or 50)
            video_enabled = False

        profile_path = browser_profiles_dir / email
        has_profile = profile_path.is_dir()

        # Project ID mapping
        cached_proj = project_cache.get(email) or {}
        project_id = cached_proj.get("project_id") if isinstance(cached_proj, dict) else None

        glabs_status = str(item.get("status") or "").lower()
        if glabs_status not in ("valid", "refreshing"):
            if email_lower in existing_by_email:
                acc_id, _ = existing_by_email[email_lower]
                cursor.execute(
                    "DELETE FROM local_resources WHERE resource_type='google_flow_account' AND id=?",
                    (acc_id,),
                )
            continue
        if has_profile and glabs_status in ("valid", "refreshing"):
            status = "ready"
        elif has_profile:
            status = "ready"
        else:
            status = "login_required"

        if email_lower in existing_by_email:
            acc_id, current_payload = existing_by_email[email_lower]
            current_payload.update({
                "email": email,
                "tier": tier,
                "credits": credits,
                "status": status,
                "enabled": True,
                "image_enabled": True,
                "video_enabled": video_enabled,
                "profile_dir": str(profile_path),
                "project_id": project_id or current_payload.get("project_id"),
                "session_present": True,
            })
            cursor.execute(
                "UPDATE local_resources SET payload=?, updated_at=? WHERE resource_type='google_flow_account' AND id=?",
                (json.dumps(current_payload), now, acc_id),
            )
            updated_count += 1
        else:
            acc_id = uuid.uuid4().hex
            new_payload = {
                "id": acc_id,
                "email": email,
                "tier": tier,
                "status": status,
                "enabled": True,
                "image_enabled": True,
                "video_enabled": video_enabled,
                "image_auto_disabled": False,
                "video_auto_disabled": False,
                "image_quota_state": "available",
                "video_quota_state": "available",
                "quota_state": "available",
                "credits": credits,
                "last_error": None,
                "unavailable_models": [],
                "project_id": project_id,
                "project_used": 0,
                "profile_dir": str(profile_path),
                "session_present": True,
            }
            cursor.execute(
                "INSERT INTO local_resources (resource_type, id, payload, created_at, updated_at) VALUES ('google_flow_account', ?, ?, ?, ?)",
                (acc_id, json.dumps(new_payload), now, now),
            )
            synced_count += 1

    conn.commit()
    conn.close()

    print(f"Sync complete: {synced_count} inserted, {updated_count} updated.")


if __name__ == "__main__":
    sync_glabs_accounts()
