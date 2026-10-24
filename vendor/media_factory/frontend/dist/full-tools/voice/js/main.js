// ================== Languages / Countries ==================
const LANGUAGES = [
    { code: 'vi',  cc: 'VN', name: 'Tiếng Việt',       color: '#da251d' },
    { code: 'en',  cc: 'US', name: 'English',          color: '#1d4ed8' },
    { code: 'zh',  cc: 'CN', name: '中文',              color: '#dc2626' },
    { code: 'ja',  cc: 'JP', name: '日本語',            color: '#be123c' },
    { code: 'ko',  cc: 'KR', name: '한국어',            color: '#0369a1' },
    { code: 'fr',  cc: 'FR', name: 'Français',         color: '#1e40af' },
    { code: 'de',  cc: 'DE', name: 'Deutsch',          color: '#b45309' },
    { code: 'es',  cc: 'ES', name: 'Español',          color: '#c2410c' },
    { code: 'pt',  cc: 'BR', name: 'Português',        color: '#15803d' },
    { code: 'ru',  cc: 'RU', name: 'Русский',          color: '#3730a3' },
    { code: 'th',  cc: 'TH', name: 'ไทย',              color: '#7c3aed' },
    { code: 'id',  cc: 'ID', name: 'Bahasa Indonesia', color: '#b91c1c' },
    { code: 'hi',  cc: 'IN', name: 'हिन्दी',             color: '#ea580c' },
    { code: 'arb', cc: 'SA', name: 'العربية',           color: '#047857' },
    { code: 'it',  cc: 'IT', name: 'Italiano',         color: '#16a34a' },
];
function ccBadge(l, cls = 'cc-badge') {
    return `<span class="${cls}" style="background:${l.color}18;color:${l.color};border-color:${l.color}40">${l.cc}</span>`;
}
const langOf = (code) => LANGUAGES.find(l => l.code === code) || LANGUAGES[0];

// ================== i18n (UI language) ==================
const i18n = {
    en: {
        tagline: "AI Voice Studio",
        nav_section_create: "CREATE AUDIO",
        nav_section_voices: "VOICES",
        nav_tts: "Text to Speech",
        nav_clone: "Clone Voice",
        nav_design: "Design Voice",
        engine_ready: "Offline engine · Ready",
        tts_title: "Text to Speech",
        tts_placeholder: "Start typing here or paste any text you want to turn into lifelike speech...",
        settings: "Settings",
        history: "History",
        country: "Country / Language",
        voice_select: "Voice",
        default_voice: "Default Voice",
        default_voice_sub: "Auto",
        no_voices_group: "No cloned voice for this country yet — the default voice will be used.",
        voice_lang_hint_default: "The default voice will speak the selected language.",
        chars: "characters",
        speed: "Speed",
        slower: "Slower",
        faster: "Faster",
        diffusion_steps: "Quality",
        fast_gen: "Faster",
        high_quality: "Higher quality",
        reset_values: "↺ Reset values",
        generate: "Generate Speech",
        result: "Latest result",
        download: "Download",
        history_empty: "No audio generated in this session yet.",
        clear_history: "Clear history",
        preview_voice: "Preview voice",
        delete_voice: "Delete voice",
        confirm_delete: "Delete this voice permanently?",
        clone_title: "Clone Voice",
        clone_desc: "Create a new voice from a 3–10 second audio sample. Clear audio with little noise gives the best match.",
        voice_name: "Voice Name",
        clone_name_ph: "E.g., My Voice",
        clone_country: "Voice country (voice group)",
        clone_country_hint: "The voice will be grouped under this country — pick the country in Text to Speech to see it.",
        ref_audio: "Reference Audio",
        upload_tab: "Upload file",
        record_tab: "Record directly",
        record_change: "Change text",
        record_start: "Start recording",
        record_stop: "Stop",
        record_again: "Record again",
        record_hint: "Read naturally in a quiet place. Stop after 3 seconds; automatic stop at 10 seconds.",
        record_unsupported: "This device does not support direct recording.",
        record_permission: "Could not open the microphone. Check Windows microphone permission.",
        record_too_short: "The recording must be at least 3 seconds.",
        record_empty: "The recording is empty. Please try again.",
        record_languages: "Direct recording currently supports Korean, English, and Vietnamese.",
        record_clean_failed: "The microphone recording could not be cleaned. Please record again.",
        upload_hint: "Drag & drop an audio file here, or click to browse",
        upload_formats: "WAV, MP3, M4A, FLAC · 3–10 seconds works best",
        ref_text: "Reference Text (Optional)",
        ref_text_ph: "Type exactly what is said in the sample. Leave empty and Whisper will auto-transcribe.",
        clone_btn: "Create Clone",
        design_title: "Design Voice",
        design_desc: "Generate a voice from a description: gender, age, pitch, texture, emotion...",
        design_name_ph: "E.g., Warm Male Narrator",
        design_instruct: "Voice Description",
        design_instruct_ph: "E.g., male, low pitch, warm, calm narrator",
        presets: "Quick Presets",
        preset_1: "Warm male",
        preset_2: "Gentle female",
        preset_3: "Ad announcer",
        preset_4: "Whispering female",
        preset_5: "Wise old man",
        preset_6: "Lively young female",
        design_btn: "Save Voice Design",
        loading: "Processing...",
        generating: "Generating...",
        t_need_text: "Please enter some text",
        t_need_name_audio: "Voice name and audio file are required",
        t_need_name_instruct: "Voice name and description are required",
        t_cloned: "Voice cloned successfully!",
        t_designed: "Voice saved successfully!",
        t_deleted: "Voice deleted",
        t_generated: "Audio generated",
        t_bad_audio: "This audio file could not be read. Try WAV or MP3.",
        t_saved: "Saved to",
        t_model_loading: "The AI model is still loading, please wait a moment..."
    },
    vi: {
        tagline: "Studio giọng nói AI",
        nav_section_create: "TẠO ÂM THANH",
        nav_section_voices: "GIỌNG NÓI",
        nav_tts: "Đọc văn bản",
        nav_clone: "Sao chép giọng",
        nav_design: "Thiết kế giọng",
        engine_ready: "Engine offline · Sẵn sàng",
        tts_title: "Đọc văn bản",
        tts_placeholder: "Bắt đầu gõ, hoặc dán bất kỳ văn bản nào bạn muốn chuyển thành giọng nói sống động...",
        settings: "Cài đặt",
        history: "Lịch sử",
        country: "Quốc gia / Ngôn ngữ",
        voice_select: "Giọng nói",
        default_voice: "Giọng mặc định",
        default_voice_sub: "Tự động",
        no_voices_group: "Nước này chưa có giọng clone nào — sẽ dùng giọng mặc định.",
        voice_lang_hint_default: "Giọng mặc định sẽ nói theo ngôn ngữ đã chọn.",
        chars: "ký tự",
        speed: "Tốc độ",
        slower: "Chậm",
        faster: "Nhanh",
        diffusion_steps: "Chất lượng",
        fast_gen: "Tạo nhanh",
        high_quality: "Chất lượng cao",
        reset_values: "↺ Khôi phục mặc định",
        generate: "Tạo giọng nói",
        result: "Kết quả mới nhất",
        download: "Tải xuống",
        history_empty: "Chưa có bản âm thanh nào trong phiên này.",
        clear_history: "Xoá lịch sử",
        preview_voice: "Nghe thử giọng",
        delete_voice: "Xoá giọng",
        confirm_delete: "Xoá vĩnh viễn giọng này?",
        clone_title: "Sao chép giọng",
        clone_desc: "Tạo giọng mới từ 3–10 giây âm thanh mẫu. Giọng càng rõ, ít tạp âm — kết quả càng giống.",
        voice_name: "Tên giọng",
        clone_name_ph: "VD: Giọng của tôi",
        clone_country: "Quốc gia của giọng (nhóm giọng)",
        clone_country_hint: "Giọng sẽ được xếp vào nhóm nước này — ở tab Đọc văn bản, chọn nước là thấy giọng.",
        ref_audio: "Âm thanh mẫu",
        upload_tab: "Tải file",
        record_tab: "Thu trực tiếp",
        record_change: "Đổi văn bản",
        record_start: "Bắt đầu thu",
        record_stop: "Dừng",
        record_again: "Thu lại",
        record_hint: "Đọc tự nhiên ở nơi yên tĩnh. Có thể dừng từ giây thứ 3; tự dừng ở giây thứ 10.",
        record_unsupported: "Thiết bị này không hỗ trợ thu âm trực tiếp.",
        record_permission: "Không thể mở micro. Hãy kiểm tra quyền micro của Windows.",
        record_too_short: "Bản thu phải dài ít nhất 3 giây.",
        record_empty: "Bản thu rỗng. Hãy thử lại.",
        record_languages: "Thu trực tiếp hiện hỗ trợ tiếng Hàn, Anh và Việt.",
        record_clean_failed: "Không thể làm sạch bản thu micro. Hãy thu lại.",
        upload_hint: "Kéo thả file âm thanh vào đây, hoặc bấm để chọn",
        upload_formats: "WAV, MP3, M4A, FLAC · tốt nhất 3–10 giây",
        ref_text: "Nội dung âm thanh mẫu (không bắt buộc)",
        ref_text_ph: "Gõ đúng câu nói trong file mẫu. Bỏ trống để Whisper tự nhận diện.",
        clone_btn: "Tạo bản sao giọng",
        design_title: "Thiết kế giọng",
        design_desc: "Tạo giọng theo mô tả: giới tính, độ tuổi, tông giọng, chất giọng, cảm xúc...",
        design_name_ph: "VD: MC nam trầm ấm",
        design_instruct: "Mô tả giọng",
        design_instruct_ph: "VD: male, low pitch, warm, calm narrator",
        presets: "Mẫu nhanh",
        preset_1: "Nam trầm ấm",
        preset_2: "Nữ dịu dàng",
        preset_3: "Nam quảng cáo",
        preset_4: "Nữ thì thầm",
        preset_5: "Ông lão hiền từ",
        preset_6: "Nữ trẻ sôi nổi",
        design_btn: "Lưu giọng thiết kế",
        loading: "Đang xử lý...",
        generating: "Đang tạo...",
        t_need_text: "Vui lòng nhập văn bản",
        t_need_name_audio: "Cần nhập tên giọng và chọn file âm thanh",
        t_need_name_instruct: "Cần nhập tên giọng và mô tả",
        t_cloned: "Đã sao chép giọng thành công!",
        t_designed: "Đã lưu giọng thành công!",
        t_deleted: "Đã xoá giọng",
        t_generated: "Đã tạo xong âm thanh",
        t_bad_audio: "Không đọc được file âm thanh này. Hãy thử WAV hoặc MP3.",
        t_saved: "Đã lưu vào",
        t_model_loading: "Model AI đang khởi động, vui lòng chờ một chút..."
    }
};

