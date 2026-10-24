# CofiDocumentary PyWebView Desktop Trial Design

## Goal

Run the existing CofiDocumentary UI inside a native Windows application window without rewriting or embedding a visible external browser, and without packaging an executable yet.

## Architecture

`desktop_app.py` owns the desktop window. It reuses a healthy CofiDocumentary backend on port 8878 when one already exists. Otherwise it starts the existing FastAPI application through Uvicorn in a daemon thread, waits for the health endpoint, and then opens the unchanged HTML/CSS/JavaScript UI in PyWebView using Edge WebView2.

The trial uses the normal Windows title bar so the window can be moved, resized, minimized, maximized, and closed safely without changing the current UI. Executable packaging and a custom title bar are outside this trial.

## Safety and lifecycle

- Never start a second backend on a port occupied by CofiDocumentary.
- Never reuse a port owned by an unrelated application.
- Try the next local ports when 8878 is occupied by another application.
- Stop Uvicorn on window exit only when this desktop process started it.
- Keep project files, checkpoints, active jobs, providers, and API contracts unchanged.

## Verification

- Unit-test backend detection, port selection, and ownership-sensitive shutdown.
- Run the existing API smoke test.
- Launch a real PyWebView window and confirm the current UI renders from the live backend.

