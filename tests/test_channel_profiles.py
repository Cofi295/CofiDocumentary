import json
from pathlib import Path

from documentary.codex_gateway import StageResult
from documentary.models import PHASES
from documentary.service import DocumentaryService
from documentary.store import JobStore


class FakeCodex:
    def __init__(self, *, fail: bool = False, reverse_today: bool = False, reverse_plan: bool = False):
        self.fail = fail
        self.reverse_today = reverse_today
        self.reverse_plan = reverse_plan
        self.calls: list[str] = []
        self.prompts: list[tuple[str, str]] = []

    def run_prompt(self, prompt, workspace, label, **kwargs):
        self.calls.append(str(label))
        self.prompts.append((str(label), str(prompt)))
        if self.fail:
            raise RuntimeError("Codex test unavailable")
        if str(label).startswith("channel_profile_strategy_"):
            payload = {
                "status": "ok",
                "audience_hypothesis": {
                    "status": "inferred",
                    "likely_interests": ["engineering failures", "China infrastructure"],
                    "viewer_needs": ["clear explanations"],
                    "content_preferences": ["evidence-led documentary"],
                    "age_groups": None,
                    "gender": None,
                    "confidence": "medium",
                    "basis": ["winner terms", "public performance"],
                },
                "own_channel_assessment": {
                    "strengths": ["bridge/system topics"],
                    "weaknesses": ["generic framing"],
                },
                "competitor_assessment": {
                    "winning_patterns": ["collapse explainers"],
                    "content_gaps": ["mechanism-first explanation"],
                },
                "strategy": {
                    "positioning": ["technical documentary"],
                    "topic_rules": ["prefer evidence + mechanism"],
                    "avoid": ["generic news recap"],
                },
                "winner_analysis": {
                    "own_winners": ["China bridge overload system failure"],
                    "competitor_winners": ["China dam collapse sediment crisis"],
                    "shared_winner_clusters": [{"cluster": "China infrastructure system failures", "own_evidence": ["China bridge overload system failure"], "competitor_evidence": ["China dam collapse sediment crisis"]}],
                },
            }
        elif str(label).startswith("channel_profile_today_rank_"):
            if self.reverse_today:
                rows = [
                    {"id": "t0", "verdict": "approve", "score": 94, "proven_winner_match": True, "winner_cluster": "China infrastructure system failures", "own_winner_evidence": ["China bridge overload system failure"], "competitor_winner_evidence": ["China dam collapse sediment crisis"], "audience_fit": 95, "channel_fit": 92, "trend_fit": 90, "competition_fit": 88, "why": ["best raw candidate"], "angle": "make it evidence-led", "risks": []},
                    {"id": "t1", "verdict": "watch", "score": 40, "proven_winner_match": True, "winner_cluster": "China infrastructure system failures", "own_winner_evidence": ["China bridge overload system failure"], "competitor_winner_evidence": ["China dam collapse sediment crisis"], "audience_fit": 45, "channel_fit": 50, "trend_fit": 80, "competition_fit": 40, "why": ["less preferred"], "angle": "narrow the mechanism", "risks": []},
                ]
            else:
                rows = [
                    {"id": "t0", "verdict": "watch", "score": 61, "proven_winner_match": False, "winner_cluster": "", "own_winner_evidence": [], "competitor_winner_evidence": [], "audience_fit": 60, "channel_fit": 63, "trend_fit": 64, "competition_fit": 58, "why": ["generic"], "angle": "find a sharper hook", "risks": ["weak differentiation"]},
                    {"id": "t1", "verdict": "approve", "score": 93, "proven_winner_match": True, "winner_cluster": "China dam and infrastructure failures", "own_winner_evidence": ["China bridge overload system failure"], "competitor_winner_evidence": ["China dam collapse sediment crisis"], "audience_fit": 94, "channel_fit": 90, "trend_fit": 91, "competition_fit": 82, "why": ["strong fit"], "angle": "explain the failure mechanism", "risks": []},
                ]
            payload = {"rankings": rows}
        elif str(label).startswith("channel_profile_plan_review_"):
            ids = list(range(1, 31))
            if self.reverse_plan:
                ids.reverse()
            payload = {
                "status": "ok",
                "items": [
                    {"id": str(item_id), "rank": rank, "verdict": "approve" if rank <= 10 else "watch", "score": max(55, 96 - rank), "why": [f"plan reason {item_id}"], "angle": f"angle {item_id}"}
                    for rank, item_id in enumerate(ids, start=1)
                ],
            }
        else:
            payload = {}
        return StageResult(0, json.dumps(payload), Path(workspace) / f"{label}.log")