let currentLang = localStorage.getItem('ov_lang') || 'vi';
const t = (key) => (i18n[currentLang] && i18n[currentLang][key]) || i18n.en[key] || key;

// ================== State ==================
let voices = [];
let sessionHistory = [];
let ttsLang = localStorage.getItem('ov_tts_lang') || 'vi';
let cloneLang = 'vi';
let designLang = 'vi';
let selectedVoiceId = localStorage.getItem('ov_voice') || '';

const $ = (id) => document.getElementById(id);

const AVATAR_COLORS = [
    'linear-gradient(135deg,#6d5cff,#b44cff)',
    'linear-gradient(135deg,#2563eb,#06b6d4)',
    'linear-gradient(135deg,#f43f5e,#fb923c)',
    'linear-gradient(135deg,#059669,#84cc16)',
    'linear-gradient(135deg,#f59e0b,#ef4444)',
    'linear-gradient(135deg,#8b5cf6,#ec4899)'
];
function avatarColor(id) {
    let h = 0;
    for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
    return AVATAR_COLORS[h % AVATAR_COLORS.length];
}

const voicesFor = (lang) => voices.filter(v => (v.language || 'en') === lang);

// ================== Toast ==================
function showToast(message, type = 'success') {
    const container = $('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'success' ? 'ic-check' : 'ic-close';
    toast.innerHTML = `<svg class="icon"><use href="#${icon}"/></svg><span></span>`;
    toast.querySelector('span').textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(40px)';
        setTimeout(() => toast.remove(), 300);
    }, 3200);
}

function friendlyError(msg) {
    // FastAPI errors arrive as the raw body {"detail": "..."} - show the message,
    // not the JSON wrapper.
    if (typeof msg === 'string' && msg.trim().startsWith('{')) {
        try {
            const d = JSON.parse(msg).detail;
            if (typeof d === 'string') msg = d;
        } catch (e) { /* not JSON, keep as is */ }
    }
    if (typeof msg === 'string' && msg.includes('still loading')) return t('t_model_loading');
    if (typeof msg === 'string' && msg.includes('Format not recognised')) return t('t_bad_audio');
    if (typeof msg === 'string' && msg.includes('Could not clean microphone audio')) {
        return t('record_clean_failed');
    }
    return msg;
}

// ================== Button loading ==================
function setBtnLoading(btn, isLoading, textKey) {
    if (isLoading) {
        btn.dataset.originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = `<span class="eq"><span></span><span></span><span></span><span></span></span> <span class="btn-text">${t('generating')}</span>`;
    } else {
        btn.disabled = false;
        if (btn.dataset.originalHtml) btn.innerHTML = btn.dataset.originalHtml;
        const span = btn.querySelector('.btn-text');
        if (span && textKey) span.textContent = t(textKey);
    }
}

// ================== Language (UI) ==================
function updateLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('ov_lang', lang);
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (t(key)) el.textContent = t(key);
    });
    document.querySelectorAll('[data-i18n-ph]').forEach(el => {
        const key = el.getAttribute('data-i18n-ph');
        if (t(key)) el.placeholder = t(key);
    });
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
        const key = el.getAttribute('data-i18n-title');
        if (t(key)) el.title = t(key);
    });
    document.querySelectorAll('.lang-btn[data-lang]').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-lang') === lang);
    });
    renderAllDropdowns();
    renderDownloadMenu();
    renderHistory();
}

// ================== Tabs ==================
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
        if (item.getAttribute('data-tab') !== 'tab-clone' && cloneSource === 'record') {
            recorder.reset();
        }
        document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
        item.classList.add('active');
        $(item.getAttribute('data-tab')).classList.add('active');
    });
});

document.querySelectorAll('.lang-btn[data-lang]').forEach(btn => {
    btn.addEventListener('click', () => updateLanguage(btn.getAttribute('data-lang')));
});

// Rightbar tabs (Settings / History)
document.querySelectorAll('.rightbar-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.rightbar-tab').forEach(x => x.classList.remove('active'));
        document.querySelectorAll('.rightbar-pane').forEach(x => x.classList.remove('active'));
        tab.classList.add('active');
        $(tab.getAttribute('data-rtab')).classList.add('active');
    });
});

