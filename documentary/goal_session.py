"""Persistent Antigravity CLI session for COFI DOCUMENTARY chat (goal mode).

One long-lived ``agy`` process per chat scope, fed with ``--input-format
stream-json`` so every user message is a new turn of the *same* process and the
*same* conversation (the CofiFrames model).  Messages are sent as ``/goal ...``
so Antigravity keeps working autonomously until the goal is complete, instead
of answering one turn and stopping.

The conversation id is persisted in ``<workspace>/.producer/<label>/gemini_session.json``
(the same file the legacy reusable path uses), so restarting the app or killing
the process resumes the exact conversation.
"""
from __future__ import annotations

import json
import os
import queue
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable


GOAL_COMPLETE_MARKER = "<!-- GOAL_COMPLETE -->"
TRANSIENT_MARKERS = (
    "unavailable", "503", "502", "504", "overloaded", "deadline exceeded",
    "stream idle timeout", "idle timeout", "không phản hồi bước đầu tiên",
    "eligibility check failed", "send failed", "temporarily", "try again",
    "connection reset", "econnreset", "internal error", "rate limit", "429",
    "resource_exhausted", "resource exhausted", "invalid model selection",
)
LEGACY_MODEL_ALIASES: dict[str, str] = {
    "claude-sonnet-5-5-high": "claude-sonnet-4-6",
    "claude-sonnet-5-5-medium": "claude-sonnet-4-6",
    "claude-sonnet-5-5-low": "claude-sonnet-4-6",
    "claude-opus-5-5-high": "claude-opus-4-6-thinking",
    "claude-opus-5-5-medium": "claude-opus-4-6-thinking",
    "claude-opus-5-5-low": "claude-opus-4-6-thinking",
}
HEALTHY_FALLBACK_MODELS: tuple[str, ...] = (
    "gemini-4-hydrogen-high",
    "gemini-3.8-flash-high",
    "claude-sonnet-4-6",
)
FIRST_STEP_STALL_TIMEOUT_SEC = float(os.getenv("COFI_GOAL_FIRST_STEP_TIMEOUT", "28.0"))
QUOTA_MARKERS = ("quota exhausted", "out of credits", "no credits", "usage limit reached")
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
    "conversation not found",
    "invalid conversation",
    "session expired",
)


class GoalTurnResult:
    def __init__(
        self,
        status: str,
        response: str = "",
        error: str = "",
        conversation_id: str = "",
        goal_complete: bool = False,
        compacted: bool = False,
    ):
        self.status = status  # success | error | cancelled | exited
        self.response = response
        self.error = error
        self.conversation_id = conversation_id
        self.goal_complete = goal_complete
        self.compacted = compacted

    @property
    def context_overflow(self) -> bool:
        text = f"{self.error}\n{self.response}".lower()
        return any(marker in text for marker in CONTEXT_LIMIT_MARKERS)

    @property
    def transient(self) -> bool:
        text = f"{self.error}\n{self.response}".lower()
        if any(marker in text for marker in QUOTA_MARKERS):
            return False
        if self.context_overflow:
            return True
        if self.status == "exited":
            return True
        return self.status == "error" and any(marker in text for marker in TRANSIENT_MARKERS)


