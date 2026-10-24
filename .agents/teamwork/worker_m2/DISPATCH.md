## 2026-10-23T17:57:52Z
You are teamwork_preview_worker (Worker M2: Tab 07 Redesign & App-Wide UI/UX Polish).
Your working directory is: B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\worker_m2

MANDATORY FIRST STEP: Read the authoritative user request at B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\ORIGINAL_REQUEST.md (especially under header ## Follow-up — 2026-10-23T17:41:06Z).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Reference Documents to read:
- `B:\ALL_TOOLS\CofiDocumentary\PROJECT.md`
- `B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\explorer_survey_3\survey_ui_ux.md`
- UI Design Skills:
  - `C:\Users\koing\.gemini\config\skills\agency-ui-designer\SKILL.md`
  - `b:\.agents\skills\design-system\SKILL.md`

FILE WRITE BOUNDARIES (You exclusively own these files; do not edit other files):
- `static/index.html`
- `static/styles.css`
- `static/thumbnail_studio.js`
- `static/app.js`

IMPLEMENTATION TASKS:
1. Redesign Tab 07 (`#seoWorkspace` in `static/index.html`):
   - **Top Priority — Expanded Interactive Thumbnail Canvas Workbench**: Maximize the 16:9 Thumbnail Canvas area at the TOP of Tab 07 so the user can easily compose, preview, edit, switch variants, and export at large scale. Retain and polish variant switcher pills (A/B/C/D), Korean/Vietnamese text input fields, font family & color swatches, mascot/reference lock indicator, and 1-click full-resolution export button.
   - **Bottom — Collapsible SEO Packaging Accordion Drawers**: Group all SEO packaging sections into clean, modern collapsible Accordion drawers (`<details class="saas-seo-accordion">`) below the canvas:
     1. Video Titles (with CTR prediction, psychological hook badges, bilingual translations)
     2. Video Description & Chapter Timestamps
     3. YouTube Tags & Mandatory Hashtags
     4. Keyword DNA & Channel Context
     5. AI Prompts & Reference Metadata
   - Add prominent 1-click Copy buttons inside each accordion drawer with visual "Đã sao chép!" (Copied!) toast/feedback.
2. Upgrade `static/styles.css`:
   - Implement 3-layer design tokens (Primitive -> Semantic -> Component) for consistent colors, surface contrast, subtle borders, shadows, typography scale, and spacing.
   - Style `.saas-seo-accordion` with smooth disclosure transitions, clear headers, badge pills, and polished copy buttons.
   - Polish ergonomics of dense panels across the studio (Overview, Channel DNA, Create Video, Edit).
3. Update `static/thumbnail_studio.js` and `static/app.js`:
   - Audit and preserve 100% of existing DOM element IDs, classes, data attributes, and event handlers (e.g. Mascot Lock, CTR prediction, A/B/C/D variants, drag-and-drop, export).
   - Implement robust clipboard copy handlers (`navigator.clipboard.writeText` with textarea fallback) for all 1-click copy buttons in the SEO accordions.
4. Verification:
   - Run `node --check static/app.js`, `node --check static/thumbnail_studio.js`, and `node --check static/desktop_chrome.js` to ensure zero syntax errors.
   - Do NOT kill, stop, or restart any running processes on ports 8000, 8878, 8890, 8900.

Write your complete handoff report to:
`B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\worker_m2\handoff.md`
Update your `progress.md` with timestamps and send a completion message when done.
