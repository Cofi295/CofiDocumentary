# SURVEY REPORT: CofiDocumentary Backend & Routing Architecture
**Document**: `survey_backend_routing.md`  
**Explorer**: Survey Explorer 2 (`teamwork_preview_explorer`)  
**Target System**: `B:\ALL_TOOLS\CofiDocumentary`  
**Date**: 2026-10-23  

---

## 1. Executive Summary

This investigation surveys CofiDocumentary's backend scene planning, beat generation, archetype routing, and channel profile persistence systems, with the explicit goal of integrating the **True Crime Vox & Real Satellite Multi-Archetype Engine** (derived from `B:\ALL_TOOLS\CofiBlenderStudio\vox_editorial_artist.py` and `vox_archetype_expansion.py`) into `CofiDocumentary`.

### Key Findings
1. **Current Architectural Disconnect**:
   - `CofiDocumentary` currently handles visual beats in `documentary/prompts.py` (PLAN) and `documentary/visuals.py` (Visuals / STP). It tags beats with high-level routing markers (`ai_visual` vs `footage`) and broad types (`ai_reconstruction`, `sourced_video`), but **lacks granular archetype assignment** (e.g., `#M1` rooftop satellite, `#D4` Y-STR DNA lightbox, `#D5` clipboard confession).
   - `services/editing_dna_service.py` already includes a `forensic_noir` editing preset and tracks editing archetypes (`forensic_case_board_red_string`, `document_scanner_telemetry`, `noir_chapter_transition`, `biometric_dna_hud`, `forensic_map_route_board`), but these archetypes exist only as descriptive strings rather than functional scene generation targets.
   - `b:\ALL_TOOLS\CofiBlenderStudio` contains a production-ready, standalone PIL/compositor rendering suite with 17+ tactical True Crime archetypes and pre-cached Esri World Imagery satellite plates (`Z6`, `Z9`, `Z14`, `Z16`). It requires zero external Blender dependencies and runs at high throughput using standard Python libraries.

2. **Semantic Voice-Content Matching**:
   - Spoken narration (Korean for broadcast, Vietnamese for creator prompts/briefs) contains dense, unambiguous investigative signals: genetic genealogy (`Y-염색체`, `유전자`, `족보`), tactical raids on specific buildings (`매점`, `옥상`, `캠퍼스`), jurisdictional river/boundary escapes (`황하`, `성계`, `행정구역`, `호구`), 3D coordinate patterns (`좌표`, `지리적 패턴`, `입체`), night curfews (`야간 통제`, `통금`, `적외선`), interrogation admissions (`심문실`, `자백`, `진술서`), wanted posters (`수배령`, `현상금`, `몽타주`), fingerprint ridge comparisons (`지문`, `융선`, `14개 특징점`), 1990s TV broadcasts (`방송`, `뉴스 특보`, `CRT 브라운관`), and raw human grief/emotion (`눈물`, `유가족`, `통곡`).
   - A dedicated `VoxSemanticRouter` module can parse these tokens using regex pattern matching and semantic intent scoring to dynamically assign the optimal archetype without resorting to hardcoded defaults or rigid round-robin rotations.

3. **Anti-Repetition Mechanism**:
   - Without anti-repetition logic, consecutive beats describing the same subject (e.g., fingerprint minutiae or satellite tracking) would trigger identical visual shells back-to-back, causing visual monotony.
   - By tracking a sliding history window (last 3 beats) and applying recency penalties alongside semantic cluster variant rotation (e.g. `#D1` -> `#D9` -> `cinema_full` or `#M1` -> `#M6` -> `#M5`), the engine maintains high visual variety and pacing dynamism.

4. **100% Channel Profile Isolation**:
   - The Vox & Satellite True Crime engine must be strictly isolated to `channel-e544a64b7c` (`특급수배록` / `true_crime_noir_ai` / `forensic_noir`).
   - Non-crime profiles (`channel-1e24de3ab5` Chinese Megaprojects & Geopolitics `판세의 이면`, `channel-f6ec4dfff3` Presidential Vault) must remain completely untouched, retaining their respective `2.5d_technical` and `archival_historical` pipelines.

5. **Test Placement**:
   - Two comprehensive test suites should be introduced in `tests/`:
     - `tests/test_vox_semantic_router.py`: Validates 10+ bilingual test sentences, anti-repetition behavior, and channel profile gating.
     - `tests/test_vox_scene_renderer.py`: Validates 1920x1080 frame composition, GIS satellite plate loading, and zero missing Korean glyphs.

---

## 2. Current CofiDocumentary Backend Pipeline & Gap Analysis

### 2.1 Stage-by-Stage Beat & Scene Flow

```
[Channel Profiles] (data/channel_profiles.json)
       │
       ▼
[Step 01: Plan] (documentary/prompts.py)
       │  • Generates research.md, script.md, visual_manifest.json (plan beats: B001, B002...)
       │  • Assigns: visual_type, source_priority, visual_description, framing_motion_intent
       ▼
[Step 02: Voice] (documentary/voice.py)
       │  • Generates voice_manifest.json and subtitles.srt with timestamps
       ▼
[Step 03: Visuals / STP] (documentary/visuals.py)
       │  • Splits narration into clause-level units (B001-V01, B001-V02)
       │  • Assigns visual_route (ai_visual vs footage) via _route_for()
       │  • Currently MISSING: scene_archetype tagging (#M1..#M8, #D1..#D10, #P1..#P6)
       ▼
[Step 04: Footage] & [Step 05: AI Visual] (documentary/footage.py & ai_visual.py)
       │  • Sources footage or generates AI visuals
       ▼
[Step 06: Edit] (documentary/edit.py)
       │  • Batches beats and executes CofiRemotion / Codex composition
       │  • Currently MISSING: True Crime Vox & Satellite scene compositor integration
```

