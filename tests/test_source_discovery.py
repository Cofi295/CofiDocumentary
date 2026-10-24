from __future__ import annotations

import json
from pathlib import Path
import time

import httpx

from documentary.source_discovery import (
    BraveSearchProvider,
    DDGSImageProvider,
    DDGSProvider,
    InternetArchiveToolProvider,
    EuropeanaProvider,
    InternetArchiveProvider,
    LibraryOfCongressProvider,
    NARAProvider,
    OpenverseProvider,
    SearXNGProvider,
    SourceDiscoveryHub,
    WikimediaCommonsProvider,
    YtDlpSearchProvider,
    direct_tool_providers,
    default_providers,
    rank_candidates,
)


class FakeProvider:
    def __init__(self, name: str, results: list[dict] | None = None, error: Exception | None = None):
        self.name = name
        self.results = list(results or [])
        self.error = error
        self.calls: list[str] = []

    def search(self, query: str, *, job: dict, limit: int) -> list[dict]:
        self.calls.append(query)
        if self.error:
            raise self.error
        return [dict(item) for item in self.results[:limit]]


def test_internet_archive_tool_provider_uses_repo_package_search():
    calls = []

    def fake_search(query: str, **kwargs):
        calls.append((query, kwargs))
        return iter([{
            "identifier": "versailles-1919",
            "title": "Signing of the Treaty of Versailles, 1919",
            "description": "President Wilson and delegates",
            "creator": "US National Archives",
            "date": "1919",
            "licenseurl": "https://creativecommons.org/publicdomain/mark/1.0/",
        }])

    provider = InternetArchiveToolProvider(search_factory=fake_search)
    row = provider.search("Woodrow Wilson Versailles 1919", job={}, limit=3)[0]

    assert calls
    assert "mediatype:movies" in calls[0][0]
    assert calls[0][1]["request_kwargs"]["timeout"] == 8.0
    assert row["provider"] == "internetarchive_tool"
    assert row["source_url"] == "https://archive.org/details/versailles-1919"
    assert row["date"] == "1919"


def test_ytdlp_search_provider_uses_bundled_repo_tool_and_returns_compact_metadata(tmp_path: Path):
    executable = tmp_path / "yt-dlp.exe"
    executable.write_text("stub", encoding="utf-8")
    seen = []

    class Result:
        returncode = 0
        stderr = ""
        stdout = json.dumps({
            "entries": [{
                "id": "2BVpuNFFrcE",
                "title": "The Signing of the Treaty of Versailles, June 28, 1919",
                "uploader": "US National Archives",
                "duration": 76,
                "webpage_url": "https://www.youtube.com/watch?v=2BVpuNFFrcE",
            }]
        })

    def fake_runner(command, **kwargs):
        seen.append((command, kwargs))
        return Result()

    provider = YtDlpSearchProvider(executable=str(executable), runner=fake_runner)
    row = provider.search("Versailles 1919 archival footage", job={}, limit=2)[0]

    assert seen
    assert seen[0][0][-1] == "ytsearch2:Versailles 1919 archival footage"
    assert row["provider"] == "yt_dlp"
    assert row["source_name"] == "US National Archives"
    assert row["source_url"].endswith("2BVpuNFFrcE")


def test_direct_tool_providers_are_repo_backed_search_tools():
    names = [provider.name for provider in direct_tool_providers()]
    assert names == ["ddgs", "ddgs_images", "internetarchive_tool", "yt_dlp", "openverse"]


