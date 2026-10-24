import os
import json
import sqlite3
from pathlib import Path

def main():
    print("=== 1. CHECKING ACTIVE JOB 20261019-185102-31983814 ===")
    job_json_path = Path("data/jobs/20261019-185102-31983814/job.json")
    ws_path = Path("workspaces/20261019-185102-31983814")
    assert job_json_path.exists(), f"Job json missing: {job_json_path}"
    assert ws_path.exists(), f"Workspace missing: {ws_path}"

    job_data = json.loads(job_json_path.read_text(encoding="utf-8"))
    print("Job ID:", job_data.get("id"))
    print("Job Title:", job_data.get("title"))
    print("Job Status:", job_data.get("status"))
    print("Channel Profile ID:", job_data.get("channel_profile_id"))
    print("Style Mode:", job_data.get("style_mode"))
    print("Style Preset:", job_data.get("style_preset"))

    ws_files = list(ws_path.glob("*"))
    print(f"Workspace contains {len(ws_files)} root files/dirs")
    for f in sorted(ws_files):
        print(f"  {f.name} ({f.stat().st_size} bytes)" if f.is_file() else f"  [DIR] {f.name}")

    ref_img = ws_path / "media" / "style_reference" / "style_reference.png"
    assert ref_img.exists(), f"Reference image missing: {ref_img}"
    print(f"Reference image exists: {ref_img} ({ref_img.stat().st_size} bytes)")

    print("\n=== 2. CHECKING SQLITE DATABASES ===")
    db_paths = [
        Path("data/radar.db"),
        Path("data/media_factory/cofi_studio.db"),
        Path("data/media_factory/media_factory.db"),
    ]
    for p in db_paths:
        print(f"DB {p}: exists={p.exists()}, size={p.stat().st_size if p.exists() else 0} bytes")
        if p.exists() and p.stat().st_size > 0:
            con = sqlite3.connect(p)
            tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            print(f"  Tables: {tables}")
            for t in tables:
                cnt = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                print(f"    {t}: {cnt} rows")
            con.close()

    print("\n=== 3. CHECKING GOOGLE FLOW ACCOUNTS ===")
    mf_db = Path("data/media_factory/cofi_studio.db")
    if not mf_db.exists() or mf_db.stat().st_size == 0:
        mf_db = Path("data/media_factory/media_factory.db")
    con = sqlite3.connect(mf_db)
    rows = con.execute("SELECT id, resource_type, payload FROM local_resources WHERE resource_type='google_flow_account'").fetchall()
    print(f"Active Google Flow accounts count: {len(rows)}")
    for rid, rtype, rdata in rows:
        acc = json.loads(rdata)
        print(f"  Account ID: {rid}, Email: {acc.get('email')}, Status: {acc.get('status')}, Tier: {acc.get('tier')}")
        prof_dir = Path("data/media_factory/google-flow-profiles") / rid
        print(f"    Profile dir exists: {prof_dir.exists()}")
    con.close()
    print("\nALL EMPIRICAL PRESERVATION CHECKS COMPLETED!")

if __name__ == "__main__":
    main()
