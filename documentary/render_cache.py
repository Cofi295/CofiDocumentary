from __future__ import annotations

import ctypes
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
from typing import Any, Callable


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    temporary = path.with_suffix(f"{path.suffix}.{os.getpid()}.{threading.get_ident()}.tmp")
    temporary.write_text(text, encoding="utf-8")
    for attempt in range(8):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 7:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
                try:
                    path.write_text(text, encoding="utf-8")
                except OSError:
                    pass
                return
            time.sleep(0.03 * (attempt + 1))


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


def _detect_system_memory_gb() -> tuple[float, float]:
    """Return (total_ram_gb, available_ram_gb) across Windows, macOS, and Linux."""
    if os.name == "nt":
        try:
            class _MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = _MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):  # type: ignore[attr-defined]
                total = round(stat.ullTotalPhys / (1024 ** 3), 2)
                avail = round(stat.ullAvailPhys / (1024 ** 3), 2)
                if total > 0:
                    return total, max(1.0, avail)
        except Exception:
            pass
    else:
        try:
            page_size = os.sysconf("SC_PAGE_SIZE")
            phys_pages = os.sysconf("SC_PHYS_PAGES")
            avail_pages = os.sysconf("SC_AVPHYS_PAGES") if "SC_AVPHYS_PAGES" in os.sysconf_names else int(phys_pages * 0.6)
            total = round((page_size * phys_pages) / (1024 ** 3), 2)
            avail = round((page_size * avail_pages) / (1024 ** 3), 2)
            if total > 0:
                return total, max(1.0, avail)
        except Exception:
            pass
    return 16.0, 8.0


_CPU_SAMPLE_CACHE: dict[str, float] = {"ts": 0.0, "busy_pct": 18.0}
_GPU_SAMPLE_CACHE: dict[str, Any] = {"ts": 0.0, "busy_pct": 0.0, "vram_free_mb": 0, "vram_total_mb": 0, "temp_c": 0}
_STATIC_HW_CACHE: dict[str, Any] = {}


def _detect_cpu_load_pct() -> float:
    """Measure live host CPU busy percentage (0.0 - 100.0) with a 2.0s cache."""
    now = time.monotonic()
    if now - _CPU_SAMPLE_CACHE["ts"] < 2.0:
        return _CPU_SAMPLE_CACHE["busy_pct"]
    busy = _CPU_SAMPLE_CACHE["busy_pct"]
    if os.name == "nt":
        try:
            class _FILETIME(ctypes.Structure):
                _fields_ = [("dwLowDateTime", ctypes.c_ulong), ("dwHighDateTime", ctypes.c_ulong)]

            def _read_times() -> tuple[int, int]:
                idle, kernel, user = _FILETIME(), _FILETIME(), _FILETIME()
                ctypes.windll.kernel32.GetSystemTimes(  # type: ignore[attr-defined]
                    ctypes.byref(idle),
                    ctypes.byref(kernel),
                    ctypes.byref(user),
                )
                i_val = (idle.dwHighDateTime << 32) | idle.dwLowDateTime
                k_val = (kernel.dwHighDateTime << 32) | kernel.dwLowDateTime
                u_val = (user.dwHighDateTime << 32) | user.dwLowDateTime
                return i_val, k_val + u_val

            i1, t1 = _read_times()
            time.sleep(0.06)
            i2, t2 = _read_times()
            dt = max(1, t2 - t1)
            di = max(0, i2 - i1)
            busy = round(max(0.0, min(100.0, (1.0 - (di / dt)) * 100.0)), 1)
        except Exception:
            pass
    else:
        try:
            load1, _, _ = os.getloadavg()  # type: ignore[attr-defined]
            cores = max(1, int(os.cpu_count() or 4))
            busy = round(max(0.0, min(100.0, (load1 / cores) * 100.0)), 1)
        except Exception:
            pass
    _CPU_SAMPLE_CACHE["ts"] = now
    _CPU_SAMPLE_CACHE["busy_pct"] = busy
    return busy


def _detect_nvidia_gpu_telemetry() -> dict[str, Any]:
    """Query live NVIDIA GPU utilization and free VRAM via nvidia-smi (cached for 2.5s)."""
    now = time.monotonic()
    if now - float(_GPU_SAMPLE_CACHE.get("ts") or 0.0) < 2.5:
        return dict(_GPU_SAMPLE_CACHE)
    smi = shutil.which("nvidia-smi")
    if not smi and os.name == "nt":
        candidate = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "nvidia-smi.exe"
        if candidate.exists():
            smi = str(candidate)
    if smi:
        try:
            kwargs: dict[str, Any] = {
                "capture_output": True,
                "text": True,
                "timeout": 1.5,
            }
            if os.name == "nt":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            res = subprocess.run(
                [
                    smi,
                    "--query-gpu=utilization.gpu,memory.free,memory.total,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                **kwargs,
            )
            if res.returncode == 0 and res.stdout.strip():
                first_line = res.stdout.strip().splitlines()[0]
                parts = [p.strip() for p in first_line.split(",")]
                if len(parts) >= 3:
                    _GPU_SAMPLE_CACHE.update({
                        "ts": now,
                        "busy_pct": float(parts[0] or 0.0),
                        "vram_free_mb": int(float(parts[1] or 0)),
                        "vram_total_mb": int(float(parts[2] or 0)),
                        "temp_c": int(float(parts[3] or 0)) if len(parts) >= 4 else 0,
                    })
                    return dict(_GPU_SAMPLE_CACHE)
        except Exception:
            pass
    _GPU_SAMPLE_CACHE["ts"] = now
    return dict(_GPU_SAMPLE_CACHE)


def _detect_cpu_and_gpus() -> tuple[str, list[str]]:
    if _STATIC_HW_CACHE.get("cpu_name") and _STATIC_HW_CACHE.get("gpus") is not None:
        return str(_STATIC_HW_CACHE["cpu_name"]), list(_STATIC_HW_CACHE["gpus"])
    cpu_name = platform.processor() or "CPU"
    gpus: list[str] = []
    if os.name == "nt":
        try:
            import winreg  # type: ignore[import-not-found]

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\Description\System\CentralProcessor\0",
            ) as key:
                val, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                if val and str(val).strip():
                    cpu_name = str(val).strip()
        except Exception:
            pass
        try:
            import winreg  # type: ignore[import-not-found]

            display_cls = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, display_cls) as base_key:
                for idx in range(16):
                    sub_name = f"{idx:04d}"
                    try:
                        with winreg.OpenKey(base_key, sub_name) as sub_key:
                            desc, _ = winreg.QueryValueEx(sub_key, "DriverDesc")
                            name = str(desc or "").strip()
                            if not name:
                                continue
                            lower = name.lower()
                            if any(skip in lower for skip in ("basic display", "remote", "parsec", "virtual", "indirect")):
                                continue
                            if name not in gpus:
                                gpus.append(name)
                    except OSError:
                        continue
        except Exception:
            pass
    elif sys.platform == "darwin" and platform.machine() == "arm64":
        gpus.append("Apple Silicon GPU")
    _STATIC_HW_CACHE["cpu_name"] = cpu_name
    _STATIC_HW_CACHE["gpus"] = list(gpus)
    return cpu_name, gpus


_LIVE_HW_CACHE: dict[str, Any] = {"ts": 0.0, "profile": None}
_FG_GPU_APP_CACHE: dict[str, Any] = {"ts": 0.0, "apps": []}

_KNOWN_FOREGROUND_GPU_APPS: frozenset[str] = frozenset({
    "league of legends.exe",
    "leagueclientuxrender.exe",
    "valorant-win64-shipping.exe",
    "valorant.exe",
    "cs2.exe",
    "dota2.exe",
    "genshinimpact.exe",
    "starrail.exe",
    "client-win64-shipping.exe",
    "eldenring.exe",
    "cyberpunk2077.exe",
    "gta5.exe",
    "playgtav.exe",
    "fc24.exe",
    "fc25.exe",
    "tslgame.exe",
    "r5apex.exe",
    "overwatch.exe",
    "naraka.exe",
    "blackmythwukong.exe",
    "b1-win64-shipping.exe",
    "blender.exe",
    "afterfx.exe",
    "adobe premiere pro.exe",
    "resolve.exe",
    "unrealeditor.exe",
    "unity.exe",
    "obs64.exe",
})


def _detect_foreground_gpu_workload() -> list[str]:
    """Fast (<0.5ms) native Win32 process snapshot detecting active 3D games / DCC GPU workloads."""
    now = time.monotonic()
    if now - float(_FG_GPU_APP_CACHE.get("ts") or 0.0) < 4.0:
        return list(_FG_GPU_APP_CACHE.get("apps") or [])
    detected: list[str] = []
    if os.name == "nt":
        try:
            TH32CS_SNAPPROCESS = 0x00000002

            class _PROCESSENTRY32W(ctypes.Structure):
                _fields_ = [
                    ("dwSize", ctypes.c_ulong),
                    ("cntUsage", ctypes.c_ulong),
                    ("th32ProcessID", ctypes.c_ulong),
                    ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", ctypes.c_ulong),
                    ("cntThreads", ctypes.c_ulong),
                    ("th32ParentProcessID", ctypes.c_ulong),
                    ("pcPriClassBase", ctypes.c_long),
                    ("dwFlags", ctypes.c_ulong),
                    ("szExeFile", ctypes.c_wchar * 260),
                ]

            k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
            invalid = ctypes.c_void_p(-1).value
            if snap and snap != invalid:
                try:
                    entry = _PROCESSENTRY32W()
                    entry.dwSize = ctypes.sizeof(_PROCESSENTRY32W)
                    ok = k32.Process32FirstW(snap, ctypes.byref(entry))
                    seen_lower: set[str] = set()
                    while ok:
                        exe = str(entry.szExeFile or "").strip()
                        low = exe.lower()
                        if low in _KNOWN_FOREGROUND_GPU_APPS and low not in seen_lower:
                            seen_lower.add(low)
                            detected.append(exe)
                        ok = k32.Process32NextW(snap, ctypes.byref(entry))
                finally:
                    k32.CloseHandle(snap)
        except Exception:
            pass
    _FG_GPU_APP_CACHE["ts"] = now
    _FG_GPU_APP_CACHE["apps"] = list(detected)
    return detected