// ================== Dropdown plumbing ==================
function setupDropdown(rootId) {
    const root = $(rootId);
    const trigger = root.querySelector('.dd-trigger');
    trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        const wasOpen = root.classList.contains('open');
        closeAllDropdowns();
        if (!wasOpen) root.classList.add('open');
    });
}
function closeAllDropdowns() {
    document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
}
document.addEventListener('click', (e) => {
    if (!e.target.closest('.dropdown')) closeAllDropdowns();
});

// ---- Language dropdown factory (used by TTS / Clone / Design) ----
function renderLangMenu(menuId, flagId, labelId, getSelected, onSelect) {
    const menu = $(menuId);
    menu.innerHTML = '';
    LANGUAGES.forEach(l => {
        const item = document.createElement('div');
        item.className = 'dd-item' + (getSelected() === l.code ? ' selected' : '');
        const count = voicesFor(l.code).length;
        item.innerHTML = `
            ${ccBadge(l)}
            <div class="dd-item-info"><div class="dd-item-name">${l.name}</div></div>
            ${count ? `<span class="lang-count">${count}</span>` : ''}
            <svg class="icon dd-check"><use href="#ic-check"/></svg>`;
        item.addEventListener('click', () => {
            onSelect(l.code);
            closeAllDropdowns();
        });
        menu.appendChild(item);
    });
    const l = langOf(getSelected());
    $(flagId).outerHTML = ccBadge(l).replace('class="cc-badge"', `class="cc-badge" id="${flagId}"`);
    $(labelId).textContent = l.name;
}

// ---- TTS voice dropdown ----
function renderVoiceMenu() {
    const menu = $('tts-voice-menu');
    menu.innerHTML = '';
    const group = voicesFor(ttsLang);

    // Default voice entry
    const def = document.createElement('div');
    def.className = 'dd-item' + (selectedVoiceId === '' ? ' selected' : '');
    def.innerHTML = `
        <span class="dd-avatar"><svg class="icon"><use href="#ic-user"/></svg></span>
        <div class="dd-item-info">
            <div class="dd-item-name">${t('default_voice')}</div>
            <div class="dd-item-sub">${t('default_voice_sub')}</div>
        </div>
        <svg class="icon dd-check"><use href="#ic-check"/></svg>`;
    def.addEventListener('click', () => { selectVoice(''); closeAllDropdowns(); });
    menu.appendChild(def);

    group.forEach(v => {
        const item = document.createElement('div');
        item.className = 'dd-item' + (selectedVoiceId === v.id ? ' selected' : '');
        const initial = (v.name || '?').trim().charAt(0).toUpperCase();
        item.innerHTML = `
            <span class="dd-avatar" style="background:${avatarColor(v.id)};color:#fff">${initial}</span>
            <div class="dd-item-info">
                <div class="dd-item-name"></div>
                <div class="dd-item-sub ${v.type}">${v.type}</div>
            </div>
            <div class="dd-item-actions">
                <button class="icon-btn small act-preview" title="${t('preview_voice')}"><svg class="icon"><use href="#ic-play"/></svg></button>
                <button class="icon-btn small danger act-delete" title="${t('delete_voice')}"><svg class="icon"><use href="#ic-trash"/></svg></button>
            </div>
            <svg class="icon dd-check"><use href="#ic-check"/></svg>`;
        item.querySelector('.dd-item-name').textContent = v.name;
        item.addEventListener('click', () => { selectVoice(v.id); closeAllDropdowns(); });
        item.querySelector('.act-preview').addEventListener('click', (e) => {
            e.stopPropagation();
            previewVoice(v.id, e.currentTarget);
        });
        item.querySelector('.act-delete').addEventListener('click', (e) => {
            e.stopPropagation();
            deleteVoice(v.id);
        });
        menu.appendChild(item);
    });

    if (group.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'dd-empty';
        empty.textContent = t('no_voices_group');
        menu.appendChild(empty);
    }

    // Trigger display
    const voice = voices.find(v => v.id === selectedVoiceId);
    const avatar = $('tts-voice-avatar');
    if (voice) {
        avatar.style.background = avatarColor(voice.id);
        avatar.style.color = '#fff';
        avatar.textContent = (voice.name || '?').trim().charAt(0).toUpperCase();
        $('tts-voice-label').textContent = voice.name;
    } else {
        avatar.style.background = '';
        avatar.style.color = '';
        avatar.innerHTML = '<svg class="icon"><use href="#ic-user"/></svg>';
        $('tts-voice-label').textContent = t('default_voice');
    }
    $('voice-lang-hint').textContent = voice ? '' : t('voice_lang_hint_default');
}

function renderAllDropdowns() {
    renderLangMenu('tts-lang-menu', 'tts-lang-flag', 'tts-lang-label',
        () => ttsLang,
        (code) => {
            ttsLang = code;
            localStorage.setItem('ov_tts_lang', code);
            // Voice must belong to the selected country group
            const voice = voices.find(v => v.id === selectedVoiceId);
            if (voice && (voice.language || 'en') !== code) selectVoice('');
            renderAllDropdowns();
        });
    renderLangMenu('clone-lang-menu', 'clone-lang-flag', 'clone-lang-label',
        () => cloneLang,
        (code) => {
            cloneLang = code;
            if (cloneSource === 'record' && !recorder.setLanguage(cloneLang)) {
                setCloneSource('upload');
                showToast(t('record_languages'), 'error');
            }
            renderAllDropdowns();
        });
    renderLangMenu('design-lang-menu', 'design-lang-flag', 'design-lang-label',
        () => designLang,
        (code) => { designLang = code; renderAllDropdowns(); });
    renderVoiceMenu();
}

function selectVoice(id) {
    selectedVoiceId = id;
    localStorage.setItem('ov_voice', id);
    renderVoiceMenu();
}

async function loadVoices() {
    try {
        const res = await fetch('/api/voices');
        voices = await res.json();
        const voice = voices.find(v => v.id === selectedVoiceId);
        if (selectedVoiceId && !voice) selectedVoiceId = '';
        if (voice && (voice.language || 'en') !== ttsLang) selectedVoiceId = '';
        renderAllDropdowns();
    } catch (e) {
        console.error('Failed to load voices', e);
    }
}

