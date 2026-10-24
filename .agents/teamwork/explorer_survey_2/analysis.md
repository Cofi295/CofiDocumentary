# Comprehensive Codebase Analysis: Persistent Channel SEO Keyword DNA (Requirement R2 & AC2)

## 1. Executive Summary

Requirement **R2** and Acceptance Criteria **AC2** require extending **CofiDocumentary** with persistent, isolated **Channel SEO Keyword DNA** (`seo_keyword_dna` / `seo_dna`). This ensures that every Channel Profile (`channel_profiles`) and linked Project (`jobs`) locks and enforces core keyword anchors (e.g., `중국 실화 사건` / `"Vụ Án Có Thật ở Trung Quốc"` for the Korean-market Chinese True Crime channel `channel-e544a64b7c`) across all stages of documentary production:
1. **Step 0 (Channel Profile Studio)**: Configure, view, edit, and persist the channel's `seo_keyword_dna`.
2. **Step 00 (Topic & Title Suggestions / Idea Discovery)**: Suggested titles automatically integrate and align with the channel's `primary_title_keyword` and `secondary_anchor_keywords` (with bilingual display: target-language title + Vietnamese translation + SEO Keyword DNA badge).
3. **Step 01 (Script & Hook Generation)**: Inject the channel's SEO Keyword DNA into the directorial prompt so opening hooks and narrative theses build unified topical authority.
4. **Step 07 (Thumbnail & SEO Package)**: Enforce the `primary_title_keyword`, `secondary_anchor_keywords`, description keyword hooks, `mandatory_hashtags`, and `default_seo_tags` in `seo_package.json`.
5. **Channel-DNA Pre-Flight Check**: Validate topic titles and SEO packages against the channel's SEO Keyword DNA before publishing.

---

## 2. Codebase Architecture & Component Inventory

### 2.1 Persistence Layer
- **`data/channel_profiles.json`**: Primary JSON store for all Channel Profiles (`profiles` array). Managed by `ChannelProfileService` (`services/channel_profile_service.py`) and synchronized with `DocumentaryService` (`documentary/service.py`).
  - **Observation**: Currently contains 4 channel profiles (`channel-aa913eb90d`, `channel-e544a64b7c`, `channel-1e24de3ab5`, `channel-f6ec4dfff3`).
  - **Gap**: None of the 4 profiles currently possess an explicit top-level `seo_keyword_dna` block (only a minimal `self_learning_memory.seo_dna` tag list exists on 2 profiles).
- **`data/jobs/<job_id>/job.json` & `workspaces/<job_id>/input.json`**: Project persistence store. Managed by `JobStore` (`documentary/store.py`) and `JobService` (`services/job_service.py`).
  - **Gap**: When jobs are created with `channel_profile_id`, they inherit `visual_strategy`, `editing_dna`, and `creative_brief`, but do NOT inherit `seo_keyword_dna`.

### 2.2 Model & Validation Layer
- **`services/channel_profile_service.py`**:
  - Defines Pydantic models: `SubtitleStyleModel`, `AudioRulesModel`, `EditingDnaModel`, `UpgradeRulesModel`, `SelfLearningMemoryModel`, `DefaultCreativeBriefModel`, `ChannelProfileCreateModel`, `ChannelProfileUpdateModel`.
  - **Observation**: Lines 126–180 omit `seo_keyword_dna` and `seo_dna`.
  - **Observation**: `update_profile` (lines 437–442) preserves and deep-merges nested objects for `default_creative_brief`, `editing_dna`, and `self_learning_memory`, but does not yet include `seo_keyword_dna`.
- **`documentary/models.py`**: Defines pipeline phases (`PHASES`), required artifacts (`REQUIRED_ARTIFACTS`), and `effective_phases`. `seo` phase requires `seo_package.json`.
- **`app.py`**:
  - `ChannelProfileRequest` (line 252): Pydantic v2 model used for `POST /api/radar/channel-profiles` and `PATCH /api/radar/channel-profiles/{profile_id}`.
  - **Observation**: Omits `seo_keyword_dna: dict[str, Any] | None = None`. In Pydantic v2, extra fields are stripped by default during `.model_dump()`.
  - `CreateJobRequest` (line 40): Omits `seo_keyword_dna: dict[str, Any] | None = None`.

