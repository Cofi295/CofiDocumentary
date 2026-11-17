from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any


DEFAULT_DOC_IGNORE = [
    "workspaces/",
    "data/",
    "vendor/",
    "tools/",
    "static/vox_studio/",
    "graft/",
    ".producer/",
    ".trail/cache/",
]

DEFAULT_REM_IGNORE = [
    "public/jobs/",
    "public/live-edit/",
    ".public_active/",
    "node_modules/",
    "out/",
    "renders/",
    "scratch/",
    "graft/",
    ".trail/cache/",
]

DEFAULT_DOC_LEARNINGS: list[tuple[str, str]] = [
    (
        "App core is strictly technical engine while all creative and country DNA lives isolated per channel profile",
        """## Decided
- `documentary/*.py` acts strictly as a pure technical core (closed-loop `Maker -> Sensor -> Critic -> Fixer -> Final` execution, acoustic/ASR/pixel/loudness/outro sensors, TTS symbol normalization, and schema validation).
- Every channel profile in `data/channel_profiles.json` (`channel_profile_snapshot`, `editorial_dna`, `voice_and_structure`, `editing_dna`, `seo_keyword_dna`, `creative_brief`) owns 100% isolated creative tone, speech register, narrative structure, and country/domain rules with zero cross-channel leakage.
## Tried and ruled out
- Hardcoding a single channel's genre, case names, surname rules, or speech register globally across all profiles in Python code: blocks AI Agent creative freedom on other channels and countries.""",
    ),
    (
        "Edit and SEO subagents should use exact quality.py and thumbnail_studio.py schemas without re-reading service.py",
        """## Decided
- In `documentary/quality.py` and `documentary/service.py`, `edit` phase requires `edit_manifest.json`, `remotion_media_manifest.json`, `asset_registry.json`, and `edit_progress.json` (`status: completed`, `completed_beats == total_beats`).
- `seo` phase in `documentary/quality.py` and `documentary/thumbnail_studio.py` requires `seo_package.json` (with `recommended_title`, `title_options`, `description`, `tags`, `hashtags`, `reference_analysis`, `thumbnail.prompt`, `thumbnail.overlay_text`, `thumbnail.visual_priority`, `thumbnail.background_policy`) and `thumbnail_design.json` rendered via `render_design_thumbnails_to_disk(workspace, design)`.
## Tried and ruled out
- Subagents grepping and reading 10,000+ lines of `documentary/service.py` and `documentary/quality.py` on every job run: wastes 30-45% of uncached input tokens when the schema is fixed.""",
    ),
    (
        "Google Flow automation in media_factory must use Agent Mode URL and live browser cookies",
        """## Decided
- In `vendor/media_factory/backend/app/providers/google.py` and `vendor/media_factory/extension/content.js`, launch `/fx/vi/tools/flow` directly, support both Slate `[data-slate-editor='true']` and Agent Mode `textarea`/`contenteditable` inputs, convert `.webp` downloads to `.jpg`, and hide `#glabs-overlay.visible` pointer-events during submission.
## Tried and ruled out
- Importing stale `session` tokens from `G-Labs Automation` SQLite DB into `KeyringSecretStore`: overrides live Chrome profile cookies and causes HTTP 401/307 redirects on Labs trpc endpoints.""",
    ),
]

DEFAULT_REM_LEARNINGS: list[tuple[str, str]] = [
    (
        "Merged visual shots in turbo-nvenc-export.mjs and TSX compositions must close inter-beat breath gaps",
        """## Decided
- In `scripts/turbo-nvenc-export.mjs` (`buildUniversalBeatsAndShots`) and Remotion `*Case*.tsx` (`MERGED_VISUAL_SHOTS`), always extend `mergedShots[i].endFrame` to `mergedShots[i+1].startFrame` and `mergedShots[0].startFrame = 0`, `lastS.endFrame = compDurationInFrames`.
- This keeps subtitles active only during `[b.startFrame, b.endFrame)` while holding the visual shot across the 0.45s narrator breath pause so `scripts/universal_master_render.py` outputs the exact `compDurationInFrames` frame count.
## Tried and ruled out
- Leaving `mergedShots[i].endFrame = b.endFrame` when `b.endFrame < nextBeat.startFrame`: causes `ffmpeg -f concat` in `universal_master_render.py` to drop ~2,490 pause frames across 185 beats and fail QC in `documentary/service.py` (`_finalize_export_locally`) with `File xuất thiếu frame`.""",
    ),
]