### 2.2 Deep Dive into Key Files

#### `documentary/prompts.py`
- **Location**: Lines 452–545 (`phase == "plan"`), Lines 563–612 (`phase == "edit"`), Lines 770–820 (`build_edit_batch_prompt`).
- **Mechanism**:
  - In `plan`, the system instructs the AI agent to generate `visual_manifest.json` with beats containing `story_group`, `narration_text`, `purpose`, `visual_type` (`ai_reconstruction` vs `sourced_video`), `source_priority` (`must_real`, `prefer_real`, `ai_ok`), `framing_motion_intent`, `on_screen_text`, and `sound_notes`.
  - In `edit`, `build_edit_batch_prompt` injects guidelines into CofiRemotion.
- **Identified Gap**: Neither `build_phase_prompt` nor `build_edit_batch_prompt` provides prompt rules or data structures for assigning granular True Crime archetypes to beats.

#### `documentary/visuals.py`
- **Location**: `VisualsCoordinator.run(...)` (Lines 250–385).
- **Mechanism**:
  - Splits spoken text into semantic units via `split_visual_text(text, max_chars=110)`.
  - Determines routing via `_route_for(...)` and formats prompts via `_prompt_for(...)`.
  - Outputs refined `visual_manifest.json` and `visual_prompts.json`.
- **Identified Gap**: `VisualsCoordinator` is the optimal interception point where each refined beat (`B001-V01`) should be analyzed by `VoxSemanticRouter` to assign its canonical `scene_archetype`.

#### `services/editing_dna_service.py`
- **Location**: Lines 112–172 (`forensic_noir` preset), Lines 305–478 (`extract_editing_dna_from_job`), Lines 479–555 (`lock_job_edit_dna_to_channel`).
- **Mechanism**:
  - Maintains `BUILTIN_EDITING_PRESETS["forensic_noir"]` with shot pacing (5.5s), visual mix (85% AI, 15% motion), color grade (`cold_forensic_noir`), and archetypes:
    `["forensic_case_board_red_string", "document_scanner_telemetry", "noir_chapter_transition", "biometric_dna_hud", "forensic_map_route_board"]`.
  - Supports `lock_job_edit_dna_to_channel` to lock approved edits to `channel_profiles.json`.
- **Identified Gap**: The archetypes in `forensic_noir` are legacy generic names. They should be expanded to include the complete 17+ True Crime Vox & Satellite catalog (`#M1..#M8`, `#D1..#D10`, `#P1..#P6`, `cinema_full`).

#### `documentary/service.py`
- **Location**: Lines 7530–7547 (`_is_true_crime_profile`).
- **Mechanism**:
  - Contains authoritative identification of True Crime channel profiles:
    ```python
    def _is_true_crime_profile(cls, profile: dict[str, Any]) -> bool:
        pid = str(profile.get("id") or "")
        if pid == "channel-e544a64b7c":
            return True
        if pid in {"channel-1e24de3ab5", "channel-aa913eb90d", "channel-f6ec4dfff3"}:
            return False
        ...
    ```
- **Identified Gap**: This logic is currently used for topic discovery and candidate filtering, but has not yet been hooked into scene routing or rendering execution.

#### `data/channel_profiles.json`
- **Location**: `channel-e544a64b7c` (Lines 4–1787).
- **Profile Attributes**:
  - Market: `KR`
  - Title: `특급수배록`
  - Style: `Cold Forensic Noir (Tông màu điện ảnh điều tra sắc lạnh, phòng thẩm vấn, hiện trường phong tỏa)`
  - Creative Brief: `Điều tra Hồ sơ Hình sự & Giải mã Tâm lý Tội phạm Nguy hiểm (형사 수사 기록 & 프로파일링 — Ngôi thứ 3)`
  - Target Duration: 20–30 minutes (~150–280 beats).

---

## 3. Catalog of True Crime Vox & Satellite Archetypes

Extracted directly from `B:\ALL_TOOLS\CofiBlenderStudio\vox_editorial_artist.py` and `vox_archetype_expansion.py`:

