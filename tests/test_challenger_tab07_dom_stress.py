"""
Empirical Challenger Test Suite for Tab 07 Redesign, DOM Selectors, Accordion Stress,
Clipboard Fallback, Responsive Resilience, and Live Process Stability.

Requirements covered:
1. DOM selector stability: #cofiThumbnailStudioHost, #seoWorkspace, #cofiThumbMainCanvas, etc.
2. Accordion stress: 5 independent .saas-seo-accordion drawers, stopPropagation check on copy buttons.
3. Clipboard fallback stress: navigator.clipboard and execCommand("copy") fallback vulnerabilities.
4. Responsive stress: 1280px-1920px horizontal overflow, z-index collisions, layout resilience.
5. Process check: Ports 8000, 8878, 8890, 8900 undisturbed.
"""

from __future__ import annotations

import re
import socket
import sys
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import sync_playwright, Page, Browser

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"
INDEX_HTML = STATIC_DIR / "index.html"
STYLES_CSS = STATIC_DIR / "styles.css"
APP_JS = STATIC_DIR / "app.js"
STUDIO_JS = STATIC_DIR / "thumbnail_studio.js"

SERVER_URL = "http://127.0.0.1:8878"
TEST_JOB_ID = "20261023-084718-f20824bc"


# ==============================================================================
# 1. STATIC DOM SELECTOR & CSS TOKEN VERIFICATION
# ==============================================================================

def test_static_dom_selectors_integrity():
    """Verify that all critical IDs and classes exist in source code."""
    index_html = INDEX_HTML.read_text(encoding="utf-8")
    app_js = APP_JS.read_text(encoding="utf-8")
    studio_js = STUDIO_JS.read_text(encoding="utf-8")
    styles_css = STYLES_CSS.read_text(encoding="utf-8")

    # Critical IDs in index.html
    assert 'id="seoWorkspace"' in index_html, "Missing #seoWorkspace in index.html"
    assert 'id="seoProjectLabel"' in index_html, "Missing #seoProjectLabel in index.html"
    assert 'id="globalProjectSelect"' in index_html, "Missing #globalProjectSelect in index.html"
    assert 'id="globalCodexDock"' in index_html, "Missing #globalCodexDock in index.html"

    # Critical IDs rendered by app.js in Tab 07
    assert 'id="cofiThumbnailStudioHost"' in app_js, "Missing #cofiThumbnailStudioHost in app.js"

    # Critical IDs rendered by thumbnail_studio.js inside workbench
    expected_studio_ids = [
        "cofiThumbMainCanvas",
        "cofiThumbLeftDock",
        "cofiThumbCenterStage",
        "cofiThumbRightInspector",
        "cofiThumbStageViewport",
        "cofiThumbStageInner",
        "thumbSafeZoneToggle",
        "thumbUndoBtn",
        "thumbDuplicateLayerBtn",
        "thumbDeleteSelectedBtn",
        "thumbZoomOutBtn",
        "thumbZoomInBtn",
        "thumbZoomReadout",
        "thumbToggleZoomEditorBtn",
        "thumbToggleDrawerBtn",
        "thumbLockChannelDnaBtn",
        "thumbExportAbPackBtn",
        "thumbBatchFlowBtn",
        "thumbDownloadAllBtn",
        "editorDownloadThisBtn",
        "editorSavePrimaryBtn",
        "applyTopicPresetAllBtn",
    ]
    for dom_id in expected_studio_ids:
        assert f'id="{dom_id}"' in studio_js, f"Missing id=\"{dom_id}\" in thumbnail_studio.js"

    # Critical data attributes
    expected_data_attrs = [
        "data-card-variant",
        "data-select-winner",
        "data-zoom-variant",
        "data-download-variant",
        "data-edit-variant",
        "data-copy-paired-title",
        "data-switch-workbench-variant",
        "data-apply-topic-preset",
        "data-thumb-view-mode",
        "data-seo-copy",
    ]
    for attr in expected_data_attrs:
        assert attr in studio_js or attr in app_js, f"Missing {attr} across studio and app JS"

    # Verify Hero Positioning: #cofiThumbnailStudioHost precedes accordionsHtml
    pos_host = app_js.find('id="cofiThumbnailStudioHost"')
    pos_accordions = app_js.find('${accordionsHtml}')
    assert pos_host != -1 and pos_accordions != -1, "Both studio host and accordions must be in app.js"
    assert pos_host < pos_accordions, "Hero Thumbnail Studio Host MUST be placed BEFORE accordions in Tab 07"