class FakeRadar:
    def __init__(self, *, own_sampled_videos: int = 20, own_total_videos: int = 20):
        self.scan_calls: list[str] = []
        self.status_updates: list[tuple[int, str]] = []
        self.plan_channel_ids: list[str | None] = []
        self.today_calls: list[dict[str, object]] = []
        self.own_sampled_videos = own_sampled_videos
        self.own_total_videos = own_total_videos
        self.items = [
            {
                "id": index,
                "plan_id": 77,
                "position": index,
                "topic_anchor": f"Topic {index}",
                "production_brief": f"Brief {index}",
                "status": "ready",
                "channel_fit": 70 + index,
            }
            for index in range(1, 31)
        ]

    def channel_scan(self, payload):
        ref = str(payload["channel_ref"])
        self.scan_calls.append(ref)
        slug = ref.rsplit("/", 1)[-1].replace("@", "") or "channel"
        is_own = "own" in slug
        dna = {
            "winner_terms": ["china", "bridge", "system"] if is_own else ["china", "dam", "collapse"],
            "weak_terms": ["generic"],
            "win_rate": 0.25 if is_own else 0.4,
            "momentum": 45 if is_own else 70,
            "median_views": 1000 if is_own else 3000,
            "sampled_videos": self.own_sampled_videos if is_own else 20,
            "winner_titles": [
                {
                    "title": "China bridge overload system failure" if is_own else "China dam collapse sediment crisis",
                    "views": 29185 if is_own else 513412,
                    "vph": 120.0 if is_own else 2676.7,
                    "outlier": 4.2 if is_own else 27.03,
                }
            ],
        }
        return {
            "id": len(self.scan_calls),
            "channel_id": f"UC-{slug}",
            "channel": {
                "id": f"UC-{slug}",
                "title": slug,
                "url": ref,
                "subscribers": 1000,
                "total_views": 20000,
                "total_videos": self.own_total_videos if is_own else 20,
            },
            "dna": dna,
        }

    def channel_today_scan(self, channel_id, *, hours=48, limit=5, max_videos=60):
        assert hours == 48
        self.today_calls.append({
            "channel_id": channel_id,
            "hours": hours,
            "limit": limit,
            "max_videos": max_videos,
        })
        return {
            "channel_id": channel_id,
            "niche_id": 9,
            "scan_id": 44,
            "market": "US",
            "plan_id": 66,
            "today": [
                {
                    "id": 901,
                    "topic_anchor": "China dam collapse explained",
                    "channel_fit": 82,
                    "evidence_outlier": 8.2,
                },
                {
                    "id": 902,
                    "topic_anchor": "Generic bridge system update",
                    "channel_fit": 96,
                    "evidence_outlier": 10.0,
                }
            ],
        }

    def create_plan(self, niche_id, *, requested_count=30, my_channel_id=None):
        assert niche_id == 9
        assert requested_count == 30
        self.plan_channel_ids.append(my_channel_id)
        return {"id": 77, "supported": 30, "items": list(self.items)}

    def plan_items(self, plan_id):
        assert plan_id == 77
        return [dict(item) for item in self.items]

    def update_plan_item_status(self, item_id, status):
        self.status_updates.append((int(item_id), str(status)))
        for item in self.items:
            if int(item["id"]) == int(item_id):
                item["status"] = status
                break
        return {"ok": True, "id": int(item_id), "status": status}


