from __future__ import annotations

import re
from typing import Iterable

_HANGUL_SYLLABLE_RE = re.compile(r"[가-힣]")
_DIGIT_GROUP_RE = re.compile(r"\d+(?:[.,]\d+)*")
_GRAMMAR_BREAK_SUFFIXES = (
    "었지만", "았지만", "였지만", "하지만", "지만",
    "었는데", "았는데", "였는데", "는데", "은데",
    "으면서", "면서", "으며", "하며", "고서", "하고",
    "아서", "어서", "여서", "해서", "니까", "므로",
    "으면", "면", "자마자", "도록", "던", "았던", "었던", "렸던",
    "라는", "다는", "냐는", "자고", "라고", "다고",
    "에서", "으로", "에게", "한테", "부터", "까지",
    "처럼", "보다", "마다", "조차", "마저",
    "은", "는", "이", "가", "을", "를", "와", "과", "로", "에", "도", "만",
    "고", "며", "자", "때", "뒤", "후", "전", "중",
)

# Pre-nominal modifiers/determiners (관형사·부사) that must NEVER be stranded at the end of a subtitle chunk
_NEVER_END_CHUNK_WORDS = {
    "연", "약", "총", "단", "무려", "최대", "최소", "평균", "불과", "겨우",
    "한", "두", "세", "네", "다섯", "여섯", "일곱", "여덟", "아홉", "열",
    "백", "천", "만", "억", "수십", "수백", "수천", "수만", "몇",
    "전", "현", "새", "각", "매", "이", "그", "저", "이런", "그런", "저런",
    "어떤", "무슨", "모든", "온갖", "일명", "소위", "속칭", "이른바",
    "더", "가장", "매우", "아주", "너무", "꼭", "바로", "이미", "아직", "결국",
    "특히", "오직", "단지", "심지어", "과연", "만약", "비록", "설령", "도대체", "왜",
    "수사팀이", "방", "눈앞의", "할", "걸어", "거슬러", "앉아", "켜져", "남아",
    "다음", "지난", "오는", "이번", "작년", "올해", "내년", "당시",
    "덩", "두", "황", "양", "뤄", "탄", "류", "천", "장", "리", "왕", "조",
    "화이화시", "신황현", "후난성", "베이징",
}

# Auxiliary verbs / bound nouns / continuations that must stay attached to the preceding predicate or modifier
_NEVER_START_CHUNK_WORDS = {
    "있던", "있었던", "있는", "있습니다", "있었습니다", "있었죠", "있었다",
    "말았습니다", "버렸습니다", "왔습니다", "갔습니다", "갑니다", "올라갑니다",
    "들어왔습니다", "시작했습니다", "보였습니다", "않았습니다", "못했습니다",
    "겁니다", "것입니다", "걸까요", "때문입니다", "뿐이었습니다", "중이었습니다",
    "따름입니다", "모릅니다", "수밖에", "없었습니다", "마찬가지였습니다",
    "미터", "킬로미터", "킬로그램", "그램", "퍼센트", "위안", "달러", "원", "명", "명의",
    "명이", "명은", "명을", "개", "개의", "개가", "개는", "건", "건의", "차례", "번",
    "주년을", "주년", "주년의", "교사의", "교사는", "교사가", "교사를", "교사",
    "교장은", "교장이", "교장의", "교장", "서기는", "서기가", "서기의", "서기",
    "소장은", "소장이", "소장의", "소장", "원장은", "원장이", "원장",
    "씨는", "씨가", "씨의", "씨를", "씨", "날", "날의", "날에", "전인", "후인", "뒤인",
    "속에", "속에서", "속의", "밑에", "밑에서", "아래", "아래에", "위에", "위에서",
    "앞에", "앞에서", "뒤에", "뒤에서", "가운데", "중에", "중에서",
}

_STRONG_BREATH_ENDINGS = (
    "었지만", "았지만", "였지만", "하지만", "지만",
    "었는데", "았는데", "였는데", "는데", "은데",
    "으면서", "면서", "으며", "하며", "나오며", "흘러나오며", "고서", "하고",
    "아서", "어서", "여서", "해서", "니까", "므로", "자마자", "도록",
    "에서는", "에게는", "으로는", "에는", "에서", "에게", "으로",
    " 끝에", " 결과", " 당시", " 무렵", " 이후", " 직후", " 직전", " 때문에", " 덕분에",
    " 몰아", " 향해", " 위해", " 통해", " 따라", " 대가로", " 채로",
)

