from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any, Callable, Protocol

import httpx

from .semantic_retrieval import OpenClipSemanticReranker


class SourceProvider(Protocol):
    name: str

    def search(self, query: str, *, job: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        ...


def _first(value: Any, default: Any = "") -> Any:
    if isinstance(value, list):
        return value[0] if value else default
    return default if value is None else value


def _text(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value if str(item).strip())
    if isinstance(value, dict):
        return " ".join(str(item) for item in value.values() if str(item).strip())
    return str(value or "")


def _default_http_client() -> httpx.Client:
    timeout = float(os.getenv("COFI_DISCOVERY_PROVIDER_TIMEOUT_SEC", "8") or 8)
    return httpx.Client(
        timeout=max(1.0, timeout),
        follow_redirects=True,
        headers={"User-Agent": "COFI-Documentary/1.0 footage-discovery"},
    )


class DDGSProvider:
    name = "ddgs"

    _REGIONS = {
        "US": "us-en", "GB": "uk-en", "UK": "uk-en", "VN": "vn-vi", "BR": "br-pt",
        "KR": "kr-kr", "JP": "jp-jp", "DE": "de-de", "FR": "fr-fr", "ES": "es-es",
        "IT": "it-it", "IN": "in-en", "ID": "id-id", "TH": "th-th", "AU": "au-en",
        "CA": "ca-en", "MX": "mx-es", "AR": "ar-es", "TR": "tr-tr", "PL": "pl-pl",
    }

    def __init__(self, searcher_factory: Callable[[], Any] | None = None):
        self.searcher_factory = searcher_factory

    def _factory(self) -> Any:
        if self.searcher_factory:
            return self.searcher_factory()
        try:
            from ddgs import DDGS
        except ImportError as exc:  # requirements installs it; keep runtime degradation graceful
            raise RuntimeError("ddgs package is not installed") from exc
        timeout = max(1, _env_int("COFI_DISCOVERY_DDGS_TIMEOUT_SEC", 6))
        return DDGS(timeout=timeout)

    def search(self, query: str, *, job: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        market = str(job.get("market") or "").strip().upper()
        region = self._REGIONS.get(market, "wt-wt")
        searcher = self._factory()
        try:
            rows = list(searcher.videos(
                query,
                region=region,
                safesearch="moderate",
                max_results=limit,
                backend="duckduckgo",
            ) or [])
        except Exception:
            rows = []
        if not rows:
            web_rows = searcher.text(
                f"{query} site:youtube.com",
                region=region,
                safesearch="moderate",
                max_results=limit,
                backend="duckduckgo",
            )
            results: list[dict[str, Any]] = []
            for row in web_rows or []:
                if not isinstance(row, dict):
                    continue
                url = str(row.get("href") or row.get("url") or "").strip()
                if not url:
                    continue
                results.append({
                    "provider": self.name,
                    "source_url": url,
                    "title": str(row.get("title") or ""),
                    "description": str(row.get("body") or row.get("content") or row.get("description") or ""),
                    "kind": "video",
                    "source_name": "YouTube via DDGS",
                    "thumbnail_url": "",
                    "duration": "",
                })
            return results[:limit]
        results: list[dict[str, Any]] = []
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            content = str(row.get("content") or "")
            url = str(row.get("url") or (content if content.startswith("http") else "")).strip()
            if not url:
                url = str(row.get("href") or "").strip()
            if not url:
                continue
            images = row.get("images")
            thumbnail = ""
            if isinstance(images, dict):
                thumbnail = str(images.get("large") or images.get("medium") or images.get("small") or "")
            elif isinstance(images, list) and images:
                thumbnail = str(images[0])
            results.append({
                "provider": self.name,
                "source_url": url,
                "title": str(row.get("title") or ""),
                "description": str(row.get("content") or row.get("description") or "") if not str(row.get("content") or "").startswith("http") else str(row.get("description") or ""),
                "kind": "video",
                "source_name": str(row.get("publisher") or row.get("uploader") or ""),
                "thumbnail_url": thumbnail,
                "duration": str(row.get("duration") or ""),
            })
        return results[:limit]


class DDGSImageProvider(DDGSProvider):
    name = "ddgs_images"

    def search(self, query: str, *, job: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        market = str(job.get("market") or "").strip().upper()
        region = self._REGIONS.get(market, "wt-wt")
        rows = self._factory().images(
            query,
            region=region,
            safesearch="moderate",
            max_results=max(1, int(limit)),
            backend="duckduckgo",
        )
        results: list[dict[str, Any]] = []
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            image_url = str(row.get("image") or row.get("url") or "").strip()
            if not image_url:
                continue
            results.append({
                "provider": self.name,
                "source_url": image_url,
                "source_page": str(row.get("url") or "").strip(),
                "title": _text(row.get("title")),
                "description": _text(row.get("description")),
                "kind": "still",
                "source_name": _text(row.get("source")) or "DDGS Images",
                "thumbnail_url": _text(row.get("thumbnail")) or image_url,
            })
            if len(results) >= max(1, int(limit)):
                break
        return results


class _HTTPProvider:
    name = "http"

    def __init__(self, client: httpx.Client | None = None):
        self.client = client or _default_http_client()


class InternetArchiveProvider(_HTTPProvider):
    name = "internet_archive"

    def search(self, query: str, *, job: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        response = self.client.get("https://archive.org/advancedsearch.php", params={
            "q": f"({query}) AND mediatype:movies",
            "fl[]": ["identifier", "title", "description", "creator", "date", "licenseurl"],
            "rows": limit,
            "page": 1,
            "output": "json",
        })
        response.raise_for_status()
        docs = ((response.json().get("response") or {}).get("docs") or [])
        results: list[dict[str, Any]] = []
        for row in docs:
            if not isinstance(row, dict):
                continue
            identifier = str(row.get("identifier") or "").strip()
            if not identifier:
                continue
            results.append({
                "provider": self.name,
                "source_url": f"https://archive.org/details/{identifier}",
                "title": _text(row.get("title")),
                "description": _text(row.get("description")),
                "kind": "video",
                "source_name": _text(row.get("creator")) or "Internet Archive",
                "date": _text(row.get("date")),
                "rights_hint": _text(row.get("licenseurl")),
            })
        return results[:limit]


class InternetArchiveToolProvider:
    """Search Archive.org through the installed internetarchive GitHub/PyPI package."""

    name = "internetarchive_tool"

    def __init__(self, search_factory: Callable[..., Any] | None = None):
        self.search_factory = search_factory

    def _search_factory(self) -> Callable[..., Any]:
        if self.search_factory is not None:
            return self.search_factory
        try:
            from internetarchive import search_items
        except ImportError as exc:
            raise RuntimeError("internetarchive package is not installed") from exc
        return search_items

    def search(self, query: str, *, job: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        search_items = self._search_factory()
        timeout = max(1.0, float(os.getenv("COFI_DISCOVERY_PROVIDER_TIMEOUT_SEC", "8") or 8))
        rows = search_items(
            f"({query}) AND mediatype:movies",
            fields=["identifier", "title", "description", "creator", "date", "licenseurl"],
            request_kwargs={"timeout": timeout},
        )
        results: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            identifier = str(row.get("identifier") or "").strip()
            if not identifier:
                continue
            results.append({
                "provider": self.name,
                "source_url": f"https://archive.org/details/{identifier}",
                "title": _text(row.get("title")),
                "description": _text(row.get("description")),
                "kind": "video",
                "source_name": _text(row.get("creator")) or "Internet Archive",
                "date": _text(row.get("date")),
                "rights_hint": _text(row.get("licenseurl")),
            })
            if len(results) >= max(1, int(limit)):
                break
        return results


class YtDlpSearchProvider:
    """Use the bundled yt-dlp repo binary for an exact YouTube metadata search."""

    name = "yt_dlp"

    def __init__(self, executable: str | None = None, runner: Callable[..., Any] | None = None):
        self.executable = executable
        self.runner = runner or subprocess.run

    def _executable(self) -> str:
        configured = str(self.executable or os.getenv("COFI_YTDLP_BIN") or "").strip()
        if configured and Path(configured).exists():
            return configured
        bundled = Path(__file__).resolve().parents[1] / "tools" / "yt-dlp.exe"
        if bundled.exists():
            return str(bundled)
        resolved = shutil.which("yt-dlp") or shutil.which("yt-dlp.exe")
        if resolved:
            return resolved
        raise RuntimeError("yt-dlp is not available")

    def search(self, query: str, *, job: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        target = max(1, int(limit))
        timeout = max(3, _env_int("COFI_DISCOVERY_YTDLP_TIMEOUT_SEC", 15))
        kwargs: dict[str, Any] = {
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "timeout": timeout,
        }
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 1)
            startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
            kwargs["startupinfo"] = startupinfo
        result = self.runner(
            [
                self._executable(),
                "--flat-playlist",
                "--playlist-end", str(target),
                "--quiet",
                "--no-warnings",
                "--dump-single-json",
                f"ytsearch{target}:{query}",
            ],
            **kwargs,
        )
        if int(getattr(result, "returncode", 1) or 0) != 0:
            raise RuntimeError(str(getattr(result, "stderr", "") or "yt-dlp search failed")[:240])
        try:
            payload = json.loads(str(getattr(result, "stdout", "") or "{}"))
        except json.JSONDecodeError as exc:
            raise RuntimeError("yt-dlp returned invalid JSON") from exc
        entries = payload.get("entries") if isinstance(payload, dict) else []
        results: list[dict[str, Any]] = []
        for row in entries or []:
            if not isinstance(row, dict):
                continue
            video_id = str(row.get("id") or "").strip()
            url = str(row.get("webpage_url") or row.get("original_url") or "").strip()
            if not url and video_id:
                url = f"https://www.youtube.com/watch?v={video_id}"
            if not url:
                continue
            results.append({
                "provider": self.name,
                "source_url": url,
                "title": _text(row.get("title")),
                "description": _text(row.get("description")),
                "kind": "video",
                "source_name": _text(row.get("uploader") or row.get("channel")) or "YouTube",
                "duration": row.get("duration") or "",
                "thumbnail_url": _text(row.get("thumbnail")),
            })
            if len(results) >= target:
                break
        return results


class LibraryOfCongressProvider(_HTTPProvider):
    name = "loc"

    def search(self, query: str, *, job: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        response = self.client.get("https://www.loc.gov/film-and-videos/", params={
            "q": query,
            "fo": "json",
            "c": limit,
            "at": "results",
        })
        response.raise_for_status()
        rows = response.json().get("results") or []
        results: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            url = str(row.get("id") or row.get("url") or "").strip()
            if not url:
                continue
            results.append({
                "provider": self.name,
                "source_url": url.replace("http://www.loc.gov/", "https://www.loc.gov/"),
                "title": _text(row.get("title")),
                "description": _text(row.get("description")),
                "kind": "video",
                "source_name": _text(row.get("contributor")) or "Library of Congress",
                "date": _text(row.get("date")),
                "thumbnail_url": str(_first(row.get("image_url"), "")),
                "rights_hint": _text(row.get("rights")),
            })
        return results[:limit]


class WikimediaCommonsProvider(_HTTPProvider):
    name = "wikimedia"

    def search(self, query: str, *, job: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        response = self.client.get("https://commons.wikimedia.org/w/api.php", params={
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,
            "gsrlimit": limit,
            "prop": "imageinfo",
            "iiprop": "url|mime|size|extmetadata",
        })
        response.raise_for_status()
        pages = ((response.json().get("query") or {}).get("pages") or {})
        rows = pages.values() if isinstance(pages, dict) else []
        results: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            info = _first(row.get("imageinfo"), {})
            if not isinstance(info, dict):
                continue
            url = str(info.get("url") or info.get("descriptionurl") or "").strip()
            if not url:
                continue
            mime = str(info.get("mime") or "").lower()
            metadata = info.get("extmetadata") if isinstance(info.get("extmetadata"), dict) else {}
            license_meta = metadata.get("LicenseShortName") if isinstance(metadata, dict) else {}
            license_hint = license_meta.get("value") if isinstance(license_meta, dict) else ""
            description_meta = metadata.get("ImageDescription") if isinstance(metadata, dict) else {}
            description = description_meta.get("value") if isinstance(description_meta, dict) else ""
            results.append({
                "provider": self.name,
                "source_url": url,
                "title": str(row.get("title") or "").removeprefix("File:"),
                "description": re.sub(r"<[^>]+>", " ", str(description or "")),
                "kind": "video" if mime.startswith("video/") else "still",
                "source_name": "Wikimedia Commons",
                "rights_hint": str(license_hint or ""),
            })
        return results[:limit]


class OpenverseProvider(_HTTPProvider):
    name = "openverse"

    def search(self, query: str, *, job: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        response = self.client.get("https://api.openverse.org/v1/images/", params={
            "q": query,
            "page_size": max(1, min(20, int(limit))),
            "mature": "false",
        })
        response.raise_for_status()
        results: list[dict[str, Any]] = []
        for row in response.json().get("results") or []:
            if not isinstance(row, dict):
                continue
            media_url = str(row.get("url") or "").strip()
            if not media_url:
                continue
            license_name = str(row.get("license") or "").strip()
            license_version = str(row.get("license_version") or "").strip()
            results.append({
                "provider": self.name,
                "source_url": media_url,
                "source_page": str(row.get("foreign_landing_url") or "").strip(),
                "title": _text(row.get("title")),
                "description": _text(row.get("detail_url") or row.get("source")),
                "kind": "still",
                "source_name": _text(row.get("creator")) or "Openverse",
                "thumbnail_url": str(row.get("thumbnail") or media_url),
                "rights_hint": " ".join(value for value in [license_name, license_version] if value),
            })
            if len(results) >= max(1, int(limit)):
                break
        return results


class SearXNGProvider(_HTTPProvider):
    name = "searxng"

    def __init__(self, base_url: str, client: httpx.Client | None = None):
        super().__init__(client)
        self.base_url = base_url.rstrip("/")

    def search(self, query: str, *, job: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        response = self.client.get(f"{self.base_url}/search", params={
            "q": query,
            "format": "json",
            "categories": "videos,general",
        })
        response.raise_for_status()
        results: list[dict[str, Any]] = []
        for row in (response.json().get("results") or [])[:limit]:
            if not isinstance(row, dict) or not row.get("url"):
                continue
            results.append({
                "provider": self.name,
                "source_url": str(row.get("url")),
                "title": _text(row.get("title")),
                "description": _text(row.get("content")),
                "kind": "video",
                "source_name": _text(row.get("engine")) or "SearXNG",
                "thumbnail_url": _text(row.get("thumbnail")),
            })
        return results


class BraveSearchProvider(_HTTPProvider):
    name = "brave"

    def __init__(self, api_key: str, client: httpx.Client | None = None):
        super().__init__(client)
        self.api_key = api_key

    def search(self, query: str, *, job: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        response = self.client.get(
            "https://api.search.brave.com/res/v1/videos/search",
            params={"q": query, "count": limit, "safesearch": "moderate"},
            headers={"Accept": "application/json", "X-Subscription-Token": self.api_key},
        )
        response.raise_for_status()
        results: list[dict[str, Any]] = []
        for row in (response.json().get("results") or [])[:limit]:
            if not isinstance(row, dict) or not row.get("url"):
                continue
            thumbnail = row.get("thumbnail")
            if isinstance(thumbnail, dict):
                thumbnail = thumbnail.get("src") or thumbnail.get("url")
            results.append({
                "provider": self.name,
                "source_url": str(row.get("url")),
                "title": _text(row.get("title")),
                "description": _text(row.get("description")),
                "kind": "video",
                "source_name": _text(row.get("publisher")) or "Brave Search",
                "thumbnail_url": str(thumbnail or ""),
                "duration": _text(row.get("duration")),
            })
        return results


class EuropeanaProvider(_HTTPProvider):
    name = "europeana"

    def __init__(self, api_key: str, client: httpx.Client | None = None):
        super().__init__(client)
        self.api_key = api_key

    def search(self, query: str, *, job: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        response = self.client.get("https://api.europeana.eu/record/v2/search.json", params={
            "wskey": self.api_key,
            "query": query,
            "rows": limit,
            "profile": "rich",
        })
        response.raise_for_status()
        results: list[dict[str, Any]] = []
        for row in (response.json().get("items") or [])[:limit]:
            if not isinstance(row, dict):
                continue
            url = str(row.get("guid") or row.get("link") or "").strip()
            if not url:
                continue
            media_type = str(row.get("type") or "").upper()
            results.append({
                "provider": self.name,
                "source_url": url,
                "title": _text(row.get("title")),
                "description": _text(row.get("dcDescription")),
                "kind": "video" if media_type == "VIDEO" else "still",
                "source_name": _text(row.get("dataProvider")) or "Europeana",
                "thumbnail_url": str(_first(row.get("edmPreview"), "")),
                "date": _text(row.get("year")),
                "rights_hint": _text(row.get("rights")),
            })
        return results


class NARAProvider(_HTTPProvider):
    name = "nara"

    def __init__(self, api_key: str, client: httpx.Client | None = None):
        super().__init__(client)
        self.api_key = api_key

    @staticmethod
    def _year(row: dict[str, Any]) -> str:
        for value in row.get("productionDates") or row.get("inclusiveDates") or []:
            if isinstance(value, dict):
                year = value.get("year") or value.get("beginYear") or value.get("endYear")
                if year:
                    return str(year)
        return _text(row.get("date"))

    def search(self, query: str, *, job: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        response = self.client.get(
            "https://catalog.archives.gov/api/v2/records/search",
            params={"availableOnline": "true", "q": query, "limit": limit},
            headers={"Content-Type": "application/json", "x-api-key": self.api_key},
        )
        response.raise_for_status()
        payload = response.json()
        hits = (((payload.get("body") or {}).get("hits") or {}).get("hits") or payload.get("records") or [])
        results: list[dict[str, Any]] = []
        for hit in hits[:limit]:
            if not isinstance(hit, dict):
                continue
            row = hit.get("_source") if isinstance(hit.get("_source"), dict) else hit
            naid = str(row.get("naId") or row.get("naid") or row.get("id") or "").strip()
            if not naid:
                continue
            materials = _text(row.get("typeOfMaterials"))
            results.append({
                "provider": self.name,
                "source_url": f"https://catalog.archives.gov/id/{naid}",
                "title": _text(row.get("title")),
                "description": _text(row.get("scopeAndContentNote") or row.get("description")),
                "kind": "video" if "moving" in materials.lower() else "still",
                "source_name": "US National Archives",
                "date": self._year(row),
                "rights_hint": _text(row.get("rights")),
            })
        return results


def default_providers(
    *,
    client: httpx.Client | None = None,
    ddgs_factory: Callable[[], Any] | None = None,
) -> list[SourceProvider]:
    providers: list[SourceProvider] = [
        DDGSProvider(searcher_factory=ddgs_factory),
        DDGSImageProvider(searcher_factory=ddgs_factory),
        InternetArchiveToolProvider(),
        YtDlpSearchProvider(),
        InternetArchiveProvider(client=client),
        LibraryOfCongressProvider(client=client),
        WikimediaCommonsProvider(client=client),
        OpenverseProvider(client=client),
    ]
    searx_url = os.getenv("COFI_SEARXNG_URL", "").strip()
    brave_key = (os.getenv("COFI_SOURCE_BRAVE_API_KEY") or os.getenv("BRAVE_SEARCH_API_KEY") or "").strip()
    europeana_key = (os.getenv("COFI_SOURCE_EUROPEANA_API_KEY") or os.getenv("EUROPEANA_API_KEY") or "").strip()
    nara_key = (os.getenv("COFI_SOURCE_NARA_API_KEY") or os.getenv("NARA_API_KEY") or "").strip()
    if searx_url:
        providers.append(SearXNGProvider(searx_url, client=client))
    if brave_key:
        providers.append(BraveSearchProvider(brave_key, client=client))
    if europeana_key:
        providers.append(EuropeanaProvider(europeana_key, client=client))
    if nara_key:
        providers.append(NARAProvider(nara_key, client=client))
    return providers


def direct_tool_providers(
    *,
    ddgs_factory: Callable[[], Any] | None = None,
    internetarchive_search_factory: Callable[..., Any] | None = None,
    ytdlp_executable: str | None = None,
    ytdlp_runner: Callable[..., Any] | None = None,
    client: httpx.Client | None = None,
) -> list[SourceProvider]:
    """Repo-backed, keyless tools that Codex/Gemini can invoke from the local shell."""

    return [
        DDGSProvider(searcher_factory=ddgs_factory),
        DDGSImageProvider(searcher_factory=ddgs_factory),
        InternetArchiveToolProvider(search_factory=internetarchive_search_factory),
        YtDlpSearchProvider(executable=ytdlp_executable, runner=ytdlp_runner),
        OpenverseProvider(client=client),
    ]


_STOP_WORDS = {
    "about", "after", "also", "and", "archive", "archival", "before", "documentary",
    "film", "footage", "for", "from", "into", "news", "scene", "shot", "that", "the",
    "their", "this", "video", "with",
}

_PROVIDER_TRUST = {
    "nara": 10.0,
    "loc": 9.0,
    "library_of_congress": 9.0,
    "internet_archive": 8.0,
    "internetarchive_tool": 8.0,
    "wikimedia": 7.0,
    "wikimedia_commons": 7.0,
    "europeana": 7.0,
    "brave": 4.0,
    "searxng": 3.0,
    "ddgs": 2.0,
    "ddgs_images": 2.0,
    "yt_dlp": 2.0,
    "openverse": 8.0,
}

SOURCE_SECRET_ENV_NAMES = {
    "BRAVE_SEARCH_API_KEY",
    "EUROPEANA_API_KEY",
    "NARA_API_KEY",
    "COFI_SOURCE_BRAVE_API_KEY",
    "COFI_SOURCE_EUROPEANA_API_KEY",
    "COFI_SOURCE_NARA_API_KEY",
}


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, value)


def _normalize_query(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _tokens(*values: Any) -> set[str]:
    text = " ".join(str(value or "") for value in values).lower()
    return {
        token
        for token in re.findall(r"[\w'-]{2,}", text, flags=re.UNICODE)
        if token not in _STOP_WORDS
    }


def _years(*values: Any) -> set[str]:
    text = " ".join(str(value or "") for value in values)
    return set(re.findall(r"\b(?:18|19|20|21)\d{2}\b", text))


def _candidate_url(candidate: dict[str, Any]) -> str:
    return str(candidate.get("source_url") or candidate.get("url") or "").strip()


def scrub_source_secret_env(env: dict[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in env.items()
        if key not in SOURCE_SECRET_ENV_NAMES and not key.upper().startswith("COFI_SOURCE_")
    }


def _safe_error(exc: Exception) -> str:
    text = str(exc)
    for env_name in SOURCE_SECRET_ENV_NAMES:
        secret = os.getenv(env_name, "").strip()
        if secret:
            text = text.replace(secret, "[REDACTED]")
    text = re.sub(r"(?i)(wskey|api[_-]?key|x-api-key)=([^&\s]+)", r"\1=[REDACTED]", text)
    return text[:240]


def rank_candidates(
    query_context: dict[str, Any],
    candidates: list[dict[str, Any]],
    limit: int = 10,
    max_per_provider: int | None = None,
) -> list[dict[str, Any]]:
    context_tokens = _tokens(
        query_context.get("query"),
        query_context.get("narration_text"),
        query_context.get("visual_description"),
        query_context.get("purpose"),
        query_context.get("job_title"),
    )
    target_years = _years(
        query_context.get("query"),
        query_context.get("narration_text"),
        query_context.get("visual_description"),
    )
    preferred_kind = str(query_context.get("preferred_kind") or "").lower()
    scored: dict[str, tuple[float, dict[str, Any]]] = {}

    for raw in candidates:
        if not isinstance(raw, dict):
            continue
        url = _candidate_url(raw)
        if not url:
            continue
        candidate = dict(raw)
        candidate["source_url"] = url
        candidate_tokens = _tokens(
            candidate.get("title"),
            candidate.get("description"),
            candidate.get("source_name"),
            candidate.get("country"),
        )
        overlap = len(context_tokens.intersection(candidate_tokens))
        score = float(overlap * 4)

        title_years = _years(candidate.get("title"))
        candidate_years = _years(candidate.get("title"), candidate.get("description"), candidate.get("date"))
        if target_years and candidate_years:
            if title_years and not target_years.intersection(title_years):
                score -= 60.0
            if target_years.intersection(candidate_years):
                score += 24.0
            else:
                score -= 40.0

        provider = str(candidate.get("provider") or "").strip().lower()
        score += _PROVIDER_TRUST.get(provider, 0.0)
        kind = str(candidate.get("kind") or "").lower()
        if preferred_kind in {"video", "sourced_video"} and kind in {"video", "sourced_video"}:
            score += 4.0

        candidate["discovery_score"] = round(score, 2)
        existing = scored.get(url)
        if existing is None or score > existing[0]:
            scored[url] = (score, candidate)

    ordered = sorted(scored.values(), key=lambda item: item[0], reverse=True)
    target = max(1, int(limit))
    provider_cap = max_per_provider
    if provider_cap is None:
        provider_cap = _env_int("COFI_DISCOVERY_MAX_PER_PROVIDER_IN_SHORTLIST", 4)
    provider_cap = max(1, int(provider_cap))

    selected: list[dict[str, Any]] = []
    selected_urls: set[str] = set()
    provider_counts: dict[str, int] = {}
    for _, candidate in ordered:
        provider = str(candidate.get("provider") or "unknown").strip().lower() or "unknown"
        if provider_counts.get(provider, 0) >= provider_cap:
            continue
        selected.append(candidate)
        selected_urls.add(candidate["source_url"])
        provider_counts[provider] = provider_counts.get(provider, 0) + 1
        if len(selected) >= target:
            return selected

    for _, candidate in ordered:
        if candidate["source_url"] in selected_urls:
            continue
        selected.append(candidate)
        selected_urls.add(candidate["source_url"])
        if len(selected) >= target:
            break
    return selected


@dataclass
class SourceDiscoveryHub:
    providers: list[SourceProvider] | None = None
    cache_ttl_sec: int | None = None
    max_workers: int | None = None
    per_provider_limit: int | None = None
    per_beat_limit: int | None = None
    shortlist_per_provider: int | None = None
    semantic_reranker: Any | None = None

    def __post_init__(self) -> None:
        if self.providers is None:
            self.providers = list(default_providers())
        else:
            self.providers = list(self.providers)
        if self.cache_ttl_sec is None:
            self.cache_ttl_sec = _env_int("COFI_DISCOVERY_CACHE_TTL_SEC", 86400, minimum=0)
        if self.max_workers is None:
            self.max_workers = _env_int("COFI_DISCOVERY_WORKERS", 6)
        if self.per_provider_limit is None:
            self.per_provider_limit = _env_int("COFI_DISCOVERY_RESULTS_PER_PROVIDER", 6)
        if self.per_beat_limit is None:
            self.per_beat_limit = _env_int("COFI_DISCOVERY_CANDIDATES_PER_BEAT", 30)
        if self.shortlist_per_provider is None:
            self.shortlist_per_provider = max(2, min(3, _env_int("COFI_DISCOVERY_SHORTLIST_PER_PROVIDER", 3)))
        if self.semantic_reranker is None:
            self.semantic_reranker = OpenClipSemanticReranker()
        self.last_diagnostics: dict[str, dict[str, Any]] = {}
        self._disabled_providers: dict[str, str] = {}

    @staticmethod
    def _cache_path(workspace: Path) -> Path:
        return workspace / ".producer" / "source_discovery" / "cache.json"

    def _load_cache(self, workspace: Path) -> dict[str, Any]:
        path = self._cache_path(workspace)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"version": 1, "entries": {}}
        if not isinstance(payload, dict) or not isinstance(payload.get("entries"), dict):
            return {"version": 1, "entries": {}}
        return payload

    def _save_cache(self, workspace: Path, cache: dict[str, Any]) -> None:
        if int(self.cache_ttl_sec or 0) <= 0:
            return
        path = self._cache_path(workspace)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    @staticmethod
    def _cache_key(provider_name: str, query: str) -> str:
        return f"{provider_name.strip().lower()}|{_normalize_query(query).lower()}"

    def _cached_results(self, cache: dict[str, Any], provider_name: str, query: str) -> list[dict[str, Any]] | None:
        if int(self.cache_ttl_sec or 0) <= 0:
            return None
        entry = (cache.get("entries") or {}).get(self._cache_key(provider_name, query))
        if not isinstance(entry, dict):
            return None
        created_at = float(entry.get("created_at") or 0)
        if time.time() - created_at > int(self.cache_ttl_sec or 0):
            return None
        results = entry.get("results")
        if not isinstance(results, list):
            return None
        return [dict(item) for item in results if isinstance(item, dict)]

    def _store_results(
        self,
        cache: dict[str, Any],
        provider_name: str,
        query: str,
        results: list[dict[str, Any]],
    ) -> None:
        if int(self.cache_ttl_sec or 0) <= 0:
            return
        cache.setdefault("entries", {})[self._cache_key(provider_name, query)] = {
            "created_at": time.time(),
            "results": results,
        }

    @staticmethod
    def _fallback_query(job: dict[str, Any], beat: dict[str, Any]) -> str:
        pieces = [
            beat.get("visual_description"),
            beat.get("narration_text"),
            beat.get("purpose"),
            job.get("title"),
        ]
        compact = _normalize_query(" ".join(str(value or "") for value in pieces if str(value or "").strip()))
        return compact[:480]

    def _queries_for_beat(self, job: dict[str, Any], beat: dict[str, Any]) -> list[str]:
        queries = [
            _normalize_query(value)
            for value in (beat.get("footage_search_queries") or [])
            if _normalize_query(value)
        ]
        if not queries:
            fallback = self._fallback_query(job, beat)
            if fallback:
                queries = [fallback]
        return list(dict.fromkeys(queries))

    def _search_query(
        self,
        query: str,
        job: dict[str, Any],
        cache: dict[str, Any],
    ) -> list[dict[str, Any]]:
        collected: list[dict[str, Any]] = []
        pending: list[SourceProvider] = []
        self.last_diagnostics = self.last_diagnostics or {}

        for provider in self.providers or []:
            provider_name = str(getattr(provider, "name", provider.__class__.__name__)).strip() or provider.__class__.__name__
            cached = self._cached_results(cache, provider_name, query)
            if cached is not None:
                self.last_diagnostics[provider_name] = {"status": "cache", "count": len(cached)}
                collected.extend(cached)
            else:
                pending.append(provider)

        if not pending:
            return collected

        workers = min(max(1, int(self.max_workers or 1)), len(pending))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(provider.search, query, job=job, limit=int(self.per_provider_limit or 1)): provider
                for provider in pending
            }
            for future in as_completed(futures):
                provider = futures[future]
                provider_name = str(getattr(provider, "name", provider.__class__.__name__)).strip() or provider.__class__.__name__
                try:
                    raw_results = future.result()
                    normalized: list[dict[str, Any]] = []
                    for item in raw_results or []:
                        if not isinstance(item, dict):
                            continue
                        candidate = dict(item)
                        candidate.setdefault("provider", provider_name)
                        if _candidate_url(candidate):
                            candidate["source_url"] = _candidate_url(candidate)
                            candidate.setdefault("search_query", query)
                            normalized.append(candidate)
                    self.last_diagnostics[provider_name] = {"status": "ok", "count": len(normalized)}
                    self._store_results(cache, provider_name, query, normalized)
                    collected.extend(normalized)
                except Exception as exc:  # provider failure must never abort the footage phase
                    self.last_diagnostics[provider_name] = {
                        "status": "error",
                        "error": _safe_error(exc),
                    }
        return collected

    def discover_for_beats(
        self,
        job: dict[str, Any],
        beats: list[dict[str, Any]],
        workspace: str | Path,
        control_callback: Callable[[], None] | None = None,
        progress_callback: Callable[[int, int, str, str], None] | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        workspace = Path(workspace)
        cache = self._load_cache(workspace)
        self.last_diagnostics = {}

        beat_queries: dict[str, list[str]] = {}
        unique_queries: dict[str, str] = {}
        for beat in beats:
            beat_id = str(beat.get("beat_id") or "").strip()
            if not beat_id:
                continue
            queries = self._queries_for_beat(job, beat)
            beat_queries[beat_id] = queries
            for query in queries:
                unique_queries.setdefault(_normalize_query(query).lower(), query)

        results_by_query: dict[str, list[dict[str, Any]]] = {
            normalized: [] for normalized in unique_queries
        }
        pending: list[tuple[str, str, SourceProvider, str]] = []
        for normalized, query in unique_queries.items():
            for provider in self.providers or []:
                provider_name = str(getattr(provider, "name", provider.__class__.__name__)).strip() or provider.__class__.__name__
                if provider_name in self._disabled_providers:
                    self.last_diagnostics[provider_name] = {
                        "status": "disabled",
                        "reason": self._disabled_providers[provider_name],
                    }
                    continue
                cached = self._cached_results(cache, provider_name, query)
                if cached is not None:
                    results_by_query[normalized].extend(cached)
                    diagnostic = self.last_diagnostics.setdefault(provider_name, {"status": "cache", "count": 0})
                    diagnostic["count"] = int(diagnostic.get("count") or 0) + len(cached)
                    if diagnostic.get("status") != "error":
                        diagnostic["status"] = "cache"
                else:
                    pending.append((normalized, query, provider, provider_name))

        if pending:
            completed_searches = 0
            total_searches = len(pending)
            if progress_callback is not None:
                progress_callback(0, total_searches, "", "")
            workers = min(max(1, int(self.max_workers or 1)), len(pending))
            # Submit one bounded wave at a time. Besides avoiding thousands of
            # queued network tasks for long videos, this gives Footage pause/stop
            # a real cooperative checkpoint while tools are still searching.
            with ThreadPoolExecutor(max_workers=workers) as executor:
                for offset in range(0, len(pending), workers):
                    if control_callback is not None:
                        control_callback()
                    wave = pending[offset:offset + workers]
                    futures = {
                        executor.submit(
                            provider.search,
                            query,
                            job=job,
                            limit=int(self.per_provider_limit or 1),
                        ): (normalized, query, provider_name)
                        for normalized, query, provider, provider_name in wave
                    }
                    for future in as_completed(futures):
                        normalized, query, provider_name = futures[future]
                        try:
                            raw_results = future.result()
                            normalized_rows: list[dict[str, Any]] = []
                            for item in raw_results or []:
                                if not isinstance(item, dict):
                                    continue
                                candidate = dict(item)
                                candidate.setdefault("provider", provider_name)
                                url = _candidate_url(candidate)
                                if not url:
                                    continue
                                candidate["source_url"] = url
                                candidate.setdefault("search_query", query)
                                normalized_rows.append(candidate)
                            results_by_query[normalized].extend(normalized_rows)
                            self._store_results(cache, provider_name, query, normalized_rows)
                            diagnostic = self.last_diagnostics.setdefault(provider_name, {"status": "ok", "count": 0})
                            diagnostic["count"] = int(diagnostic.get("count") or 0) + len(normalized_rows)
                            if diagnostic.get("status") == "error":
                                diagnostic["status"] = "partial"
                            elif diagnostic.get("status") != "partial":
                                diagnostic["status"] = "ok"
                        except Exception as exc:
                            diagnostic = self.last_diagnostics.setdefault(provider_name, {"status": "error", "count": 0})
                            if diagnostic.get("status") in {"ok", "cache"}:
                                diagnostic["status"] = "partial"
                            else:
                                diagnostic["status"] = "error"
                            diagnostic["error"] = _safe_error(exc)
                            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in {401, 403}:
                                self._disabled_providers[provider_name] = f"HTTP {exc.response.status_code} trong job hiện tại"

                        completed_searches += 1
                        if progress_callback is not None:
                            progress_callback(completed_searches, total_searches, provider_name, query)
                        if control_callback is not None:
                            control_callback()

                    # Persist each completed wave so an interrupted/restarted
                    # Footage run can reuse provider work instead of starting
                    # the whole discovery pass from zero again.
                    self._save_cache(workspace, cache)

        self._save_cache(workspace, cache)

        discovered: dict[str, list[dict[str, Any]]] = {}
        rank_total = len([
            beat for beat in beats
            if str(beat.get("beat_id") or "").strip()
        ])
        rank_completed = 0
        for beat in beats:
            beat_id = str(beat.get("beat_id") or "").strip()
            if not beat_id:
                continue
            queries = beat_queries.get(beat_id, [])
            pool: list[dict[str, Any]] = []
            for query in queries:
                pool.extend(results_by_query.get(_normalize_query(query).lower(), []))
            preferred_kind = "video" if "video" in str(beat.get("visual_type") or "").lower() else ""
            context = {
                "query": " ".join(queries),
                "narration_text": beat.get("narration_text"),
                "visual_description": beat.get("visual_description"),
                "purpose": beat.get("purpose"),
                "job_title": job.get("title"),
                "preferred_kind": preferred_kind,
            }
            ranked = rank_candidates(
                context,
                pool,
                limit=max(int(self.per_beat_limit or 1), len(pool) or 1),
                max_per_provider=max(int(self.per_provider_limit or 1), int(self.shortlist_per_provider or 1)),
            )
            reranker = self.semantic_reranker
            if reranker is not None and callable(getattr(reranker, "rerank", None)):
                try:
                    ranked = reranker.rerank(context, ranked, limit=len(ranked))
                    self.last_diagnostics["semantic_reranker"] = {
                        "status": "ok",
                        "provider": str(getattr(reranker, "__class__", type(reranker)).__name__),
                    }
                except Exception as exc:
                    self.last_diagnostics["semantic_reranker"] = {
                        "status": "error",
                        "error": _safe_error(exc),
                    }

            provider_cap = max(2, min(3, int(self.shortlist_per_provider or 3)))
            provider_counts: dict[str, int] = {}
            shortlist: list[dict[str, Any]] = []
            for candidate in ranked:
                provider = str(candidate.get("provider") or "unknown").strip().lower() or "unknown"
                if provider_counts.get(provider, 0) >= provider_cap:
                    continue
                shortlist.append(candidate)
                provider_counts[provider] = provider_counts.get(provider, 0) + 1
                if len(shortlist) >= int(self.per_beat_limit or 1):
                    break
            discovered[beat_id] = shortlist
            rank_completed += 1
            if progress_callback is not None:
                progress_callback(rank_completed, rank_total, "semantic_rank", beat_id)
            if control_callback is not None:
                control_callback()
        return discovered