def make_service(tmp_path: Path, radar: FakeRadar, codex: FakeCodex | None = None) -> DocumentaryService:
    return DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        radar_client=radar,
        codex_gateway=codex or FakeCodex(),
        remotion_dir=tmp_path / "CofiRemotion",
    )


def test_channel_profile_persists_own_channel_and_multiple_competitors(tmp_path: Path):
    radar = FakeRadar()
    service = make_service(tmp_path, radar)

    profile = service.save_channel_profile({
        "label": "US documentary",
        "market": "US",
        "own_channel_ref": "https://youtube.com/@own",
        "competitor_refs": ["https://youtube.com/@comp-a", "https://youtube.com/@comp-b"],
    })

    assert profile["own_channel"]["channel_id"] == "UC-own"
    assert len(profile["competitors"]) == 2
    assert profile["latest_analysis"]["competitors"]["count"] == 2
    assert "dam" in profile["latest_analysis"]["competitors"]["opportunity_terms"]
    assert profile["latest_analysis"]["audience"]["age_groups"] is None

    reloaded = make_service(tmp_path, FakeRadar())
    saved = reloaded.list_channel_profiles()
    assert [item["id"] for item in saved] == [profile["id"]]
    assert saved[0]["competitor_refs"] == ["https://youtube.com/@comp-a", "https://youtube.com/@comp-b"]


def test_channel_profile_persists_editorial_dna_and_default_duration(tmp_path: Path):
    service = make_service(tmp_path, FakeRadar())
    editorial_dna = {
        "narrative": {
            "pov": "third_person_documentary",
            "hook": "concrete_scene_then_reversal",
        },
        "footage": {
            "priority": "archival_evidence_first",
            "typical_shot_seconds": [4, 8],
            "rules": [
                "Match footage to the named person, event, document, place, and period.",
                "Reuse authentic archival material contextually instead of forcing one new asset per sentence.",
            ],
            "avoid": ["generic unrelated stock", "slideshow pacing"],
        },
    }

    profile = service.save_channel_profile({
        "label": "US secrets",
        "market": "US",
        "own_channel_ref": "https://youtube.com/@own",
        "competitor_refs": ["https://youtube.com/@comp-a"],
        "default_duration_minutes": 30,
        "editorial_dna": editorial_dna,
    })

    assert profile["default_duration_minutes"] == 30
    assert profile["editorial_dna"] == editorial_dna

    refreshed = service.refresh_channel_profile(profile["id"])
    assert refreshed["default_duration_minutes"] == 30
    assert refreshed["editorial_dna"]["footage"]["priority"] == "archival_evidence_first"

    reloaded = make_service(tmp_path, FakeRadar())
    saved = reloaded.get_channel_profile(profile["id"])
    assert saved["default_duration_minutes"] == 30
    assert saved["editorial_dna"] == editorial_dna


def test_job_from_profile_inherits_editorial_dna_and_profile_default_duration(tmp_path: Path):
    service = make_service(tmp_path, FakeRadar())
    profile = service.save_channel_profile({
        "label": "US secrets",
        "market": "US",
        "own_channel_ref": "https://youtube.com/@own",
        "competitor_refs": ["https://youtube.com/@comp-a"],
        "default_duration_minutes": 30,
        "editorial_dna": {
            "footage": {
                "priority": "archival_evidence_first",
                "rules": ["Cut footage by narration clause and evidence beat."],
            },
        },
    })

    job = service.create_job({
        "title": "Profile-driven documentary",
        "market": "US",
        "language": "en",
        "channel_profile_id": profile["id"],
    })

    assert job["production_recipe"]["target_duration_sec"] == 1800
    assert job["channel_profile_snapshot"]["id"] == profile["id"]
    assert job["channel_profile_snapshot"]["editorial_dna"]["footage"]["priority"] == "archival_evidence_first"


