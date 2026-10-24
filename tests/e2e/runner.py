#!/usr/bin/env python3
"""
E2E Test Runner & Structured Quality Gate Reporter for CofiDocumentary
Orchestrates test execution across Tiers 1-4 and outputs a structured verification scorecard.
"""

from __future__ import annotations
import sys
import time
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

E2E_DIR = ROOT / "tests" / "e2e"
BASETEMP_DIR = ROOT / "data" / "pytest_tmp"


class E2ECollectorPlugin:
    def __init__(self):
        self.results = []
        self.start_time = None
        self.end_time = None

    def pytest_sessionstart(self, session):
        self.start_time = time.time()

    def pytest_sessionfinish(self, session, exitstatus):
        self.end_time = time.time()

    def pytest_runtest_logreport(self, report):
        if report.when == "call":
            self.results.append({
                "nodeid": report.nodeid,
                "passed": report.passed,
                "failed": report.failed,
                "skipped": report.skipped,
                "duration": getattr(report, "duration", 0.0),
            })


def run_e2e_suite(args: list[str] | None = None) -> int:
    BASETEMP_DIR.mkdir(parents=True, exist_ok=True)
    collector = E2ECollectorPlugin()

    pytest_args = [
        str(E2E_DIR),
        f"--basetemp={BASETEMP_DIR}",
        "-W", "ignore::DeprecationWarning",
        "-q",
    ]
    if args:
        pytest_args.extend(args)

    print("=" * 80)
    print(" COFI DOCUMENTARY - PROFESSIONAL SAAS STUDIO E2E TEST RUNNER")
    print(" Requirements: R1-R6 | Acceptance Criteria: AC1-AC4 | Tiers: 1-5")
    print("=" * 80)

    exit_code = pytest.main(pytest_args, plugins=[collector])

    # Classify results into Tiers and Features
    tier_mapping = {
        "Tier 1 (Feature Coverage)": {"total": 0, "passed": 0, "failed": 0},
        "Tier 2 (Boundary & Corner Cases)": {"total": 0, "passed": 0, "failed": 0},
        "Tier 3 (Cross-Feature Pairwise)": {"total": 0, "passed": 0, "failed": 0},
        "Tier 4 (Real-World Workloads)": {"total": 0, "passed": 0, "failed": 0},
        "Tier 5 (Adversarial Hardening)": {"total": 0, "passed": 0, "failed": 0},
    }

    feature_mapping = {
        "F1: SaaS UI/UX & Dual Control (AC1)": {"total": 0, "passed": 0, "failed": 0},
        "F2: Profile & Project Isolation (AC2)": {"total": 0, "passed": 0, "failed": 0},
        "F3: Non-Destructive Backfill (AC2)": {"total": 0, "passed": 0, "failed": 0},
        "F4: Persistent Edit Style Memory (AC3)": {"total": 0, "passed": 0, "failed": 0},
        "F5: Voice-Visual Sync & Policy (AC3)": {"total": 0, "passed": 0, "failed": 0},
        "F6: Channel-DNA Pre-Flight (AC4)": {"total": 0, "passed": 0, "failed": 0},
        "F7: Self-Learning Post-Mortem (AC4)": {"total": 0, "passed": 0, "failed": 0},
        "F_Cross: Pairwise Combinations (Tier 3)": {"total": 0, "passed": 0, "failed": 0},
        "F_Workload: Production Workloads (Tier 4)": {"total": 0, "passed": 0, "failed": 0},
        "F_Tier5: Adversarial Hardening (Tier 5)": {"total": 0, "passed": 0, "failed": 0},
    }

    for res in collector.results:
        nodeid = res["nodeid"]
        passed = res["passed"]
        failed = res["failed"]

        # Tier detection
        if "tier1" in nodeid:
            tier_key = "Tier 1 (Feature Coverage)"
        elif "tier2" in nodeid:
            tier_key = "Tier 2 (Boundary & Corner Cases)"
        elif "tier3" in nodeid:
            tier_key = "Tier 3 (Cross-Feature Pairwise)"
        elif "tier4" in nodeid:
            tier_key = "Tier 4 (Real-World Workloads)"
        elif "tier5" in nodeid:
            tier_key = "Tier 5 (Adversarial Hardening)"
        else:
            tier_key = "Tier 1 (Feature Coverage)"

        tier_mapping[tier_key]["total"] += 1
        if passed:
            tier_mapping[tier_key]["passed"] += 1
        if failed:
            tier_mapping[tier_key]["failed"] += 1

        # Feature detection
        if "ac1_ui_ux" in nodeid:
            feat_key = "F1: SaaS UI/UX & Dual Control (AC1)"
        elif "ac2_isolation_backfill" in nodeid:
            feat_key = "F2: Profile & Project Isolation (AC2)" if "f2" in nodeid else "F3: Non-Destructive Backfill (AC2)"
        elif "ac3_edit_memory_sync_policy" in nodeid:
            feat_key = "F4: Persistent Edit Style Memory (AC3)" if "f4" in nodeid else "F5: Voice-Visual Sync & Policy (AC3)"
        elif "ac4_preflight_self_learning" in nodeid:
            feat_key = "F6: Channel-DNA Pre-Flight (AC4)" if "f6" in nodeid else "F7: Self-Learning Post-Mortem (AC4)"
        elif "tier3_pairwise" in nodeid:
            feat_key = "F_Cross: Pairwise Combinations (Tier 3)"
        elif "tier4_workload" in nodeid:
            feat_key = "F_Workload: Production Workloads (Tier 4)"
        elif "tier5_adversarial" in nodeid:
            feat_key = "F_Tier5: Adversarial Hardening (Tier 5)"
        else:
            feat_key = "F1: SaaS UI/UX & Dual Control (AC1)"

        feature_mapping[feat_key]["total"] += 1
        if passed:
            feature_mapping[feat_key]["passed"] += 1
        if failed:
            feature_mapping[feat_key]["failed"] += 1

    total_tests = len(collector.results)
    total_passed = sum(1 for r in collector.results if r["passed"])
    total_failed = sum(1 for r in collector.results if r["failed"])
    elapsed = (collector.end_time - collector.start_time) if collector.end_time and collector.start_time else 0.0

    print("\n" + "-" * 80)
    print(" VERIFICATION SCORECARD BY FEATURE")
    print("-" * 80)
    print(f"{'Feature / Requirement':<45} | {'Tests':<6} | {'Passed':<6} | {'Failed':<6} | {'Status'}")
    print("-" * 80)
    for feat, counts in feature_mapping.items():
        status = "PASSED" if counts["failed"] == 0 and counts["total"] > 0 else "FAILED"
        print(f"{feat:<45} | {counts['total']:<6} | {counts['passed']:<6} | {counts['failed']:<6} | {status}")

    print("\n" + "-" * 80)
    print(" VERIFICATION SCORECARD BY TIER")
    print("-" * 80)
    print(f"{'Test Tier':<35} | {'Target':<8} | {'Actual':<6} | {'Passed':<6} | {'Status'}")
    print("-" * 80)
    targets = {
        "Tier 1 (Feature Coverage)": ">=35",
        "Tier 2 (Boundary & Corner Cases)": ">=35",
        "Tier 3 (Cross-Feature Pairwise)": ">=7",
        "Tier 4 (Real-World Workloads)": ">=5",
        "Tier 5 (Adversarial Hardening)": ">=25",
    }
    for tier, counts in tier_mapping.items():
        tgt = targets.get(tier, "-")
        status = "PASSED" if counts["failed"] == 0 and counts["total"] > 0 else "FAILED"
        print(f"{tier:<35} | {tgt:<8} | {counts['total']:<6} | {counts['passed']:<6} | {status}")

    print("-" * 80)
    print(f"Total Test Cases: {total_tests} (Threshold: >=82)")
    print(f"Passed:           {total_passed}")
    print(f"Failed:           {total_failed}")
    print(f"Duration:         {elapsed:.2f}s")
    gate_verdict = "PASSED (READY FOR DEPLOYMENT / QUALITY GATE SATISFIED)" if total_failed == 0 and total_tests >= 82 else "FAILED"
    print(f"Gate Verdict:     {gate_verdict}")
    print("=" * 80 + "\n")

    return 0 if (total_failed == 0 and total_tests >= 82) else 1


if __name__ == "__main__":
    sys.exit(run_e2e_suite(sys.argv[1:]))