def worker_qos_enabled() -> bool:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return False
    val = str(os.getenv("COFI_ENABLE_WORKER_QOS") or "").strip().lower()
    return val in {"1", "true", "yes", "on"}


def background_worker_creationflags(base_flags: int = 0) -> int:
    """Return Windows creationflags keeping worker subtrees hidden at full normal priority."""
    flags = int(base_flags or 0)
    if os.name == "nt":
        flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    return flags


def apply_background_worker_qos(process_or_handle: Any, affinity_mask: int | None = None) -> bool:
    """No-op by default so export workers run at full multi-core CPU & NVENC CapCut speed."""
    return False


def background_worker_env_overrides(profile: dict[str, Any] | None = None) -> dict[str, str]:
    """Thread & concurrency environment variables inherited by Edit/Footage/Voice child scripts."""
    hw = profile if isinstance(profile, dict) else detect_hardware_profile()
    ff_threads = str(max(1, int(hw.get("edit_ffmpeg_threads") or 2)))
    max_workers = str(max(1, int(hw.get("edit_worker_concurrency") or 2)))
    return {
        "COFI_EDIT_MAX_WORKERS": max_workers,
        "COFI_EDIT_FFMPEG_THREADS": ff_threads,
        "COFI_VRAM_FREE_MB": str(int(hw.get("vram_free_mb") or 0)),
        "COFI_GOVERNOR_MODE": str(hw.get("governor_mode") or "balanced_smooth"),
        "FFMPEG_THREADS": ff_threads,
        "OMP_NUM_THREADS": ff_threads,
        "OPENBLAS_NUM_THREADS": ff_threads,
        "MKL_NUM_THREADS": ff_threads,
        "NUMEXPR_NUM_THREADS": ff_threads,
        "UV_THREADPOOL_SIZE": str(max(2, min(4, int(max_workers) + 1))),
    }


def format_smart_hardware_contract(phase: str = "edit") -> str:
    """Build live Smart Hardware & VRAM Governor directive injected into Agent prompts."""
    hw = detect_hardware_profile()
    max_w = int(hw.get("edit_worker_concurrency") or 2)
    ff_t = int(hw.get("edit_ffmpeg_threads") or 2)
    nvenc_c = int(hw.get("nvenc_concurrency") or 1)
    vram_free = int(hw.get("vram_free_mb") or 0)
    vram_tot = int(hw.get("vram_total_mb") or 0)
    fg_apps = hw.get("foreground_gpu_apps") or []
    fg_note = f" (Foreground GPU app active: {', '.join(fg_apps[:2])})" if fg_apps else ""
    hwaccel_rule = (
        "VRAM is tight or a foreground 3D app/game is active: DO NOT pass `-hwaccel cuda` / `h264_nvenc` inside ad-hoc Edit slicing scripts — use CPU `-c:v libx264 -preset veryfast -threads "
        f"{ff_t}` so 100% of GPU VRAM stays smooth for foreground tasks."
        if not hw.get("prefer_edit_hwaccel")
        else f"When running `ffmpeg`, cap `-threads {ff_t}` and at most `{nvenc_c}` concurrent GPU encode stream(s)."
    )
    return (
        f"\nSMART HARDWARE & VRAM GOVERNOR CONTRACT (AUTO-DETECTED FOR `{phase.upper()}` — ZERO PC LAG LAW):\n"
        f"- Host Hardware Telemetry: `{hw.get('gpu_name')}` (VRAM free `{vram_free}/{vram_tot} MB`), "
        f"CPU free `{hw.get('cpu_free_pct')}%` (`{hw.get('logical_cores')}` logical threads, `{hw.get('reserved_ui_threads')}` UI/Game threads reserved), "
        f"RAM free `{hw.get('available_ram_gb')}/{hw.get('total_ram_gb')} GB` -> Active Mode: **`{hw.get('governor_mode')}`**{fg_note}.\n"
        f"- STRICT MULTI-THREAD & VRAM CAPS FOR ALL PYTHON / NODE / FFMPEG SCRIPTS YOU WRITE OR RUN:\n"
        f"  1. NEVER spawn `ThreadPoolExecutor` / `ProcessPoolExecutor` with `max_workers > {max_w}` (strict cap: `max_workers={max_w}`, also exposed via `os.environ['COFI_EDIT_MAX_WORKERS']`). NEVER use `max_workers=8`!\n"
        f"  2. ALWAYS pass `-threads {ff_t}` to every `ffmpeg` / `ffprobe` command you invoke in custom scripts.\n"
        f"  3. {hwaccel_rule}\n"
    )


def detect_hardware_profile(*, force_refresh: bool = False) -> dict[str, Any]:
    """Real-Time Adaptive Resource Governor: inspects remaining CPU, RAM, and GPU VRAM to optimize render speed without freezing the PC."""
    now_ts = time.monotonic()
    cached = _LIVE_HW_CACHE.get("profile")
    if not force_refresh and isinstance(cached, dict) and (now_ts - float(_LIVE_HW_CACHE.get("ts") or 0.0)) < 8.0:
        return dict(cached)
    logical_cores = max(1, int(os.cpu_count() or 4))
    total_ram_gb, available_ram_gb = _detect_system_memory_gb()
    cpu_name, gpus = _detect_cpu_and_gpus()
    cpu_busy_pct = _detect_cpu_load_pct()
    cpu_free_pct = round(max(5.0, 100.0 - cpu_busy_pct), 1)

    gpu_vendor = "software"
    primary_gpu = gpus[0] if gpus else "Software Renderer"
    for gpu in gpus:
        low = gpu.lower()
        if any(k in low for k in ("nvidia", "geforce", "rtx", "gtx", "quadro", "tesla")):
            gpu_vendor = "nvidia"
            primary_gpu = gpu
            break
        if any(k in low for k in ("amd", "radeon", "rx ")):
            gpu_vendor = "amd"
            primary_gpu = gpu
            break
        if "apple" in low:
            gpu_vendor = "apple"
            primary_gpu = gpu
            break
        if any(k in low for k in ("intel", "arc", "iris", "uhd")):
            gpu_vendor = "intel"
            primary_gpu = gpu

    gpu_stats = _detect_nvidia_gpu_telemetry() if gpu_vendor == "nvidia" else {}
    gpu_busy_pct = float(gpu_stats.get("busy_pct") or 0.0)
    vram_free_mb = int(gpu_stats.get("vram_free_mb") or 0)
    vram_total_mb = int(gpu_stats.get("vram_total_mb") or 0)
    gpu_temp_c = int(gpu_stats.get("temp_c") or 0)
    foreground_gpu_apps: list[str] = []
    has_fg_game = False
    foreground_gpu_active = False

    # CapCut-Speed Turbo Export Profile: unleash all CPU threads and full NVENC streams
    reserved_ui_threads = 0
    usable_cpu_threads = logical_cores
    reserved_ram_gb = 2.0
    usable_ram_gb = max(2.0, round(available_ram_gb - reserved_ram_gb, 2))
    usable_vram_mb = max(0, vram_free_mb - 512) if vram_total_mb > 0 else 0

    export_concurrency = 8
    still_concurrency = 8
    nvenc_concurrency = 6 if gpu_vendor == "nvidia" else 2
    ffmpeg_threads = 6
    offthreadvideo_threads = 6
    remotion_concurrency = 8

    cache_size_mb = 768
    cache_size_bytes = cache_size_mb * 1024 * 1024
    affinity_mask = 0

    governor_mode = "turbo_max"
    governor_label = "Turbo tối đa · CapCut Speed"
    edit_worker_concurrency = 6
    edit_ffmpeg_threads = 6
    prefer_edit_hwaccel = bool(gpu_vendor == "nvidia")

    has_hw_gpu = gpu_vendor in {"nvidia", "amd", "intel", "apple"}
    gl_backend = "angle" if has_hw_gpu else "swangle"
    hardware_acceleration = "if-possible" if has_hw_gpu else "disable"

    vram_badge = (
        f", VRAM trống {vram_free_mb / 1024:.1f}/{vram_total_mb / 1024:.0f}GB"
        if vram_total_mb > 0
        else ""
    )

    profile = {
        "cpu_name": cpu_name,
        "logical_cores": logical_cores,
        "cpu_busy_pct": cpu_busy_pct,
        "cpu_free_pct": cpu_free_pct,
        "usable_cpu_threads": usable_cpu_threads,
        "reserved_ui_threads": reserved_ui_threads,
        "affinity_mask": None,
        "use_low_priority": False,
        "total_ram_gb": total_ram_gb,
        "available_ram_gb": available_ram_gb,
        "usable_ram_gb": usable_ram_gb,
        "gpu_name": primary_gpu,
        "gpu_vendor": gpu_vendor,
        "gpu_busy_pct": gpu_busy_pct,
        "vram_free_mb": vram_free_mb,
        "vram_total_mb": vram_total_mb,
        "usable_vram_mb": usable_vram_mb,
        "gpu_temp_c": gpu_temp_c,
        "gpus": gpus,
        "foreground_gpu_active": foreground_gpu_active,
        "foreground_gpu_apps": foreground_gpu_apps,
        "governor_mode": governor_mode,
        "governor_label": governor_label,
        "edit_worker_concurrency": edit_worker_concurrency,
        "edit_ffmpeg_threads": edit_ffmpeg_threads,
        "prefer_edit_hwaccel": prefer_edit_hwaccel,
        "export_concurrency": export_concurrency,
        "remotion_concurrency": remotion_concurrency,
        "still_concurrency": still_concurrency,
        "nvenc_concurrency": nvenc_concurrency,
        "ffmpeg_threads": ffmpeg_threads,
        "offthreadvideo_threads": offthreadvideo_threads,
        "cache_size_bytes": cache_size_bytes,
        "cache_size_mb": cache_size_mb,
        "gl_backend": gl_backend,
        "hardware_acceleration": hardware_acceleration,
        "x264_preset": "ultrafast",
        "turbo_nvenc": gpu_vendor == "nvidia",
        "summary": (
            f"CPU {usable_cpu_threads}/{logical_cores} luồng · "
            f"RAM trống {available_ram_gb:.1f}/{total_ram_gb:.0f}GB · "
            f"{primary_gpu}"
            + (f" [Turbo NVENC{vram_badge}]" if gpu_vendor == "nvidia" else "")
            + f" → {governor_label}: {still_concurrency} tab dựng + {nvenc_concurrency} luồng GPU ({ffmpeg_threads} thread/worker)"
        ),
    }
    _LIVE_HW_CACHE["ts"] = now_ts
    _LIVE_HW_CACHE["profile"] = dict(profile)
    return profile