// ================== Preview voice ==================
async function previewVoice(voiceId, btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="loader" style="border-color:rgba(109,92,255,.3);border-top-color:#6d5cff"></span>';
    try {
        const res = await fetch(`/api/voices/${voiceId}/preview`, { method: 'POST' });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        const player = $('global-preview-player');
        player.src = data.preview_url + '?t=' + Date.now();
        player.play();
    } catch (e) {
        showToast(friendlyError(e.message), 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<svg class="icon"><use href="#ic-play"/></svg>';
    }
}

// ================== Delete voice ==================
async function deleteVoice(voiceId) {
    if (!confirm(t('confirm_delete'))) return;
    try {
        const res = await fetch(`/api/voices/${voiceId}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Delete failed');
        showToast(t('t_deleted'), 'success');
        await loadVoices();
    } catch (e) {
        showToast(friendlyError(e.message), 'error');
    }
}

// ================== Sliders ==================
// The steps slider is an INDEX into these stops, not a free 10..50 range.
// Measured 28/7, same text + same seed at 8/12/16/24/32/48: consecutive step
// counts differ by <0.1% spectrally, and similarity to the reference does NOT
// improve with more steps. Decoding has converged well before 16, so anything
// above it costs time and buys nothing. 16 is the default only for headroom.
const STEP_STOPS = [8, 12, 16, 24, 32];
const DEFAULT_SPEED = '1.0', DEFAULT_STEP_IDX = String(STEP_STOPS.indexOf(24));

function qualityModeValue() {
    return ($('quality-mode') && $('quality-mode').value) || 'balanced';
}

if ($('quality-mode')) {
    const savedMode = localStorage.getItem('ov_quality_mode');
    if (['off', 'balanced', 'deep'].includes(savedMode)) $('quality-mode').value = savedMode;
    $('quality-mode').addEventListener('change', () =>
        localStorage.setItem('ov_quality_mode', qualityModeValue()));
}

function stepsValue() {
    return STEP_STOPS[parseInt($('steps-slider').value)] ?? 32;
}

function showSpeed() {
    $('speed-val').textContent = parseFloat($('speed-slider').value).toFixed(2) + '×';
}

$('speed-slider').addEventListener('input', showSpeed);
$('steps-slider').addEventListener('input', () => {
    $('steps-val').textContent = stepsValue();
});
$('btn-reset').addEventListener('click', () => {
    $('speed-slider').value = DEFAULT_SPEED;
    $('steps-slider').value = DEFAULT_STEP_IDX;
    if ($('quality-mode')) $('quality-mode').value = 'balanced';
    showSpeed();
    $('steps-val').textContent = stepsValue();
});

// Double-click the value badge to type an exact speed (e.g. 1.01).
$('speed-val').addEventListener('dblclick', () => {
    const badge = $('speed-val');
    if (badge.querySelector('input')) return;

    const slider = $('speed-slider');
    const min = parseFloat(slider.min), max = parseFloat(slider.max);
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'slider-val-input';
    input.value = parseFloat(slider.value).toFixed(2);
    badge.textContent = '';
    badge.appendChild(input);
    input.focus();
    input.select();

    let done = false;
    const commit = (save) => {
        if (done) return;
        done = true;
        if (save) {
            const v = parseFloat(input.value.replace(',', '.'));
            if (!isNaN(v)) slider.value = Math.min(max, Math.max(min, v));
        }
        badge.textContent = '';
        showSpeed();
    };
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') commit(true);
        else if (e.key === 'Escape') commit(false);
    });
    input.addEventListener('blur', () => commit(true));
});

// ================== Char count ==================
$('tts-text').addEventListener('input', (e) => {
    $('char-count').textContent = e.target.value.length;
});

// ================== Custom audio player ==================
const audioEl = $('tts-audio-player');

// Waveform: bar pitch in px (bar + gap). Bar count follows the container width,
// so the shape stays readable instead of turning into a dense smear.
const BAR_PITCH = 5;
const MIN_BAR_H = 6;   // % - a silent stretch still shows a hairline
let _audioCtx = null;

function barCount() {
    const w = $('waveform').clientWidth || 600;
    return Math.max(24, Math.min(320, Math.floor(w / BAR_PITCH)));
}

function paintBars(peaks) {
    const wf = $('waveform');
    wf.innerHTML = '';
    const frag = document.createDocumentFragment();
    for (const p of peaks) {
        const bar = document.createElement('div');
        bar.className = 'bar';
        bar.style.height = Math.max(MIN_BAR_H, Math.round(p * 100)) + '%';
        frag.appendChild(bar);
    }
    wf.appendChild(frag);
}

/** Placeholder shown while the real peaks are still being decoded. */
function buildWaveform() {
    const n = barCount();
    paintBars(Array.from({ length: n }, (_, i) =>
        0.30 + 0.14 * Math.sin(i * 0.7) + 0.06 * Math.sin(i * 1.9)));
}

/** Decode the audio and draw its actual peak envelope. */
async function renderRealWaveform(url) {
    try {
        const buf = await (await fetch(url)).arrayBuffer();
        _audioCtx = _audioCtx || new (window.AudioContext || window.webkitAudioContext)();
        const decoded = await _audioCtx.decodeAudioData(buf);
        const data = decoded.getChannelData(0);
        const n = barCount();
        const block = Math.floor(data.length / n) || 1;

        const peaks = new Array(n);
        let max = 1e-6;
        for (let i = 0; i < n; i++) {
            let peak = 0;
            const start = i * block, end = Math.min(start + block, data.length);
            // stride-sample long blocks: a 20-minute file does not need every sample
            const stride = Math.max(1, Math.floor((end - start) / 400));
            for (let j = start; j < end; j += stride) {
                const v = data[j] < 0 ? -data[j] : data[j];
                if (v > peak) peak = v;
            }
            peaks[i] = peak;
            if (peak > max) max = peak;
        }
        // normalise, then soften with a gentle curve so quiet speech stays visible
        paintBars(peaks.map(p => Math.pow(p / max, 0.7)));
        cacheBars();
        updatePlayerProgress();
    } catch (e) {
        console.warn('waveform decode failed, keeping placeholder', e);
    }
}

function fmtTime(s) {
    if (!isFinite(s)) return '0:00';
    const m = Math.floor(s / 60);
    const ss = Math.floor(s % 60);
    return `${m}:${ss.toString().padStart(2, '0')}`;
}

// Repainting every bar on every tick is what made seeking stutter: up to 320
// classList writes per frame, and timeupdate only fires ~4Hz so the playhead
// moved in visible jumps. Now: rAF for smoothness, and only the bars that
// actually crossed the playhead get touched.
let _wfBars = [];
let _wfPlayed = 0;
let _wfRaf = null;
let _seekFrac = null;   // set while dragging, overrides currentTime

function cacheBars() {
    _wfBars = Array.from($('waveform').children);
    _wfPlayed = 0;
}

function updatePlayerProgress() {
    const wf = $('waveform');
    if (_wfBars.length !== wf.children.length) cacheBars();

    const frac = _seekFrac !== null ? _seekFrac
        : (audioEl.duration ? audioEl.currentTime / audioEl.duration : 0);
    const target = Math.round(frac * _wfBars.length);

    if (target > _wfPlayed) {
        for (let i = _wfPlayed; i < target; i++) _wfBars[i].classList.add('played');
    } else if (target < _wfPlayed) {
        for (let i = target; i < _wfPlayed; i++) _wfBars[i].classList.remove('played');
    }
    _wfPlayed = target;

    wf.style.setProperty('--wf-progress', (frac * 100).toFixed(2) + '%');
    $('player-current').textContent = fmtTime(
        _seekFrac !== null ? _seekFrac * (audioEl.duration || 0) : audioEl.currentTime);
}

function startWfLoop() {
    if (_wfRaf) return;
    const tick = () => {
        updatePlayerProgress();
        _wfRaf = (audioEl.paused && _seekFrac === null) ? null : requestAnimationFrame(tick);
    };
    _wfRaf = requestAnimationFrame(tick);
}

audioEl.addEventListener('play', startWfLoop);
audioEl.addEventListener('seeking', updatePlayerProgress);
audioEl.addEventListener('timeupdate', () => { if (!_wfRaf) updatePlayerProgress(); });
audioEl.addEventListener('loadedmetadata', () => {
    $('player-duration').textContent = fmtTime(audioEl.duration);
});
audioEl.addEventListener('play', () => {
    $('player-play-icon').innerHTML = '<use href="#ic-pause"/>';
    $('waveform').classList.add('playing');
});
audioEl.addEventListener('pause', () => {
    $('player-play-icon').innerHTML = '<use href="#ic-play"/>';
    $('waveform').classList.remove('playing');
});
audioEl.addEventListener('ended', () => {
    $('player-play-icon').innerHTML = '<use href="#ic-play"/>';
    $('waveform').classList.remove('playing');
});

$('player-play').addEventListener('click', () => {
    if (audioEl.paused) audioEl.play(); else audioEl.pause();
});

// Scrub: press and drag along the waveform. The bars follow the pointer
// immediately (_seekFrac) and the audio element is only told once on release,
// so dragging never fights the decoder.
(() => {
    const wf = $('waveform');
    const fracAt = (clientX) => {
        const r = wf.getBoundingClientRect();
        return Math.max(0, Math.min(1, (clientX - r.left) / r.width));
    };
    const commit = () => {
        if (_seekFrac !== null && audioEl.duration) {
            audioEl.currentTime = _seekFrac * audioEl.duration;
        }
        _seekFrac = null;
        wf.classList.remove('scrubbing');
        updatePlayerProgress();
    };

    wf.addEventListener('pointerdown', (e) => {
        if (!audioEl.duration) return;
        wf.setPointerCapture(e.pointerId);
        wf.classList.add('scrubbing');
        _seekFrac = fracAt(e.clientX);
        startWfLoop();
    });
    wf.addEventListener('pointermove', (e) => {
        if (_seekFrac === null) return;
        _seekFrac = fracAt(e.clientX);
    });
    wf.addEventListener('pointerup', commit);
    wf.addEventListener('pointercancel', commit);
})();

function showPlayer(url) {
    stopActiveSegment();
    buildWaveform();                 // instant placeholder
    audioEl.src = url;
    fullAudioUrl = url;
    $('tts-result').classList.add('show');
    audioEl.play();
    renderRealWaveform(url);         // swap in the real envelope when decoded
}

// ================== Download / export ==================
// Everything is rendered as 24kHz WAV; the server transcodes on the way out.
const DL_FORMATS = [
    { id: 'wav', name: 'WAV', vi: 'gốc, không nén', en: 'original, uncompressed' },
    { id: 'mp3', name: 'MP3', vi: 'nhẹ, chạy được mọi nơi', en: 'small, plays anywhere' },
    { id: 'm4a', name: 'M4A', vi: 'AAC, hợp điện thoại', en: 'AAC, good for phones' },
    { id: 'flac', name: 'FLAC', vi: 'nén không mất chất', en: 'lossless compression' },
    { id: 'ogg', name: 'OGG', vi: 'Vorbis', en: 'Vorbis' },
];
let fullAudioUrl = '';
let dlFmt = localStorage.getItem('ov_dl_fmt') || 'wav';
if (!DL_FORMATS.some(f => f.id === dlFmt)) dlFmt = 'wav';

// A name the file can carry: the first words of what was spoken.
function nameFromText(text) {
    const s = (text || '').replace(/<break[^>]*>/gi, ' ')
        .replace(/[\\/:*?"<>|]+/g, ' ').replace(/\s+/g, ' ').trim();
    return s ? s.split(' ').slice(0, 6).join(' ').slice(0, 40) : 'cofivoice';
}

async function saveAudio(url, fmt, name) {
    if (!url) return;
    // Inside the desktop app, Python owns the save dialog: WebView2's own dialog
    // filters on "All files (*.*)" and appends no extension, so renaming the
    // file there produced an extension-less file that would not play.
    const api = tbApi();
    if (api && api.save_audio) {
        try {
            const path = await api.save_audio(url, fmt, name);
            if (path) showToast(t('t_saved') + ' ' + path, 'success');
        } catch (e) {
            showToast(friendlyError(String(e && e.message || e)), 'error');
        }
        return;
    }
    // plain browser: let it download normally
    const a = document.createElement('a');
    a.href = `/api/download?src=${encodeURIComponent(url)}`
        + `&fmt=${encodeURIComponent(fmt)}&name=${encodeURIComponent(name)}`;
    a.download = `${name}.${fmt}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
}

function renderDownloadMenu() {
    const menu = $('download-menu');
    if (!menu) return;
    menu.innerHTML = '';
    DL_FORMATS.forEach(f => {
        const item = document.createElement('div');
        item.className = 'dd-item' + (f.id === dlFmt ? ' selected' : '');
        item.innerHTML = `
            <div class="dd-item-info">
                <div class="dd-item-name">${f.name}</div>
                <div class="dd-item-sub">${f[currentLang] || f.en}</div>
            </div>
            <svg class="icon dd-check"><use href="#ic-check"/></svg>`;
        item.addEventListener('click', () => {
            dlFmt = f.id;
            localStorage.setItem('ov_dl_fmt', dlFmt);
            renderDownloadMenu();
            closeAllDropdowns();
            saveAudio(fullAudioUrl, dlFmt, nameFromText($('tts-text').value));
        });
        menu.appendChild(item);
    });
}

if ($('player-download')) {
    $('player-download').addEventListener('click', (e) => {
        e.stopPropagation();
        const root = $('dd-download');
        const wasOpen = root.classList.contains('open');
        closeAllDropdowns();
        if (!wasOpen) root.classList.add('open');
    });
    renderDownloadMenu();
}

// Re-bar on resize so the shape keeps its pitch instead of stretching
let _wfResizeTimer = null;
window.addEventListener('resize', () => {
    clearTimeout(_wfResizeTimer);
    _wfResizeTimer = setTimeout(() => {
        if (audioEl.src) renderRealWaveform(audioEl.src);
    }, 200);
});

// ================== History ==================
function renderHistory() {
    const list = $('history-list');
    list.innerHTML = '';
    $('history-empty').style.display = sessionHistory.length ? 'none' : 'block';
    $('btn-clear-history').style.display = sessionHistory.length ? 'block' : 'none';
    sessionHistory.forEach((item, idx) => {
        const row = document.createElement('div');
        row.className = 'history-item';
        row.style.animationDelay = Math.min(idx * 40, 240) + 'ms';
        row.innerHTML = `
            <button class="icon-btn h-play" title="${t('preview_voice')}"><svg class="icon"><use href="#ic-play"/></svg></button>
            <div class="history-info">
                <div class="history-text"></div>
                <div class="history-voice">${ccBadge(langOf(item.lang), 'cc-badge cc-mini')} <span class="hv-name"></span></div>
            </div>
            <button class="icon-btn h-dl" title="${t('download')}"><svg class="icon"><use href="#ic-download"/></svg></button>`;
        row.querySelector('.history-text').textContent = item.text;
        row.querySelector('.hv-name').textContent = item.voiceName;
        row.querySelector('.h-dl').addEventListener('click', () =>
            saveAudio(item.url, dlFmt, nameFromText(item.text)));
        row.querySelector('.h-play').addEventListener('click', () => showPlayer(item.url));
        list.appendChild(row);
    });
}

$('btn-clear-history').addEventListener('click', () => {
    sessionHistory.forEach(h => URL.revokeObjectURL(h.url));
    sessionHistory = [];
    renderHistory();
});

// ================== Generate TTS (job based) ==================
// Long scripts render segment by segment so there is real progress, a working
// cancel, and a way to re-roll one bad take instead of the whole thing.
let currentJob = null;
let jobPoll = null;

// seconds per 1000 characters, measured on RTX 4060 (batch=1)
const SEC_PER_1K = { 8: 11.6, 12: 16.9, 16: 22.1, 24: 32.0, 32: 41.8 };

function estimateSeconds(chars, step) {
    return (chars / 1000) * (SEC_PER_1K[step] || SEC_PER_1K[32]);
}

function fmtDur(s) {
    if (s < 60) return Math.round(s) + ' giây';
    const m = Math.floor(s / 60);
    return `${m} phút ${Math.round(s % 60)} giây`;
}

function updateEstimate() {
    const el = $('gen-estimate');
    if (!el) return;
    const chars = $('tts-text').value.length;
    el.textContent = chars ? `≈ ${fmtDur(estimateSeconds(chars, stepsValue()))}` : '';
}

function setJobUI(running) {
    $('btn-generate-tts').style.display = running ? 'none' : '';
    const cancel = $('btn-cancel-tts');
    if (cancel) cancel.style.display = running ? '' : 'none';
    const bar = $('job-progress');
    if (bar) bar.style.display = running ? '' : 'none';
}

function renderJob(job) {
    currentJob = job;
    const pct = job.total ? Math.round(job.done / job.total * 100) : 0;
    const fill = $('job-progress-fill');
    if (fill) fill.style.width = pct + '%';
    const label = $('job-progress-label');
    if (label) label.textContent = `${job.done}/${job.total} đoạn · ${pct}%`;

    const box = $('segment-box');
    const list = $('segment-list');
    // Rebuild only when something actually changed - the poll runs every 700ms
    // and a blind re-render would kill hover state and flicker the playing row.
    const sig = job.segments.map(s => s.url || '').join('|');
    if (box && list && sig !== _segSig) {
        _segSig = sig;
        // Only worth showing when the text actually split into pieces
        box.style.display = job.total > 1 ? '' : 'none';
        $('segment-count').textContent = `${job.total} đoạn`;

        stopActiveSegment();
        list.innerHTML = '';
        job.segments.forEach(seg => {
            const row = document.createElement('div');
            row.className = 'seg-item' + (seg.url ? '' : ' pending');
            row.title = `seed ${seg.seed}` + (seg.pause_after ? ` · nghỉ ${seg.pause_after}s` : '');
            row.innerHTML = `
                <button class="icon-btn seg-play" title="Nghe"><svg class="icon"><use href="#ic-play"/></svg></button>
                <span class="seg-text"></span>
                <span class="seg-qa"></span>
                <span class="seg-dur"></span>
                <button class="icon-btn seg-reroll" title="Sinh lại đoạn này">
                    <svg class="icon" viewBox="0 0 24 24"><path d="M20 12a8 8 0 1 1-2.3-5.6M20 4v4h-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </button>`;
            row.querySelector('.seg-text').textContent = seg.text;
            row.querySelector('.seg-dur').textContent = seg.duration ? seg.duration + 's' : '…';
            const qaWarning = seg.qa_status === 'warning';
            const qa = row.querySelector('.seg-qa');
            if (qaWarning) {
                qa.textContent = '⚠ cần nghe lại';
                qa.classList.add('warning');
            } else if (seg.retry_count) {
                qa.textContent = `đã lọc ${seg.retry_count} lần`;
            }
            const play = row.querySelector('.seg-play');
            const reroll = row.querySelector('.seg-reroll');
            if (!seg.url) {
                play.disabled = reroll.disabled = true;
            } else {
                row.dataset.segIndex = seg.index;
                const segAudio = new Audio(seg.url);
                play.addEventListener('click', () => toggleSegmentAudio(segAudio, play));
                segAudio.addEventListener('play', () => paintSegmentButton(play, true));
                segAudio.addEventListener('pause', () => paintSegmentButton(play, false));
                segAudio.addEventListener('ended', () => {
                    paintSegmentButton(play, false);
                    segAudio.currentTime = 0;
                    if (activeSegmentAudio === segAudio) {
                        activeSegmentAudio = null;
                        activeSegmentButton = null;
                    }
                });
                reroll.addEventListener('click', () => rerollSegment(seg.index, reroll));
            }
            list.appendChild(row);
        });
    }

    if (job.state === 'done' && job.full_url) {
        showPlayer(job.full_url);
        finishJob(t('t_generated'), 'success');
        const voice = voices.find(v => v.id === selectedVoiceId);
        const txt = $('tts-text').value;
        sessionHistory.unshift({
            url: job.full_url,
            text: txt.length > 60 ? txt.slice(0, 60) + '…' : txt,
            voiceName: voice ? voice.name : t('default_voice'),
            lang: ttsLang, seed: job.seed
        });
        if (sessionHistory.length > 20) sessionHistory.pop();
        renderHistory();
    } else if (job.state === 'error') {
        finishJob(friendlyError(job.error || 'error'), 'error');
        showResume(job);
    } else if (job.state === 'cancelled') {
        finishJob('Đã huỷ', 'error');
        showResume(job);
    }
}

/** An interrupted job keeps its finished segments; offer to carry on. */
function showResume(job) {
    const bar = $('job-resume');
    if (!bar) return;
    bar.style.display = '';
    $('job-resume-label').textContent =
        `Dừng ở ${job.done}/${job.total} đoạn` +
        (job.state === 'error' ? ' vì lỗi' : '');
}

function hideResume() {
    const bar = $('job-resume');
    if (bar) bar.style.display = 'none';
}

async function resumeJob(restart) {
    if (!currentJob) return;
    hideResume();
    setJobUI(true);
    try {
        const res = await fetch(
            `/api/job/${currentJob.id}/resume?restart=${restart ? 'true' : 'false'}`,
            { method: 'POST' });
        if (!res.ok) throw new Error(await res.text());
        renderJob(await res.json());
        jobPoll = setInterval(async () => {
            try {
                const r = await fetch(`/api/job/${currentJob.id}`);
                if (r.ok) renderJob(await r.json());
            } catch (_) { /* keep polling */ }
        }, 700);
    } catch (e) {
        finishJob(friendlyError(e.message), 'error');
    }
}

let _segSig = null;
let activeSegmentAudio = null;
let activeSegmentButton = null;

function paintSegmentButton(button, playing) {
    const row = button && button.closest('.seg-item');
    if (row) row.classList.toggle('playing', playing);
    const icon = button && button.querySelector('.icon');
    if (icon) icon.innerHTML = `<use href="#${playing ? 'ic-pause' : 'ic-play'}"/>`;
}

function stopActiveSegment() {
    if (activeSegmentAudio) activeSegmentAudio.pause();
    if (activeSegmentButton) paintSegmentButton(activeSegmentButton, false);
    activeSegmentAudio = null;
    activeSegmentButton = null;
}

function toggleSegmentAudio(segAudio, button) {
    audioEl.pause();
    if (activeSegmentAudio === segAudio && !segAudio.paused) {
        stopActiveSegment();
    } else {
        stopActiveSegment();
        activeSegmentAudio = segAudio;
        activeSegmentButton = button;
        segAudio.play().catch(() => stopActiveSegment());
    }
}

function finishJob(msg, kind) {
    clearInterval(jobPoll); jobPoll = null;
    setJobUI(false);
    showToast(msg, kind);
}

async function rerollSegment(index, btn) {
    btn.disabled = true;
    try {
        const res = await fetch(`/api/job/${currentJob.id}/reroll/${index}`, { method: 'POST' });
        if (!res.ok) throw new Error(await res.text());
        const job = await res.json();
        renderJob(job);
        if (job.full_url) showPlayer(job.full_url);
    } catch (e) {
        showToast(friendlyError(e.message), 'error');
    } finally {
        btn.disabled = false;
    }
}

$('btn-generate-tts').addEventListener('click', async () => {
    const text = $('tts-text').value;
    if (!text.trim()) return showToast(t('t_need_text'), 'error');

    const seedField = $('seed-input');
    const seedRaw = seedField ? seedField.value.trim() : '';

    hideResume();
    _segSig = null;
    setJobUI(true);
    try {
        const res = await fetch('/api/job', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text,
                voice_id: selectedVoiceId || null,
                speed: parseFloat($('speed-slider').value),
                num_step: stepsValue(),
                language: ttsLang,
                mode: qualityModeValue(),
                seed: seedRaw === '' ? null : parseInt(seedRaw)
            })
        });
        if (!res.ok) throw new Error(await res.text());
        const job = await res.json();
        if (seedField && seedRaw === '') seedField.placeholder = 'đã dùng ' + job.seed;
        renderJob(job);

        jobPoll = setInterval(async () => {
            try {
                const r = await fetch(`/api/job/${job.id}`);
                if (r.ok) renderJob(await r.json());
            } catch (_) { /* keep polling */ }
        }, 700);
    } catch (e) {
        finishJob(friendlyError(e.message), 'error');
    }
});