### 2.3 Business Logic & Service Layer
- **`services/channel_profile_service.py`**:
  - `create_profile()`: Initializes default profile schemas. Needs default `seo_keyword_dna`.
  - `update_profile()`: Needs deep merge for `seo_keyword_dna`.
  - `clone_profile()`: Needs deep copy of `seo_keyword_dna`.
- **`services/job_service.py`**:
  - `create_job()` (lines 77–150): When `channel_profile_id` is provided, copies `editing_dna`, `visual_strategy`, and `creative_brief`. Needs to copy `seo_keyword_dna` into `job_data["seo_keyword_dna"]` and `job_data["channel_profile_snapshot"]["seo_keyword_dna"]`.
- **`documentary/service.py`**:
  - `save_channel_profile()` (lines 5811–6045): Extracts fields and saves `data/channel_profiles.json`. Needs to extract `seo_keyword_dna` from payload.
  - `create_job()` (lines 296–480): Service-level job creator. Needs to copy `seo_keyword_dna` from `profile` into `initial["seo_keyword_dna"]` and `channel_profile_snapshot`.
  - `channel_profile_today()` & `_discover_profile_topics_strict_dna()` (lines 6959–7320): Generates topic/title candidates for Step 00. Needs to apply `seo_keyword_dna` to generated titles based on `keyword_placement_rule`.
  - `_seo_reference_context()` (lines 6144–6250): Prepares `seo_reference_context.json` for Step 07. Needs to include `context["seo_keyword_dna"]`.
- **`services/preflight_service.py`**:
  - `check()` (lines 100–365): Runs pre-flight checks for `topic`, `thumbnail`, and `seo`. Needs to validate `primary_title_keyword`, `secondary_anchor_keywords`, and `mandatory_hashtags`.
- **`documentary/prompts.py`**:
  - `_job_context()` (line 161): Serializes job fields for Codex prompts. Needs `seo_keyword_dna`.
  - `build_phase_prompt()` (line 369): Needs `_seo_keyword_dna_direction()` to guide Step 01 Script Hook and Step 07 SEO Packaging.
- **`documentary/quality.py`**:
  - `validate_phase_quality()` (lines 213–265): Validates `seo_package.json`. Needs to enforce presence of `primary_title_keyword` in titles and merge `mandatory_hashtags` and `default_seo_tags`.

### 2.4 Frontend UI / UX Layer
- **`static/index.html`**:
  - Line 170 (`#channelProfileForm`): Needs a dedicated `SEO KEYWORD DNA` subcard with form fields for `primary_title_keyword`, `primary_title_keyword_meaning_vi`, `keyword_placement_rule`, `secondary_anchor_keywords`, `mandatory_hashtags`, and `default_seo_tags`.
  - Line 463 (`#createTopicDiscovery` & `#createTopicSuggestions`): Cards need to render the SEO Keyword DNA badge, Korean/target title, and Vietnamese translation.
- **`static/app.js`**:
  - `resetChannelProfileForm()` (lines 2845–2889): Must reset SEO Keyword DNA form fields.
  - `fillChannelProfileForm()` (lines 2915–3004): Must populate SEO Keyword DNA form fields from `profile.seo_keyword_dna`.
  - `#channelProfileForm` submit handler (lines 3424–3448): Must serialize `seo_keyword_dna` into the save payload.
  - `renderCreateTopicSuggestions()` (lines 2344–2404): Must parse dual titles (target language + Vietnamese) and render the SEO Keyword DNA badge on each suggested topic card.
  - `selectCreateTopic()` (lines 2307–2340): Must display the SEO Keyword DNA badge and dual title in `#selectedTopicBadge`.

---

## 3. Schema & Data Structure Definition: `seo_keyword_dna`

The structured `seo_keyword_dna` configuration must be placed directly on each Channel Profile and inherited by each linked Project:

