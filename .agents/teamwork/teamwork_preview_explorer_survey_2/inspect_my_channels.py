import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")

con = sqlite3.connect(r"B:\ALL_TOOLS\CofiRadar\data\cofi-radar.db")
cur = con.cursor()

print("my_channels in cofi-radar.db:")
rows = cur.execute("SELECT channel_id, label, content_type, niche_id, added_at, last_scan_at FROM my_channels").fetchall()
for r in rows:
    print("  ", r)

print("\nSearching channels table:")
for target in ["1e24de3ab5", "e544a64b7c", "aa913eb90d", "f6ec4dfff3"]:
    r = cur.execute("SELECT id, title, custom_url FROM channels WHERE id LIKE ? OR custom_url LIKE ? OR title LIKE ?", (f"%{target}%", f"%{target}%", f"%{target}%")).fetchall()
    print(f"  Target {target}: {r}")
