"""COFI Producer AI orchestration layer.

Connects expert memory and video criticism into one production review step.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .expert_evolution import ExpertEvolutionEngine
from .video_critic import critic_report
from .master_youtube_agent import MasterYouTubeAgent
from .permission_gateway import PermissionGateway


class CofiProducerAI:
    def __init__(self, root: Path | None = None):
        self.root = root or Path(__file__).resolve().parent
        self.expert = ExpertEvolutionEngine(self.root)
        self.master = MasterYouTubeAgent(self.root)
        self.permissions = PermissionGateway(self.root)

    @classmethod
    def role_profile(cls) -> dict[str, Any]:
        return {
            "name": "COFI Production Coordinator",
            "role": "Trợ lý điều phối COFI DOCUMENTARY",
            "title": "Production Operations Assistant / Producer AI / Đạo diễn sản xuất",
            "mission": "Vận hành trọn vẹn quy trình sản xuất video 8 bước: nghiên cứu, kịch bản, voice, visuals, footage, AI visual, dựng video, QC & xuất bản",
            "stages": [
                {"step": 1, "id": "plan", "label": "Nghiên cứu / Radar"},
                {"step": 2, "id": "script", "label": "Kịch bản"},
                {"step": 3, "id": "voice", "label": "Voice & SRT"},
                {"step": 4, "id": "visuals", "label": "Visuals / Phân cảnh"},
                {"step": 5, "id": "footage", "label": "Tư liệu / Footage"},
                {"step": 6, "id": "ai_visual", "label": "AI visual bổ sung"},
                {"step": 7, "id": "edit", "label": "Dựng video / Edit"},
                {"step": 8, "id": "qc", "label": "QC & Xuất video"},
            ],
            "execution_policy": "Luôn thực thi hành động qua action/runtime khi nhận lệnh; không hứa hẹn suông bằng chữ; kế thừa ngữ cảnh gần nhất cho các câu ngắn như 'chạy nốt đi', 'làm đi'.",
        }

    def review_production(self, video: dict[str, Any]) -> dict[str, Any]:
        critic = critic_report(video)
        evolution = self.expert.review_video(video)
        return {
            "role_profile": self.role_profile(),
            "producer_profile": self.expert.profile(),
            "critic": critic,
            "evolution": evolution,
            "ready": critic["approved"] and evolution["score"] >= 70,
            "master_agent": self.master.capabilities(),
            "permissions": self.permissions.get_permissions(),
        }