```json
{
  "seo_keyword_dna": {
    "primary_title_keyword": "중국 실화 사건",
    "primary_title_keyword_meaning_vi": "Vụ Án Có Thật ở Trung Quốc",
    "keyword_placement_rule": "smart_seo_flexible",
    "secondary_anchor_keywords": [
      "중국 미제사건",
      "실제 사건 파일",
      "공안 수사 기록",
      "특급수배록",
      "중국 강력범죄 실화"
    ],
    "mandatory_hashtags": [
      "#중국실화사건",
      "#특급수배록",
      "#중국미제사건",
      "#실화사건"
    ],
    "default_seo_tags": [
      "중국실화사건",
      "특급수배록",
      "중국미제사건",
      "실제사건파일",
      "공안수사기록",
      "중국강력범죄실화",
      "그것이알고싶다",
      "범죄실화"
    ]
  }
}
```

### Keyword Placement Rules:
1. **`smart_seo_flexible` (Default)**:
   - If title contains a dramatic quotation or dash (`'...' —`), prepends bracket: `[{primary_title_keyword}] {target_title}`.
   - If title is concise without quotes, appends pipe: `{target_title} | {primary_title_keyword}`.
   - If `primary_title_keyword` is already naturally embedded in `{target_title}`, avoids redundant repetition.
2. **`prefix_bracket`**: Force bracket prefix: `[{primary_title_keyword}] {target_title}`.
3. **`suffix_pipe`**: Force pipe suffix: `{target_title} | {primary_title_keyword}`.
4. **`natural_hook`**: Integrates keyword naturally within the first 40 characters or opening clause.

---

## 4. Current State & Configuration for the 4 Channel Profiles

| Profile ID | Channel Name / Niche | Market / Lang | Current `seo_keyword_dna` | Canonical `seo_keyword_dna` Configuration Required |
|---|---|---|---|---|
| `channel-e544a64b7c` | **특급수배록** · True Crime Hình Sự Trung Quốc (30p Full AI) | KR / `ko` | **Missing** (None) | **Primary Keyword**: `중국 실화 사건`<br>**Meaning (VI)**: `"Vụ Án Có Thật ở Trung Quốc"`<br>**Placement**: `smart_seo_flexible`<br>**Secondary**: `["중국 미제사건", "실제 사건 파일", "공안 수사 기록", "특급수배록", "중국 강력범죄 실화"]`<br>**Hashtags**: `["#중국실화사건", "#특급수배록", "#중국미제사건", "#실화사건"]`<br>**Tags**: `["중국실화사건", "특급수배록", "중국미제사건", "실제사건파일", "공안수사기록", "중국강력범죄실화", "그것이알고싶다", "범죄실화"]` |
| `channel-1e24de3ab5` | **판세의 이면** · Đại Công Trình & Hạ Tầng Trung Quốc (22p Hybrid) | KR / `ko` | **Missing** (None) | **Primary Keyword**: `중국 인프라의 이면`<br>**Meaning (VI)**: `"Mặt Tối & Đại Công Trình Hạ Tầng Trung Quốc"`<br>**Placement**: `smart_seo_flexible`<br>**Secondary**: `["판세의 이면", "중국 대공정", "남수북조", "삼협댐", "토목공학", "지질 역학"]`<br>**Hashtags**: `["#판세의이면", "#중국인프라", "#남수북조", "#대공정"]`<br>**Tags**: `["판세의이면", "중국인프라", "중국대공정", "남수북조", "삼협댐", "토목공학", "지반침하", "팽창토"]` |
| `channel-aa913eb90d` | **bí mật US** · Archival Vault & Intelligence Declassification | US / `en` | **Missing** (None) | **Primary Keyword**: `Declassified US Intelligence Files`<br>**Meaning (VI)**: `"Hồ Sơ Giải Mật Tình Báo Hoa Kỳ"`<br>**Placement**: `smart_seo_flexible`<br>**Secondary**: `["Declassified Files", "Cold War Vault", "CIA Project", "National Archives"]`<br>**Hashtags**: `["#Declassified", "#ColdWarVault", "#CIAFiles", "#USHistory"]`<br>**Tags**: `["Declassified", "National Archives", "Cold War", "Project Azorian", "CIA", "Intelligence Vault"]` |
| `channel-f6ec4dfff3` | **The First Family Vault** · Presidential Records & Executive Forensics | US / `en` | **Missing** (None) | **Primary Keyword**: `Presidential Records & Executive Forensics`<br>**Meaning (VI)**: `"Hồ Sơ Tổng Thống & Mệnh Lệnh Mật"`<br>**Placement**: `smart_seo_flexible`<br>**Secondary**: `["Presidential Archives", "Executive Orders", "White House Tapes", "Secret History"]`<br>**Hashtags**: `["#PresidentialRecords", "#WhiteHouseVault", "#ExecutiveOrders", "#AmericanHistory"]`<br>**Tags**: `["Presidential Vault", "Executive Orders", "National Archives", "White House Tapes", "Secret Memos"]` |