class BackgroundRenderCache:
    """Render timeline to MP4 with automatic hardware optimization.

    By default, rendering runs in a single pass at Export time (not repeatedly
    during Edit/edit_chat), while preserving chunk invalidation if partial re-exports
    are needed later.
    """

    VERSION = 1
    FINAL_VALIDATION_VERSION = 5

    def __init__(
        self,
        remotion_dir: str | Path,
        *,
        chunk_seconds: int | None = None,
        concurrency: int | None = None,
        poll_interval: float = 1.0,
        runner: Callable[[list[str], Path, Path], int] | None = None,
    ) -> None:
        self.remotion_dir = Path(remotion_dir).resolve()
        self.hardware_profile = detect_hardware_profile()
        # Default chunk size is 10800s (180 minutes) so videos render in 1 single continuous pass
        # with per-shot content-hash caching in .render_cache/universal_segments/.
        self.chunk_seconds = max(
            10,
            int(
                chunk_seconds
                if chunk_seconds is not None
                else _env_int("COFI_RENDER_CACHE_CHUNK_SEC", 10800, 10)
            ),
        )
        self.concurrency = max(
            1,
            int(
                concurrency
                if concurrency is not None
                else _env_int("COFI_RENDER_CACHE_CONCURRENCY", self.hardware_profile["export_concurrency"], 1)
            ),
        )
        self._explicit_concurrency = concurrency is not None or bool(os.getenv("COFI_RENDER_CACHE_CONCURRENCY"))
        self.poll_interval = max(0.05, float(poll_interval))
        self.runner = runner or self._run_process
        self.enabled = str(os.getenv("COFI_RENDER_CACHE_ENABLED", "1")).strip().lower() not in {"0", "false", "no", "off"}
        self.render_during_edit = str(os.getenv("COFI_RENDER_DURING_EDIT", "0")).strip().lower() in {"1", "true", "yes", "on"}
        self._guard = threading.RLock()
        self._threads: dict[str, threading.Thread] = {}
        self._stops: dict[str, threading.Event] = {}
        self._processes: dict[str, subprocess.Popen[Any]] = {}
        self._render_locks: dict[str, threading.RLock] = {}

    @staticmethod
    def _manifest_path(workspace: Path) -> Path:
        return workspace / "render_cache_manifest.json"

    def _source_signature(self) -> str:
        digest = hashlib.sha256()
        src = self.remotion_dir / "src"
        extensions = {".ts", ".tsx", ".js", ".jsx", ".css", ".json"}
        if src.exists():
            for path in sorted(item for item in src.rglob("*") if item.is_file() and item.suffix.lower() in extensions):
                if path.name.startswith(".auto_standalone_"):
                    continue
                digest.update(str(path.relative_to(self.remotion_dir)).encode("utf-8", errors="replace"))
                digest.update(path.read_bytes())
        turbo_script = self.remotion_dir / "scripts" / "turbo-nvenc-export.mjs"
        if turbo_script.is_file():
            digest.update(b"scripts/turbo-nvenc-export.mjs")
            digest.update(turbo_script.read_bytes())
        universal_py = self.remotion_dir / "scripts" / "universal_master_render.py"
        if universal_py.is_file():
            digest.update(b"scripts/universal_master_render.py")
            digest.update(universal_py.read_bytes())
        return digest.hexdigest()

    def _resolve_composition_total_frames(self, job_id: str | None) -> int | None:
        if not job_id:
            return None
        src_dir = self.remotion_dir / "src"
        if not src_dir.is_dir():
            return None
        for path in sorted(src_dir.glob("*Data.ts")):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if str(job_id) not in text:
                continue
            match = re.search(
                r"(?:DURATION_FRAMES|TOTAL_FRAMES)\s*=\s*(\d+)",
                text,
            )
            if match:
                val = int(match.group(1))
                if val > 0:
                    return val
        return None

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _beat_id(beat: dict[str, Any]) -> str:
        return str(beat.get("beat_id") or "").strip()

    @staticmethod
    def _chunk_matches_beat(chunk: dict[str, Any], target_beat_id: str) -> bool:
        target = str(target_beat_id or "").strip()
        if not target:
            return False
        target_root = target.split("-")[0]
        for bid in chunk.get("beat_ids") or []:
            b_str = str(bid or "").strip()
            if not b_str:
                continue
            b_root = b_str.split("-")[0]
            if b_str == target or b_root == target or b_str == target_root:
                return True
        return False

    def snapshot_beat_signatures(
        self,
        workspace: str | Path,
        beats: list[dict[str, Any]] | None = None,
    ) -> dict[str, str]:
        """Compute deterministic per-beat content signatures across manifests and Remotion source."""
        ws = Path(workspace).resolve()
        if beats is None:
            vis = self._read_json(ws / "visual_manifest.json")
            beats_list = [b for b in (vis.get("beats") or []) if isinstance(b, dict)]
        else:
            beats_list = [b for b in beats if isinstance(b, dict)]
        if not beats_list:
            return {}

        vox = self._read_json(ws / "vox_scene_manifest.json")
        vox_by_beat: dict[str, list[dict[str, Any]]] = {}
        for scene in vox.get("scenes") or []:
            if isinstance(scene, dict) and scene.get("beat_id"):
                bid = str(scene.get("beat_id")).strip()
                vox_by_beat.setdefault(bid, []).append(scene)

        media = self._read_json(ws / "remotion_media_manifest.json")
        media_by_beat: dict[str, list[dict[str, Any]]] = {}
        for item in media.get("media_items") or []:
            if isinstance(item, dict) and item.get("beat_id"):
                bid = str(item.get("beat_id")).strip()
                media_by_beat.setdefault(bid, []).append(item)

        src_dir = self.remotion_dir / "src"
        src_texts: list[tuple[str, str]] = []
        extensions = {".ts", ".tsx", ".js", ".jsx", ".css", ".json"}
        if src_dir.exists():
            for path in sorted(p for p in src_dir.rglob("*") if p.is_file() and p.suffix.lower() in extensions):
                try:
                    rel = str(path.relative_to(self.remotion_dir))
                    text = path.read_text(encoding="utf-8", errors="replace")
                    src_texts.append((rel, text))
                except OSError:
                    continue

        signatures: dict[str, str] = {}
        for beat in beats_list:
            bid = self._beat_id(beat)
            if not bid:
                continue
            root_id = bid.split("-")[0]
            snippets: list[str] = []
            for rel, text in src_texts:
                for token in ({bid, root_id} if root_id != bid else {bid}):
                    idx = text.find(token)
                    while idx != -1:
                        lo = max(0, idx - 240)
                        hi = min(len(text), idx + 640)
                        snippets.append(f"{rel}:{text[lo:hi]}")
                        idx = text.find(token, idx + len(token))
            payload = {
                "beat": beat,
                "vox": vox_by_beat.get(bid) or vox_by_beat.get(root_id) or [],
                "media": media_by_beat.get(bid) or media_by_beat.get(root_id) or [],
                "src_snippets": snippets,
            }
            raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8", errors="replace")
            signatures[bid] = hashlib.sha256(raw).hexdigest()
        return signatures

    @staticmethod
    def _fps(job: dict[str, Any]) -> int:
        for value in (
            job.get("fps"),
            (job.get("production_recipe") or {}).get("fps") if isinstance(job.get("production_recipe"), dict) else None,
        ):
            try:
                fps = int(value or 0)
            except (TypeError, ValueError):
                fps = 0
            if fps > 0:
                return fps
        return 30

    @staticmethod
    def _resolution(job: dict[str, Any]) -> dict[str, int]:
        contract = (job.get("production_recipe") or {}).get("quality_contract") if isinstance(job.get("production_recipe"), dict) else {}
        minimum = (contract or {}).get("min_resolution") if isinstance(contract, dict) else {}
        try:
            width = int((minimum or {}).get("width") or 1920)
            height = int((minimum or {}).get("height") or 1080)
        except (TypeError, ValueError):
            width, height = 1920, 1080
        return {"width": max(1, width), "height": max(1, height)}

    def _timings(self, workspace: Path, beats: list[dict[str, Any]]) -> list[dict[str, Any]]:
        voice = self._read_json(workspace / "voice_manifest.json")
        voice_by_id = {
            str(item.get("beat_id") or ""): item
            for item in (voice.get("beats") or [])
            if isinstance(item, dict) and item.get("beat_id")
        }
        parent_groups: dict[str, list[dict[str, Any]]] = {}
        for beat in beats:
            bid = self._beat_id(beat)
            if not bid or bid in voice_by_id:
                continue
            pid = str(beat.get("parent_beat_id") or bid.split("-")[0]).strip()
            parent_groups.setdefault(pid, []).append(beat)

        sub_timings_by_id: dict[str, tuple[float, float]] = {}
        for pid, group in parent_groups.items():
            vb = voice_by_id.get(pid)
            if not isinstance(vb, dict):
                continue
            try:
                p_start = float(vb.get("visual_open_sec") if vb.get("visual_open_sec") is not None else vb.get("start_sec"))
                p_end = float(vb.get("visual_close_sec") if vb.get("visual_close_sec") is not None else vb.get("end_sec"))
            except (TypeError, ValueError):
                continue
            if p_end <= p_start:
                continue
            if len(group) == 1:
                sub_timings_by_id[self._beat_id(group[0])] = (p_start, p_end)
            else:
                weights = [
                    max(0.2, float(g.get("duration_sec") or g.get("target_duration_sec") or g.get("estimated_duration_sec") or 1.0))
                    for g in group
                ]
                total_w = sum(weights) or float(len(group))
                span = p_end - p_start
                acc = p_start
                for g_idx, (g, w) in enumerate(zip(group, weights)):
                    nxt = p_end if g_idx == len(group) - 1 else acc + span * (w / total_w)
                    sub_timings_by_id[self._beat_id(g)] = (acc, max(acc + 0.001, nxt))
                    acc = nxt

        result: list[dict[str, Any]] = []
        cursor = 0.0
        for beat in beats:
            beat_id = self._beat_id(beat)
            if not beat_id:
                continue
            voice_beat = voice_by_id.get(beat_id) or {}
            try:
                if voice_beat:
                    start = float(voice_beat.get("visual_open_sec") if voice_beat.get("visual_open_sec") is not None else voice_beat.get("start_sec"))
                    end = float(voice_beat.get("visual_close_sec") if voice_beat.get("visual_close_sec") is not None else voice_beat.get("end_sec"))
                elif beat_id in sub_timings_by_id:
                    start, end = sub_timings_by_id[beat_id]
                else:
                    raise ValueError("no voice mapping")
            except (TypeError, ValueError):
                try:
                    b_start = float(beat.get("start_sec"))
                    b_end = float(beat.get("end_sec"))
                    if b_end <= b_start:
                        raise ValueError("invalid beat start/end")
                    start, end = b_start, b_end
                except (TypeError, ValueError):
                    start = cursor
                    try:
                        duration = float(beat.get("duration_sec") or beat.get("target_duration_sec") or beat.get("estimated_duration_sec") or 0)
                    except (TypeError, ValueError):
                        duration = 0.0
                    end = start + max(0.001, duration)
            if end <= start:
                end = start + 0.001
            result.append({"beat_id": beat_id, "start_sec": start, "end_sec": end})
            cursor = max(cursor, end)
        return result

    def _build_manifest(self, job: dict[str, Any], workspace: Path, beats: list[dict[str, Any]]) -> dict[str, Any]:
        timings = self._timings(workspace, beats)
        if not timings:
            raise RuntimeError("Không có timing beat để tạo background render cache")
        fps = self._fps(job)
        total_seconds = max(item["end_sec"] for item in timings)
        voice_doc = self._read_json(workspace / "voice_manifest.json")
        try:
            voice_dur = float(voice_doc.get("duration_sec") or 0.0)
        except (TypeError, ValueError):
            voice_dur = 0.0
        last_speech_end = 0.0
        for vb_item in voice_doc.get("beats") or []:
            if isinstance(vb_item, dict):
                try:
                    last_speech_end = max(last_speech_end, float(vb_item.get("speech_end_sec") or 0.0))
                except (TypeError, ValueError):
                    pass
        min_outro_total_sec = (last_speech_end + 3.8) if last_speech_end > 0.0 else 0.0
        if max(voice_dur, min_outro_total_sec) > total_seconds:
            total_seconds = max(voice_dur, min_outro_total_sec)
        raw_frames = total_seconds * fps
        nearest_frames = round(raw_frames)
        total_frames = max(1, int(nearest_frames if abs(raw_frames - nearest_frames) <= 0.25 else math.ceil(raw_frames)))
        edit_doc = self._read_json(workspace / "edit_manifest.json")
        try:
            edit_frames = int(edit_doc.get("duration_in_frames") or 0)
        except (TypeError, ValueError):
            edit_frames = 0
        comp_frames = self._resolve_composition_total_frames(str(job.get("id") or "")) or edit_frames
        max_comp_slack = max(150, int(total_frames * 0.03))
        if comp_frames and comp_frames > total_frames and (comp_frames - total_frames) <= max_comp_slack:
            total_frames = comp_frames
        frames_per_chunk = max(1, self.chunk_seconds * fps)
        cache_root = workspace / ".render_cache"
        video_dir = cache_root / "video"
        audio_dir = cache_root / "audio"
        log_dir = cache_root / "logs"
        video_dir.mkdir(parents=True, exist_ok=True)
        audio_dir.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)

        chunks: list[dict[str, Any]] = []
        part_count = int(math.ceil(total_frames / frames_per_chunk))
        for index in range(part_count):
            start_frame = index * frames_per_chunk
            end_frame = min(((index + 1) * frames_per_chunk) - 1, total_frames - 1)
            start_sec = start_frame / fps
            end_sec = (end_frame + 1) / fps
            overlapping = [
                item["beat_id"]
                for item in timings
                if item["end_sec"] > start_sec and item["start_sec"] < end_sec
            ]
            name = f"part-{index + 1:04d}"
            chunks.append({
                "index": index + 1,
                "start_frame": start_frame,
                "end_frame": end_frame,
                "start_sec": round(start_sec, 6),
                "end_sec": round(end_sec, 6),
                "beat_ids": overlapping,
                "video_path": str((video_dir / f"{name}.mp4").resolve()),
                "audio_path": str((audio_dir / f"{name}.aac").resolve()),
                "log_path": str((log_dir / f"{name}.log").resolve()),
                "status": "pending",
                "attempts": 0,
                "rendered_at": None,
                "error": None,
                "dirty_beat_ids": [],
            })

        composition_id = str(job.get("composition_id") or f"Documentary-{job.get('id')}")
        output = workspace / "release" / "video.mp4"
        return {
            "version": self.VERSION,
            "job_id": job.get("id"),
            "composition_id": composition_id,
            "source_signature": self._source_signature(),
            "beat_signatures": self.snapshot_beat_signatures(workspace, beats),
            "dirty_beat_ids": [],
            "selective_invalidation": False,
            "fps": fps,
            "resolution": self._resolution(job),
            "chunk_seconds": self.chunk_seconds,
            "frames_per_chunk": frames_per_chunk,
            "duration_in_frames": total_frames,
            "duration_seconds": total_frames / fps,
            "output_path": str(output.resolve()),
            "chunks": chunks,
            "ready_chunks": 0,
            "total_chunks": len(chunks),
            "status": "pending",
            "status_message": "Chỉ render 1 lượt khi bấm Xuất video (không render ngầm lúc đang Edit).",
            "render_during_edit": self.render_during_edit,
            "hardware_profile": self.hardware_profile,
            "updated_at": _now(),
            "finalized_signature": None,
            "finalized_validation_version": None,
        }

    @staticmethod
    def _is_chunk_output_complete(chunk: dict[str, Any]) -> bool:
        """Check if chunk video & audio outputs exist and either status=='ready' or log confirms full encode completion."""
        if not isinstance(chunk, dict):
            return False
        video = Path(str(chunk.get("video_path") or ""))
        audio = Path(str(chunk.get("audio_path") or ""))
        try:
            if not video.exists() or video.stat().st_size <= 0:
                return False
            if not audio.exists() or audio.stat().st_size <= 0:
                return False
        except OSError:
            return False
        if chunk.get("status") == "ready":
            return True
        log = Path(str(chunk.get("log_path") or ""))
        try:
            if log.exists():
                with log.open("rb") as fh:
                    fh.seek(0, os.SEEK_END)
                    fsize = fh.tell()
                    fh.seek(max(0, fsize - 8192), os.SEEK_SET)
                    tail = fh.read().decode("utf-8", errors="replace")
                matches = re.findall(r"Encoded\s+(\d+)/(\d+)", tail)
                if matches:
                    done_f, total_f = int(matches[-1][0]), int(matches[-1][1])
                    if total_f > 0 and done_f >= total_f:
                        return True
        except OSError:
            pass
        return False

    def prepare(self, job: dict[str, Any], workspace: str | Path, beats: list[dict[str, Any]]) -> dict[str, Any]:
        workspace = Path(workspace).resolve()
        current = self._read_json(self._manifest_path(workspace))
        self.hardware_profile = detect_hardware_profile()
        planned = self._build_manifest(job, workspace, beats)
        planned["hardware_profile"] = self.hardware_profile

        old_beat_sigs = current.get("beat_signatures") if isinstance(current.get("beat_signatures"), dict) else {}
        new_beat_sigs = planned.get("beat_signatures") if isinstance(planned.get("beat_signatures"), dict) else {}
        auto_dirty_beats: list[str] = []
        if old_beat_sigs and new_beat_sigs and set(old_beat_sigs.keys()) == set(new_beat_sigs.keys()):
            diff = [bid for bid, sig in new_beat_sigs.items() if old_beat_sigs.get(bid) != sig]
            if 0 < len(diff) < len(new_beat_sigs):
                auto_dirty_beats = diff

        selective_mode = bool(current.get("selective_invalidation") or auto_dirty_beats)
        has_existing_chunks = any(
            isinstance(c, dict) and (c.get("status") in {"ready", "rendering"} or self._is_chunk_output_complete(c))
            for c in (current.get("chunks") or [])
        )
        same_source = bool(
            current.get("version") == self.VERSION
            and current.get("job_id") == planned.get("job_id")
            and current.get("composition_id") == planned.get("composition_id")
            and (current.get("source_signature") == planned.get("source_signature") or selective_mode or has_existing_chunks)
            and current.get("fps") == planned.get("fps")
            and current.get("frames_per_chunk") == planned.get("frames_per_chunk")
            and len(current.get("chunks") or []) == len(planned.get("chunks") or [])
        )
        compatible = bool(
            same_source
            and (
                current.get("duration_in_frames") == planned.get("duration_in_frames")
                or len(planned.get("chunks") or []) == 1
            )
        )
        if compatible:
            old_chunks = current.get("chunks") or []
            combined_dirty = sorted(
                set((current.get("dirty_beat_ids") or []) + auto_dirty_beats)
            )
            planned["dirty_beat_ids"] = combined_dirty
            if isinstance(current.get("last_delta_window_sec"), dict):
                planned["last_delta_window_sec"] = dict(current["last_delta_window_sec"])
            elif combined_dirty:
                timings = self._timings(workspace, beats)
                matched = [
                    t
                    for t in timings
                    if any(
                        self._chunk_matches_beat({"beat_ids": [t.get("beat_id")]}, b)
                        for b in combined_dirty
                    )
                ]
                if matched:
                    planned["last_delta_window_sec"] = {
                        "start_sec": round(min(float(t["start_sec"]) for t in matched), 3),
                        "end_sec": round(max(float(t["end_sec"]) for t in matched), 3),
                        "beat_ids": combined_dirty,
                    }
            for chunk, old in zip(planned["chunks"], old_chunks):
                chunk_dirty = sorted(
                    set(
                        (old.get("dirty_beat_ids") or [])
                        + [
                            b
                            for b in auto_dirty_beats
                            if self._chunk_matches_beat(chunk, b) or len(planned["chunks"]) == 1
                        ]
                    )
                )
                chunk["dirty_beat_ids"] = chunk_dirty
                if auto_dirty_beats and any(self._chunk_matches_beat(chunk, b) for b in auto_dirty_beats):
                    for field in ("video_path", "audio_path", "log_path"):
                        try:
                            Path(str(chunk.get(field) or "")).unlink(missing_ok=True)
                        except OSError:
                            pass
                    chunk["status"] = "pending"
                    continue
                if self._is_chunk_output_complete(old):
                    chunk.update({
                        "status": "ready",
                        "attempts": max(1, int(old.get("attempts") or 1)),
                        "rendered_at": old.get("rendered_at") or _now(),
                        "error": None,
                        "dirty_beat_ids": [],
                    })
            planned["selective_invalidation"] = bool(
                selective_mode and any(c.get("status") != "ready" for c in planned["chunks"])
            )
            if (
                current.get("duration_in_frames") == planned.get("duration_in_frames")
                and not auto_dirty_beats
                and all(c.get("status") == "ready" for c in planned["chunks"])
            ):
                planned["finalized_signature"] = current.get("finalized_signature")
                planned["finalized_validation_version"] = current.get("finalized_validation_version")
                planned["finalized_at"] = current.get("finalized_at")
        else:
            for chunk in (current.get("chunks") or []) + planned["chunks"]:
                if not isinstance(chunk, dict):
                    continue
                for field in ("video_path", "audio_path", "log_path"):
                    try:
                        Path(str(chunk.get(field) or "")).unlink(missing_ok=True)
                    except OSError:
                        pass
        self._refresh_summary(planned)
        _atomic_json(self._manifest_path(workspace), planned)
        return planned

    @staticmethod
    def _completed_frontier(workspace: Path, manifest: dict[str, Any]) -> tuple[set[str], float, str]:
        progress = BackgroundRenderCache._read_json(workspace / "edit_progress.json")
        completed = {str(value) for value in (progress.get("completed_beat_ids") or []) if str(value)}
        status = str(progress.get("status") or "").lower()
        frontier = 0.0
        for chunk in manifest.get("chunks") or []:
            # A fixed render chunk is safe once every beat touching that range has
            # been marked complete by the editor.
            if all(str(beat_id) in completed for beat_id in (chunk.get("beat_ids") or [])):
                frontier = max(frontier, float(chunk.get("end_sec") or 0))
            else:
                break
        return completed, frontier, status

    @staticmethod
    def _refresh_summary(manifest: dict[str, Any]) -> None:
        chunks = manifest.get("chunks") or []
        ready = sum(1 for chunk in chunks if chunk.get("status") == "ready")
        rendering = sum(1 for chunk in chunks if chunk.get("status") == "rendering")
        failed = sum(1 for chunk in chunks if chunk.get("status") == "failed")
        hw = manifest.get("hardware_profile") or {}
        hw_summary = str(hw.get("summary") or "").strip()
        manifest["ready_chunks"] = ready
        manifest["total_chunks"] = len(chunks)
        if chunks and ready == len(chunks):
            manifest["status"] = "ready"
            manifest["status_message"] = (
                f"Đã render xong {ready}/{len(chunks)} phần"
                + (f" · {hw_summary}" if hw_summary else ".")
            )
        elif rendering:
            manifest["status"] = "rendering"
            manifest["status_message"] = f"Đang render 1 lượt ({ready}/{len(chunks)} phần){f' · {hw_summary}' if hw_summary else ''}."
        elif failed:
            manifest["status"] = "partial"
            manifest["status_message"] = f"Đã render {ready}/{len(chunks)} phần · {failed} phần cần thử lại."
        else:
            manifest["status"] = "waiting"
            manifest["status_message"] = (
                f"Sẵn sàng xuất 1 lượt ({ready}/{len(chunks)} phần đã có sẵn)"
                + (f" · Tối ưu tự động: {hw_summary}" if hw_summary else "")
            )
        manifest["updated_at"] = _now()

    @staticmethod
    def _run_process(
        command: list[str],
        cwd: Path,
        log_path: Path,
        *,
        low_priority: bool = False,
        env_overrides: dict[str, str] | None = None,
        affinity_mask: int = 0,
        process_slot: dict[str, subprocess.Popen[Any]] | None = None,
        slot_key: str = "",
        append_log: bool = False,
    ) -> int:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        shell = str(command[0]).lower().endswith((".cmd", ".bat"))
        launch: list[str] | str = subprocess.list2cmdline(command) if shell else command
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 1)
            startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        env = None
        if env_overrides:
            env = dict(os.environ)
            env.update(env_overrides)
        mode = "a" if append_log else "w"
        with log_path.open(mode, encoding="utf-8", errors="replace") as handle:
            process = subprocess.Popen(
                launch,
                cwd=str(cwd),
                stdout=handle,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=creationflags,
                startupinfo=startupinfo,
                env=env,
                text=True,
                shell=shell,
            )
            if process_slot is not None and slot_key:
                process_slot[slot_key] = process
            try:
                return process.wait()
            finally:
                if process_slot is not None and slot_key:
                    process_slot.pop(slot_key, None)

    @staticmethod
    def _run_low_priority(command: list[str], cwd: Path, log_path: Path) -> int:
        return BackgroundRenderCache._run_process(command, cwd, log_path, low_priority=True)

    def _npx(self) -> str:
        npx = shutil.which("npx.cmd") or shutil.which("npx")
        if not npx:
            raise RuntimeError("Không tìm thấy npx để render video")
        return npx

    def _prepare_isolated_public_dir(self, workspace: Path, job_id: str | None) -> Path | None:
        if not job_id:
            return None
        pub_src = self.remotion_dir / "public"
        job_src = pub_src / "jobs" / str(job_id)
        if not pub_src.is_dir() or not job_src.is_dir():
            return None
        isolated = workspace / ".render_cache" / "public_dir"
        try:
            if isolated.exists():
                shutil.rmtree(isolated, ignore_errors=True)
            (isolated / "jobs").mkdir(parents=True, exist_ok=True)

            def _link_or_copy(src: str, dst: str) -> None:
                try:
                    os.link(src, dst)
                except OSError:
                    shutil.copy2(src, dst)

            shutil.copytree(job_src, isolated / "jobs" / str(job_id), copy_function=_link_or_copy, dirs_exist_ok=True)
            for item in pub_src.iterdir():
                if item.name == "jobs":
                    continue
                dst_item = isolated / item.name
                if item.is_file():
                    _link_or_copy(str(item), str(dst_item))
                elif item.is_dir():
                    shutil.copytree(item, dst_item, copy_function=_link_or_copy, dirs_exist_ok=True)
            return isolated
        except Exception:
            return None

    PREBAKE_PREFIX = "prebake|"

    def _any_render_active(self) -> bool:
        with self._guard:
            for key, proc in list(self._processes.items()):
                if str(key).startswith(self.PREBAKE_PREFIX):
                    continue
                if proc is not None and proc.poll() is None:
                    return True
            for thread in list(self._threads.values()):
                if thread is not None and thread.is_alive():
                    return True
            locks = list(self._render_locks.values())
        for lock in locks:
            if lock.acquire(blocking=False):
                lock.release()
            else:
                return True
        return False

    def cancel_prebake(self, workspace: str | Path | None = None) -> bool:
        """Stop an opportunistic VOX/CT prebake (the real export always wins)."""
        cancelled = False
        target = self.PREBAKE_PREFIX + str(Path(workspace).resolve()) if workspace is not None else None
        with self._guard:
            items = [(k, v) for k, v in self._processes.items() if str(k).startswith(self.PREBAKE_PREFIX)]
        for key, proc in items:
            if target is not None and key != target:
                continue
            if proc is not None and proc.poll() is None:
                try:
                    if os.name == "nt":
                        subprocess.run(
                            ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                            capture_output=True,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                        )
                    else:
                        proc.terminate()
                    cancelled = True
                except Exception:
                    pass
        return cancelled

    def prebake_standalone_async(
        self,
        job: dict[str, Any],
        workspace: str | Path,
        *,
        studio_running: bool = False,
    ) -> dict[str, Any]:
        """Bake VOX/CinemaText standalone clips + subtitle PNGs in the background.

        Low priority and opportunistic: skipped (never blocking the job) when
        Remotion Studio is open, another render/bake is active, or the turbo
        script is unavailable. A real export cancels it via cancel_prebake().
        """
        workspace = Path(workspace).resolve()
        if studio_running:
            return {"started": False, "reason": "studio_running"}
        turbo_script = self.remotion_dir / "scripts" / "turbo-nvenc-export.mjs"
        bundled_node = Path(__file__).resolve().parents[1] / "tools" / "node.exe"
        node_bin = os.getenv("COFI_NODE_BIN") or shutil.which("node") or (str(bundled_node) if bundled_node.exists() else None)
        if not turbo_script.exists() or not node_bin or not job.get("id"):
            return {"started": False, "reason": "turbo_unavailable"}
        with self._guard:
            existing = getattr(self, "_prebake_thread", None)
            if existing is not None and existing.is_alive():
                return {"started": False, "reason": "prebake_already_running"}
        if self._any_render_active():
            return {"started": False, "reason": "render_active"}

        composition_id = str(job.get("composition_id") or f"Documentary-{job.get('id')}")
        cache_root = workspace / ".render_cache"
        probe_video = cache_root / "video" / "prebake_probe.mp4"
        plan_path = cache_root / "prebake_plan.json"
        log_path = cache_root / "logs" / "prebake.log"
        command = [
            str(node_bin),
            str(turbo_script),
            "remotion",
            "render",
            composition_id,
            str(probe_video),
            "--frames=0-0",
            "--concurrency=4",
            f"--job-id={job.get('id')}",
            f"--public-dir={self.remotion_dir / 'public'}",
            f"--prepare-plan-only={plan_path}",
        ]
        slot_key = self.PREBAKE_PREFIX + str(workspace)

        def _run() -> None:
            started = time.time()
            status: dict[str, Any] = {"status": "running", "started_at": _now()}
            try:
                probe_video.parent.mkdir(parents=True, exist_ok=True)
                rc = self._run_process(
                    command,
                    self.remotion_dir,
                    log_path,
                    low_priority=True,
                    env_overrides={"COFI_PRIORITY_LOW": "1"},
                    process_slot=self._processes,
                    slot_key=slot_key,
                )
                status = {"status": "done" if rc == 0 else "failed", "returncode": rc}
            except Exception as exc:  # opportunistic: never raise
                status = {"status": "failed", "error": str(exc)[:400]}
            finally:
                plan_path.unlink(missing_ok=True)
                status["seconds"] = round(time.time() - started, 1)
                status["finished_at"] = _now()
                try:
                    _atomic_json(cache_root / "prebake_status.json", status)
                except Exception:
                    pass

        thread = threading.Thread(target=_run, name=f"cofi-prebake-{job.get('id')}", daemon=True)
        with self._guard:
            self._prebake_thread = thread
        thread.start()
        return {"started": True, "reason": "started", "log_path": str(log_path)}

    DEFAULT_TARGET_LUFS = -16.0

    @classmethod
    def _resolve_target_lufs(cls, job: dict[str, Any] | None) -> float:
        """Channel-profile loudness target (editing_dna.audio_rules.target_lufs).

        Reads the job's editing DNA snapshot first, then the channel profile
        snapshot, then data/channel_profiles.json; falls back to
        COFI_DEFAULT_TARGET_LUFS / -16 LUFS. Profile data only, no channel names.
        """
        def _pick(container: Any) -> float | None:
            if not isinstance(container, dict):
                return None
            rules = ((container.get("editing_dna") or container).get("audio_rules") or {}) if isinstance(container.get("editing_dna") or container, dict) else {}
            value = rules.get("target_lufs") if isinstance(rules, dict) else None
            try:
                return float(value) if value is not None and str(value).strip() != "" else None
            except (TypeError, ValueError):
                return None

        job = job if isinstance(job, dict) else {}
        for candidate in (job, job.get("channel_profile_snapshot")):
            value = _pick(candidate)
            if value is not None:
                return value
        profile_id = str(job.get("channel_profile_id") or "").strip()
        if profile_id:
            try:
                data = json.loads((Path(__file__).resolve().parents[1] / "data" / "channel_profiles.json").read_text(encoding="utf-8"))
                for prof in (data.get("profiles") or []) if isinstance(data, dict) else []:
                    if isinstance(prof, dict) and str(prof.get("id") or prof.get("profile_id") or "") == profile_id:
                        value = _pick(prof)
                        if value is not None:
                            return value
            except (OSError, ValueError):
                pass
        try:
            return float(os.getenv("COFI_DEFAULT_TARGET_LUFS", str(cls.DEFAULT_TARGET_LUFS)))
        except ValueError:
            return cls.DEFAULT_TARGET_LUFS

    def _render_chunk(self, manifest: dict[str, Any], chunk: dict[str, Any], *, render_all: bool = False) -> None:
        video = Path(str(chunk["video_path"]))
        audio = Path(str(chunk["audio_path"]))
        log = Path(str(chunk["log_path"]))
        video.parent.mkdir(parents=True, exist_ok=True)
        audio.parent.mkdir(parents=True, exist_ok=True)
        for path in (video, audio):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        frame_range = f"{chunk['start_frame']}-{chunk['end_frame']}"
        # Refresh hardware profile so live CPU load, free RAM, and free GPU VRAM are evaluated right before launching workers
        hw = detect_hardware_profile(force_refresh=True)
        self.hardware_profile = hw
        manifest["hardware_profile"] = hw
        if self._explicit_concurrency and not render_all:
            effective_concurrency = self.concurrency
        elif self._explicit_concurrency and render_all:
            effective_concurrency = max(self.concurrency, int(hw["export_concurrency"]))
        else:
            effective_concurrency = int(hw["export_concurrency"]) if render_all else max(2, int(hw["export_concurrency"]) // 2)

        still_concurrency = max(1, min(8, int(hw.get("still_concurrency") or 8)))
        nvenc_concurrency = max(1, min(6, int(hw.get("nvenc_concurrency") or 6)))
        ffmpeg_threads = max(1, min(6, int(hw.get("ffmpeg_threads") or 6)))
        offthread_threads = int(hw.get("offthreadvideo_threads") or 6)
        cache_size_bytes = int(hw.get("cache_size_bytes") or (768 * 1024 * 1024))
        gl_backend = str(hw.get("gl_backend") or "angle")
        hw_accel = str(hw.get("hardware_acceleration") or "if-possible")
        x264_preset = str(hw.get("x264_preset") or "ultrafast")
        affinity_mask = 0
        use_low_priority = False

        command = [
            self._npx(),
            "remotion",
            "render",
            str(manifest["composition_id"]),
            str(video),
            f"--frames={frame_range}",
            "--codec=h264",
            "--crf=16",
            "--jpeg-quality=95",
            "--pixel-format=yuv420p",
            f"--x264-preset={x264_preset}",
            f"--concurrency={effective_concurrency}",
            f"--offthreadvideo-video-threads={offthread_threads}",
            f"--offthreadvideo-cache-size-in-bytes={cache_size_bytes}",
            f"--media-cache-size-in-bytes={cache_size_bytes}",
            f"--gl={gl_backend}",
            f"--hardware-acceleration={hw_accel}",
            f"--separate-audio-to={audio}",
            "--for-seamless-aac-concatenation",
        ]
        workspace = video.parent.parent.parent
        slot_key = str(workspace.resolve())
        direct_pub = self.remotion_dir / "public"

        chunk["status"] = "rendering"
        chunk["attempts"] = int(chunk.get("attempts") or 0) + 1
        chunk["error"] = None
        if True:
            turbo_script = self.remotion_dir / "scripts" / "turbo-nvenc-export.mjs"
            turbo_enabled = str(os.getenv("COFI_TURBO_EXPORT", "1")).strip().lower() not in {"0", "false", "no", "off"}
            bundled_node = Path(__file__).resolve().parents[1] / "tools" / "node.exe"
            node_bin = os.getenv("COFI_NODE_BIN") or shutil.which("node") or (str(bundled_node) if bundled_node.exists() else None)
            returncode = -1
            env_overrides = {
                "COFI_STILL_CONCURRENCY": str(still_concurrency),
                "COFI_NVENC_CONCURRENCY": str(nvenc_concurrency),
                "COFI_FFMPEG_THREADS": str(ffmpeg_threads),
            }
            if manifest.get("target_lufs") is not None:
                # Turbo path: 2-pass loudnorm of the final mix to the channel target (non-blocking).
                env_overrides["COFI_TARGET_LUFS"] = str(manifest["target_lufs"])
                env_overrides.setdefault("COFI_TARGET_TP", "-1.0")
            if turbo_enabled and turbo_script.exists() and node_bin:
                dirty_beats = sorted(
                    {
                        str(b).strip()
                        for b in ((chunk.get("dirty_beat_ids") or []) + (manifest.get("dirty_beat_ids") or []))
                        if str(b).strip()
                    }
                )
                plan_path = video.parent.parent / "universal_render_plan.json"
                for _turbo_try in range(2):
                    plan_path.unlink(missing_ok=True)
                    turbo_prep_cmd = [
                        str(node_bin),
                        str(turbo_script),
                        "remotion",
                        "render",
                        str(manifest["composition_id"]),
                        str(video),
                        f"--frames={frame_range}",
                        f"--concurrency={still_concurrency}",
                        f"--nvenc-concurrency={nvenc_concurrency}",
                        f"--ffmpeg-threads={ffmpeg_threads}",
                        f"--separate-audio-to={audio}",
                        f"--job-id={manifest.get('job_id') or ''}",
                        f"--public-dir={direct_pub}",
                        f"--prepare-plan-only={plan_path}",
                    ]
                    if dirty_beats:
                        turbo_prep_cmd.append(f"--dirty-beats={','.join(dirty_beats)}")
                    prep_rc = self._run_process(
                        turbo_prep_cmd,
                        self.remotion_dir,
                        log,
                        low_priority=False,
                        env_overrides=env_overrides,
                        affinity_mask=None,
                        process_slot=self._processes,
                        slot_key=slot_key,
                        append_log=(_turbo_try > 0),
                    )
                    universal_py = self.remotion_dir / "scripts" / "universal_master_render.py"
                    if prep_rc == 0 and plan_path.is_file() and universal_py.is_file():
                        returncode = self._run_process(
                            [sys.executable, str(universal_py), str(plan_path)],
                            self.remotion_dir,
                            log,
                            low_priority=False,
                            env_overrides=env_overrides,
                            affinity_mask=None,
                            process_slot=self._processes,
                            slot_key=slot_key,
                            append_log=True,
                        )
                    if returncode == 0 and video.exists() and video.stat().st_size > 0 and audio.exists() and audio.stat().st_size > 0:
                        break
        if returncode != 0 or not video.exists() or video.stat().st_size <= 0 or not audio.exists() or audio.stat().st_size <= 0:
            returncode = self._run_process(
                command,
                self.remotion_dir,
                log,
                low_priority=use_low_priority,
                affinity_mask=affinity_mask,
                process_slot=self._processes,
                slot_key=slot_key,
                append_log=True,
            )
        if returncode != 0 or not video.exists() or video.stat().st_size <= 0 or not audio.exists() or audio.stat().st_size <= 0:
            chunk["status"] = "failed"
            chunk["error"] = f"Remotion chunk render exited with code {returncode}"
            return
        chunk["status"] = "ready"
        chunk["rendered_at"] = _now()
        chunk["error"] = None
        chunk["dirty_beat_ids"] = []

    def render_ready(
        self,
        job: dict[str, Any],
        workspace: str | Path,
        beats: list[dict[str, Any]],
        *,
        render_all: bool = False,
        stop_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        workspace = Path(workspace).resolve()
        key = str(workspace)
        with self._guard:
            render_lock = self._render_locks.setdefault(key, threading.RLock())
            active_stop = stop_event or self._stops.get(key)
        self.cancel_prebake(workspace)
        with render_lock:
            self.hardware_profile = detect_hardware_profile()
            if not self._explicit_concurrency:
                self.concurrency = max(1, int(self.hardware_profile["export_concurrency"]))
            manifest = self.prepare(job, workspace, beats)
            manifest["hardware_profile"] = self.hardware_profile
            manifest["target_lufs"] = self._resolve_target_lufs(job)
            source_signature = str(manifest.get("source_signature") or "")
            _, frontier, progress_status = self._completed_frontier(workspace, manifest)
            changed = False
            for chunk in manifest.get("chunks") or []:
                if active_stop is not None and active_stop.is_set():
                    break
                if self._is_chunk_output_complete(chunk):
                    if chunk.get("status") != "ready":
                        chunk["status"] = "ready"
                        chunk["rendered_at"] = chunk.get("rendered_at") or _now()
                        chunk["error"] = None
                        chunk["dirty_beat_ids"] = []
                        changed = True
                    continue
                chunk["status"] = "pending"
                eligible = bool(render_all or float(chunk.get("end_sec") or 0) <= frontier + 1e-6)
                if not eligible:
                    break
                # Codex/Studio can save source while a background chunk is being
                # encoded. Do not continue rendering later chunks from a newer
                # source while earlier chunks still belong to the old source.
                multi_chunk = len(manifest.get("chunks") or []) > 1
                if multi_chunk and self._source_signature() != source_signature:
                    return self.prepare(job, workspace, beats)
                chunk["status"] = "rendering"
                self._refresh_summary(manifest)
                _atomic_json(self._manifest_path(workspace), manifest)
                self._render_chunk(manifest, chunk, render_all=render_all)
                changed = True
                if multi_chunk and self._source_signature() != source_signature:
                    return self.prepare(job, workspace, beats)
                self._refresh_summary(manifest)
                manifest["finalized_signature"] = None
                manifest["finalized_validation_version"] = None
                _atomic_json(self._manifest_path(workspace), manifest)
                if chunk.get("status") != "ready":
                    break
            if all(c.get("status") == "ready" for c in (manifest.get("chunks") or [])):
                manifest["dirty_beat_ids"] = []
                manifest["selective_invalidation"] = False
                manifest["source_signature"] = self._source_signature()
                manifest["beat_signatures"] = self.snapshot_beat_signatures(workspace, beats)
            if changed or progress_status in {"completed", "failed"}:
                self._refresh_summary(manifest)
                _atomic_json(self._manifest_path(workspace), manifest)
            return manifest

    def _watch(self, job: dict[str, Any], workspace: Path, beats: list[dict[str, Any]], stop: threading.Event) -> None:
        try:
            self.prepare(job, workspace, beats)
            while not stop.is_set():
                progress = self._read_json(workspace / "edit_progress.json")
                status = str(progress.get("status") or "").lower()
                self.render_ready(job, workspace, beats, render_all=status == "completed", stop_event=stop)
                if status in {"completed", "failed"}:
                    return
                stop.wait(self.poll_interval)
        finally:
            with self._guard:
                key = str(workspace)
                current = self._threads.get(key)
                if current is threading.current_thread():
                    self._threads.pop(key, None)
                    self._stops.pop(key, None)

    def start(self, job: dict[str, Any], workspace: str | Path, beats: list[dict[str, Any]]) -> bool:
        if not self.enabled:
            return False
        workspace = Path(workspace).resolve()
        key = str(workspace)
        with self._guard:
            existing = self._threads.get(key)
            if existing is not None and existing.is_alive():
                return False
            stop = threading.Event()
            thread = threading.Thread(
                target=self._watch,
                args=(dict(job), workspace, list(beats), stop),
                name=f"cofi-render-cache-{job.get('id')}",
                daemon=True,
            )
            self._stops[key] = stop
            self._threads[key] = thread
            thread.start()
            return True

    def is_rendering(self, workspace: str | Path) -> bool:
        workspace = Path(workspace).resolve()
        key = str(workspace)
        with self._guard:
            thread = self._threads.get(key)
            if thread is not None and thread.is_alive():
                return True
            proc = self._processes.get(key)
            if proc is not None and proc.poll() is None:
                return True
        return False

    def stop(self, workspace: str | Path) -> None:
        workspace = Path(workspace).resolve()
        key = str(workspace)
        with self._guard:
            stop = self._stops.get(key)
            if stop is not None:
                stop.set()
            proc = self._processes.pop(key, None)
            if proc is not None and proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:
                    pass

    def invalidate(
        self,
        workspace: str | Path,
        *,
        beat_id: str | None = None,
        beat_ids: list[str] | tuple[str, ...] | set[str] | None = None,
        timestamp_sec: float | None = None,
    ) -> list[int]:
        workspace = Path(workspace).resolve()
        path = self._manifest_path(workspace)
        manifest = self._read_json(path)
        if not manifest:
            return []
        chunks = list(manifest.get("chunks") or [])
        explicit_beats: list[str] = []
        if beat_id and str(beat_id).strip():
            explicit_beats.append(str(beat_id).strip())
        if beat_ids:
            for item in beat_ids:
                s = str(item or "").strip()
                if s and s not in explicit_beats:
                    explicit_beats.append(s)

        current_sigs = self.snapshot_beat_signatures(workspace)
        old_sigs = manifest.get("beat_signatures") if isinstance(manifest.get("beat_signatures"), dict) else {}
        if not explicit_beats and timestamp_sec is None and old_sigs and current_sigs:
            diff_beats = [bid for bid, sig in current_sigs.items() if old_sigs.get(bid) != sig]
            if 0 < len(diff_beats) < len(current_sigs):
                explicit_beats = diff_beats

        targets: list[dict[str, Any]] = []
        if explicit_beats:
            targets = [
                chunk
                for chunk in chunks
                if any(self._chunk_matches_beat(chunk, b) for b in explicit_beats)
            ]
        elif timestamp_sec is not None:
            try:
                second = float(timestamp_sec)
            except (TypeError, ValueError):
                second = -1.0
            targets = [
                chunk
                for chunk in chunks
                if float(chunk.get("start_sec") or 0) <= second < float(chunk.get("end_sec") or 0)
            ]
            vis = self._read_json(workspace / "visual_manifest.json")
            vis_beats = [b for b in (vis.get("beats") or []) if isinstance(b, dict)]
            for timing in self._timings(workspace, vis_beats):
                if float(timing.get("start_sec") or 0) <= second < float(timing.get("end_sec") or 0):
                    bid = str(timing.get("beat_id") or "").strip()
                    if bid and bid not in explicit_beats:
                        explicit_beats.append(bid)

        is_selective = bool(targets and (explicit_beats or timestamp_sec is not None))
        if not targets:
            targets = list(chunks)

        invalidated: list[int] = []
        for chunk in targets:
            for field in ("video_path", "audio_path", "log_path"):
                try:
                    Path(str(chunk.get(field) or "")).unlink()
                except (FileNotFoundError, OSError):
                    pass
            chunk["status"] = "pending"
            chunk["rendered_at"] = None
            chunk["error"] = None
            if is_selective:
                chunk_dirty = sorted(
                    set(
                        (chunk.get("dirty_beat_ids") or [])
                        + [
                            b
                            for b in explicit_beats
                            if self._chunk_matches_beat(chunk, b) or len(chunks) == 1
                        ]
                    )
                )
                chunk["dirty_beat_ids"] = chunk_dirty
            else:
                chunk["dirty_beat_ids"] = []
            invalidated.append(int(chunk.get("index") or 0))

        manifest["source_signature"] = self._source_signature()
        if current_sigs:
            manifest["beat_signatures"] = current_sigs
        if is_selective:
            manifest["selective_invalidation"] = True
            merged_dirty = sorted(
                set((manifest.get("dirty_beat_ids") or []) + explicit_beats)
            )
            manifest["dirty_beat_ids"] = merged_dirty
            vis = self._read_json(workspace / "visual_manifest.json")
            vis_beats = [b for b in (vis.get("beats") or []) if isinstance(b, dict)]
            timings = self._timings(workspace, vis_beats) if vis_beats else []
            matched_timings = [
                t
                for t in timings
                if any(
                    self._chunk_matches_beat({"beat_ids": [t.get("beat_id")]}, b)
                    for b in merged_dirty
                )
            ]
            if matched_timings:
                manifest["last_delta_window_sec"] = {
                    "start_sec": round(min(float(t["start_sec"]) for t in matched_timings), 3),
                    "end_sec": round(max(float(t["end_sec"]) for t in matched_timings), 3),
                    "beat_ids": merged_dirty,
                }
            elif targets:
                manifest["last_delta_window_sec"] = {
                    "start_sec": round(min(float(c.get("start_sec") or 0.0) for c in targets), 3),
                    "end_sec": round(max(float(c.get("end_sec") or 0.0) for c in targets), 3),
                    "beat_ids": merged_dirty,
                }
        else:
            manifest["selective_invalidation"] = False
            manifest["dirty_beat_ids"] = []
            manifest["last_delta_window_sec"] = None
        manifest["finalized_signature"] = None
        manifest["finalized_validation_version"] = None
        self._refresh_summary(manifest)
        _atomic_json(path, manifest)
        return invalidated

    def rebuild_async(self, job: dict[str, Any], workspace: str | Path, beats: list[dict[str, Any]]) -> None:
        # Reuse the tracked watcher so repeated UI polls / edit-chat callbacks
        # cannot start multiple renderers for the same workspace.
        self.start(job, workspace, beats)

    @staticmethod
    def _chunk_signature(manifest: dict[str, Any]) -> str:
        digest = hashlib.sha256()
        for chunk in manifest.get("chunks") or []:
            for field in ("video_path", "audio_path"):
                path = Path(str(chunk.get(field) or ""))
                stat = path.stat()
                digest.update(str(path).encode("utf-8", errors="replace"))
                digest.update(str(stat.st_size).encode())
                digest.update(str(stat.st_mtime_ns).encode())
        return digest.hexdigest()

    def finalize(self, job: dict[str, Any], workspace: str | Path, beats: list[dict[str, Any]]) -> dict[str, Any]:
        workspace = Path(workspace).resolve()
        manifest = self.render_ready(job, workspace, beats, render_all=True)
        chunks = manifest.get("chunks") or []
        if not chunks or any(chunk.get("status") != "ready" for chunk in chunks):
            raise RuntimeError("Background render cache chưa thể hoàn tất tất cả chunk")
        signature = self._chunk_signature(manifest)
        output = Path(str(manifest["output_path"]))
        if (
            manifest.get("finalized_signature") == signature
            and manifest.get("finalized_validation_version") == self.FINAL_VALIDATION_VERSION
            and output.exists()
            and output.stat().st_size > 0
        ):
            return self._write_render_manifest(workspace, manifest, output, signature)
        output.parent.mkdir(parents=True, exist_ok=True)
        combine_script = self.remotion_dir / "scripts" / "combine-cofi-cache.mjs"
        if not combine_script.exists():
            raise RuntimeError(f"Thiếu script ghép render cache: {combine_script}")
        bundled_node = Path(__file__).resolve().parents[1] / "tools" / "node.exe"
        node = os.getenv("COFI_NODE_BIN") or shutil.which("node") or (str(bundled_node) if bundled_node.exists() else None)
        if not node:
            raise RuntimeError("Không tìm thấy Node để ghép background render cache")
        log_path = workspace / ".render_cache" / "combine.log"
        returncode = self._run_process(
            [str(node), str(combine_script), str(self._manifest_path(workspace))],
            self.remotion_dir,
            log_path,
            low_priority=False,
            affinity_mask=None,
            process_slot=self._processes,
            slot_key=str(workspace),
        )
        if returncode != 0 or not output.exists() or output.stat().st_size <= 0:
            raise RuntimeError(f"Ghép background render cache thất bại, code={returncode}")
        manifest["finalized_signature"] = signature
        manifest["finalized_validation_version"] = self.FINAL_VALIDATION_VERSION
        manifest["finalized_at"] = _now()
        self._refresh_summary(manifest)
        _atomic_json(self._manifest_path(workspace), manifest)
        return self._write_render_manifest(workspace, manifest, output, signature)

    def _write_render_manifest(self, workspace: Path, cache: dict[str, Any], output: Path, signature: str) -> dict[str, Any]:
        render_manifest = {
            "video_path": str(output.resolve()),
            "composition_id": cache.get("composition_id"),
            "duration_seconds": float(cache.get("duration_seconds") or 0),
            "fps": int(cache.get("fps") or 30),
            "resolution": cache.get("resolution") or {"width": 1920, "height": 1080},
            "render_mode": "background_chunk_cache",
            "cache_signature": signature,
            "cached_chunks": int(cache.get("ready_chunks") or 0),
            "total_chunks": int(cache.get("total_chunks") or 0),
            "created_at": _now(),
            "edit_usage": {},
        }
        _atomic_json(workspace / "render_manifest.json", render_manifest)
        return render_manifest

    def status(self, workspace: str | Path) -> dict[str, Any] | None:
        workspace = Path(workspace).resolve()
        manifest_path = self._manifest_path(workspace)
        manifest = self._read_json(manifest_path)
        if not manifest:
            return None
        self.hardware_profile = detect_hardware_profile()
        manifest["hardware_profile"] = self.hardware_profile
        active = self.is_rendering(workspace)
        chunks = [c for c in (manifest.get("chunks") or []) if isinstance(c, dict)]
        changed = False
        for chunk in chunks:
            if chunk.get("status") != "ready" and self._is_chunk_output_complete(chunk):
                chunk["status"] = "ready"
                chunk["rendered_at"] = chunk.get("rendered_at") or _now()
                chunk["error"] = None
                changed = True
            elif chunk.get("status") == "rendering" and not active:
                chunk["status"] = "pending"
                changed = True
        if chunks and (changed or (manifest.get("status") == "rendering" and not active)):
            self._refresh_summary(manifest)
            _atomic_json(manifest_path, manifest)
        return {
            "status": manifest.get("status"),
            "status_message": manifest.get("status_message"),
            "ready_chunks": manifest.get("ready_chunks"),
            "total_chunks": manifest.get("total_chunks"),
            "chunk_seconds": manifest.get("chunk_seconds"),
            "hardware_profile": self.hardware_profile,
            "updated_at": manifest.get("updated_at"),
        }