| Archetype ID | Canonical Label | Resolution / GIS Plate | Description & Visual Shell |
|---|---|---|---|
| `#M1` | Zoom x16 Tactical Rooftop Store | `plate_baiyin_campus_sat_z16.png` | Extreme close-up satellite plate (Zoom 16, ~1.19 m/px). Shows school campus, building rooftops, red tactical target box, radius measurement callout. |
| `#M2` | Regional Satellite Corridor Z6/Z9 | `plate_baiyin_lanzhou_sat_z9.png`, `plate_gansu_sat_z6.png` | Provincial geographic corridor, Gansu/Lanzhou/Baiyin highway, mountain terrain, mining basin vector routes. |
| `#M3` | Administrative Boundary / River Crossing | `plate_baiyin_lanzhou_sat_z9.png` + GeoJSON boundaries | Regional county borders, Yellow River crossing, hukou registration blindspot, inter-provincial migration vector. |
| `#M4` | Multi-Coordinate Crime Distribution Map | `plate_baiyin_city_sat_z14.png` | Citywide incident map (Zoom 14), cluster pins marking attack locations across years (e.g. 1998 4 cases), connecting yellow vector threads. |
| `#M5` | 2.5D Tilted Satellite Slab | `plate_baiyin_lanzhou_sat_z9.png` | Angled 3D topographic plate (`perspective(1400px) rotateX(24deg)`), elevated elevation contour, crime coordinate connection slab. |
| `#M6` | Split Dual Satellite (Macro vs Micro) | `plate_baiyin_city_sat_z14.png` + `plate_baiyin_campus_sat_z16.png` | Split screen: Left wide city radar (Z14) showing area, Right micro optical zoom (Z16) zooming into suspect building rooftop. |
| `#M7` | Night-Ops Infrared Satellite Curfew | `plate_baiyin_city_sat_z14.png` (Infrared Inverted) | Nocturnal surveillance plate: dark-blue/cyan thermal palette, 3km red curfew radius ring, night patrol checkpoint vectors. |
| `#M8` | Inter-Provincial Pursuit Highway Corridor | `plate_gansu_sat_z6.png` | Macro interstate tracking, railway and bus line escape routes across provincial borders. |
| `#D1` | Latent Print Paradox Comparator | Split Dual Macro Frame | 230,000 prints screening comparison: latent crime scene print vs suspect record card, brass measurement calipers. |
| `#D2` | Dual Identity / Double Life Dossier | Dual Polaroid / Manila Folder | Duality contrast: Left normal citizen/family man, Right forensic detention photo, yellow split-divider tape. |
| `#D3` | Three Physical Clues Triad Dossier | Manila Dossier + 3 Evidence Windows | Triad physical evidence: Fingerprint ridge + Blood type / Saliva swab + Footwear tread pattern card. |
| `#D4` | Y-STR DNA Lightbox & Clan Pedigree Tree | Translucent Lightbox + Pedigree Node Tree | Y-chromosome marker lightbox, familial genetic genealogy tree, clan node highlighted in forensic crimson. |
| `#D5` | Aluminum Clipboard Q&A + Voiceprint | Brushed Aluminum Board + Waveform HUD | Official interrogation Q&A transcript on lined paper, audio tape recorder, real-time voiceprint waveform HUD. |
| `#D6` | Class-A Red Wanted Warrant & Sketch | Archival Wanted Poster Card | Ministry of Public Security Class-A Red Notice, 200,000 RMB cash reward badge, composite sketch vs actual mugshot. |
| `#D7` | Tool Mark & Weapon Striation Comparator | Forensic Microscope Split Frame | Striation comparison under optical split: weapon/blade tool marks vs evidence surface impressions. |
| `#D8` | Autopsy & Medical Examiner Report | Formal Forensic Pathology Slab | Time of death calculation, trauma mapping, toxicology findings on formal police medical examiner form. |
| `#D9` | Microscope 14-Point Minutiae Comparator | Dual Circular Lens Overlay | 14 ridge points highlighted (bifurcations, ridge endings, islands), cyan/red vector connection lines, 100% ridge match. |
| `#D10` | Cold Case Evidence Locker / Tagged Artifact | Archival Kraft Box & Poly Bag | Evidence locker shelf, chain-of-custody paper tag, sealed evidence poly bag with police seal. |
| `#P1` | Chronological Timeline / Silent Gap | Horizontal Aged Kraft Timeline | Multi-year chronological progression, timeline bar highlighting years of dormancy (e.g. 1988 -> 1994, 6-year silence). |
| `#P2` | Archival Newspaper Panic & Curfew Notice | Broadsheet Newspaper + Curfew Notice | Broadsheet headline ("도심 연쇄 범행 주의보"), red police curfew advisory notice, night-shift worker safety alert. |
| `#P3` | 1990s CRT TV Broadcast Monitor | CRT 4:3 Frame + Scanlines & Glitch | 1990s emergency television broadcast, CRT phosphor curvature, VHS timecode (`REC 1998-12-03`), news anchor bulletin. |
| `#P4` | Police Press Conference & Flashbulbs | Press Stage Overlay + Camera Flashes | Police leadership press conference, table microphones, investigative task force spokesperson statement. |
| `#P5` | Megaphone Street Warning Noticeboard | Wooden Neighborhood Bulletin Board | Physical community board, megaphone icon, handwritten advisory warning women against walking alone. |
| `#P6` | Courtroom Sentencing Verdict & Gavel | Legal Verdict Parchment + Red Seal | Final Intermediate People's Court judgment, judicial stamp, death penalty execution announcement. |
| `cinema_full` | Fullscreen Cinematic Documentary Frame | 16:9 Full Frame + Lower-Third Typography | Uncluttered cinematic visual (real footage or full-frame AI), used for raw emotional grief, victim remembrance, dramatic pauses. |

---

## 4. Semantic Voice-Content Matching Engine Design

### 4.1 Architecture & Workflow

The matching engine analyzes the spoken narration of each beat (`narration_text` from `visual_manifest.json` and `text` from `voice_manifest.json` / SRT). It matches tokens across two languages:
1. **Korean (Primary Target Language)**: Spoken voice track for `channel-e544a64b7c`.
2. **Vietnamese (Creator / Production Language)**: Creative brief, topic anchors, prompt notes, and bilingual drafts.

```
                  ┌──────────────────────────────────────────────┐
                  │ Beat Input (Narration Text: KO / VI)        │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │ Token Normalization & Regex Pattern Matcher │
                  └──────────────────────┬───────────────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
     [Candidate Archetypes Scoring]               [Recent History Context]
     • High-intent triggers (+50 pts)             • Beat i-1 (-80 pts penalty)
     • Contextual keywords (+20 pts)              • Beat i-2 (-40 pts penalty)
     • Story group relevance (+15 pts)            • Cluster variety bonus (+10 pts)
                 └───────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │ Final Selection & Conflict Tie-Breaker       │
                  │ (Selected Archetype, Confidence, Reasoning) │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │ Update Sliding Window History & Stamp Beat  │
                  └──────────────────────────────────────────────┘
```

### 4.2 Bilingual Trigger Lexicon & Regex Patterns