def test_rank_candidates_penalizes_wrong_year_even_with_similar_entity_tokens():
    context = {
        "query": "Henry Cabot Lodge League of Nations Senate 1919 archival footage",
        "narration_text": "In 1919, Senator Henry Cabot Lodge led opposition to Wilson's League of Nations plan.",
        "visual_description": "Henry Cabot Lodge or the United States Senate in 1919",
        "preferred_kind": "video",
    }
    candidates = [
        {
            "provider": "ddgs",
            "source_url": "https://example.test/lodge-1969",
            "title": "Henry Cabot Lodge speaks to press in 1969",
            "description": "Archival news footage",
            "kind": "video",
        },
        {
            "provider": "internet_archive",
            "source_url": "https://example.test/senate-1919",
            "title": "United States Senate and League of Nations debate, 1919",
            "description": "Henry Cabot Lodge and the Treaty debate",
            "kind": "video",
        },
    ]

    ranked = rank_candidates(context, candidates, limit=5)

    assert ranked[0]["source_url"].endswith("senate-1919")
    assert ranked[0]["discovery_score"] > ranked[1]["discovery_score"]


def test_rank_candidates_penalizes_wrong_title_year_even_if_description_mentions_target_year():
    context = {
        "query": "2011 Tohoku earthquake tsunami Japan footage",
        "narration_text": "The 2011 Tohoku earthquake triggered a tsunami in Japan.",
        "preferred_kind": "video",
    }
    candidates = [
        {
            "provider": "internet_archive",
            "source_url": "https://archive.example/real-2011",
            "title": "NHK Broadcast Footage 2011 Tohoku earthquake and tsunami",
            "description": "News footage from Japan",
            "kind": "video",
        },
        {
            "provider": "internet_archive",
            "source_url": "https://archive.example/movie-2016",
            "title": "Shin Godzilla (2016)",
            "description": "A film discussed alongside the 2011 Tohoku disaster",
            "kind": "video",
        },
    ]

    ranked = rank_candidates(context, candidates, limit=2)

    assert ranked[0]["source_url"].endswith("real-2011")
    assert ranked[1]["discovery_score"] < 0


def test_discovery_deduplicates_query_and_url_across_providers(tmp_path: Path):
    shared = "https://archive.example/item-1"
    provider_a = FakeProvider("alpha", [{
        "source_url": shared,
        "title": "Pantanal jaguar wildlife",
        "kind": "video",
    }])
    provider_b = FakeProvider("beta", [
        {
            "source_url": shared,
            "title": "Pantanal jaguar wildlife duplicate",
            "kind": "video",
        },
        {
            "source_url": "https://archive.example/item-2",
            "title": "Jaguar crossing Pantanal wetland",
            "kind": "video",
        },
    ])
    hub = SourceDiscoveryHub(providers=[provider_a, provider_b], cache_ttl_sec=3600, max_workers=2)
    query = "Pantanal jaguar wildlife Brazil"
    beats = [
        {"beat_id": "B001", "footage_search_queries": [query], "narration_text": "A jaguar patrols the Pantanal."},
        {"beat_id": "B002", "footage_search_queries": [query], "narration_text": "The same wetland floods seasonally."},
    ]

    discovered = hub.discover_for_beats({"title": "Pantanal", "market": "BR"}, beats, tmp_path)

    assert provider_a.calls == [query]
    assert provider_b.calls == [query]
    assert len({item["source_url"] for item in discovered["B001"]}) == len(discovered["B001"])
    assert len({item["source_url"] for item in discovered["B002"]}) == len(discovered["B002"])


def test_discovery_cache_avoids_repeating_provider_calls(tmp_path: Path):
    provider = FakeProvider("alpha", [{
        "source_url": "https://example.test/cached",
        "title": "Tokyo earthquake 1923 archival film",
        "kind": "video",
    }])
    query = "Tokyo earthquake 1923 archival footage"
    beats = [{"beat_id": "B001", "footage_search_queries": [query]}]

    first = SourceDiscoveryHub(providers=[provider], cache_ttl_sec=3600, max_workers=1)
    assert first.discover_for_beats({"title": "Tokyo"}, beats, tmp_path)["B001"]
    second = SourceDiscoveryHub(providers=[provider], cache_ttl_sec=3600, max_workers=1)
    assert second.discover_for_beats({"title": "Tokyo"}, beats, tmp_path)["B001"]

    assert provider.calls == [query]