---

## 5. Cross-Pipeline Execution & Enforcement Flow

```
+---------------------------------------------------------------------------------------------------+
| STEP 0: CHANNEL PROFILE STUDIO                                                                    |
| - Channel Profile defines `seo_keyword_dna`                                                       |
| - Backfilled into data/channel_profiles.json & scripts/backfill_migration.py                      |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| STEP 00: CREATE PROJECT & TOPIC DISCOVERY                                                         |
| - `channel_profile_today()` & `_discover_profile_topics_strict_dna()`                              |
| - Automatically applies `apply_seo_keyword_dna_to_title(title, seo_dna)`                          |
| - UI `#createTopicSuggestions` displays SEO Keyword DNA badge + Korean title + Vietnamese meaning |
| - Job creation inherits `seo_keyword_dna` into `job.json`, `input.json`, and profile snapshot    |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| STEP 01: SCRIPT & OUTLINE HOOK                                                                    |
| - `build_phase_prompt()` injects `_seo_keyword_dna_direction()`                                   |
| - Instructs AI to anchor opening hook and thesis to `primary_title_keyword` & secondary keywords   |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| STEP 07: THUMBNAIL & SEO PACKAGE                                                                  |
| - `_seo_reference_context()` embeds `context["seo_keyword_dna"]`                                   |
| - SEO Phase Prompt requires `recommended_title` to follow `keyword_placement_rule`                |
| - `validate_phase_quality("seo")` verifies title keywords and merges mandatory tags/hashtags     |
| - Pre-Flight Check verifies compliance against channel DNA                                        |
+---------------------------------------------------------------------------------------------------+
```

### 5.1 Step 00 Title Formatting Algorithm
```python
def apply_seo_keyword_dna_to_title(
    title: str,
    seo_dna: dict[str, Any] | None,
    rule: str | None = None
) -> tuple[str, str, str]:
    """
    Returns (formatted_full_title, target_language_title, vi_translation).
    Handles titles formatted like 'Korean Title (Vietnamese Meaning)'
    and incorporates the primary_title_keyword cleanly.
    """
    if not seo_dna or not seo_dna.get("primary_title_keyword"):
        # Split target and VI if parentheses present
        match = re.match(r"^(.*?)\s*\((.*?)\)$", title.strip())
        if match:
            return title, match.group(1).strip(), match.group(2).strip()
        return title, title, ""

    primary_kw = str(seo_dna["primary_title_keyword"]).strip()
    meaning_vi = str(seo_dna.get("primary_title_keyword_meaning_vi") or "").strip()
    rule = rule or seo_dna.get("keyword_placement_rule") or "smart_seo_flexible"

    # Separate target title from Vietnamese translation if enclosed in parentheses
    match = re.match(r"^(.*?)\s*\((.*?)\)$", title.strip())
    if match:
        target_part = match.group(1).strip()
        vi_part = match.group(2).strip()
    else:
        target_part = title.strip()
        vi_part = ""

    # Check if primary_kw is already present in target_part
    if primary_kw.lower() not in target_part.lower():
        if rule == "prefix_bracket" or (rule == "smart_seo_flexible" and ("—" in target_part or "'" in target_part or '"' in target_part)):
            target_formatted = f"[{primary_kw}] {target_part}"
            vi_formatted = f"[{meaning_vi}] {vi_part}" if meaning_vi and vi_part else vi_part
        elif rule == "suffix_pipe":
            target_formatted = f"{target_part} | {primary_kw}"
            vi_formatted = f"{vi_part} | {meaning_vi}" if meaning_vi and vi_part else vi_part
        else: # natural_hook or fallback
            target_formatted = f"[{primary_kw}] {target_part}"
            vi_formatted = f"[{meaning_vi}] {vi_part}" if meaning_vi and vi_part else vi_part
    else:
        target_formatted = target_part
        vi_formatted = vi_part

    full_title = f"{target_formatted} ({vi_formatted})" if vi_formatted else target_formatted
    return full_title, target_formatted, vi_formatted