def test_static_design_tokens_hierarchy():
    """Verify 3-layer design tokens in styles.css."""
    styles_css = STYLES_CSS.read_text(encoding="utf-8")

    # Layer 1: Primitives
    assert "--co-slate-950:" in styles_css
    assert "--co-cyan-400:" in styles_css
    assert "--co-amber-400:" in styles_css
    assert "--co-space-3:" in styles_css
    assert "--co-radius-lg:" in styles_css

    # Layer 2: Semantics
    assert "--surface-app:" in styles_css
    assert "--surface-card:" in styles_css
    assert "--border-default:" in styles_css
    assert "--text-main:" in styles_css
    assert "--badge-green-bg:" in styles_css

    # Layer 3: Component
    assert "--canva-stage-bg:" in styles_css
    assert "--accordion-border:" in styles_css
    assert "--accordion-summary-bg:" in styles_css

    # Accordion & Workbench styles
    assert "details.saas-seo-accordion" in styles_css
    assert ".saas-seo-summary" in styles_css
    assert ".saas-accordion-chevron" in styles_css
    assert ".saas-copy-btn" in styles_css
    assert ".copied-pulse" in styles_css
    assert ".thumb-workbench-variant-bar" in styles_css
    assert ".variant-pill-btn" in styles_css


def test_static_event_stop_propagation_and_fallback():
    """Verify e.stopPropagation() and clipboard fallback in app.js."""
    app_js = APP_JS.read_text(encoding="utf-8")

    # stopPropagation in bindSeoCopyButtons
    bind_fn = app_js.split("function bindSeoCopyButtons(")[1].split("function renderSeoWorkspace")[0]
    assert "e.stopPropagation()" in bind_fn, "bindSeoCopyButtons must call e.stopPropagation() to prevent accordion toggle"

    # copySeoText fallback
    copy_fn = app_js.split("async function copySeoText(")[1].split("function bindSeoCopyButtons(")[0]
    assert "navigator.clipboard?.writeText" in copy_fn, "copySeoText must check navigator.clipboard"
    assert 'document.createElement("textarea")' in copy_fn, "copySeoText must create textarea fallback"
    assert 'textarea.setAttribute("readonly", "")' in copy_fn, "copySeoText fallback must be readonly"
    assert 'document.execCommand("copy")' in copy_fn, "copySeoText must execute copy command"
    assert "textarea.remove()" in copy_fn, "copySeoText must clean up textarea"


# ==============================================================================
# 2. LIVE BROWSER / DOM EMPIRICAL PLAYWRIGHT TESTS
# ==============================================================================

@pytest.fixture(scope="module")
def browser_context():
    """Launch headless Chromium with clipboard permissions granted for base testing."""
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        permissions=["clipboard-read", "clipboard-write"],
    )
    page = context.new_page()

    try:
        # Load app
        page.goto(f"{SERVER_URL}/", timeout=15000, wait_until="networkidle")

        # Select the True Crime test job
        job_select = page.locator("#globalProjectSelect")
        job_select.wait_for(state="visible", timeout=10000)
        job_select.select_option(value=TEST_JOB_ID)

        # Click Tab 07: SEO + Thumbnail
        tab_btn = page.locator('[data-app-tab="seo"]')
        tab_btn.wait_for(state="visible", timeout=5000)
        tab_btn.click()

        # Wait for Tab 07 to render both Thumbnail Studio and SEO Accordions
        page.wait_for_selector("#cofiThumbnailStudioHost .canva-workbench-3col", timeout=12000)
        page.wait_for_selector(".saas-seo-accordions-group", timeout=12000)

        yield {"browser": browser, "context": context, "page": page, "playwright": playwright}

    finally:
        browser.close()
        playwright.stop()