def test_provider_failure_is_isolated_when_other_provider_returns_results(tmp_path: Path):
    broken = FakeProvider("broken", error=RuntimeError("rate limited"))
    healthy = FakeProvider("healthy", [{
        "source_url": "https://example.test/healthy",
        "title": "Saigon street footage 1968",
        "kind": "video",
    }])
    hub = SourceDiscoveryHub(providers=[broken, healthy], cache_ttl_sec=0, max_workers=2)

    result = hub.discover_for_beats(
        {"title": "Vietnam history", "market": "VN"},
        [{"beat_id": "B001", "footage_search_queries": ["Saigon street footage 1968"]}],
        tmp_path,
    )

    assert [item["source_url"] for item in result["B001"]] == ["https://example.test/healthy"]
    assert hub.last_diagnostics["broken"]["status"] == "error"
    assert hub.last_diagnostics["healthy"]["status"] == "ok"


def test_fallback_query_uses_voice_visual_and_job_context(tmp_path: Path):
    provider = FakeProvider("alpha", [{
        "source_url": "https://example.test/fallback",
        "title": "Mekong Delta floating market",
        "kind": "video",
    }])
    hub = SourceDiscoveryHub(providers=[provider], cache_ttl_sec=0, max_workers=1)

    hub.discover_for_beats(
        {"title": "Mekong Delta", "market": "VN"},
        [{
            "beat_id": "B001",
            "narration_text": "Boats gather before sunrise at the floating market.",
            "visual_description": "Mekong Delta floating market boats at dawn",
        }],
        tmp_path,
    )

    assert len(provider.calls) == 1
    fallback = provider.calls[0].lower()
    assert "mekong" in fallback
    assert "floating market" in fallback


class FakeDDGS:
    def videos(self, query: str, **kwargs):
        assert query == "Pantanal jaguar Brazil"
        assert kwargs["max_results"] == 3
        assert kwargs["backend"] == "duckduckgo"
        return [{
            "title": "Jaguar in Brazil's Pantanal",
            "content": "Wild jaguar crossing a wetland",
            "url": "https://video.example/pantanal",
            "publisher": "Nature Archive",
            "duration": "00:42",
            "images": {"large": "https://img.example/pantanal.jpg"},
        }]


def test_ddgs_provider_normalizes_video_results():
    provider = DDGSProvider(searcher_factory=lambda: FakeDDGS())

    results = provider.search("Pantanal jaguar Brazil", job={"market": "BR"}, limit=3)

    assert results == [{
        "provider": "ddgs",
        "source_url": "https://video.example/pantanal",
        "title": "Jaguar in Brazil's Pantanal",
        "description": "Wild jaguar crossing a wetland",
        "kind": "video",
        "source_name": "Nature Archive",
        "thumbnail_url": "https://img.example/pantanal.jpg",
        "duration": "00:42",
    }]


def test_ddgs_provider_falls_back_to_youtube_web_results_when_video_search_is_empty():
    class FallbackDDGS:
        def videos(self, query: str, **kwargs):
            raise RuntimeError("No results found")

        def text(self, query: str, **kwargs):
            assert "site:youtube.com" in query
            assert kwargs["backend"] == "duckduckgo"
            return [{
                "title": "Pantanal Jaguar Wildlife - YouTube",
                "href": "https://www.youtube.com/watch?v=abc123",
                "body": "Jaguar footage from Brazil's Pantanal",
            }]

    provider = DDGSProvider(searcher_factory=lambda: FallbackDDGS())

    result = provider.search("Pantanal jaguar Brazil", job={"market": "BR"}, limit=3)

    assert result[0]["source_url"] == "https://www.youtube.com/watch?v=abc123"
    assert result[0]["kind"] == "video"
    assert result[0]["source_name"] == "YouTube via DDGS"