```

### 5.2 Step 01 Script Hook Direction
In `documentary/prompts.py`:
```python
def _seo_keyword_dna_direction(job: dict[str, Any]) -> str:
    seo_dna = job.get("seo_keyword_dna") or (job.get("channel_profile_snapshot") or {}).get("seo_keyword_dna")
    if not seo_dna or not seo_dna.get("primary_title_keyword"):
        return ""
    primary = seo_dna.get("primary_title_keyword")
    meaning_vi = seo_dna.get("primary_title_keyword_meaning_vi") or ""
    secondary = seo_dna.get("secondary_anchor_keywords") or []
    return f"""
CHANNEL SEO KEYWORD DNA — TOPICAL AUTHORITY REQUIREMENTS:
- Primary Title / Channel Anchor Keyword: "{primary}" ({meaning_vi})
- Secondary Anchor Keywords: {json.dumps(secondary, ensure_ascii=False)}
- For Step 01 (Script & Hook): The opening hook (00:00-02:30) and research thesis must explicitly anchor the investigation around the core niche authority phrase "{primary}".
"""
```

### 5.3 Step 07 SEO Package Post-Processing & Quality Enforcement
In `documentary/quality.py` (`validate_phase_quality`):
```python
if phase == "seo":
    seo_dna = job.get("seo_keyword_dna") or (job.get("channel_profile_snapshot") or {}).get("seo_keyword_dna")
    if seo_dna and isinstance(seo_dna, dict):
        primary_kw = str(seo_dna.get("primary_title_keyword") or "").strip().lower()
        if primary_kw:
            rec_title = str(package.get("recommended_title") or "").lower()
            title_opts = [str(t).lower() for t in (package.get("title_options") or [])]
            # Verify primary_kw is present in recommended_title or at least one title_option
            has_primary = primary_kw in rec_title or any(primary_kw in opt for opt in title_opts)
            if not has_primary:
                # Enforce rule: auto-wrap recommended title with bracket
                placement = seo_dna.get("keyword_placement_rule") or "smart_seo_flexible"
                orig_title = str(package.get("recommended_title") or "")
                raw_kw = seo_dna.get("primary_title_keyword")
                if placement == "suffix_pipe":
                    package["recommended_title"] = f"{orig_title} | {raw_kw}"
                else:
                    package["recommended_title"] = f"[{raw_kw}] {orig_title}"

        # Merge mandatory hashtags
        mand_hashtags = seo_dna.get("mandatory_hashtags") or []
        current_hashtags = list(package.get("hashtags") or [])
        for ht in mand_hashtags:
            if ht not in current_hashtags:
                current_hashtags.append(ht)
        package["hashtags"] = current_hashtags

        # Merge default tags
        def_tags = seo_dna.get("default_seo_tags") or []
        current_tags = list(package.get("tags") or [])
        for t in def_tags:
            if t not in current_tags:
                current_tags.append(t)
        package["tags"] = current_tags

        # Write back updated package
        (workspace / "seo_package.json").write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