def test_channel_profile_can_be_deleted_and_stays_deleted_after_reload(tmp_path: Path):
    service = make_service(tmp_path, FakeRadar())
    profile = service.save_channel_profile({
        "label": "Delete me",
        "market": "US",
        "own_channel_ref": "https://youtube.com/@own",
        "competitor_refs": ["https://youtube.com/@comp-a"],
    })

    deleted = service.delete_channel_profile(profile["id"])

    assert deleted["id"] == profile["id"]
    assert service.list_channel_profiles() == []
    assert make_service(tmp_path, FakeRadar()).list_channel_profiles() == []


def test_codex_json_parser_accepts_markdown_escaped_keys_and_brackets() -> None:
    raw = (
        r'{"status":"ok","evidence\_scope":"public\_youtube\_only",'
        r'"audience\_hypothesis":{"likely\_interests":\["infrastructure"\],'
        r'"age\_groups":null},"note":"line\nkept"}'
    )

    parsed = DocumentaryService._json_object_from_message(raw)

    assert parsed["evidence_scope"] == "public_youtube_only"
    assert parsed["audience_hypothesis"]["likely_interests"] == ["infrastructure"]
    assert parsed["audience_hypothesis"]["age_groups"] is None
    assert parsed["note"] == "line\nkept"


def test_channel_profile_can_start_from_competitor_without_own_channel(tmp_path: Path):
    radar = FakeRadar()
    service = make_service(tmp_path, radar)

    profile = service.save_channel_profile({
        "label": "New channel",
        "market": "US",
        "own_channel_ref": "",
        "competitor_refs": ["https://youtube.com/@comp-a"],
    })

    assert profile["own_channel"] == {}
    assert profile["source_mode"] == "competitor_only"
    assert profile["latest_analysis"]["source_mode"] == "competitor_only"
    assert len(profile["competitors"]) == 1


def test_channel_profile_rejects_empty_sources(tmp_path: Path):
    service = make_service(tmp_path, FakeRadar())

    try:
        service.save_channel_profile({"own_channel_ref": "", "competitor_refs": []})
    except ValueError as exc:
        assert "ít nhất một kênh" in str(exc)
    else:
        raise AssertionError("Expected profile without any source to be rejected")


def test_established_own_channel_uses_own_only_mode_without_competitor(tmp_path: Path):
    radar = FakeRadar()
    service = make_service(tmp_path, radar)

    profile = service.save_channel_profile({
        "own_channel_ref": "https://youtube.com/@own",
        "competitor_refs": [],
        "market": "US",
    })
    assert profile["source_mode"] == "own_only"

    service.refresh_channel_profile(profile["id"])
    assert radar.scan_calls == ["https://youtube.com/@own", "https://youtube.com/@own"]


def test_channel_profile_plan_exposes_three_pending_days_and_advances(tmp_path: Path):
    radar = FakeRadar()
    service = make_service(tmp_path, radar)
    profile = service.save_channel_profile({
        "own_channel_ref": "https://youtube.com/@own",
        "competitor_refs": ["https://youtube.com/@comp-a"],
        "market": "US",
    })

    plan = service.channel_profile_plan(profile["id"])

    assert plan["total"] == 30
    assert [item["day_number"] for item in plan["upcoming"]] == [1, 2, 3]

    advanced = service.update_channel_profile_plan_item(profile["id"], 1, "done")
    assert advanced["completed"] == 1
    assert [item["day_number"] for item in advanced["upcoming"]] == [2, 3, 4]


def test_create_job_without_title_uses_hot_topic_from_channel_profile(tmp_path: Path):
    radar = FakeRadar(own_sampled_videos=5, own_total_videos=5)
    service = make_service(tmp_path, radar, FakeCodex())
    profile = service.save_channel_profile({
        "own_channel_ref": "https://youtube.com/@own",
        "competitor_refs": ["https://youtube.com/@comp-a"],
        "market": "US",
    })

    job = service.create_job({
        "channel_profile_id": profile["id"],
        "target_duration_minutes": 5,
    })

    assert job["title"]
    assert job["topic_discovery"]["source"] == "channel_profile_today"
    assert job["topic_discovery"]["profile_id"] == profile["id"]
    assert radar.today_calls


