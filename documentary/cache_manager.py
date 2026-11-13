from __future__ import annotations

import ctypes
import gc
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
from typing import Any

from .hot_reload import ensure_runtime_modules_synced

ensure_runtime_modules_synced(caller_module=__name__)


PROTECTED_JSON_AND_DOC_EXTS = {".json", ".md", ".srt", ".vtt", ".txt", ".ass"}
TEMP_BUNDLE_PREFIXES = (
    "remotion-webpack-bundle-",
    "remotion-rspack-bundle-",
    "cofi-standalone-pub-",
    "hf-render-",
    "hyperframes-extract-cache-",
    "puppeteer_dev_chrome_profile-",
    "react-motion-render",
    "playwright-",
    "_MEI",
)

# Ephemeral render/preview directories inside a workspace that are 100% safe to purge
# once the final MP4 is verified (Tier 1 & automatic post-job hygiene).
WORKSPACE_EPHEMERAL_REL_DIRS = (
    ".render_cache",
    ".render_segments",
    "universal_segments",
    "universal_sub_pngs",
    ".sacred_chapters",
    ".sacred_3d_pip",
    "_preview",
    "media/_preview",
    "scratch",
    "_scratch_inspect",
    "vox_verify_frames",
    "qa_frames",
    "cinema_text_renders",
    "cinema_text",
    "audio/beats_raw",
    "audio/beats_raw_fast",
    "audio/beats_backup_orig",
    "audio/segments",
    "media/edit_plates",
    "media/footage/probes",
    "media/edit_footage/probes",
    "media/storyboard_probes",
    "media/contact_sheets",
    "vox_renders",
    "shorts_9x16/remotion_bundle",
    "shorts_9x16/remotion_bundle_v2",
    "shorts_9x16/remotion_bundle_v3",
    "shorts_9x16/public_min",
    "shorts_9x16/subs_v2",
    "shorts_9x16/clips",
    "shorts_9x16/clips_v2",
    "shorts_9x16/clips_v3",
)

# Raw full-length download directories where unreferenced source videos accumulate.
# Files inside these folders that are NOT directly referenced by visual_manifest.json
# are safe to remove after the cut beat clips and final MP4 exist.
WORKSPACE_RAW_SOURCE_REL_DIRS = (
    "media/footage/sources",
    "media/raw_sources",
    "media/edit_footage/raw",
    "media/edit_footage/_cache",
    "media/raw_case_videos",
    "media/_raw_broll_cache",
    "media/case_sources",
    "media/clean_pool",
    "footage_raw",
    "footage/raw",
    "footage/sources",
    "footage/_cache",
    "footage_candidates",
    "raw_downloads",
)


def _dir_stats(path: Path, seen_inodes: set[int] | None = None) -> tuple[int, int]:
    """Return ``(total_bytes, file_count)`` for a directory or file without raising.
    Respects NTFS hardlinks when ``seen_inodes`` is passed or internally within the tree.
    """
    if not path.exists():
        return 0, 0
    seen = seen_inodes if seen_inodes is not None else set()
    try:
        if path.is_file():
            st = path.stat()
            if st.st_ino and st.st_nlink > 1:
                if st.st_ino in seen:
                    return 0, 0
                seen.add(st.st_ino)
            return st.st_size, 1
    except OSError:
        return 0, 0
    total_bytes = 0
    file_count = 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                st = (Path(root) / name).stat()
                if st.st_ino and st.st_nlink > 1:
                    if st.st_ino in seen:
                        continue
                    seen.add(st.st_ino)
                total_bytes += st.st_size
                file_count += 1
            except OSError:
                continue
    return total_bytes, file_count


def _safe_remove_path(path: Path) -> tuple[int, int, bool]:
    """Remove a file or directory and return ``(freed_bytes, removed_files, ok)``.
    If a file has ``st_nlink > 1`` (hardlinked elsewhere), unlinking it frees 0 physical bytes
    but still removes the directory entry cleanly.
    """
    if not path.exists():
        return 0, 0, True
    try:
        if path.is_file() or path.is_symlink():
            st = path.stat()
            freed = st.st_size if st.st_nlink <= 1 else 0
            path.unlink(missing_ok=True)
            return freed, 1, True
    except OSError:
        return 0, 0, False

    freed_bytes = 0
    removed_files = 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                st = (Path(root) / name).stat()
                if st.st_nlink <= 1:
                    freed_bytes += st.st_size
                removed_files += 1
            except OSError:
                continue
    try:
        shutil.rmtree(path, ignore_errors=False)
        return freed_bytes, removed_files, True
    except OSError:
        shutil.rmtree(path, ignore_errors=True)
        if not path.exists():
            return freed_bytes, removed_files, True
        return 0, 0, False


def _locate_canonical_final_mp4(workspace: Path, job: dict[str, Any] | None = None) -> Path | None:
    """Locate the primary verified final MP4 for a workspace across all known output locations."""
    candidates: list[Path] = []
    for manifest_name in ("final_manifest.json", "render_manifest.json"):
        mpath = workspace / manifest_name
        if mpath.is_file():
            try:
                data = json.loads(mpath.read_text(encoding="utf-8", errors="ignore"))
                if isinstance(data, dict):
                    vp = str(data.get("video_path") or data.get("output_path") or "").strip()
                    if vp:
                        p = Path(vp)
                        if not p.is_absolute():
                            p = workspace / p
                        candidates.append(p)
            except Exception:
                pass
    if isinstance(job, dict):
        out_vid = str(job.get("output_video") or "").strip()
        if out_vid:
            p = Path(out_vid)
            if not p.is_absolute():
                p = workspace / p
            candidates.append(p)

    candidates.extend([
        workspace / "release" / "video.mp4",
        workspace / "final.mp4",
        workspace / "output" / "final.mp4",
        workspace / "export" / "final_documentary.mp4",
        workspace / "final_documentary.mp4",
    ])
    release_dir = workspace / "release"
    if release_dir.is_dir():
        for mp4 in sorted(release_dir.glob("*.mp4"), key=lambda x: x.stat().st_mtime if x.exists() else 0, reverse=True):
            candidates.append(mp4)

    for c in candidates:
        try:
            if c.is_file() and c.stat().st_size >= 512 * 1024:
                return c
        except OSError:
            continue
    return None