```python
VOX_ARCHETYPE_RULES = {
    "#D4": {
        "cluster": "biometrics",
        "label": "Y-STR DNA Lightbox & Clan Pedigree Tree",
        "regex_ko": r"(Y-염색체|유전자|족보|가문|DNA|부계|혈통|친척|가오씨|대조\s*검사|염색체|가계도)",
        "regex_vi": r"(Y-STR|nhiễm\s*sắc\s*thể\s*Y|ADN\s*dòng\s*họ|phả\s*hệ|gia\s*tộc|huyết\s*thống|quan\s*hệ\s*họ\s*hàng|xét\s*nghiệm\s*ADN)",
        "priority_score": 95,
    },
    "#M1": {
        "cluster": "satellite_zoom",
        "label": "Zoom x16 Tactical Rooftop Store",
        "regex_ko": r"(매점|학교|캠퍼스|지붕|옥상|건물|급습|현장\s*포위|주소|골목\s*안|매점\s*주인)",
        "regex_vi": r"(tiệm\s*tạp\s*hóa|mái\s*nhà|trường\s*học|khuôn\s*viên|nóc\s*nhà|đột\s*kích|bao\s*vây|tạp\s*hóa\s*trường)",
        "priority_score": 90,
    },
    "#M6": {
        "cluster": "satellite_zoom",
        "label": "Split Dual Satellite (Macro vs Micro)",
        "regex_ko": r"(광역.*좁혀졌|도심.*매점|위성.*분할|확대.*포착|줌인)",
        "regex_vi": r"(thu\s*hẹp.*phạm\s*vi|vệ\s*tinh.*phóng\s*to|từ\s*toàn\s*cảnh.*đến\s*chi\s*tiết|chia\s*đôi\s*vệ\s*tinh)",
        "priority_score": 85,
    },
    "#M2": {
        "cluster": "satellite_corridor",
        "label": "Regional Satellite Corridor Z6/Z9",
        "regex_ko": r"(황하|황토\s*고원|공업\s*기지|광산|간쑤성|란저우|바이인시|고속도로|회랑|지형)",
        "regex_vi": r"(sông\s*Hoàng\s*Hà|cao\s*nguyên\s*hoàng\s*thổ|mỏ\s*đồng|công\s*nghiệp|Cam\s*Túc|Lan\s*Châu|Bạch\s*Ngân|tuyến\s*đường)",
        "priority_score": 80,
    },
    "#M3": {
        "cluster": "satellite_corridor",
        "label": "Administrative Boundary / River Crossing",
        "regex_ko": r"(성\s*경계|행정구역|도주로|호구|외지인|관할|경계선|강을\s*건너|철도)",
        "regex_vi": r"(ranh\s*giới\s*tỉnh|ranh\s*giới\s*hành\s*chính|đường\s*trốn\s*chạy|hộ\s*khẩu|ngoại\s*tỉnh|vượt\s*sông|ngoài\s*tầm\s*kiểm\s*soát)",
        "priority_score": 85,
    },
    "#M5": {
        "cluster": "satellite_slab",
        "label": "2.5D Tilted Satellite Slab",
        "regex_ko": r"(좌표|지리적\s*패턴|연결하자|입체|반경|거리|공간적|위성\s*지형|슬랩|동선\s*패턴)",
        "regex_vi": r"(tọa\s*độ|mô\s*thức\s*địa\s*lý|liên\s*kết|bản\s*đồ\s*lập\s*thể|khối\s*3D|khoảng\s*cách|mô\s*hình\s*không\s*gian)",
        "priority_score": 90,
    },
    "#M7": {
        "cluster": "curfew_surveillance",
        "label": "Night-Ops Infrared Satellite Curfew",
        "regex_ko": r"(야간\s*통제|통금|해가\s*지면|반경\s*3|적외선|외출\s*금지|밤거리|야간\s*순찰)",
        "regex_vi": r"(giới\s*nghiêm|vùng\s*kiểm\s*soát|màn\s*đêm\s*buông\s*xuống|bán\s*kính\s*3\s*km|hồng\s*ngoại|cấm\s*ra\s*đường\s*đêm)",
        "priority_score": 85,
    },
    "#P2": {
        "cluster": "curfew_surveillance",
        "label": "Archival Newspaper Panic & Curfew Notice",
        "regex_ko": r"(신문|보도|신문\s*1면|공포에\s*휩싸|비상\s*통고|경고문|호외|붉은\s*옷)",
        "regex_vi": r"(báo\s*chí|trang\s*nhất|hoảng\s*loạn|thông\s*báo\s*khẩn|giấy\s*cảnh\s*báo|áo\s*đỏ|dư\s*luận)",
        "priority_score": 80,
    },
    "#D5": {
        "cluster": "interrogation",
        "label": "Aluminum Clipboard Q&A + Voiceprint",
        "regex_ko": r"(심문실|자백|진술서|자필|시인했다|녹음|취조|차분한\s*목소리|필적|심문)",
        "regex_vi": r"(phòng\s*thẩm\s*vấn|thú\s*tội|lời\s*khai|bản\s*cung|thừa\s*nhận|ghi\s*âm|hỏi\s*cung|bút\s*tích)",
        "priority_score": 95,
    },
    "#D6": {
        "cluster": "warrant_sketch",
        "label": "Class-A Red Wanted Warrant & Sketch",
        "regex_ko": r"(수배령|현상금|몽타주|공안부|1급\s*수배|공개수배|인상착의|스케치|20만\s*위안)",
        "regex_vi": r"(lệnh\s*truy\s*nã|tiền\s*thưởng|phác\s*họa\s*chân\s*dung|truy\s*nã\s*đỏ|truy\s*nã\s*cấp\s*A|phác\s*thảo|20\s*vạn)",
        "priority_score": 95,
    },
    "#D1": {
        "cluster": "fingerprint",
        "label": "Latent Print Paradox Comparator",
        "regex_ko": r"(23만\s*장|지문\s*대조망|유령으로|지문\s*카드|불일치|대조했으나)",
        "regex_vi": r"(23\s*vạn\s*dấu\s*vân\s*tay|lưới\s*so\s*sánh|bóng\s*ma|không\s*tìm\s*ra|phiếu\s*vân\s*tay)",
        "priority_score": 85,
    },
    "#D9": {
        "cluster": "fingerprint",
        "label": "Microscope 14-Point Minutiae Comparator",
        "regex_ko": r"(지문|융선|14개|특징점|포개졌|현미경|완벽히\s*일치|단\s*하나의\s*지문)",
        "regex_vi": r"(dấu\s*vân\s*tay|đặc\s*điểm\s*vân|14\s*điểm|trùng\s*khớp\s*hoàn\s*hảo|kính\s*hiển\s*vi|vân\s*ngón\s*tay)",
        "priority_score": 95,
    },
    "#P3": {
        "cluster": "broadcast",
        "label": "1990s CRT TV Broadcast Monitor",
        "regex_ko": r"(방송|뉴스|특보|TV|화면|앵커|보도자료|아카이브\s*영상|당시\s*보도|브라운관)",
        "regex_vi": r"(bản\s*tin\s*truyền\s*hình|phát\s*sóng|thời\s*sự|ti\s*vi|đài\s*truyền\s*hình|băng\s*VHS|màn\s*hình\s*CRT)",
        "priority_score": 90,
    },
    "#P1": {
        "cluster": "timeline",
        "label": "Chronological Timeline / Silent Gap",
        "regex_ko": r"(년\s*만에|년\s*동안|세월|침묵|공백|타임라인|미제로\s*남은|흐른\s*뒤|6년)",
        "regex_vi": r"(suốt\s*bao\s*nhiêu\s*năm|dòng\s*thời\s*gian|năm\s*im\s*lặng|chưa\s*có\s*lời\s*giải|thời\s*gian\s*trôi|khoảng\s*lặng)",
        "priority_score": 85,
    },
    "#D2": {
        "cluster": "duality",
        "label": "Dual Identity / Double Life Dossier",
        "regex_ko": r"(두\s*얼굴|이중생활|남편|아버지|괴물|평범한|가면|악마|한\s*지붕)",
        "regex_vi": r"(hai\s*mặt|vỏ\s*bọc|cuộc\s*sống\s*hai\s*mặt|người\s*chồng\s*mẫu\s*mực|quỷ\s*dữ|đội\s*lốt)",
        "priority_score": 80,
    },
    "#D3": {
        "cluster": "evidence_triad",
        "label": "Three Physical Clues Triad Dossier",
        "regex_ko": r"(생체\s*시료|혈액형|족적|3대\s*단서|물증|현장\s*증거|신발\s*자국)",
        "regex_vi": r"(mẫu\s*sinh\s*học|nhóm\s*máu|dấu\s*chân|3\s*manh\s*mối\s*vật\s*chứng|dấu\s*vết\s*hiện\s*trường)",
        "priority_score": 85,
    },
    "cinema_full": {
        "cluster": "cinema",
        "label": "Fullscreen Cinematic Documentary Frame",
        "regex_ko": r"(눈물|슬픔|유가족|통곡|공포|비극|망연자실|분노|기억하며|어머니|가슴|한숨)",
        "regex_vi": r"(nước\s*mắt|đau\s*đớn|người\s*nhà\s*nạn\s*nhân|bi\s*kịch|tưởng\s*niệm|cảm\s*xúc|nghẹn\s*ngào|gục\s*ngã)",
        "priority_score": 75,
    },
}
```