def test_today_scan_uses_48h_and_adds_competitor_support(tmp_path: Path):
    radar = FakeRadar(own_sampled_videos=5, own_total_videos=5)
    codex = FakeCodex()
    service = make_service(tmp_path, radar, codex)
    profile = service.save_channel_profile({
        "own_channel_ref": "https://youtube.com/@own",
        "competitor_refs": ["https://youtube.com/@comp-a"],
        "market": "US",
    })

    result = service.channel_profile_today(profile["id"])

    assert result["hours"] == 48
    assert result["today"][0]["competitor_support_count"] == 1
    assert result["today"][0]["profile_score"] > result["today"][0]["channel_fit"]
    assert result["decision_engine"] == "codex_plus_radar"
    assert result["today"][0]["codex_verdict"] == "approve"
    assert result["codex_analysis"]["audience_hypothesis"]["status"] == "inferred"
    assert result["codex_analysis"]["audience_hypothesis"]["age_groups"] is None
    assert radar.today_calls[-1]["max_videos"] == 30
    assert any(call.startswith("channel_profile_strategy_") for call in codex.calls)
    assert any(call.startswith("channel_profile_today_rank_") for call in codex.calls)
    strategy_prompt = next(prompt for label, prompt in codex.prompts if label.startswith("channel_profile_strategy_"))
    rank_prompt = next(prompt for label, prompt in codex.prompts if label.startswith("channel_profile_today_rank_"))
    assert "China bridge overload system failure" in strategy_prompt
    assert "China dam collapse sediment crisis" in strategy_prompt
    assert "WINNER_EVIDENCE" in rank_prompt
    assert "proven_winner_match" in rank_prompt
    assert result["today"][0]["proven_winner_match"] is True
    assert result["today"][0]["winner_cluster"] == "China dam and infrastructure failures"
    assert result["codex_ranking"]["winner_rejected"] == 1


def test_hybrid_today_falls_back_to_competitor_when_own_channel_has_no_radar_seed(tmp_path: Path):
    class OwnTodayFailsRadar(FakeRadar):
        def channel_today_scan(self, channel_id, *, hours=48, limit=5, max_videos=60):
            if channel_id == "UC-own":
                self.today_calls.append({
                    "channel_id": channel_id,
                    "hours": hours,
                    "limit": limit,
                    "max_videos": max_videos,
                })
                raise RuntimeError("Kênh chưa có đủ DNA từ video công khai để tìm chủ đề mới")
            return super().channel_today_scan(channel_id, hours=hours, limit=limit, max_videos=max_videos)

    radar = OwnTodayFailsRadar(own_sampled_videos=1, own_total_videos=1)
    service = make_service(tmp_path, radar, FakeCodex())
    profile = service.save_channel_profile({
        "own_channel_ref": "https://youtube.com/@own",
        "competitor_refs": ["https://youtube.com/@comp-a"],
        "market": "US",
    })

    result = service.channel_profile_today(profile["id"])

    assert result["source_mode"] == "hybrid"
    assert result["mode"] == "hybrid_competitor_fallback"
    assert result["today"]
    assert result["today"][0]["seed_channel"] == "comp-a"
    assert [call["channel_id"] for call in radar.today_calls] == ["UC-own", "UC-comp-a"]


def test_codex_ranking_can_override_raw_radar_order(tmp_path: Path):
    radar = FakeRadar(own_sampled_videos=5, own_total_videos=5)
    service = make_service(tmp_path, radar, FakeCodex())
    profile = service.save_channel_profile({
        "own_channel_ref": "https://youtube.com/@own",
        "competitor_refs": ["https://youtube.com/@comp-a"],
        "market": "US",
    })

    result = service.channel_profile_today(profile["id"])

    assert result["today"][0]["id"] == 901
    assert result["today"][0]["codex_score"] == 93
    assert result["today"][0]["radar_profile_score"] == 87
    assert result["today"][0]["profile_score"] == 93


