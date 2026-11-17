from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import create_app
from documentary.service import DocumentaryService
from documentary.topic_research import _has_real_case_anchor, harvest_live_case_leads
from services.case_similarity import check_case_similarity, classify_true_crime_topic_stream
from services.preflight_service import PreflightService


REPO_ROOT = Path(__file__).resolve().parents[1]
PROD_PROFILES_PATH = REPO_ROOT / "data" / "channel_profiles.json"


class _SequencedResearchGateway:
    """Stateless mock gateway returning distinct batches per research round, plus deliberate traps."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self._batches = [
            # Round 1: includes 3 traps (already-produced Xie Renliang, slash-hedged multi-case, Japanese kana) + fresh valid cases
            {
                "candidates": [
                    {
                        "id": "trap_produced_xie",
                        "topic_stream": "financial_crime",
                        "case_real_name_zh": "浙江宁波证券公司谢仁良9150万元国债潜逃案 (1997–2015)",
                        "title": "[중국 실화 사건] 9,150만 위안 국채 증발과 18년 호주 여권 세탁 | 셰런량 사건 ([Vụ Án Có Thật ở Trung Quốc] Bốc hơi 91,5 triệu tệ công trái | Vụ Tạ Nhân Lương)",
                        "note": "Trap: already produced case Xie Renliang 谢仁良",
                    },
                    {
                        "id": "trap_slash_multi",
                        "topic_stream": "major_violent_crime",
                        "case_real_name_zh": "山西绛县金库被盗案 / 湖北潜江运钞车大案 — 张某",
                        "title": "[중국 실화 사건] 두 사건을 섞은 잘못된 후보 | 장모 사건 ([Vụ Án Có Thật ở Trung Quốc] Gộp 2 vụ án)",
                        "note": "Trap: multi-case slash hedging",
                    },
                    {
                        "id": "trap_jp_kana",
                        "topic_stream": "major_violent_crime",
                        "case_real_name_zh": "陕西西安董雷特大追捕案 (2006)",
                        "title": "[중국 실화 사건] 단 1枚の 기차표 추격전 | 둥레이 사건 ([Vụ Án Có Thật ở Trung Quốc] 1 tấm vé tàu)",
                        "note": "Trap: Japanese kana + Kanji in Korean title",
                    },
                    {
                        "id": "r1_fin_1",
                        "topic_stream": "financial_crime",
                        "case_real_name_zh": "江西鄱阳县财政局经建股9400万元贪污潜逃新加坡案 — 李华波 (2006–2015)",
                        "archival_search_keywords_zh": ["李华波 鄱阳 9400万 今日说法", "猎狐 李华波 遣返"],
                        "recommended_vox_verbs": ["LEDGER_DIFF_SCRUB", "GEO_VECTOR_PURSUIT"],
                        "title": "[중국 실화 사건] 가짜 직인 하나로 군청 예산 9,400만 위안을 빼돌린 과장의 싱가포르 도피극 | 리화보 사건 ([Vụ Án Có Thật ở Trung Quốc] Một con dấu giả rút ruột 94 triệu tệ ngân sách huyện và màn đào tẩu sang Singapore | Đại án Lý Hoa Ba)",
                        "opening_hook": "가난한 시골 현의 재정국 금고에서 구천사백만 위안이 감쪽같이 사라졌습니다.",
                        "note": "Hồ sơ thật Lý Hoa Ba (李华波) tại Bà Dương, Giang Tây (2006–2015).",
                    },
                    {
                        "id": "r1_fin_2",
                        "topic_stream": "financial_crime",
                        "case_real_name_zh": "温州建设总公司2.53亿元贪污潜逃13年红通1号案 — 杨秀珠 (2003–2016)",
                        "archival_search_keywords_zh": ["杨秀珠 红通1号 归案 央视", "杨秀珠 13年 逃亡"],
                        "recommended_vox_verbs": ["GEO_VECTOR_PURSUIT", "DUAL_ERA_LOCK"],
                        "title": "[중국 실화 사건] 6개국을 돌며 13년간 도망친 '적색수배 1호'가 네덜란드 지하실에 숨었던 이유 | 양슈주 사건 ([Vụ Án Có Thật ở Trung Quốc] Lý do 'Truy nã đỏ số 1' trốn qua 6 quốc gia suốt 13 năm phải chui xuống căn hầm ở Hà Lan | Đại án Dương Tú Châu)",
                        "opening_hook": "위조 여권으로 여섯 나라의 국경을 넘나들던 중국 적색수배 일 호 인물.",
                        "note": "Hồ sơ thật Dương Tú Châu (杨秀珠, 2003–2016).",
                    },
                    {
                        "id": "r1_vio_1",
                        "topic_stream": "major_violent_crime",
                        "case_real_name_zh": "吉林通化串并积案26年物证锁定真凶案 — 崔大钢 (1994–2020)",
                        "archival_search_keywords_zh": ["吉林通化 26年 命案积案 今日说法"],
                        "recommended_vox_verbs": ["MICRO_TRACE_MATCH", "DUAL_ERA_LOCK"],
                        "title": "[중국 실화 사건] 봉인된 증거 봉투 속 미세 흔적이 26년 뒤 지목한 이웃집 남자의 정체 | 퉁화 26년 미제사건 ([Vụ Án Có Thật ở Trung Quốc] Vết tích vi lượng trong túi niêm phong chỉ thẳng gã hàng xóm sau 26 năm | Kỳ án Thông Hóa)",
                        "opening_hook": "스물여섯 해 동안 냉동 보관실에 잠들어 있던 작은 증거물 봉투 하나가 열렸습니다.",
                        "note": "Hồ sơ thật Thông Hóa Cát Lâm (崔大钢, 1994–2020).",
                    },
                    {
                        "id": "r1_vio_2",
                        "topic_stream": "major_violent_crime",
                        "case_real_name_zh": "安徽蚌埠2002年白马湘商城19年Y-STR家系侦破悬案 — 冯亮 (2002–2021)",
                        "archival_search_keywords_zh": ["蚌埠 19年 悬案 侦破 天网"],
                        "recommended_vox_verbs": ["FORENSIC_ZOOM_CHAIN", "NETWORK_GRAPH"],
                        "title": "[중국 실화 사건] 19년 전 현장에 남은 반쪽짜리 지문이 유전자 가계도를 만나자 벌어진 일 | 벙부 19년 추적 사건 ([Vụ Án Có Thật ở Trung Quốc] Nửa dấu vân tay 19 năm trước gặp phả hệ gen đã phơi bày điều gì | Chuyên án Bạng Phụ)",
                        "opening_hook": "일만 명이 넘는 용의자를 대조하고도 풀리지 않던 십구 년 전 미제 사건.",
                        "note": "Hồ sơ thật Bạng Phụ An Huy (冯亮, 2002–2021).",
                    },
                ]
            },
            # Round 2: tries to re-suggest r1_fin_1 (Li Huabo) + brand new cases -> r1_fin_1 MUST be blocked!
            {
                "candidates": [
                    {
                        "id": "r2_repeat_lihuabo",
                        "topic_stream": "financial_crime",
                        "case_real_name_zh": "江西鄱阳县9400万元潜逃案 — 李华波 (2015)",
                        "title": "[중국 실화 사건] 9,400만 위안 빼돌린 리화보의 싱가포르 도주극 | 리화보 재등장 사건 ([Vụ Án Có Thật ở Trung Quốc] Vụ Lý Hoa Ba lặp lại)",
                        "note": "Trap: was already suggested in Round 1!",
                    },
                    {
                        "id": "r2_fin_new_1",
                        "topic_stream": "financial_crime",
                        "case_real_name_zh": "北京中国银行劲松支行金库195万元调包潜逃18年案 — 陆建荣 (1997–2015)",
                        "archival_search_keywords_zh": ["北京劲松支行 金库 18年 天网"],
                        "recommended_vox_verbs": ["BLIND_SPOT_REVEAL", "DUAL_ERA_LOCK"],
                        "title": "[중국 실화 사건] 열쇠 구멍에 흠집 하나 없이 증발한 은행 금고 현금 자루와 18년의 잠적 | 베이징 진쑹 금고 사건 ([Vụ Án Có Thật ở Trung Quốc] Bao tiền mặt bốc hơi khỏi két sắt không một vết xước ổ khóa và 18 năm lẩn trốn | Vụ két sắt Bắc Kinh)",
                        "opening_hook": "아침 출근길에 은행 지하 금고를 연 직원들은 눈앞의 광경에 얼어붙었습니다.",
                        "note": "Hồ sơ thật két sắt Bắc Kinh (陆建荣, 1997–2015).",
                    },
                    {
                        "id": "r2_vio_new_1",
                        "topic_stream": "major_violent_crime",
                        "case_real_name_zh": "浙江舟山孤岛悬案22年船票记录与Y-STR家系侦破纪实 — 蒋明 (1998–2020)",
                        "archival_search_keywords_zh": ["浙江舟山 22年 悬案 今日说法"],
                        "recommended_vox_verbs": ["BLIND_SPOT_REVEAL", "GEO_VECTOR_PURSUIT"],
                        "title": "[중국 실화 사건] 배가 끊긴 고립된 섬에서 증발한 용의자… 22년 뒤 잡힌 유전자 단서 | 저우산 고도 미제사건 ([Vụ Án Có Thật ở Trung Quốc] Nghi phạm bốc hơi khỏi hòn đảo cô lập | Kỳ án Chu Sơn)",
                        "opening_hook": "풍랑주의보로 마지막 여객선마저 끊긴 작은 바위섬에서 용의자가 흔적 없이 사라졌습니다.",
                        "note": "Hồ sơ thật Chu Sơn Chiết Giang (蒋明, 1998–2020).",
                    },
                ]
            },
        ]

    def run_prompt(self, prompt: str, workspace: Any, label: str, **_: Any) -> Any:
        idx = min(len(self.calls), len(self._batches) - 1)
        self.calls.append((label, prompt))
        return SimpleNamespace(returncode=0, last_message=json.dumps(self._batches[idx], ensure_ascii=False))


def _make_isolated_service(tmp_path: Path) -> tuple[DocumentaryService, str]:
    root = tmp_path / "app_root"
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "jobs").mkdir(parents=True, exist_ok=True)

    prod_raw = json.loads(PROD_PROFILES_PATH.read_text(encoding="utf-8"))
    copied_profiles = []
    for p in prod_raw["profiles"]:
        cp = copy.deepcopy(p)
        if cp.get("id") == "channel-e544a64b7c":
            # Start clean history for deterministic round-by-round testing while keeping full topic_memory
            cp["suggested_topic_history"] = []
            cp["topic_research_round"] = 0
        copied_profiles.append(cp)
    (data_dir / "channel_profiles.json").write_text(
        json.dumps({"profiles": copied_profiles}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    prod_pools = REPO_ROOT / "data" / "dna_topic_pools.json"
    if prod_pools.exists():
        (data_dir / "dna_topic_pools.json").write_text(
            prod_pools.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    gw = _SequencedResearchGateway()
    svc = DocumentaryService(root, codex_gateway=gw)
    return svc, "channel-e544a64b7c"


def test_truecrime_profiles_have_clean_stream_dna_and_green_dollar_hygiene() -> None:
    import re
    from documentary.prompts import EPISODE_OPENING_ARCHETYPES, _rank_topic_fitted_opening_archetypes
    from documentary.thumbnail_studio import YOUTUBE_POLICY_REPLACEMENTS_ALL
    from documentary.topic_research import VERIFIED_TWO_STREAM_RESERVE_CASES

    data = json.loads(PROD_PROFILES_PATH.read_text(encoding="utf-8"))
    profiles = {p["id"]: p for p in data.get("profiles", [])}

    # 1. Legacy 2-stream profile channel-e544a64b7c keeps both streams
    leg_prof = profiles["channel-e544a64b7c"]
    assert {s.get("id") for s in (leg_prof.get("topic_streams") or [])} == {"financial_crime", "major_violent_crime"}
    assert leg_prof.get("locked_single_stream") is None

    # 2. Stream 1 independent channel owns financial + vault break-in + safe-cracking + cash-in-transit heists
    fin_prof = profiles["channel-kr-financial-fugitive-director-v2"]
    assert fin_prof.get("locked_single_stream") == "financial_crime"
    assert {s.get("id") for s in (fin_prof.get("topic_streams") or [])} == {"financial_crime"}

    # 3. Stream 2 independent channel is locked 100% to pure major_violent_crime (0% vault/safe/cash heists)
    vio_prof = profiles["channel-kr-truecrime-director-v2"]
    assert vio_prof.get("locked_single_stream") == "major_violent_crime"
    assert {s.get("id") for s in (vio_prof.get("topic_streams") or [])} == {"major_violent_crime"}

    # 4. Verify vault/safe-cracking/cash-in-transit/bank robberies route 100% to Stream 1
    for vault_sample in (
        "산소절단기 하나로 9년간 은행 금고만 골라 뚫은 단독범 | 레이궈민 사건",
        "청진기 하나로 다이얼 소리를 읽던 대형 금고 털이범",
        "현금수송차 79만 위안을 털고 사라진 주범 | 자오즈용 사건",
        "고원 지대에서 순금 48kg을 강탈한 주범",
        "đột nhập kho bạc mở két sắt cướp xe chở tiền",
    ):
        assert classify_true_crime_topic_stream(vault_sample) == "financial_crime"

    pf = PreflightService(profiles_file=PROD_PROFILES_PATH, jobs_dir=REPO_ROOT / "data" / "jobs")
    # Stream 1 accepts vault/safe/cash heist; Stream 2 rejects vault/safe/cash heist and accepts pure cold case
    vault_topic = {
        "title": "[중국 실화 사건] 청진기 하나로 대형 금고 다이얼을 연 유령 기술자 | 포산 금고 개방 사건",
        "topic": "Đột nhập kho bạc mở két sắt Phật Sơn",
    }
    assert pf.check(fin_prof, "topic", vault_topic)["preflight_summary"]["passed"] is True
    assert pf.check(vio_prof, "topic", vault_topic)["preflight_summary"]["passed"] is False

    cold_case_topic = {
        "title": "[중국 실화 사건] 봉인된 증거 봉투 속 미세 흔적이 26년 뒤 지목한 이웃집 남자의 정체 | 퉁화 26년 미제사건",
        "topic": "Trọng án án lạnh pháp y Thông Hóa Cát Lâm 崔某钢",
    }
    assert pf.check(vio_prof, "topic", cold_case_topic)["preflight_summary"]["passed"] is True

    # Both profiles block forbidden dam/infrastructure topics
    for prof in (fin_prof, vio_prof, leg_prof):
        dam_res = pf.check(
            prof,
            "topic",
            {"title": "중국 삼협댐 붕괴 위기와 남수북조 프로젝트", "topic": "đập Tam Hiệp"},
        )
        assert dam_res["preflight_summary"]["passed"] is False

    # 5. Verify canonical Winner Opening Hook Archetype resolves cleanly
    assert len(EPISODE_OPENING_ARCHETYPES) >= 1
    r_vault = _rank_topic_fitted_opening_archetypes({"title": "흠집 하나 없이 열린 지하 금고 미스터리", "notes": "밀실 금고"})
    assert r_vault[0]["id"] in {item["id"] for item in EPISODE_OPENING_ARCHETYPES}

    # 6. Verify 100% Broadcast Green-Dollar cleanliness across reserve vault & policy replacements (15/07/2025 - Present YouTube Policy)
    yellow_re = re.compile(
        r"(생명을\s*앗아|목숨을\s*앗아|운명을\s*앗아|생명을\s*빼앗|살인|살해|사망|숨진|시신|시체|사체|백골|토막|참수|피투성이|혈흔|핏자국|총성|총격|총살|사형|흉기|자살|극단적\s*선택|성폭행|강간|고문|엽기|đoạt\s+mạng|tước\s+đoạt\s+(?:\d+\s+|hàng\s+loạt\s+|nhiều\s+)?sinh\s+mạng|sát\s+hại|giết\s+người|xác\s+chết|thi\s+thể)",
        re.IGNORECASE,
    )
    for c in VERIFIED_TWO_STREAM_RESERVE_CASES:
        assert not yellow_re.search(c["title"]), f"Yellow-dollar / life-taking phrase in public reserve title {c['id']}: {c['title']}"
        assert not yellow_re.search(c.get("topic_anchor", "")), f"Yellow-dollar / life-taking phrase in topic_anchor {c['id']}: {c.get('topic_anchor')}"
        assert not yellow_re.search(c["opening_hook"]), f"Yellow-dollar word in reserve hook {c['id']}: {c['opening_hook']}"
        assert "【Hồ sơ vụ án:" in c.get("note", ""), f"Internal dossier popup note missing 【Hồ sơ vụ án: ...】 in {c['id']}"
    for _, safe_dst in YOUTUBE_POLICY_REPLACEMENTS_ALL:
        assert not yellow_re.search(safe_dst), f"Policy replacement target itself has yellow-dollar term: {safe_dst}"


def test_real_case_anchor_gate_blocks_slash_hedging_and_mixed_scripts() -> None:
    assert _has_real_case_anchor({
        "case_real_name_zh": "山西绛县金库案 / 湖北潜江运钞车案 — 张某",
        "title": "[중국 실화 사건] 금고 사건 | 장모 사건 ([Vụ Án Có Thật ở Trung Quốc] Vụ án)",
    }) is False
    assert _has_real_case_anchor({
        "case_real_name_zh": "陕西西安董雷案 (2006)",
        "title": "[중국 실화 사건] 1枚の 기차표 | 둥레이 사건 ([Vụ Án Có Thật ở Trung Quốc] Vụ án)",
    }) is False
    assert _has_real_case_anchor({
        "case_real_name_zh": "公安部缅北明学昌案 (2023)",
        "title": "[중국 실화 사건] 국경 밖 금고의 실체 | 밍학창 사건 ([Vụ Án Có Thật ở Trung Quốc] Thực체 kho tiền)",
    }) is False
    # Single person with lay name / monk name is allowed
    assert _has_real_case_anchor({
        "case_real_name_zh": "黑龙江大庆命案逃犯潜逃16年变身龙兴寺住持案 — 张立伟 / 释广闻 (2000–2017)",
        "title": "[중국 실화 사건] 600년 고찰 주지 스님의 두 얼굴 | 장리웨이 사건 ([Vụ Án Có Thật ở Trung Quốc] Hai bộ mặt của Trương Lập Vĩ)",
    }) is True


def test_consecutive_refreshes_research_new_topics_and_never_repeat(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "documentary.topic_research.harvest_live_case_leads",
        lambda **kwargs: [{"stream_hint": "financial_crime", "title": "江西鄱阳李华波9400万案", "snippet": "央视今日说法纪实"}],
    )
    svc, pid = _make_isolated_service(tmp_path)
    prof = svc.get_channel_profile(pid)
    produced_memory = list(prof.get("topic_memory") or [])
    assert len(produced_memory) >= 20

    # Round 1 live refresh
    r1 = svc.channel_profile_today(pid, target_duration_minutes=27, discovery_mode="dna_strict", force_refresh=True, topic_stream="all")
    r1_titles = [c["title"] for c in r1["today"]]
    r1_zh = [c.get("case_real_name_zh", "") for c in r1["today"]]
    assert r1["is_two_stream_profile"] is True
    assert r1["streams_summary"]["financial_crime"] >= 4
    assert r1["streams_summary"]["major_violent_crime"] >= 4

    # Traps from Round 1 must be 100% absent
    joined_r1 = " ".join(r1_titles + r1_zh)
    assert "谢仁良" not in joined_r1 and "셰런량" not in joined_r1
    assert "1枚の" not in joined_r1
    assert "山西绛县金库被盗案 / 湖北潜江" not in joined_r1
    # Valid live AI items from Round 1 must be present
    assert any("리화보" in t for t in r1_titles)
    assert any("양슈주" in t for t in r1_titles)

    # Zero overlap with produced topic_memory
    for cand in r1["today"]:
        probe = f"{cand['title']} {cand.get('case_real_name_zh', '')}"
        for mem in produced_memory:
            is_dup, _, _ = check_case_similarity(probe, str(mem.get("title") or ""), target_topic=str(mem.get("topic") or ""))
            assert not is_dup, f"Candidate {probe} collided with produced memory {mem.get('title')}"

    # Round 2 live refresh: must NOT repeat ANY item from Round 1 (including trap r2_repeat_lihuabo!)
    r2 = svc.channel_profile_today(pid, target_duration_minutes=27, discovery_mode="dna_strict", force_refresh=True, topic_stream="all")
    r2_titles = [c["title"] for c in r2["today"]]
    assert not any("리화보" in t for t in r2_titles), "Li Huabo from Round 1 was repeated in Round 2!"
    for c2 in r2["today"]:
        p2 = f"{c2['title']} {c2.get('case_real_name_zh', '')}"
        for c1 in r1["today"]:
            p1 = f"{c1['title']} {c1.get('case_real_name_zh', '')}"
            assert not check_case_similarity(p2, c1["title"], target_topic=p1)[0], f"Round 2 repeated Round 1 item: {p2}"


def test_stream_filtering_and_clear_suggested_history_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("documentary.topic_research.harvest_live_case_leads", lambda **kwargs: [])
    svc, pid = _make_isolated_service(tmp_path)
    client = TestClient(create_app(svc))

    fin_resp = client.post(
        f"/api/radar/channel-profiles/{pid}/today?discovery_mode=dna_strict&force_refresh=true&topic_stream=financial_crime",
        json={"exclude_titles": [], "topic_stream": "financial_crime"},
    )
    assert fin_resp.status_code == 200
    fin_data = fin_resp.json()
    assert len(fin_data["today"]) >= 4
    assert all(c["topic_stream"] == "financial_crime" for c in fin_data["today"])

    vio_resp = client.post(
        f"/api/radar/channel-profiles/{pid}/today?discovery_mode=dna_strict&force_refresh=true&topic_stream=major_violent_crime",
        json={"exclude_titles": [], "topic_stream": "major_violent_crime"},
    )
    assert vio_resp.status_code == 200
    vio_data = vio_resp.json()
    assert len(vio_data["today"]) >= 4
    assert all(c["topic_stream"] == "major_violent_crime" for c in vio_data["today"])

    # Clear suggested history without touching topic_memory
    mem_before = len(svc.get_channel_profile(pid).get("topic_memory") or [])
    del_resp = client.delete(f"/api/radar/channel-profiles/{pid}/suggested-topic-history")
    assert del_resp.status_code == 200
    assert del_resp.json()["suggested_history_count"] == 0
    mem_after = len(svc.get_channel_profile(pid).get("topic_memory") or [])
    assert mem_after == mem_before and mem_after >= 20


def test_frontend_app_js_no_longer_rotates_static_pool() -> None:
    app_js = (REPO_ROOT / "static" / "app.js").read_text(encoding="utf-8")
    assert "_dnaRotateOffset" not in app_js
    assert "dna_topic_pools.json" not in app_js
    assert "createTopicStreamBar" in app_js
    assert "financial_crime" in app_js
    assert "major_violent_crime" in app_js
    assert "suggested-topic-history" in app_js


def test_comma_number_normalization_and_no_spurious_zero_metric_collision() -> None:
    # 3,000미터 Guizhou Karst bridges must NOT collide with 4,000미터 Sichuan-Tibet railway
    guizhou = "해발 3,000미터 절벽과 카르스트 동굴 위에 세운 구이저우 초고층 대교들"
    sichuan_tibet = "해발 4,000미터 활성 단층대를 뚫는 쓰촨-티베트 철도의 극한 공학"
    is_dup, score, _ = check_case_similarity(guizhou, sichuan_tibet)
    assert is_dup is False, f"Guizhou 3,000m bridge falsely matched Sichuan-Tibet 4,000m railway (score={score})"

    # Baiyin 28-year + DNA genealogy must NOT falsely trigger Xiaoshan 28-year taxi cluster
    baiyin = "중국에서 붉은 옷 입은 여성 11명을 노린 악마 | 28년간 고등학교 매점에 숨어 웃고 있었다 유전자 족보"
    xiaoshan = "1995년 샤오산 택시 미제사건 28년 만에 담배꽁초 유전자 족보로 잡힌 항생원"
    assert check_case_similarity(baiyin, xiaoshan)[0] is False

    # Comma vs non-comma numbers in Korean/Vietnamese must match identically
    handan_a = "은행 지하 금고 현금 5,100만 위안으로 복권을 사 모은 두 금고지기 | 한단 농협 금고 사건"
    handan_b = "5100만 위안 금고 현금 복권 구매 사건 — 임소봉(任晓峰)"
    assert check_case_similarity(handan_a, handan_b)[0] is True


def test_production_channel_profiles_zero_duplicates_in_memory_and_curated() -> None:
    from services.channel_profile_service import ChannelProfileService

    raw = json.loads((REPO_ROOT / "data" / "channel_profiles.json").read_text(encoding="utf-8"))
    profiles = raw.get("profiles") if isinstance(raw, dict) else raw
    assert isinstance(profiles, list) and len(profiles) >= 3

    for p in profiles:
        pid = str(p.get("id") or "")
        mem = list(p.get("topic_memory") or [])
        cur = list(p.get("curated_today_candidates") or [])

        # 1. Zero duplicate entries inside topic_memory
        _, mem_had_dups = ChannelProfileService._deduplicate_topic_memory_list(mem)
        assert mem_had_dups is False, f"Profile {pid} still has duplicate entries in topic_memory"

        # 2. Zero internal duplicates inside curated_today_candidates
        for i in range(len(cur)):
            for j in range(i + 1, len(cur)):
                b1 = f"{cur[i].get('title', '')} {cur[i].get('case_real_name_zh', '')} {cur[i].get('note', '')}"
                b2 = f"{cur[j].get('title', '')} {cur[j].get('case_real_name_zh', '')} {cur[j].get('note', '')}"
                is_dup, _, reason = check_case_similarity(b1, str(cur[j].get("title") or ""), target_topic=b2)
                assert not is_dup, f"Profile {pid} has internal curated duplicate: {cur[i].get('id')} vs {cur[j].get('id')} ({reason})"

        # 3. Zero overlap between curated_today_candidates and topic_memory
        for c in cur:
            b1 = f"{c.get('title', '')} {c.get('case_real_name_zh', '')} {c.get('note', '')}"
            for m in mem:
                is_dup, _, reason = check_case_similarity(
                    b1,
                    str(m.get("title") or ""),
                    target_topic=str(m.get("topic") or ""),
                    target_entities=list(m.get("tags") or []),
                    target_keywords=list(m.get("anchors") or []),
                )
                assert not is_dup, f"Profile {pid} curated item {c.get('id')} collides with topic_memory {m.get('id')} ({reason})"

    # 4. Zero active curated candidate overlap across all 3 sibling KR True-Crime profiles
    p_map = {str(p.get("id")): p for p in profiles}
    tc_siblings = [
        pid
        for pid in ("channel-e544a64b7c", "channel-kr-truecrime-director-v2", "channel-kr-financial-fugitive-director-v2")
        if pid in p_map
    ]
    for idx_a in range(len(tc_siblings)):
        for idx_b in range(idx_a + 1, len(tc_siblings)):
            pid_a, pid_b = tc_siblings[idx_a], tc_siblings[idx_b]
            c1 = p_map[pid_a].get("curated_today_candidates") or []
            c2 = p_map[pid_b].get("curated_today_candidates") or []
            for x in c1:
                bx = f"{x.get('title', '')} {x.get('case_real_name_zh', '')} {x.get('note', '')}"
                for y in c2:
                    by = f"{y.get('title', '')} {y.get('case_real_name_zh', '')} {y.get('note', '')}"
                    assert not check_case_similarity(
                        bx,
                        str(y.get("title") or ""),
                        target_topic=by,
                        candidate_id=str(x.get("id") or ""),
                        target_candidate_id=str(y.get("id") or ""),
                    )[0], (
                        f"Sibling profiles {pid_a} and {pid_b} share duplicate curated candidate: {x.get('id')} vs {y.get('id')}"
                    )

    # 5. Verify independent Stream 1 channel profile vs Stream 2 channel profile
    assert "channel-kr-financial-fugitive-director-v2" in p_map
    fin_p = p_map["channel-kr-financial-fugitive-director-v2"]
    vio_p = p_map["channel-kr-truecrime-director-v2"]
    assert fin_p.get("default_topic_stream") == "financial_crime"
    assert fin_p.get("locked_single_stream") == "financial_crime"
    assert fin_p.get("own_channel_ref") == ""
    assert all(c.get("topic_stream") == "financial_crime" for c in (fin_p.get("curated_today_candidates") or []))
    assert vio_p.get("default_topic_stream") == "major_violent_crime"
    assert vio_p.get("locked_single_stream") == "major_violent_crime"
    assert all(c.get("topic_stream") == "major_violent_crime" for c in (vio_p.get("curated_today_candidates") or []))


def test_selecting_final_topic_auto_prunes_saves_memory_and_replenishes_one_new_topic(tmp_path: Path) -> None:
    """
    When a final topic is chosen for production:
    1) Automatically removed from active curated_today_candidates (and sibling profiles).
    2) Saved into topic_memory with rich anti-duplicate anchors (candidate_id, case_real_name_zh, pipe_case_tag) across siblings.
    3) Automatically replenished with +1 brand-new unproduced topic restoring full list count.
    """
    svc, pid = _make_isolated_service(tmp_path)
    prof_before = svc.get_channel_profile(pid)
    curated_before = list(prof_before.get("curated_today_candidates") or [])
    assert len(curated_before) >= 10
    chosen = curated_before[0]
    chosen_id = str(chosen.get("id") or "")
    chosen_title = str(chosen.get("title") or "")
    before_ids = {str(x.get("id") or "") for x in curated_before}

    created_job = svc.create_job(
        {
            "title": chosen_title,
            "topic": chosen_title,
            "channel_profile_id": pid,
            "target_duration_minutes": 27,
            "notes": str(chosen.get("note") or ""),
            "topic_discovery": {
                "source": "channel_profile_today",
                "profile_id": pid,
                "selected_candidate": {
                    "id": chosen_id,
                    "title": chosen_title,
                    "case_real_name_zh": chosen.get("case_real_name_zh"),
                    "topic_stream": chosen.get("topic_stream"),
                },
            },
        },
        start_plan=False,
    )

    mem_sync = created_job.get("topic_memory_sync") or {}
    assert mem_sync.get("candidate_id") == chosen_id
    assert mem_sync.get("removed_from_curated_count", 0) >= 1
    assert mem_sync.get("replenished_count", 0) >= 1
    assert len(mem_sync.get("replenished_candidates") or []) >= 1

    prof_after = svc.get_channel_profile(pid)
    curated_after = list(prof_after.get("curated_today_candidates") or [])
    after_ids = {str(x.get("id") or "") for x in curated_after}

    # Chosen topic must be 100% gone from curated list
    assert chosen_id not in after_ids
    assert not any(
        check_case_similarity(
            f"{c.get('title')} {c.get('case_real_name_zh')}",
            chosen_title,
            target_topic=str(chosen.get("case_real_name_zh") or ""),
            candidate_id=str(c.get("id") or ""),
            target_candidate_id=chosen_id,
        )[0]
        for c in curated_after
    )
    # Count restored with at least +1 newly replenished topic
    assert len(curated_after) == len(curated_before)
    newly_added_ids = after_ids - before_ids
    assert len(newly_added_ids) >= 1

    # Sibling profiles must ALSO remember the produced topic so they never suggest it
    for sib_id in ("channel-kr-truecrime-director-v2", "channel-kr-financial-fugitive-director-v2"):
        try:
            sib_prof = svc.get_channel_profile(sib_id)
        except KeyError:
            continue
        sib_mem = list(sib_prof.get("topic_memory") or [])
        assert any(
            check_case_similarity(
                f"{chosen_title} {chosen.get('case_real_name_zh') or ''}",
                str(m.get("title") or ""),
                target_topic=f"{m.get('topic') or ''} {m.get('case_real_name_zh') or ''}",
                target_entities=list(m.get("tags") or []),
                target_keywords=list(m.get("anchors") or []),
                candidate_id=chosen_id,
                target_candidate_id=str(m.get("candidate_id") or ""),
            )[0]
            for m in sib_mem
        ), f"Sibling {sib_id} did not receive synced topic_memory for {chosen_id}"


def test_non_truecrime_profile_auto_prunes_and_replenishes_one_new_topic(tmp_path: Path) -> None:
    """
    Verify non-True-Crime channels (e.g. channel-vn-cn-fraud-lab, channel-cn-cyber-finance-kr)
    also automatically remove a selected topic, save anti-duplicate memory, and replenish +1 new topic.
    """
    svc, _ = _make_isolated_service(tmp_path)
    pid = "channel-vn-cn-fraud-lab"
    prof_before = svc.get_channel_profile(pid)
    curated_before = list(prof_before.get("curated_today_candidates") or [])
    assert len(curated_before) >= 5
    chosen = curated_before[0]
    chosen_id = str(chosen.get("id") or "")
    chosen_title = str(chosen.get("title") or "")
    before_ids = {str(x.get("id") or "") for x in curated_before}

    created_job = svc.create_job(
        {
            "title": chosen_title,
            "topic": chosen_title,
            "channel_profile_id": pid,
            "target_duration_minutes": 5,
            "notes": str(chosen.get("note") or ""),
            "topic_discovery": {
                "source": "channel_profile_today",
                "profile_id": pid,
                "selected_candidate": {
                    "id": chosen_id,
                    "title": chosen_title,
                    "case_real_name_zh": chosen.get("case_real_name_zh"),
                },
            },
        },
        start_plan=False,
    )

    mem_sync = created_job.get("topic_memory_sync") or {}
    assert mem_sync.get("candidate_id") == chosen_id
    assert mem_sync.get("removed_from_curated_count", 0) >= 1
    assert mem_sync.get("replenished_count", 0) >= 1

    prof_after = svc.get_channel_profile(pid)
    curated_after = list(prof_after.get("curated_today_candidates") or [])
    after_ids = {str(x.get("id") or "") for x in curated_after}
    assert chosen_id not in after_ids
    assert len(curated_after) == len(curated_before)
    assert len(after_ids - before_ids) >= 1




