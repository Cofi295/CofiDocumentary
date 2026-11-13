from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import tomllib
from typing import Callable

from .prompts import build_phase_prompt
from .render_cache import (
    apply_background_worker_qos,
    background_worker_creationflags,
    background_worker_env_overrides,
)
from .source_discovery import scrub_source_secret_env


@dataclass(frozen=True)
class StageResult:
    returncode: int
    last_message: str
    log_path: Path


class CodexGateway:
    MAX_PERSISTED_EVENT_DATA_CHARS = 4096
    SHARED_SESSION_LABEL = "_codex_web_shared"
    DEFAULT_SESSION_MAX_TURNS = 0
    DEFAULT_SESSION_MAX_PROMPT_CHARS = 450_000
    DEFAULT_SAME_SESSION_TRANSIENT_RETRIES = 1
    DEFAULT_MIN_TURN_GAP_SECONDS = 2
    HANDOFF_MAX_CHARS = 12_000
    HANDOFF_PROMPT = (
        "Bạn sắp kết thúc conversation ChatGPT hiện tại để tiếp tục công việc trong một conversation mới. "
        "Hãy trả về một bản handoff NGẮN GỌN, tự đủ ngữ cảnh cho Codex tiếp tục ngay. Chỉ giữ: "
        "mục tiêu đang làm, phần đã hoàn thành, quyết định/constraint quan trọng, file hoặc artifact đã tạo/sửa, "
        "lỗi còn tồn tại, checkpoint hiện tại và bước tiếp theo chính xác. Không chép log dài, không giải thích lan man."
    )
    CONTEXT_LIMIT_MARKERS = (
        "context window",
        "context length",
        "maximum context",
        "max context",
        "conversation too long",
        "too many tokens",
        "token limit",
        "context limit",
        "encoded request body exceeds",
        "request body exceeds",
    )
    BROKEN_RESUME_CONTEXT_MARKERS = (
        "missing cwd in trusted codex environment context",
        "chatgpt browser tab was closed",
        "chatgpt web turn aborted",
        "chatgpt did not confirm that the prompt was sent",
        "no rollout found for thread id",
        "retained chatgpt conversation is no longer available",
        "retained conversation unavailable",
        "compaction_source_unavailable",
    )
    TRANSIENT_FAILURE_MARKERS = (
        "3221225794",
        "0xc0000142",
        "dll initialization failed",
        "connection",
        "disconnected",
        "network",
        "transport",
        "timeout",
        "timed out",
        "socket",
        "connection reset",
        "stream closed",
        "stream disconnected",
        "unexpected eof",
        "broken pipe",
        "temporarily unavailable",
        "did not accept all prompt attachments",
        "browser stage timed out",
    )

    def __init__(
        self,
        remotion_dir: str | Path,
        executable: str | None = None,
        session_root: str | Path | None = None,
    ):
        self.remotion_dir = Path(remotion_dir).resolve()
        self.executable = executable or os.getenv("COFI_CODEX_BIN") or shutil.which("codex") or "codex"
        self.project_dir = Path(__file__).resolve().parents[1]
        self.session_root = Path(session_root).resolve() if session_root is not None else None
        self.tools_dir = self.project_dir / "tools"
        self._session_locks_guard = threading.RLock()
        self._session_locks: dict[tuple[str, str], threading.RLock] = {}
        self._reusable_switch_lock = threading.RLock()
        self._web_turn_lock = threading.RLock()
        self._last_web_turn_finished_at = 0.0

    def _subprocess_env(self) -> dict[str, str]:
        env = scrub_source_secret_env(os.environ.copy())
        current_path = env.get("PATH", "")
        env["PATH"] = str(self.tools_dir) + (os.pathsep + current_path if current_path else "")
        env["COFI_MEDIA_TOOLS_DIR"] = str(self.tools_dir)
        env["COFI_YTDLP_BIN"] = str(self.tools_dir / "yt-dlp.exe")
        env["COFI_FFMPEG_BIN"] = str(self.tools_dir / "ffmpeg.exe")
        env["COFI_FFPROBE_BIN"] = str(self.tools_dir / "ffprobe.exe")
        env["COFI_NODE_BIN"] = str(self.tools_dir / "node.exe")
        try:
            for k, v in background_worker_env_overrides().items():
                env.setdefault(k, v)
        except Exception:
            pass
        return env

    def _transport_config_args(self) -> list[str]:
        """Use the user's ChatGPT bridge with transport retries disabled."""
        configured = os.getenv("COFI_CODEX_BASE_URL", "").strip()
        if not configured:
            config_path = Path.home() / ".codex" / "config.toml"
            try:
                payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
            except (OSError, tomllib.TOMLDecodeError):
                payload = {}
            configured = str(payload.get("openai_base_url") or "").strip()
        if not configured:
            return []
        provider = (
            'model_providers.cofi_chatgpt_web={name="COFI ChatGPT Web",'
            f'base_url="{configured}",wire_api="responses",request_max_retries=0,'
            'stream_max_retries=0,requires_openai_auth=true}'
        )
        return ["-c", 'model_provider="cofi_chatgpt_web"', "-c", provider]

    @property
    def available(self) -> bool:
        return bool(shutil.which(self.executable) or Path(str(self.executable)).exists())

    def command_for(
        self,
        phase: str,
        workspace: str | Path,
        image_paths: list[str | Path] | None = None,
    ) -> list[str]:
        workspace = Path(workspace).resolve()
        command = [
            self.executable,
            "--search",
            "--dangerously-bypass-approvals-and-sandbox",
        ]
        command += self._transport_config_args()
        command += ["exec", "--json", "--skip-git-repo-check"]
        if phase in {"edit", "qc"}:
            command += ["-C", str(self.remotion_dir), "--add-dir", str(workspace)]
        else:
            command += ["-C", str(workspace)]
        for image_path in image_paths or []:
            command += ["-i", str(Path(image_path).resolve())]
        return command

    def run(
        self,
        job: dict,
        phase: str,
        workspace: str | Path,
        log_callback: Callable[[str], None] | None = None,
    ) -> StageResult:
        prompt = build_phase_prompt(job, phase, workspace, self.remotion_dir)
        return self.run_prompt_reusable(
            prompt,
            workspace,
            phase,
            log_callback=log_callback,
            use_remotion_root=phase in {"edit", "qc"},
        )

    def _reusable_session_root(self, workspace: str | Path) -> Path:
        return self.session_root or Path(workspace).resolve()

    def _reusable_session_meta_dir(self, workspace: str | Path) -> Path:
        return self._reusable_session_root(workspace) / ".producer" / self.SHARED_SESSION_LABEL

    def _load_or_migrate_reusable_session(self, workspace: Path, session_meta_dir: Path) -> dict:
        session_path = session_meta_dir / "session.json"
        session = self._load_session(session_path)
        if session:
            return session

        root = self._reusable_session_root(workspace)
        candidates: list[tuple[str, float, Path, dict]] = []
        paths: list[Path] = []
        try:
            paths.extend((root / ".producer").glob("*/session.json"))
            paths.extend((root / "workspaces").glob("*/.producer/*/session.json"))
        except OSError:
            paths = []
        for path in paths:
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if resolved == session_path.resolve() or ".producer" not in resolved.parts:
                continue
            payload = self._load_session(resolved)
            if not str(payload.get("thread_id") or "").strip():
                continue
            try:
                modified = resolved.stat().st_mtime
            except OSError:
                modified = 0.0
            candidates.append((str(payload.get("last_used_at") or ""), modified, resolved, payload))
        if not candidates:
            return {}

        _last_used, _modified, source_path, payload = max(candidates, key=lambda item: (item[0], item[1]))
        migrated = {**payload, "migrated_from": str(source_path)}
        session_meta_dir.mkdir(parents=True, exist_ok=True)
        session_path.write_text(json.dumps(migrated, ensure_ascii=False, indent=2), encoding="utf-8")
        migrated_at = datetime.now(timezone.utc).isoformat()
        with (session_meta_dir / "legacy_sessions.jsonl").open("a", encoding="utf-8") as handle:
            for _last_used_at, _mtime, legacy_path, legacy_payload in candidates:
                handle.write(json.dumps({
                    **legacy_payload,
                    "legacy_path": str(legacy_path),
                    "migrated_at": migrated_at,
                    "selected_for_shared_session": legacy_path == source_path,
                }, ensure_ascii=False) + "\n")
        for _last_used_at, _mtime, legacy_path, _legacy_payload in candidates:
            try:
                legacy_path.unlink(missing_ok=True)
            except OSError:
                pass
        return migrated

    def run_prompt(
        self,
        prompt: str,
        workspace: str | Path,
        label: str,
        log_callback: Callable[[str], None] | None = None,
        use_remotion_root: bool = False,
        reuse_session: bool = False,
        image_paths: list[str | Path] | None = None,
    ) -> StageResult:
        workspace = Path(workspace).resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        meta_dir = workspace / ".producer" / label
        meta_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = meta_dir / "prompt.txt"
        log_path = meta_dir / "events.jsonl"
        last_path = meta_dir / "last_message.txt"
        session_meta_dir = self._reusable_session_meta_dir(workspace) if reuse_session else meta_dir
        session_meta_dir.mkdir(parents=True, exist_ok=True)
        session_path = session_meta_dir / "session.json"
        session = self._load_or_migrate_reusable_session(workspace, session_meta_dir) if reuse_session else None
        auth_fingerprint = self._codex_auth_fingerprint() if reuse_session else None
        suppress_saved_handoff = False
        if (
            reuse_session
            and session
            and auth_fingerprint
            and session.get("auth_fingerprint")
            and str(session.get("auth_fingerprint")) != auth_fingerprint
        ):
            self._retire_session(session_meta_dir, session, "codex_account_changed")
            session = None
            suppress_saved_handoff = True
        if reuse_session and session and self._should_rotate_proactively(session, prompt):
            handoff = self._handoff_session(
                session_meta_dir,
                session,
                reason="proactive_context_guard",
                fallback_workspace=workspace,
                fallback_label=label,
                use_remotion_root=use_remotion_root,
            )
            session = None
            if handoff:
                prompt = self._prepend_handoff(prompt, handoff)
        elif reuse_session and not session and not suppress_saved_handoff:
            handoff = self._read_handoff_summary(session_meta_dir)
            if handoff:
                prompt = self._prepend_handoff(prompt, handoff)

        prompt_path.write_text(prompt, encoding="utf-8")
        execute_kwargs = {
            "log_callback": log_callback,
            "use_remotion_root": use_remotion_root,
            "thread_id": str(session.get("thread_id")) if session and session.get("thread_id") else None,
            "append_log": reuse_session,
        }
        if image_paths:
            execute_kwargs["image_paths"] = image_paths
        result, thread_id, output_text = self._execute_prompt_queued(
            prompt,
            workspace,
            log_path,
            last_path,
            **execute_kwargs,
        )

        broken_resume_context = bool(
            reuse_session
            and session
            and result.returncode != 0
            and self._is_broken_resume_context_failure(output_text, result.last_message)
        )
        context_limit = bool(
            reuse_session
            and session
            and result.returncode != 0
            and self._is_context_limit_failure(output_text, result.last_message)
        )
        if broken_resume_context or context_limit:
            handoff = self._fallback_handoff_summary(session_meta_dir, fallback_meta_dir=meta_dir)
            self._retire_session(
                session_meta_dir,
                session,
                "broken_resume_environment_context" if broken_resume_context else "context_limit",
            )
            retry_prompt = self._prepend_handoff(prompt, handoff) if handoff else prompt
            prompt_path.write_text(retry_prompt, encoding="utf-8")
            retry_kwargs = {
                "log_callback": log_callback,
                "use_remotion_root": use_remotion_root,
                "thread_id": None,
                "append_log": True,
            }
            if image_paths:
                retry_kwargs["image_paths"] = image_paths
            result, thread_id, output_text = self._execute_prompt_queued(
                retry_prompt,
                workspace,
                log_path,
                last_path,
                **retry_kwargs,
            )
            session = None
            prompt = retry_prompt

        if reuse_session and result.returncode == 0:
            active_thread_id = thread_id or (str(session.get("thread_id")) if session and session.get("thread_id") else None)
            if active_thread_id:
                now = datetime.now(timezone.utc).isoformat()
                payload = {
                    "thread_id": active_thread_id,
                    "created_at": (session or {}).get("created_at") or now,
                    "last_used_at": now,
                    "turn_count": int((session or {}).get("turn_count") or 0) + 1,
                    "prompt_chars_total": int((session or {}).get("prompt_chars_total") or 0) + len(prompt),
                    "last_workspace": str(workspace),
                    "last_label": str(label),
                    "last_use_remotion_root": bool(use_remotion_root),
                }
                persisted_auth_fingerprint = auth_fingerprint or (session or {}).get("auth_fingerprint")
                if persisted_auth_fingerprint:
                    payload["auth_fingerprint"] = persisted_auth_fingerprint
                session_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        elif reuse_session and result.returncode != 0 and thread_id and self._is_transient_result(result, output_text):
            # A browser/stream interruption can happen after ChatGPT has already
            # created the thread. Keep that observed thread id so the immediate
            # retry can resume the same conversation instead of opening a new one.
            now = datetime.now(timezone.utc).isoformat()
            payload = {
                "thread_id": str(thread_id),
                "created_at": (session or {}).get("created_at") or now,
                "last_used_at": (session or {}).get("last_used_at") or now,
                "turn_count": int((session or {}).get("turn_count") or 0),
                "prompt_chars_total": int((session or {}).get("prompt_chars_total") or 0),
                "last_failure_at": now,
                "failure_count": int((session or {}).get("failure_count") or 0) + 1,
                "last_workspace": str(workspace),
                "last_label": str(label),
                "last_use_remotion_root": bool(use_remotion_root),
            }
            persisted_auth_fingerprint = auth_fingerprint or (session or {}).get("auth_fingerprint")
            if persisted_auth_fingerprint:
                payload["auth_fingerprint"] = persisted_auth_fingerprint
            session_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    def run_prompt_reusable(
        self,
        prompt: str,
        workspace: str | Path,
        label: str,
        log_callback: Callable[[str], None] | None = None,
        use_remotion_root: bool = False,
        image_paths: list[str | Path] | None = None,
    ) -> StageResult:
        workspace_path = Path(workspace).resolve()
        session_meta_dir = self._reusable_session_meta_dir(workspace_path)
        key = (str(session_meta_dir), self.SHARED_SESSION_LABEL)
        with self._reusable_switch_lock:
            with self._session_locks_guard:
                session_lock = self._session_locks.setdefault(key, threading.RLock())
            with session_lock:
                try:
                    transient_retries = max(
                        0,
                        int(
                            os.getenv(
                                "COFI_CODEX_SAME_SESSION_RETRIES",
                                str(self.DEFAULT_SAME_SESSION_TRANSIENT_RETRIES),
                            )
                        ),
                    )
                except (TypeError, ValueError):
                    transient_retries = self.DEFAULT_SAME_SESSION_TRANSIENT_RETRIES

                result: StageResult | None = None
                for attempt in range(transient_retries + 1):
                    kwargs = {
                        "log_callback": log_callback,
                        "use_remotion_root": use_remotion_root,
                        "reuse_session": True,
                    }
                    if image_paths:
                        kwargs["image_paths"] = image_paths
                    result = self.run_prompt(prompt, workspace_path, label, **kwargs)
                    if result.returncode == 0 or not self._is_transient_result(result):
                        return result
                    if attempt >= transient_retries:
                        return result
                return result or StageResult(1, "Codex reusable prompt failed", workspace_path / ".producer" / label)

    def reset_reusable_session(self, workspace: str | Path, label: str, reason: str = "manual_reset") -> bool:
        """Retire the active reusable Codex session so the next prompt starts fresh."""
        workspace = Path(workspace).resolve()
        meta_dir = self._reusable_session_meta_dir(workspace)
        session_path = meta_dir / "session.json"
        session = self._load_or_migrate_reusable_session(workspace, meta_dir)
        if not session:
            if session_path.exists():
                session_path.unlink()
            return False
        meta_dir.mkdir(parents=True, exist_ok=True)
        self._retire_session(meta_dir, session, reason)
        return True

    @staticmethod
    def _load_session(path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _codex_auth_fingerprint() -> str | None:
        """Return a non-secret fingerprint for the account used by the local Codex CLI."""
        configured_home = os.getenv("CODEX_HOME", "").strip()
        codex_home = Path(configured_home).expanduser() if configured_home else Path.home() / ".codex"
        auth_path = codex_home / "auth.json"
        try:
            payload = json.loads(auth_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None

        tokens = payload.get("tokens")
        account_id = str(tokens.get("account_id") or "").strip() if isinstance(tokens, dict) else ""
        identity = account_id
        if not identity:
            api_key = payload.get("OPENAI_API_KEY")
            identity = str(api_key or "").strip()
        if not identity:
            return None

        auth_mode = str(payload.get("auth_mode") or "").strip()
        return hashlib.sha256(f"{auth_mode}\0{identity}".encode("utf-8")).hexdigest()

    @staticmethod
    def _retire_session(meta_dir: Path, session: dict, reason: str) -> None:
        payload = {
            **session,
            "retired_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
        }
        with (meta_dir / "retired_sessions.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        session_path = meta_dir / "session.json"
        if session_path.exists():
            session_path.unlink()

    @classmethod
    def _trim_handoff(cls, value: str) -> str:
        text = str(value or "").strip()
        if len(text) <= cls.HANDOFF_MAX_CHARS:
            return text
        return text[-cls.HANDOFF_MAX_CHARS:]

    @classmethod
    def _prepend_handoff(cls, prompt: str, handoff: str) -> str:
        summary = cls._trim_handoff(handoff)
        if not summary:
            return prompt
        return (
            "HANDOFF TỪ CONVERSATION TRƯỚC:\n"
            f"{summary}\n\n"
            "Tiếp tục từ checkpoint trên. Không làm lại phần đã hoàn thành nếu không có lý do mới.\n\n"
            "YÊU CẦU HIỆN TẠI:\n"
            f"{prompt}"
        )

    @classmethod
    def _read_handoff_summary(cls, meta_dir: Path) -> str:
        path = meta_dir / "handoff_summary.txt"
        try:
            return cls._trim_handoff(path.read_text(encoding="utf-8"))
        except OSError:
            return ""

    @classmethod
    def _fallback_handoff_summary(cls, meta_dir: Path, fallback_meta_dir: Path | None = None) -> str:
        if fallback_meta_dir is not None:
            try:
                recent = cls._trim_handoff((fallback_meta_dir / "last_message.txt").read_text(encoding="utf-8"))
            except OSError:
                recent = ""
            if recent:
                return recent
        saved = cls._read_handoff_summary(meta_dir)
        if saved:
            return saved
        try:
            return cls._trim_handoff((meta_dir / "last_message.txt").read_text(encoding="utf-8"))
        except OSError:
            return ""

    def _handoff_session(
        self,
        session_meta_dir: Path,
        session: dict,
        *,
        reason: str,
        fallback_workspace: Path,
        fallback_label: str,
        use_remotion_root: bool,
    ) -> str:
        session_meta_dir.mkdir(parents=True, exist_ok=True)
        workspace = Path(str(session.get("last_workspace") or fallback_workspace)).resolve()
        label = str(session.get("last_label") or fallback_label)
        last_use_remotion_root = session.get("last_use_remotion_root")
        if last_use_remotion_root is not None:
            use_remotion_root = bool(last_use_remotion_root)
        fallback_meta_dir = workspace / ".producer" / label
        summary = ""
        thread_id = str(session.get("thread_id") or "").strip()
        if thread_id:
            try:
                result, _thread_id, _output_text = self._execute_prompt_queued(
                    self.HANDOFF_PROMPT,
                    workspace,
                    session_meta_dir / "handoff_events.jsonl",
                    session_meta_dir / "handoff_last_message.txt",
                    log_callback=None,
                    use_remotion_root=use_remotion_root,
                    thread_id=thread_id,
                    append_log=True,
                )
                if result.returncode == 0:
                    summary = self._trim_handoff(result.last_message)
            except Exception:
                summary = ""
        if not summary:
            summary = self._fallback_handoff_summary(session_meta_dir, fallback_meta_dir=fallback_meta_dir)
        if summary:
            (session_meta_dir / "handoff_summary.txt").write_text(summary, encoding="utf-8")
        self._retire_session(session_meta_dir, session, reason)
        return summary

    def _is_context_limit_failure(self, output_text: str, last_message: str) -> bool:
        haystack = f"{output_text}\n{last_message}".lower()
        return any(marker in haystack for marker in self.CONTEXT_LIMIT_MARKERS)

    def _is_broken_resume_context_failure(self, output_text: str, last_message: str) -> bool:
        haystack = f"{output_text}\n{last_message}".lower()
        return any(marker in haystack for marker in self.BROKEN_RESUME_CONTEXT_MARKERS)

    def _is_transient_failure(self, output_text: str, last_message: str) -> bool:
        haystack = f"{output_text}\n{last_message}".lower()
        return any(marker in haystack for marker in self.TRANSIENT_FAILURE_MARKERS)

    def _is_transient_result(self, result: StageResult, output_text: str = "") -> bool:
        # Windows can fail before Codex emits any text. 0xC0000142 is surfaced
        # either as the unsigned process code or its signed 32-bit equivalent.
        if result.returncode in {3221225794, -1073741502}:
            return True
        return self._is_transient_failure(output_text, result.last_message)

    @staticmethod
    def _nonnegative_int_env(name: str, default: int) -> int:
        try:
            return max(0, int(os.getenv(name, str(default))))
        except (TypeError, ValueError):
            return default

    def _execute_prompt_queued(self, *args, **kwargs):
        """Serialize browser turns and leave a short cooldown between them."""
        with self._web_turn_lock:
            gap_seconds = self._nonnegative_int_env(
                "COFI_CODEX_MIN_TURN_GAP_SEC",
                self.DEFAULT_MIN_TURN_GAP_SECONDS,
            )
            if gap_seconds and self._last_web_turn_finished_at:
                elapsed = time.monotonic() - self._last_web_turn_finished_at
                remaining = gap_seconds - elapsed
                if remaining > 0:
                    time.sleep(remaining)
            try:
                return self._execute_prompt(*args, **kwargs)
            finally:
                self._last_web_turn_finished_at = time.monotonic()

    def _should_rotate_proactively(self, session: dict, prompt: str) -> bool:
        max_turns = self._nonnegative_int_env("COFI_CODEX_SESSION_MAX_TURNS", self.DEFAULT_SESSION_MAX_TURNS)
        max_prompt_chars = self._nonnegative_int_env(
            "COFI_CODEX_SESSION_MAX_PROMPT_CHARS",
            self.DEFAULT_SESSION_MAX_PROMPT_CHARS,
        )
        turn_count = int(session.get("turn_count") or 0)
        prompt_chars_total = int(session.get("prompt_chars_total") or 0)
        if max_turns and turn_count >= max_turns:
            return True
        if max_prompt_chars and prompt_chars_total + len(prompt) > max_prompt_chars:
            return True
        return False

    @classmethod
    def _sanitize_event_line(cls, line: str) -> str:
        """Keep Codex JSONL useful without persisting multi-megabyte image payloads."""
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return line

        def scrub(value, key: str | None = None):
            if isinstance(value, dict):
                return {item_key: scrub(item_value, str(item_key)) for item_key, item_value in value.items()}
            if isinstance(value, list):
                return [scrub(item) for item in value]
            if (
                key == "data"
                and isinstance(value, str)
                and len(value) > cls.MAX_PERSISTED_EVENT_DATA_CHARS
            ):
                return f"<redacted binary payload: {len(value)} chars>"
            return value

        suffix = "\n" if line.endswith("\n") else ""
        return json.dumps(scrub(payload), ensure_ascii=False, separators=(",", ":")) + suffix

    def _resume_command(
        self,
        workspace: Path,
        thread_id: str,
        last_path: Path,
        use_remotion_root: bool,
        image_paths: list[str | Path] | None = None,
    ) -> list[str]:
        command = [
            self.executable,
            "--search",
            "--dangerously-bypass-approvals-and-sandbox",
        ]
        command += self._transport_config_args()
        command += ["exec"]
        if use_remotion_root:
            command += ["-C", str(self.remotion_dir), "--add-dir", str(workspace)]
        else:
            command += ["-C", str(workspace)]
        command += [
            "resume",
            "--json",
            "--skip-git-repo-check",
        ]
        for image_path in image_paths or []:
            command += ["-i", str(Path(image_path).resolve())]
        command += ["--output-last-message", str(last_path), thread_id, "-"]
        return command

    def _execute_prompt(
        self,
        prompt: str,
        workspace: Path,
        log_path: Path,
        last_path: Path,
        log_callback: Callable[[str], None] | None,
        use_remotion_root: bool,
        thread_id: str | None,
        append_log: bool,
        image_paths: list[str | Path] | None = None,
    ) -> tuple[StageResult, str | None, str]:
        if last_path.exists():
            last_path.unlink()
        command = (
            self._resume_command(workspace, thread_id, last_path, use_remotion_root, image_paths=image_paths)
            if thread_id
            else self.command_for(
                "edit" if use_remotion_root else "plan",
                workspace,
                image_paths=image_paths,
            ) + ["--output-last-message", str(last_path), "-"]
        )
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(self.remotion_dir if use_remotion_root else workspace),
            env=self._subprocess_env(),
            # A long-running Windows backend can otherwise inherit a stale
            # console host and make Codex exit before emitting JSONL with
            # 0xC0000142 (DLL initialization failed).  Codex is a piped worker;
            # it does not need its own console window.
            creationflags=background_worker_creationflags() if os.name == "nt" else 0,
            startupinfo=(
                subprocess.STARTUPINFO(
                    dwFlags=getattr(subprocess, "STARTF_USESHOWWINDOW", 1),
                    wShowWindow=getattr(subprocess, "SW_HIDE", 0),
                )
                if os.name == "nt"
                else None
            ),
        )
        apply_background_worker_qos(process)
        assert process.stdin is not None
        assert process.stdout is not None
        stdin_error = ""
        try:
            process.stdin.write(prompt)
            process.stdin.close()
        except (BrokenPipeError, OSError) as exc:
            stdin_error = str(exc)
            try:
                process.stdin.close()
            except OSError:
                pass

        observed_thread_id = thread_id
        output_lines: list[str] = []
        with log_path.open("a" if append_log else "w", encoding="utf-8") as log_handle:
            for line in process.stdout:
                safe_line = self._sanitize_event_line(line)
                output_lines.append(safe_line)
                log_handle.write(safe_line)
                log_handle.flush()
                if not observed_thread_id:
                    try:
                        event = json.loads(safe_line)
                    except json.JSONDecodeError:
                        event = None
                    if isinstance(event, dict) and event.get("type") == "thread.started":
                        candidate = event.get("thread_id") or (event.get("thread") or {}).get("id")
                        if candidate:
                            observed_thread_id = str(candidate)
                if log_callback:
                    log_callback(safe_line.rstrip("\r\n"))
        returncode = process.wait()
        output_text = "".join(output_lines)
        last_message = last_path.read_text(encoding="utf-8", errors="replace") if last_path.exists() else ""
        if returncode != 0 and not last_message.strip():
            last_message = self._terminal_error_message(output_text)
        if returncode != 0 and not last_message.strip() and stdin_error:
            last_message = f"Codex process closed stdin early: {stdin_error}"
        if returncode != 0 and last_message.strip() == "" and output_text.strip():
            last_message = output_text.strip()[-4000:]
        result = StageResult(returncode=returncode, last_message=last_message.strip(), log_path=log_path)
        return result, observed_thread_id, output_text

    @staticmethod
    def _terminal_error_message(output_text: str) -> str:
        """Extract the useful Codex failure text when output-last-message is empty."""
        messages: list[str] = []
        for line in output_text.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            error = event.get("error")
            if isinstance(error, dict) and isinstance(error.get("message"), str):
                messages.append(error["message"].strip())
            elif isinstance(error, str):
                messages.append(error.strip())
            if event.get("type") == "error" and isinstance(event.get("message"), str):
                messages.append(event["message"].strip())
        return next((message for message in reversed(messages) if message), "")