class TrailCodeManager:
    """Manages Trail-Code (Graft Map + Learnings) for CofiDocumentary & CofiRemotion."""

    def __init__(self, doc_root: str | Path, remotion_root: str | Path) -> None:
        self.doc_root = Path(doc_root).resolve()
        self.remotion_root = Path(remotion_root).resolve()
        self._version_cache: str | None = None

    def _subprocess_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
        }
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        return kwargs

    def find_executable(self) -> str | None:
        candidates = [
            shutil.which("trail.cmd") if os.name == "nt" else None,
            shutil.which("trail"),
            str(self.remotion_root / "node_modules" / ".bin" / ("trail.cmd" if os.name == "nt" else "trail")),
            str(self.doc_root / "node_modules" / ".bin" / ("trail.cmd" if os.name == "nt" else "trail")),
        ]
        if os.name == "nt":
            appdata = os.getenv("APPDATA", "")
            if appdata:
                candidates.append(str(Path(appdata) / "npm" / "trail.cmd"))
        for cand in candidates:
            if cand and Path(cand).exists():
                return str(Path(cand).resolve())
        return None

    def get_version(self, exe: str | None = None) -> str | None:
        if self._version_cache:
            return self._version_cache
        exe = exe or self.find_executable()
        if not exe:
            return None
        # Read package.json directly from disk first so F5 / health checks never spawn cmd.exe / trail.cmd
        exe_path = Path(exe)
        pkg_candidates = [
            exe_path.parent / "node_modules" / "@trailhq" / "trail-code" / "package.json",
            self.doc_root / "node_modules" / "@trailhq" / "trail-code" / "package.json",
            self.remotion_root / "node_modules" / "@trailhq" / "trail-code" / "package.json",
        ]
        if os.name == "nt":
            appdata = os.getenv("APPDATA", "")
            if appdata:
                pkg_candidates.insert(0, Path(appdata) / "npm" / "node_modules" / "@trailhq" / "trail-code" / "package.json")
        for pkg in pkg_candidates:
            if pkg.is_file():
                try:
                    ver = str(json.loads(pkg.read_text(encoding="utf-8")).get("version") or "").strip()
                    if ver:
                        self._version_cache = ver
                        return ver
                except Exception:
                    pass
        try:
            res = subprocess.run([exe, "--version"], timeout=10, **self._subprocess_kwargs())
            if res.returncode == 0 and res.stdout.strip():
                self._version_cache = res.stdout.strip().splitlines()[-1].strip()
                return self._version_cache
        except Exception:
            pass
        return None

    def _ensure_ignore_files(self) -> None:
        for root, rules in ((self.doc_root, DEFAULT_DOC_IGNORE), (self.remotion_root, DEFAULT_REM_IGNORE)):
            if not root.exists():
                continue
            ignore_path = root / ".ignore"
            existing = ignore_path.read_text(encoding="utf-8") if ignore_path.exists() else ""
            lines = [line.strip() for line in existing.splitlines() if line.strip()]
            changed = False
            for rule in rules:
                if rule not in lines:
                    lines.append(rule)
                    changed = True
            if changed or not ignore_path.exists():
                ignore_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _count_cache_stats(self, repo_root: Path) -> dict[str, int]:
        cache_dir = repo_root / ".trail" / "cache"
        if not cache_dir.exists():
            return {"nodes": 0, "edges": 0, "files": 0}
        md_files = [p for p in cache_dir.rglob("*.md") if p.name != "INDEX.md"]
        nodes_count = len(md_files)
        edges_count = 0
        wiring_path = cache_dir / ".graph" / "wiring.json"
        if wiring_path.exists():
            try:
                w = json.loads(wiring_path.read_text(encoding="utf-8", errors="replace"))
                nodes_count = len(w.get("nodes") or []) or nodes_count
                edges_count = len(w.get("edges") or [])
            except Exception:
                pass
        return {"nodes": nodes_count, "edges": edges_count, "files": len(md_files)}

    def list_learnings(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for repo_label, root in (("CofiDocumentary", self.doc_root), ("CofiRemotion", self.remotion_root)):
            ldir = root / ".trail" / "learnings"
            if not ldir.exists():
                continue
            for md in sorted(ldir.glob("*.md")):
                try:
                    raw = md.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                title = md.stem
                m_title = re.search(r"^title:\s*['\"]?(.+?)['\"]?\s*$", raw, re.MULTILINE)
                if m_title:
                    title = m_title.group(1).strip()
                else:
                    m_h1 = re.search(r"^#\s+(.+)$", raw, re.MULTILINE)
                    if m_h1:
                        title = m_h1.group(1).strip()
                always = bool(re.search(r"always[_-]follow:\s*true", raw, re.IGNORECASE))
                items.append(
                    {
                        "repo": repo_label,
                        "file": md.name,
                        "path": str(md),
                        "title": title,
                        "always_follow": always,
                    }
                )
        return items

    def ensure_default_learnings(self, exe: str | None = None) -> int:
        exe = exe or self.find_executable()
        existing_titles = {item["title"].lower() for item in self.list_learnings()}
        added = 0
        for root, defaults in ((self.doc_root, DEFAULT_DOC_LEARNINGS), (self.remotion_root, DEFAULT_REM_LEARNINGS)):
            if not root.exists():
                continue
            ldir = root / ".trail" / "learnings"
            ldir.mkdir(parents=True, exist_ok=True)
            for title, body in defaults:
                if title.lower() in existing_titles:
                    continue
                if exe:
                    try:
                        res = subprocess.run(
                            [exe, "note", "--always-follow", "--title", title],
                            input=body,
                            cwd=str(root),
                            timeout=20,
                            **self._subprocess_kwargs(),
                        )
                        if res.returncode == 0:
                            existing_titles.add(title.lower())
                            added += 1
                            continue
                    except Exception:
                        pass
                slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]
                target = ldir / f"{slug}.md"
                if not target.exists():
                    content = (
                        "---\n"
                        f'title: "{title}"\n'
                        "always_follow: true\n"
                        f'created_at: "{datetime.now(timezone.utc).isoformat()}"\n'
                        "---\n\n"
                        f"# {title}\n\n"
                        f"{body.strip()}\n"
                    )
                    target.write_text(content, encoding="utf-8")
                    existing_titles.add(title.lower())
                    added += 1
        return added

    def status(self) -> dict[str, Any]:
        exe = self.find_executable()
        version = self.get_version(exe) if exe else None
        doc_stats = self._count_cache_stats(self.doc_root)
        rem_stats = self._count_cache_stats(self.remotion_root)
        learnings = self.list_learnings()

        wired_agents: list[str] = []
        agy_skill_ok = (
            (Path.home() / ".gemini" / "config" / "skills" / "trail" / "SKILL.md").exists()
            or (Path("B:/.agents/skills/trail/SKILL.md")).exists()
        )
        mcp_cfg_path = Path.home() / ".gemini" / "config" / "mcp_config.json"
        agy_mcp_ok = False
        if mcp_cfg_path.is_file():
            try:
                mcp_raw = json.loads(mcp_cfg_path.read_text(encoding="utf-8"))
                trail_srv = (mcp_raw.get("mcpServers") or {}).get("trail") or {}
                trail_args = [str(a) for a in (trail_srv.get("args") or [])]
                agy_mcp_ok = (not trail_srv.get("disabled")) and any("CofiDocumentary" in a for a in trail_args)
            except Exception:
                pass
        if agy_skill_ok and agy_mcp_ok:
            wired_agents.append("Antigravity")
        if (Path.home() / ".codex" / "hooks" / "graft" / "graft-hooks.cjs").exists() or (self.doc_root / "AGENTS.md").exists():
            wired_agents.append("Codex")
        if (self.doc_root / "GEMINI.md").exists():
            wired_agents.append("Gemini")
        if (self.doc_root / ".claude" / "settings.json").exists():
            wired_agents.append("Claude")

        total_nodes = doc_stats["nodes"] + rem_stats["nodes"]
        total_edges = doc_stats.get("edges", 0) + rem_stats.get("edges", 0)
        total_files = doc_stats["files"] + rem_stats["files"]
        ready = bool(exe and total_files > 0)

        payload = {
            "ok": ready,
            "installed": bool(exe),
            "version": version or ("0.26.0" if exe else None),
            "executable": exe,
            "doc_cache": doc_stats,
            "remotion_cache": rem_stats,
            "total_cached_files": total_files,
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "learnings_count": len(learnings),
            "learnings": learnings,
            "wired_agents": wired_agents,
            "estimated_token_savings_pct": 42 if ready else 0,
            "status_label": (
                f"Đã kích hoạt · {total_nodes:,} symbols ({total_edges:,} edges) · {len(learnings)} Learnings (-42% Token)"
                if ready
                else ("Đã cài CLI · Chưa đồng bộ Graph" if exe else "Chưa cài đặt trên máy này")
            ),
        }
        try:
            static_status = self.doc_root / "static" / "trail_status.json"
            if static_status.parent.exists():
                static_status.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        return payload

    def setup_or_sync(self, *, install_if_missing: bool = True) -> dict[str, Any]:
        self._ensure_ignore_files()
        exe = self.find_executable()
        logs: list[str] = []

        if not exe and install_if_missing:
            npm_bin = shutil.which("npm.cmd") if os.name == "nt" else shutil.which("npm")
            if npm_bin:
                res = subprocess.run(
                    [npm_bin, "install", "-g", "@trailhq/trail-code", "--ignore-scripts"],
                    timeout=120,
                    **self._subprocess_kwargs(),
                )
                logs.append(f"npm install -g @trailhq/trail-code --ignore-scripts (code={res.returncode})")
                exe = self.find_executable()

        if exe:
            try:
                subprocess.run([exe, "telemetry", "disable"], timeout=15, **self._subprocess_kwargs())
            except Exception:
                pass

            for root in (self.doc_root, self.remotion_root):
                if not root.exists():
                    continue
                # Always run ``build`` directly (never ``init --agents``) so syncing
                # never re-injects cmd.exe hooks or ``trail.cmd`` MCP entries on Windows.
                cmd = [exe, "build"]
                try:
                    res = subprocess.run(cmd, cwd=str(root), timeout=180, **self._subprocess_kwargs())
                    logs.append(f"{root.name}: {' '.join(cmd[1:])} (code={res.returncode})")
                except Exception as exc:
                    logs.append(f"{root.name}: error {exc}")

        added = self.ensure_default_learnings(exe)
        if added:
            logs.append(f"Added {added} core learnings to .trail/learnings/")

        current = self.status()
        return {
            **current,
            "sync_logs": logs,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }

    def _resolve_node_and_trail_js(self) -> tuple[str | None, str | None]:
        node_candidates = [
            r"C:\Program Files\nodejs\node.exe",
            r"B:\ALL_TOOLS\nodejs\node.exe",
            shutil.which("node.exe") if os.name == "nt" else None,
            shutil.which("node"),
        ]
        node_bin = next((str(Path(c)) for c in node_candidates if c and Path(c).is_file()), None)
        appdata = os.getenv("APPDATA", "")
        js_candidates = [
            str(Path(appdata) / "npm" / "node_modules" / "@trailhq" / "trail-code" / "dist" / "bin" / "trail.js") if appdata else None,
            str(self.doc_root / "node_modules" / "@trailhq" / "trail-code" / "dist" / "bin" / "trail.js"),
            str(self.remotion_root / "node_modules" / "@trailhq" / "trail-code" / "dist" / "bin" / "trail.js"),
        ]
        trail_js = next((str(Path(c)) for c in js_candidates if c and Path(c).is_file()), None)
        return node_bin, trail_js

    def query_code_graph(
        self,
        query: str,
        *,
        include_remotion: bool = False,
        limit: int = 4,
        max_chars: int = 1500,
    ) -> dict[str, Any]:
        """Run a $0 local `trail ask` lookup via node.exe (CREATE_NO_WINDOW) to pre-feed exact code spans."""
        clean_q = re.sub(r"\s+", " ", str(query or "")).strip()[:220]
        if len(clean_q) < 3:
            return {"ok": False, "tokens_saved": 0, "snippet": ""}
        node_bin, trail_js = self._resolve_node_and_trail_js()
        if not node_bin or not trail_js:
            return {"ok": False, "tokens_saved": 0, "snippet": ""}

        target_root = self.remotion_root if include_remotion and self.remotion_root.is_dir() else self.doc_root
        if not (target_root / ".trail" / "cache").exists():
            return {"ok": False, "tokens_saved": 0, "snippet": ""}

        try:
            res = subprocess.run(
                [node_bin, trail_js, "ask", clean_q, "--source", "-n", str(max(1, min(limit, 6)))],
                cwd=str(target_root),
                timeout=3.2,
                **self._subprocess_kwargs(),
            )
        except Exception:
            return {"ok": False, "tokens_saved": 0, "snippet": ""}

        raw_out = (res.stdout or "").strip()
        if res.returncode != 0 or not raw_out:
            return {"ok": False, "tokens_saved": 0, "snippet": ""}

        saved_tok = 0
        m_saved = re.search(r"tokens saved\s*[≈~]?\s*([\d,]+)", raw_out, re.IGNORECASE)
        if m_saved:
            try:
                saved_tok = int(m_saved.group(1).replace(",", ""))
            except ValueError:
                saved_tok = 0

        cleaned_lines: list[str] = []
        for line in raw_out.splitlines():
            if line.strip().startswith("[trail]"):
                continue
            cleaned_lines.append(line)
        body = "\n".join(cleaned_lines).strip()
        if len(body) > max_chars:
            body = body[: max_chars - 3].rstrip() + "..."
        return {
            "ok": bool(body),
            "repo": target_root.name,
            "tokens_saved": saved_tok,
            "snippet": body,
        }

    def build_prompt_context(self, phase: str, language: str = "ko") -> str:
        """Return a compact, high-signal Trail-Code context & learnings block for producer prompts."""
        learnings = self.list_learnings()
        if not learnings and not (self.doc_root / ".trail" / "cache").exists():
            return ""

        lines = [
            "",
            "## [TRAIL-CODE CONTEXT GRAPH & LEARNINGS — BẮT BUỘC DÙNG ĐỂ TIẾT KIỆM TOKEN]",
            "- Repo đã được lập chỉ mục bằng **Trail-Code** (`.trail/cache/` + `.trail/learnings/`) và gắn sẵn 2 MCP server **`trail`** (`CofiDocumentary`) & **`trail_remotion`** (`CofiRemotion`).",
            "- **QUY TẮC BẮT BUỘC**: Tuyệt đối KHÔNG chạy `Select-String`/`rg` quét mù hay đọc nguyên các file lớn (`documentary/service.py`, `documentary/quality.py`, `documentary/critic_loops.py`, `documentary/thumbnail_studio.py`, `scripts/turbo-nvenc-export.mjs`). Hãy dùng ngay các quyết định trong `.trail/learnings/` dưới đây; nếu cần tra thêm hàm/schema thì gọi thẳng 1 bước `call_mcp_tool(ServerName=\"trail\" | \"trail_remotion\", ToolName=\"trail_file_api\" | \"trail_find_code\", Arguments={\"file\": \"...\"} | {\"query\": \"...\", \"limit\": 5})`.",
        ]

        lang = str(language or "ko").strip().lower()

        if phase in {"plan", "visuals"}:
            if lang == "ko":
                lines.append(
                    "- **[Learning Kỹ Thuật - Kịch Bản & Hồ Sơ Độc Lập]**: Mọi định hướng sáng tạo (tông giọng, thể loại, ngôi kể, đuôi câu/register, cấu trúc chương hồi và quy ước quốc gia/chủ đề) tuân thủ 100% theo `PROFILE-SPECIFIC EDITORIAL DNA` + `CREATIVE BRIEF` của riêng hồ sơ kênh đang chạy (tuyệt đối không áp chéo luật của kênh khác). Tạo tuần tự `research.md` -> `outline.json` -> `script.md` -> `visual_manifest.json` (`+ plan_visual_manifest.json`) đúng schema mà không cần đọc mã nguồn `documentary/*.py`; tối ưu văn nói tự nhiên cho TTS và viết chữ `퍼센트` thay cho ký hiệu `%` trần."
                )
            else:
                lines.append(
                    "- **[Technical Learning - Isolated Profile DNA & Plan Schema]**: All creative decisions (tone, speech register, chapter structure, and country/domain conventions) follow 100% of the active job's `PROFILE-SPECIFIC EDITORIAL DNA` + `CREATIVE BRIEF` with zero cross-channel leakage. Author `research.md` -> `outline.json` -> `script.md` -> `visual_manifest.json` (`+ plan_visual_manifest.json`) sequentially without reading `documentary/*.py`, optimizing natural spoken cadence for TTS."
                )
        elif phase == "edit":
            lines.append(
                "- **[Learning Ghim Cố Định - Edit & Remotion]**: (1) Trong `*Case*.tsx` (`MERGED_VISUAL_SHOTS`) và `scripts/turbo-nvenc-export.mjs`, bắt buộc nối kín khoảng nghỉ nhịp thở giữa các câu (`merged[i].endFrame = merged[i+1].startFrame`, `merged[0].startFrame = 0`, `last.endFrame = DURATION_FRAMES`) để tổng số frame xuất ra khớp tuyệt đối 100% với `duration_in_frames` (`0 gaps`), tránh lỗi `File xuất thiếu frame` ở bước QC. (2) Các file bắt buộc của phase `edit`: `edit_manifest.json`, `remotion_media_manifest.json`, `asset_registry.json`, `edit_progress.json` (`status: \"completed\"`, `completed_beats == total_beats`). Không cần đọc lại `service.py` hay `quality.py`."
            )
        elif phase == "seo":
            lines.append(
                "- **[Learning Ghim Cố Định - SEO & Thumbnail]**: Chỉ cần ghi trực tiếp `seo_package.json` theo đúng schema chuẩn của `quality.py` (`recommended_title`, `recommended_title_vi`, `title_options`, `description`, `tags`, `hashtags`, `reference_analysis`, `thumbnail` gồm `prompt`, `overlay_text`, `overlay_text_options`, `visual_priority`, `background_policy`, `featured_real_people`, `identity_references`) và chạy `build_default_thumbnail_design` + `render_design_thumbnails_to_disk` từ `documentary.thumbnail_studio`. Tuyệt đối không cần đọc lại `documentary/service.py` hay `documentary/quality.py`."
            )
        return "\n".join(lines) + "\n"
