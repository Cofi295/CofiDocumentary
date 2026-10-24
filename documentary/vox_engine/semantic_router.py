"""True Crime Vox & Real Satellite Semantic Scene Router.

Analyzes spoken voice narration (Korean / Vietnamese) to semantically select matching
True Crime archetypes (#M1..#M8, #D1..#D10, #P1..#P6, cinema_full) with dynamic sliding-window
anti-repetition protection and strict channel profile isolation to channel-e544a64b7c.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


VOX_ARCHETYPE_RULES: dict[str, dict[str, Any]] = {
    "#D4": {
        "cluster": "biometrics",
        "label": "Y-STR DNA Lightbox & Clan Pedigree Tree",
        "regex_ko": r"(Y-염색체|유전자|족보|가문|DNA|부계|혈통|친척|가오씨|대조\s*검사|염색체|가계도)",
        "regex_vi": r"(Y-STR|nhiễm\s*sắc\s*thể\s*Y|ADN\s*dòng\s*họ|phả\s*hệ|gia\s*tộc|huyết\s*thống|quan\s*hệ\s*họ\s*hàng|xét\s*nghiệm\s*ADN)",
        "priority_score": 96,
    },
    "#M1": {
        "cluster": "satellite_zoom",
        "label": "Zoom x16 Tactical Rooftop Store",
        "regex_ko": r"(매점|학교|캠퍼스|지붕|옥상|건물|급습|현장\s*포위|주소|골목\s*안|매점\s*주인)",
        "regex_vi": r"(tiệm\s*tạp\s*hóa|mái\s*nhà|trường\s*học|khuôn\s*viên|nóc\s*nhà|đột\s*kích|bao\s*vây|tạp\s*hóa\s*trường)",
        "priority_score": 92,
    },
    "#M6": {
        "cluster": "satellite_zoom",
        "label": "Split Dual Satellite (Macro vs Micro)",
        "regex_ko": r"(광역.*좁혀졌|도심.*매점|위성.*분할|확대.*포착|줌인|광역.*정밀)",
        "regex_vi": r"(thu\s*hẹp.*phạm\s*vi|vệ\s*tinh.*phóng\s*to|từ\s*toàn\s*cảnh.*đến\s*chi\s*tiết|chia\s*đôi\s*vệ\s*tinh|vệ\s*tinh\s*kép)",
        "priority_score": 88,
    },
    "#M2": {
        "cluster": "satellite_corridor",
        "label": "Regional Satellite Corridor Z6/Z9",
        "regex_ko": r"(황토\s*고원|공업\s*기지|광산|간쑤성|란저우|바이인시|고속도로|회랑|지형|성도|도주로)",
        "regex_vi": r"(cao\s*nguyên\s*hoàng\s*thổ|mỏ\s*đồng|công\s*nghiệp|Cam\s*Túc|Lan\s*Châu|Bạch\s*Ngân|tuyến\s*đường|hành\s*lang)",
        "priority_score": 82,
    },
    "#M3": {
        "cluster": "satellite_corridor",
        "label": "Administrative Boundary / River Crossing",
        "regex_ko": r"(성\s*경계|행정구역|도주로|호구|외지인|관할|경계선|강을\s*건너|철도|황하)",
        "regex_vi": r"(ranh\s*giới\s*tỉnh|ranh\s*giới\s*hành\s*chính|đường\s*trốn\s*chạy|hộ\s*khẩu|ngoại\s*tỉnh|vượt\s*sông|ngoài\s*tầm\s*kiểm\s*soát|sông\s*Hoàng\s*Hà)",
        "priority_score": 87,
    },
    "#M5": {
        "cluster": "satellite_slab",
        "label": "2.5D Tilted Satellite Slab",
        "regex_ko": r"(좌표|지리적\s*패턴|연결하자|입체|3차원|위성\s*지형|슬랩|동선\s*패턴|거리.*연결|좌표.*거리)",
        "regex_vi": r"(tọa\s*độ|mô\s*thức\s*địa\s*lý|bản\s*đồ\s*lập\s*thể|khối\s*3D|mô\s*hình\s*không\s*gian|khối\s*bản\s*đồ|khoảng\s*cách.*liên\s*kết|tọa\s*độ.*khoảng\s*cách)",
        "priority_score": 92,
    },
    "#M4": {
        "cluster": "satellite_slab",
        "label": "Detective Cork Pinboard & Crime Cluster",
        "regex_ko": r"(핀보드|붉은\s*실|사건\s*연결|연쇄.*분포|범행.*연결|코르크)",
        "regex_vi": r"(bảng\s*điều\s*tra|dây\s*chỉ\s*đỏ|ghim\s*nối|chuỗi\s*án|phân\s*bố\s*tội\s*phạm|bảng\s*gỗ)",
        "priority_score": 86,
    },
    "#M7": {
        "cluster": "curfew_surveillance",
        "label": "Night-Ops Infrared Satellite Curfew",
        "regex_ko": r"(야간\s*통제|통금|해가\s*지면|반경\s*3|적외선|외출\s*금지|밤거리|야간\s*순찰|봉쇄)",
        "regex_vi": r"(giới\s*nghiêm|vùng\s*kiểm\s*soát|màn\s*đêm\s*buông\s*xuống|bán\s*kính\s*3\s*km|hồng\s*ngoại|cấm\s*ra\s*đường\s*đêm|tuần\s*tra\s*đêm|phong\s*tỏa)",
        "priority_score": 95,
    },
    "#M8": {
        "cluster": "satellite_corridor",
        "label": "Topographic Elevation Profile & Interstate Highway",
        "regex_ko": r"(등고선|고도|해발|산악\s*지형|단면\s*프로파일|협곡\s*고도)",
        "regex_vi": r"(đường\s*đồng\s*mức|độ\s*cao|mặt\s*cắt\s*địa\s*hình|núi\s*cao|đèo\s*dốc|hẻm\s*núi)",
        "priority_score": 83,
    },
    "#D9": {
        "cluster": "fingerprint",
        "label": "Microscope 14-Point Minutiae Comparator",
        "regex_ko": r"(14개|특징점|포개졌|현미경|완벽히\s*일치|단\s*하나의\s*지문|융선)",
        "regex_vi": r"(đặc\s*điểm\s*vân|14\s*điểm|trùng\s*khớp\s*hoàn\s*hảo|kính\s*hiển\s*vi|vân\s*ngón\s*tay|điểm\s*đặc\s*trưng)",
        "priority_score": 97,
    },
    "#D1": {
        "cluster": "fingerprint",
        "label": "Case Dossier Folder & Verification Matrix",
        "regex_ko": r"(23만\s*장|지문\s*대조망|유령으로|지문\s*카드|불일치|대조했으나|지문|수사\s*기록|사건\s*파일|전수\s*조사|전수\s*판독|명부|대조표|6,000시간)",
        "regex_vi": r"(23\s*vạn\s*dấu\s*vân\s*tay|lưới\s*so\s*sánh|bóng\s*ma|không\s*tìm\s*ra|phiếu\s*vân\s*tay|dấu\s*vân\s*tay|hồ\s*sơ\s*vụ\s*án|hồ\s*sơ\s*điều\s*tra|rà\s*soát\s*toàn\s*bộ)",
        "priority_score": 87,
    },
    "#D3": {
        "cluster": "fingerprint",
        "label": "Three Physical Clues & Case Evidence Dossier",
        "regex_ko": r"(생체\s*시료|혈액형|족적|3대\s*단서|물증|현장\s*증거|신발\s*자국|유류품|신분증|지갑|계량기|수돗물\s*2톤)",
        "regex_vi": r"(mẫu\s*sinh\s*học|nhóm\s*máu|dấu\s*chân|3\s*manh\s*mối\s*vật\s*chứng|dấu\s*vết\s*hiện\s*trường|vật\s*chứng\s*để\s*lại|đồng\s*hồ\s*nước)",
        "priority_score": 85,
    },
    "#D5": {
        "cluster": "interrogation",
        "label": "Aluminum Clipboard Q&A + Voiceprint",
        "regex_ko": r"(심문실|자백|진술서|자필|시인했다|녹음|취조|차분한\s*목소리|필적|심문|실종\s*신고|진술)",
        "regex_vi": r"(phòng\s*thẩm\s*vấn|thú\s*tội|lời\s*khai|bản\s*cung|thừa\s*nhận|ghi\s*âm|hỏi\s*cung|bút\s*tích|trình\s*báo|báo\s*án)",
        "priority_score": 96,
    },
    "#D2": {
        "cluster": "interrogation",
        "label": "Dual Identity / Suspect-Victim Case Profile Dossier",
        "regex_ko": r"(두\s*얼굴|이중생활|남편|아버지|괴물|평범한|가면|악마|한\s*지붕|재혼|아파트.*소유|주식\s*투자|빚|재산)",
        "regex_vi": r"(hai\s*mặt|vỏ\s*bọc|cuộc\s*sống\s*hai\s*mặt|người\s*chồng\s*mẫu\s*mực|quỷ\s*dữ|đội\s*lốt|hồ\s*sơ\s*nhân\s*thân|tài\s*sản|nợ\s*nần)",
        "priority_score": 81,
    },
    "#D6": {
        "cluster": "warrant_sketch",
        "label": "Class-A Red Wanted Warrant & Sketch",
        "regex_ko": r"(수배령|현상금|몽타주|공안부|1급\s*수배|공개수배|인상착의|스케치|20만\s*위안)",
        "regex_vi": r"(lệnh\s*truy\s*nã|tiền\s*thưởng|phác\s*họa\s*chân\s*dung|truy\s*nã\s*đỏ|truy\s*nã\s*cấp\s*A|phác\s*thảo|20\s*vạn)",
        "priority_score": 96,
    },
    "#D7": {
        "cluster": "biometrics",
        "label": "Ballistics & Toolmark Comparator",
        "regex_ko": r"(조흔|흉기\s*흔적|공구흔|칼자국|절단흔|탄도)",
        "regex_vi": r"(vết\s*cắt|dấu\s*vết\s*hung\s*khí|vết\s*xước\s*kim\s*loại|dấu\s*kìm|đạn\s*đạo)",
        "priority_score": 84,
    },
    "#D8": {
        "cluster": "biometrics",
        "label": "Autopsy & Medical Examiner Report",
        "regex_ko": r"(부검|검시|사망\s*원인|법의학|시신|타살|질식|사체\s*감정)",
        "regex_vi": r"(khám\s*nghiệm\s*tử\s*thi|pháp\s*y|nguyên\s*nhân\s*tử\s*vong|giải\s*phẫu|ngạt\s*thở)",
        "priority_score": 86,
    },
    "#D10": {
        "cluster": "timeline",
        "label": "Cold Case Archive Vault Box",
        "regex_ko": r"(서고|보존\s*상자|미제사건\s*캐비닛|캐비닛|먼지\s*쌓인|증거물\s*보관)",
        "regex_vi": r"(kho\s*lưu\s*trữ|hộp\s*hồ\s*sơ|hồ\s*sơ\s*đóng\s*bụi|tủ\s*tài\s*liệu\s*vụ\s*án|niêm\s*phong)",
        "priority_score": 83,
    },
    "#P3": {
        "cluster": "broadcast",
        "label": "1990s CRT TV Broadcast Monitor",
        "regex_ko": r"(방송|뉴스|특보|TV|화면|앵커|보도자료|아카이브\s*영상|당시\s*보도|브라운관|CRT)",
        "regex_vi": r"(bản\s*tin\s*truyền\s*hình|phát\s*sóng|thời\s*sự|ti\s*vi|đài\s*truyền\s*hình|băng\s*VHS|màn\s*hình\s*CRT)",
        "priority_score": 93,
    },
    "#P2": {
        "cluster": "curfew_surveillance",
        "label": "Archival Newspaper Panic & Curfew Notice",
        "regex_ko": r"(신문|보도|신문\s*1면|공포에\s*휩싸|비상\s*통고|경고문|호외|붉은\s*옷)",
        "regex_vi": r"(báo\s*chí|trang\s*nhất|hoảng\s*loạn|thông\s*báo\s*khẩn|giấy\s*cảnh\s*báo|áo\s*đỏ|dư\s*luận)",
        "priority_score": 82,
    },
    "#P1": {
        "cluster": "timeline",
        "label": "Chronological Timeline / Silent Gap",
        "regex_ko": r"(년\s*만에|년\s*동안|세월|침묵|공백|타임라인|미제로\s*남은|흐른\s*뒤|6년|28년)",
        "regex_vi": r"(suốt\s*bao\s*nhiêu\s*năm|dòng\s*thời\s*gian|năm\s*im\s*lặng|chưa\s*có\s*lời\s*giải|thời\s*gian\s*trôi|khoảng\s*lặng|6\s*năm|28\s*năm)",
        "priority_score": 88,
    },
    "#P4": {
        "cluster": "warrant_sketch",
        "label": "Police Bulletin Teletype / Telex Dispatch",
        "regex_ko": r"(전신|전문|급보|타자기|전국\s*전파|공안\s*전신)",
        "regex_vi": r"(điện\s*báo|bản\s*tin\s*khẩn|máy\s*đánh\s*chữ|báo\s*động\s*toàn\s*quốc|điện\s*mật)",
        "priority_score": 84,
    },
    "#P5": {
        "cluster": "broadcast",
        "label": "Emergency Radio Dispatch Frequency Log",
        "regex_ko": r"(무전|무전기|주파수|순찰차\s*교신|무전\s*일지|신호음)",
        "regex_vi": r"(bộ\s*đàm|tần\s*số|xe\s*tuần\s*tra|liên\s*lạc\s*vô\s*tuyến|sóng\s*radio)",
        "priority_score": 83,
    },
    "#P6": {
        "cluster": "court_verdict",
        "label": "Supreme Court Verdict & Sentence Proclamation",
        "regex_ko": r"(판결문|사형|재판|법원|선고|집행|정치권리\s*박탈|판결)",
        "regex_vi": r"(bản\s*án|tử\s*hình|tòa\s*án|tuyên\s*án|thi\s*hành\s*án|phán\s*quyết)",
        "priority_score": 90,
    },
    "cinema_full": {
        "cluster": "cinema",
        "label": "Fullscreen Cinematic Documentary Frame",
        "regex_ko": r"(눈물|슬픔|유가족|통곡|비통|오열|망연자실|주저앉아|말을\s*잇지\s*못|가슴이\s*무너|희생자의\s*어머니)",
        "regex_vi": r"(nước\s*mắt|đau\s*đớn|người\s*nhà\s*nạn\s*nhân|bi\s*kịch|tưởng\s*niệm|nghẹn\s*ngào|gục\s*ngã|thương\s*tâm|không\s*nói\s*nên\s*lời|người\s*mẹ\s*nạn\s*nhân)",
        "priority_score": 90,
    },
}


def is_vox_satellite_enabled(job: dict[str, Any], profile: dict[str, Any] | None = None) -> bool:
    """Verifies whether Vox & Satellite engine should activate for this job/profile.

    Strictly activates for True Crime profile (channel-e544a64b7c) or forensic_noir preset,
    while strictly protecting non-crime profiles (channel-1e24de3ab5, channel-aa913eb90d, channel-f6ec4dfff3).
    """
    profile_id = str(
        job.get("channel_profile_id")
        or (profile or {}).get("id")
        or (job.get("channel_profile_snapshot") or {}).get("id")
        or ""
    ).strip()

    # Strict whitelist for True Crime channel
    if profile_id == "channel-e544a64b7c":
        return True

    # Strict blacklist for known non-crime channels
    if profile_id in {"channel-1e24de3ab5", "channel-aa913eb90d", "channel-f6ec4dfff3"}:
        return False

    # Check editing preset and visual strategy
    preset_id = str(
        (job.get("editing_dna") or {}).get("preset_id")
        or ((profile or {}).get("editing_dna") or {}).get("preset_id")
        or ""
    ).strip().lower()
    if preset_id == "forensic_noir":
        return True

    strategy = str(
        job.get("visual_strategy")
        or (job.get("production_recipe") or {}).get("visual_strategy")
        or ""
    ).strip().lower()
    if strategy in {"forensic_noir", "true_crime_noir_ai"}:
        return True

    return False


class VoxSemanticRouter:
    """Voice-driven semantic router for True Crime investigative archetypes.

    Implements:
    1. Bilingual intent scoring (Korean broadcast voice + Vietnamese briefs).
    2. Sliding window anti-repetition mechanism (recency penalty + sibling rotation).
    3. Emotion bypass to cinema_full.
    """

    def __init__(self, history_size: int = 4):
        self.history_size = history_size
        self.recent_archetypes: list[str] = []

    def reset_history(self) -> None:
        self.recent_archetypes.clear()

    def _same_cluster(self, arch1: str, arch2: str) -> bool:
        c1 = (VOX_ARCHETYPE_RULES.get(arch1) or {}).get("cluster")
        c2 = (VOX_ARCHETYPE_RULES.get(arch2) or {}).get("cluster")
        return bool(c1 and c2 and c1 == c2)

    def route_beat(
        self,
        narration_text: str,
        metadata: dict[str, Any] | None = None,
        recent_history: list[str] | None = None,
    ) -> dict[str, Any]:
        """Classifies a single narration beat and resolves the optimal archetype."""
        text = str(narration_text or "").strip()
        history = list(recent_history) if recent_history is not None else list(self.recent_archetypes)

        candidates: list[tuple[float, str, str, str]] = []

        # Check emotional trigger first
        cinema_rule = VOX_ARCHETYPE_RULES["cinema_full"]
        ko_emotion = bool(re.search(cinema_rule["regex_ko"], text, re.IGNORECASE))
        vi_emotion = bool(re.search(cinema_rule["regex_vi"], text, re.IGNORECASE))
        if ko_emotion or vi_emotion:
            # Emotional grief / human confrontation takes precedence unless just used
            penalty = 180.0 if history and history[-1] == "cinema_full" else 0.0
            score = max(0.0, 120.0 - penalty)
            if score > 0.0:
                candidates.append((score, "cinema_full", cinema_rule["label"], "Human sorrow / dramatic confrontation detected"))

        for arch_id, rule in VOX_ARCHETYPE_RULES.items():
            if arch_id == "cinema_full":
                continue

            match_ko = bool(re.search(rule["regex_ko"], text, re.IGNORECASE))
            match_vi = bool(re.search(rule["regex_vi"], text, re.IGNORECASE))

            if not (match_ko or match_vi):
                continue

            base_score = float(rule["priority_score"])
            if match_ko:
                base_score += 30.0
            if match_vi:
                base_score += 25.0

            # Recency penalty calculation
            penalty = 0.0
            if history:
                # Immediate predecessor (Beat i-1): >= 160.0 to prevent consecutive repetition
                if history[-1] == arch_id:
                    penalty += 180.0
                # Two beats ago (Beat i-2): -40 points
                if len(history) >= 2 and history[-2] == arch_id:
                    penalty += 40.0
                # Three beats ago (Beat i-3): -15 points
                if len(history) >= 3 and history[-3] == arch_id:
                    penalty += 15.0
                # Same cluster predecessor (e.g. #M1 immediately after #M6): -25 points
                if self._same_cluster(history[-1], arch_id):
                    penalty += 25.0

            final_score = max(0.0, base_score - penalty)
            reason = f"Matched tokens on {arch_id} ({rule['label']}) [base={base_score:.0f}, penalty={penalty:.0f}]"
            candidates.append((final_score, arch_id, rule["label"], reason))

        # Filter for valid candidates with positive scores that do not repeat the immediate previous archetype
        valid_candidates = [
            c for c in candidates
            if c[0] > 0.0 and (not history or c[1] != history[-1])
        ]

        if not valid_candidates:
            # Fallback to cinema_full if neutral / no match or avoiding repetition
            chosen_id = "cinema_full" if history and history[-1] != "cinema_full" else "#D2"
            chosen_label = VOX_ARCHETYPE_RULES[chosen_id]["label"]
            chosen_reason = f"Default fallback / anti-repetition rotation away from {history[-1] if history else 'none'}"
            chosen_cluster = VOX_ARCHETYPE_RULES[chosen_id]["cluster"]
            winning_score = 0.0
        else:
            valid_candidates.sort(key=lambda x: x[0], reverse=True)
            winning_score, chosen_id, chosen_label, chosen_reason = valid_candidates[0]
            chosen_cluster = VOX_ARCHETYPE_RULES[chosen_id]["cluster"]

        # Update sliding history
        self.recent_archetypes.append(chosen_id)
        if len(self.recent_archetypes) > self.history_size:
            self.recent_archetypes.pop(0)

        return {
            "archetype": chosen_id,
            "label": chosen_label,
            "cluster": chosen_cluster,
            "score": winning_score,
            "reason": chosen_reason,
        }

    def route_timeline(
        self,
        beats: list[dict[str, Any]],
        job: dict[str, Any],
        profile: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Tags all beats in a project timeline with their resolved scene archetypes.

        Enforces the Universal 4-Tier Semantic Visual Priority Rule:
        1. Real Video Footage -> 2. Real Photo Footage -> 3. Semantic Vox (Case Files, Satellite Maps,
           Forensic Dossiers, Press/Broadcast & any analytical graphic) -> 4. AI Image.
        Vox archetypes (#M*, #D*, #P*) are assigned whenever the spoken narration semantically matches
        (score > 0). Archetypes are NOT restricted to count = 1; they may recur purposefully across
        the investigation timeline, and each beat receives its own voice-specific rendered motion.
        """
        if not is_vox_satellite_enabled(job, profile):
            return beats

        self.reset_history()
        routed_beats: list[dict[str, Any]] = []
        used_archetypes: dict[str, int] = {}
        is_full_documentary = len(beats) > 12
        last_vox_idx = -99

        for idx, beat in enumerate(beats):
            text = str(beat.get("narration_text") or beat.get("text") or "").strip()
            decision = self.route_beat(text, metadata=beat)
            arch = decision["archetype"]
            label = decision["label"]
            cluster = decision["cluster"]
            score = float(decision.get("score") or 0.0)

            # Never force a Vox graphic when the voice narration has zero semantic match (score <= 0)
            if score <= 0.0:
                arch = "cinema_full"
                label = VOX_ARCHETYPE_RULES["cinema_full"]["label"]
                cluster = "cinema"
            elif is_full_documentary and arch != "cinema_full":
                # Allow purposeful recurrence across the documentary while preventing back-to-back clustering
                if (idx - last_vox_idx) < 2:
                    arch = "cinema_full"
                    label = VOX_ARCHETYPE_RULES["cinema_full"]["label"]
                    cluster = "cinema"
                else:
                    used_archetypes[arch] = used_archetypes.get(arch, 0) + 1
                    last_vox_idx = idx

            updated_beat = {
                **beat,
                "scene_archetype": arch,
                "archetype_label": label,
                "archetype_cluster": cluster,
            }
            routed_beats.append(updated_beat)

        return routed_beats
