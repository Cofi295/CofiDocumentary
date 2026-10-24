from vendor.media_factory.backend.app.providers.base import ProviderError
from vendor.media_factory.backend.app.providers.google import GoogleFlowSessionProvider
from vendor.media_factory.backend.app.providers.google_flow_migrated import _flow_public_error_codes
from documentary.ai_visual import AIVisualCoordinator


def test_flow_public_error_codes_extracts_unusual_activity_reply() -> None:
    text = ")]}\'\n229\n[[\"wrb.fr\",\"eb1hJf\",null,null,null,[7,null,[[\"type.googleapis.com/google.rpc.ErrorInfo\",[\"PUBLIC_ERROR_UNUSUAL_ACTIVITY\"]]]],\"generic\"]]"

    assert _flow_public_error_codes(text) == ("PUBLIC_ERROR_UNUSUAL_ACTIVITY",)


def test_unusual_activity_reply_is_treated_as_verification_challenge() -> None:
    exc = ProviderError("Google Flow submit rejected: PUBLIC_ERROR_UNUSUAL_ACTIVITY")

    assert GoogleFlowSessionProvider._is_recaptcha_challenge(exc) is True


def test_video_prompt_uses_safe_generic_motion_without_real_person_name() -> None:
    prompt = AIVisualCoordinator._video_prompt(
        {
            "narration_text": "이 위험한 집착의 뿌리는 100년 전 쑨원의 손끝에서 시작되었습니다.",
            "framing_motion_intent": "고풍스러운 책장 넘김과 쑨원의 결연한 눈빛으로 서서히 줌인",
        }
    )

    assert "쑨원" not in prompt
    assert "Narration:" not in prompt
    assert "Preserve identity" not in prompt
    assert "non-identifiable" in prompt
    assert "push-in" in prompt
