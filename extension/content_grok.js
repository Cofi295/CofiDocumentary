

(() => {
    if (document.getElementById("glabs-grok-fab")) return;

    let iconUrl;
    try {
        iconUrl = chrome.runtime.getURL("icon48.png");
    } catch (e) {
        return;
    }

    function isAlive() {
        try { return !!chrome.runtime?.id; } catch (e) { return false; }
    }

    
    
    
    window.addEventListener("message", (e) => {
        if (e.source !== window) return;
        const d = e.data;
        if (!d || d.from !== "glabs-grok-task" || !d.taskId || !d.event) return;
        try {
            if (!isAlive()) return;
            chrome.runtime.sendMessage(d, () => {  });
        } catch (err) {  }
    });

    
    
    try {
        chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
            if (msg && msg.type === "GROK_CONTENT_PING") {
                try { sendResponse({ ready: true }); } catch (e) {}
                return false;
            }
            return false;
        });
    } catch (e) {  }

    const styles = document.createElement("style");
    styles.textContent = `
        #glabs-grok-fab {
            position: fixed; bottom: 20px; right: 20px; z-index: 2147483647;
            width: 48px; height: 48px; border-radius: 14px;
            background: rgba(15,17,24,0.85);
            backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 4px 24px rgba(0,0,0,0.4);
            display: flex; align-items: center; justify-content: center;
            cursor: grab; user-select: none;
            transition: box-shadow 0.3s ease, transform 0.2s ease;
        }
        #glabs-grok-fab:hover {
            box-shadow: 0 8px 32px rgba(99,102,241,0.25);
            transform: scale(1.08);
        }
        #glabs-grok-fab-badge {
            position: absolute; top: -5px; right: -5px;
            min-width: 18px; height: 18px; line-height: 18px; text-align: center;
            font-size: 10px; font-weight: 800; color: #fff;
            background: linear-gradient(135deg, #6366f1, #3b82f6);
            border-radius: 9px; padding: 0 5px;
            box-shadow: 0 2px 8px rgba(99,102,241,0.5);
        }
        #glabs-grok-fab.connected #glabs-grok-fab-badge {
            background: linear-gradient(135deg, #22c55e, #10b981);
        }
        #glabs-grok-fab.disconnected #glabs-grok-fab-badge {
            background: linear-gradient(135deg, #ef4444, #f43f5e);
        }

        
        #glabs-grok-overlay {
            position: fixed; inset: 0; z-index: 2147483640;
            background: rgba(8, 10, 18, 0.55);
            backdrop-filter: blur(2px); -webkit-backdrop-filter: blur(2px);
            pointer-events: none; opacity: 0;
            transition: opacity 0.5s ease;
            display: flex; align-items: center; justify-content: center;
            font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
        }
        #glabs-grok-overlay.visible { opacity: 1; pointer-events: auto; }
        #glabs-grok-overlay-card {
            width: 320px; padding: 32px 28px 24px;
            background: rgba(15, 17, 28, 0.75);
            backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
            border-radius: 20px; border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 24px 80px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.04) inset;
            text-align: center; color: #e2e8f0;
        }
        #glabs-grok-overlay-icon {
            width: 48px; height: 48px; border-radius: 12px; margin: 0 auto 14px;
            box-shadow: 0 4px 20px rgba(59,130,246,0.3);
        }
        #glabs-grok-overlay-title {
            font-size: 18px; font-weight: 700; color: #f1f5f9;
            letter-spacing: -0.3px; margin: 0 0 4px;
        }
        #glabs-grok-overlay-subtitle {
            font-size: 12px; font-weight: 500; color: #94a3b8;
            text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 20px;
        }
        #glabs-grok-overlay-status {
            display: flex; align-items: center; justify-content: center; gap: 8px; margin: 0 0 16px;
        }
        #glabs-grok-overlay-dot {
            width: 8px; height: 8px; border-radius: 50%;
            background: #22c55e; box-shadow: 0 0 8px rgba(34,197,94,0.6);
            animation: glabsGrokPulse 1.5s ease-in-out infinite;
        }
        @keyframes glabsGrokPulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(0.85); }
        }
        #glabs-grok-overlay-status-text { font-size: 13px; font-weight: 600; color: #4ade80; }
        #glabs-grok-overlay-counter {
            font-size: 28px; font-weight: 800; margin: 0 0 6px;
            background: linear-gradient(135deg, #60a5fa, #34d399);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            background-clip: text; letter-spacing: -0.5px;
        }
        #glabs-grok-overlay-divider {
            height: 1px; margin: 16px 0;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
        }
        #glabs-grok-overlay-footer { font-size: 11px; color: #64748b; line-height: 1.5; }
    `;
    document.head.appendChild(styles);

    const fab = document.createElement("div");
    fab.id = "glabs-grok-fab";
    fab.title = "G-Labs Auth Helper — Grok mode";
    fab.innerHTML = `<img src="${iconUrl}" width="26" height="26" style="border-radius:7px;opacity:0.9;" /><span id="glabs-grok-fab-badge">G</span>`;
    document.body.appendChild(fab);

    
    let isDragging = false, startX, startY, fabX, fabY, rafId = null;
    const _FAB_BOX = 48;
    fab.addEventListener("mousedown", (e) => {
        isDragging = false;
        startX = e.clientX; startY = e.clientY;
        const r = fab.getBoundingClientRect();
        fabX = r.left; fabY = r.top;
        fab.style.cursor = "grabbing";
        e.preventDefault();
        const onMove = (e2) => {
            const dx = e2.clientX - startX, dy = e2.clientY - startY;
            if (Math.abs(dx) > 3 || Math.abs(dy) > 3) isDragging = true;
            if (!isDragging) return;
            if (rafId) cancelAnimationFrame(rafId);
            rafId = requestAnimationFrame(() => {
                const x = Math.max(0, Math.min(window.innerWidth - _FAB_BOX, fabX + dx));
                const y = Math.max(0, Math.min(window.innerHeight - _FAB_BOX, fabY + dy));
                fab.style.left = `${x}px`; fab.style.top = `${y}px`;
                fab.style.right = "auto"; fab.style.bottom = "auto";
            });
        };
        const onUp = () => {
            document.removeEventListener("mousemove", onMove);
            document.removeEventListener("mouseup", onUp);
            if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
            fab.style.cursor = "grab";
        };
        document.addEventListener("mousemove", onMove);
        document.addEventListener("mouseup", onUp);
    });

    
    const overlay = document.createElement("div");
    overlay.id = "glabs-grok-overlay";
    overlay.innerHTML = `
        <div id="glabs-grok-overlay-card">
            <img id="glabs-grok-overlay-icon" src="${iconUrl}" alt="G-Labs" />
            <div id="glabs-grok-overlay-title">G-Labs Studio</div>
            <div id="glabs-grok-overlay-subtitle">Auth Helper Active</div>
            <div id="glabs-grok-overlay-status">
                <div id="glabs-grok-overlay-dot"></div>
                <span id="glabs-grok-overlay-status-text">Processing...</span>
            </div>
            <div id="glabs-grok-overlay-counter">Session Token #0</div>
            <div id="glabs-grok-overlay-divider"></div>
            <div id="glabs-grok-overlay-footer">
                🤖 Automated authentication in progress<br>
                This tab is managed by G-Labs Studio
            </div>
        </div>
    `;
    document.body.appendChild(overlay);

    let overlayVisible = false;
    function showOverlay(data) {
        if (!overlayVisible) { overlay.classList.add("visible"); overlayVisible = true; }
        updateOverlayData(data);
    }
    function hideOverlay() {
        if (overlayVisible) { overlay.classList.remove("visible"); overlayVisible = false; }
    }
    function updateOverlayData(data) {
        if (!data) return;
        const counter = document.getElementById("glabs-grok-overlay-counter");
        if (counter) counter.textContent = `Session Token #${data.sessionCount || data.tokenCount || 0}`;
    }

    
    try {
        chrome.runtime.onMessage.addListener((msg) => {
            if (msg && msg.type === "GROK_STATE_CHANGED") {
                if (msg.active) showOverlay(msg); else hideOverlay();
            }
            return false;
        });
    } catch (e) {  }

    
    
    
    
    
    
    function ensureMounted() {
        if (!isAlive()) return;
        try {
            if (styles && !styles.isConnected && document.head) document.head.appendChild(styles);
            if (fab && !fab.isConnected && document.body) document.body.appendChild(fab);
            if (overlay && !overlay.isConnected && document.body) document.body.appendChild(overlay);
        } catch (e) {  }
    }
    let _remountScheduled = false;
    function scheduleRemount() {
        if (_remountScheduled) return;
        _remountScheduled = true;
        requestAnimationFrame(() => { _remountScheduled = false; ensureMounted(); });
    }
    let domObserver = null;
    try {
        domObserver = new MutationObserver(scheduleRemount);
        domObserver.observe(document.documentElement, { childList: true, subtree: true });
    } catch (e) {  }

    function updateBadge() {
        if (!isAlive()) {
            try { fab.remove(); overlay.remove(); } catch (e) {}
            if (domObserver) { try { domObserver.disconnect(); } catch (e) {} }
            clearInterval(timer);
            return;
        }
        ensureMounted();  
        try {
            chrome.runtime.sendMessage({ type: "GET_METRICS" }, (response) => {
                if (chrome.runtime.lastError || !response) {
                    fab.className = "disconnected";
                    return;
                }
                fab.className = response.connected ? "connected" : "disconnected";
                
                if (response.grokActive && !overlayVisible) showOverlay(response);
                else if (!response.grokActive && overlayVisible) hideOverlay();
                else if (response.grokActive && overlayVisible) updateOverlayData(response);
            });
        } catch (e) {  }
    }

    updateBadge();
    const timer = setInterval(updateBadge, 3000);
})();