_TOPIC_OR_CASE_ENDINGS = (
    "은", "는", "이", "가", "을", "를", "와", "과", "로", "에", "도", "만",
    "고", "며", "자", "때", "뒤", "후", "전", "중", "다",
)


def _bind_atomic_korean_tokens(segment: str) -> list[str]:
    """Pre-group dates, times, addresses, numbers+counters, surnames+titles, and verb+auxiliary pairs into atomic eojeol tokens."""
    s = re.sub(r"\s+", " ", segment.strip())
    if not s:
        return []
    sep = "\u00A0"
    # Bind date/time/address expressions with a temporary non-breaking marker
    s = re.sub(r"(\d{4}년)\s+(\d{1,2}월)\s+(\d{1,2}일)", f"\\1{sep}\\2{sep}\\3", s)
    s = re.sub(r"(\d{4}년)\s+(\d{1,2}월)", f"\\1{sep}\\2", s)
    s = re.sub(r"(\d{1,2}월)\s+(\d{1,2}일)", f"\\1{sep}\\2", s)
    s = re.sub(r"(새벽|오전|오후|밤|아침|저녁)\s+(\d{1,2}시(?:경|가|에|쯤)?)", f"\\1{sep}\\2", s)
    s = re.sub(r"(\d{1,2}시)\s+(무렵|경|쯤)", f"\\1{sep}\\2", s)
    s = re.sub(r"(\d+년)\s+(\d+개월)", f"\\1{sep}\\2", s)
    s = re.sub(r"([가-힣]+로)\s+(\d+호)", f"\\1{sep}\\2", s)
    s = re.sub(r"(\d+층)\s+(\d+호)", f"\\1{sep}\\2", s)
    s = re.sub(r"(\d+호)\s+(교학동|교실에는|교실에|교실|기숙사)", f"\\1{sep}\\2", s)
    # Bind Korean spelled-out numbers or digits + counters/units
    s = re.sub(
        r"([일이삼사오육칠팔구십백천만억]+|한|두|세|네|다섯|여섯|일곱|여덟|아홉|열|열두|열다섯|열여섯|열아홉|스무|서른|마흔|쉰|예순|일흔|여든|아흔|수십|수백|수천|수만|\d+)\s+(미터|킬로미터|킬로그램|센티미터|퍼센트|위안|만\s*위안|원|달러|명|개|건|차례|번|년|개월|일|시간|시|분|초|살|세|구|구덩이|트럭|대|채|곳|권|장|통|봉지|자루|덩어리|주년|여\s*명)[가-힣,.\?!]*",
        lambda m: m.group(0).replace(" ", sep),
        s,
    )
    # Bind 1-syllable surname + title/role
    s = re.sub(
        r"\b(덩|두|황|양|뤄|탄|류|천|장|리|왕|조)\s+(교사|교장|서기|소장|원장|국장|주임|팀장|반장|총리|주석|씨)[가-힣,.\?!]*",
        lambda m: m.group(0).replace(" ", sep),
        s,
    )
    # Bind modifier + bound noun / time noun
    s = re.sub(r"\b(다음|지난|그|이|어느|같은|첫)\s+(날|해|달|주|순간|자리|곳|때|일)[가-힣,.\?!]*", lambda m: m.group(0).replace(" ", sep), s)
    s = re.sub(r"\b(사건|실종|매립|발굴|처형|체포|수사)\s+(당시|직후|직전|이후|당일)[가-힣,.\?!]*", lambda m: m.group(0).replace(" ", sep), s)
    s = re.sub(r"(여드레|사흘|나흘|닷새|엿새|이틀|하루)\s+(전인|후인|뒤인|만에|동안)", f"\\1{sep}\\2", s)
    s = re.sub(r"(눈보라)\s+(치는)\s+(새벽에|새벽)", f"\\1{sep}\\2{sep}\\3", s)
    s = re.sub(r"(불도저를)\s+(몰아)", f"\\1{sep}\\2", s)
    s = re.sub(r"(단)\s+(하나의|한\s+명의|한\s+번도)", lambda m: m.group(0).replace(" ", sep), s)
    s = re.sub(r"(할\s+말을)\s+(잃고\s+말았습니다)", f"할{sep}말을{sep}잃고{sep}말았습니다", s)
    s = re.sub(r"(무슨\s+일이)\s+(벌어졌던\s+걸까요)", f"무슨{sep}일이{sep}벌어졌던{sep}걸까요", s)
    s = re.sub(r"(봄비가)\s+(내리던)", f"\\1{sep}\\2", s)
    s = re.sub(r"(짐을)\s+(챙겨)", f"\\1{sep}\\2", s)
    s = re.sub(r"(문을\s+열고)\s+(들어가)", f"문을{sep}열고{sep}들어가", s)
    s = re.sub(r"(거슬러)\s+(올라갑니다)", f"\\1{sep}\\2", s)
    s = re.sub(r"(걸어)\s+(들어왔습니다|나왔습니다|나갔습니다)", f"\\1{sep}\\2", s)
    s = re.sub(r"(말을\s+걸기)\s+(시작했습니다)", f"말을{sep}걸기{sep}시작했습니다", s)
    s = re.sub(r"(쥐고)\s+(있던)", f"\\1{sep}\\2", s)
    s = re.sub(r"(남아)\s+(있던|있는|있었습니다)", f"\\1{sep}\\2", s)
    s = re.sub(r"(켜져|열려|닫혀|쓰러져|숨겨져|감춰져|묻혀|파묻혀|가려져)\s+(있던|있는|있었습니다|있었죠|있었다)", f"\\1{sep}\\2", s)
    s = re.sub(r"(앉아)\s+(있는|있던|있었습니다)", f"\\1{sep}\\2", s)
    s = re.sub(r"(살아온|살아왔던|지켜온|버텨온|기다려온|숨겨온)\s+(겁니다|것입니다|세월이었습니다)", f"\\1{sep}\\2", s)
    return [w.replace(sep, " ") for w in s.split(" ") if w]