def test_codex_failure_is_explicit_radar_fallback(tmp_path: Path):
    radar = FakeRadar(own_sampled_videos=5, own_total_videos=5)
    service = make_service(tmp_path, radar, FakeCodex(fail=True))
    profile = service.save_channel_profile({
        "own_channel_ref": "https://youtube.com/@own",
        "competitor_refs": ["https://youtube.com/@comp-a"],
        "market": "US",
    })

    result = service.channel_profile_today(profile["id"])

    assert result["decision_engine"] == "radar_fallback"
    assert result["codex_ranking"]["status"] == "unavailable"
    assert result["today"][0]["codex_status"] == "unavailable"
    assert result["codex_analysis"]["audience_hypothesis"]["age_groups"] is None


def test_new_channel_today_uses_competitor_as_48h_seed(tmp_path: Path):
    radar = FakeRadar()
    service = make_service(tmp_path, radar)
    profile = service.save_channel_profile({
        "own_channel_ref": "",
        "competitor_refs": ["https://youtube.com/@comp-a"],
        "market": "US",
    })

    result = service.channel_profile_today(profile["id"])

    assert result["source_mode"] == "competitor_only"
    assert result["hours"] == 48
    assert result["today"]
    assert result["today"][0]["seed_channel"] == "comp-a"
    assert radar.today_calls[-1]["max_videos"] == 30


def test_new_channel_plan_uses_competitor_niche_without_own_channel_id(tmp_path: Path):
    radar = FakeRadar()
    service = make_service(tmp_path, radar)
    profile = service.save_channel_profile({
        "own_channel_ref": "",
        "competitor_refs": ["https://youtube.com/@comp-a"],
        "market": "US",
    })

    plan = service.channel_profile_plan(profile["id"])

    assert plan["source_mode"] == "competitor_only"
    assert [item["day_number"] for item in plan["upcoming"]] == [1, 2, 3]
    assert radar.plan_channel_ids[-1] is None
    assert radar.today_calls[-1]["max_videos"] == 30


def test_new_channel_plan_reuses_latest_today_niche_without_second_live_scan(tmp_path: Path):
    radar = FakeRadar()
    service = make_service(tmp_path, radar)
    profile = service.save_channel_profile({
        "own_channel_ref": "",
        "competitor_refs": ["https://youtube.com/@comp-a"],
        "market": "US",
    })

    service.channel_profile_today(profile["id"])
    assert len(radar.today_calls) == 1

    plan = service.channel_profile_plan(profile["id"])

    assert plan["source_mode"] == "competitor_only"
    assert len(radar.today_calls) == 1
    assert radar.plan_channel_ids[-1] is None


def test_codex_reviews_and_reorders_30_day_plan(tmp_path: Path):
    radar = FakeRadar()
    service = make_service(tmp_path, radar, FakeCodex(reverse_plan=True))
    profile = service.save_channel_profile({
        "own_channel_ref": "https://youtube.com/@own",
        "competitor_refs": ["https://youtube.com/@comp-a"],
        "market": "US",
    })

    plan = service.channel_profile_plan(profile["id"])

    assert plan["decision_engine"] == "codex_plus_radar"
    assert [item["id"] for item in plan["upcoming"]] == [30, 29, 28]
    assert [item["day_number"] for item in plan["upcoming"]] == [1, 2, 3]
    assert plan["upcoming"][0]["codex_status"] == "ok"
    assert plan["upcoming"][0]["codex_angle"] == "angle 30"

    reloaded = make_service(tmp_path, radar, FakeCodex(fail=True))
    persisted = reloaded.channel_profile_plan(profile["id"], rebuild=False, refresh_profile=False)
    assert [item["id"] for item in persisted["upcoming"]] == [30, 29, 28]
    assert persisted["decision_engine"] == "codex_plus_radar"