### 4.3 Benchmark Test Matrix (11 Verification Sentences)

| # | Test Sentence (Korean / Vietnamese) | Expected Archetype | Rationale & Dominant Signals |
|---|---|---|---|
| 1 | "단 하나의 Y-염색체 유전자 표지가 칭청진 가오씨 가문의 족보를 정조준했습니다."<br>*(Chỉ một dấu chỉ thị Y-STR trên nhiễm sắc thể Y đã nhắm thẳng vào cuốn gia phả của dòng họ Cao)* | `#D4` | Unambiguous match on `Y-염색체`, `유전자`, `족보`, `가문` (`Y-STR`, `phả hệ`). Highest score in Biometrics cluster. |
| 2 | "사복 형사들이 최종적으로 덮친 곳은 놀랍게도 한 고등학교 캠퍼스 안의 평화로운 매점과 옥상 건물이었습니다."<br>*(Nơi các trinh sát hình sự ập vào bao vây lại là tiệm tạp hóa và tòa nhà trên khuôn viên trường)* | `#M1` | Clear tactical building raid matching `매점`, `캠퍼스`, `옥상` (`tiệm tạp hóa`, `mái nhà`). Triggers Z16 tactical satellite. |
| 3 | "해가 지면 바이인시 도심 반경 3킬로미터 전체가 거대한 야간 통제 구역으로 변해 철문이 굳게 닫혔습니다."<br>*(Khi mặt trời lặn, toàn bộ bán kính 3km quanh trung tâm thành phố biến thành vùng giới nghiêm)* | `#M7` | Strong night surveillance signals: `해가 지면`, `반경 3킬로미터`, `야간 통제` (`giới nghiêm`, `bán kính 3km`). |
| 4 | "28년 전 현장에 남겨진 지문의 14개 융선 특징점이 가오청융의 손가락과 완벽히 포개졌습니다."<br>*(14 điểm đặc trưng trên các đường vân tay hiện trường 28 năm trước đã trùng khớp hoàn hảo)* | `#D9` | Explicit minutiae comparison triggers: `지문`, `융선`, `14개 특징점`, `포개졌` (`14 điểm`, `đặc trưng vân`). |
| 5 | "심문실 의자에 앉은 가오청융은 취조관 앞에서 녹음기를 켜자 단 한 번의 동요도 없이 11건의 범행 자백 진술서를 작성했습니다."<br>*(Ngồi trong phòng thẩm vấn trước máy ghi âm, hắn không dao động mà ký bản cung thú nhận 11 vụ án)* | `#D5` | Interrogation room and confession tokens: `심문실`, `자백`, `진술서`, `녹음기` (`phòng thẩm vấn`, `bản cung`). |
| 6 | "공안부가 20만 위안의 현상금과 붉은색 1급 수배령 몽타주를 전국의 검문소에 일제히 배포했습니다."<br>*(Bộ Công an phát lệnh truy nã đỏ cấp A cùng tiền thưởng 20 vạn tệ và bản phác họa chân dung)* | `#D6` | Public Security Red Warrant indicators: `수배령`, `현상금`, `몽타주`, `1급 수배` (`lệnh truy nã đỏ`, `phác họa chân dung`). |
| 7 | "용의자는 황하 상류의 험준한 지형과 성 경계선을 넘어 공안의 관할 행정구역 밖으로 도주했습니다."<br>*(Nghi phạm đã vượt qua thượng nguồn sông Hoàng Hà và ranh giới tỉnh để trốn khỏi địa bàn quản hạt)* | `#M3` | River boundary and administrative evasion: `황하`, `성 경계선`, `행정구역`, `도주` (`ranh giới tỉnh`, `vượt sông`). |
| 8 | "당시 지역 방송국의 1998년 긴급 뉴스 특보는 CRT 브라운관 TV를 통해 도시 전체를 뒤덮은 공포를 생생히 보도했습니다."<br>*(Bản tin truyền hình khẩn cấp năm 1998 của đài địa phương phát qua màn hình TV CRT)* | `#P3` | Historical television broadcast cues: `방송국`, `뉴스 특보`, `CRT 브라운관 TV` (`truyền hình`, `màn hình CRT`). |
| 9 | "1988년 첫 번째 사건 이후 아무런 흔적도 남기지 않은 채 6년의 세월 동안 공포의 침묵이 이어졌습니다."<br>*(Sau vụ án đầu tiên năm 1988, khoảng lặng kéo dài 6 năm không để lại dấu vết)* | `#P1` | Unsolved timeline and years of silence: `1988년`, `6년의 세월`, `침묵`, `공백` (`khoảng lặng 6 năm`, `thời gian trôi`). |
| 10 | "입체 위성 지형 슬랩 위에 연쇄 사건들의 지리적 발생 좌표와 거리를 연결하자 명확한 동선 패턴이 드러났습니다."<br>*(Khi liên kết tọa độ và khoảng cách các vụ án trên khối bản đồ vệ tinh lập thể 3D)* | `#M5` | 3D coordinate connection: `입체 위성 지형 슬랩`, `좌표`, `거리`, `동선 패턴` (`khối bản đồ vệ tinh lập thể 3D`, `tọa độ`). |
| 11 | "희생자의 어머니는 차마 문을 열지 못한 채 차가운 바닥에 주저앉아 눈물만 흘리며 말을 잇지 못했습니다."<br>*(Người mẹ nạn nhân gục xuống sàn nhà lạnh lẽo, nghẹn ngào trong nước mắt không nói nên lời)* | `cinema_full` | Deep human sorrow and grief: `희생자의 어머니`, `차가운 바닥`, `눈물만 흘리며` (`nước mắt`, `nghẹn ngào`). Document shell suppressed. |

