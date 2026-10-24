# Multi-source Footage Discovery Design

## Goal

Giữ Codex CLI / Gemini CLI là lớp hiểu câu voice, xem media thật và quyết định ACCEPT/REVIEW/REJECT, nhưng chuyển phần discovery ban đầu sang một hub đa nguồn chạy song song để tăng độ phủ theo chủ đề, quốc gia và thời kỳ, đồng thời giảm số lượt AI phải tự mò web.

## Architecture

`visual beat -> query normalization -> multi-source discovery -> dedupe/cache -> lexical/entity/year ranking -> top candidates -> Codex/Gemini visual inspection -> yt-dlp/ffmpeg/ffprobe -> ACCEPT/REVIEW/REJECT`

Discovery Hub không được tự ACCEPT footage. Mọi kết quả hub chỉ là candidate metadata. Quy tắc hiện tại trong `documentary/footage.py` về tải/preview representative frames, timestamp, technical validation, watermark/logo, context match và rights risk vẫn là gate cuối.

## Source providers

### Luôn bật, không cần API key

- DDGS video/web search: broad discovery cho YouTube và web video toàn cầu.
- Internet Archive Advanced Search API: archive đa chủ đề, lịch sử, phim/tư liệu cũ.
- Library of Congress JSON API: phim, video, ảnh và tài liệu số hóa của LOC.
- Wikimedia Commons MediaWiki API: video/ảnh có metadata/license rõ và đa quốc gia.

### Tự bật khi có cấu hình

- SearXNG qua `COFI_SEARXNG_URL`: metasearch tự host, thêm coverage và fallback.
- Brave Search qua `BRAVE_SEARCH_API_KEY`: video/web search có cấu trúc.
- Europeana qua `EUROPEANA_API_KEY`: di sản văn hóa từ hàng nghìn tổ chức châu Âu.
- NARA Catalog API qua `NARA_API_KEY`: moving images và digital objects của US National Archives.

Provider lỗi, timeout, thiếu key hoặc rate-limit không được làm fail toàn bộ footage phase. Hub ghi diagnostic ngắn rồi trả kết quả từ các provider còn sống.

## Query strategy

Mỗi beat dùng `footage_search_queries`; nếu trống thì tạo fallback query từ `narration_text`, `visual_description`, `purpose`, title và market. Query được normalize và dedupe theo batch/search_group.

Để hỗ trợ nội dung đa quốc gia, hub không ép market thành bộ lọc cứng. `market` chỉ làm region hint cho general web search. Archive providers vẫn tìm global. Query tiếng bản địa được giữ nguyên; khi planner đã tạo query tiếng Anh thì cả hai cùng được dùng.

## Ranking

Hub tính pre-score chỉ để chọn candidate nào đáng đưa cho Codex/Gemini trước:

- token/entity overlap giữa query/voice/visual description và title/description;
- exact year bonus;
- strong year-mismatch penalty, ví dụ query 1919 nhưng title chỉ có 1969;
- source trust bonus cho archive/chính thức;
- video bonus khi beat ưu tiên sourced video;
- duplicate URL collapse;
- không tự kết luận semantic match chỉ từ metadata.

Mỗi beat nhận tối đa một pool nhỏ đã xếp hạng để prompt không phình context.

## Cache and concurrency

- Cache theo normalized query + provider trong `.producer/source_discovery/cache.json`.
- TTL mặc định 24 giờ, cấu hình bằng `COFI_DISCOVERY_CACHE_TTL_SEC`.
- Query giống nhau chỉ chạy một lần và được tái dùng cho các beat cùng search_group.
- Provider calls chạy song song tối đa `COFI_DISCOVERY_WORKERS` (mặc định 6).
- Timeout mỗi provider mặc định 8 giây; lỗi một nguồn không chặn nguồn khác.

## Integration with Codex/Gemini

`build_worker_prompt()` nhận thêm `discovery_candidates` đã compact. Prompt yêu cầu:

1. xem pool discovery trước;
2. nếu candidate phù hợp thì tải/inspect thật;
3. nếu pool yếu hoặc không đủ thì Codex/Gemini vẫn được tự web search như hiện tại;
4. mọi candidate discovery vẫn phải qua visual inspection + ffprobe trước ACCEPT.

Như vậy Codex/Gemini vẫn là engine vận hành chính và có quyền bỏ toàn bộ kết quả hub.

## Performance target

Trên máy hiện tại, một `yt-dlp ytsearch5` thử nghiệm mất khoảng 5.2 giây, trong khi các archive HTTP API phản hồi khoảng 0.1-0.8 giây. Mục tiêu của hub là:

- discovery metadata p50 <= 2.5 giây/query group khi cache miss;
- cache hit p50 <= 50 ms;
- giảm ít nhất 50% số web-search metadata commands mà Codex/Gemini phải tự chạy trên batch có query lặp;
- end-to-end footage phase kỳ vọng nhanh hơn khoảng 1.5-3x trên job dài có nhiều beat, tùy tỷ lệ thời gian nằm ở download/inspection; không hứa tăng tương đương cho các beat phải tải và xem nhiều video nặng.

## Failure handling

- Không provider nào là single point of failure.
- Không lưu API key vào artifact/prompt/log.
- Cache chỉ lưu metadata tìm kiếm, không thay đổi `asset_registry`.
- Nếu hub không có kết quả, worker prompt hoạt động như trước và tự tìm web.

## Acceptance criteria

1. Có provider abstraction và ít nhất DDGS, Internet Archive, LOC, Wikimedia hoạt động theo cùng schema.
2. Brave, SearXNG, Europeana, NARA tự bật khi env tương ứng tồn tại.
3. Query dedupe + cache có test.
4. Year mismatch 1919/1969 bị hạ rank bằng test deterministic.
5. Footage worker prompt nhận candidate pool nhưng vẫn bắt buộc visual inspection trước ACCEPT.
6. Provider failure không làm footage batch fail.
7. Test suite hiện có vẫn pass.