if ($('btn-cancel-tts')) {
    $('btn-cancel-tts').addEventListener('click', async () => {
        if (!currentJob) return;
        await fetch(`/api/job/${currentJob.id}/cancel`, { method: 'POST' });
    });
}

// ================== Tag bar ==================
// Inserts at the caret and keeps focus in the editor, so a tag can be dropped
// mid-sentence without losing your place.
function insertTag(tag) {
    const ta = $('tts-text');
    const start = ta.selectionStart, end = ta.selectionEnd;
    ta.value = ta.value.slice(0, start) + tag + ta.value.slice(end);
    const caret = start + tag.length;
    ta.focus();
    ta.setSelectionRange(caret, caret);
    ta.dispatchEvent(new Event('input'));   // refresh char count + estimate
}

// ---- Auto: insert <break> by rule, no API ----
// Only <break>, deliberately. Emotion tags were measured to pull the cloned
// voice off the reference in ko/ja (1.3x-3.8x the run-to-run wobble), so they
// are never placed automatically. A break is spliced-in silence - the model
// never generates it, so it cannot affect the voice at all.
// Breaks depend on STRUCTURE, not meaning, which is why punctuation is enough
// and no language understanding is needed.
const SENT_END = /([.!?。！？…]+["'”’)\]]*)\s+/g;
const BREAK_PARA = 0.7;    // blank line / new paragraph
const BREAK_QUESTION = 0.4;  // after a question - let it land
const BREAK_RHYTHM = 0.3;  // every Nth sentence, so long reads still breathe
const RHYTHM_EVERY = 3;

function autoBreaks(text) {
    // never stack onto breaks the user already placed
    const hasBreak = /<break[^>]*>\s*$/;
    let inserted = 0;

    const paras = text.split(/\n{2,}/);
    const out = paras.map(para => {
        const parts = para.split(SENT_END);
        // split() with one capture group gives [text, punct, text, punct, ...]
        let rebuilt = '';
        let sentIdx = 0;
        for (let i = 0; i < parts.length; i += 2) {
            const body = parts[i];
            const punct = parts[i + 1];
            rebuilt += body + (punct || '');
            if (punct === undefined) break;
            sentIdx++;
            const isQuestion = /[?？]/.test(punct);
            const isLast = i + 2 >= parts.length || !parts[i + 2];
            let secs = 0;
            if (isQuestion) secs = BREAK_QUESTION;
            else if (sentIdx % RHYTHM_EVERY === 0) secs = BREAK_RHYTHM;
            if (secs && !isLast && !hasBreak.test(rebuilt)) {
                rebuilt += `<break time="${secs}s"/>`;
                inserted++;
            }
            rebuilt += ' ';
        }
        return rebuilt.trim();
    });

    let joined = '';
    out.forEach((p, i) => {
        joined += p;
        if (i < out.length - 1) {
            if (!hasBreak.test(joined)) { joined += `<break time="${BREAK_PARA}s"/>`; inserted++; }
            joined += '\n\n';
        }
    });
    return { text: joined, inserted };
}

function runAutoTag(btn) {
    const ta = $('tts-text');
    if (!ta.value.trim()) return showToast(t('t_need_text'), 'error');
    const { text, inserted } = autoBreaks(ta.value);
    ta.value = text;
    ta.dispatchEvent(new Event('input'));
    showToast(inserted ? `Đã chèn ${inserted} khoảng nghỉ` : 'Không có chỗ nào cần nghỉ thêm',
              inserted ? 'success' : 'error');
    void btn;
}

if ($('tag-bar')) {
    $('tag-bar').addEventListener('click', (e) => {
        const chip = e.target.closest('.tag-chip');
        if (!chip) return;
        if (chip.id === 'btn-autotag') { runAutoTag(chip); return; }
        if (chip.id === 'tag-more') {
            $('tag-extra').classList.toggle('open');
            chip.textContent = $('tag-extra').classList.contains('open') ? 'thu gọn' : 'thêm…';
            return;
        }
        insertTag(chip.dataset.tag);
    });
}

if ($('btn-job-resume')) {
    $('btn-job-resume').addEventListener('click', () => resumeJob(false));
}
if ($('btn-job-restart')) {
    $('btn-job-restart').addEventListener('click', () => resumeJob(true));
}

// ================== Custom title bar ==================
// pywebview injects window.pywebview.api asynchronously; guard every call so a
// click before it lands is a no-op rather than a console error.
function tbApi() {
    return (window.pywebview && window.pywebview.api) || null;
}
if ($('tb-min')) {
    $('tb-min').addEventListener('click', () => tbApi() && tbApi().minimize());
    $('tb-max').addEventListener('click', () => tbApi() && tbApi().toggle_maximize());
    $('tb-close').addEventListener('click', () => tbApi() && tbApi().close());
    // double-clicking the bar toggles maximise, like a native window
    $('tb-max') && document.querySelector('.titlebar-drag')
        .addEventListener('dblclick', () => tbApi() && tbApi().toggle_maximize());
}

if ($('segment-toggle')) {
    $('segment-toggle').addEventListener('click', () => {
        $('segment-box').classList.toggle('open');
    });
}

if ($('btn-seed-dice')) {
    $('btn-seed-dice').addEventListener('click', () => {
        $('seed-input').value = Math.floor(Math.random() * 2147483647);
    });
}
$('tts-text').addEventListener('input', updateEstimate);
$('steps-slider').addEventListener('input', updateEstimate);

// ================== Upload (Clone) ==================
const uploadArea = $('upload-area');
const fileInput = $('clone-audio');
let cloneSource = 'upload';

const recorder = new window.CloneRecorder({
    onError: key => showToast(t(key), 'error'),
    onStateChange: (state, seconds = 0, previewUrl = '') => {
        const elapsed = Math.floor(seconds);
        $('record-timer').textContent = `00:${String(elapsed).padStart(2, '0')} / 00:10`;
        $('record-stop').disabled = state !== 'recording' || seconds < 3;
        $('record-start').hidden = state === 'recording' || state === 'preview';
        $('record-stop').hidden = state !== 'recording';
        $('record-reset').hidden = state !== 'preview';
        $('record-preview').hidden = state !== 'preview';
        $('record-panel').classList.toggle('recording', state === 'recording');
        $('btn-clone').disabled = state === 'recording' || state === 'requesting_permission';
        if (previewUrl) {
            $('record-preview').src = previewUrl;
        } else if (state === 'idle') {
            $('record-preview').removeAttribute('src');
            $('record-preview').load();
        }
    },
});

function setCloneSource(source) {
    if (source === 'record' && !recorder.setLanguage(cloneLang)) {
        showToast(t('record_languages'), 'error');
        source = 'upload';
    }
    cloneSource = source;
    const recording = source === 'record';
    $('clone-source-upload').classList.toggle('active', !recording);
    $('clone-source-record').classList.toggle('active', recording);
    $('clone-source-upload').setAttribute('aria-selected', String(!recording));
    $('clone-source-record').setAttribute('aria-selected', String(recording));
    uploadArea.style.display = recording || fileInput.files.length ? 'none' : 'block';
    $('file-chip').style.display = !recording && fileInput.files.length ? 'flex' : 'none';
    $('record-panel').hidden = !recording;
    if (!recording) recorder.reset();
}

$('clone-source-upload').addEventListener('click', () => setCloneSource('upload'));
$('clone-source-record').addEventListener('click', () => setCloneSource('record'));
$('record-random').addEventListener('click', () => recorder.randomizePrompt());
$('record-start').addEventListener('click', () => {
    recorder.start().catch(error => showToast(t(error.message), 'error'));
});
$('record-stop').addEventListener('click', () => recorder.stop());
$('record-reset').addEventListener('click', () => recorder.reset());

function fmtSize(bytes) {
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function showFileChip(file) {
    $('file-chip').style.display = 'flex';
    $('file-chip-name').textContent = file.name;
    $('file-chip-size').textContent = fmtSize(file.size);
    uploadArea.style.display = 'none';
}

function clearFile() {
    fileInput.value = '';
    $('file-chip').style.display = 'none';
    uploadArea.style.display = cloneSource === 'record' ? 'none' : 'block';
}

uploadArea.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});
uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        showFileChip(fileInput.files[0]);
    }
});
fileInput.addEventListener('change', () => {
    if (fileInput.files.length) showFileChip(fileInput.files[0]);
});
$('file-chip-remove').addEventListener('click', clearFile);