---

## 5. Anti-Repetition Mechanism Across Timeline Beats

### 5.1 The Repetition Problem
In investigative documentaries, multiple sequential beats frequently address the same evidence theme. For example:
- **Beat 14**: "형사들은 현장에 남겨진 지문 카드를 현미경으로 살폈습니다." (Triggers `#D1` / `#D9`)
- **Beat 15**: "하지만 23만 장의 데이터베이스에는 일치하는 인물이 없었습니다." (Also triggers `#D1`)
- **Beat 16**: "단 하나의 지문만이 유일한 희망이었습니다." (Also triggers `#D1` / `#D9`)

If the router operates in isolation, it selects `#D1` for all three beats, causing visual shell lock and audience fatigue.

### 5.2 Anti-Repetition Algorithm

```python
class VoxSemanticRouter:
    def __init__(self, history_size: int = 4):
        self.history_size = history_size
        self.recent_archetypes: list[str] = []

    def score_beat(self, text: str, recent_history: list[str]) -> str:
        candidates = []
        for arch_id, rule in VOX_ARCHETYPE_RULES.items():
            base_score = self._compute_base_match_score(text, rule)
            if base_score <= 0:
                continue

            # Recency Penalty calculation
            penalty = 0
            if recent_history:
                # Immediate predecessor (Beat i - 1): -80 points
                if recent_history[-1] == arch_id:
                    penalty += 80
                # Two beats ago (Beat i - 2): -40 points
                if len(recent_history) >= 2 and recent_history[-2] == arch_id:
                    penalty += 40
                # Same cluster predecessor (e.g. #M1 immediately after #M6): -25 points
                if self._same_cluster(recent_history[-1], arch_id):
                    penalty += 25

            final_score = max(0, base_score - penalty)
            candidates.append((final_score, arch_id, rule["cluster"]))

        if not candidates or all(c[0] == 0 for c in candidates):
            # Fallback to cinema_full if emotion or general narration, or rotating neutral dossier
            return "cinema_full" if recent_history and recent_history[-1] != "cinema_full" else "#D2"

        # Sort by final score descending
        candidates.sort(key=lambda x: x[0], reverse=True)
        chosen = candidates[0][1]

        # Update FIFO sliding history
        self.recent_archetypes.append(chosen)
        if len(self.recent_archetypes) > self.history_size:
            self.recent_archetypes.pop(0)

        return chosen
```

