from __future__ import annotations

from dataclasses import dataclass
import io
import os
from typing import Any

import httpx


def _flag(name: str, default: bool = True) -> bool:
    raw = str(os.getenv(name, "1" if default else "0") or "").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _cosine_to_unit(value: float) -> float:
    return _clamp((float(value) + 1.0) / 2.0)


@dataclass
class OpenClipSemanticReranker:
    """Rerank source candidates by narration/text and preview-image semantics.

    The model is loaded lazily so application startup never depends on model
    downloads. Failure is fail-open: discovery keeps the metadata ranking and
    the final Codex/Gemini media review remains authoritative.
    """

    model_name: str | None = None
    pretrained: str | None = None
    device: str | None = None
    client: httpx.Client | None = None

    def __post_init__(self) -> None:
        self.enabled = _flag("COFI_OPENCLIP_ENABLED", True)
        # Source discovery already has a later stage that downloads/cuts the
        # real media before Gemini/Codex vision review. Pulling every remote
        # thumbnail again here makes the semantic prefilter network-bound and
        # repeats the same previews across many beats. Keep OpenCLIP text
        # semantics on by default; visual preview scoring is opt-in.
        self.visual_preview_enabled = _flag("COFI_OPENCLIP_VISUAL_PREVIEW_ENABLED", False)
        self.model_name = str(self.model_name or os.getenv("COFI_OPENCLIP_MODEL") or "ViT-B-32").strip()
        self.pretrained = str(
            self.pretrained or os.getenv("COFI_OPENCLIP_PRETRAINED") or "laion2b_s34b_b79k"
        ).strip()
        self.device = str(self.device or os.getenv("COFI_OPENCLIP_DEVICE") or "cpu").strip()
        self.client = self.client or httpx.Client(
            timeout=max(2.0, float(os.getenv("COFI_OPENCLIP_PREVIEW_TIMEOUT_SEC", "8") or 8)),
            follow_redirects=True,
            headers={"User-Agent": "COFI-Documentary/1.0 semantic-preview"},
        )
        self._model: Any | None = None
        self._preprocess: Any | None = None
        self._tokenizer: Any | None = None
        self._load_error = ""

    def health(self) -> dict[str, Any]:
        if not self.enabled:
            return {"ok": True, "provider": "openclip", "enabled": False, "mode": "metadata-only"}
        try:
            import open_clip  # noqa: F401
            import torch  # noqa: F401
            from PIL import Image  # noqa: F401
        except Exception as exc:
            return {
                "ok": False,
                "provider": "openclip",
                "enabled": True,
                "model": self.model_name,
                "error": f"{type(exc).__name__}: {exc}",
            }
        return {
            "ok": True,
            "provider": "openclip",
            "enabled": True,
            "model": self.model_name,
            "pretrained": self.pretrained,
            "device": self.device,
            "loaded": self._model is not None,
            "load_error": self._load_error,
            "visual_preview_enabled": self.visual_preview_enabled,
        }

    def _ensure_model(self) -> bool:
        if not self.enabled:
            return False
        if self._model is not None:
            return True
        if self._load_error:
            return False
        try:
            import open_clip

            model, _, preprocess = open_clip.create_model_and_transforms(
                self.model_name,
                pretrained=self.pretrained,
                device=self.device,
            )
            model.eval()
            self._model = model
            self._preprocess = preprocess
            self._tokenizer = open_clip.get_tokenizer(self.model_name)
            return True
        except Exception as exc:
            self._load_error = f"{type(exc).__name__}: {exc}"
            return False

    @staticmethod
    def _query_text(context: dict[str, Any]) -> str:
        values = [
            context.get("narration_text"),
            context.get("visual_description"),
            context.get("purpose"),
            context.get("query"),
        ]
        return " ".join(str(value or "").strip() for value in values if str(value or "").strip())[:1800]

    @staticmethod
    def _candidate_text(candidate: dict[str, Any]) -> str:
        values = [
            candidate.get("title"),
            candidate.get("description"),
            candidate.get("source_name"),
            candidate.get("date"),
        ]
        return " ".join(str(value or "").strip() for value in values if str(value or "").strip())[:1800]

    @staticmethod
    def _preview_url(candidate: dict[str, Any]) -> str:
        preview = str(candidate.get("thumbnail_url") or "").strip()
        if preview:
            return preview
        kind = str(candidate.get("kind") or "").lower()
        url = str(candidate.get("source_url") or "").strip()
        if kind == "still" and url:
            return url
        return ""

    def _preview_image(self, url: str) -> Any | None:
        if not url:
            return None
        try:
            response = self.client.get(url)
            response.raise_for_status()
            if len(response.content) > 8 * 1024 * 1024:
                return None
            from PIL import Image

            return Image.open(io.BytesIO(response.content)).convert("RGB")
        except Exception:
            return None

    def rerank(
        self,
        query_context: dict[str, Any],
        candidates: list[dict[str, Any]],
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        rows = [dict(item) for item in candidates if isinstance(item, dict)]
        if not rows:
            return rows[:limit] if limit else rows
        if not self._ensure_model():
            return rows[:limit] if limit else rows

        query = self._query_text(query_context)
        if not query:
            return rows[:limit] if limit else rows

        import torch

        assert self._model is not None
        assert self._preprocess is not None
        assert self._tokenizer is not None

        candidate_texts = [self._candidate_text(item) or str(item.get("search_query") or "") for item in rows]
        with torch.inference_mode():
            query_tokens = self._tokenizer([query]).to(self.device)
            candidate_tokens = self._tokenizer(candidate_texts).to(self.device)
            query_feature = self._model.encode_text(query_tokens)
            text_features = self._model.encode_text(candidate_tokens)
            query_feature = query_feature / query_feature.norm(dim=-1, keepdim=True)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            text_scores = (text_features @ query_feature.T).squeeze(-1).detach().cpu().tolist()

        for index, item in enumerate(rows):
            text_score = _cosine_to_unit(float(text_scores[index]))
            visual_score: float | None = None
            image = self._preview_image(self._preview_url(item)) if self.visual_preview_enabled else None
            if image is not None:
                try:
                    image_tensor = self._preprocess(image).unsqueeze(0).to(self.device)
                    with torch.inference_mode():
                        image_feature = self._model.encode_image(image_tensor)
                        image_feature = image_feature / image_feature.norm(dim=-1, keepdim=True)
                        raw_visual = float((image_feature @ query_feature.T).squeeze().detach().cpu().item())
                    visual_score = _cosine_to_unit(raw_visual)
                except Exception:
                    visual_score = None

            if visual_score is None:
                semantic_score = text_score
            else:
                semantic_score = text_score * 0.58 + visual_score * 0.42
            item["semantic_score"] = round(_clamp(semantic_score), 4)
            item["semantic_text_score"] = round(text_score, 4)
            if visual_score is not None:
                item["visual_semantic_score"] = round(visual_score, 4)
            item["semantic_provider"] = "openclip"

        rows.sort(
            key=lambda item: (
                float(item.get("semantic_score") or 0.0),
                float(item.get("discovery_score") or 0.0),
            ),
            reverse=True,
        )
        return rows[:limit] if limit else rows
