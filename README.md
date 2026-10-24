# COFI DOCUMENTARY

Hệ điều hành sản xuất video tài liệu dài 2–30 phút, gom toàn bộ luồng từ tìm chủ đề đến dựng và kiểm tra video trong một giao diện tiếng Việt.

Luồng chuẩn:

`COFI RADAR -> Codex/Gemini nghiên cứu + viết kịch bản + chia cảnh -> CofiVoice tạo giọng + SRT -> Codex + Gemini tìm và kiểm tra tư liệu -> kiểm tra độ phủ -> CofiRemotion dựng + xem trước -> kiểm tra cuối`

Mỗi đoạn hình ảnh dùng một `beat_id` ổn định trong `visual_manifest.json`. Kịch bản, giọng đọc, SRT, tư liệu và mã dựng đều bám vào cùng mã đoạn này để có thể tiếp tục chính xác sau khi phiên làm việc bị ngắt.

Các bộ máy dùng chung được tích hợp vào app:

- COFI RADAR: tìm ngách/chủ đề cho kênh mới hoặc video tiếp theo của kênh đang chạy.
- Codex CLI hoặc Gemini CLI: nghiên cứu, viết kịch bản và chia hình ảnh.
- CofiVoice: tạo giọng đọc theo từng đoạn và xuất SRT đồng bộ.
- Codex CLI + Gemini CLI: cùng tìm tư liệu cho từng đoạn và ghi nguồn/timestamp/chất lượng.
- CofiRemotion: dựng video, lưu trạng thái dựng và mở phần xem trước trực tiếp trong app.

Tìm footage dùng ba lớp. Lớp discovery fan-out nhiều nguồn: DDGS video, DDGS Images, Internet Archive, yt-dlp/YouTube, Library of Congress, Wikimedia Commons, Openverse và các provider tùy chọn SearXNG/Brave/Europeana/NARA. OpenCLIP so câu voice/visual intent với thumbnail hoặc ảnh thật khi provider có preview; metadata/entity/year vẫn là fallback cho nguồn không có preview. Mỗi provider chỉ giữ 2-3 candidate tốt nhất để tránh tải bừa theo từ khóa.

`python -m documentary.footage_search_tool --query "Woodrow Wilson Versailles 1919 archival footage" --narration "<câu voice của beat>" --workspace "<job-workspace>" --market "US" --limit 3`

Thứ tự fallback là: semantic shortlist -> local repo tools tải video/ảnh + representative frames -> Codex/Gemini xem media thật để ACCEPT/REJECT -> nếu REJECT thì AI trả query mới cho chính local tools tìm lại -> AI visual chỉ cho beat vẫn thiếu sau khi đã hoàn tất vòng video thật và ảnh thật. Không còn local Ollama/vision service bắt buộc trong Footage.

### Candidate inspection tools

Ngoài lớp search, Codex/Gemini có một CLI inspection on-demand: `python -m documentary.footage_inspection_tool`.

- `scenes`: PySceneDetect chia video thành shot để không phải quét frame mù trên clip dài.
- `dedupe`: ImageHash loại các representative frame gần trùng nhau.
- `gallery`: gallery-dl tải media từ URL/site mà yt-dlp không hỗ trợ tốt.
- `transcribe`: faster-whisper chỉ dùng cho clip inspection thiếu caption/VTT/subtitle. Mặc định `base`, CPU, `int8`; có thể đổi qua `COFI_FASTER_WHISPER_MODEL`, `COFI_FASTER_WHISPER_DEVICE`, `COFI_FASTER_WHISPER_COMPUTE_TYPE`.

OpenCLIP nạp lazy khi có thumbnail/still thật cần so với voice; không có preview thì bỏ qua model và dùng metadata rank. Caption có sẵn vẫn được ưu tiên trước faster-whisper; visual inspection của Codex/Gemini vẫn là gate cuối trước khi ACCEPT.

Chạy `run.bat`, sau đó mở `http://127.0.0.1:8878`.

Một bước không được coi là hoàn tất chỉ vì đã có tệp. Tư liệu phải khớp nội dung, có đoạn thời gian dùng được và đủ độ phủ; bản dựng phải đạt thời lượng/độ phân giải/FPS đã đặt; video cuối phải qua kiểm tra thực tế. Nếu không tìm được tư liệu chính xác, hệ thống phải báo thiếu thay vì chèn tư liệu không liên quan.

Video chuẩn tham chiếu Nepal: `benchmarks/nepal_flood_5min_reference.json` và `benchmarks/nepal_flood_5min_ko.mp4`.

Kiểm thử: `python -m pytest -q --basetemp=.pytest_tmp`