// ================== Clone ==================
$('btn-clone').addEventListener('click', async () => {
    const name = $('clone-name').value.trim();
    const recorded = cloneSource === 'record';
    const file = recorded ? recorder.getFile() : fileInput.files[0];
    if (!name || !file) return showToast(t('t_need_name_audio'), 'error');

    const btn = $('btn-clone');
    setBtnLoading(btn, true, 'clone_btn');

    const formData = new FormData();
    formData.append('name', name);
    formData.append('ref_audio', file);
    formData.append('ref_text', recorded ? recorder.getTranscript() : $('clone-text').value);
    formData.append('language', cloneLang);
    formData.append('recorded', String(recorded));

    try {
        const res = await fetch('/api/clone', { method: 'POST', body: formData });
        if (!res.ok) throw new Error(await res.text());
        showToast(t('t_cloned'), 'success');

        $('clone-name').value = '';
        $('clone-text').value = '';
        clearFile();
        recorder.reset();

        // Jump to TTS with the new voice's country selected
        ttsLang = cloneLang;
        localStorage.setItem('ov_tts_lang', ttsLang);
        await loadVoices();
        const newest = voicesFor(ttsLang).slice(-1)[0];
        if (newest) selectVoice(newest.id);
        $('nav-tts').click();
    } catch (e) {
        showToast(friendlyError(e.message), 'error');
    } finally {
        setBtnLoading(btn, false, 'clone_btn');
    }
});