def _job_has_verified_release_video(workspace: Path, job: dict[str, Any] | None = None) -> bool:
    """Return True when the workspace has a valid final MP4 (>= 512 KB)."""
    return _locate_canonical_final_mp4(workspace, job) is not None


def canonicalize_and_deduplicate_job_mp4s(
    workspace: Path,
    job: dict[str, Any] | None = None,
    *,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Ensure ``release/video.mp4`` and ``final.mp4`` are NTFS hardlinks to the single canonical
    final MP4, and purge duplicate/superseded full-length MP4 copies in ``output/``, ``export/``,
    ``media/video/``, ``release/``, or root. Returns ``(freed_bytes, removed_or_linked_files)``.
    """
    canonical = _locate_canonical_final_mp4(workspace, job)
    if canonical is None:
        return 0, 0

    try:
        canonical_stat = canonical.stat()
        canonical_size = canonical_stat.st_size
    except OSError:
        return 0, 0

    release_dir = workspace / "release"
    target_release_mp4 = release_dir / "video.mp4"
    freed_bytes = 0
    touched_files = 0

    # 1. Ensure release/video.mp4 exists and points to canonical
    if not dry_run:
        try:
            release_dir.mkdir(parents=True, exist_ok=True)
            if not target_release_mp4.exists():
                try:
                    os.link(canonical, target_release_mp4)
                except OSError:
                    shutil.copy2(canonical, target_release_mp4)
                canonical = target_release_mp4
                canonical_stat = canonical.stat()
            elif target_release_mp4.resolve() != canonical.resolve() and target_release_mp4.stat().st_ino != canonical_stat.st_ino:
                # If canonical is newer/referenced by final_manifest, link target_release_mp4 to canonical
                tmp_link = release_dir / "video.mp4.tmp_link"
                tmp_link.unlink(missing_ok=True)
                os.link(canonical, tmp_link)
                if target_release_mp4.stat().st_nlink <= 1:
                    freed_bytes += target_release_mp4.stat().st_size
                tmp_link.replace(target_release_mp4)
                touched_files += 1
                canonical = target_release_mp4
                canonical_stat = canonical.stat()
        except OSError:
            pass

    # 2. Ensure root final.mp4 is hardlinked (not a separate physical copy) if it exists
    root_final = workspace / "final.mp4"
    if root_final.exists():
        try:
            rf_stat = root_final.stat()
            if rf_stat.st_ino != canonical_stat.st_ino:
                if dry_run:
                    if rf_stat.st_nlink <= 1:
                        freed_bytes += rf_stat.st_size
                    touched_files += 1
                else:
                    tmp_link = workspace / "final.mp4.tmp_link"
                    tmp_link.unlink(missing_ok=True)
                    os.link(canonical, tmp_link)
                    if rf_stat.st_nlink <= 1:
                        freed_bytes += rf_stat.st_size
                    tmp_link.replace(root_final)
                    touched_files += 1
        except OSError:
            pass

    # 3. Clean duplicate/superseded large MP4 renders in output/, export/, render/, renders/, media/video/, root, and release/
    dup_candidates: list[Path] = []
    for sub in ("output", "export", "render", "renders", "media/video"):
        sdir = workspace / sub
        if sdir.is_dir():
            dup_candidates.extend(sdir.rglob("*.mp4"))
    for rmp4 in workspace.glob("*.mp4"):
        if rmp4.name.lower() != "final.mp4":
            dup_candidates.append(rmp4)
    if release_dir.is_dir():
        for rmp4 in release_dir.glob("*.mp4"):
            if rmp4.name.lower() != "video.mp4" and rmp4.resolve() != canonical.resolve():
                # Only remove superseded full-length renders (>= 200 MB) in release/
                try:
                    if rmp4.stat().st_size >= 200 * 1024 * 1024:
                        dup_candidates.append(rmp4)
                except OSError:
                    pass

    for cand in dup_candidates:
        try:
            if not cand.is_file():
                continue
            st = cand.stat()
            if st.st_ino == canonical_stat.st_ino:
                # Hardlinked alias in output/ or export/: remove redundant alias folder entry
                if not dry_run:
                    cand.unlink(missing_ok=True)
                touched_files += 1
            else:
                if dry_run:
                    if st.st_nlink <= 1:
                        freed_bytes += st.st_size
                    touched_files += 1
                else:
                    b, f, ok = _safe_remove_path(cand)
                    if ok:
                        freed_bytes += b
                        touched_files += f
        except OSError:
            continue

    # Also clean huge intermediate master wav mixes (>80MB) & .orig backup wavs if narration.wav + release/video.mp4 already exist
    for mix_name in ("audio/master_director_mix.wav", "audio/master_emotional_bgm_sfx.wav"):
        mix_path = workspace / mix_name
        if mix_path.is_file():
            try:
                st = mix_path.stat()
                if st.st_size >= 80 * 1024 * 1024:
                    if dry_run:
                        freed_bytes += st.st_size if st.st_nlink <= 1 else 0
                        touched_files += 1
                    else:
                        b, f, ok = _safe_remove_path(mix_path)
                        if ok:
                            freed_bytes += b
                            touched_files += f
            except OSError:
                pass

    audio_dir = workspace / "audio"
    if audio_dir.is_dir():
        for wav_orig in audio_dir.glob("*.orig*"):
            if wav_orig.is_file():
                try:
                    st = wav_orig.stat()
                    if dry_run:
                        freed_bytes += st.st_size if st.st_nlink <= 1 else 0
                        touched_files += 1
                    else:
                        b, f, ok = _safe_remove_path(wav_orig)
                        if ok:
                            freed_bytes += b
                            touched_files += f
                except OSError:
                    pass

    # 4. Deduplicate identical files (>= 64 KB) across root audio, footage/, media/footage/, media/edit_footage/, vox/, media/vox/, ai/, media/ai/, audio/ via NTFS hardlinks
    by_size: dict[int, list[tuple[Path, int]]] = {}
    for root_audio in ("narration.wav", "universal_master_audio.m4a"):
        rap = workspace / root_audio
        if rap.is_file():
            try:
                st = rap.stat()
                if st.st_size >= 65536:
                    by_size.setdefault(st.st_size, []).append((rap, st.st_ino))
            except OSError:
                pass
    for sub in ("footage", "media/footage", "media/edit_footage", "vox", "media/vox", "ai", "media/ai", "audio"):
        sdir = workspace / sub
        if not sdir.is_dir():
            continue
        for root, _, files in os.walk(sdir):
            for fname in files:
                fp = Path(root) / fname
                try:
                    st = fp.stat()
                except OSError:
                    continue
                if st.st_size >= 65536:
                    by_size.setdefault(st.st_size, []).append((fp, st.st_ino))

    for sz, items in by_size.items():
        if len(items) < 2:
            continue
        by_hash: dict[bytes, list[tuple[Path, int]]] = {}
        for fp, ino in items:
            try:
                with open(fp, "rb") as fh:
                    h = hashlib.sha256()
                    h.update(fh.read(65536))
                    if sz > 131072:
                        fh.seek(sz - 65536)
                        h.update(fh.read(65536))
                    digest = h.digest()
                by_hash.setdefault(digest, []).append((fp, ino))
            except OSError:
                continue
        for digest, group in by_hash.items():
            inodes = {ino for _, ino in group if ino != 0}
            if len(inodes) <= 1:
                continue
            master_fp, master_ino = group[0]
            for dup_fp, dup_ino in group[1:]:
                if dup_ino == master_ino:
                    continue
                if dry_run:
                    freed_bytes += sz
                    touched_files += 1
                else:
                    try:
                        tmp_link = dup_fp.with_name(dup_fp.name + ".tmp_hlink")
                        tmp_link.unlink(missing_ok=True)
                        os.link(master_fp, tmp_link)
                        st_dup = dup_fp.stat()
                        if st_dup.st_nlink <= 1:
                            freed_bytes += st_dup.st_size
                        tmp_link.replace(dup_fp)
                        touched_files += 1
                    except OSError:
                        pass

    return freed_bytes, touched_files


def _collect_referenced_workspace_files(workspace: Path) -> set[Path]:
    """Return resolved Paths of all media files actively referenced by manifests in ``workspace``."""
    referenced: set[Path] = set()
    for mname in (
        "visual_manifest.json",
        "remotion_media_manifest.json",
        "ai_visual_manifest.json",
        "voice_manifest.json",
        "footage_approved_live.json",
        "asset_registry.json",
    ):
        mpath = workspace / mname
        if not mpath.is_file():
            continue
        try:
            raw = mpath.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue

        def _walk(obj: Any) -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, str) and any(
                        ext in v.lower() for ext in (".mp4", ".mov", ".mkv", ".webm", ".jpg", ".png", ".webp", ".wav", ".mp3")
                    ):
                        p = Path(v)
                        if not p.is_absolute():
                            p = workspace / v
                        try:
                            referenced.add(p.resolve())
                        except OSError:
                            pass
                    else:
                        _walk(v)
            elif isinstance(obj, list):
                for item in obj:
                    _walk(item)

        _walk(data)
    return referenced


def _collect_unreferenced_raw_source_files(workspace: Path) -> list[Path]:
    """Return unreferenced raw full-length source files & incomplete downloads inside a completed workspace."""
    referenced = _collect_referenced_workspace_files(workspace)
    targets: list[Path] = []
    seen: set[Path] = set()

    for rel_dir in WORKSPACE_RAW_SOURCE_REL_DIRS:
        folder = workspace / rel_dir
        if not folder.is_dir():
            continue
        for root, _, files in os.walk(folder):
            for name in files:
                fpath = Path(root) / name
                try:
                    resolved = fpath.resolve()
                except OSError:
                    resolved = fpath
                if resolved in referenced or resolved in seen:
                    continue
                seen.add(resolved)
                targets.append(fpath)

    # Also catch incomplete yt-dlp / ffmpeg temp files anywhere in workspace
    for root, _, files in os.walk(workspace):
        for name in files:
            low = name.lower()
            if low.endswith((".part", ".ytdl", ".temp.mp4", ".tmp.mp4", ".bak.mp4", ".bak.wav")):
                fpath = Path(root) / name
                try:
                    resolved = fpath.resolve()
                except OSError:
                    resolved = fpath
                if resolved not in referenced and resolved not in seen:
                    seen.add(resolved)
                    targets.append(fpath)

    return targets


def _is_job_protected_active(job_id: str, job: dict[str, Any] | None, active_job_ids: set[str]) -> bool:
    if job_id in active_job_ids:
        return True
    if not isinstance(job, dict):
        return False
    status = str(job.get("status") or "").strip().lower()
    if status in {"running", "queued"}:
        return True
    phases = job.get("phases")
    if isinstance(phases, dict):
        for pstate in phases.values():
            if isinstance(pstate, dict) and str(pstate.get("status") or "").strip().lower() in {"running", "queued"}:
                return True
    return False


def get_system_memory_snapshot() -> dict[str, Any]:
    """Return current Windows/POSIX physical memory metrics in GB."""
    if os.name == "nt":
        try:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                total_gb = round(stat.ullTotalPhys / (1024**3), 2)
                avail_gb = round(stat.ullAvailPhys / (1024**3), 2)
                used_gb = round(max(0.0, total_gb - avail_gb), 2)
                return {
                    "total_ram_gb": total_gb,
                    "available_ram_gb": avail_gb,
                    "used_ram_gb": used_gb,
                    "memory_load_pct": int(stat.dwMemoryLoad),
                }
        except Exception:
            pass
    return {
        "total_ram_gb": 16.0,
        "available_ram_gb": 8.0,
        "used_ram_gb": 8.0,
        "memory_load_pct": 50,
    }


def trim_current_process_working_set() -> bool:
    """Run Python GC and ask Windows to trim unused pages from the current process working set."""
    gc.collect()
    if os.name != "nt":
        return True
    try:
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        ctypes.windll.kernel32.SetProcessWorkingSetSize(
            ctypes.c_void_p(handle),
            ctypes.c_size_t(-1),
            ctypes.c_size_t(-1),
        )
        return True
    except Exception:
        return False


def stop_port_listener_process(port: int) -> bool:
    """Terminate the local TCP listener process on ``port`` (e.g. Remotion Studio on 8890)."""
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=0.25):
            pass
    except OSError:
        return False

    if os.name != "nt":
        return False

    try:
        res = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        pids: set[int] = set()
        target_suffix = f":{int(port)}"
        for line in (res.stdout or "").splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[0].upper() == "TCP" and parts[3].upper() == "LISTENING":
                if parts[1].endswith(target_suffix):
                    try:
                        pid = int(parts[4])
                        if pid > 4 and pid != os.getpid():
                            pids.add(pid)
                    except ValueError:
                        continue
        for pid in pids:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                timeout=5,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        return bool(pids)
    except Exception:
        return False


def reap_orphan_and_idle_processes(
    *,
    has_active_jobs: bool = False,
    voice_engine: Any = None,
    studio_embed_manager: Any = None,
    remotion_studio_port: int = 8890,
    stop_remotion_studio: bool = True,
    kill_orphan_headless_chrome: bool = True,
) -> dict[str, Any]:
    """Reclaim RAM/VRAM from idle sub-servers and orphaned headless browsers."""
    before_mem = get_system_memory_snapshot()
    actions: list[str] = []

    if voice_engine is not None:
        release_vram = getattr(voice_engine, "release_idle_vram", None)
        if callable(release_vram):
            try:
                release_vram("smart_cache_reclaim")
                actions.append("voice_vram_released")
            except Exception:
                pass

    if not has_active_jobs and studio_embed_manager is not None:
        try:
            if getattr(studio_embed_manager, "_process", None) is not None:
                studio_embed_manager.stop(timeout_seconds=3.0)
                actions.append("media_factory_stopped")
        except Exception:
            pass

    if stop_remotion_studio:
        if stop_port_listener_process(remotion_studio_port):
            actions.append(f"remotion_studio_{remotion_studio_port}_stopped")

    if kill_orphan_headless_chrome and not has_active_jobs and os.name == "nt":
        try:
            res = subprocess.run(
                ["taskkill", "/F", "/IM", "chrome-headless-shell.exe", "/T"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if res.returncode == 0:
                actions.append("orphan_chrome_headless_killed")
        except Exception:
            pass

    trim_current_process_working_set()
    after_mem = get_system_memory_snapshot()
    freed_ram_gb = round(max(0.0, after_mem["available_ram_gb"] - before_mem["available_ram_gb"]), 2)
    return {
        "ok": True,
        "actions": actions,
        "before_memory": before_mem,
        "after_memory": after_mem,
        "freed_ram_gb": freed_ram_gb,
    }


def _collect_job_slim_targets(workspace: Path, *, is_selected: bool = False) -> list[tuple[str, Path]]:
    """Return Tier 2 intermediate paths inside a completed job workspace."""
    targets: list[tuple[str, Path]] = []
    rel_dirs = [
        "audio/beats",
        "vox_plates",
        "media/vox_plates",
        "media/ai_Selects",
    ]
    for rel_dir in rel_dirs:
        candidate = workspace / rel_dir
        if candidate.exists():
            targets.append((rel_dir, candidate))
    return targets


def _collect_temp_bundle_dirs(min_age_seconds: float = 300.0) -> list[Path]:
    """Return stale Remotion/Hyperframes/Puppeteer temp directories in LOCALAPPDATA\\Temp."""
    results: list[Path] = []
    temp_root = Path(os.environ.get("LOCALAPPDATA", "")) / "Temp"
    if not temp_root.is_dir():
        temp_root = Path(os.environ.get("TEMP", ""))
    if not temp_root.is_dir():
        return results

    now = time.time()
    try:
        for entry in temp_root.iterdir():
            name = entry.name
            is_match = any(name.startswith(prefix) for prefix in TEMP_BUNDLE_PREFIXES)
            if not is_match and name.startswith("tmp") and len(name) in (10, 11):
                is_match = True
            if not is_match:
                continue
            try:
                age = max(0.0, now - entry.stat().st_mtime)
                if age >= min_age_seconds:
                    results.append(entry)
            except OSError:
                continue
    except OSError:
        pass
    return results


def _collect_app_internal_cache_paths(app_root: Path) -> list[Path]:
    """Return app-level archive logs & legacy render caches inside CofiDocumentary."""
    results: list[Path] = []
    producer_dir = app_root / ".producer"
    if producer_dir.is_dir():
        for sub in ("chat_runs_archive", "chat_runs"):
            p = producer_dir / sub
            if p.exists():
                results.append(p)
        for item in producer_dir.glob("producer_chat_*"):
            results.append(item)

    mf_logs = app_root / "data" / "media_factory" / "logs"
    if mf_logs.is_dir():
        for log_file in mf_logs.rglob("*"):
            if log_file.is_file():
                results.append(log_file)

    legacy_jobs_dir = app_root / "jobs"
    if legacy_jobs_dir.is_dir():
        for rc in legacy_jobs_dir.rglob(".render_cache"):
            if rc.is_dir():
                results.append(rc)
    return results


def scan_cache_report(
    *,
    workspaces_dir: Path,
    remotion_dir: Path | None,
    jobs: list[dict[str, Any]],
    active_job_ids: set[str] | None = None,
    selected_job_id: str | None = None,
    temp_min_age_seconds: float = 300.0,
) -> dict[str, Any]:
    """Scan and categorize reclaimable disk cache & intermediate files without deleting anything."""
    active_ids = set(active_job_ids or set())
    selected_id = str(selected_job_id or "").strip()
    keep_in_remotion_public = set(active_ids)

    job_map: dict[str, dict[str, Any]] = {}
    for job in jobs:
        jid = str(job.get("id") or "").strip()
        if jid:
            job_map[jid] = job
            if _is_job_protected_active(jid, job, active_ids):
                active_ids.add(jid)
                keep_in_remotion_public.add(jid)

    # Tier 1A: Remotion public/jobs/<completed_job> mirrors & public_* temp mirrors
    remotion_mirror_bytes = 0
    remotion_mirror_files = 0
    remotion_mirror_jobs: list[dict[str, Any]] = []
    if remotion_dir:
        pub_jobs_root = remotion_dir / "public" / "jobs"
        if pub_jobs_root.is_dir():
            for entry in sorted(pub_jobs_root.iterdir()):
                if not entry.is_dir():
                    continue
                if entry.name in keep_in_remotion_public:
                    continue
                b, f = _dir_stats(entry)
                if b > 0 or f > 0:
                    remotion_mirror_bytes += b
                    remotion_mirror_files += f
                    remotion_mirror_jobs.append({"job_id": entry.name, "bytes": b, "files": f})
        for extra_pub in sorted(remotion_dir.glob("public_*")):
            if extra_pub.is_dir():
                b, f = _dir_stats(extra_pub)
                if b > 0 or f > 0:
                    remotion_mirror_bytes += b
                    remotion_mirror_files += f
                    remotion_mirror_jobs.append({"job_id": extra_pub.name, "bytes": b, "files": f})

    # Tier 1B: Ephemeral render segments, preview frames, unreferenced raw downloads & duplicate MP4s
    render_cache_bytes = 0
    render_cache_files = 0
    render_cache_jobs: list[dict[str, Any]] = []

    # Tier 2: Intermediate files inside completed jobs (audio/beats, vox_plates)
    slim_bytes = 0
    slim_files = 0
    slim_jobs: list[dict[str, Any]] = []

    # Tier 3: Deep archive (media/ clips on completed jobs with verified release/*.mp4)
    archive_bytes = 0
    archive_files = 0
    archive_jobs: list[dict[str, Any]] = []

    all_workspace_dirs: dict[str, Path] = {}
    if workspaces_dir.is_dir():
        for entry in sorted(workspaces_dir.iterdir()):
            if entry.is_dir():
                all_workspace_dirs[entry.name] = entry
    for jid, job in job_map.items():
        ws_str = str(job.get("workspace") or "").strip()
        if ws_str:
            ws_path = Path(ws_str)
            if ws_path.is_dir():
                all_workspace_dirs[jid] = ws_path

    for jid, ws in all_workspace_dirs.items():
        job = job_map.get(jid)
        if _is_job_protected_active(jid, job, active_ids):
            continue
        has_release = _job_has_verified_release_video(ws, job)
        status = str((job or {}).get("status") or "").strip().lower()

        job_rc_bytes = 0
        job_rc_files = 0
        if has_release or status in {"completed", "failed", "cancelled"}:
            seen_rc_inodes: set[int] = set()
            for rc_name in WORKSPACE_EPHEMERAL_REL_DIRS:
                rc_path = ws / rc_name
                if rc_path.exists():
                    b, f = _dir_stats(rc_path, seen_rc_inodes)
                    job_rc_bytes += b
                    job_rc_files += f
            if has_release:
                for raw_file in _collect_unreferenced_raw_source_files(ws):
                    b, f = _dir_stats(raw_file, seen_rc_inodes)
                    job_rc_bytes += b
                    job_rc_files += f
                dup_b, dup_f = canonicalize_and_deduplicate_job_mp4s(ws, job, dry_run=True)
                job_rc_bytes += dup_b
                job_rc_files += dup_f

        if job_rc_bytes > 0:
            render_cache_bytes += job_rc_bytes
            render_cache_files += job_rc_files
            render_cache_jobs.append({"job_id": jid, "bytes": job_rc_bytes, "files": job_rc_files})

        if has_release and (status == "completed" or job is None or status not in {"running", "queued"}):
            job_slim_bytes = 0
            job_slim_files = 0
            seen_slim_inodes: set[int] = set()
            for _, target_path in _collect_job_slim_targets(ws, is_selected=(jid == selected_id)):
                b, f = _dir_stats(target_path, seen_slim_inodes)
                job_slim_bytes += b
                job_slim_files += f
            if job_slim_bytes > 0:
                slim_bytes += job_slim_bytes
                slim_files += job_slim_files
                slim_jobs.append({
                    "job_id": jid,
                    "title": str((job or {}).get("title") or jid),
                    "bytes": job_slim_bytes,
                    "files": job_slim_files,
                })

            archive_rel_dirs = (
                "media/footage",
                "media/edit_footage",
                "media/vox",
                "media/ai",
                "media/audio",
                "media/archival",
                "footage",
                "vox",
                "ai",
                "assets",
            )
            job_arch_bytes = 0
            job_arch_files = 0
            seen_arch_inodes: set[int] = set()
            for arch_rel in archive_rel_dirs:
                arch_dir = ws / arch_rel
                if arch_dir.is_dir():
                    b, f = _dir_stats(arch_dir, seen_arch_inodes)
                    job_arch_bytes += b
                    job_arch_files += f
            if job_arch_bytes > 0:
                archive_bytes += job_arch_bytes
                archive_files += job_arch_files
                archive_jobs.append({
                    "job_id": jid,
                    "title": str((job or {}).get("title") or jid),
                    "bytes": job_arch_bytes,
                    "files": job_arch_files,
                })

    # Tier 1C: CofiRemotion/out, renders, scratch + App internal archive logs
    remotion_out_bytes = 0
    remotion_out_files = 0
    if remotion_dir and not active_ids:
        for sub in ("out", "renders", "scratch"):
            b, f = _dir_stats(remotion_dir / sub)
            remotion_out_bytes += b
            remotion_out_files += f

    app_root = workspaces_dir.parent
    for internal_path in _collect_app_internal_cache_paths(app_root):
        b, f = _dir_stats(internal_path)
        remotion_out_bytes += b
        remotion_out_files += f

    # Tier 1D: System Temp bundles
    temp_bytes = 0
    temp_files = 0
    temp_dirs = _collect_temp_bundle_dirs(min_age_seconds=temp_min_age_seconds if active_ids else 60.0)
    for tdir in temp_dirs:
        b, f = _dir_stats(tdir)
        temp_bytes += b
        temp_files += f

    tier1_total_bytes = remotion_mirror_bytes + render_cache_bytes + remotion_out_bytes + temp_bytes
    tier1_total_files = remotion_mirror_files + render_cache_files + remotion_out_files + temp_files

    return {
        "ok": True,
        "active_job_ids": sorted(active_ids),
        "selected_job_id": selected_id or None,
        "memory": get_system_memory_snapshot(),
        "tiers": {
            "safe_ephemeral": {
                "mode": "safe_ephemeral",
                "label": "Tầng 1 · Cache Rác, Phân Đoạn Render, Video Nguồn Thô & Bản Sao Remotion (An toàn 100%)",
                "total_bytes": tier1_total_bytes,
                "total_gb": round(tier1_total_bytes / (1024**3), 2),
                "total_files": tier1_total_files,
                "breakdown": {
                    "remotion_public_mirror": {
                        "bytes": remotion_mirror_bytes,
                        "gb": round(remotion_mirror_bytes / (1024**3), 2),
                        "files": remotion_mirror_files,
                        "jobs_count": len(remotion_mirror_jobs),
                    },
                    "render_cache": {
                        "bytes": render_cache_bytes,
                        "gb": round(render_cache_bytes / (1024**3), 2),
                        "files": render_cache_files,
                        "jobs_count": len(render_cache_jobs),
                    },
                    "remotion_scratch_outputs": {
                        "bytes": remotion_out_bytes,
                        "gb": round(remotion_out_bytes / (1024**3), 2),
                        "files": remotion_out_files,
                    },
                    "system_temp_bundles": {
                        "bytes": temp_bytes,
                        "gb": round(temp_bytes / (1024**3), 2),
                        "files": temp_files,
                        "dirs_count": len(temp_dirs),
                    },
                },
            },
            "slim_completed": {
                "mode": "slim_completed",
                "label": "Tầng 2 · Thu Gọn Dự Án Đã Hoàn Thành (Giữ 100% Video MP4 cuối, Clip đã cắt, Voice tổng & Kịch bản)",
                "total_bytes": slim_bytes,
                "total_gb": round(slim_bytes / (1024**3), 2),
                "total_files": slim_files,
                "jobs_count": len(slim_jobs),
                "jobs": slim_jobs,
            },
            "archive_completed": {
                "mode": "archive_completed",
                "label": "Tầng 3 · Lưu Trữ Lạnh (Xóa thêm clip nguyên liệu lẻ sau khi đã có MP4 cuối)",
                "total_bytes": archive_bytes,
                "total_gb": round(archive_bytes / (1024**3), 2),
                "total_files": archive_files,
                "jobs_count": len(archive_jobs),
                "jobs": archive_jobs,
            },
        },
        "total_reclaimable_bytes": tier1_total_bytes + slim_bytes,
        "total_reclaimable_gb": round((tier1_total_bytes + slim_bytes) / (1024**3), 2),
    }


def clean_smart_cache(
    *,
    mode: str = "safe_ephemeral",
    workspaces_dir: Path,
    remotion_dir: Path | None,
    jobs: list[dict[str, Any]],
    active_job_ids: set[str] | None = None,
    selected_job_id: str | None = None,
    target_job_ids: list[str] | None = None,
    include_tier1: bool = True,
    reclaim_ram: bool = True,
    voice_engine: Any = None,
    studio_embed_manager: Any = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute smart cache cleaning while strictly protecting running jobs and final deliverables."""
    normalized_mode = str(mode or "safe_ephemeral").strip().lower()
    if normalized_mode not in {"safe_ephemeral", "slim_completed", "archive_completed"}:
        raise ValueError(f"Chế độ dọn cache không hợp lệ: {mode}")

    active_ids = set(active_job_ids or set())
    selected_id = str(selected_job_id or "").strip()
    keep_in_remotion_public = set(active_ids)

    job_map: dict[str, dict[str, Any]] = {}
    for job in jobs:
        jid = str(job.get("id") or "").strip()
        if jid:
            job_map[jid] = job
            if _is_job_protected_active(jid, job, active_ids):
                active_ids.add(jid)
                keep_in_remotion_public.add(jid)

    target_filter = {str(x).strip() for x in (target_job_ids or []) if str(x).strip()}
    freed_bytes = 0
    removed_files = 0
    cleaned_items: list[dict[str, Any]] = []
    skipped_active: list[str] = []

    all_workspace_dirs: dict[str, Path] = {}
    if workspaces_dir.is_dir():
        for entry in sorted(workspaces_dir.iterdir()):
            if entry.is_dir():
                all_workspace_dirs[entry.name] = entry
    for jid, job in job_map.items():
        ws_str = str(job.get("workspace") or "").strip()
        if ws_str:
            ws_path = Path(ws_str)
            if ws_path.is_dir():
                all_workspace_dirs[jid] = ws_path

    # 1. Tier 1 cleaning (safe_ephemeral)
    if normalized_mode == "safe_ephemeral" or include_tier1:
        if remotion_dir:
            pub_jobs_root = remotion_dir / "public" / "jobs"
            if pub_jobs_root.is_dir():
                for entry in sorted(pub_jobs_root.iterdir()):
                    if not entry.is_dir():
                        continue
                    if entry.name in keep_in_remotion_public:
                        continue
                    if target_filter and entry.name not in target_filter:
                        continue
                    if dry_run:
                        b, f = _dir_stats(entry)
                        ok = True
                    else:
                        b, f, ok = _safe_remove_path(entry)
                    if ok and (b > 0 or f > 0):
                        freed_bytes += b
                        removed_files += f
                        cleaned_items.append({"category": "remotion_public_mirror", "job_id": entry.name, "bytes": b, "files": f})
            if not target_filter:
                for extra_pub in sorted(remotion_dir.glob("public_*")):
                    if extra_pub.is_dir():
                        if dry_run:
                            b, f = _dir_stats(extra_pub)
                            ok = True
                        else:
                            b, f, ok = _safe_remove_path(extra_pub)
                        if ok and (b > 0 or f > 0):
                            freed_bytes += b
                            removed_files += f
                            cleaned_items.append({"category": "remotion_public_mirror", "job_id": extra_pub.name, "bytes": b, "files": f})

        for jid, ws in all_workspace_dirs.items():
            if target_filter and jid not in target_filter:
                continue
            job = job_map.get(jid)
            if _is_job_protected_active(jid, job, active_ids):
                skipped_active.append(jid)
                continue
            has_release = _job_has_verified_release_video(ws, job)
            status = str((job or {}).get("status") or "").strip().lower()
            if not (has_release or status in {"completed", "failed", "cancelled"}):
                continue

            # 1B-1: Ephemeral render segments & preview directories
            for rc_name in WORKSPACE_EPHEMERAL_REL_DIRS:
                rc_path = ws / rc_name
                if not rc_path.exists():
                    continue
                if dry_run:
                    b, f = _dir_stats(rc_path)
                    ok = True
                else:
                    b, f, ok = _safe_remove_path(rc_path)
                if ok and (b > 0 or f > 0):
                    freed_bytes += b
                    removed_files += f
                    cleaned_items.append({"category": "render_cache", "job_id": jid, "path": rc_name, "bytes": b, "files": f})

            # 1B-2: Unreferenced raw full-length source videos & duplicate MP4s (only when final MP4 is verified)
            if has_release:
                raw_freed = 0
                raw_count = 0
                for raw_file in _collect_unreferenced_raw_source_files(ws):
                    if dry_run:
                        b, f = _dir_stats(raw_file)
                        ok = True
                    else:
                        b, f, ok = _safe_remove_path(raw_file)
                    if ok:
                        raw_freed += b
                        raw_count += f
                if raw_freed > 0 or raw_count > 0:
                    freed_bytes += raw_freed
                    removed_files += raw_count
                    cleaned_items.append({"category": "unreferenced_raw_sources", "job_id": jid, "bytes": raw_freed, "files": raw_count})

                dup_b, dup_f = canonicalize_and_deduplicate_job_mp4s(ws, job, dry_run=dry_run)
                if dup_b > 0 or dup_f > 0:
                    freed_bytes += dup_b
                    removed_files += dup_f
                    cleaned_items.append({"category": "deduplicate_final_mp4", "job_id": jid, "bytes": dup_b, "files": dup_f})

        if remotion_dir and not active_ids and not target_filter:
            for sub in ("out", "renders", "scratch"):
                sub_path = remotion_dir / sub
                if not sub_path.exists():
                    continue
                if dry_run:
                    b, f = _dir_stats(sub_path)
                    ok = True
                else:
                    b, f, ok = _safe_remove_path(sub_path)
                if ok and (b > 0 or f > 0):
                    freed_bytes += b
                    removed_files += f
                    cleaned_items.append({"category": "remotion_scratch_outputs", "path": sub, "bytes": b, "files": f})

        if not target_filter:
            app_root = workspaces_dir.parent
            for internal_path in _collect_app_internal_cache_paths(app_root):
                if dry_run:
                    b, f = _dir_stats(internal_path)
                    ok = True
                else:
                    b, f, ok = _safe_remove_path(internal_path)
                if ok and (b > 0 or f > 0):
                    freed_bytes += b
                    removed_files += f
                    cleaned_items.append({"category": "app_internal_cache", "path": str(internal_path.relative_to(app_root)), "bytes": b, "files": f})

            temp_dirs = _collect_temp_bundle_dirs(min_age_seconds=1800.0 if active_ids else 60.0)
            for tdir in temp_dirs:
                if dry_run:
                    b, f = _dir_stats(tdir)
                    ok = True
                else:
                    b, f, ok = _safe_remove_path(tdir)
                if ok and (b > 0 or f > 0):
                    freed_bytes += b
                    removed_files += f
                    cleaned_items.append({"category": "system_temp_bundles", "path": tdir.name, "bytes": b, "files": f})

    # 2. Tier 2 (slim_completed) & Tier 3 (archive_completed)
    if normalized_mode in {"slim_completed", "archive_completed"}:
        for jid, ws in all_workspace_dirs.items():
            if target_filter and jid not in target_filter:
                continue
            job = job_map.get(jid)
            if _is_job_protected_active(jid, job, active_ids):
                if jid not in skipped_active:
                    skipped_active.append(jid)
                continue
            status = str((job or {}).get("status") or "").strip().lower()
            if not _job_has_verified_release_video(ws, job) or status in {"running", "queued"}:
                continue

            for rel_label, target_path in _collect_job_slim_targets(ws, is_selected=(jid == selected_id)):
                if not target_path.exists():
                    continue
                if dry_run:
                    b, f = _dir_stats(target_path)
                    ok = True
                else:
                    b, f, ok = _safe_remove_path(target_path)
                if ok and (b > 0 or f > 0):
                    freed_bytes += b
                    removed_files += f
                    cleaned_items.append({
                        "category": "slim_completed",
                        "job_id": jid,
                        "path": rel_label,
                        "bytes": b,
                        "files": f,
                    })

            if normalized_mode == "archive_completed":
                archive_rel_dirs = (
                    "media/footage",
                    "media/edit_footage",
                    "media/vox",
                    "media/ai",
                    "media/audio",
                    "media/archival",
                    "footage",
                    "vox",
                    "ai",
                    "assets",
                )
                for arch_rel in archive_rel_dirs:
                    arch_dir = ws / arch_rel
                    if arch_dir.is_dir():
                        if dry_run:
                            b, f = _dir_stats(arch_dir)
                            ok = True
                        else:
                            b, f, ok = _safe_remove_path(arch_dir)
                        if ok and (b > 0 or f > 0):
                            freed_bytes += b
                            removed_files += f
                            cleaned_items.append({
                                "category": "archive_completed",
                                "job_id": jid,
                                "path": arch_rel,
                                "bytes": b,
                                "files": f,
                            })

    ram_result: dict[str, Any] = {}
    if reclaim_ram and not dry_run:
        ram_result = reap_orphan_and_idle_processes(
            has_active_jobs=bool(active_ids),
            voice_engine=voice_engine,
            studio_embed_manager=studio_embed_manager,
            stop_remotion_studio=not bool(active_ids),
            kill_orphan_headless_chrome=not bool(active_ids),
        )

    return {
        "ok": True,
        "mode": normalized_mode,
        "dry_run": dry_run,
        "freed_bytes": freed_bytes,
        "freed_gb": round(freed_bytes / (1024**3), 2),
        "removed_files": removed_files,
        "cleaned_count": len(cleaned_items),
        "cleaned_items": cleaned_items[:100],
        "skipped_active_jobs": skipped_active,
        "ram_reclaim": ram_result,
        "memory": get_system_memory_snapshot(),
    }


def auto_hygiene_after_job_export(
    *,
    workspace: Path,
    job_id: str,
    remotion_dir: Path | None,
    active_job_ids: set[str] | None = None,
    job: dict[str, Any] | None = None,
    voice_engine: Any = None,
    studio_embed_manager: Any = None,
) -> dict[str, Any]:
    """Smart Post-Job Memory & Storage Manager:
    Automatically runs after a job finishes export / QC to:
    1. Canonicalize & NTFS-hardlink ``release/video.mp4`` <-> ``final.mp4`` and purge duplicate MP4 renders.
    2. Purge ephemeral render segments (``universal_segments``, ``_preview``, ``scratch``, ``.render_cache``, etc.).
    3. Purge unreferenced full-length raw source downloads (preserving 100% of cut beat clips, AI frames, Vox & WAVs).
    4. Purge ``CofiRemotion/public/jobs/<job_id>`` mirrors, ``CofiRemotion/out`` bundles, and ``%TEMP%`` bundles.
    5. Reclaim idle RAM/VRAM from background servers & headless Chrome.
    """
    if not _job_has_verified_release_video(workspace, job):
        return {"ok": False, "reason": "release_video_not_verified"}

    freed_bytes = 0
    removed_files = 0
    breakdown: dict[str, int] = {
        "deduplicated_mp4_bytes": 0,
        "ephemeral_segments_bytes": 0,
        "unreferenced_raw_sources_bytes": 0,
        "remotion_mirror_and_out_bytes": 0,
        "system_temp_bytes": 0,
    }

    # 1. Canonicalize & hardlink final MP4s
    dup_b, dup_f = canonicalize_and_deduplicate_job_mp4s(workspace, job, dry_run=False)
    freed_bytes += dup_b
    removed_files += dup_f
    breakdown["deduplicated_mp4_bytes"] = dup_b

    # 2. Purge ephemeral render segments & preview frames inside workspace
    for rc_name in WORKSPACE_EPHEMERAL_REL_DIRS:
        rc_path = workspace / rc_name
        if rc_path.exists():
            b, f, _ = _safe_remove_path(rc_path)
            freed_bytes += b
            removed_files += f
            breakdown["ephemeral_segments_bytes"] += b

    # 3. Purge unreferenced full-length raw source downloads inside workspace
    for raw_file in _collect_unreferenced_raw_source_files(workspace):
        b, f, _ = _safe_remove_path(raw_file)
        freed_bytes += b
        removed_files += f
        breakdown["unreferenced_raw_sources_bytes"] += b

    # 4. Purge Remotion public/jobs mirrors & out bundles (except any other currently running job)
    other_active_ids = {x for x in (active_job_ids or set()) if x and x != job_id}
    if remotion_dir:
        pub_jobs_root = remotion_dir / "public" / "jobs"
        if pub_jobs_root.is_dir():
            for entry in sorted(pub_jobs_root.iterdir()):
                if entry.is_dir() and entry.name not in other_active_ids:
                    b, f, _ = _safe_remove_path(entry)
                    freed_bytes += b
                    removed_files += f
                    breakdown["remotion_mirror_and_out_bytes"] += b
        if not other_active_ids:
            for sub in ("out", "renders", "scratch"):
                sub_path = remotion_dir / sub
                if sub_path.exists():
                    b, f, _ = _safe_remove_path(sub_path)
                    freed_bytes += b
                    removed_files += f
                    breakdown["remotion_mirror_and_out_bytes"] += b

    # 5. Purge stale %TEMP% bundles
    for tdir in _collect_temp_bundle_dirs(min_age_seconds=600.0 if other_active_ids else 30.0):
        b, f, _ = _safe_remove_path(tdir)
        freed_bytes += b
        removed_files += f
        breakdown["system_temp_bytes"] += b

    # 6. Reclaim RAM/VRAM
    ram_result = reap_orphan_and_idle_processes(
        has_active_jobs=bool(other_active_ids),
        voice_engine=voice_engine,
        studio_embed_manager=studio_embed_manager,
        stop_remotion_studio=not bool(other_active_ids),
        kill_orphan_headless_chrome=not bool(other_active_ids),
    )

    report = {
        "ok": True,
        "job_id": job_id,
        "freed_bytes": freed_bytes,
        "freed_gb": round(freed_bytes / (1024**3), 2),
        "removed_files": removed_files,
        "breakdown": breakdown,
        "ram_reclaim": ram_result,
        "cleaned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        (workspace / ".smart_hygiene_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass
    return report
