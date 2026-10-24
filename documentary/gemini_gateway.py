from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
from typing import Callable
from urllib.parse import urlparse

import requests

from .codex_gateway import StageResult
from .engines import resolve_executable
from .prompts import build_phase_prompt
from .source_discovery import scrub_source_secret_env


class GeminiGateway:
    DEFAULT_WEB2API_URL = "http://127.0.0.1:8081"
    DEFAULT_WEB2API_MODEL = "gemini-3.5-flash-thinking@think=0"
    ANTIGRAVITY_PROBE_TTL_SEC = 60.0
    DEFAULT_SESSION_MAX_INPUT_TOKENS = 90_000
    DEFAULT_SESSION_MAX_TURNS = 0
    DEFAULT_SESSION_MAX_PROMPT_CHARS = 180_000
    HANDOFF_PROMPT = (
        "Tóm tắt cuộc hội thoại này để chính bạn tiếp tục trong một session Gemini mới. "
        "Giữ lại mục tiêu người dùng, quyết định đã chốt, việc đã làm và bằng chứng, "
        "đường dẫn/ID cần thiết, việc đang dở và bước tiếp theo. "
        "Phân biệt rõ điều đã xác minh với điều chưa xác minh. "
        "Không thực hiện thao tác mới. Trả về bản bàn giao tiếng Việt ngắn gọn, tối đa 6000 ký tự."
    )
    PLAN_FIELDS = (
        "beat_id",
        "narration_text",
        "purpose",
        "target_duration_sec",
        "visual_type",
        "source_priority",
        "visual_description",
        "footage_search_queries",
        "factual_source_refs",
        "framing_motion_intent",
        "on_screen_text",
        "sound_notes",
    )

    def __init__(self, executable: str | None = None, antigravity_executable: str | None = None):
        requested = executable or os.getenv("COFI_GEMINI_BIN") or "gemini"
        self.legacy_executable = resolve_executable(requested) or requested
        self.antigravity_executable = self._find_antigravity_executable(
            antigravity_executable,
            auto_detect=executable is None,
        )
        self.transport = "antigravity" if self.antigravity_executable else "gemini"
        self.executable = self.antigravity_executable or self.legacy_executable
        self.default_model = str(os.getenv("COFI_GEMINI_MODEL") or "").strip()
        self._antigravity_probe_cache: dict[str, object] | None = None
        self._antigravity_probe_at = 0.0
        self._probe_lock = threading.RLock()
        self._reusable_lock = threading.RLock()
        self._session_locks: dict[str, threading.RLock] = {}

    def _lock_for_session(self, meta_dir: Path) -> threading.RLock:
        key = str(meta_dir.resolve()).lower()
        with self._reusable_lock:
            lock = self._session_locks.get(key)
            if lock is None:
                lock = threading.RLock()
                self._session_locks[key] = lock
            return lock

    @staticmethod
    def _find_antigravity_executable(requested: str | None, *, auto_detect: bool) -> str | None:
        candidates: list[str] = []
        if requested:
            candidates.append(requested)
        elif auto_detect:
            configured = str(os.getenv("COFI_ANTIGRAVITY_BIN") or "").strip()
            if configured:
                candidates.append(configured)
            shared_binary = Path(__file__).resolve().parents[2] / "agy" / "bin" / "agy.exe"
            candidates.append(str(shared_binary))
            candidates.append("agy")
            local_app_data = str(os.getenv("LOCALAPPDATA") or "").strip()
            if local_app_data:
                candidates.append(str(Path(local_app_data) / "agy" / "bin" / "agy.exe"))

        for candidate in candidates:
            resolved = resolve_executable(candidate)
            if resolved:
                return resolved
            path = Path(candidate).expanduser()
            if path.is_file():
                return str(path.resolve())
        return None

    def _antigravity_runtime_executable(self) -> str:
        """Prefer the original console-subsystem binary on Windows.

        ``agy.exe`` is intentionally GUI-subsystem on this desktop build so the
        CLI itself does not flash a console window.  That also means commands
        spawned by Antigravity have no console to inherit and Windows may create
        a visible terminal for cmd/pwsh/python.  Running the preserved console
        binary inside one hidden console keeps the entire child process tree
        attached to that hidden console instead.
        """
        executable = str(self.antigravity_executable or "").strip()
        if os.name != "nt" or not executable:
            return executable
        path = Path(executable)
        if path.name.lower() != "agy.exe":
            return executable
        console_binary = path.with_name("agy_real.exe")
        if console_binary.is_file():
            return str(console_binary)
        return executable

    def _launch_window_options(self, executable: str) -> tuple[int, subprocess.STARTUPINFO | None]:
        """Return Windows flags that keep the whole Antigravity terminal tree hidden."""
        if os.name != "nt":
            return 0, None
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 1)
        startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        if self.transport == "antigravity" and Path(executable).name.lower() == "agy_real.exe":
            # Keep one real console attached to Antigravity and all of its
            # cmd/pwsh/python children, but never show that console on desktop.
            return getattr(subprocess, "CREATE_NEW_CONSOLE", 0), startupinfo
        return getattr(subprocess, "CREATE_NO_WINDOW", 0), startupinfo

    @property
    def available(self) -> bool:
        if self.transport == "antigravity":
            return bool(self.auth_status().get("ready"))
        return bool(resolve_executable(str(self.executable)))

    def _subprocess_env(self, overrides: dict[str, str] | None = None) -> dict[str, str]:
        env = scrub_source_secret_env(os.environ.copy())
        if overrides:
            env.update(overrides)
        return env

    @property
    def web2api_url(self) -> str:
        return str(os.getenv("COFI_GEMINI_WEB2API_URL") or self.DEFAULT_WEB2API_URL).rstrip("/")

    @property
    def web2api_model(self) -> str:
        return str(os.getenv("COFI_GEMINI_WEB2API_MODEL") or self.DEFAULT_WEB2API_MODEL).strip()

    def web2api_status(self, timeout: float = 0.35) -> dict[str, object]:
        url = self.web2api_url
        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            with socket.create_connection((host, port), timeout=timeout):
                pass
        except OSError as exc:
            return {
                "ok": False,
                "url": url,
                "model": self.web2api_model,
                "error": str(exc),
            }
        return {"ok": True, "url": url, "model": self.web2api_model}

    @property
    def plan_available(self) -> bool:
        # Gemini CLI (Antigravity CLI) is the default engine for PLAN.
        # Falls back to web2api only when CLI is unavailable.
        return bool(self.available) or bool(self.web2api_status().get("ok"))

    @staticmethod
    def _atomic_write_text(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        pending = path.with_name(f".{path.name}.tmp")
        pending.write_text(text, encoding="utf-8")
        pending.replace(path)

    @staticmethod
    def _decode_json_object(content: str) -> dict:
        text = str(content or "").strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
            if text.lower().startswith("json"):
                text = text[4:].lstrip()
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end <= start:
                raise RuntimeError("Gemini web2api did not return a JSON object")
            try:
                value = json.loads(text[start:end + 1])
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Gemini web2api returned invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise RuntimeError("Gemini web2api response must be a JSON object")
        return value

    @classmethod
    def _validate_plan_package(cls, package: dict) -> tuple[str, str, dict]:
        research = str(package.get("research_md") or "").strip()
        script = str(package.get("script_md") or "").strip()
        visual = package.get("visual_manifest")
        if not research:
            raise RuntimeError("Gemini PLAN package is missing research_md")
        if not script:
            raise RuntimeError("Gemini PLAN package is missing script_md")
        if not isinstance(visual, dict):
            raise RuntimeError("Gemini PLAN package is missing visual_manifest")
        try:
            target_duration = float(visual.get("target_duration_sec"))
        except (TypeError, ValueError) as exc:
            raise RuntimeError("visual_manifest.target_duration_sec is invalid") from exc
        if target_duration <= 0:
            raise RuntimeError("visual_manifest.target_duration_sec must be positive")
        beats = visual.get("beats")
        if not isinstance(beats, list) or not beats:
            raise RuntimeError("visual_manifest.beats must be a non-empty array")
        seen: set[str] = set()
        for index, beat in enumerate(beats, start=1):
            if not isinstance(beat, dict):
                raise RuntimeError(f"visual_manifest beat {index} must be an object")
            missing = [field for field in cls.PLAN_FIELDS if field not in beat]
            if missing:
                raise RuntimeError(f"visual_manifest beat {index} is missing: {', '.join(missing)}")
            beat_id = str(beat.get("beat_id") or "").strip()
            if not beat_id:
                raise RuntimeError(f"visual_manifest beat {index} has an empty beat_id")
            if beat_id in seen:
                raise RuntimeError(f"visual_manifest contains duplicate beat_id: {beat_id}")
            seen.add(beat_id)
            if not isinstance(beat.get("footage_search_queries"), list):
                raise RuntimeError(f"visual_manifest {beat_id} footage_search_queries must be an array")
            if not isinstance(beat.get("factual_source_refs"), list):
                raise RuntimeError(f"visual_manifest {beat_id} factual_source_refs must be an array")
        return research, script, visual

    def _web2api_plan_prompt(self, job: dict, workspace: Path) -> str:
        base = build_phase_prompt(job, "plan", workspace, workspace)
        return base + """

DIRECT WEB2API TRANSPORT OVERRIDE
You do not have filesystem tools in this request. Do not claim that you wrote files.
Return ONLY one valid JSON object, with no markdown fences and no commentary, using exactly this top-level shape:
{
  "research_md": "complete contents for research.md",
  "script_md": "complete narration-only contents for script.md",
  "visual_manifest": {"target_duration_sec": 300, "beats": []}
}
The visual_manifest object must satisfy every PLAN requirement above, including the full ordered timeline, stable unique beat_id values and every required beat field.
"""

    def run_plan_web2api(
        self,
        job: dict,
        workspace: str | Path,
        log_callback: Callable[[str], None] | None = None,
    ) -> StageResult:
        workspace = Path(workspace).resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        meta_dir = workspace / ".producer" / "plan"
        meta_dir.mkdir(parents=True, exist_ok=True)
        prompt = self._web2api_plan_prompt(job, workspace)
        self._atomic_write_text(meta_dir / "prompt.txt", prompt)
        timeout = float(os.getenv("COFI_GEMINI_WEB2API_TIMEOUT_SEC") or 300)
        url = f"{self.web2api_url}/v1/chat/completions"
        if log_callback:
            log_callback(f"Gemini web2api PLAN: {self.web2api_model}")
        request_kwargs: dict[str, Any] = {
            "json": {
                "model": self.web2api_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.35,
            },
            "timeout": timeout,
        }
        api_key = str(os.getenv("COFI_GEMINI_WEB2API_KEY") or "").strip()
        if api_key:
            request_kwargs["headers"] = {"Authorization": f"Bearer {api_key}"}
        try:
            response = requests.post(url, **request_kwargs)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise RuntimeError(f"Gemini web2api PLAN request failed: {exc}") from exc
        except ValueError as exc:
            raise RuntimeError("Gemini web2api PLAN returned a non-JSON HTTP response") from exc
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Gemini web2api PLAN response is missing choices[0].message.content") from exc
        package = self._decode_json_object(str(content or ""))
        research, script, visual = self._validate_plan_package(package)
        self._atomic_write_text(workspace / "research.md", research + "\n")
        self._atomic_write_text(workspace / "script.md", script + "\n")
        self._atomic_write_text(
            workspace / "visual_manifest.json",
            json.dumps(visual, ensure_ascii=False, indent=2) + "\n",
        )
        event = {
            "engine": "gemini-web2api",
            "model": self.web2api_model,
            "status": "completed",
            "beats": len(visual.get("beats") or []),
        }
        log_path = meta_dir / "events.jsonl"
        self._atomic_write_text(log_path, json.dumps(event, ensure_ascii=False) + "\n")
        message = f"Gemini web2api wrote PLAN artifacts ({event['beats']} beats)."
        self._atomic_write_text(meta_dir / "last_message.txt", message)
        if log_callback:
            log_callback(message)
        return StageResult(returncode=0, last_message=message, log_path=log_path)

    def auth_status(self) -> dict[str, object]:
        if self.transport == "antigravity":
            return self._antigravity_auth_status()

        selected_type = ""
        settings_path = Path.home() / ".gemini" / "settings.json"
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            selected_type = str(settings.get("security", {}).get("auth", {}).get("selectedType") or "")
        except (OSError, ValueError, TypeError):
            pass

        if os.getenv("GEMINI_API_KEY"):
            return {"ready": True, "auth_method": "gemini-api-key", "action": ""}

        vertex = str(os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "")).strip().lower() in {"1", "true", "yes", "on"}
        if vertex:
            return {"ready": True, "auth_method": "vertex-ai", "action": ""}

        gca = str(os.getenv("GOOGLE_GENAI_USE_GCA", "")).strip().lower() in {"1", "true", "yes", "on"}
        if gca:
            return {"ready": True, "auth_method": "code-assist", "action": ""}

        if selected_type == "oauth-personal":
            return {
                "ready": False,
                "auth_method": selected_type,
                "reason_code": "UNSUPPORTED_CLIENT",
                "action": "Gemini CLI OAuth cá nhân đang bị Google từ chối với UNSUPPORTED_CLIENT. Hãy dùng Antigravity CLI (agy) với cùng tài khoản Google/Ultra.",
            }

        return {
            "ready": False,
            "auth_method": selected_type,
            "action": "Cài hoặc đăng nhập Antigravity CLI (agy) bằng tài khoản Google/Ultra.",
        }

    def _antigravity_auth_status(self) -> dict[str, object]:
        now = time.monotonic()
        if (
            self._antigravity_probe_cache is not None
            and now - self._antigravity_probe_at < self.ANTIGRAVITY_PROBE_TTL_SEC
        ):
            return dict(self._antigravity_probe_cache)

        with self._probe_lock:
            now = time.monotonic()
            if (
                self._antigravity_probe_cache is not None
                and now - self._antigravity_probe_at < self.ANTIGRAVITY_PROBE_TTL_SEC
            ):
                return dict(self._antigravity_probe_cache)

            executable = self._antigravity_runtime_executable()
            if not executable:
                status = {
                    "ready": False,
                    "auth_method": "antigravity-cli",
                    "reason_code": "ANTIGRAVITY_NOT_FOUND",
                    "action": "Cài Antigravity CLI (agy) và đăng nhập bằng tài khoản Google/Ultra.",
                }
            else:
                try:
                    command = [executable, "models"]
                    shell = executable.lower().endswith((".cmd", ".bat"))
                    launch = subprocess.list2cmdline(command) if shell else command
                    creationflags, startupinfo = self._launch_window_options(executable)
                    result = subprocess.run(
                        launch,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=25,
                        env=self._subprocess_env(),
                        shell=shell,
                        creationflags=creationflags,
                        startupinfo=startupinfo,
                    )
                    if result.returncode == 0 and str(result.stdout or "").strip():
                        models: list[dict[str, str]] = []
                        for line in str(result.stdout or "").splitlines():
                            model_id, separator, label = line.strip().partition("\t")
                            if not separator or not model_id:
                                continue
                            models.append({"id": model_id.strip(), "label": label.strip() or model_id.strip()})
                        status = {
                            "ready": True,
                            "auth_method": "antigravity-cli",
                            "action": "",
                            "models": models,
                            "selected_model": self.default_model,
                        }
                    else:
                        status = {
                            "ready": False,
                            "auth_method": "antigravity-cli",
                            "reason_code": "ANTIGRAVITY_AUTH_FAILED",
                            "action": "Mở Antigravity và đăng nhập lại tài khoản Google/Ultra, rồi thử lại.",
                        }
                except (OSError, subprocess.SubprocessError):
                    status = {
                        "ready": False,
                        "auth_method": "antigravity-cli",
                        "reason_code": "ANTIGRAVITY_AUTH_FAILED",
                        "action": "Mở Antigravity và đăng nhập lại tài khoản Google/Ultra, rồi thử lại.",
                    }

            self._antigravity_probe_cache = dict(status)
            # Only cache successful probes for full TTL; retry failures quickly (2s)
            self._antigravity_probe_at = now if status.get("ready") else now - (self.ANTIGRAVITY_PROBE_TTL_SEC - 2.0)
            return status

    def command_for(
        self,
        workspace: str | Path,
        model: str | None = None,
        conversation_id: str | None = None,
        effort: str | None = None,
        json_schema: dict | None = None,
        print_timeout: str | None = None,
    ) -> list[str]:
        selected_model = str(self.default_model if model is None else model).strip()
        if self.transport == "antigravity":
            command = [
                self._antigravity_runtime_executable(),
                "--dangerously-skip-permissions",
                "--input-format", "text",
                "--output-format", "stream-json",
            ]
            if selected_model:
                command.extend(["--model", selected_model])
            if effort in {"low", "medium", "high"}:
                command.extend(["--effort", effort])
            if json_schema is not None:
                command.extend(["--json-schema", json.dumps(json_schema, ensure_ascii=False)])
            if print_timeout:
                command.extend(["--print-timeout", print_timeout])
            if conversation_id:
                command.extend(["--conversation", str(conversation_id)])
            return command

        command = [
            str(self.executable),
            "--skip-trust",
            "--approval-mode", "yolo",
            "--output-format", "stream-json",
        ]
        if selected_model:
            command.extend(["-m", selected_model])
        command.extend(["-p", ""])
        return command

    @staticmethod
    def _stream_last_message(lines: list[str]) -> str:
        """Return only the assistant's final response from stream-json output.

        Antigravity emits transport events such as init/step_update/result. Those
        events are useful in events.jsonl, but they must never become the chat
        reply shown to the user. Prefer the final result.response and fall back
        to the raw tail only when the stream format is unknown.
        """
        for raw_line in reversed(lines):
            line = str(raw_line or "").strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue

            event = str(payload.get("event") or payload.get("type") or "").strip().lower()
            if event == "result":
                result = payload.get("result")
                if isinstance(result, dict):
                    response = result.get("response")
                    if isinstance(response, str) and response.strip():
                        return response.strip()
                    error = result.get("error")
                    if isinstance(error, str) and error.strip():
                        return f"Lỗi dịch vụ AI: {error.strip()}"
                elif isinstance(result, str) and result.strip():
                    return result.strip()

            response = payload.get("response")
            if isinstance(response, str) and response.strip():
                return response.strip()

        return "\n".join(str(line or "").rstrip("\r\n") for line in lines[-80:]).strip()

    def run_prompt(
        self,
        prompt: str,
        workspace: str | Path,
        label: str,
        log_callback: Callable[[str], None] | None = None,
        model: str | None = None,
        env_overrides: dict[str, str] | None = None,
        image_paths: list[str | Path] | None = None,
        conversation_id: str | None = None,
        effort: str | None = None,
        json_schema: dict | None = None,
        print_timeout: str | None = None,
    ) -> StageResult:
        workspace = Path(workspace).resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        meta_dir = workspace / ".producer" / label
        meta_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = meta_dir / "prompt.txt"
        log_path = meta_dir / "events.jsonl"
        last_path = meta_dir / "last_message.txt"
        resolved_images: list[Path] = []
        for value in image_paths or []:
            path = Path(value).resolve()
            if path.exists() and path.is_file():
                resolved_images.append(path)
        if resolved_images:
            prompt += (
                "\n\nLOCAL MEDIA ATTACHMENTS FOR VISUAL REVIEW:\n"
                + "\n".join(f"- {path}" for path in resolved_images)
                + "\nOpen and inspect these exact local image/frame files before deciding. Do not judge only from filenames or metadata."
            )
        prompt_path.write_text(prompt, encoding="utf-8")
        command = self.command_for(
            workspace, model=model, conversation_id=conversation_id,
            effort=effort, json_schema=json_schema, print_timeout=print_timeout,
        )
        if self.transport == "antigravity" and resolved_images:
            parents: list[str] = []
            for path in resolved_images:
                parent = str(path.parent)
                if parent.lower() not in {item.lower() for item in parents}:
                    parents.append(parent)
            for parent in parents:
                command.extend(["--add-dir", parent])
        shell = str(command[0]).lower().endswith((".cmd", ".bat"))
        launch = subprocess.list2cmdline(command) if shell else command
        creationflags, startupinfo = self._launch_window_options(str(command[0]))
        process = subprocess.Popen(
            launch,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(workspace),
            shell=shell,
            env=self._subprocess_env(env_overrides),
            creationflags=creationflags,
            startupinfo=startupinfo,
        )
        assert process.stdin is not None
        assert process.stdout is not None
        process.stdin.write(prompt)
        process.stdin.close()
        tail: list[str] = []
        saw_result_event = False
        with log_path.open("w", encoding="utf-8") as handle:
            for line in process.stdout:
                handle.write(line)
                handle.flush()
                stripped = line.rstrip("\r\n")
                tail.append(stripped)
                tail = tail[-80:]
                if log_callback:
                    log_callback(stripped)
                if '"event":"result"' in stripped.replace(" ", "") or '"type":"result"' in stripped.replace(" ", ""):
                    try:
                        evt = json.loads(stripped)
                        if isinstance(evt, dict) and str(evt.get("event") or evt.get("type") or "").strip().lower() == "result":
                            saw_result_event = True
                            break
                    except json.JSONDecodeError:
                        pass
        try:
            returncode = process.wait(timeout=5 if saw_result_event else None)
        except subprocess.TimeoutExpired:
            if os.name == "nt" and process.pid:
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=5,
                        creationflags=creationflags,
                    )
                except Exception:
                    pass
            try:
                process.terminate()
                returncode = process.wait(timeout=3)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
                returncode = 0 if saw_result_event else 1
        if saw_result_event and returncode != 0:
            returncode = 0
        last_message = self._stream_last_message(tail)
        last_path.write_text(last_message, encoding="utf-8")
        return StageResult(returncode=returncode, last_message=last_message, log_path=log_path)

    @staticmethod
    def _conversation_id_from_log(log_path: str | Path) -> str:
        path = Path(log_path)
        if not path.exists():
            return ""
        for raw_line in reversed(path.read_text(encoding="utf-8", errors="replace").splitlines()):
            try:
                payload = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            candidates = [payload.get("conversation_id")]
            for key in ("init", "result", "step_update"):
                nested = payload.get(key)
                if isinstance(nested, dict):
                    candidates.append(nested.get("conversation_id"))
            for candidate in candidates:
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
        return ""

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

    @staticmethod
    def _input_tokens_from_log(log_path: str | Path) -> int:
        path = Path(log_path)
        if not path.exists():
            return 0
        for raw_line in reversed(path.read_text(encoding="utf-8", errors="replace").splitlines()):
            try:
                payload = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            result = payload.get("result") if isinstance(payload, dict) else None
            usage = result.get("usage") if isinstance(result, dict) else None
            if isinstance(usage, dict):
                try:
                    return max(
                        0,
                        int(usage.get("input_tokens") or 0) + int(usage.get("cache_read_tokens") or 0),
                    )
                except (TypeError, ValueError):
                    return 0
        return 0

    @staticmethod
    def _build_local_fallback_handoff(workspace: Path, meta_dir: Path, session: dict[str, object]) -> str:
        parts: list[str] = []
        previous = meta_dir / "handoff_summary.txt"
        if previous.exists():
            try:
                prev_text = previous.read_text(encoding="utf-8", errors="replace").strip()
                if prev_text:
                    parts.append(prev_text[-3000:])
            except OSError:
                pass
        last_excerpt = str(session.get("last_response_excerpt") or "").strip()
        if last_excerpt:
            parts.append(f"Kết quả gần nhất của session trước:\n{last_excerpt[-2000:]}")
        for hist_candidate in (
            workspace / "producer_chat_history.jsonl",
            workspace / "data" / "producer_chat_history.jsonl",
        ):
            if hist_candidate.exists():
                try:
                    lines = hist_candidate.read_text(encoding="utf-8", errors="replace").splitlines()[-8:]
                    recent_turns: list[str] = []
                    for line in lines:
                        item = json.loads(line)
                        if isinstance(item, dict) and item.get("role") in {"user", "assistant"}:
                            role_label = "Người dùng" if item["role"] == "user" else "AI"
                            recent_turns.append(f"- {role_label}: {str(item.get('content') or '').strip()[:400]}")
                    if recent_turns:
                        parts.append("Lịch sử hội thoại gần nhất:\n" + "\n".join(recent_turns))
                        break
                except (OSError, json.JSONDecodeError):
                    continue
        summary = "\n\n".join(parts).strip()
        if not summary:
            summary = (
                f"Tiếp tục công việc từ session Gemini trước ({session.get('conversation_id') or 'auto'}, "
                f"{session.get('turn_count') or 1} lượt). Kiểm tra trạng thái workspace trước khi thực hiện bước tiếp theo."
            )
        return summary[:6000]

    def reset_reusable_session(self, workspace: str | Path, label: str, reason: str = "manual_reset") -> bool:
        workspace = Path(workspace).resolve()
        meta_dir = workspace / ".producer" / label
        session_path = meta_dir / "gemini_session.json"
        with self._lock_for_session(meta_dir):
            if not session_path.exists():
                return False
            try:
                loaded = json.loads(session_path.read_text(encoding="utf-8"))
                session = loaded if isinstance(loaded, dict) else {}
            except (OSError, json.JSONDecodeError):
                session = {}
            cid = str(session.get("conversation_id") or "").strip()
            try:
                session_path.unlink(missing_ok=True)
            except OSError:
                pass
            if cid:
                meta_dir.mkdir(parents=True, exist_ok=True)
                with (meta_dir / "retired_sessions.jsonl").open("a", encoding="utf-8") as handle:
                    handle.write(
                        json.dumps(
                            {
                                "conversation_id": cid,
                                "turn_count": session.get("turn_count"),
                                "reason": reason,
                                "at": time.time(),
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
            return True

    @staticmethod
    def _positive_limit(name: str, default: int) -> int:
        try:
            return max(1, int(os.getenv(name) or default))
        except (TypeError, ValueError):
            return default

    def _should_rotate_session(self, session: dict[str, object], next_prompt: str) -> bool:
        turns = int(session.get("turn_count") or 0)
        try:
            max_turns = max(0, int(os.getenv("COFI_GEMINI_SESSION_MAX_TURNS") or self.DEFAULT_SESSION_MAX_TURNS))
        except (TypeError, ValueError):
            max_turns = self.DEFAULT_SESSION_MAX_TURNS
        if max_turns and turns >= max_turns:
            return True
        # Sessions saved by older app versions did not track context size.
        if turns >= 3 and "prompt_chars_total" not in session:
            return True
        chars = int(session.get("prompt_chars_total") or 0) + len(next_prompt)
        if chars >= self._positive_limit("COFI_GEMINI_SESSION_MAX_PROMPT_CHARS", self.DEFAULT_SESSION_MAX_PROMPT_CHARS):
            return True
        tokens = int(session.get("input_tokens") or 0)
        estimate = max(1, len(next_prompt) // 3)
        return bool(tokens and tokens + estimate >= self._positive_limit(
            "COFI_GEMINI_SESSION_MAX_INPUT_TOKENS", self.DEFAULT_SESSION_MAX_INPUT_TOKENS
        ))

    def run_prompt_reusable(
        self,
        prompt: str,
        workspace: str | Path,
        label: str,
        *,
        continuation_prompt: str | None = None,
        **kwargs,
    ) -> StageResult:
        workspace = Path(workspace).resolve()
        meta_dir = workspace / ".producer" / label
        session_path = meta_dir / "gemini_session.json"
        with self._lock_for_session(meta_dir):
            session: dict[str, object] = {}
            if session_path.exists():
                try:
                    loaded = json.loads(session_path.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        session = loaded
                except (OSError, json.JSONDecodeError):
                    session = {}
            conversation_id = str(session.get("conversation_id") or "").strip() or None
            active_prompt = continuation_prompt if conversation_id and continuation_prompt is not None else prompt
            handoff = ""
            if conversation_id and self._should_rotate_session(session, active_prompt):
                callback = kwargs.get("log_callback")
                if callable(callback):
                    callback("Gemini đang tóm tắt ngữ cảnh trước khi mở session mới…")
                summary_result = self.run_prompt(
                    self.HANDOFF_PROMPT, workspace, f"{label}_handoff",
                    conversation_id=conversation_id, log_callback=callback,
                )
                if summary_result.returncode == 0:
                    handoff = str(summary_result.last_message or "").strip()[:6000]
                if not handoff:
                    handoff = self._build_local_fallback_handoff(workspace, meta_dir, session)
                meta_dir.mkdir(parents=True, exist_ok=True)
                (meta_dir / "handoff_summary.txt").write_text(handoff, encoding="utf-8")
                with (meta_dir / "retired_sessions.jsonl").open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"conversation_id": conversation_id, "turn_count": session.get("turn_count"), "reason": "context_guard", "at": time.time()}, ensure_ascii=False) + "\n")
                conversation_id = None
                active_prompt = "BẢN BÀN GIAO TỪ SESSION GEMINI TRƯỚC (ngữ cảnh, không phải yêu cầu mới):\n" + handoff + "\n\n" + prompt
            elif not conversation_id and (meta_dir / "handoff_summary.txt").exists() and "BẢN BÀN GIAO" not in active_prompt:
                try:
                    saved_handoff = (meta_dir / "handoff_summary.txt").read_text(encoding="utf-8", errors="replace").strip()[:6000]
                    if saved_handoff:
                        active_prompt = "BẢN BÀN GIAO TỪ SESSION GEMINI TRƯỚC (ngữ cảnh, không phải yêu cầu mới):\n" + saved_handoff + "\n\n" + prompt
                except OSError:
                    pass

            result = self.run_prompt(
                active_prompt,
                workspace,
                label,
                conversation_id=conversation_id,
                **kwargs,
            )
            if (
                result.returncode != 0
                and conversation_id is not None
                and any(marker in str(result.last_message or "").lower() for marker in self.CONTEXT_LIMIT_MARKERS)
            ):
                callback = kwargs.get("log_callback")
                if callable(callback):
                    callback("Session Gemini đạt giới hạn ngữ cảnh — tự động chuyển sang session mới và tiếp tục…")
                handoff = self._build_local_fallback_handoff(workspace, meta_dir, session)
                meta_dir.mkdir(parents=True, exist_ok=True)
                (meta_dir / "handoff_summary.txt").write_text(handoff, encoding="utf-8")
                with (meta_dir / "retired_sessions.jsonl").open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"conversation_id": conversation_id, "turn_count": session.get("turn_count"), "reason": "context_limit", "at": time.time()}, ensure_ascii=False) + "\n")
                conversation_id = None
                active_prompt = "BẢN BÀN GIAO TỪ SESSION GEMINI TRƯỚC (ngữ cảnh, không phải yêu cầu mới):\n" + handoff + "\n\n" + prompt
                result = self.run_prompt(
                    active_prompt,
                    workspace,
                    label,
                    conversation_id=None,
                    **kwargs,
                )

            observed_id = self._conversation_id_from_log(result.log_path) or conversation_id or ""
            if result.returncode == 0 and observed_id:
                meta_dir.mkdir(parents=True, exist_ok=True)
                updated = {
                    "conversation_id": observed_id,
                    "turn_count": (int(session.get("turn_count") or 0) + 1) if conversation_id else 1,
                    "prompt_chars_total": (int(session.get("prompt_chars_total") or 0) + len(active_prompt)) if conversation_id else len(active_prompt),
                    "input_tokens": self._input_tokens_from_log(result.log_path),
                    "last_response_excerpt": str(result.last_message or "").strip()[-1200:],
                    "updated_at": time.time(),
                }
                temporary = session_path.with_suffix(".tmp")
                temporary.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
                temporary.replace(session_path)
            return result

    def run(self, job: dict, phase: str, workspace: str | Path, log_callback=None) -> StageResult:
        prompt = build_phase_prompt(job, phase, workspace, Path(workspace))
        if self.available:
            return self.run_prompt(prompt, workspace, phase, log_callback)
        if phase == "plan" and self.web2api_status().get("ok"):
            if log_callback:
                log_callback("Gemini CLI không sẵn sàng, thử dự phòng web2api...")
            return self.run_plan_web2api(job, workspace, log_callback)
        raise RuntimeError("Gemini PLAN is unavailable: Antigravity CLI is not authenticated and web2api is offline")