```

---

## 6. Frontend UI / UX Implementation Details

### 6.1 Step 0: Channel Profile Form (`static/index.html`)
Add a new subcard inside `#channelProfileForm`:
```html
<div class="dna-rulebook-box saas-subcard" id="channelSeoKeywordDnaBox" style="margin-top:14px;">
  <div class="dna-rulebook-head">
    <span>🔑 TỪ KHÓA SEO TRỤ CỘT &amp; THƯƠNG HIỆU KÊNH (SEO KEYWORD DNA)</span>
    <small>Khóa cứng từ khóa thương hiệu bản ngữ và quy tắc đặt tên để 100% video trên kênh tạo authority đồng nhất.</small>
  </div>
  <div class="saas-form-grid saas-grid-3">
    <label>Từ khóa Tiêu đề Chủ lực (Primary Title Keyword)
      <input name="primary_title_keyword" id="channelPrimaryTitleKeyword" placeholder="VD: 중국 실화 사건" />
    </label>
    <label>Ý nghĩa Tiếng Việt (Vietnamese Meaning)
      <input name="primary_title_keyword_meaning_vi" id="channelPrimaryTitleKeywordMeaningVi" placeholder="VD: Vụ Án Có Thật ở Trung Quốc" />
    </label>
    <label>Quy tắc gắn Từ khóa vào Tiêu đề
      <select name="keyword_placement_rule" id="channelKeywordPlacementRule">
        <option value="smart_seo_flexible" selected>Linh hoạt thông minh (smart_seo_flexible)</option>
        <option value="prefix_bracket">Đầu tiêu đề trong ngoặc vuông [Từ khóa]</option>
        <option value="suffix_pipe">Cuối tiêu đề sau gạch đứng | Từ khóa</option>
        <option value="natural_hook">Tự nhiên trong câu Hook mở màn</option>
      </select>
    </label>
  </div>
  <div class="saas-form-grid saas-grid-3">
    <label>Từ khóa ngách lặp lại (Secondary Anchors)
      <input name="secondary_anchor_keywords" id="channelSecondaryAnchorKeywords" placeholder="VD: 중국 미제사건, 실제 사건 파일, 공안 수사 기록, 특급수배록" />
    </label>
    <label>Hashtag bắt buộc (Mandatory Hashtags)
      <input name="mandatory_hashtags" id="channelMandatoryHashtags" placeholder="VD: #중국실화사건, #특급수배록, #중국미제사건, #실화사건" />
    </label>
    <label>Tags YouTube mặc định (Default Tags)
      <input name="default_seo_tags" id="channelDefaultSeoTags" placeholder="VD: 중국실화사건, 특급수배록, 중국미제사건, 실제사건파일, 공안수사기록" />
    </label>
  </div>
</div>
```

### 6.2 Step 00: Topic Suggestion Cards (`static/app.js`)
In `renderCreateTopicSuggestions`:
Render each card with:
```html
<article class="create-topic-option">
  <div class="create-topic-option-rank">${String(index + 1).padStart(2, "0")}</div>
  <div class="create-topic-option-body">
    ${seoDnaBadgeHtml}
    <div class="topic-title-dual">
      <div class="topic-title-target"><b>${escapeHtml(targetTitle)}</b></div>
      ${viTitle ? `<div class="topic-title-vi">🇻🇳 <i>${escapeHtml(viTitle)}</i></div>` : ""}
    </div>
    ${detail ? `<div class="topic-metrics"><span>${escapeHtml(detail)}</span></div>` : ""}
    ${hookPreview}
    ${item.note ? `<span>${escapeHtml(item.note)}</span>` : ""}
  </div>
  <button class="ghost compact" type="button" data-create-topic-index="${index}">Chọn đề tài này</button>
</article>
```
Where `seoDnaBadgeHtml` is:
```html
<div class="topic-seo-badge-row" style="margin-bottom:4px;">
  <span class="badge" style="background:rgba(234,179,8,0.15);color:#facc15;border:1px solid rgba(234,179,8,0.3);font-size:11px;padding:2px 8px;border-radius:6px;font-weight:700;">
    🔑 SEO DNA: [${escapeHtml(primaryKeyword)}] · ${escapeHtml(meaningVi)}
  </span>
</div>
```

---

## 7. Existing Test Coverage & Verification Strategy

### 7.1 Existing Coverage
- `tests/test_channel_profiles.py`: 21 unit tests covering CRUD, Radar scan recovery, and basic profile isolation.
- `tests/test_adversarial_profile_challenge.py`: 16 adversarial tests verifying that cloning generates distinct IDs and preserves deep configurations (`editing_dna`, `default_creative_brief`, `self_learning_memory`).
- `tests/test_m1_backend_isolation_backfill.py`: 17 tests verifying non-null fields on canonical profiles.
- `tests/test_anti_duplicate_memory_and_workspace.py`: 7 tests verifying 2-layer pre-flight check, topic memory CRUD, and topic exclusion.