class AntigravityGoalSession:
    DEFAULT_MAX_CONTEXT_TOKENS = 115_000
    DEFAULT_MAX_STEPS = 600
    HANDOFF_MAX_CHARS = 10_000

    def __init__(self, gateway: Any, workspace: str | Path, label: str):
        self.gateway = gateway
        self.workspace = Path(workspace).resolve()
        self.label = label
        self.meta_dir = self.workspace / ".producer" / label
        base_label = label[:-5] if label.endswith("_goal") else label
        self.shared_meta_dir = self.workspace / ".producer" / base_label
        self.session_path = self.meta_dir / "gemini_session.json"
        self.log_path = self.meta_dir / "goal_events.jsonl"
        self.proc: subprocess.Popen | None = None
        default_extra: list[str] = []
        uploads_cand = self.workspace / "data" / "chat_uploads"
        if (self.workspace / "documentary").is_dir():
            try:
                uploads_cand.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
        if uploads_cand.is_dir():
            default_extra.append(str(uploads_cand))
        remotion_cand = self.workspace.parent / "CofiRemotion"
        if remotion_cand.is_dir():
            default_extra.append(str(remotion_cand))
        self._extra_dirs: list[str] = default_extra
        self._events: "queue.Queue[dict[str, Any] | None]" = queue.Queue()
        self._turn_lock = threading.Lock()
        self._proc_lock = threading.RLock()
        self._active_cancel_event: threading.Event | None = None
        self._launched_model: str = ""
        self._transcript_cid: str = ""
        self._transcript_offset: int = 0
        self._transcript_steps: dict[int, dict[str, Any]] = {}
        loaded = self._load_session()
        self.conversation_id = str(loaded.get("conversation_id") or "").strip()
        self.input_tokens = int(loaded.get("input_tokens") or 0)
        self.cache_read_tokens = int(loaded.get("cache_read_tokens") or 0)
        self.output_tokens = int(loaded.get("output_tokens") or 0)
        self.step_index = int(loaded.get("step_index") or 0)
        self.turn_count = int(loaded.get("turn_count") or 0)

    # ----------------------------------------------------------------- state
    def _load_session(self) -> dict[str, Any]:
        for candidate in (self.session_path, self.shared_meta_dir / "gemini_session.json"):
            try:
                if candidate.exists():
                    payload = json.loads(candidate.read_text(encoding="utf-8"))
                    if isinstance(payload, dict):
                        return payload
            except (OSError, json.JSONDecodeError):
                continue
        return {}

    def _load_conversation_id(self) -> str:
        return str(self._load_session().get("conversation_id") or "").strip()

    def _save_session_state(self, **updates: Any) -> None:
        session = self._load_session()
        active_model = self._launched_model or str(getattr(self.gateway, "default_model", "") or "").strip()
        session.update({
            "conversation_id": self.conversation_id,
            "mode": "goal",
            "model": active_model,
            "input_tokens": self.input_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "output_tokens": self.output_tokens,
            "step_index": self.step_index,
            "turn_count": self.turn_count,
            "updated_at": time.time(),
            **updates,
        })
        self.meta_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.session_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.session_path)

    def _save_conversation_id(self, conversation_id: str) -> None:
        if not conversation_id:
            return
        changed = conversation_id != self.conversation_id or not self.session_path.exists()
        self.conversation_id = conversation_id
        if changed:
            self._save_session_state()

    @property
    def total_context_tokens(self) -> int:
        return max(0, self.input_tokens) + max(0, self.cache_read_tokens)

    def should_compact(self) -> bool:
        if not self.conversation_id:
            return False
        try:
            max_tokens = max(20_000, int(os.getenv("COFI_GOAL_MAX_CONTEXT_TOKENS") or self.DEFAULT_MAX_CONTEXT_TOKENS))
        except (TypeError, ValueError):
            max_tokens = self.DEFAULT_MAX_CONTEXT_TOKENS
        try:
            max_steps = max(30, int(os.getenv("COFI_GOAL_MAX_STEPS") or self.DEFAULT_MAX_STEPS))
        except (TypeError, ValueError):
            max_steps = self.DEFAULT_MAX_STEPS
        if self.total_context_tokens >= max_tokens:
            return True
        if self.step_index >= max_steps and self.total_context_tokens >= 75_000:
            return True
        return False

    def load_handoff_summary(self) -> str:
        for directory in (self.meta_dir, self.shared_meta_dir):
            path = directory / "handoff_summary.txt"
            if path.exists():
                try:
                    text = path.read_text(encoding="utf-8", errors="replace").strip()
                    if text:
                        return text[:self.HANDOFF_MAX_CHARS]
                except OSError:
                    continue
        return ""

    @staticmethod
    def _format_tool_step_detail(upd: dict[str, Any]) -> str:
        tool_name = str(upd.get("tool_name") or upd.get("step_type") or "").strip()
        summary = str(upd.get("tool_summary") or upd.get("summary") or "").strip()
        tinfo = upd.get("tool_info") if isinstance(upd.get("tool_info"), dict) else {}
        params = tinfo.get("parameters") if isinstance(tinfo.get("parameters"), dict) else {}
        path_val = str(
            params.get("Path")
            or params.get("AbsolutePath")
            or params.get("TargetFile")
            or upd.get("target")
            or ""
        ).strip()
        start_line = params.get("StartLine")
        end_line = params.get("EndLine")
        line_suffix = ""
        if start_line is not None or end_line is not None:
            line_suffix = f"#L{start_line or 1}-L{end_line or start_line}"
        if path_val:
            norm_path = path_val.replace("\\", "/")
            if "/workspaces/" in norm_path:
                norm_path = "workspaces/" + norm_path.split("/workspaces/", 1)[1]
            elif "/documentary/" in norm_path:
                norm_path = "documentary/" + norm_path.split("/documentary/", 1)[1]
            label = f"{tool_name}: {norm_path}{line_suffix}"
            if summary and summary.lower() != tool_name.lower():
                label += f" ({summary})"
            return label[:220]
        if tool_name == "call_mcp_tool":
            srv = str(params.get("ServerName") or "").strip()
            tname = str(params.get("ToolName") or "").strip()
            args_obj = params.get("Arguments") if isinstance(params.get("Arguments"), dict) else {}
            out_path = str(args_obj.get("output_path") or args_obj.get("save_path") or args_obj.get("video_path") or "").strip()
            if out_path:
                out_path = Path(out_path).name
            mcp_desc = "/".join(x for x in (srv, tname) if x) or "mcp"
            if out_path:
                mcp_desc += f" -> {out_path}"
            return f"call_mcp_tool ({mcp_desc})"[:220]
        cmd_val = str(params.get("CommandLine") or "").strip()
        if summary and summary.lower() not in {"run_command", "read_file", "edit_file", "write_file", "tool"}:
            return f"{tool_name}: {summary}"[:220] if tool_name else summary[:220]
        if cmd_val:
            first_line = " ".join(cmd_val.splitlines()).strip()
            return f"{tool_name}: {first_line[:160]}"[:220]
        return (summary or tool_name)[:160]

    def _build_local_handoff_summary(self, extra_context: str = "") -> str:
        sections: list[str] = []
        target_ws: Path | None = None
        try:
            from .workspace_ledger import (
                collect_job_live_diagnostics,
                format_compact_ledger_brief,
                format_compact_repo_code_brief,
                resolve_job_workspace_for_meta,
                sync_workspace_ledger,
            )

            target_ws = resolve_job_workspace_for_meta(self.workspace, self.meta_dir)
            if target_ws is not None:
                job_json_path = self.workspace / "data" / "jobs" / target_ws.name / "job.json"
                if not job_json_path.is_file():
                    job_json_path = self.workspace / "data" / "jobs" / f"{target_ws.name}.json"
                fresh_job = None
                if job_json_path.is_file():
                    try:
                        fresh_job = json.loads(job_json_path.read_text(encoding="utf-8", errors="replace"))
                    except Exception:
                        fresh_job = None
                sync_workspace_ledger(target_ws, fresh_job)
                ledger_brief = format_compact_ledger_brief(target_ws)
                if ledger_brief:
                    sections.append(f"Sổ cái tiến độ dự án (`state_ledger.json`):\n{ledger_brief}")
                diag = collect_job_live_diagnostics(target_ws, fresh_job)
                rc_logs = diag.get("root_cause_log_excerpts") if isinstance(diag, dict) else None
                if isinstance(rc_logs, dict) and rc_logs:
                    diag_lines = ["Chẩn đoán lỗi thực tế trên đĩa hiện tại (`live_diagnostics`):"]
                    for lrel, exs in rc_logs.items():
                        diag_lines.append(f"- `{lrel}`: " + " | ".join(exs[:4]))
                    sections.append("\n".join(diag_lines))
            else:
                repo_brief = format_compact_repo_code_brief(self.workspace)
                if repo_brief:
                    sections.append(f"Sổ cái mã nguồn hệ thống (`repo_code_index.json`):\n- {repo_brief}")
        except Exception:
            pass

        # Include recent substantive user/assistant exchanges from producer_chat_history.jsonl
        # Never let repeated Stop ("Đã dừng lượt làm việc") or short pings ("trả lời đi") evict the user's real task!
        meta_ping_re = re.compile(
            r"(?i)^\s*(?:trả lời đi|tra loi di|tiếp tục|tiep tuc|làm đi|fix đi|sao lâu thế\??|nhanh lên)\s*[.!?\s]*$"
        )
        history_candidates: list[Path] = []
        if target_ws is not None:
            history_candidates.append(target_ws / "producer_chat_history.jsonl")
        history_candidates.append(self.workspace / "data" / "producer_chat_history.jsonl")
        history_candidates.append(self.workspace / ".producer" / "producer_chat_history.jsonl")
        chat_lines: list[str] = []
        last_substantive_user: str = ""
        history_tool_steps: list[str] = []
        for hpath in history_candidates:
            if not hpath.is_file():
                continue
            try:
                raw_rows = hpath.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]
                for raw_row in raw_rows:
                    try:
                        item = json.loads(raw_row)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(item, dict):
                        continue
                    role = str(item.get("role") or "user").upper()
                    content = str(item.get("content") or "").strip()
                    for st in (item.get("steps") or [])[-12:]:
                        if isinstance(st, dict) and str(st.get("step_type") or "") not in {"agent_response", "thinking", "user_input", ""}:
                            detail = self._format_tool_step_detail(st)
                            if detail and detail not in {"run_command", "read_file", "edit_file", "write_file", "user_input"}:
                                if not history_tool_steps or history_tool_steps[-1] != detail:
                                    history_tool_steps.append(detail)
                    low = content.lower()
                    if not content or low in {"/compact", "/nen", "/new", "/reset"}:
                        continue
                    if (
                        content.startswith("Đã nén ngữ cảnh (`/compact`)")
                        or content.startswith("Đã khởi tạo phiên hội thoại")
                        or content.startswith("Đã dừng lượt làm việc theo yêu cầu")
                    ):
                        continue
                    if role == "USER" and not meta_ping_re.match(content):
                        last_substantive_user = f"[USER]: {content[:700]}"
                    chat_lines.append(f"[{role}]: {content[:700]}")
                if chat_lines or history_tool_steps:
                    break
            except OSError:
                continue
        if chat_lines or last_substantive_user:
            tail_chat = chat_lines[-6:]
            if last_substantive_user and last_substantive_user not in tail_chat:
                tail_chat = [last_substantive_user, *tail_chat[-5:]]
            sections.append("Lịch sử trao đổi & yêu cầu gần nhất trong dự án:\n" + "\n".join(tail_chat))

        recent_responses: list[str] = []
        recent_tools: list[str] = list(history_tool_steps[-10:])
        last_thinking = ""
        in_progress_thinking_after_last_result = False
        if self.log_path.exists():
            try:
                if self.conversation_id:
                    self._sync_transcript_steps(self.conversation_id)
                tail_lines = self.log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-260:]
                for raw in tail_lines:
                    try:
                        evt = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(evt, dict):
                        continue
                    cid = self._conversation_id_of(evt)
                    if cid and cid != self._transcript_cid:
                        self._sync_transcript_steps(cid)
                    kind = str(evt.get("event") or evt.get("type") or "").lower()
                    if kind == "step_update":
                        upd = evt.get("step_update") if isinstance(evt.get("step_update"), dict) else {}
                        self._enrich_step_update_from_transcript(upd)
                        step_type = str(upd.get("step_type") or "")
                        if step_type == "agent_response":
                            th = str(upd.get("thinking") or "").strip()
                            if th:
                                last_thinking = th[-700:]
                                in_progress_thinking_after_last_result = True
                            cnt = str(upd.get("content") or upd.get("text_delta") or "").strip()
                            if cnt and len(cnt) >= 40:
                                recent_responses.append(cnt[-900:])
                        elif step_type and step_type not in {"thinking", "system_message", "user_input"}:
                            detail = self._format_tool_step_detail(upd)
                            if detail and detail not in {"run_command", "read_file", "edit_file", "write_file", "user_input"}:
                                if not recent_tools or recent_tools[-1] != detail:
                                    recent_tools.append(detail)
                    elif kind == "result":
                        res = evt.get("result") if isinstance(evt.get("result"), dict) else {}
                        resp = str(res.get("response") or "").replace(GOAL_COMPLETE_MARKER, "").strip()
                        if resp:
                            recent_responses.append(resp[-900:])
                            in_progress_thinking_after_last_result = False
            except OSError:
                pass
        if recent_tools:
            sections.append("Các thao tác công cụ cụ thể vừa thực hiện trên đĩa:\n- " + "\n- ".join(recent_tools[-12:]))
        if last_thinking and (in_progress_thinking_after_last_result or not recent_responses):
            sections.append(f"Chẩn đoán / suy luận kỹ thuật vừa tìm ra trước khi dừng hoặc nén:\n{last_thinking}")
        if recent_responses:
            sections.append("Phản hồi hoàn tất gần nhất của phiên trước:\n" + recent_responses[-1])
        if extra_context.strip():
            clean_extra = extra_context.strip()
            if not clean_extra.startswith("Đã dừng lượt làm việc theo yêu cầu"):
                sections.append(f"Ghi chú bàn giao tức thì:\n{clean_extra[-1200:]}")
        summary = "\n\n".join(sections).strip()
        if not summary:
            summary = f"Phiên làm việc trước ({self.conversation_id or 'goal'}) đã bàn giao ngữ cảnh sau {self.turn_count} lượt / {self.step_index} bước."
        return summary[:self.HANDOFF_MAX_CHARS]

    def save_checkpoint_handoff(self, extra_context: str = "") -> str:
        """Persist an up-to-date `handoff_summary.txt` without rotating or dropping `conversation_id`."""
        handoff = self._build_local_handoff_summary(extra_context=extra_context)
        for directory in {self.meta_dir, self.shared_meta_dir}:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                (directory / "handoff_summary.txt").write_text(handoff, encoding="utf-8")
            except OSError:
                pass
        return handoff

    def compact_and_rotate(self, reason: str = "context_guard", extra_context: str = "") -> str:
        old_cid = self.conversation_id
        handoff = self.save_checkpoint_handoff(extra_context=extra_context)
        if old_cid:
            try:
                self.meta_dir.mkdir(parents=True, exist_ok=True)
                with (self.meta_dir / "retired_sessions.jsonl").open("a", encoding="utf-8") as handle:
                    handle.write(
                        json.dumps(
                            {
                                "conversation_id": old_cid,
                                "turn_count": self.turn_count,
                                "step_index": self.step_index,
                                "input_tokens": self.input_tokens,
                                "cache_read_tokens": self.cache_read_tokens,
                                "reason": reason,
                                "at": time.time(),
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
            except OSError:
                pass
        self.stop()
        self.conversation_id = ""
        self.input_tokens = 0
        self.cache_read_tokens = 0
        self.output_tokens = 0
        self.step_index = 0
        self.turn_count = 0
        self._save_session_state(compacted_from=old_cid, compacted_reason=reason)
        return handoff

    @property
    def busy(self) -> bool:
        return self._turn_lock.locked()

    @property
    def has_conversation(self) -> bool:
        return bool(self.conversation_id)

    def _effective_model(self) -> str:
        raw = str(getattr(self, "_model_override", "") or getattr(self.gateway, "default_model", "") or "").strip()
        return LEGACY_MODEL_ALIASES.get(raw.lower(), raw)

    # --------------------------------------------------------------- process
    def _args(self) -> list[str]:
        executable = self.gateway._antigravity_runtime_executable()
        if not executable:
            raise RuntimeError("Không tìm thấy Antigravity CLI (agy). Cài agy hoặc đặt COFI_ANTIGRAVITY_BIN.")
        args = [
            executable,
            "--dangerously-skip-permissions",
            "--input-format", "stream-json",
            "--output-format", "stream-json",
        ]
        model = self._effective_model()
        if model:
            args.extend(["--model", model])
        effort = str(os.getenv("COFI_GOAL_EFFORT") or "").strip().lower()
        if effort in {"low", "medium", "high", "xhigh", "max"}:
            args.extend(["--effort", effort])
        if self.conversation_id:
            args.extend(["--conversation", self.conversation_id])
        for directory in self._extra_dirs:
            args.extend(["--add-dir", directory])
        return args

    def _alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def _ensure(self, extra_dirs: list[str]) -> None:
        with self._proc_lock:
            desired_model = self._effective_model()
            wanted = [d for d in extra_dirs if d and Path(d).is_dir()]
            missing = [d for d in wanted if d.lower() not in {x.lower() for x in self._extra_dirs}]
            model_changed = bool(desired_model and self._launched_model and desired_model != self._launched_model)
            if (missing or model_changed) and self._alive():
                # --add-dir and --model are launch flags; relaunch on the same conversation.
                self._kill_locked()
            if missing:
                self._extra_dirs.extend(missing)
            if self._alive():
                return
            self._events = queue.Queue()
            command = self._args()
            self._launched_model = desired_model
            creationflags, startupinfo = self.gateway._launch_window_options(command[0])
            self.meta_dir.mkdir(parents=True, exist_ok=True)
            self.proc = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(self.workspace),
                env=self.gateway._subprocess_env(),
                creationflags=creationflags,
                startupinfo=startupinfo,
                bufsize=1,
            )
            try:
                from .render_cache import apply_background_worker_qos

                apply_background_worker_qos(self.proc)
            except Exception:
                pass
            threading.Thread(target=self._reader, args=(self.proc, self._events), daemon=True, name=f"goal-{self.label}").start()

    def _reader(self, proc: subprocess.Popen, events: "queue.Queue[dict[str, Any] | None]") -> None:
        assert proc.stdout is not None
        with self.log_path.open("a", encoding="utf-8") as log:
            for raw in proc.stdout:
                line = raw.rstrip("\r\n")
                if not line:
                    continue
                log.write(line + "\n")
                log.flush()
                try:
                    payload = json.loads(line)
                    if not isinstance(payload, dict):
                        payload = {"event": "raw", "text": line}
                except json.JSONDecodeError:
                    payload = {"event": "raw", "text": line}
                payload["_line"] = line
                events.put(payload)
        events.put(None)

    def _kill_locked(self) -> None:
        proc = self.proc
        self.proc = None
        if proc is None or proc.poll() is not None:
            return
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=15,
                )
            else:
                proc.kill()
        except (OSError, subprocess.SubprocessError):
            pass
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass

    def stop(self) -> None:
        """Kill the running turn. The conversation id is kept, so the next
        message resumes the same conversation (agy has no in-band cancel)."""
        with self._proc_lock:
            self._kill_locked()

    def reset(self) -> None:
        self.stop()
        self.conversation_id = ""
        self.input_tokens = 0
        self.cache_read_tokens = 0
        self.output_tokens = 0
        self.step_index = 0
        self.turn_count = 0
        self._transcript_cid = ""
        self._transcript_offset = 0
        self._transcript_steps = {}
        try:
            self.session_path.unlink(missing_ok=True)
        except OSError:
            pass

    # ------------------------------------------------------------------ turn
    @staticmethod
    def _brain_transcript_path(cid: str) -> Path | None:
        if not cid:
            return None
        home = Path.home()
        for base in (home / ".gemini" / "antigravity-cli" / "brain", home / ".gemini" / "antigravity" / "brain"):
            for fname in ("transcript_full.jsonl", "transcript.jsonl"):
                candidate = base / cid / ".system_generated" / "logs" / fname
                if candidate.exists():
                    return candidate
        return None

    def _sync_transcript_steps(self, cid: str) -> None:
        if not cid:
            return
        if cid != self._transcript_cid:
            self._transcript_cid = cid
            self._transcript_offset = 0
            self._transcript_steps = {}
        path = self._brain_transcript_path(cid)
        if path is None:
            return
        try:
            with path.open("rb") as handle:
                handle.seek(self._transcript_offset)
                chunk = handle.read()
                self._transcript_offset = handle.tell()
            if not chunk:
                return
            for raw_line in chunk.decode("utf-8", errors="replace").split("\n"):
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    row = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict) and isinstance(row.get("step_index"), int):
                    self._transcript_steps[int(row["step_index"])] = row
        except OSError:
            pass

    def _enrich_step_update_from_transcript(self, update: dict[str, Any]) -> bool:
        cid = str(update.get("conversation_id") or self.conversation_id or "").strip()
        if not cid:
            return False
        self._sync_transcript_steps(cid)
        raw_step = update.get("step_index")
        if not isinstance(raw_step, int):
            return False
        step_type = str(update.get("step_type") or "")
        changed = False
        if step_type == "agent_response":
            row = self._transcript_steps.get(raw_step)
            if isinstance(row, dict):
                thinking = str(row.get("thinking") or "").strip()
                if thinking and not update.get("thinking"):
                    update["thinking"] = thinking
                    changed = True
                content = str(row.get("content") or "").strip()
                if content and not update.get("content"):
                    update["content"] = content
                    changed = True
        else:
            tool_name = str(update.get("tool_name") or "").strip()
            for back_idx in range(raw_step, max(-1, raw_step - 6), -1):
                prow = self._transcript_steps.get(back_idx)
                if not isinstance(prow, dict):
                    continue
                tcalls = prow.get("tool_calls")
                if not isinstance(tcalls, list) or not tcalls:
                    continue
                matched = None
                for tc in tcalls:
                    if isinstance(tc, dict) and (not tool_name or str(tc.get("name") or "") == tool_name):
                        matched = tc
                        break
                if matched is None and isinstance(tcalls[0], dict):
                    matched = tcalls[0]
                if isinstance(matched, dict):
                    args = matched.get("args") if isinstance(matched.get("args"), dict) else {}
                    tool_action = str(args.get("toolAction") or "").strip().strip('"')
                    tool_summary = str(args.get("toolSummary") or "").strip().strip('"')
                    if tool_action and not update.get("tool_action"):
                        update["tool_action"] = tool_action
                        changed = True
                    if tool_summary and not update.get("tool_summary"):
                        update["tool_summary"] = tool_summary
                        changed = True
                    if args:
                        tinfo = update.get("tool_info")
                        if not isinstance(tinfo, dict):
                            tinfo = {}
                            update["tool_info"] = tinfo
                        params = tinfo.get("parameters")
                        if not isinstance(params, dict):
                            params = {}
                            tinfo["parameters"] = params
                        for k in ("Path", "AbsolutePath", "TargetFile", "StartLine", "EndLine", "CommandLine", "ServerName", "ToolName", "Arguments", "Url", "query", "Pattern"):
                            if k in args and k not in params:
                                params[k] = args[k]
                                changed = True
                break
        return changed

    def _poll_active_subagents(
        self,
        subagent_offsets: dict[str, int],
        on_line: Callable[[str], None] | None,
    ) -> None:
        if not on_line or not self.conversation_id:
            return
        self._sync_transcript_steps(self.conversation_id)
        for row in list(self._transcript_steps.values())[-12:]:
            if not isinstance(row, dict):
                continue
            raw_text = str(row.get("content") or "")
            if "conversationId" not in raw_text:
                continue
            for match in re.findall(r'"conversationId"\s*:\s*"([0-9a-fA-F-]{32,40})"', raw_text):
                if match and match != self.conversation_id and match not in subagent_offsets:
                    subagent_offsets[match] = 0
        for sub_cid in list(subagent_offsets.keys()):
            path = self._brain_transcript_path(sub_cid)
            if path is None:
                continue
            try:
                with path.open("rb") as handle:
                    handle.seek(subagent_offsets[sub_cid])
                    chunk = handle.read()
                    subagent_offsets[sub_cid] = handle.tell()
                if not chunk:
                    continue
                for raw_line in chunk.decode("utf-8", errors="replace").split("\n"):
                    raw_line = raw_line.strip()
                    if not raw_line:
                        continue
                    try:
                        srow = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(srow, dict):
                        continue
                    sidx = srow.get("step_index")
                    stype = str(srow.get("type") or "").upper()
                    tcalls = srow.get("tool_calls") if isinstance(srow.get("tool_calls"), list) else []
                    thinking = str(srow.get("thinking") or "").strip()
                    if tcalls and isinstance(tcalls[0], dict):
                        tc = tcalls[0]
                        tname = str(tc.get("name") or "tool")
                        targs = tc.get("args") if isinstance(tc.get("args"), dict) else {}
                        tsum = str(targs.get("toolSummary") or targs.get("toolAction") or targs.get("Path") or targs.get("CommandLine") or "")[:140]
                        synth = {
                            "type": "step_update",
                            "conversation_id": self.conversation_id,
                            "step_update": {
                                "conversation_id": self.conversation_id,
                                "subagent_conversation_id": sub_cid,
                                "step_index": int(sidx or 0),
                                "step_type": tname,
                                "status": "RUNNING",
                                "tool_name": tname,
                                "tool_summary": f"[Subagent] {tsum}" if tsum else f"[Subagent] {tname}",
                                "thinking": thinking[:400] if thinking else "",
                            },
                        }
                        on_line(json.dumps(synth, ensure_ascii=False))
                    elif stype == "PLANNER_RESPONSE" and thinking:
                        synth = {
                            "type": "step_update",
                            "conversation_id": self.conversation_id,
                            "step_update": {
                                "conversation_id": self.conversation_id,
                                "subagent_conversation_id": sub_cid,
                                "step_index": int(sidx or 0),
                                "step_type": "agent_response",
                                "status": "DONE",
                                "thinking": f"[Subagent] {thinking[:400]}",
                            },
                        }
                        on_line(json.dumps(synth, ensure_ascii=False))
            except OSError:
                pass

    @staticmethod
    def _conversation_id_of(event: dict[str, Any]) -> str:
        for candidate in (
            event.get("conversation_id"),
            (event.get("init") or {}).get("conversation_id") if isinstance(event.get("init"), dict) else None,
            (event.get("step_update") or {}).get("conversation_id") if isinstance(event.get("step_update"), dict) else None,
            (event.get("result") or {}).get("conversation_id") if isinstance(event.get("result"), dict) else None,
        ):
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return ""

    @staticmethod
    def _inject_handoff(content: str, handoff: str) -> str:
        if not handoff.strip() or "BẢN BÀN GIAO" in content:
            return content
        prefix = "/goal " if content.lstrip().lower().startswith("/goal") else ""
        body = content.lstrip()[5:].strip() if prefix else content
        return (
            f"{prefix}[BẢN BÀN GIAO NGỮ CẢNH TỰ ĐỘNG TỪ PHIÊN TRƯỚC — TIẾP TỤC LIỀN MẠCH, KHÔNG LÀM LẠI PHẦN ĐÃ XONG]\n"
            f"{handoff.strip()}\n\n"
            f"{body}"
        )

    def _execute_single_turn(
        self,
        content: str,
        *,
        extra_dirs: list[str],
        on_line: Callable[[str], None] | None,
        cancel_event: threading.Event | None,
        compacted: bool = False,
    ) -> GoalTurnResult:
        self._ensure(extra_dirs)
        proc = self.proc
        events = self._events
        assert proc is not None and proc.stdin is not None
        try:
            proc.stdin.write(json.dumps({"event": "user", "message": {"content": content}}, ensure_ascii=False) + "\n")
            proc.stdin.flush()
        except (OSError, ValueError) as exc:
            self.stop()
            return GoalTurnResult("exited", error=f"Không gửi được tin nhắn tới Antigravity: {exc}", conversation_id=self.conversation_id, compacted=compacted)
        text_parts: list[str] = []
        subagent_offsets: dict[str, int] = {}
        last_step_input_tokens: int | None = None
        last_step_cache_read_tokens: int | None = None
        agent_response_done = False
        steps_in_turn = 0
        turn_started_mono = time.monotonic()
        saw_real_activity = False
        error_step_messages: list[str] = []
        last_error_step_mono: float | None = None
        active_model_name = self._effective_model() or "default"
        while True:
            if cancel_event is not None and cancel_event.is_set():
                self.stop()
                if last_step_input_tokens is not None or last_step_cache_read_tokens is not None:
                    self.input_tokens = int(last_step_input_tokens or self.input_tokens or 0)
                    self.cache_read_tokens = int(last_step_cache_read_tokens or self.cache_read_tokens or 0)
                partial_text = "".join(text_parts).replace(GOAL_COMPLETE_MARKER, "").strip()
                self._save_session_state(
                    last_cancelled_at=time.time(),
                    last_response_excerpt=partial_text[-1200:] if partial_text else "",
                )
                self.save_checkpoint_handoff(extra_context=partial_text[-1000:] if partial_text else "")
                return GoalTurnResult(
                    "cancelled",
                    response=partial_text,
                    conversation_id=self.conversation_id,
                    compacted=compacted,
                )
            try:
                event = events.get(timeout=0.5)
            except queue.Empty:
                self._poll_active_subagents(subagent_offsets, on_line)
                now_mono = time.monotonic()
                if last_error_step_mono is not None and (now_mono - last_error_step_mono) >= 3.0 and not text_parts:
                    self.stop()
                    err_summary = error_step_messages[-1] if error_step_messages else f"Model '{active_model_name}' trả về lỗi upstream (stream idle timeout)."
                    return GoalTurnResult(
                        "error",
                        response="",
                        error=err_summary,
                        conversation_id=self.conversation_id,
                        compacted=compacted,
                    )
                if not saw_real_activity and (now_mono - turn_started_mono) >= FIRST_STEP_STALL_TIMEOUT_SEC:
                    self.stop()
                    return GoalTurnResult(
                        "error",
                        response="",
                        error=f"Model '{active_model_name}' quá tải hoặc treo kết nối (không phản hồi bước đầu tiên sau {int(FIRST_STEP_STALL_TIMEOUT_SEC)}s — stream idle timeout).",
                        conversation_id=self.conversation_id,
                        compacted=compacted,
                    )
                continue
            if event is None:
                code = proc.poll()
                self.proc = None
                streamed_clean = "".join(text_parts).replace(GOAL_COMPLETE_MARKER, "").strip()
                if streamed_clean and (GOAL_COMPLETE_MARKER in "".join(text_parts) or (agent_response_done and len(streamed_clean) >= 60)):
                    return GoalTurnResult(
                        "success",
                        streamed_clean,
                        conversation_id=self.conversation_id,
                        goal_complete=GOAL_COMPLETE_MARKER in "".join(text_parts),
                        compacted=compacted,
                    )
                return GoalTurnResult(
                    "exited",
                    response=streamed_clean,
                    error=f"Antigravity CLI đã thoát (mã {code}).",
                    conversation_id=self.conversation_id,
                    compacted=compacted,
                )
            line = str(event.pop("_line", "") or "")
            cid = self._conversation_id_of(event)
            if cid:
                self._save_conversation_id(cid)
            kind = str(event.get("event") or event.get("type") or "").lower()
            if kind == "step_update":
                update = event.get("step_update") if isinstance(event.get("step_update"), dict) else {}
                raw_step = event.get("step_index") or update.get("step_index")
                if isinstance(raw_step, int) and raw_step > self.step_index:
                    self.step_index = raw_step
                step_usage = update.get("usage") if isinstance(update.get("usage"), dict) else {}
                if step_usage:
                    steps_in_turn += 1
                    try:
                        last_step_input_tokens = max(0, int(step_usage.get("input_tokens") or 0))
                        last_step_cache_read_tokens = max(0, int(step_usage.get("cache_read_tokens") or 0))
                    except (TypeError, ValueError):
                        pass
                if self._enrich_step_update_from_transcript(update):
                    line = json.dumps(event, ensure_ascii=False)
                stype_low = str(update.get("step_type") or "").lower()
                if stype_low in {"agent_response", "tool", "command", "mcp"}:
                    saw_real_activity = True
                    last_error_step_mono = None
                elif stype_low == "error_message":
                    raw_step_int = raw_step if isinstance(raw_step, int) else -1
                    trow = self._transcript_steps.get(raw_step_int) if raw_step_int >= 0 else None
                    err_txt = str((trow or {}).get("content") or update.get("error") or "API stream idle timeout").strip()
                    error_step_messages.append(err_txt)
                    last_error_step_mono = time.monotonic()
                    if len(error_step_messages) >= 2 and not text_parts:
                        self.stop()
                        return GoalTurnResult(
                            "error",
                            response="",
                            error=err_txt,
                            conversation_id=self.conversation_id,
                            compacted=compacted,
                        )
                if update.get("step_type") == "agent_response":
                    if isinstance(update.get("text_delta"), str):
                        text_parts.append(update["text_delta"])
                    if str(update.get("state") or "").upper() == "DONE":
                        agent_response_done = True
                        if not text_parts and isinstance(update.get("content"), str) and update["content"].strip():
                            text_parts.append(update["content"])
            if on_line and line:
                on_line(line)
            if kind == "step_update":
                continue
            if kind != "result":
                continue
            result = event.get("result") if isinstance(event.get("result"), dict) else {}
            usage = result.get("usage") if isinstance(result.get("usage"), dict) else {}
            if last_step_input_tokens is not None or last_step_cache_read_tokens is not None:
                self.input_tokens = int(last_step_input_tokens or 0)
                self.cache_read_tokens = int(last_step_cache_read_tokens or 0)
                if isinstance(usage, dict):
                    try:
                        self.output_tokens = max(0, int(usage.get("output_tokens") or self.output_tokens))
                    except (TypeError, ValueError):
                        pass
            elif isinstance(usage, dict):
                try:
                    divisor = max(1, steps_in_turn)
                    self.input_tokens = max(0, int(usage.get("input_tokens") or self.input_tokens) // divisor)
                    self.cache_read_tokens = max(0, int(usage.get("cache_read_tokens") or self.cache_read_tokens))
                    self.output_tokens = max(0, int(usage.get("output_tokens") or self.output_tokens))
                except (TypeError, ValueError):
                    pass
            self.turn_count += 1
            status = str(result.get("status") or "").upper()
            response = str(result.get("response") or "").strip() or "".join(text_parts).strip()
            error = str(result.get("error") or "").strip()
            complete = GOAL_COMPLETE_MARKER in response
            clean = response.replace(GOAL_COMPLETE_MARKER, "").strip()
            self._save_session_state(last_response_excerpt=clean[-1200:] if clean else "")
            if (status == "SUCCESS" and not error) or (clean and (complete or (agent_response_done and len(clean) >= 60))):
                return GoalTurnResult("success", clean, conversation_id=self.conversation_id, goal_complete=complete, compacted=compacted)
            return GoalTurnResult("error", clean, error or status or "Lỗi không xác định", self.conversation_id, complete, compacted=compacted)

    def preempt(self) -> None:
        ev = self._active_cancel_event
        if ev is not None:
            ev.set()
        self.stop()

    def run_turn(
        self,
        content: str,
        *,
        extra_dirs: list[str] | None = None,
        on_line: Callable[[str], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> GoalTurnResult:
        if not self._turn_lock.acquire(blocking=False):
            self.preempt()
            if not self._turn_lock.acquire(timeout=15.0):
                raise RuntimeError("Phiên goal đang chạy; hãy đợi hoặc bấm Dừng trước khi gửi yêu cầu mới.")
        self._active_cancel_event = cancel_event
        try:
            dirs = list(extra_dirs or [])
            compacted = False
            active_content = content
            if self.has_conversation and self.should_compact():
                handoff = self.compact_and_rotate(reason="proactive_context_guard")
                compacted = True
                active_content = self._inject_handoff(content, handoff)
                if on_line:
                    on_line(json.dumps({
                        "event": "step_update",
                        "step_update": {
                            "step_type": "context_compaction",
                            "summary": "Tự động nén ngữ cảnh (Context Compaction) và nối tiếp phiên làm việc mới",
                        },
                    }, ensure_ascii=False))
            elif not self.has_conversation:
                existing_handoff = self.load_handoff_summary()
                if existing_handoff:
                    active_content = self._inject_handoff(content, existing_handoff)

            had_conversation = self.has_conversation
            self._model_override = ""
            result = self._execute_single_turn(
                active_content,
                extra_dirs=dirs,
                on_line=on_line,
                cancel_event=cancel_event,
                compacted=compacted,
            )
            if (
                result.status in {"error", "exited"}
                and not (cancel_event is not None and cancel_event.is_set())
                and not (result.response or "").strip()
                and result.transient
                and not result.context_overflow
            ):
                failed_model = self._effective_model()
                for fb_model in HEALTHY_FALLBACK_MODELS:
                    if fb_model.lower() == failed_model.lower():
                        continue
                    self._model_override = fb_model
                    self.stop()
                    if on_line:
                        on_line(json.dumps({
                            "event": "step_update",
                            "step_update": {
                                "step_type": "context_compaction",
                                "summary": f"⚡ Máy chủ model `{failed_model or 'cũ'}` đang quá tải/treo luồng — tự động chuyển sang `{fb_model}` để mở phiên ngay!",
                            },
                        }, ensure_ascii=False))
                    result = self._execute_single_turn(
                        active_content,
                        extra_dirs=dirs,
                        on_line=on_line,
                        cancel_event=cancel_event,
                        compacted=compacted,
                    )
                    if result.status == "success" or (cancel_event is not None and cancel_event.is_set()):
                        setattr(self.gateway, "default_model", fb_model)
                        break
                    failed_model = fb_model
            if (
                result.status in {"error", "exited"}
                and not (cancel_event is not None and cancel_event.is_set())
                and (result.context_overflow or (had_conversation and self.total_context_tokens >= 180_000))
            ):
                handoff = self.compact_and_rotate(
                    reason="reactive_context_overflow",
                    extra_context=result.response or result.error,
                )
                if on_line:
                    on_line(json.dumps({
                        "event": "step_update",
                        "step_update": {
                            "step_type": "context_compaction",
                            "summary": "Phiên đạt giới hạn ngữ cảnh — tự động bàn giao sang phiên mới và tiếp tục",
                        },
                    }, ensure_ascii=False))
                retry_content = self._inject_handoff(content, handoff)
                result = self._execute_single_turn(
                    retry_content,
                    extra_dirs=dirs,
                    on_line=on_line,
                    cancel_event=cancel_event,
                    compacted=True,
                )
            return result
        finally:
            self._active_cancel_event = None
            self._turn_lock.release()


class GoalSessionRegistry:
    def __init__(self) -> None:
        self._sessions: dict[str, AntigravityGoalSession] = {}
        self._lock = threading.Lock()

    def get(self, gateway: Any, workspace: str | Path, label: str) -> AntigravityGoalSession:
        key = f"{Path(workspace).resolve()}::{label}".lower()
        with self._lock:
            session = self._sessions.get(key)
            if session is None:
                session = AntigravityGoalSession(gateway, workspace, label)
                self._sessions[key] = session
            return session

    def reset(self, workspace: str | Path, label: str) -> None:
        key = f"{Path(workspace).resolve()}::{label}".lower()
        with self._lock:
            session = self._sessions.pop(key, None)
        if session is not None:
            session.reset()
        else:
            try:
                (Path(workspace).resolve() / ".producer" / label / "gemini_session.json").unlink(missing_ok=True)
            except OSError:
                pass

    def stop_all(self) -> None:
        with self._lock:
            sessions = list(self._sessions.values())
        for session in sessions:
            session.stop()