def format_srt_time(seconds: float) -> str:
    total_ms = max(0, round(float(seconds) * 1000))
    hours, rest = divmod(total_ms, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def estimate_spoken_korean_weight(clause: str) -> float:
    """Estimate spoken duration weight of a Korean subtitle phrase based on expanded spoken syllables."""
    s = str(clause or "").strip()
    if not s:
        return 1.0
    try:
        from .voice import normalize_korean_tts_text

        spoken = normalize_korean_tts_text(s)
    except Exception:
        spoken = s
    hangul_count = len(_HANGUL_SYLLABLE_RE.findall(spoken))
    alpha_count = sum(1 for ch in spoken if ch.isascii() and ch.isalpha())
    rem_digits = sum(len(m.group(0).replace(",", "")) for m in _DIGIT_GROUP_RE.finditer(spoken))
    base_syllables = max(2.0, float(hangul_count) + float(alpha_count) * 0.7 + float(rem_digits) * 1.6)
    pause_bonus = 0.0
    if s.endswith((",", "，", "·")):
        pause_bonus = 1.6
    elif s.endswith((".", "?", "!", "…")):
        pause_bonus = 2.2
    return round(base_syllables + pause_bonus, 3)


def _split_long_segment_by_eojeols(segment: str, max_chars: int = 21) -> list[str]:
    words = _bind_atomic_korean_tokens(segment)
    n = len(words)
    if n == 0:
        return []
    joined = " ".join(words)
    hard_max = min(24, max_chars + 3)
    if len(joined) <= max_chars or (len(joined) <= hard_max and n <= 1):
        if len(joined) <= hard_max:
            return [joined]
    if n <= 1:
        raw_words = [w for w in segment.strip().split(" ") if w]
        if len(raw_words) <= 1:
            return [joined]
        words = raw_words
        n = len(words)

    # Use dynamic programming over atomic Korean eojeol groups to find natural single-line breath phrases
    ideal_len = max(13.0, float(max_chars) - 3.5)

    dp: list[tuple[float, list[str]]] = [(0.0, [])] + [(1e9, []) for _ in range(n)]

    for i in range(n):
        if dp[i][0] >= 1e8:
            continue
        for j in range(i + 1, min(n, i + 7) + 1):
            phrase = " ".join(words[i:j])
            plen = len(phrase)
            if plen > hard_max and j > i + 1:
                break

            last_w_raw = words[j - 1]
            last_w = last_w_raw.rstrip(",.?!'\"”’)%")
            is_last_chunk = (j == n)

            # Base cost: squared deviation from ideal_len
            cost = ((plen - ideal_len) ** 2) * 1.15

            # Penalize overly short chunks (< 7 chars or 1 word unless punctuation-bounded)
            if plen < 7:
                cost += (7 - plen) * 24.0
            if j - i == 1 and plen < 9 and not last_w_raw.endswith((",", "，", ".", "?", "!")):
                cost += 45.0
            if plen > max_chars:
                cost += ((plen - max_chars) ** 2) * 18.0
            if plen > hard_max:
                cost += (plen - hard_max) * 500.0

            if not is_last_chunk:
                next_w_raw = words[j]
                next_w = next_w_raw.lstrip("('\"“‘[").rstrip(",.?!'\"”’)%")
                next_first_token = next_w.split(" ")[0]
                last_last_token = last_w.split(" ")[-1]

                # Never strand a pre-nominal modifier at the end of a chunk
                if last_w in _NEVER_END_CHUNK_WORDS or last_last_token in _NEVER_END_CHUNK_WORDS:
                    cost += 400.0
                # Never start the next chunk with an auxiliary verb or bound noun
                if next_w in _NEVER_START_CHUNK_WORDS or next_first_token in _NEVER_START_CHUNK_WORDS:
                    cost += 400.0

                # Penalize breaking right after genitive '의' (possessor/modifier -> head noun)
                if last_last_token.endswith("의") and plen < 19:
                    cost += 58.0

                # Penalize breaking after adnominal modifier (~는 / ~던 / ~은 / ~할 / ~된 / ~한) when phrase is short
                if (
                    last_last_token.endswith(("는", "던", "할", "될", "된", "한", "같은", "라는", "다는"))
                    and not last_last_token.endswith(("있는", "없는", "있던", "없던", "하는", "되는", "않는", "에는", "에서는", "에게는", "으로는"))
                    and plen < 14
                ):
                    cost += 45.0

                # Reward strong syntactic breath boundaries
                if last_w_raw.endswith((",", "，")):
                    cost -= 75.0
                elif last_w.endswith(_STRONG_BREATH_ENDINGS) or phrase.endswith(_STRONG_BREATH_ENDINGS):
                    cost -= 54.0
                elif last_w.endswith(("며", "고", "자")) and plen >= 8:
                    cost -= 44.0
                elif last_w.endswith(("은", "는", "이", "가")) and plen >= 9:
                    cost -= 36.0
                elif last_w.endswith(("을", "를", "에", "로", "도")) and plen >= 10:
                    cost -= 24.0
                elif last_w.endswith(("와", "과")) and plen >= 14:
                    cost -= 16.0
                elif last_w.endswith(_GRAMMAR_BREAK_SUFFIXES):
                    cost -= 20.0
                elif last_w.endswith(_TOPIC_OR_CASE_ENDINGS):
                    cost -= 10.0
                else:
                    # Bare noun without particle likely forms a compound noun with next word
                    cost += 32.0

                if next_first_token in _NEVER_END_CHUNK_WORDS:
                    cost -= 10.0

            cand_cost = dp[i][0] + cost
            if cand_cost < dp[j][0]:
                dp[j] = (cand_cost, dp[i][1] + [phrase])

    best_chunks = dp[n][1]
    return best_chunks if best_chunks else [joined]


def _norm_hangul_alnum(s: str) -> str:
    return re.sub(r"[^가-힣a-zA-Z0-9]", "", s or "")


def align_clause_windows_to_whisper_words(
    clauses: list[str],
    words: list[dict] | None,
    wav_path: str | None = None,
    voice_dur_sec: float | None = None,
) -> list[tuple[str, float, float]]:
    """
    Map each 1-line clause to [w0, w1] in [0.0, 1.0] using Whisper word timestamps (words[].rel_start / rel_end)
    when available, falling back to syllable + WAV pause alignment.
    """
    if not clauses:
        return []
    n_clauses = len(clauses)
    if n_clauses == 1:
        return [(clauses[0], 0.0, 1.0)]

    valid_words = [
        w for w in (words or [])
        if isinstance(w, dict) and str(w.get("word") or "").strip() and w.get("rel_start") is not None and w.get("rel_end") is not None
    ]
    if len(valid_words) >= n_clauses:
        clause_eojeol_counts = [max(1, len(c.split())) for c in clauses]
        n_words = len(valid_words)
        word_norms = [_norm_hangul_alnum(str(w.get("word") or "")) for w in valid_words]
        clause_norms = [_norm_hangul_alnum(c) for c in clauses]

        word_bounds = [0]
        cur_w_idx = 0
        for c_idx in range(n_clauses - 1):
            target_len = max(1, len(clause_norms[c_idx]))
            best_j = min(n_words - (n_clauses - 1 - c_idx), cur_w_idx + 1)
            best_diff = 1e9
            acc_len = 0
            for j in range(cur_w_idx + 1, n_words - (n_clauses - 1 - c_idx) + 1):
                acc_len += len(word_norms[j - 1])
                eojeol_diff = abs((j - cur_w_idx) - clause_eojeol_counts[c_idx]) * 2.5
                char_diff = abs(acc_len - target_len)
                score = char_diff + eojeol_diff
                if score < best_diff:
                    best_diff = score
                    best_j = j
                if acc_len > target_len + 6:
                    break
            word_bounds.append(best_j)
            cur_w_idx = best_j
        word_bounds.append(n_words)

        first_rel = float(valid_words[0].get("rel_start") or 0.0)
        last_rel = max(first_rel + 0.15, float(valid_words[-1].get("rel_end") or 0.15))
        span_dur = max(0.15, max(float(voice_dur_sec or 0.0), last_rel))

        raw_w_bounds = [0.0]
        for k in range(1, n_clauses):
            w_idx = word_bounds[k]
            prev_end = float(valid_words[w_idx - 1].get("rel_end") or 0.0)
            next_start = float(valid_words[w_idx].get("rel_start") or prev_end)
            mid_rel = 0.5 * (prev_end + next_start)
            frac = max(raw_w_bounds[-1] + 0.06, min(1.0 - (n_clauses - k) * 0.06, mid_rel / span_dur))
            raw_w_bounds.append(round(frac, 4))
        raw_w_bounds.append(1.0)
        return [(clauses[i], raw_w_bounds[i], raw_w_bounds[i + 1]) for i in range(n_clauses)]

    weights = [estimate_spoken_korean_weight(c) for c in clauses]
    return align_clause_windows_to_wav(clauses, weights, wav_path=wav_path)


def align_clause_windows_to_wav(
    clauses: list[str],
    weights: list[float],
    wav_path: str | None = None,
) -> list[tuple[str, float, float]]:
    """Compute [w0, w1] windows weighted by spoken syllables, snapping to real acoustic pauses when wav_path is available."""
    if not clauses:
        return []
    total_w = max(1e-6, sum(weights))
    raw_bounds: list[float] = [0.0]
    acc = 0.0
    for idx, w in enumerate(weights):
        acc += w
        raw_bounds.append(1.0 if idx == len(weights) - 1 else acc / total_w)

    if wav_path and len(clauses) > 1:
        try:
            import wave
            import numpy as np

            with wave.open(str(wav_path), "rb") as handle:
                sr = handle.getframerate()
                nch = handle.getnchannels()
                sw = handle.getsampwidth()
                nframes = handle.getnframes()
                raw_pcm = handle.readframes(nframes)
            if sw == 2 and sr >= 8000 and nframes > int(sr * 0.6):
                pcm = np.frombuffer(raw_pcm, dtype=np.int16).astype(np.float32) / 32768.0
                if nch > 1:
                    pcm = pcm.reshape(-1, nch).mean(axis=1)
                hop = max(1, int(sr * 0.010))
                nhop = len(pcm) // hop
                if nhop >= 20:
                    rms = np.sqrt(np.mean(pcm[: nhop * hop].reshape(nhop, hop) ** 2, axis=1) + 1e-12)
                    # Smooth RMS over 50ms window to find true phrase-boundary energy valleys
                    kernel = np.ones(5, dtype=np.float32) / 5.0
                    smooth_rms = np.convolve(rms, kernel, mode="same")
                    p85 = float(np.percentile(smooth_rms, 85))
                    for k in range(1, len(raw_bounds) - 1):
                        expected = raw_bounds[k]
                        lo_idx = max(4, int((expected - 0.10) * nhop))
                        hi_idx = min(nhop - 5, int((expected + 0.10) * nhop))
                        if hi_idx > lo_idx:
                            window_slice = smooth_rms[lo_idx : hi_idx + 1]
                            min_rel = int(np.argmin(window_slice))
                            min_val = float(window_slice[min_rel])
                            if min_val <= p85 * 0.32:
                                snapped = (lo_idx + min_rel) / float(nhop)
                                if raw_bounds[k - 1] + 0.08 <= snapped <= raw_bounds[k + 1] - 0.08:
                                    raw_bounds[k] = snapped
        except Exception:
            pass

    result: list[tuple[str, float, float]] = []
    for idx, c in enumerate(clauses):
        w0 = 0.0 if idx == 0 else round(raw_bounds[idx], 4)
        w1 = 1.0 if idx == len(clauses) - 1 else round(raw_bounds[idx + 1], 4)
        if w1 <= w0:
            w1 = min(1.0, round(w0 + 0.05, 4))
        result.append((c, w0, w1))
    return result


def split_korean_narration_into_short_clauses(
    text: str,
    max_chars: int = 21,
    wav_path: str | None = None,
    words: list[dict] | None = None,
    voice_dur_sec: float | None = None,
) -> list[tuple[str, float, float]]:
    """
    BROADCAST_KOREAN_SUBTITLE_DIRECTOR:
    Splits Korean narration into short, single-line, senior-friendly phrases (12-22 chars, hard max <= 24 chars)
    and returns [(clause_text, w_start, w_end), ...] aligned to Whisper word timestamps or spoken syllables + WAV pauses.
    """
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if not cleaned:
        return []

    hard_max = min(24, max_chars + 3)
    raw_parts = [
        p.strip()
        for p in re.split(r'(?<=[.?!])["”’]?\s+|(?<=,)\s+|(?<=—)\s+', cleaned)
        if p and p.strip()
    ]

    clauses: list[str] = []
    for part in raw_parts:
        if len(part) <= hard_max:
            if clauses and len(part) <= 6 and len(f"{clauses[-1]} {part}") <= hard_max and not clauses[-1].endswith((".", "?", "!")):
                clauses[-1] = f"{clauses[-1]} {part}"
            else:
                clauses.append(part)
        else:
            sub_chunks = _split_long_segment_by_eojeols(part, max_chars=max_chars)
            for sc in sub_chunks:
                if clauses and len(sc) <= 5 and len(f"{clauses[-1]} {sc}") <= hard_max and not clauses[-1].endswith((".", "?", "!")):
                    clauses[-1] = f"{clauses[-1]} {sc}"
                else:
                    clauses.append(sc)

    merged: list[str] = []
    i = 0
    while i < len(clauses):
        cur = clauses[i]
        if len(cur) <= 5 and i + 1 < len(clauses) and len(f"{cur} {clauses[i + 1]}") <= hard_max:
            clauses[i + 1] = f"{cur} {clauses[i + 1]}"
            i += 1
            continue
        merged.append(cur)
        i += 1
    clauses = merged if merged else [cleaned]

    return align_clause_windows_to_whisper_words(clauses, words=words, wav_path=wav_path, voice_dur_sec=voice_dur_sec)


_LATIN_BREATH_WORDS = {
    "but", "yet", "however", "meanwhile", "instead", "suddenly", "then",
    "because", "although", "while", "when", "where", "until", "before", "after",
    "nhưng", "tuy", "khi", "trong", "giữa", "tại", "bởi", "vì", "nếu", "mà", "để",
}


def _estimate_multilang_clause_weight(clause: str) -> float:
    text = str(clause or "").strip()
    if not text:
        return 1.0
    if any("\uac00" <= ch <= "\ud7a3" for ch in text):
        return estimate_spoken_korean_weight(text)
    alpha_num = sum(1 for ch in text if ch.isalnum())
    weight = float(max(2, alpha_num))
    if text.endswith((".", "?", "!", "…", "。")):
        weight += 3.5
    elif text.endswith((",", ";", ":", "—", "、", "，")):
        weight += 1.8
    return weight


def split_multilang_narration_into_clauses(
    text: str,
    max_chars: int = 21,
    wav_path: str | None = None,
    words: list[dict] | None = None,
    voice_dur_sec: float | None = None,
) -> list[tuple[str, float, float]]:
    """Language-aware broadcast subtitle clause splitter (`ko`, `ja`, `zh`, `en`, `vi`, `eu`)."""
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if not cleaned:
        return []

    # 1. Korean: use specialized Hangul eojeol & syllable director
    if any("\uac00" <= ch <= "\ud7a3" for ch in cleaned):
        return split_korean_narration_into_short_clauses(
            cleaned,
            max_chars=max_chars,
            wav_path=wav_path,
            words=words,
            voice_dur_sec=voice_dur_sec,
        )

    # 2. Japanese / Chinese (CJK without spaces)
    if any(("\u3040" <= ch <= "\u30ff") or ("\u4e00" <= ch <= "\u9fff") for ch in cleaned):
        cjk_limit = max(22, max_chars + 4) if max_chars == 19 else max(12, max_chars)
        raw_parts = [p.strip() for p in re.split(r"(?<=[。？！?!；;、，,])\s*", cleaned) if p and p.strip()]
        clauses: list[str] = []
        for part in raw_parts:
            while len(part) > cjk_limit:
                clauses.append(part[:cjk_limit])
                part = part[cjk_limit:].strip()
            if part:
                if clauses and len(part) <= 5 and len(clauses[-1]) + len(part) <= cjk_limit + 2:
                    clauses[-1] += part
                else:
                    clauses.append(part)
        if not clauses:
            clauses = [cleaned]
        weights = [_estimate_multilang_clause_weight(c) for c in clauses]
        return align_clause_windows_to_wav(clauses, weights, wav_path=wav_path)

    # 3. Latin / Vietnamese / English / European broadcast clauses
    latin_limit = 44 if max_chars == 19 else max(18, max_chars)
    if len(cleaned) <= latin_limit:
        return [(cleaned, 0.0, 1.0)]

    raw_parts = [
        p.strip()
        for p in re.split(r'(?<=[.?!;:])["”’]?\s+|(?<=,)\s+|(?<=—)\s+', cleaned)
        if p and p.strip()
    ]
    clauses = []
    for part in raw_parts:
        if len(part) <= latin_limit + 4:
            if clauses and len(part) <= 12 and len(f"{clauses[-1]} {part}") <= latin_limit + 4 and not clauses[-1].endswith((".", "?", "!")):
                clauses[-1] = f"{clauses[-1]} {part}"
            else:
                clauses.append(part)
            continue
        words = part.split(" ")
        cur: list[str] = []
        for idx, wd in enumerate(words):
            cand = " ".join(cur + [wd])
            if cur and len(cand) > latin_limit:
                # Prefer breaking right before a breath conjunction if one appeared in the last 2 tokens
                if len(cur) >= 3 and cur[-1].lower().strip(",;:") in _LATIN_BREATH_WORDS:
                    carry = cur.pop()
                    clauses.append(" ".join(cur))
                    cur = [carry, wd]
                else:
                    clauses.append(" ".join(cur))
                    cur = [wd]
            else:
                cur.append(wd)
            # Soft breath break near target length before conjunction
            if (
                len(" ".join(cur)) >= int(latin_limit * 0.68)
                and idx + 1 < len(words)
                and words[idx + 1].lower().strip(",;:") in _LATIN_BREATH_WORDS
            ):
                clauses.append(" ".join(cur))
                cur = []
        if cur:
            tail = " ".join(cur)
            if clauses and len(tail) <= 10 and len(f"{clauses[-1]} {tail}") <= latin_limit + 6:
                clauses[-1] = f"{clauses[-1]} {tail}"
            else:
                clauses.append(tail)

    if not clauses:
        clauses = [cleaned]
    weights = [_estimate_multilang_clause_weight(c) for c in clauses]
    return align_clause_windows_to_wav(clauses, weights, wav_path=wav_path)


def _resolve_beat_speech_segments(beat: dict, start_sec: float, end_sec: float) -> list[tuple[str, float, float, str | None]]:
    """Return `[(seg_text, abs_start_sec, abs_end_sec, wav_path_or_none), ...]` respecting mid-beat caesura holds."""
    text = str(beat.get("text") or beat.get("narration_text") or "").strip()
    if not text:
        return []
    wav_path = beat.get("audio_path")

    # Priority 1: Explicit `editorial_speech_segments` produced by `editorial_voice_cutter`
    raw_segs = beat.get("editorial_speech_segments")
    if isinstance(raw_segs, list) and len(raw_segs) >= 2:
        out: list[tuple[str, float, float, str | None]] = []
        for seg in raw_segs:
            if not isinstance(seg, dict):
                continue
            stext = str(seg.get("text") or "").strip()
            if not stext:
                continue
            s0 = start_sec + max(0.0, float(seg.get("rel_start") or 0.0))
            s1 = start_sec + max(0.05, float(seg.get("rel_end") or 0.0))
            if s1 > s0 + 0.04:
                out.append((stext, s0, min(end_sec + 0.05, s1), None))
        if len(out) >= 2:
            return out

    # Priority 2: Fallback `editorial_caesuras` + `words[]` gap alignment
    caesuras = beat.get("editorial_caesuras")
    words = beat.get("words")
    if isinstance(caesuras, list) and caesuras and isinstance(words, list) and len(words) >= 2:
        out_w: list[tuple[str, float, float, str | None]] = []
        split_indices = sorted(
            {
                int(c.get("split_word_index"))
                for c in caesuras
                if isinstance(c, dict) and c.get("split_word_index") is not None and 0 < int(c.get("split_word_index")) < len(words)
            }
        )
        if split_indices:
            bounds = [0] + split_indices + [len(words)]
            for bi in range(len(bounds) - 1):
                chunk = words[bounds[bi] : bounds[bi + 1]]
                if not chunk:
                    continue
                ctext = " ".join(str(w.get("word") or "").strip() for w in chunk if str(w.get("word") or "").strip()).strip()
                if not ctext:
                    continue
                s0 = float(chunk[0].get("start") if chunk[0].get("start") is not None else (start_sec + float(chunk[0].get("rel_start") or 0.0)))
                s1 = float(chunk[-1].get("end") if chunk[-1].get("end") is not None else (start_sec + float(chunk[-1].get("rel_end") or 0.2)))
                if s1 > s0 + 0.04:
                    out_w.append((ctext, s0, s1, None))
            if len(out_w) >= 2:
                return out_w

    return [(text, start_sec, end_sec, wav_path)]


def build_srt(beats: Iterable[dict], max_chars: int = 21) -> str:
    blocks: list[str] = []
    cue_index = 1
    for beat in beats:
        text = str(beat.get("text") or beat.get("narration_text") or "").strip()
        if not text:
            continue
        start_sec = float(beat.get("start_sec") or 0.0)
        end_sec = float(beat.get("speech_end_sec") or beat.get("end_sec") or start_sec)
        if end_sec <= start_sec:
            end_sec = start_sec + 0.5

        speech_segments = _resolve_beat_speech_segments(beat, start_sec, end_sec)
        beat_words = beat.get("words") if len(speech_segments) == 1 else None
        for seg_text, seg_start, seg_end, seg_wav in speech_segments:
            dur_sec = max(0.12, seg_end - seg_start)
            clause_windows = split_multilang_narration_into_clauses(
                seg_text,
                max_chars=max_chars,
                wav_path=seg_wav,
                words=beat_words,
                voice_dur_sec=dur_sec,
            )
            if not clause_windows:
                clause_windows = [(seg_text, 0.0, 1.0)]

            for clause_text, w0, w1 in clause_windows:
                c_start = format_srt_time(seg_start + dur_sec * w0)
                c_end = format_srt_time(seg_start + dur_sec * w1)
                blocks.append(f"{cue_index}\n{c_start} --> {c_end}\n{clause_text}")
                cue_index += 1
    return "\n\n".join(blocks) + ("\n" if blocks else "")