### 5.3 Semantic Cluster Groupings & Sibling Swapping
When high semantic affinity exists for a concept across multiple beats, the router swaps to a complementary sibling archetype within the same cluster rather than repeating:
- **Satellite Zoom Cluster**: `#M1` (Tactical Rooftop) ⇄ `#M6` (Split Dual Satellite)
- **Regional Corridor Cluster**: `#M2` (Satellite Corridor) ⇄ `#M3` (River/Boundary Crossing)
- **Fingerprint Minutiae Cluster**: `#D1` (Latent Print Paradox) ⇄ `#D9` (14-Point Minutiae) ⇄ `#D3` (3 Clues Triad)
- **Surveillance & Curfew Cluster**: `#M7` (Infrared Night Satellite) ⇄ `#P2` (Curfew Notice) ⇄ `#P3` (CRT Broadcast)
- **Dramatic Pause / Emotion**: Drops back to `cinema_full` whenever human suffering or reflection occurs.

---

## 6. Channel Profile Isolation & Safety Guardrails

### 6.1 Gating Rules
The Vox & Satellite engine must apply **strictly and exclusively** to `channel-e544a64b7c` (`특급수배록` / `true_crime_noir_ai` / `forensic_noir`).

```python
def is_vox_satellite_enabled(job: dict[str, Any], profile: dict[str, Any] | None = None) -> bool:
    """Verify whether Vox & Satellite engine should activate for this job/profile."""
    profile_id = str(
        job.get("channel_profile_id")
        or (profile or {}).get("id")
        or (job.get("channel_profile_snapshot") or {}).get("id")
        or ""
    ).strip()

    # 1. Primary White-listed Profile
    if profile_id == "channel-e544a64b7c":
        return True

    # 2. Strict Black-list for known non-crime channels
    if profile_id in {"channel-1e24de3ab5", "channel-aa913eb90d", "channel-f6ec4dfff3"}:
        return False

    # 3. Defensive Editing Preset Check
    preset_id = str(
        (job.get("editing_dna") or {}).get("preset_id")
        or ((profile or {}).get("editing_dna") or {}).get("preset_id")
        or ""
    ).strip().lower()
    if preset_id == "forensic_noir":
        return True

    return False
```

### 6.2 Protection of Non-Crime Channels
- `channel-1e24de3ab5` (Chinese Megaprojects & Geopolitics `판세의 이면`):
  Uses `2.5d_technical` editing DNA, `DanjiangkouDam` / `BaihetanDam` Remotion components, and infrastructure technical callouts (`KeyMetricCallout`, `MapSatelliteMotionStage`).
  -> The Vox True Crime router **returns False and completely bypasses archetype assignment**, preventing forensic red string boards or wanted warrants from appearing in engineering documentaries.
- `channel-f6ec4dfff3` (The First Family Vault):
  Uses `archival_historical` editing DNA, historical typewriter effects, and declassified stamps.
  -> The Vox True Crime router **returns False**, preserving US archival formatting.

---

## 7. Implementation Blueprint: Proposed CofiDocumentary Modules

To maintain clean architecture and code maintainability, two dedicated modules should be added to `b:\ALL_TOOLS\CofiDocumentary\documentary\`:

### 7.1 `documentary/vox_router.py`
- **Class `VoxSemanticRouter`**:
  - Encapsulates the trigger lexicon (`VOX_ARCHETYPE_RULES`), regex parsers, scoring engine, and sliding history window.
  - Exposes:
    - `route_beat(narration_text: str, metadata: dict | None = None, recent_history: list | None = None) -> dict`: Evaluates one beat.
    - `route_timeline(beats: list[dict], job: dict, profile: dict | None = None) -> list[dict]`: Routes all beats across a project timeline, maintaining chronological context and stamping `"scene_archetype": archetype_id` into each beat.
    - `is_applicable(job: dict, profile: dict | None = None) -> bool`: Enforces strict channel isolation.

### 7.2 `documentary/vox_renderer.py`
- **Class `VoxSceneRenderer`**:
  - Bridges the standalone PIL/NumPy compositor from `CofiBlenderStudio` into `CofiDocumentary`.
  - Points to `B:\ALL_TOOLS\CofiBlenderStudio\vox_gis_cache` for satellite plates.
  - Implements rendering methods for each archetype:
    - `render_satellite_frame(archetype, progress, base_plate, subtitle_text)`
    - `render_dossier_frame(archetype, progress, left_img, right_img, subtitle_text)`
    - `render_press_broadcast_frame(archetype, progress, bg_img, subtitle_text)`
    - `render_cinema_full_frame(img, subtitle_text, lower_third)`
  - Guarantees 1920x1080 dimensions, RGBA/RGB output, and loads `C:\Windows\Fonts\malgunbd.ttf` / `NanumGothicBold.ttf` with zero missing glyphs.

### 7.3 Integration Points in Existing Pipeline

```
1. documentary/visuals.py (Step 03: Visuals / STP):
   Inside VisualsCoordinator.run(...):
     if is_vox_satellite_enabled(job):
         router = VoxSemanticRouter()
         refined = router.route_timeline(refined, job)
   --> Each refined beat in visual_manifest.json receives:
       "scene_archetype": "#D4",
       "archetype_label": "Y-STR DNA Lightbox & Clan Pedigree Tree",
       "archetype_cluster": "biometrics"

