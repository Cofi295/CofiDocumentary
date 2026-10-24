"""
Independent Forensic Integrity Probe by auditor_m1_fix.
Verifies all Milestone 1 Iteration 2 fixes empirically.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from server import create_app

def run_auditor_probe():
    client = TestClient(create_app())
    print("=== AUDITOR INDEPENDENT INTEGRITY PROBE ===")

    # Test 1: POST /api/jobs with real channel-1e24de3ab5
    r1 = client.post("/api/jobs", json={"title": "Auditor Probe Job", "channel_profile_id": "channel-1e24de3ab5"})
    assert r1.status_code == 200, f"r1 failed: {r1.status_code} {r1.text}"
    j1 = r1.json()
    jid = j1["id"]
    print("Test 1 PASS: Job created:", jid)

    # Test 1b: Verify on-disk file directly without using service
    disk_file = Path("data/jobs") / jid / "job.json"
    assert disk_file.exists(), f"Disk file {disk_file} does not exist!"
    on_disk_data = json.loads(disk_file.read_text(encoding="utf-8"))
    assert on_disk_data.get("editing_dna"), "editing_dna missing on disk!"
    assert on_disk_data.get("default_creative_brief"), "default_creative_brief missing on disk!"
    strat = on_disk_data.get("visual_strategy")
    assert strat == "hybrid", f"Expected hybrid, got {strat}"
    print("Test 1b PASS: Direct disk file verified!")

    # Test 2: POST /api/jobs with non-existent profile
    r2 = client.post("/api/jobs", json={"title": "Ghost Job", "channel_profile_id": "channel-ghost-99999"})
    assert r2.status_code == 400, f"Expected 400, got {r2.status_code}: {r2.text}"
    print("Test 2 PASS: Non-existent profile rejected with 400")

    # Test 3: POST /api/jobs with malformed non-dict payload
    r3 = client.post("/api/jobs", json=["invalid", "list"])
    assert r3.status_code == 400, f"Expected 400, got {r3.status_code}: {r3.text}"
    print("Test 3 PASS: Non-dict payload on POST rejected with 400")

    # Test 4: PATCH /api/jobs/{jid} with malformed non-dict payload
    r4 = client.patch(f"/api/jobs/{jid}", json="not_a_dict")
    assert r4.status_code == 400, f"Expected 400, got {r4.status_code}: {r4.text}"
    print("Test 4 PASS: Non-dict payload on PATCH rejected with 400")

    # Test 5: PATCH /api/jobs/{jid} with malformed phases
    r5 = client.patch(f"/api/jobs/{jid}", json={"phases": "not_a_dict_phase"})
    assert r5.status_code == 400, f"Expected 400, got {r5.status_code}: {r5.text}"
    print("Test 5 PASS: Non-dict phases on PATCH rejected with 400")

    # Test 6: PUT /api/radar/channel-profiles/{id} with malformed editing_dna
    r6 = client.put("/api/radar/channel-profiles/channel-1e24de3ab5", json={"editing_dna": "corrupted_string"})
    assert r6.status_code == 400, f"Expected 400, got {r6.status_code}: {r6.text}"
    print("Test 6 PASS: Malformed nested editing_dna on PUT rejected with 400")

    # Test 7: PUT non-existent profile
    r7 = client.put("/api/radar/channel-profiles/channel-ghost-99999", json={"label": "Ghost"})
    assert r7.status_code == 404, f"Expected 404, got {r7.status_code}: {r7.text}"
    print("Test 7 PASS: Non-existent profile on PUT returned 404")

    # Test 8: Cleanup and verify disk deletion
    del_r = client.delete(f"/api/jobs/{jid}")
    assert del_r.status_code == 200, f"Delete failed: {del_r.status_code}"
    assert not disk_file.exists(), f"Disk file {disk_file} still exists after delete!"
    print("Test 8 PASS: Job deleted and disk file purged!")

    print("=== ALL AUDITOR PROBES PASSED 100% ===")

if __name__ == "__main__":
    run_auditor_probe()