def test_profile_activity_exposes_codex_completion_and_plan_can_rerun_codex(tmp_path: Path):
    radar = FakeRadar()
    codex = FakeCodex()
    service = make_service(tmp_path, radar, codex)
    profile = service.save_channel_profile({
        "own_channel_ref": "https://youtube.com/@own",
        "competitor_refs": ["https://youtube.com/@comp-a"],
        "market": "US",
    })

    service.channel_profile_today(profile["id"])
    today_activity = service.channel_profile_activity(profile["id"])
    assert today_activity["operation"] == "today"
    assert today_activity["stage"] == "done"
    assert today_activity["status"] == "done"
    assert today_activity["engine"] == "codex"

    service.channel_profile_plan(profile["id"])
    first_review_calls = len([call for call in codex.calls if call.startswith("channel_profile_plan_review_")])
    service.channel_profile_plan(profile["id"], refresh_profile=False, refresh_codex=True)
    second_review_calls = len([call for call in codex.calls if call.startswith("channel_profile_plan_review_")])
    assert second_review_calls == first_review_calls + 1
    plan_activity = service.channel_profile_activity(profile["id"])
    assert plan_activity["operation"] == "plan"
    assert plan_activity["stage"] == "done"
    assert plan_activity["status"] == "done"
    assert plan_activity["engine"] == "codex"


def test_completed_job_auto_marks_linked_plan_item_done(tmp_path: Path, monkeypatch):
    radar = FakeRadar()
    service = make_service(tmp_path, radar)
    profile = service.save_channel_profile({
        "own_channel_ref": "https://youtube.com/@own",
        "competitor_refs": ["https://youtube.com/@comp-a"],
        "market": "US",
    })
    service.channel_profile_plan(profile["id"])
    job = service.create_job({
        "title": "Plan video",
        "channel_profile_id": profile["id"],
        "channel_plan_item_id": 2,
    })
    monkeypatch.setattr(
        service,
        "_run_phase",
        lambda job, phase, workspace: StageResult(0, "ok", Path(workspace) / f"{phase}.log"),
    )
    monkeypatch.setattr(service, "_validate_artifacts", lambda phase, workspace, job: None)

    service._run_sequence(job["id"], list(PHASES))

    assert service.get_job(job["id"])["status"] == "completed"
    assert (2, "done") in radar.status_updates


def test_channel_profile_ui_exposes_profile_competitors_today_and_plan_actions() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    js = (root / "static" / "app.js").read_text(encoding="utf-8")

    assert "channelProfileSelect" in html
    assert "own_channel_ref" in html
    assert "tùy chọn nếu chưa có kênh" in html
    assert "Chế độ AUTO" in html
    assert "competitorInputs" in html
    assert "Gợi ý video mới hôm nay · trend 48h" in html
    assert "Tạo danh sách video 30 ngày" in html
    assert "newChannelProfileBtn" in html
    assert "Tạo profile mới" in html
    assert "saveChannelProfileLabel" in html
    assert "channelProfileCards" in html
    assert "Sửa" in js
    assert "Xóa" in js
    assert 'method: "DELETE"' in js
    assert "edit-channel-profile" in js
    assert "delete-channel-profile" in js
    assert "channelProfileActivity" in html
    assert "Tube/Cofi Radar thu dữ liệu công khai" in html
    assert "/api/radar/channel-profiles/" in js
    assert "/activity" in js
    assert "refresh_codex=true" in js
    assert "Codex · xếp hạng" in js
    assert "Codex · review 30 ngày" in js
    assert "Radar = dữ liệu/tín hiệu · Codex = phân tích kênh" in js
    assert "codex_plus_radar" in js
    assert "channel_plan_item_id" in js
    assert "Hãy nhập kênh của bạn hoặc ít nhất một kênh mẫu" in js
    assert 'if (!ownRef) return toast("Hãy nhập kênh của bạn"' not in js
    assert "if (profile?.plan?.plan_id)" in js
    assert "if (loadPlan)" in js
    assert "default_duration_minutes" in html
    assert "profileTodayDuration" in html
    assert "createChannelProfileSelect" in html
    assert "target_duration_minutes=" in js
    assert "selectedRadar?.profileId" in js
    assert "channel_profile_id" in js
