from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Callable

from .codex_gateway import StageResult
from .prompts import build_phase_prompt


class FailoverGateway:
    """Codex-first gateway that keeps work moving through Gemini when needed."""

    def __init__(
        self,
        codex_gateway: Any,
        gemini_gateway: Any,
        *,
        remotion_dir: str | Path,
        enabled: bool = True,
    ) -> None:
        self.codex_gateway = codex_gateway
        self.gemini_gateway = gemini_gateway
        self.remotion_dir = Path(remotion_dir).resolve()
        self.enabled = bool(enabled)
        self.preferred_provider = "codex"
        self.active_provider = "codex"
        self.last_switch: dict[str, Any] | None = None
        self._lock = RLock()

    @property
    def executable(self) -> str:
        active = self._gateway(self.active_provider)
        return str(getattr(active, "executable", self.active_provider))

    @property
    def available(self) -> bool:
        if not self.enabled:
            return self._provider_ready(self.preferred_provider)
        return self._provider_ready("codex") or self._provider_ready("gemini")

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "enabled": self.enabled,
                "preferred_provider": self.preferred_provider,
                "active_provider": self.active_provider,
                "order": [self.active_provider, self._other(self.active_provider)] if self.enabled else [self.preferred_provider],
                "last_switch": dict(self.last_switch) if self.last_switch else None,
            }

    def run(
        self,
        job: dict,
        phase: str,
        workspace: str | Path,
        log_callback: Callable[[str], None] | None = None,
    ) -> StageResult:
        workspace_path = Path(workspace).resolve()
        prompt = build_phase_prompt(job, phase, workspace_path, self.remotion_dir)
        with self._lock:
            first = self.active_provider if self.enabled else self.preferred_provider
        providers = [first]
        if self.enabled:
            providers.append(self._other(first))

        previous_failure: StageResult | None = None
        for index, provider in enumerate(providers):
            if not self._provider_ready(provider):
                previous_failure = self._unavailable_result(workspace_path, phase, provider)
                continue

            if index == 0:
                gateway = self._gateway(provider)
                runner = getattr(gateway, "run", None)
                if callable(runner):
                    try:
                        result = runner(job, phase, workspace_path, log_callback=log_callback)
                    except Exception as exc:
                        result = StageResult(
                            1,
                            f"{provider} failed: {type(exc).__name__}: {exc}",
                            workspace_path / ".producer" / phase / f"{provider}_failover_error.log",
                        )
                else:
                    result = self._call_provider(
                        provider,
                        prompt,
                        workspace_path,
                        phase,
                        reusable=True,
                        log_callback=log_callback,
                        use_remotion_root=phase in {"edit", "qc"},
                        image_paths=None,
                    )
            else:
                handoff = self._handoff_prompt(
                    prompt,
                    workspace_path,
                    phase,
                    failed_provider=providers[index - 1],
                    failure=previous_failure or self._unavailable_result(workspace_path, phase, providers[index - 1]),
                    image_paths=None,
                )
                result = self._call_provider(
                    provider,
                    handoff,
                    workspace_path,
                    phase,
                    reusable=True,
                    log_callback=log_callback,
                    use_remotion_root=phase in {"edit", "qc"},
                    image_paths=None,
                )

            if result.returncode == 0:
                if provider != first:
                    self._record_switch(first, provider, previous_failure, workspace_path, phase)
                else:
                    with self._lock:
                        self.active_provider = provider
                return result
            if result.returncode == 130:
                return result
            previous_failure = result

        return previous_failure or self._unavailable_result(workspace_path, phase, first)

    def run_prompt(
        self,
        prompt: str,
        workspace: str | Path,
        label: str,
        log_callback: Callable[[str], None] | None = None,
        use_remotion_root: bool = False,
        reuse_session: bool = False,
        image_paths: list[str | Path] | None = None,
        **_: Any,
    ) -> StageResult:
        return self._run_with_failover(
            prompt,
            workspace,
            label,
            reusable=bool(reuse_session),
            log_callback=log_callback,
            use_remotion_root=use_remotion_root,
            image_paths=image_paths,
        )

    def run_prompt_reusable(
        self,
        prompt: str,
        workspace: str | Path,
        label: str,
        log_callback: Callable[[str], None] | None = None,
        use_remotion_root: bool = False,
        image_paths: list[str | Path] | None = None,
        **_: Any,
    ) -> StageResult:
        return self._run_with_failover(
            prompt,
            workspace,
            label,
            reusable=True,
            log_callback=log_callback,
            use_remotion_root=use_remotion_root,
            image_paths=image_paths,
        )

    def reset_reusable_session(self, workspace: str | Path, label: str, reason: str = "manual_reset") -> bool:
        resetter = getattr(self.codex_gateway, "reset_reusable_session", None)
        reset = bool(resetter(workspace, label, reason)) if callable(resetter) else False
        with self._lock:
            self.active_provider = self.preferred_provider
            self.last_switch = None
        return reset

    def _run_with_failover(
        self,
        prompt: str,
        workspace: str | Path,
        label: str,
        *,
        reusable: bool,
        log_callback: Callable[[str], None] | None,
        use_remotion_root: bool,
        image_paths: list[str | Path] | None,
    ) -> StageResult:
        workspace_path = Path(workspace).resolve()
        with self._lock:
            first = self.active_provider if self.enabled else self.preferred_provider
        providers = [first]
        if self.enabled:
            providers.append(self._other(first))

        previous_failure: StageResult | None = None
        for index, provider in enumerate(providers):
            if not self._provider_ready(provider):
                previous_failure = self._unavailable_result(workspace_path, label, provider)
                continue

            current_prompt = prompt
            if index > 0 and previous_failure is not None:
                current_prompt = self._handoff_prompt(
                    prompt,
                    workspace_path,
                    label,
                    failed_provider=providers[index - 1],
                    failure=previous_failure,
                    image_paths=image_paths,
                )

            result = self._call_provider(
                provider,
                current_prompt,
                workspace_path,
                label,
                reusable=reusable,
                log_callback=log_callback,
                use_remotion_root=use_remotion_root,
                image_paths=image_paths,
            )
            if result.returncode == 0:
                if provider != first:
                    self._record_switch(first, provider, previous_failure, workspace_path, label)
                else:
                    with self._lock:
                        self.active_provider = provider
                return result
            if result.returncode == 130:
                return result
            previous_failure = result

        return previous_failure or self._unavailable_result(workspace_path, label, first)

    def _call_provider(
        self,
        provider: str,
        prompt: str,
        workspace: Path,
        label: str,
        *,
        reusable: bool,
        log_callback: Callable[[str], None] | None,
        use_remotion_root: bool,
        image_paths: list[str | Path] | None,
    ) -> StageResult:
        if (workspace / ".producer" / "stop_phase.json").is_file():
            return StageResult(
                returncode=130,
                last_message="Đã dừng bước sản xuất theo yêu cầu (stop_phase).",
                log_path=workspace / ".producer" / label,
            )
        gateway = self._gateway(provider)
        try:
            if provider == "codex":
                kwargs: dict[str, Any] = {"use_remotion_root": use_remotion_root}
                if log_callback is not None:
                    kwargs["log_callback"] = log_callback
                if image_paths:
                    kwargs["image_paths"] = image_paths
                if reusable:
                    runner = getattr(gateway, "run_prompt_reusable", None)
                    if callable(runner):
                        return runner(prompt, workspace, label, **kwargs)
                return gateway.run_prompt(prompt, workspace, label, **kwargs)

            gemini_kwargs: dict[str, Any] = {}
            if log_callback is not None:
                gemini_kwargs["log_callback"] = log_callback
            if image_paths:
                gemini_kwargs["image_paths"] = image_paths
            if reusable:
                runner = getattr(gateway, "run_prompt_reusable", None)
                if callable(runner):
                    return runner(prompt, workspace, label, **gemini_kwargs)
            return gateway.run_prompt(prompt, workspace, label, **gemini_kwargs)
        except Exception as exc:
            return StageResult(
                returncode=1,
                last_message=f"{provider} failed: {type(exc).__name__}: {exc}",
                log_path=workspace / ".producer" / label / f"{provider}_failover_error.log",
            )

    def _provider_ready(self, provider: str) -> bool:
        gateway = self._gateway(provider)
        if not bool(getattr(gateway, "available", True)):
            return False
        if provider == "gemini":
            auth_status = getattr(gateway, "auth_status", None)
            if callable(auth_status):
                try:
                    return bool(auth_status().get("ready"))
                except Exception:
                    return False
        return True

    def _handoff_prompt(
        self,
        prompt: str,
        workspace: Path,
        label: str,
        *,
        failed_provider: str,
        failure: StageResult,
        image_paths: list[str | Path] | None,
    ) -> str:
        artifacts = self._workspace_artifacts(workspace)
        attachments = ", ".join(str(Path(path).resolve()) for path in (image_paths or []))
        context = [
            "[COFI AUTO FAILOVER]",
            f"Engine trước ({failed_provider}) không thể hoàn thành: {str(failure.last_message or '').strip()[-1200:]}",
            f"Workspace hiện tại: {workspace}",
            f"Bước/label hiện tại: {label}",
            "Tiếp tục đúng công việc còn dở trên workspace/checkpoint hiện có; kiểm tra artifact trước khi làm.",
            "Không làm lại phần đã hoàn thành và không tạo lại checkpoint đã có.",
        ]
        if artifacts:
            context.append(f"Artifact/checkpoint đang có: {artifacts}")
        if attachments:
            context.append(f"File đính kèm cần giữ ngữ cảnh: {attachments}")
        context.extend(["", "Yêu cầu gốc cần tiếp tục:", prompt])
        return "\n".join(context)

    @staticmethod
    def _workspace_artifacts(workspace: Path) -> str:
        names: list[str] = []
        try:
            for path in workspace.iterdir():
                if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".srt", ".wav", ".mp3", ".mp4"}:
                    names.append(path.name)
        except OSError:
            return ""
        return ", ".join(sorted(names)[:40])

    def _record_switch(
        self,
        source: str,
        target: str,
        failure: StageResult | None,
        workspace: Path,
        label: str,
    ) -> None:
        with self._lock:
            self.active_provider = target
            self.last_switch = {
                "from": source,
                "to": target,
                "reason": str((failure.last_message if failure else "") or "provider unavailable")[-1200:],
                "at": datetime.now(timezone.utc).isoformat(),
                "workspace": str(workspace),
                "label": label,
            }

    def _unavailable_result(self, workspace: Path, label: str, provider: str) -> StageResult:
        return StageResult(
            returncode=1,
            last_message=f"{provider} unavailable or not authenticated",
            log_path=workspace / ".producer" / label / f"{provider}_unavailable.log",
        )

    def _gateway(self, provider: str) -> Any:
        return self.codex_gateway if provider == "codex" else self.gemini_gateway

    @staticmethod
    def _other(provider: str) -> str:
        return "gemini" if provider == "codex" else "codex"