window.addEventListener('beforeunload', () => recorder.destroy());

// ================== Presets ==================
document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        $('design-instruct').value = btn.getAttribute('data-preset');
        document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
    });
});

// ================== Design ==================
$('btn-design').addEventListener('click', async () => {
    const name = $('design-name').value;
    const instruct = $('design-instruct').value;
    if (!name || !instruct) return showToast(t('t_need_name_instruct'), 'error');

    const btn = $('btn-design');
    setBtnLoading(btn, true, 'design_btn');

    try {
        const res = await fetch('/api/design', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, instruct, language: designLang })
        });
        if (!res.ok) throw new Error(await res.text());
        showToast(t('t_designed'), 'success');

        $('design-name').value = '';
        $('design-instruct').value = '';
        document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('selected'));

        ttsLang = designLang;
        localStorage.setItem('ov_tts_lang', ttsLang);
        await loadVoices();
        const newest = voicesFor(ttsLang).slice(-1)[0];
        if (newest) selectVoice(newest.id);
        $('nav-tts').click();
    } catch (e) {
        showToast(friendlyError(e.message), 'error');
    } finally {
        setBtnLoading(btn, false, 'design_btn');
    }
});

// ================== Theme (light / dark) ==================
let currentTheme = localStorage.getItem('ov_theme') || 'dark';