### 7.2 Required New Test Suite for AC2 (`tests/test_channel_seo_keyword_dna.py`)
A dedicated automated test suite must be added to verify:
1. **Channel Profiles Persist `seo_keyword_dna`**:
   - Verify `GET /api/radar/channel-profiles/channel-e544a64b7c` contains `seo_keyword_dna` with `primary_title_keyword: "중국 실화 사건"`, `primary_title_keyword_meaning_vi: "Vụ Án Có Thật ở Trung Quốc"`, `keyword_placement_rule`, `secondary_anchor_keywords`, and `mandatory_hashtags`.
   - Verify all 4 profiles (`channel-e544a64b7c`, `channel-1e24de3ab5`, `channel-aa913eb90d`, `channel-f6ec4dfff3`) have valid, non-empty `seo_keyword_dna`.
2. **Profile CRUD & Clone Deep Independence**:
   - Creating/updating a profile preserves `seo_keyword_dna`.
   - Cloning `channel-e544a64b7c` deep-copies its `seo_keyword_dna` without reference sharing.
   - Partial updates to a profile do not delete unmentioned sibling keys in `seo_keyword_dna`.
3. **Job Inheritance**:
   - Creating a job with `channel_profile_id: "channel-e544a64b7c"` locks `seo_keyword_dna` into `job["seo_keyword_dna"]` and `job["channel_profile_snapshot"]["seo_keyword_dna"]`.
4. **Step 00 Topic/Title Suggestions Enforce Keyword DNA**:
   - `channel_profile_today("channel-e544a64b7c")` returns candidates that incorporate `중국 실화 사건` according to `smart_seo_flexible` (or `prefix_bracket`).
5. **Step 07 SEO Package Quality & Preflight Enforcement**:
   - Running `validate_phase_quality("seo", ...)` or generating SEO package enforces `primary_title_keyword` in `recommended_title` / `title_options`, and automatically merges `mandatory_hashtags` and `default_seo_tags`.
   - Running `PreflightService.check(profile, stage="seo", ...)` reports compliance with the channel's `seo_keyword_dna`.

---

## 8. Implementation Blueprint for Implementer

1. **`data/channel_profiles.json` & `scripts/backfill_migration.py`**:
   - Update canonical backfill definitions with accurate `seo_keyword_dna` for all 4 profiles.
   - Run non-destructive backfill migration script to update `data/channel_profiles.json`.
2. **`services/channel_profile_service.py`**:
   - Add `SeoKeywordDnaModel` Pydantic schema.
   - Add `seo_keyword_dna` to `ChannelProfileCreateModel` and `ChannelProfileUpdateModel`.
   - Support `seo_keyword_dna` deep merge in `update_profile` and deep copy in `clone_profile`.
3. **`services/job_service.py`**:
   - Copy `seo_keyword_dna` from profile into new job and snapshot.
4. **`app.py` & `server.py`**:
   - Add `seo_keyword_dna` to `ChannelProfileRequest` and `CreateJobRequest`.
5. **`documentary/service.py`**:
   - In `save_channel_profile()`, extract `seo_keyword_dna`.
   - In `create_job()`, copy `seo_keyword_dna`.
   - In `channel_profile_today()` & `_discover_profile_topics_strict_dna()`, format candidate titles using `apply_seo_keyword_dna_to_title()`.
   - In `_seo_reference_context()`, embed `context["seo_keyword_dna"]`.
6. **`documentary/prompts.py`**:
   - Add `_seo_keyword_dna_direction()` to `build_phase_prompt()`.
7. **`documentary/quality.py`**:
   - Enforce `primary_title_keyword` and merge `mandatory_hashtags` in `validate_phase_quality()`.
8. **`services/preflight_service.py`**:
   - Check `primary_title_keyword` and `mandatory_hashtags` in `check()`.
9. **`static/index.html` & `static/app.js`**:
   - Add `SEO Keyword DNA` UI subcard in Step 0.
   - Add reset, populate, and save logic in `app.js`.
   - Render SEO Keyword DNA badge and dual title in Step 00 topic cards.
10. **`tests/test_channel_seo_keyword_dna.py`**:
    - Write and verify comprehensive test suite for AC2.