def test_ddgs_image_provider_normalizes_image_results():
    class ImageDDGS:
        def images(self, query: str, **kwargs):
            assert query == "Pantanal jaguar Brazil"
            assert kwargs["backend"] == "duckduckgo"
            return [{
                "title": "Jaguar crossing the Pantanal",
                "image": "https://img.example/jaguar-full.jpg",
                "thumbnail": "https://img.example/jaguar-thumb.jpg",
                "url": "https://source.example/jaguar",
                "source": "Nature Archive",
            }]

    provider = DDGSImageProvider(searcher_factory=lambda: ImageDDGS())
    result = provider.search("Pantanal jaguar Brazil", job={"market": "BR"}, limit=3)

    assert result[0]["provider"] == "ddgs_images"
    assert result[0]["kind"] == "still"
    assert result[0]["source_url"] == "https://img.example/jaguar-full.jpg"
    assert result[0]["thumbnail_url"] == "https://img.example/jaguar-thumb.jpg"


def test_openverse_provider_normalizes_openly_licensed_images():
    def handler(request: httpx.Request):
        assert request.url.host == "api.openverse.org"
        return httpx.Response(200, json={"results": [{
            "title": "Pantanal wetland",
            "url": "https://images.example/pantanal.jpg",
            "thumbnail": "https://images.example/pantanal-thumb.jpg",
            "creator": "Archive Photographer",
            "license": "cc-by",
            "license_version": "4.0",
            "foreign_landing_url": "https://source.example/pantanal",
        }]})

    provider = OpenverseProvider(client=_client(handler))
    result = provider.search("Pantanal wetland", job={}, limit=3)

    assert result[0]["provider"] == "openverse"
    assert result[0]["kind"] == "still"
    assert result[0]["source_url"] == "https://images.example/pantanal.jpg"
    assert result[0]["thumbnail_url"] == "https://images.example/pantanal-thumb.jpg"
    assert "cc-by" in result[0]["rights_hint"]


def test_hub_applies_semantic_reranker_then_keeps_provider_shortlist(tmp_path: Path):
    provider_a = FakeProvider("alpha", [
        {"source_url": f"https://a.example/{index}", "title": f"candidate a{index}", "kind": "video"}
        for index in range(4)
    ])
    provider_b = FakeProvider("beta", [
        {"source_url": f"https://b.example/{index}", "title": f"candidate b{index}", "kind": "video"}
        for index in range(4)
    ])

    class FakeSemanticReranker:
        def rerank(self, query_context, candidates, limit=None):
            rows = []
            for row in candidates:
                item = dict(row)
                index = int(item["source_url"].rsplit("/", 1)[-1])
                item["semantic_score"] = 1.0 - index * 0.1
                item["semantic_provider"] = "fake-openclip"
                rows.append(item)
            rows.sort(key=lambda item: item["semantic_score"], reverse=True)
            return rows[:limit] if limit else rows

    hub = SourceDiscoveryHub(
        providers=[provider_a, provider_b],
        cache_ttl_sec=0,
        max_workers=2,
        per_provider_limit=4,
        per_beat_limit=20,
        shortlist_per_provider=2,
        semantic_reranker=FakeSemanticReranker(),
    )
    result = hub.discover_for_beats(
        {"title": "test"},
        [{"beat_id": "B001", "narration_text": "voice meaning", "footage_search_queries": ["voice meaning"]}],
        tmp_path,
    )["B001"]

    assert len(result) == 4
    assert {item["provider"] for item in result} == {"alpha", "beta"}
    assert all(item["semantic_provider"] == "fake-openclip" for item in result)
    assert sum(item["provider"] == "alpha" for item in result) == 2
    assert sum(item["provider"] == "beta" for item in result) == 2


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_internet_archive_provider_normalizes_movie_records():
    def handler(request: httpx.Request):
        assert request.url.host == "archive.org"
        return httpx.Response(200, json={
            "response": {"docs": [{
                "identifier": "tokyo-quake-1923",
                "title": "Great Kanto Earthquake 1923",
                "description": "Tokyo after the earthquake",
                "creator": "Archive Films",
                "date": "1923",
                "licenseurl": "https://creativecommons.org/publicdomain/mark/1.0/",
            }]},
        })

    provider = InternetArchiveProvider(client=_client(handler))
    result = provider.search("Tokyo earthquake 1923", job={}, limit=4)

    assert result[0]["source_url"] == "https://archive.org/details/tokyo-quake-1923"
    assert result[0]["kind"] == "video"
    assert result[0]["date"] == "1923"
    assert "publicdomain" in result[0]["rights_hint"]