2. services/editing_dna_service.py:
   Update BUILTIN_EDITING_PRESETS["forensic_noir"]["editing_archetypes"]:
     Include ["#M1_sat_rooftop_z16", "#M2_sat_corridor_z6_z9", "#M3_hukou_boundary_river",
              "#M4_crime_coords_distribution", "#M5_25d_tilted_slab", "#M6_split_dual_sat",
              "#M7_night_infrared_curfew", "#D1_fingerprint_comparator", "#D2_duality_dossier",
              "#D3_three_clues_dossier", "#D4_ydna_lightbox", "#D5_clipboard_interrogation",
              "#D6_wanted_warrant_sketch", "#D9_microscope_minutiae", "#P1_timeline_silence",
              "#P2_newspaper_curfew", "#P3_90s_tv_broadcast", "cinema_full"]

3. documentary/prompts.py (Step 06: Edit batch prompt):
   Inside build_edit_batch_prompt(...):
     if is_vox_satellite_enabled(job):
         Inject archetype execution rules instructing Remotion / Codex to render
         or mount the exact assigned archetype visual shell for each beat.
```

---

## 8. Test Suite & Independent Verification Framework

### 8.1 Test Files Location
Following CofiDocumentary's established testing structure (where tests are co-located in `B:\ALL_TOOLS\CofiDocumentary\tests\`), two new test suites should be placed at:
1. `B:\ALL_TOOLS\CofiDocumentary\tests\test_vox_semantic_router.py`
2. `B:\ALL_TOOLS\CofiDocumentary\tests\test_vox_scene_renderer.py`

### 8.2 Scope of `tests/test_vox_semantic_router.py`
1. **Diverse Semantic Sentences Test**:
   Passes 11+ distinct Korean and Vietnamese True Crime voice narration sentences covering all investigative domains into `VoxSemanticRouter.route_beat(...)`:
   - DNA genealogy -> asserts `#D4`
   - Campus store raid -> asserts `#M1` or `#M6`
   - Night curfew / lockdown -> asserts `#M7` or `#P2`
   - Fingerprint ridge points -> asserts `#D1` or `#D9`
   - Interrogation confession -> asserts `#D5`
   - Wanted warrant & composite sketch -> asserts `#D6`
   - Provincial river escape -> asserts `#M2` or `#M3`
   - 1990s TV broadcast -> asserts `#P3`
   - Years of silence timeline -> asserts `#P1`
   - 3D spatial coordinates -> asserts `#M5`
   - Emotional grief / weeping -> asserts `cinema_full`
2. **Anti-Repetition Sequence Test**:
   Passes a sequence of 4 consecutive beats all mentioning "지문" (fingerprint).
   - Verifies Beat 1 selects `#D1`.
   - Verifies Beat 2 selects `#D9` (sibling minutiae comparator, NOT repeating `#D1`).
   - Verifies Beat 3 selects `#D3` (triad evidence) or `cinema_full`.
   - Asserts `beat[1].archetype != beat[0].archetype`.
3. **Strict Channel Isolation Test**:
   - Tests `is_vox_satellite_enabled` for `channel-e544a64b7c` -> returns `True`.
   - Tests `is_vox_satellite_enabled` for `channel-1e24de3ab5` -> returns `False`.
   - Tests `is_vox_satellite_enabled` for `channel-f6ec4dfff3` -> returns `False`.
   - Verifies that running `route_timeline` on a `channel-1e24de3ab5` job does not attach True Crime archetypes to beats.

### 8.3 Scope of `tests/test_vox_scene_renderer.py`
1. **Cached GIS Plate Loading Test**:
   - Asserts that `plate_baiyin_campus_sat_z16.png`, `plate_baiyin_city_sat_z14.png`, `plate_baiyin_lanzhou_sat_z9.png`, and `plate_gansu_sat_z6.png` load from `b:\ALL_TOOLS\CofiBlenderStudio\vox_gis_cache` without error.
2. **1920x1080 Frame Rendering Test**:
   - Renders sample frames for `#M1` (Satellite Rooftop), `#D4` (Y-DNA Lightbox), `#D5` (Clipboard Interrogation), `#D6` (Wanted Warrant), `#D9` (Microscope Minutiae), and `#P3` (CRT Broadcast).
   - Validates that every rendered output is exactly `(1920, 1080)` with mode `RGB`.
3. **Hangul & CJK Typography Verification**:
   - Verifies Korean text rendering using `malgunbd.ttf` / `malgun.ttf`.
   - Checks bounding boxes to ensure zero text overflow, zero line clipping, and zero undefined glyph boxes (`□`).

### 8.4 Verification Execution Command
The tests can be executed independently using the host Python binary:
```powershell
C:\Users\koing\AppData\Local\python\bin\python.exe -m pytest tests\test_vox_semantic_router.py tests\test_vox_scene_renderer.py -v
```

---

## 9. Conclusion

CofiDocumentary has a robust foundation in channel DNA isolation and timeline generation, but currently lacks the granular voice-driven archetype routing and tactile forensic/satellite compositing required for `channel-e544a64b7c`. 

By introducing `VoxSemanticRouter` and connecting the standalone PIL compositor and Esri satellite tile cache from `CofiBlenderStudio`, CofiDocumentary can seamlessly transform raw spoken narration into authored, cinematic True Crime investigative scenes with dynamic anti-repetition protection and zero collateral impact on non-crime profiles.
