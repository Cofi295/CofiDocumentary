# Source Repair Agent Design

## Goal

Allow the Cofi Producer chatbot to hand a reported application/code failure to either Codex CLI or Gemini CLI with full read, write, command, and test access inside `B:\ALL_TOOLS\CofiDocumentary`, then report a durable terminal result based on an independent test run.

## Design

`SourceRepairAgent` owns repair jobs under `.producer/source_repairs`. A job is queued from the existing `repair_code` producer action and runs on a background thread so the HTTP chat request returns promptly. The agent chooses the requested provider or falls back from Codex to Gemini when `provider=auto` and the first provider cannot run.

Each CLI receives the exact project root, failure evidence, and instructions to diagnose, edit, and test the application. Codex runs with its full-access noninteractive flags; Gemini runs in headless YOLO mode. The controller captures stdout, stderr, command, timestamps, provider attempts, and the final independent verification result. A repair reaches `fixed` only when the provider exits successfully and the configured verification command exits zero. All other terminal paths are `failed`.

The API exposes list/detail endpoints for polling. The producer action returns the queued job and never claims that a repair is complete before the durable job reaches a terminal state.

## Constraints

- Filesystem mutation is restricted to the configured CofiDocumentary project root by the prompt and working directory.
- The default verification is the repository test suite; it can be overridden with `COFI_REPAIR_TEST_COMMAND`.
- At most one worker thread is created per repair ID.
- Every attempt and test output is persisted for diagnosis.
- The existing app process is not restarted by a repair worker because replacing the process serving the repair API would lose in-memory coordination; a repaired app can be restarted explicitly after a fixed result.

