"""Dynamic Context-Aware Audio Library Manager & Auto-Fetcher for CofiDocumentary.

Ensures every documentary episode has a rich, context-matched Foley SFX and
multi-mood BGM library. Never repeats the same 1-2 SFX mechanically across a
video; selects audio based on narrative context, emotional tone, and visual
archetype, and can automatically fetch new CC0/open-licensed audio from
Wikimedia Commons when a specialized scene requires new sound design.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRESET_AUDIO_DIR = PROJECT_ROOT / "presets" / "audio_library"
REMOTION_AUDIO_DIR = Path(r"B:\ALL_TOOLS\CofiRemotion\public\audio_library")

USER_AGENT = "CofiDocumentaryStudio/2.0 (https://github.com/cofi-studio; contact@cofi.local)"

# Canonical catalog of 28 context-specific Foley SFX & 7 multi-mood BGM beds
CONTEXTUAL_SFX_CATALOG: dict[str, dict[str, Any]] = {
    # Judicial, Legal & Verdict
    "sfx_gavel_hit.mp3": {
        "category": "judicial",
        "description": "Courtroom wooden gavel strike / verdict pronouncement",
        "keywords": ["법원", "판결", "선고", "재판", "재심", "사형", "법정", "판사", "징역", "감형", "무기징역", "court", "verdict", "trial", "gavel", "sentence"],
        "commons_source": "File:Knocking on wood or door.ogg",
        "trim_sec": 1.35,
        "af_filter": "asetrate=44100*0.88,aresample=44100,lowpass=f=3800,afade=t=in:st=0:d=0.01,afade=t=out:st=0.95:d=0.40,volume=0.85",
    },
    "sfx_dossier_stamp.mp3": {
        "category": "judicial",
        "description": "Official ink stamp on legal/confidential dossier",
        "keywords": ["도장", "직인", "비준", "승인", "기밀", "문건", "공문", "결정문", "집행", "stamp", "approved", "classified"],
    },
    "sfx_official_seal_thud.mp3": {
        "category": "judicial",
        "description": "Heavy institutional seal & case-closed folder thud",
        "keywords": ["최고인민법원", "특허", "특혜", "사면", "석방", "집행유예", "확정", "최종", "seal", "supreme court"],
        "base_mix": ("sfx_dossier_stamp.mp3", "sfx_soft_impact.mp3"),
        "trim_sec": 1.4,
        "af_filter": "asetrate=44100*0.84,aresample=44100,lowpass=f=2800,afade=t=out:st=0.9:d=0.45,volume=0.80",
    },
    "sfx_court_bell_toll.mp3": {
        "category": "judicial",
        "description": "Solemn low bronze bell chime for final reckoning / execution",
        "keywords": ["사형 집행", "처형", "최후", "종말", "영원히", "역사", "정의", "심판", "execution", "reckoning"],
        "commons_source": "File:Striking a bell 15cm large.ogg",
        "trim_sec": 2.4,
        "af_filter": "asetrate=44100*0.58,aresample=44100,lowpass=f=2400,afade=t=in:st=0:d=0.03,afade=t=out:st=1.4:d=1.0,volume=0.65",
    },
    # Prison, Custody & Iron Gates
    "sfx_cell_door.mp3": {
        "category": "prison",
        "description": "Heavy prison iron gate / cell door closing",
        "keywords": ["교도소", "감옥", "수감", "독방", "구치소", "철창", "복역", "이감", "prison", "jail", "cell"],
    },
    "sfx_iron_lock_latch.mp3": {
        "category": "prison",
        "description": "Metallic prison lock latch / handcuff arrest click",
        "keywords": ["체포", "구속", "수갑", "연행", "압송", "제1교도소", "제2교도소", "감방", "arrest", "lock", "custody"],
        "commons_source": "File:342701 spacejoe lock-3-close-lock-1.wav",
        "trim_sec": 1.2,
        "af_filter": "highpass=f=120,lowpass=f=5200,afade=t=in:st=0:d=0.01,afade=t=out:st=0.8:d=0.38,volume=0.78",
    },
    "sfx_footsteps_corridor.mp3": {
        "category": "prison",
        "description": "Measured footsteps in stone corridor / night patrol",
        "keywords": ["복도", "밤", "새벽", "잠입", "출입", "호위", "간수", "행보", "corridor", "footsteps", "walk"],
        "commons_source": "File:Pasos en escalera de caracol.ogg",
        "trim_sec": 1.8,
        "af_filter": "lowpass=f=3200,afade=t=in:st=0:d=0.08,afade=t=out:st=1.2:d=0.55,volume=0.72",
    },
    # Press, Newspaper & Archival Paper
    "sfx_paper_turn.mp3": {
        "category": "editorial",
        "description": "Crisp archival dossier page turn",
        "keywords": ["기록", "페이지", "서류", "파일", "문서", "조서", "진술서", "열람", "page", "document"],
    },
    "sfx_newspaper_unfold.mp3": {
        "category": "editorial",
        "description": "Broadsheet newspaper unfolding / press exposé reveal",
        "keywords": ["신문", "보도", "언론", "기사", "특종", "폭로", "헤드라인", "취재", "기자", "newspaper", "press"],
        "base_mix": ("sfx_paper_turn.mp3", "sfx_soft_whoosh.mp3"),
        "trim_sec": 1.35,
        "af_filter": "asetrate=44100*0.91,aresample=44100,highpass=f=180,lowpass=f=4800,afade=t=out:st=0.85:d=0.45,volume=0.82",
    },
    "sfx_highlighter_swipe.mp3": {
        "category": "editorial",
        "description": "Soft felt-pen marker swipe across newspaper headline",
        "keywords": ["강조", "핵심", "밑줄", "주목", "문구", "적시", "밝혀", "드러나", "highlight", "marker"],
        "commons_source": "File:Writing with feltpen.ogg",
        "trim_sec": 1.1,
        "af_filter": "highpass=f=240,lowpass=f=4500,afade=t=in:st=0:d=0.03,afade=t=out:st=0.70:d=0.38,volume=0.75",
    },
    "sfx_folder_open.mp3": {
        "category": "editorial",
        "description": "Case file folder opening on investigation desk",
        "keywords": ["사건 파일", "수사 기록", "내사", "보관", "미제", "봉인", "철", "folder", "case file"],
        "base_mix": ("sfx_paper_turn.mp3", "sfx_soft_impact.mp3"),
        "trim_sec": 1.15,
        "af_filter": "asetrate=44100*1.08,aresample=44100,lowpass=f=4200,afade=t=out:st=0.75:d=0.38,volume=0.78",
    },
    # Satellite, GIS Map & Trajectory Motion
    "sfx_radar_ping_sonar.mp3": {
        "category": "map_gis",
        "description": "Warm tactical radar / sonar location lock pulse",
        "keywords": ["위성", "좌표", "위치", "반경", "추적", "거점", "포착", "지점", "타깃", "radar", "satellite", "pin"],
        "commons_source": "File:Sonar pings.ogg",
        "trim_sec": 1.5,
        "af_filter": "lowpass=f=3400,afade=t=in:st=0:d=0.02,afade=t=out:st=0.95:d=0.50,volume=0.68",
    },
    "sfx_map_route_sweep.mp3": {
        "category": "map_gis",
        "description": "Smooth cartographic camera flight & route line sweep",
        "keywords": ["이동", "경로", "노선", "베이징", "쿤밍", "윈난", "전역", "투입", "파견", "지도", "route", "map", "flight"],
        "base_mix": ("sfx_soft_whoosh.mp3", "sfx_telemetry_tick.mp3"),
        "trim_sec": 1.5,
        "af_filter": "asetrate=44100*0.94,aresample=44100,lowpass=f=3600,afade=t=in:st=0:d=0.05,afade=t=out:st=1.0:d=0.45,volume=0.76",
    },
    "sfx_satellite_lock_beep.mp3": {
        "category": "map_gis",
        "description": "Subtle orbital telemetry lock chime for map pins",
        "keywords": ["관할", "구역", "거리", "야시", "나이트클럽", "술집", "현장", "지도", "zone", "district"],
        "base_mix": ("sfx_data_ping.mp3", "sfx_telemetry_tick.mp3"),
        "trim_sec": 1.1,
        "af_filter": "asetrate=44100*0.89,aresample=44100,lowpass=f=3200,afade=t=out:st=0.65:d=0.40,volume=0.70",
    },
    "sfx_telemetry_tick.mp3": {
        "category": "map_gis",
        "description": "Crisp forensic telemetry counter tick",
        "keywords": ["수치", "통계", "건수", "비율", "데이터", "카운트", "명단", "리스트", "count", "metric"],
    },
    # Forensics, Biometrics & Police Dispatch
    "sfx_camera_shutter.mp3": {
        "category": "forensic",
        "description": "Archival evidence camera shutter click",
        "keywords": ["사진", "현장", "목격", "촬영", "증거물", "초상", "얼굴", "신원", "photo", "evidence"],
    },
    "sfx_biometric_match_chime.mp3": {
        "category": "forensic",
        "description": "Biometric fingerprint / DNA database match confirmation",
        "keywords": ["지문", "대조", "생체", "일치", "신분", "위조", "리린", "리루이", "호적", "fingerprint", "biometric", "match"],
        "base_mix": ("sfx_data_ping.mp3", "sfx_typing_log.mp3"),
        "trim_sec": 1.35,
        "af_filter": "asetrate=44100*0.96,aresample=44100,lowpass=f=3800,afade=t=out:st=0.85:d=0.45,volume=0.76",
    },
    "sfx_document_scanner_hum.mp3": {
        "category": "forensic",
        "description": "Forensic optical document & microfilm scanner pass",
        "keywords": ["감식", "검증", "전산", "시스템", "조회", "데이터베이스", "스캔", "추적", "scan", "database"],
        "base_mix": ("sfx_typing_log.mp3", "sfx_soft_whoosh.mp3"),
        "trim_sec": 1.4,
        "af_filter": "asetrate=44100*0.86,aresample=44100,lowpass=f=3000,afade=t=out:st=0.9:d=0.45,volume=0.72",
    },
    "sfx_police_radio_chirp.mp3": {
        "category": "forensic",
        "description": "Subtle police dispatch / central taskforce comms tone",
        "keywords": ["공안", "경찰", "출동", "신고", "파출소", "독도조", "특수팀", "수사관", "체포조", "police", "dispatch", "taskforce"],
        "commons_source": "File:Strange police scanner tones.ogg",
        "trim_sec": 1.25,
        "af_filter": "highpass=f=300,lowpass=f=3200,afade=t=in:st=0:d=0.03,afade=t=out:st=0.80:d=0.40,volume=0.62",
    },
    "sfx_typing_log.mp3": {
        "category": "forensic",
        "description": "Mechanical investigation log typing",
        "keywords": ["작성", "보고서", "입력", "타자", "기록관", "록", "타이핑", "log", "report"],
    },
    "sfx_data_ping.mp3": {
        "category": "forensic",
        "description": "Clean analytical node connection ping",
        "keywords": ["연결", "고리", "네트워크", "관계도", "조직도", "커넥션", "배후", "보호막", "network", "node"],
    },
    # Narrative Pacing, Bribery, Chronology & Atmosphere
    "sfx_clock_tick_tense.mp3": {
        "category": "chronology",
        "description": "Measured analog clock ticking for timeline progression",
        "keywords": ["년", "월", "일", "시간", "흐르", "세월", "연도", "20년", "기간", "당시", "timeline", "year", "clock"],
        "commons_source": "File:Clock ticking.ogg",
        "trim_sec": 1.6,
        "af_filter": "lowpass=f=3600,afade=t=in:st=0:d=0.04,afade=t=out:st=1.05:d=0.50,volume=0.72",
    },
    "sfx_somber_chime.mp3": {
        "category": "emotional",
        "description": "Warm somber resonant chime for tragic / reflective beats",
        "keywords": ["피해자", "고문", "비극", "고통", "눈물", "소녀", "치아", "상처", "분노", "충격", "victim", "tragedy"],
    },
    "sfx_soft_whoosh.mp3": {
        "category": "transition",
        "description": "Gentle warm air whoosh for card entrance",
        "keywords": ["전환", "장면", "이어", "한편", "그리고", "transition"],
    },
    "sfx_transition_whoosh.mp3": {
        "category": "transition",
        "description": "Smooth editorial slide transition",
        "keywords": ["배경", "과정", "전말", "실체", "slide"],
    },
    "sfx_soft_impact.mp3": {
        "category": "emphasis",
        "description": "Warm cushioned low-end impact for key revelation",
        "keywords": ["반전", "실상", "진실", "충격적", "전대미문", "미스터리", "impact", "reveal"],
    },
    "sfx_chapter_hit.mp3": {
        "category": "emphasis",
        "description": "Deep documentary chapter transition hit",
        "keywords": ["장", "챕터", "시작", "서막", "결말", "chapter"],
    },
    "sfx_deep_impact.mp3": {
        "category": "emphasis",
        "description": "Deep cinematic sub-bass accent",
        "keywords": ["암흑", "권력", "제국", "붕괴", "몰락", "empire", "collapse"],
    },
}

CONTEXTUAL_BGM_CATALOG: dict[str, dict[str, Any]] = {
    "bgm_emerging_mysteries.mp3": {
        "mood": "mystery_hook",
        "description": "Suspenseful investigative opening & paradoxical mystery hook",
        "keywords": ["미스터리", "의문", "왜", "과연", "사형수", "부활", "시작"],
    },
    "bgm_gathering_darkness.mp3": {
        "mood": "dark_crime",
        "description": "Somber, tense undertone for brutal crimes, victims & fear",
        "keywords": ["폭행", "고문", "피해자", "범행", "공포", "야간", "나이트클럽", "만행"],
    },
    "bgm_investigative_bed.mp3": {
        "mood": "institutional_corruption",
        "description": "Measured journalistic investigation bed for bribery, paper trails & collusion",
        "keywords": ["부모", "권력", "뇌물", "감형", "특허", "가짜", "서류", "조작", "보호막"],
    },
    "bgm_forensic_pulse.mp3": {
        "mood": "forensic_pursuit",
        "description": "Focused analytical pulse for fingerprint match, central taskforce & arrest",
        "keywords": ["지문", "대조", "독도조", "베이징", "수사", "체포", "추적", "포위"],
    },
    "bgm_dark_ambient_drone.mp3": {
        "mood": "solemn_reckoning",
        "description": "Solemn atmospheric drone for supreme court retrial, execution & historical reflection",
        "keywords": ["재심", "사형 선고", "집행", "처형", "역사", "정의", "심판", "최후"],
    },
}


def _get_commons_download_urls(titles: list[str]) -> dict[str, str]:
    if not titles:
        return {}
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "query",
            "titles": "|".join(titles),
            "prop": "imageinfo",
            "iiprop": "url",
            "format": "json",
        }
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    out: dict[str, str] = {}
    for _, page in data.get("query", {}).get("pages", {}).items():
        title = page.get("title", "")
        ii = page.get("imageinfo", [{}])[0]
        if title and ii.get("url"):
            out[title] = ii["url"]
    return out


def ensure_audio_library_stocked() -> dict[str, Any]:
    """Ensure all 28 contextual Foley SFX and 5+ BGM tracks exist in both
    CofiDocumentary presets and CofiRemotion public/audio_library.
    """
    sfx_dir = PRESET_AUDIO_DIR / "sfx"
    bgm_dir = PRESET_AUDIO_DIR / "bgm"
    sfx_dir.mkdir(parents=True, exist_ok=True)
    bgm_dir.mkdir(parents=True, exist_ok=True)

    missing_commons: dict[str, str] = {}
    for fname, meta in CONTEXTUAL_SFX_CATALOG.items():
        target = sfx_dir / fname
        if not target.exists() and meta.get("commons_source"):
            missing_commons[fname] = meta["commons_source"]

    commons_urls: dict[str, str] = {}
    if missing_commons:
        try:
            commons_urls = _get_commons_download_urls(list(set(missing_commons.values())))
        except Exception as exc:
            print(f"[audio_library_manager] Warning fetching Commons URLs: {exc}")

    created: list[str] = []
    for fname, meta in CONTEXTUAL_SFX_CATALOG.items():
        target = sfx_dir / fname
        if target.exists() and target.stat().st_size > 1500:
            continue

        commons_title = meta.get("commons_source")
        af_filter = meta.get("af_filter", "afade=t=out:st=0.8:d=0.4,volume=0.8")
        trim_sec = float(meta.get("trim_sec", 1.35))

        if commons_title and commons_title in commons_urls:
            dl_url = commons_urls[commons_title]
            try:
                with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as tmp:
                    tmp_path = tmp.name
                req = urllib.request.Request(dl_url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=25) as r, open(tmp_path, "wb") as f:
                    f.write(r.read())
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    tmp_path,
                    "-t",
                    str(trim_sec),
                    "-af",
                    af_filter,
                    "-ar",
                    "44100",
                    "-ac",
                    "2",
                    "-b:a",
                    "192k",
                    str(target),
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                os.unlink(tmp_path)
                created.append(fname)
                time.sleep(0.35)
                continue
            except Exception as exc:
                print(f"[audio_library_manager] Commons download fallback for {fname}: {exc}")

        # Fallback or layered real Foley mix from existing library recordings
        base_mix = meta.get("base_mix")
        if base_mix:
            src_a = sfx_dir / base_mix[0]
            src_b = sfx_dir / base_mix[1]
            if src_a.exists() and src_b.exists():
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(src_a),
                    "-i",
                    str(src_b),
                    "-filter_complex",
                    f"[0:a][1:a]amix=inputs=2:duration=longest:dropout_transition=0.2,{af_filter}",
                    "-t",
                    str(trim_sec),
                    "-ar",
                    "44100",
                    "-ac",
                    "2",
                    "-b:a",
                    "192k",
                    str(target),
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                created.append(fname)

    # Sync all SFX and BGM to CofiRemotion/public/audio_library
    if REMOTION_AUDIO_DIR.parent.exists():
        rem_sfx = REMOTION_AUDIO_DIR / "sfx"
        rem_bgm = REMOTION_AUDIO_DIR / "bgm"
        rem_sfx.mkdir(parents=True, exist_ok=True)
        rem_bgm.mkdir(parents=True, exist_ok=True)
        for f in sfx_dir.glob("*.mp3"):
            shutil.copy2(f, rem_sfx / f.name)
        for f in bgm_dir.glob("*.mp3"):
            shutil.copy2(f, rem_bgm / f.name)

    # Update manifest.json
    manifest_path = PRESET_AUDIO_DIR / "manifest.json"
    manifest_data = {
        "version": "2.0-contextual-dynamic",
        "updated_at": "2026-10-25",
        "sfx": {
            k: {
                "path": f"audio_library/sfx/{k}",
                "category": v["category"],
                "description": v["description"],
                "keywords": v["keywords"],
            }
            for k, v in CONTEXTUAL_SFX_CATALOG.items()
            if (sfx_dir / k).exists()
        },
        "bgm": {
            k: {
                "path": f"audio_library/bgm/{k}",
                "mood": v["mood"],
                "description": v["description"],
                "keywords": v["keywords"],
            }
            for k, v in CONTEXTUAL_BGM_CATALOG.items()
            if (bgm_dir / k).exists()
        },
    }
    manifest_path.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")
    if REMOTION_AUDIO_DIR.exists():
        (REMOTION_AUDIO_DIR / "manifest.json").write_text(
            json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return {"created_sfx": created, "total_sfx": len(manifest_data["sfx"]), "total_bgm": len(manifest_data["bgm"])}


def fetch_missing_audio_asset(query: str, target_filename: str, category: str = "sfx") -> str | None:
    """Dynamically search Wikimedia Commons for a new CC0/open audio asset when
    a new documentary topic requires specialized sound effects or music.
    """
    sub = "bgm" if category == "bgm" else "sfx"
    out_dir = PRESET_AUDIO_DIR / sub
    out_dir.mkdir(parents=True, exist_ok=True)
    if not target_filename.endswith(".mp3"):
        target_filename += ".mp3"
    target_path = out_dir / target_filename
    if target_path.exists() and target_path.stat().st_size > 1500:
        return f"audio_library/{sub}/{target_filename}"

    search_url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "query",
            "list": "search",
            "srsearch": f"filetype:audio {query}",
            "srnamespace": 6,
            "srlimit": 6,
            "format": "json",
        }
    )
    try:
        req = urllib.request.Request(search_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        candidates = [
            x["title"]
            for x in data.get("query", {}).get("search", [])
            if not any(x["title"].startswith(prefix) for prefix in ("File:LL-", "File:En-", "File:De-", "File:Fr-"))
        ]
        if not candidates:
            return None
        urls = _get_commons_download_urls(candidates[:3])
        for title, dl_url in urls.items():
            with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as tmp:
                tmp_path = tmp.name
            req_dl = urllib.request.Request(dl_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req_dl, timeout=25) as r_dl, open(tmp_path, "wb") as f_out:
                f_out.write(r_dl.read())
            trim_d = "60.0" if sub == "bgm" else "1.8"
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    tmp_path,
                    "-t",
                    trim_d,
                    "-ar",
                    "44100",
                    "-ac",
                    "2",
                    "-b:a",
                    "192k",
                    str(target_path),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            os.unlink(tmp_path)
            if REMOTION_AUDIO_DIR.exists():
                rem_target = REMOTION_AUDIO_DIR / sub / target_filename
                rem_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target_path, rem_target)
            return f"audio_library/{sub}/{target_filename}"
    except Exception as exc:
        print(f"[audio_library_manager] Dynamic fetch failed for '{query}': {exc}")
    return None


def select_contextual_sfx_for_beat(
    narration_text: str,
    archetype: str,
    chapter_mood: str = "",
    prev_sfx: list[str] | None = None,
    beat_index: int = 1,
) -> list[dict[str, Any]]:
    """Select 2 distinct, context-matched Foley SFX for a single beat:
    1) Primary context/entrance SFX matched to the scene's narrative & visual archetype.
    2) Secondary mid-beat action SFX matched to the spoken reveal (marker swipe, radar ping,
       gavel strike, prison latch, biometric chime, dossier stamp, etc.) without repeating
       the previous beat's SFX.
    """
    prev_set = set(prev_sfx or [])
    text = (narration_text or "").lower()
    arch = (archetype or "").upper()

    # Score all catalog SFX against the spoken text
    scored: list[tuple[int, str]] = []
    for fname, meta in CONTEXTUAL_SFX_CATALOG.items():
        score = 0
        for kw in meta.get("keywords", []):
            if kw.lower() in text:
                score += 3
        if fname in prev_set:
            score -= 5
        scored.append((score, fname))
    scored.sort(key=lambda x: (-x[0], x[1]))

    # Archetype-guided primary + secondary defaults when text has multiple nuances
    if "FULLSCREEN_GIS" in arch or "FULLSCREEN_SATELLITE" in arch:
        primary_pool = ["sfx_map_route_sweep.mp3", "sfx_radar_ping_sonar.mp3", "sfx_satellite_lock_beep.mp3"]
        secondary_pool = ["sfx_radar_ping_sonar.mp3", "sfx_satellite_lock_beep.mp3", "sfx_telemetry_tick.mp3"]
    elif "SATELLITE" in arch or "MAP" in arch or "ROUTE" in arch:
        primary_pool = ["sfx_newspaper_unfold.mp3", "sfx_map_route_sweep.mp3", "sfx_paper_turn.mp3"]
        secondary_pool = ["sfx_radar_ping_sonar.mp3", "sfx_satellite_lock_beep.mp3", "sfx_highlighter_swipe.mp3"]
    elif "PRISON" in arch or "CUSTODY" in arch:
        primary_pool = ["sfx_cell_door.mp3", "sfx_iron_lock_latch.mp3", "sfx_footsteps_corridor.mp3"]
        secondary_pool = ["sfx_dossier_stamp.mp3", "sfx_clock_tick_tense.mp3", "sfx_iron_lock_latch.mp3"]
    elif "COURT" in arch or "SENTENCE" in arch or "VERDICT" in arch:
        primary_pool = ["sfx_gavel_hit.mp3", "sfx_official_seal_thud.mp3", "sfx_court_bell_toll.mp3"]
        secondary_pool = ["sfx_dossier_stamp.mp3", "sfx_highlighter_swipe.mp3", "sfx_gavel_hit.mp3"]
    elif "BIOMETRIC" in arch or "IDENTITY" in arch or "PATENT" in arch:
        primary_pool = ["sfx_document_scanner_hum.mp3", "sfx_folder_open.mp3", "sfx_paper_turn.mp3"]
        secondary_pool = ["sfx_biometric_match_chime.mp3", "sfx_dossier_stamp.mp3", "sfx_telemetry_tick.mp3"]
    elif "NETWORK" in arch or "HIERARCHY" in arch or "MATRIX" in arch:
        primary_pool = ["sfx_folder_open.mp3", "sfx_data_ping.mp3", "sfx_police_radio_chirp.mp3"]
        secondary_pool = ["sfx_telemetry_tick.mp3", "sfx_highlighter_swipe.mp3", "sfx_official_seal_thud.mp3"]
    elif "TIMELINE" in arch:
        primary_pool = ["sfx_clock_tick_tense.mp3", "sfx_newspaper_unfold.mp3", "sfx_paper_turn.mp3"]
        secondary_pool = ["sfx_highlighter_swipe.mp3", "sfx_dossier_stamp.mp3", "sfx_somber_chime.mp3"]
    else:
        primary_pool = ["sfx_newspaper_unfold.mp3", "sfx_paper_turn.mp3", "sfx_folder_open.mp3", "sfx_camera_shutter.mp3"]
        secondary_pool = ["sfx_highlighter_swipe.mp3", "sfx_dossier_stamp.mp3", "sfx_somber_chime.mp3", "sfx_clock_tick_tense.mp3"]

    # Override with highest keyword-matched SFX if strongly matched in spoken text
    best_kw_score, best_kw_sfx = scored[0]
    second_kw_score, second_kw_sfx = scored[1]

    primary_sfx = None
    if best_kw_score >= 3 and best_kw_sfx not in prev_set:
        primary_sfx = best_kw_sfx
    else:
        for cand in primary_pool:
            if cand not in prev_set:
                primary_sfx = cand
                break
        if not primary_sfx:
            primary_sfx = primary_pool[beat_index % len(primary_pool)]

    secondary_sfx = None
    if second_kw_score >= 3 and second_kw_sfx != primary_sfx and second_kw_sfx not in prev_set:
        secondary_sfx = second_kw_sfx
    else:
        for cand in secondary_pool:
            if cand != primary_sfx and cand not in prev_set:
                secondary_sfx = cand
                break
        if not secondary_sfx:
            secondary_sfx = "sfx_highlighter_swipe.mp3" if primary_sfx != "sfx_highlighter_swipe.mp3" else "sfx_paper_turn.mp3"

    return [
        {"file": f"audio_library/sfx/{primary_sfx}", "offset_ratio": 0.02, "volume": 0.14},
        {"file": f"audio_library/sfx/{secondary_sfx}", "offset_ratio": 0.34, "volume": 0.12},
    ]


def select_chapter_bgm_schedule(beats: list[dict[str, Any]], fps: int = 30) -> list[dict[str, Any]]:
    """Build a multi-chapter BGM schedule so background music shifts organically
    with the documentary's emotional acts instead of looping a single static track.
    """
    if not beats:
        return []
    total_beats = len(beats)
    # 5 narrative movements across the documentary
    movements = [
        (0.00, 0.16, "audio_library/bgm/bgm_emerging_mysteries.mp3", 0.065, "Act I: Paradoxical Hook & Early Impunity"),
        (0.16, 0.36, "audio_library/bgm/bgm_gathering_darkness.mp3", 0.060, "Act II: 1997 Nightclub Crimes & Death Sentence"),
        (0.36, 0.62, "audio_library/bgm/bgm_investigative_bed.mp3", 0.062, "Act III: Fake Patent, Prison Transfers & Nightlife Return"),
        (0.62, 0.84, "audio_library/bgm/bgm_forensic_pulse.mp3", 0.065, "Act IV: 2018 Clash, Fingerprint Match & Beijing Taskforce"),
        (0.84, 1.00, "audio_library/bgm/bgm_dark_ambient_drone.mp3", 0.060, "Act V: 2019 Retrial, Protective Umbrella Collapse & Execution"),
    ]
    schedule: list[dict[str, Any]] = []
    for r_start, r_end, bgm_path, vol, label in movements:
        idx_start = min(total_beats - 1, max(0, int(round(r_start * total_beats))))
        idx_end = min(total_beats - 1, max(idx_start, int(round(r_end * total_beats)) - 1))
        start_sec = float(beats[idx_start].get("start_sec", 0.0))
        end_sec = float(beats[idx_end].get("end_sec", start_sec + 10.0))
        schedule.append(
            {
                "src": bgm_path,
                "startFrame": int(round(start_sec * fps)),
                "endFrame": max(int(round(start_sec * fps)) + 30, int(round(end_sec * fps))),
                "volume": vol,
                "label": label,
            }
        )
    return schedule


if __name__ == "__main__":
    summary = ensure_audio_library_stocked()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
