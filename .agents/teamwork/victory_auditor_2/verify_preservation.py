import os
import sqlite3
from pathlib import Path

# 1. Check style reference image
ref = Path("workspaces/20261019-185102-31983814/media/style_reference/style_reference.png")
assert ref.exists(), f"Style reference {ref} does not exist!"
size = ref.stat().st_size
assert size == 533261, f"Expected size 533261, got {size}"
print(f"PASS: Style reference exists with {size} bytes")

# 2. Check essential job artifacts
ws = Path("workspaces/20261019-185102-31983814")
for fname in ["input.json", "ai_visual_settings.json", "creative_brief.json", "research.md", "script.md", "visual_manifest.json", "voice_manifest.json"]:
    fpath = ws / fname
    assert fpath.exists(), f"Essential file {fpath} missing!"
print("PASS: Essential workspace files present")

# 3. Check media files
renders_dir = ws / "media" / "renders"
if renders_dir.exists():
    imgs = list(renders_dir.glob("*.png")) + list(renders_dir.glob("*.jpg"))
    print(f"PASS: Renders dir contains {len(imgs)} images")
videos_dir = ws / "media" / "videos"
if videos_dir.exists():
    mp4s = list(videos_dir.glob("*.mp4"))
    print(f"PASS: Videos dir contains {len(mp4s)} mp4 clips")

# 4. Check SQLite database integrity
for db_rel in ["data/radar.db", "data/media_factory/cofi_studio.db", "data/media_factory/media_factory.db"]:
    db_p = Path(db_rel)
    assert db_p.exists(), f"DB {db_rel} missing!"
    c = sqlite3.connect(str(db_p))
    res = c.execute("PRAGMA integrity_check").fetchall()
    c.close()
    assert res == [("ok",)], f"Integrity check failed for {db_rel}: {res}"
    print(f"PASS: DB {db_rel} integrity check passed (size: {db_p.stat().st_size} bytes)")

# 5. Check active Google Flow accounts in DB
c = sqlite3.connect("data/media_factory/cofi_studio.db")
accounts = c.execute("SELECT id FROM local_resources WHERE resource_type='google_flow_account'").fetchall()
c.close()
assert len(accounts) == 3, f"Expected 3 accounts, got {len(accounts)}"
print(f"PASS: Active Google Flow accounts count = {len(accounts)}")
for acc_id, in accounts:
    pdir = Path(f"data/media_factory/google-flow-profiles/{acc_id}")
    assert pdir.is_dir(), f"Profile dir {pdir} does not exist!"
    print(f"PASS: Profile dir for account {acc_id} exists")

print("\nALL R4 NON-DESTRUCTIVE PRESERVATION CHECKS VERIFIED EMPIRICALLY!")