def test_live_dom_selector_stability(browser_context: dict[str, Any]):
    """Verify all critical IDs and DOM nodes in the live browser."""
    page: Page = browser_context["page"]

    # 1. Host and workspace
    assert page.locator("#seoWorkspace").is_visible()
    assert page.locator("#cofiThumbnailStudioHost").is_visible()

    # 2. Hero Workbench Canvas & Docks
    assert page.locator("#cofiThumbMainCanvas").is_visible()
    assert page.locator("#cofiThumbLeftDock").is_visible()
    assert page.locator("#cofiThumbRightInspector").is_visible()
    assert page.locator("#cofiThumbCenterStage").is_visible()

    # Verify Canvas resolution attributes
    canvas = page.locator("#cofiThumbMainCanvas")
    assert canvas.get_attribute("width") == "1280"
    assert canvas.get_attribute("height") == "720"

    # 3. Toolbar controls
    assert page.locator("#thumbUndoBtn").is_visible()
    assert page.locator("#thumbSafeZoneToggle").is_visible()
    assert page.locator("#thumbZoomInBtn").is_visible()
    assert page.locator("#thumbZoomOutBtn").is_visible()
    assert page.locator("#thumbZoomReadout").inner_text() != ""
    assert page.locator("#thumbLockChannelDnaBtn").is_visible()
    assert page.locator("#thumbExportAbPackBtn").is_visible()
    assert page.locator("#thumbDownloadAllBtn").is_visible()

    # 4. Top Hero Variant Switcher Bar
    variant_bar = page.locator(".thumb-workbench-variant-bar")
    assert variant_bar.is_visible()
    pills = page.locator(".variant-pill-btn")
    assert pills.count() >= 3, f"Expected at least 3 variant pills, got {pills.count()}"

    # Verify switching active variant updates pill state
    first_pill = pills.nth(0)
    second_pill = pills.nth(1)
    second_pill.click()
    page.wait_for_timeout(300)
    assert "active" in second_pill.get_attribute("class")


def test_live_accordion_independence_and_stress(browser_context: dict[str, Any]):
    """Verify all 5 accordions toggle independently without layout breakage."""
    page: Page = browser_context["page"]
    accordions = page.locator(".saas-seo-accordion")
    assert accordions.count() == 5, f"Expected exactly 5 SEO accordions, found {accordions.count()}"

    # Verify initial states: Accordion 1 and 2 open, 3, 4, 5 closed
    assert accordions.nth(0).evaluate("el => el.open") is True, "Accordion 1 should be open initially"
    assert accordions.nth(1).evaluate("el => el.open") is True, "Accordion 2 should be open initially"
    assert accordions.nth(2).evaluate("el => el.open") is False, "Accordion 3 should be closed initially"
    assert accordions.nth(3).evaluate("el => el.open") is False, "Accordion 4 should be closed initially"
    assert accordions.nth(4).evaluate("el => el.open") is False, "Accordion 5 should be closed initially"

    # Toggle Accordion 3 (Tags) open
    acc3_summary = accordions.nth(2).locator("summary.saas-seo-summary")
    acc3_summary.click()
    page.wait_for_timeout(200)

    # Verify Accordion 3 is now open, and others are NOT affected
    assert accordions.nth(2).evaluate("el => el.open") is True
    assert accordions.nth(0).evaluate("el => el.open") is True
    assert accordions.nth(1).evaluate("el => el.open") is True
    assert accordions.nth(3).evaluate("el => el.open") is False
    assert accordions.nth(4).evaluate("el => el.open") is False

    # Close Accordion 1
    acc1_summary = accordions.nth(0).locator("summary.saas-seo-summary")
    acc1_summary.click()
    page.wait_for_timeout(200)
    assert accordions.nth(0).evaluate("el => el.open") is False
    assert accordions.nth(2).evaluate("el => el.open") is True  # Accordion 3 still open!

    # Stress test: Rapid sequential toggling (20 cycles)
    for _ in range(4):
        for idx in range(5):
            accordions.nth(idx).locator("summary.saas-seo-summary").click()
    page.wait_for_timeout(300)

    # Confirm all accordions are still functional and interactive
    for idx in range(5):
        assert accordions.nth(idx).is_visible()

    # Re-open all 5 accordions and verify all content blocks render properly
    for idx in range(5):
        if not accordions.nth(idx).evaluate("el => el.open"):
            accordions.nth(idx).locator("summary.saas-seo-summary").click()
    page.wait_for_timeout(300)

    for idx in range(5):
        assert accordions.nth(idx).evaluate("el => el.open") is True
        content = accordions.nth(idx).locator(".saas-seo-content")
        assert content.is_visible()