def test_library_of_congress_provider_normalizes_film_results():
    def handler(request: httpx.Request):
        assert request.url.host == "www.loc.gov"
        return httpx.Response(200, json={
            "results": [{
                "id": "https://www.loc.gov/item/12345/",
                "title": "Saigon street scenes, 1968",
                "description": ["Street traffic and civilians"],
                "date": "1968",
                "image_url": ["https://tile.loc.gov/thumb.jpg"],
                "contributor": ["Library of Congress"],
            }],
        })

    provider = LibraryOfCongressProvider(client=_client(handler))
    result = provider.search("Saigon 1968", job={}, limit=4)

    assert result[0]["provider"] == "loc"
    assert result[0]["source_url"] == "https://www.loc.gov/item/12345/"
    assert result[0]["thumbnail_url"] == "https://tile.loc.gov/thumb.jpg"


def test_wikimedia_provider_uses_file_mime_to_distinguish_video_and_still():
    def handler(request: httpx.Request):
        return httpx.Response(200, json={
            "query": {"pages": {
                "10": {
                    "title": "File:Pantanal jaguar.webm",
                    "imageinfo": [{
                        "url": "https://upload.wikimedia.org/jaguar.webm",
                        "mime": "video/webm",
                        "extmetadata": {"LicenseShortName": {"value": "CC BY-SA 4.0"}},
                    }],
                },
                "11": {
                    "title": "File:Pantanal.jpg",
                    "imageinfo": [{
                        "url": "https://upload.wikimedia.org/pantanal.jpg",
                        "mime": "image/jpeg",
                    }],
                },
            }},
        })

    provider = WikimediaCommonsProvider(client=_client(handler))
    result = provider.search("Pantanal", job={}, limit=5)

    assert [item["kind"] for item in result] == ["video", "still"]
    assert result[0]["rights_hint"] == "CC BY-SA 4.0"


def test_optional_providers_normalize_common_response_shapes(monkeypatch):
    def handler(request: httpx.Request):
        host = request.url.host
        if host == "searx.test":
            return httpx.Response(200, json={"results": [{
                "url": "https://video.example/searx",
                "title": "Seoul 1988 opening ceremony",
                "content": "Olympic footage",
                "thumbnail": "https://img.example/searx.jpg",
            }]})
        if host == "api.search.brave.com":
            assert request.headers["X-Subscription-Token"] == "brave-key"
            return httpx.Response(200, json={"results": [{
                "url": "https://video.example/brave",
                "title": "Seoul 1988 Olympics",
                "description": "Opening ceremony",
            }]})
        if host == "api.europeana.eu":
            return httpx.Response(200, json={"items": [{
                "guid": "https://www.europeana.eu/item/1",
                "title": ["Berlin 1989"],
                "dcDescription": ["Fall of the Berlin Wall"],
                "type": "VIDEO",
                "dataProvider": ["European Archive"],
                "edmPreview": ["https://img.example/europeana.jpg"],
                "rights": ["http://rightsstatements.org/vocab/NoC-US/1.0/"],
            }]})
        if host == "catalog.archives.gov":
            assert request.headers["x-api-key"] == "nara-key"
            return httpx.Response(200, json={"body": {"hits": {"hits": [{"_source": {
                "naId": "24746",
                "title": "Signing of the Treaty of Versailles",
                "scopeAndContentNote": "President Wilson and delegates",
                "typeOfMaterials": ["Moving Images"],
                "productionDates": [{"year": 1919}],
            }}]}}})
        raise AssertionError(host)

    client = _client(handler)
    assert SearXNGProvider("https://searx.test", client=client).search("Seoul 1988", job={}, limit=2)[0]["kind"] == "video"
    assert BraveSearchProvider("brave-key", client=client).search("Seoul 1988", job={}, limit=2)[0]["provider"] == "brave"
    assert EuropeanaProvider("eu-key", client=client).search("Berlin 1989", job={}, limit=2)[0]["kind"] == "video"
    nara = NARAProvider("nara-key", client=client).search("Versailles 1919", job={}, limit=2)[0]
    assert nara["source_url"] == "https://catalog.archives.gov/id/24746"
    assert nara["date"] == "1919"

    monkeypatch.setenv("COFI_SEARXNG_URL", "https://searx.test")
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "brave-key")
    monkeypatch.setenv("EUROPEANA_API_KEY", "eu-key")
    monkeypatch.setenv("NARA_API_KEY", "nara-key")
    names = [provider.name for provider in default_providers(client=client, ddgs_factory=lambda: FakeDDGS())]
    assert names == [
        "ddgs", "ddgs_images", "internetarchive_tool", "yt_dlp",
        "internet_archive", "loc", "wikimedia", "openverse",
        "searxng", "brave", "europeana", "nara",
    ]


