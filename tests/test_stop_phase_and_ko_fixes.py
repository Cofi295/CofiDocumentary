from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from documentary.codex_gateway import StageResult
from documentary.critic_loops import _KO_AI_CLICHE_RE, normalize_korean_script_orthography
from documentary.edit import EditCoordinator
from documentary.failover_gateway import FailoverGateway
from documentary.service import DocumentaryService
from documentary.voice import normalize_korean_tts_text


def test_korean_orthography_and_tts_generation_and_temperature() -> None:
    raw = "실내 온도는 늘 영하 사 도로 유지됩니다. 일세대 감식관들과 이 세대 형사, 삼세대 전담팀, 사세대 형사들이 나섰고 이 세대의 아픔을 기억했습니다."
    ortho, pairs = normalize_korean_script_orthography(raw)
    assert "영하 4도로" in ortho
    assert "1세대 감식관" in ortho
    assert "2세대 형사" in ortho
    assert "3세대 전담팀" in ortho
    assert "4세대 형사" in ortho
    assert "이 세대의 아픔" in ortho
    assert len(pairs) == 1

    tts = normalize_korean_tts_text(ortho)
    assert "영하 사도로" in tts
    assert "영하 사 도로" not in tts
    assert "일세대 감식관" in tts
    assert "사세대 형사" in tts


def test_ko_ai_cliche_detector_catches_xu_dapeng_fingerprints() -> None:
    cliches = [
        "두 자국 모두 사십이 호 보급형 고무 작업화였던 겁니다. 바닥 앞코 바깥쪽이 유독 닳아 있는 보행 습관까지 판박이처럼 포개졌습니다.",
        "수사팀은 그를 자극하지 않은 채 적법한 절차로 생체 대조 시료를 확보해 감정실로 긴급 송부했죠.",
        "밤마다 사이렌 소리만 들려도 가슴이 철렁 내려앉았다고 했습니다.",
        "네 세대의 손길을 거친 작은 물증 봉투에는 애초부터 유효기간이 존재하지 않았던 셈입니다.",
    ]
    for line in cliches:
        assert _KO_AI_CLICHE_RE.search(line) is not None, f"Expected cliché match on: {line}"

    clean = (
        "2002년 6월 25일 퉁화시 둥창구 현장의 그을음 속에서 수거한 원본 생체 검재가 "
        "2023년 4월 19일 다롄시 외곽 단칸방에 숨어 있던 미모펑을 정조준했습니다."
    )
    assert _KO_AI_CLICHE_RE.search(clean) is None


def test_stop_phase_aborts_without_failover_or_retry(tmp_path: Path) -> None:
    producer_dir = tmp_path / ".producer"
    producer_dir.mkdir(parents=True, exist_ok=True)
    stop_file = producer_dir / "stop_phase.json"
    stop_file.write_text('{"reason": "stop_phase"}', encoding="utf-8")

    codex_gw = MagicMock()
    gemini_gw = MagicMock()
    codex_gw.is_available.return_value = True
    gemini_gw.is_available.return_value = True

    gw = FailoverGateway(codex_gateway=codex_gw, gemini_gateway=gemini_gw, remotion_dir=tmp_path, enabled=True)
    res = gw.run_prompt("test", tmp_path, "edit")
    assert res.returncode == 130
    assert "stop_phase" in res.last_message
    codex_gw.run_prompt.assert_not_called()
    gemini_gw.run_prompt.assert_not_called()

    coord = EditCoordinator(codex_gateway=gw, remotion_manager=MagicMock(), remotion_dir=tmp_path)
    assert coord._is_transient_failure(res) is False
    assert coord._is_transient_failure(StageResult(1, "", producer_dir / "edit" / "events.jsonl")) is False
    assert DocumentaryService._is_non_retriable_phase_error("edit", res.last_message, res.returncode) is True
