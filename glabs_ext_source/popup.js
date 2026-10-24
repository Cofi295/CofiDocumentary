

const _SYNC_PORT = 18923;
const _SYNC_URL = `http://127.0.0.1:${_SYNC_PORT}`;

const dotBridge = document.getElementById("dotBridge");
const valBridge = document.getElementById("valBridge");
const dotTab = document.getElementById("dotTab");
const valTab = document.getElementById("valTab");
const dotCaptcha = document.getElementById("dotRecaptcha");
const valCaptcha = document.getElementById("valRecaptcha");

const btnCheck = document.getElementById("btnTest");
const btnVerify = document.getElementById("btnTestCaptcha");
const btnRefresh = document.getElementById("btnRefresh");
const resultBox = document.getElementById("resultBox");

const statTokens = document.getElementById("statTokens");
const statStatus = document.getElementById("statStatus");
const statLast = document.getElementById("statLast");

function init() {
    _pullSnapshot();
    refreshStatus().catch(() => {});

    
    
    setInterval(() => {
        refreshStatus().catch(() => {});
        _pullSnapshot();
    }, 3000);
}

function _pullSnapshot() {
    
    try {
        if (chrome.storage && chrome.storage.local) {
            chrome.storage.local.get(["tokenCount", "lastSuccess"], (data) => {
                if (chrome.runtime.lastError) return;
                statTokens.textContent = data.tokenCount || 0;
                statLast.textContent = data.lastSuccess ? _humanizeAt(data.lastSuccess) : "—";
            });
        }
    } catch (e) {  }

    
    try {
        chrome.runtime.sendMessage({ type: "GET_METRICS" }, (response) => {
            if (chrome.runtime.lastError) return;
            if (response) {
                statTokens.textContent = response.tokenCount || 0;
                statStatus.textContent = response.connected ? "🟢" : "🔴";
                statStatus.style.color = response.connected ? "#22c55e" : "#ef4444";
                if (response.lastSuccess) statLast.textContent = _humanizeAt(response.lastSuccess);
            }
        });
    } catch (e) {  }
}

function _humanizeAt(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffSeconds = Math.floor((now - date) / 1000);

    if (diffSeconds < 60) return `${diffSeconds}s ago`;
    if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`;
    if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)}h ago`;

    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

async function _pingAll() {
    await refreshStatus();
    _pullSnapshot();
}

async function refreshStatus() {
    let r = null;
    try {
        r = await Promise.race([
            chrome.runtime.sendMessage({ type: "CHECK_RENDER" }),
            new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), 6000)),
        ]);
    } catch (e) {  }

    if (!r) {
        _setIndicator(dotBridge, "err"); valBridge.textContent = "Not running";
        _setIndicator(dotTab, "warn"); valTab.textContent = "No session";
        _setIndicator(dotCaptcha, "warn"); valCaptcha.textContent = "—";
        return;
    }
    _setIndicator(dotBridge, r.bridge || "err"); valBridge.textContent = r.bridgeText || "—";
    _setIndicator(dotTab, r.tab || "warn"); valTab.textContent = r.tabText || "—";
    _setIndicator(dotCaptcha, r.captcha || "warn"); valCaptcha.textContent = r.captchaText || "—";
}

function _setIndicator(element, status) {
    element.className = "status-dot";
    if (status === "ok") element.classList.add("dot-ok");
    else if (status === "warn") element.classList.add("dot-warn");
    else if (status === "err") element.classList.add("dot-err");
    else element.classList.add("dot-loading");
}

function _displayMessage(text, type) {
    resultBox.textContent = text;
    resultBox.className = "result-box show " + type;
}

btnCheck.addEventListener("click", async () => {
    btnCheck.disabled = true;
    btnCheck.textContent = "⏳ ...";
    _setIndicator(dotBridge, "loading"); _setIndicator(dotTab, "loading");
    _setIndicator(dotCaptcha, "loading");
    valBridge.textContent = "..."; valTab.textContent = "...";
    valCaptcha.textContent = "...";
    await _pingAll();
    btnCheck.disabled = false;
    btnCheck.textContent = "🔍 Check";
});

btnVerify.addEventListener("click", async () => {
    btnVerify.disabled = true;
    btnVerify.textContent = "⏳ ...";
    resultBox.className = "result-box";

    try {
        
        
        
        
        
        let siteKey = "", action = "";
        try {
            let extId = "";
            try { extId = (await chrome.storage.local.get(["instanceId"])).instanceId || ""; } catch (e) {  }
            const response = await fetch(`${_SYNC_URL}/sync/config`, {
                signal: AbortSignal.timeout(3000),
                headers: extId ? { "X-Ext-Id": extId } : {},
            });
            if (response.ok) {
                const config = await response.json();
                siteKey = config.recaptcha_ent_key || config.site_key || "";
                action = config.recaptcha_action || "";
            }
        } catch (e) {  }

        const result = await chrome.runtime.sendMessage({
            type: "TEST_V",
            site_key: siteKey,
            action: action,
        });

        if (result && result.token) {
            _displayMessage(`✅ Verified (${result.token.length} chars)`, "success");
            _pullSnapshot();
        } else {
            _displayMessage(`❌ ${result ? result.error || "Failed" : "No response"}`, "error");
        }
    } catch (e) {
        _displayMessage(`❌ ${e.message}`, "error");
    } finally {
        btnVerify.disabled = false;
        btnVerify.textContent = "⚡ Verify";
    }
});

btnRefresh.addEventListener("click", async () => {
    btnRefresh.disabled = true;
    btnRefresh.textContent = "⏳ ...";

    try {
        const r = await Promise.race([
            chrome.runtime.sendMessage({ type: "RESET_LAYOUT" }),
            new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), 8000)),
        ]);
        if (r && r.ok) _displayMessage("✅ Cleared cookies & refreshed session", "success");
        else _displayMessage("❌ Refresh failed", "error");
    } catch (e) {
        _displayMessage(`❌ ${e.message}`, "error");
    }

    setTimeout(async () => {
        await _pingAll();
        btnRefresh.disabled = false;
        btnRefresh.textContent = "🔄 Refresh";
    }, 3000);
});

init();

function reportPopupHeight() {
    try { parent.postMessage({ __glabsPopupHeight: document.body.getBoundingClientRect().height }, "*"); } catch (e) {  }
}
try { new ResizeObserver(reportPopupHeight).observe(document.body); } catch (e) {  }
window.addEventListener("load", reportPopupHeight);
reportPopupHeight();