def test_independent_queries_run_concurrently(tmp_path: Path):
    class SlowProvider(FakeProvider):
        def search(self, query: str, *, job: dict, limit: int) -> list[dict]:
            self.calls.append(query)
            time.sleep(0.15)
            return [{
                "source_url": f"https://example.test/{query.replace(' ', '-')}",
                "title": query,
                "kind": "video",
            }]

    provider = SlowProvider("slow")
    hub = SourceDiscoveryHub(providers=[provider], cache_ttl_sec=0, max_workers=2)
    beats = [
        {"beat_id": "B001", "footage_search_queries": ["query alpha"]},
        {"beat_id": "B002", "footage_search_queries": ["query beta"]},
    ]

    started = time.perf_counter()
    hub.discover_for_beats({"title": "parallel"}, beats, tmp_path)
    elapsed = time.perf_counter() - started

    assert elapsed < 0.26
    assert sorted(provider.calls) == ["query alpha", "query beta"]


def test_provider_errors_redact_configured_api_keys(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("EUROPEANA_API_KEY", "super-secret-key")
    broken = FakeProvider("europeana", error=RuntimeError("request failed wskey=super-secret-key"))
    hub = SourceDiscoveryHub(providers=[broken], cache_ttl_sec=0, max_workers=1)

    hub.discover_for_beats(
        {"title": "Europe"},
        [{"beat_id": "B001", "footage_search_queries": ["Berlin 1989"]}],
        tmp_path,
    )

    assert "super-secret-key" not in hub.last_diagnostics["europeana"]["error"]
    assert "REDACTED" in hub.last_diagnostics["europeana"]["error"]


def test_hub_uses_default_providers_when_none_are_injected(monkeypatch):
    fake = FakeProvider("default-alpha")
    monkeypatch.setattr("documentary.source_discovery.default_providers", lambda: [fake])

    hub = SourceDiscoveryHub()

    assert hub.providers == [fake]


def test_ranked_shortlist_keeps_source_diversity_when_alternatives_exist():
    context = {
        "query": "Woodrow Wilson Versailles 1919",
        "narration_text": "Wilson arrived at Versailles in 1919.",
        "preferred_kind": "video",
    }
    candidates = [
        {
            "provider": "ddgs",
            "source_url": f"https://youtube.example/{index}",
            "title": f"Woodrow Wilson Versailles 1919 clip {index}",
            "kind": "video",
        }
        for index in range(6)
    ] + [
        {
            "provider": "loc",
            "source_url": "https://loc.example/1",
            "title": "President Wilson in Europe 1919",
            "kind": "video",
        },
        {
            "provider": "internet_archive",
            "source_url": "https://archive.example/1",
            "title": "Versailles peace conference 1919",
            "kind": "video",
        },
    ]

    ranked = rank_candidates(context, candidates, limit=4, max_per_provider=2)

    providers = [item["provider"] for item in ranked]
    assert providers.count("ddgs") <= 2
    assert "loc" in providers
    assert "internet_archive" in providers


def test_discovery_global_worker_cap_bounds_all_query_provider_calls(tmp_path: Path):
    import threading

    lock = threading.Lock()
    active = 0
    peak = 0

    class TrackingProvider(FakeProvider):
        def search(self, query: str, *, job: dict, limit: int) -> list[dict]:
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            try:
                time.sleep(0.05)
                return [{
                    "source_url": f"https://{self.name}.example/{query.replace(' ', '-')}",
                    "title": query,
                    "kind": "video",
                }]
            finally:
                with lock:
                    active -= 1

    providers = [TrackingProvider("p1"), TrackingProvider("p2"), TrackingProvider("p3")]
    hub = SourceDiscoveryHub(providers=providers, cache_ttl_sec=0, max_workers=3)
    beats = [
        {"beat_id": f"B{index:03d}", "footage_search_queries": [f"query {index}"]}
        for index in range(1, 5)
    ]

    hub.discover_for_beats({"title": "bounded"}, beats, tmp_path)

    assert peak <= 3


def test_discovery_reports_provider_search_progress_and_persists_cache(tmp_path: Path):
    providers = [
        FakeProvider("p1", [{"source_url": "https://p1.example/item", "title": "item", "kind": "video"}]),
        FakeProvider("p2", [{"source_url": "https://p2.example/item", "title": "item", "kind": "video"}]),
    ]
    hub = SourceDiscoveryHub(providers=providers, cache_ttl_sec=3600, max_workers=2)
    progress = []

    hub.discover_for_beats(
        {"title": "progress"},
        [
            {"beat_id": "B001", "footage_search_queries": ["query one"]},
            {"beat_id": "B002", "footage_search_queries": ["query two"]},
        ],
        tmp_path,
        progress_callback=lambda done, total, provider, query: progress.append((done, total, provider, query)),
    )

    assert progress[0][:2] == (0, 4)
    search_progress = [entry for entry in progress if entry[2] != "semantic_rank"]
    rank_progress = [entry for entry in progress if entry[2] == "semantic_rank"]
    assert search_progress[-1][:2] == (4, 4)
    assert {entry[2] for entry in search_progress[1:]} == {"p1", "p2"}
    assert rank_progress[-1][:3] == (2, 2, "semantic_rank")
    cache = json.loads((tmp_path / ".producer" / "source_discovery" / "cache.json").read_text(encoding="utf-8"))
    assert len(cache["entries"]) == 4


def test_provider_auth_forbidden_opens_circuit_for_later_batches(tmp_path: Path):
    class ForbiddenProvider(FakeProvider):
        def search(self, query: str, *, job: dict, limit: int) -> list[dict]:
            self.calls.append(query)
            request = httpx.Request("GET", "https://blocked.example/search")
            response = httpx.Response(403, request=request)
            raise httpx.HTTPStatusError("forbidden", request=request, response=response)

    provider = ForbiddenProvider("blocked")
    hub = SourceDiscoveryHub(providers=[provider], cache_ttl_sec=0, max_workers=1)

    hub.discover_for_beats(
        {"title": "first"},
        [{"beat_id": "B001", "footage_search_queries": ["first query"]}],
        tmp_path,
    )
    hub.discover_for_beats(
        {"title": "second"},
        [{"beat_id": "B002", "footage_search_queries": ["different query"]}],
        tmp_path,
    )

    assert provider.calls == ["first query"]
    assert hub.last_diagnostics["blocked"]["status"] == "disabled"
