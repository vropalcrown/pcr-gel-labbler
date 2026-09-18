# 🛠️ Ready-to-paste remediation prompt

Copy everything inside the fenced block below into your coding agent (or use it as your own checklist).

---

```text
ROLE
You are a senior Python/PyQt6 + vanilla-JS engineer. Fix the bug and security audit findings in
this repository (`pcr-gel-labbler`: a PyQt6 gel-electrophoresis annotator in `gel_labeler/` plus a
browser version in `docs/`). Work in small, reviewable commits and keep the app shippable after
every step.

GROUND RULES
1. Never break previously saved data: keep reading old `*_labels.json` files, old
   `.autosave_session.json` files and the existing `pcr_gel_genie_session` localStorage key.
2. The desktop app and the web app must keep the same label/colony schema (id, text, x, y, color,
   font_size, font_family, rotation; colony: id, x, y, radius, area, is_manual).
3. Don't rewrite files wholesale — make surgical edits and preserve the existing Blender-style
   dark theme, keyboard shortcuts and toolbar layout.
4. After each phase: `python -m pyflakes run.py create_mock_gel.py create_shortcut.py gel_labeler/`
   must be clean, `python -c "import gel_labeler.gui.main_window"` must succeed, and the web app
   must load with zero uncaught console errors (verify with jsdom or a real browser).
5. Add tests where feasible (`tests/` with pytest; a small jsdom/node test for `docs/app.js`).
   If a hidden environment can't run Qt, still add the test and mark it `skipif`.
6. Never delete/rename the repo root, and don't commit generated artifacts (*_processed.png,
   *_annotated.png, *_labels.json, .autosave_session.json) — extend `.gitignore` instead.

PHASE 1 — STOP DATA LOSS (do these first, one commit each)
1.1 `gel_labeler/gui/main_window.py::autosave_path()` currently returns a hard-coded path
    `C:\Users\DEVANANDAN K C\.gemini\antigravity\scratch\gel_labeler\.autosave_session.json`.
    Replace it with the OS-appropriate app-data location, e.g.
    `QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)` (fallback:
    `tempfile.gettempdir()`), create the directory with `os.makedirs(..., exist_ok=True)`, and
    store only a session file name. Never read or delete files outside that directory.
    Do the same for every other use of that path (`trigger_autosave`, `check_and_recover_session`,
    `closeEvent`).
1.2 `gel_labeler/core/project.py::GelProject.rotate_image()` overwrites its own source file when the
    file name already ends in `_processed` (rotating twice destroys the image). Always write a NEW
    unique file (e.g. `<stem>_rotated_<YYYYmmdd-HHMMSS>.png`), check `QImage.save()`'s boolean
    result, and only then update `image_path` / `image_width` / `image_height`. On failure show a
    `QMessageBox` and leave the project untouched. Null-check the reloaded `cv2.imread` result.
1.3 There is no global exception handling, so any exception inside a Qt slot/paint handler makes
    PyQt6 call `qFatal()` and the app dies with SIGABRT (reproduced: `ZeroDivisionError` in
    `profile_panel.py:111` → exit code 134). Add a crash-safe layer:
      * `run.py`: install `sys.excepthook` and `threading.excepthook` that append the traceback to
        `<app-data>/crash.log` and show a non-blocking error dialog instead of dying;
      * wrap the bodies of `ProfileGraphWidget.paintEvent`, `GelCanvas.paint/draw*`,
        `ColonyCanvas.mousePressEvent` and every export/save handler in `try/except Exception`
        with a logged, user-visible message.
1.4 `main_window.py::closeEvent()` deletes the recovery file even when the user confirms exit while
    tabs are dirty. Only delete it when EVERY tab has `is_dirty == False`; otherwise keep it so the
    next launch can offer recovery.
1.5 `main_window.py::trigger_autosave()` uses `os.remove()` + `os.rename()`. Use `os.replace()`
    (atomic) and clean up the `.tmp` file on failure. Replace `print()` diagnostics with the
    `logging` module writing to `<app-data>/gel_labeler.log` (the app is launched with `pythonw`,
    so stdout is invisible).

PHASE 2 — UNTRUSTED INPUT
2.1 `project.py::load_from_json()` passes arbitrary JSON straight into Qt (`QColor`, `QFont`).
    Add a validation function that enforces: `text` is a `str` (cap length, e.g. 200 chars),
    `x`/`y` are finite numbers inside the current image bounds, `color` matches
    `^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$`, `font_size` is an int in 6..200,
    `font_family` is a `str` (cap 64), `rotation` is a finite float, `id` is a unique `str`.
    On validation failure: refuse the whole file (or import the valid rows and report the rejected
    ones) with a `QMessageBox` that names the offending field. Call `save_undo_state()` before
    replacing labels, and confirm with the user when labels already exist.
2.2 CSV injection: `project.py::export_to_csv()`, `colony_counter_dialog.py::export_csv()` and
    `docs/app.js::exportColonyCsvTable()` write user-controlled text (label text, file names) into
    CSV. Neutralise cells starting with `= + - @ TAB CR` by prefixing a single quote, quote/escape
    every field per RFC 4180 (use `csv.writer` correctly on both sides), and add a UTF-8 BOM for
    Excel.
2.3 Web stored XSS: `docs/app.js::recoverSession()` copies arbitrary objects out of
    `localStorage["pcr_gel_genie_session"]` and `renderActiveTabGrid()` interpolates `tab.gridColor`
    into `innerHTML` (proved exploitable: `'"><img src=x onerror=...><b x="'`). Fix all of:
      * validate/normalise the restored session (exact key whitelist, type checks, ranges, colour
        regex, `tabs.length <= 50`, `labels <= 5000`, string caps);
      * rebuild the grid SVG with `document.createElementNS(...)` + `setAttribute(...)` instead of
        `innerHTML` (or escape every interpolated value);
      * audit every other `innerHTML` assignment (`docs/app.js:228, 231, 261, 1026, 1028, 1586,
        1716`) and replace with `textContent`/DOM APIs.
2.4 Add Subresource Integrity hashes (`integrity` + `crossorigin="anonymous"`) to the CDN
    `<script>`/`<link>` tags in `docs/index.html`, or vendor the libraries locally.

PHASE 3 — BROKEN CORE FLOWS
3.1 `docs/app.js` is broken on load: `elements.selectionCount` is never defined in the DOM cache
    (`docs/app.js:228, 231`), so every `updateSelectionStatus()` call throws a TypeError and
    silently kills the rest of its caller — label dragging is impossible and autosave never runs
    after placing/deleting labels/undo. Add the missing cache entry
    (`selectionCount: document.getElementById("selection-count")`), make the function defensive,
    and wrap each top-level event handler so one failure cannot disable a user flow. Verify with
    jsdom that dragging changes the label position and that no uncaught errors appear.
3.2 `main_window.py::paste_labels()` calls `canvas.populate_labels()` without clearing existing
    items, so every pasted set duplicates all existing labels as ghost graphics (measured: 6 labels
    → 9 scene items, 9 labels → 18 items). Only create items for the pasted labels, or clear and
    rebuild the scene.
3.3 Editing a label through the edit dialog (or the toolbar with a selection) never sets
    `project.is_dirty`, so the title keeps no `*` and the unsaved-changes prompts never fire.
    Set the flag and refresh the title in `canvas.handle_label_updated`, and in every
    style-change path in `MainWindow`.
3.4 `profile_panel.py:111` divides by `n_points - 1` (ZeroDivisionError → SIGABRT with a 1-px tall
    image). Guard with `max(1, n_points - 1)` and render single-sample profiles without a line.
3.5 `open_image_dialog()` / `open_folder_dialog()` reset the active tab's project without warning.
    If the tab is dirty, offer Save / Discard / Cancel (reuse the JSON save dialog) before loading.
3.6 Manual colony/seed annotations are wiped whenever detection re-runs (slider move, checkbox
    toggle) in both `colony_counter_dialog.py::trigger_live_detection()` and
    `docs/app.js::runColonyAiDetection()`. Split state into `auto[]`, `manual[]`, `removed[]`;
    count/render the union; re-run detection only on an explicit button or a debounced change.
3.7 Desktop colony dialog: `self.canvas.colonies` and the guard in `export_image()` should use the
    same union list; `if not self.raw_cv_image is not None or not ...` is a double negative —
    rewrite it as `if self.raw_cv_image is None or not self.canvas.colonies:`.

PHASE 4 — ROBUSTNESS & PERFORMANCE
4.1 `open_folder_dialog()` loads every image in the folder synchronously into its own tab.
    Cap the batch, load lazily when a tab is activated, and show progress with cancel.
4.2 `project.py::compile_projects_to_pptx()` creates a `QGraphicsTextItem` per label and never
    deletes it (memory leak). Reuse one item and `del`/clear it, or use `QFontMetrics` instead of a
    scene item; make the measurement match the rendered (bold) font.
4.3 `canvas.py::mousePressEvent()` calls `super().mousePressEvent(event)` twice on the Disabled
    path; `clear_canvas()` leaves `temp_marker`/mode state dangling; `LabelItem` clamp ignores
    rotation and label size; `LabelItem.open_edit_dialog()` passes `parent=None`.
    Fix all four while keeping the existing behaviour of the other modes.
4.4 `project.py::align_all_labels()` and `generate_span_labels()` push undo states before their
    no-op/guard checks (and the web `alignLabels()` does the same) — move `save_undo_state()` after
    the guards. Narrow `generate_span_labels()`'s "delete overlapping labels" region to labels that
    actually lie on the span line.
4.5 Web colony detection: the flood fill is seeded on a coarse grid
    (`step = max(1, floor(minRad*0.5))`) so small/thin colonies are missed — scan the whole mask
    with a proper queue over unvisited pixels, debounce the parameter handlers (~150 ms), and run
    the scan once per settled change.
4.6 Web: quote the font family in `ctx.font` (`"bold 12px 'Times New Roman'"`), assign `onload`
    before `src`, use `removeAttribute("src")` instead of `src = ""`, use a monotonic counter for
    new tab names, clamp dragged labels using their own bounding box, and neutralise the CSV export
    (see 2.2).

PHASE 5 — HYGIENE
5.1 Delete every unused import and the shadowed import reported by pyflakes
    (`main_window.py:1001, 1234`, `QCheckBox`/`QSplitter`, `tab_widget.py: os`,
    `create_shortcut.py: sys` + f-strings without placeholders, etc.).
5.2 `requirements.txt`: declare `numpy`, pin minimum versions that exclude known-vulnerable
    releases (e.g. `Pillow>=9.0.1`), and add a lock file (`pip freeze > requirements.lock` or
    `pip-tools`). Note Pillow is only needed by `create_mock_gel.py`; consider an optional group.
5.3 `create_shortcut.py`: escape the paths interpolated into the generated VBScript (or create the
    shortcut through `pywin32`/PowerShell with proper quoting); `Install_Dependencies.bat` should
    use `python -m pip install --upgrade pip` and check for Python >= 3.10.
5.4 `launch.bat` uses `pythonw` (no console) — keep it, but log errors to the file added in 1.5
    and show a message box if the launch fails.
5.5 Add a CI job (GitHub Actions) running pyflakes/ruff + pytest + a `node --check docs/app.js`
    and a jsdom smoke test, plus `pip-audit`.

DELIVERABLE FORMAT
For every item: (a) the exact file(s) and line(s) changed, (b) a 3-line explanation, (c) the
before/after snippet for the risky parts, (d) how you verified it (test name / command / manual
steps). Finish with:
  * a table mapping every ID from BUG_REPORT.md (C1-C5, H1-H10, M1-M26, L1-L10) to its status
    (fixed / partially fixed / deferred + why),
  * the exact commands I should run to verify the desktop app, the web app and the tests,
  * a short "release notes" paragraph written for end users (not developers).

START WITH PHASE 1 and show me the diff for 1.1-1.5 before continuing.
```

---

### Notes for whoever runs this

* The report these IDs refer to is `BUG_REPORT.md` in this repository.
* If you only have time for five fixes, do **C1, C2, C3, H1, H3** — they are the difference between
  "users lose their work" and "users don't".
* A headless smoke test that touches most of the desktop app can be run like this (Linux, no
  display): `QT_QPA_PLATFORM=minimal python -c "from PyQt6.QtWidgets import QApplication; ..."` —
  see the checks described in section 0 of the report.