function applyTheme(theme) {
    currentTheme = theme;
    localStorage.setItem('ov_theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
    $('theme-icon').innerHTML = theme === 'dark' ? '<use href="#ic-sun"/>' : '<use href="#ic-moon"/>';
}

$('btn-theme').addEventListener('click', () => {
    applyTheme(currentTheme === 'light' ? 'dark' : 'light');
});

// ================== Canh bao thiet bi (GPU / CPU) ==================
// Chay bang CPU thi cham gap 40-50 lan. Truoc day chuyen do dien ra hoan toan
// im lang: khach chi thay "tao mai khong xong" va tuong app hong, con minh thi
// phai soi Task Manager tung anh mot de doan. Gio noi thang tren giao dien.
let _lastHealthEvent = 0;

function renderDeviceBanner(h) {
    let el = $('device-banner');
    if (!el) {
        el = document.createElement('div');
        el.id = 'device-banner';
        el.style.cssText =
            'position:fixed;left:50%;transform:translateX(-50%);bottom:18px;z-index:9999;' +
            'max-width:min(720px,92vw);padding:11px 16px;border-radius:12px;' +
            'background:#7a2e0e;color:#ffe9d6;border:1px solid #c2410c;' +
            'box-shadow:0 8px 28px #0007;font-size:13.5px;line-height:1.5;' +
            'display:flex;gap:10px;align-items:flex-start';
        document.body.appendChild(el);
    }
    el.innerHTML = '<span style="font-size:16px;line-height:1.2">⚠</span><span></span>';
    el.lastChild.textContent = h.message;
    el.style.display = 'flex';
}

function hideDeviceBanner() {
    const el = $('device-banner');
    if (el) el.style.display = 'none';
}

async function pollHealth() {
    try {
        const h = await (await fetch('/api/health')).json();
        if (h.device === 'cpu' && h.message) renderDeviceBanner(h);
        else hideDeviceBanner();

        // event_id chi tang khi co su kien moi -> toast dung mot lan, khong lap
        if (h.event_id > _lastHealthEvent) {
            _lastHealthEvent = h.event_id;
            if (h.event === 'switched_to_gpu')
                showToast('GPU đã rảnh — đã chuyển sang GPU, từ giờ sẽ nhanh bình thường.',
                          'success');
        }
    } catch (e) { /* server chua len hoac dang ban - lan sau hoi tiep */ }
}

pollHealth();
setInterval(pollHealth, 15000);

// ================== Init ==================
applyTheme(currentTheme);
setupDropdown('dd-tts-lang');
setupDropdown('dd-tts-voice');
setupDropdown('dd-clone-lang');
setupDropdown('dd-design-lang');
updateLanguage(currentLang);
loadVoices();