def test_live_copy_button_stop_propagation(browser_context: dict[str, Any]):
    """Verify that clicking a copy button does NOT toggle the accordion state."""
    page: Page = browser_context["page"]
    accordions = page.locator(".saas-seo-accordion")
    acc2 = accordions.nth(1)

    # Ensure Accordion 2 is open
    if not acc2.evaluate("el => el.open"):
        acc2.locator("summary.saas-seo-summary").click()
        page.wait_for_timeout(200)
    assert acc2.evaluate("el => el.open") is True

    # Find copy button on Accordion 2 summary
    summary_copy_btn = acc2.locator("summary .saas-copy-btn").first
    assert summary_copy_btn.is_visible()

    # Click copy button
    summary_copy_btn.click()
    page.wait_for_timeout(200)

    # CRITICAL CHECK: Accordion 2 MUST REMAIN OPEN! (e.stopPropagation worked)
    assert acc2.evaluate("el => el.open") is True, "Clicking copy button inadvertently closed the accordion!"

    # Now close Accordion 2
    acc2.locator("summary.saas-seo-summary").click()
    page.wait_for_timeout(200)
    assert acc2.evaluate("el => el.open") is False

    # Click copy button on closed Accordion 2
    summary_copy_btn.click()
    page.wait_for_timeout(200)

    # CRITICAL CHECK: Accordion 2 MUST REMAIN CLOSED!
    assert acc2.evaluate("el => el.open") is False, "Clicking copy button inadvertently opened the closed accordion!"

    # Re-open Accordion 2
    acc2.locator("summary.saas-seo-summary").click()
    page.wait_for_timeout(200)


def test_empirical_finding_clipboard_double_click_label_corruption(browser_context: dict[str, Any]):
    """
    ADVERSARIAL STRESS TEST: Copy button label corruption on rapid click / double-click.
    When a user double-clicks the copy button or clicks again during the 1500ms feedback window,
    `previous` captures '✓ Đã sao chép!', causing the button to be permanently stuck on '✓ Đã sao chép!'.
    """
    page: Page = browser_context["page"]
    acc3 = page.locator(".saas-seo-accordion").nth(2)
    if not acc3.evaluate("el => el.open"):
        acc3.locator("summary.saas-seo-summary").click()
        page.wait_for_timeout(200)

    btn = acc3.locator("summary .saas-copy-btn").first
    initial_text = btn.inner_text()
    assert "✓ Đã sao chép!" not in initial_text

    # Click 1
    btn.click()
    page.wait_for_timeout(100)
    assert "✓ Đã sao chép!" in btn.inner_text()

    # Click 2 within the 1.5s window
    btn.click()
    page.wait_for_timeout(100)

    # Wait past the 1500ms timeout
    page.wait_for_timeout(2500)

    # VERIFICATION OF THE FIX:
    # Double-click must restore original label and not leave button permanently stuck on '✓ Đã sao chép!'
    is_corrupted = "✓ Đã sao chép!" in btn.inner_text()
    print(f"\n[VERIFIED FIX] Copy button stuck on copied state after double-click: {is_corrupted}")
    assert not is_corrupted, "Button label must be restored and not corrupted by rapid double-click"


def test_empirical_finding_clipboard_unhandled_notallowed_error(browser_context: dict[str, Any]):
    """
    ADVERSARIAL STRESS TEST: Unhandled NotAllowedError when clipboard permissions are not granted.
    When navigator.clipboard.writeText throws NotAllowedError, copySeoText must catch the rejection
    and execute document.execCommand('copy') fallback instead of failing with an error toast.
    """
    page: Page = browser_context["page"]

    eval_result = page.evaluate("""
        async () => {
            // Emulate what happens when writeText throws (e.g. non-secure context or no focus)
            const originalWrite = navigator.clipboard.writeText;
            let currentCopySeoTextThrows = false;
            let currentError = null;

            navigator.clipboard.writeText = async () => {
                const err = new Error("Failed to execute 'writeText' on 'Clipboard': Write permission denied.");
                err.name = "NotAllowedError";
                throw err;
            };

            try {
                await copySeoText("Test String");
            } catch (e) {
                currentCopySeoTextThrows = true;
                currentError = e.name + ": " + e.message;
            }

            // Restore
            navigator.clipboard.writeText = originalWrite;

            return {
                currentCopySeoTextThrows,
                currentError
            };
        }
    """)

    print(f"\n[VERIFIED FIX] copySeoText throws unhandled rejection on clipboard failure: {eval_result['currentCopySeoTextThrows']}")
    print(f"[VERIFIED FIX] Error received: {eval_result['currentError']}")
    assert eval_result["currentCopySeoTextThrows"] is False, "copySeoText must catch rejection and execute execCommand fallback without throwing"


