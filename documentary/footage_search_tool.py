from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .source_discovery import SourceDiscoveryHub, direct_tool_providers


_OUTPUT_FIELDS = (
    "provider", "source_url", "title", "description", "kind", "source_name", "date",
    "country", "rights_hint", "thumbnail_url", "duration", "discovery_score", "search_query",
    "semantic_score", "semantic_text_score", "visual_semantic_score", "semantic_provider",
)


def _compact_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        item: dict[str, Any] = {}
        for key in _OUTPUT_FIELDS:
            value = row.get(key)
            if value in (None, "", [], {}):
                continue
            if isinstance(value, str):
                value = value[:320]
            item[key] = value
        if item.get("source_url"):
            compact.append(item)
    return compact


def search_with_local_tools(
    query: str,
    *,
    workspace: str | Path,
    market: str = "",
    language: str = "",
    limit: int = 12,
    narration: str = "",
) -> dict[str, Any]:
    workspace_path = Path(workspace).resolve()
    # The local tool contract is per provider: every source engine may contribute
    # 2-3 of its best matches, instead of letting one provider fill the whole
    # shortlist.
    target = max(4, min(12, int(limit)))
    providers = direct_tool_providers()
    hub = SourceDiscoveryHub(
        providers=providers,
        max_workers=min(6, max(1, len(providers))),
        per_provider_limit=target,
        per_beat_limit=target * len(providers),
        shortlist_per_provider=target,
    )
    beat = {
        "beat_id": "LOCAL_TOOL",
        "visual_type": "sourced_video",
        "narration_text": narration,
        "footage_search_queries": [query],
    }
    job = {
        "title": query,
        "market": market,
        "language": language,
    }
    discovered = hub.discover_for_beats(job, [beat], workspace_path)
    return {
        "query": query,
        "candidates": _compact_candidates(discovered.get("LOCAL_TOOL") or []),
        "providers": hub.last_diagnostics,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Search footage with local repo-backed tools before model web research.",
    )
    parser.add_argument("--query", required=True)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--market", default="")
    parser.add_argument("--language", default="")
    parser.add_argument("--narration", default="")
    parser.add_argument("--limit", type=int, default=12, help="Kết quả tối đa trên mỗi provider")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    payload = search_with_local_tools(
        args.query,
        workspace=args.workspace,
        market=args.market,
        language=args.language,
        narration=args.narration,
        limit=args.limit,
    )
    print(json.dumps(
        payload,
        ensure_ascii=False,
        indent=2 if args.pretty else None,
        separators=None if args.pretty else (",", ":"),
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