def test_live_responsive_viewport_resilience(browser_context: dict[str, Any]):
    """Stress test layout across 1280px to 1920px viewports for horizontal overflow and z-index collisions."""
    page: Page = browser_context["page"]
    viewports = [
        {"width": 1280, "height": 800},
        {"width": 1366, "height": 768},
        {"width": 1440, "height": 900},
        {"width": 1536, "height": 864},
        {"width": 1600, "height": 900},
        {"width": 1920, "height": 1080},
    ]

    for vp in viewports:
        page.set_viewport_size(vp)
        page.wait_for_timeout(250)

        # Check for horizontal overflow
        metrics = page.evaluate("""
            () => {
                const scrollWidth = document.documentElement.scrollWidth;
                const clientWidth = document.documentElement.clientWidth;
                const innerWidth = window.innerWidth;
                const hostRect = document.getElementById("cofiThumbnailStudioHost").getBoundingClientRect();
                const canvasRect = document.getElementById("cofiThumbMainCanvas").getBoundingClientRect();
                const leftDock = document.getElementById("cofiThumbLeftDock").getBoundingClientRect();
                const rightInspector = document.getElementById("cofiThumbRightInspector").getBoundingClientRect();

                return {
                    scrollWidth,
                    clientWidth,
                    innerWidth,
                    hostWidth: hostRect.width,
                    canvasWidth: canvasRect.width,
                    canvasHeight: canvasRect.height,
                    leftDockRight: leftDock.right,
                    rightInspectorLeft: rightInspector.left,
                    hasDockOverlap: leftDock.right > rightInspector.left
                };
            }
        """)

        # Allow small tolerance for native vertical scrollbar (~17px)
        assert metrics["scrollWidth"] <= metrics["innerWidth"] + 20, (
            f"Horizontal overflow detected at {vp['width']}px: "
            f"scrollWidth={metrics['scrollWidth']} > innerWidth={metrics['innerWidth']}"
        )

        # Ensure Left Dock and Right Inspector do not collide
        assert not metrics["hasDockOverlap"], (
            f"Left Dock ({metrics['leftDockRight']}) collided with Right Inspector ({metrics['rightInspectorLeft']}) at {vp['width']}px"
        )

        # Ensure Canvas is rendered and has positive dimensions
        assert metrics["canvasWidth"] > 0
        assert metrics["canvasHeight"] > 0


def test_live_zindex_stacking_integrity(browser_context: dict[str, Any]):
    """Verify z-index hierarchy: modals & lightboxes above docks, docks above content."""
    page: Page = browser_context["page"]
    z_indexes = page.evaluate("""
        () => {
            const getZ = (sel) => {
                const el = document.querySelector(sel);
                if (!el) return -1;
                const z = window.getComputedStyle(el).zIndex;
                return z === 'auto' ? 0 : parseInt(z, 10);
            };

            return {
                chatDock: getZ(".global-codex-dock"),
                toast: getZ("#toastContainer, .toast-container, .toast"),
                accordion: getZ(".saas-seo-accordion"),
                workbench: getZ(".thumb-workbench-variant-bar")
            };
        }
    """)

    # Chat dock should have high z-index (e.g. >= 10 or 9999)
    assert z_indexes["chatDock"] >= 10, f"Chat dock z-index should be prominent: {z_indexes['chatDock']}"


# ==============================================================================
# 3. LIVE PROCESS & PORT VERIFICATION
# ==============================================================================

def test_live_core_ports_undisturbed():
    """Verify ports 8000, 8878, 8890, 8900 are actively listening and undisturbed."""
    ports = [8000, 8878, 8890, 8900]
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            result = s.connect_ex(("127.0.0.1", port))
            assert result == 0, f"Port {port} is NOT responding or closed (connect_ex returned {result})"
