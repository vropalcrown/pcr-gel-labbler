# 🧪 Gel Labeler — Bug & Security Audit

**Repository:** `vropalcrown/pcr-gel-labbler` @ `36111ca` (branch `arena/01a0b592-pcr-gel-labbler`)
**Scope:** 21 Python files (~5,900 LOC, PyQt6 desktop app) + the `docs/` web app (`index.html`, `app.js` 1,977 lines, `style.css`) + 5 Windows/helper scripts
**Date:** 2026-09-18

---

## 0. How this audit was done

| Method | Detail |
|---|---|
| Static analysis | Full read of every source file + `pyflakes` (unused imports, shadowed names, dead code) |
| Dynamic (desktop) | App actually executed headless: `PyQt6` + `QT_QPA_PLATFORM=minimal`, `MainWindow` built, images loaded, labels placed by real mouse events (`QTest`), undo/redo, rotation, JSON/CSV/PPTX export, session autosave/recovery, colony detector |
| Dynamic (web) | `docs/index.html` + `docs/app.js` executed in **jsdom** with a poisoned `localStorage` session; DOM/injection and event-flow behaviour observed |
| Not verified at runtime | Anything requiring a GUI file-picker, a real `<img>` decoder in jsdom, or Windows (marked ⚠️ below) |

**Legend**

* ✅ **Verified by execution** — I reproduced it and have the evidence.
* ⚠️ **Verified by code reading** — logic is unambiguous, not executed.
* Severity: **Critical** (data loss / crash-to-desktop / exploitable) · **High** (feature broken or silent data loss risk) · **Medium** (wrong behaviour, robustness) · **Low** (cosmetic / hygiene)

### Headline numbers

* **5 Critical**, **10 High**, **26 Medium**, **10 Low** issues — **51 total**.
* The desktop app **crashes to the desktop (SIGABRT) on any unhandled exception in a Qt slot/paint handler** — verified with `exit code 134`.
* **Autosave / crash-recovery never works** on any machine except the author's — the path is hard-coded to `C:\Users\DEVANANDAN K C\...` — while every other safety net (unsaved-changes prompt, undo) has holes.
* The published **web app is broken on load**: a `TypeError` is thrown at startup on every page view, and it silently disables label dragging and autosave.
* The web app contains a **stored DOM-XSS sink** reachable from poisoned `localStorage`.

---

## 1. 🔴 Critical

### C1 ✅ — Autosave & crash recovery are hard-coded to the developer's private Windows folder
**`gel_labeler/gui/main_window.py:919-921`**

```python
def autosave_path(self) -> str:
    """Returns the path of the hidden session recovery file."""
    return os.path.join(r"C:\Users\DEVANANDAN K C\.gemini\antigravity\scratch\gel_labeler", ".autosave_session.json")
```

* Verified live: `trigger_autosave()` → `Error during auto-save: [Errno 2] No such file or directory: 'C:\\Users\\DEVANANDAN K C\\...\\.autosave_session.json.tmp'`; `check_and_recover_session()` silently no-ops.
* The 2-minute `QTimer` autosave (`main_window.py:307-311`) therefore runs forever and **never saves anything** for any user or on macOS/Linux.
* Collateral privacy/security problems: the file path embeds a **real personal username**; on the author's machine the app **reads and deletes** a file that lives inside another tool's scratch directory (`.gemini/antigravity/scratch`) — it will happily load someone else's leftover session, including absolute image paths.
* Impact: combined with C3 (no exception guard) and the fact that labels are only persisted through a manual *Save Label Data (JSON)* dialog, **any crash loses all annotation work**.

**Fix:** store the session under the user's app-data dir (`QStandardPaths.writableLocation(AppDataLocation)`), fall back to a temp dir if unwritable, never hard-code home paths, and never delete files outside the app's own directory.

---

### C2 ✅ — Rotating an image **overwrites the source file** (data loss)
**`gel_labeler/core/project.py:110-130`**

```python
base, ext = os.path.splitext(self.image_path)
if not base.endswith("_processed"):  new_path = f"{base}_processed.png"
else:                                new_path = f"{base}.png"      # == source when base ends in _processed
rotated_image.save(new_path)                                       # return value ignored
...
self.image_path = new_path
```

Verified live: first rotation of `/tmp/rot.jpg` → `/tmp/rot_processed.png`; **second rotation writes to `/tmp/rot_processed.png` again — i.e. it destroys its own source**, with no confirmation and no backup. Repeated rotations compound the loss. Additionally the `save()` result is ignored and `image_path`/`image_width` are updated even if the write failed, so the project can end up pointing at a stale/absent file.

**Fix:** always write to a *new uniquely-named* file (e.g. `stem_rotated_<timestamp>.png`), check the boolean return of `QImage.save()`, and keep the original untouched (or prompt before overwriting).

---

### C3 ✅ — Any unexpected exception in a Qt handler **aborts the whole application** (no global exception hook)
**`run.py:11-22`, all GUI modules**

PyQt6 default behaviour: an unhandled Python exception raised inside a slot / `paintEvent` / event handler prints a traceback and calls `qFatal()` → `SIGABRT`. There is no `sys.excepthook` / `qInstallMessageHandler` anywhere, no `try` around slot bodies, and `launch.bat` starts the app with `pythonw` — **so there is no console to see the error in**.

Verified live: a 1-pixel-tall image hit the `ZeroDivisionError` in the profile panel (see **H4**) inside `paintEvent` →

```
Traceback (most recent call last):
  File "gel_labeler/gui/profile_panel.py", line 111, in map_coords
    py = margin_top + (idx / float(n_points - 1)) * plot_h
ZeroDivisionError: float division by zero
Aborted (core dumped)     # exit code 134
```

Any latent bug in this report therefore becomes "the app just vanishes and my work is gone".

**Fix:** install a global `sys.excepthook` + `threading.excepthook` that logs to a rotating file (`QStandardPaths.AppDataLocation/../crash.log`), shows a non-fatal `QMessageBox`, and keeps the app alive; wrap risky slot bodies (`paintEvent`, `mousePressEvent`, export handlers) in `try/except`.

---

### C4 ✅ — Stored DOM-XSS in the web app: `localStorage` → `innerHTML`
**`docs/app.js:1062` (save), `1069-1081` (restore, no validation), `464` (sink)**

```js
// restore: blindly trusts anything in localStorage
state.tabs = parsed.tabs.map(t => ({ ...t, undoStack: [], redoStack: [] }));
...
// sink:
svgContent += `<line ... stroke="${tab.gridColor}" ... />`;
elements.gridOverlaySvg.innerHTML = svgContent;
```

jsdom proof with `gridColor = '"><img src="nope404.png" onerror="window.__PWNED=1"><b x="'`:

```
grid overlay innerHTML: <line x1="0" ... stroke=""></line><img src="nope404.png" onerror="window.__PWNED=1"><b x="" ...
injected <img> element inside SVG : true
```

`<img>` is an HTML "breakout" tag in foreign content, so the parser creates a real `HTMLImageElement` whose `onerror` fires in any real browser → arbitrary JS with the page's origin.

**Why this matters more than "self-XSS":** the app is published as a **GitHub Pages project site**. Every project page under `https://vropalcrown.github.io/` shares **one origin and therefore one `localStorage`**. Any XSS or third-party script on *any* other page of that account can write `pcr_gel_genie_session` and get script execution in the Gel Labeler page (and vice-versa).

**Fix:** validate/normalise everything read from `localStorage` (whitelist colour format `^#[0-9a-fA-F]{3,8}$`, numeric ranges, string lengths, cap `tabs`/`labels` counts), and build the SVG with `document.createElementNS` + `setAttribute` instead of `innerHTML`, or escape the values. Apply the same rule to every other `innerHTML` sink (`docs/app.js:228, 231, 261, 1026, 1028, 1586, 1716`).

---

### C5 ✅ — CSV / formula injection in every CSV export
**`gel_labeler/core/project.py:201-215`, `gel_labeler/gui/colony_counter_dialog.py:548-566`, `docs/app.js:1923-1950`**

Label text, colony file names and image paths are written into CSV with no quoting or neutralisation. Verified live with label text `=cmd|'/c calc'!A0`:

```
label_id,text,pixel_x,pixel_y,color,font_size,font_family
25d4b713-…,=cmd|'/c calc'!A0,5,5,not-a-color,big,
```

Opening that export in Excel/LibreOffice/Sheets can execute the formula (classic DDE/CSV-injection, `=`, `+`, `-`, `@`, tab/CR prefixes). The web app additionally builds the CSV with raw string concatenation (no RFC 4180 escaping at all), so a file name containing `,` or `"` corrupts the table structure.

**Fix:** prefix dangerous cells with `'` (or wrap in `="…"`), always quote/escape per RFC 4180 (`csv.writer` already quotes — add the neutralisation), and use `csv`/`text/csv` generation helpers in JS.

---

## 2. 🟠 High

### H1 ✅ — The web app throws on load; label dragging and autosave are dead
**`docs/app.js:228, 231`** vs the DOM cache at `docs/app.js:33-122`

```js
elements.selectionCount.innerHTML = `... ${tab.selectedIds.length} selected`;
```

There is **no `selectionCount` key in the `elements` cache** (the element exists in `index.html:462` as `id="selection-count"`), so `elements.selectionCount` is `undefined` and **every** call throws `TypeError: Cannot set properties of undefined (setting 'innerHTML')`.

Because the throw happens *mid-handler*, everything after it is skipped:

| Caller | What never runs |
|---|---|
| `switchTab()` (line 344) | uncaught error at boot; `showStatus("…initialized…")` |
| `handleLabelMouseDown()` (line 548) | **`dragData.active = true` and the drag listeners → dragging labels is impossible** |
| `createNewLabel()` | `autosaveSession()` → **placing a label is never persisted** |
| `triggerUndo()/triggerRedo()` | `autosaveSession()`, status message |
| `Delete` key handler, modal delete | `autosaveSession()`, status message |

jsdom A/B proof (same page, shipped vs. one line added):

```
### SHIPPED app.js (as published)
  status text: Gel Labeler ready.
  uncaught errors: Uncaught [TypeError: Cannot set properties of undefined (setting 'innerHTML')] | (×2)
### same app + the one missing DOM-cache entry
  status text: Moved selected labels.
  uncaught errors: none
```

**Fix:** add `selectionCount: document.getElementById("selection-count"),` to the cache **and** make `updateSelectionStatus()` defensive; better, wrap all handlers in a single `try/catch` bootstrap so one bad selector cannot kill a user flow.

---

### H2 ✅ — "Paste Labels" duplicates every existing label on the canvas
**`gel_labeler/gui/main_window.py:1607`** → `gel_labeler/gui/canvas.py:80-85`

`paste_labels()` calls `active_tab.canvas.populate_labels()`, which iterates **all** labels and creates a **new** `LabelItem` for each, without clearing `label_items`/the scene first. Every pre-existing label gets a second, unmanaged ghost item.

Verified live:

```
after adding 3 : project labels=3  scene LabelItems=3  label_items dict=3
after paste    : project labels=6  scene LabelItems=9   label_items dict=6
after 2nd paste: project labels=9  scene LabelItems=18  label_items dict=9
```

Ghosts can't be selected or deleted individually and remain after a drag.

**Fix:** import the pasted labels into the model, then call the reload path (`deferred_reload`) or `create_label_item()` only for the new labels.

---

### H3 ✅ — Editing a label never marks the project dirty → edits are lost silently
**`gel_labeler/gui/label_item.py:132-155`** → `canvas.handle_label_updated` → `main_window.handle_project_modified` (only updates the title)

Verified live — after changing a label's text/colour/size through the edit dialog:

```
label text after edit: EDITED
dirty after edit     : False            <-- project.is_dirty never set
title                : mock_gel.png - Gel Electrophoresis Image Labeler   (no "*")
```

Consequences: the window title never shows the `*` marker, `close_tab()` and `closeEvent()` **do not warn about unsaved work**, and the JSON export is the only way to persist the edits.

**Fix:** set `project.is_dirty = True` in `handle_label_updated` (and after any style change made from the toolbar when nothing is selected), then call `update_window_title()`.

---

### H4 ✅ — Profile graph divides by zero → application abort
**`gel_labeler/gui/profile_panel.py:107-127`**

```python
py = margin_top + (idx / float(n_points - 1)) * plot_h     # n_points == 1 → ZeroDivisionError
```

Reproduced with a 1-px-tall image (e.g. a thin lane strip, a freshly cropped/rotated slice): the exception is raised inside `paintEvent`, so — per **C3** — the process **aborts** (`exit code 134`). The same guard is needed wherever a profile is drawn.

**Fix:** `denom = max(1, n_points - 1)` and short-circuit when `n_points < 2` (draw the single sample as a point/line).

---

### H5 ⚠️ — Opening a new image (or a folder) silently discards unsaved labels
**`gel_labeler/gui/main_window.py:1035-1085` (`open_image_dialog`), `1087-1135` (`open_folder_dialog`)**

Both call `tab.project.reset()` / `load_image()` on the *active* tab without checking `project.is_dirty` — unlike `close_tab()` and `closeEvent()`, which do prompt. Ctrl+O on a tab with 300 placed labels deletes them with no confirmation and no undo entry.

**Fix:** if `active_tab.project.is_dirty`, ask "Save / Discard / Cancel" (reuse the JSON save dialog) before resetting; also skip empty unused tabs instead of overwriting the active one.

---

### H6 ✅ — Manual colony / seed markers are destroyed by any parameter change
**`gel_labeler/gui/colony_counter_dialog.py:449-472` (`trigger_live_detection`)`, `docs/app.js:1616-1780`**

Both implementations rebuild the colony list from scratch (`colonyState.colonies = detectedColonies`) whenever a slider/checkbox changes. Everything the user added by hand (✔ left-click) or corrected (right-click deletions) is thrown away — including the "count" they were about to export.

**Fix:** keep AI detections and manual edits in separate collections (`auto[]` + `manual[]` + `removed[]`) and render/count the union; or re-run detection only on an explicit "Re-detect" button.

---

### H7 ⚠️ — `Open Folder of Gel Images` loads *every* image at once, synchronously
**`gel_labeler/gui/main_window.py:1087-1135`**

The folder is scanned, sorted and then each image is decoded (`QImage`, `cv2.imread` grayscale copy, `QPixmap`) and given its own tab, on the GUI thread. A folder of 100 × 12 MP images = 100 live pixmaps + 100 grayscale arrays → multi-GB RSS and a frozen window with no progress or cancel. There is no cap, no lazy loading, and no de-duplication of the same file.

**Fix:** cap the batch (e.g. 20), load lazily on tab activation, show a progress dialog with cancel, and load images in a worker (`QThreadPool`).

---

### H8 ⚠️ — Rotate/align failures are silent; the project ends up pointing at the wrong file
**`gel_labeler/core/project.py:98-131`**

Besides C2: `QImage(self.image_path)` can be null (unsupported/`CMYK`/16-bit TIFF) → the function returns early **after** `save_undo_state()`; `rotated_image.save(new_path)` may fail (read-only folder, permission denied) but `image_path`, `image_width`, `image_height` are updated anyway; `gray_data = cv2.imread(new_path, ...)` is not null-checked (a `None` here later breaks the profile panel silently). Each rotation also leaves a processed copy behind forever — nothing cleans up.

**Fix:** check every return value, only commit state on success, raise a user-visible error otherwise, and clean/replace derived files deterministically.

---

### H9 ⚠️ — Recovery file is deleted even when the user quits *with unsaved changes*
**`gel_labeler/gui/main_window.py:1043-1071` (`closeEvent`)**

If a tab is dirty the app asks "Are you sure you want to exit?", and on **Yes** it deletes `.autosave_session.json`. The user's last 2 minutes of unsaved work therefore become unrecoverable — the opposite of what a crash-recovery file is for.

**Fix:** only delete the session file when *every* tab is clean (`is_dirty == False`); otherwise keep it (it will be offered again on next launch).

---

### H10 ✅ — Label JSON is trusted blindly (arbitrary values, no undo, no confirmation)
**`gel_labeler/core/project.py:182-199` (`load_from_json`)**, `label.py:38-49` (`from_dict`)**, `docs/app.js:1069-1081`**

Verified live with a hand-crafted `labels.json`:

```
parsed label: GelLabel(text="=cmd|'/c calc'!A0", pos=(5.0, 5.0), color='not-a-color', size=big, rot=0.0)
```

`color`, `font_size`, `font_family`, `x/y`, `id` and `text` are copied straight into Qt (`QColor`, `QFont`) and into the PPTX exporter without any type/range/format validation. A `.json` received together with a gel image (the normal sharing workflow) is fully untrusted input: `font_size: "big"` propagates to `QFont(family, "big")` → `TypeError` inside a slot → **app abort (C3)**; a huge `x/y` puts labels off-canvas; duplicated `id`s silently overwrite each other. Loading also replaces all current labels with no confirmation and **no undo entry** (`save_undo_state()` is not called), and the stored `image_width/height` are ignored (labels are drawn against whatever image happens to be open → all coordinates are wrong).

**Fix:** schema-validate on import (types, ranges, hex-colour regex, `id` uniqueness, text length caps), reject the file with a clear message listing the bad fields, verify/set the image dimensions, push an undo state before replacing, and ask for confirmation.

---

## 3. 🟡 Medium

| # | Issue | Location | Detail |
|---|---|---|---|
| M1 ✅ | `update_selection_status()` / `toggle_profile_panel()` crash with no active tab | `main_window.py:1745-1753`, `1830-1835` | Verified: `AttributeError: 'NoneType' object has no attribute 'scene' / 'isVisible'`. The UI's own `close_tab()` re-creates a tab so it is hard to hit — but if it is hit it aborts the app (C3). Guard with `if not self.canvas: return`. |
| M2 ⚠️ | Autosave is not atomic and errors are invisible | `main_window.py:945-963` | `os.remove(path)` + `os.rename()` is a race window with no undo of the unlink; `os.replace()` is atomic. On any failure the `.tmp` file is left behind and the message goes to `print()` — invisible under `pythonw` (see L3). |
| M3 ⚠️ | Grid overlay settings are not persisted & the dialog is recreated each time | `main_window.py:1216-1240`, `grid_dialog.py` | Per-canvas only (lost on restart); `_grid_overlay_dialog` is dropped on `finished`, so reopening rebuilds it. Enabling the grid is also not stored in the saved JSON session. |
| M4 ⚠️ | No-op operations still push undo states | `project.py:331-343` (`align_all_labels`) pushes before the `n < 2` check; `alignLabels` JS pushes before the "need 3" check (`app.js:831-856`) | Ctrl+Z then does nothing visible at least once; the redo stack is cleared for free. |
| M5 ⚠️ | `Mark Well Boundaries` deletes labels in a ±40 px **box**, not on the line | `project.py:262-284` | Any label within 40 px of the span endpoints is removed, including ones on a different deck. Undo covers it, but it is a surprising, hard-to-notice loss. |
| M6 ⚠️ | Drag clamping ignores rotation and label size | `label_item.py:71-79` | Uses the *unrotated* `boundingRect()`, so 90°/270° ladder labels can be dragged half off the image, and nothing stops a label from being clipped by the right/bottom edge. |
| M7 ⚠️ | Label edit dialog has no parent | `label_item.py:132-137` (`parent=None`) | The dialog can open behind the main window / outside the modal stack; on some window managers it loses focus. Pass the view. |
| M8 ⚠️ | Image export ignores the chosen filter and never initialises its buffer | `main_window.py:1425-1460` | `selected_filter` is discarded (format decided by the file extension → silently fails when the user types no extension); `QImage(size, Format_ARGB32)` is not `fill()`ed (undefined pixels if anything ever renders outside the scene rect) and saving an ARGB image as JPEG turns transparency black. |
| M9 ✅ | Shadowed import / dead code / unused imports | `main_window.py:14` vs `:1234` (re-imports `GridOverlayDialog`), `:1001` (`clean_name` unused), plus 20+ unused imports flagged by pyflakes (`project.py:8`, `canvas.py:1,3`, `colony_counter_dialog.py:7,13,14`, `grid_dialog.py:1`, `profile_panel.py:6`, `tab_widget.py:1`, `create_shortcut.py:2`, …) | Noise that hides real problems; run pyflakes in CI. |
| M10 ⚠️ | PPTX export builds a throw-away `QGraphicsTextItem` **per label** just to measure text | `project.py:527-556` | Slow and heap-churning for decks with thousands of labels; if the function is ever called before a `QApplication` exists it silently creates a second/extra one. It also measures with `bold` set even when the label is not bold, and the exception fallback estimate differs from the GUI measurement, so exported text boxes drift from what the user saw. Use `QFontMetricsF` once and reuse. |
| M11 ⚠️ | Auto-increment appends "1" to non-numeric text | `main_window.py:1795-1805`, `docs/app.js:535-543` | After placing "Ladder" the next label becomes "Ladder1"; "NC" → "NC1". Should leave non-numeric text unchanged (or ask). |
| M12 ⚠️ | Click handler calls `super().mousePressEvent()` twice | `canvas.py:308-327` | In `Disabled` mode a click on empty space dispatches the base handler twice (rubber-band restarted). Harmless today, but it defeats the `clicked_item` check and breaks easily. |
| M13 ⚠️ | `clear_canvas()` does not reset `temp_marker` / mode state | `canvas.py:104-113` | A pending span/ladder/align marker is removed from the scene by `scene.clear()` but the Python reference survives; `cancel_*` then calls `scene.removeItem()` on an already-deleted item (Qt warning / potential crash), and `span_first_point` can leak into the next image. |
| M14 ⚠️ | Profile panel replaces the real label with a throw-away copy | `profile_panel.py:250-268` | `self.selected_label = temp_label` (a transient `GelLabel` not in the project) — later `export_csv`/`export_graph` use that copy, so the panel can end up describing a label that no longer exists in the document. |
| M15 ⚠️ | Export file names are built from raw label text | `profile_panel.py:270-300` | `f"profile_{self.selected_label.text.replace(' ','_')}.csv"` — text with `/`, `\`, `..`, `:` or emoji produces invalid/odd default paths (Windows will reject `:` and `*`). Sanitise. |
| M16 ⚠️ | Exported JSON/CSV leak absolute local paths | `project.py:172` (`to_dict` → `image_path`), session file (`main_window.py:930-940`) | Publishing a label JSON (a documented workflow) discloses the author's directory layout/username. Store the file name + a relative path, or make it opt-in. |
| M17 ✅ | Web: `Ctrl+Z / Ctrl+Y` only work when a label is selected | `docs/app.js:741` | The handler starts with `if (!tab \|\| tab.selectedIds.length === 0) return;`, so undo/redo is dead after clicking empty canvas space (the buttons still work). Move the modifier checks above that guard. |
| M18 ⚠️ | Web: clicking a marker deletes it immediately | `docs/app.js:1735-1750` | Left-click on a marker = delete, with no undo entry and no confirmation; clicking on empty canvas adds a marker → the two gestures are easy to confuse on a touchpad. Use right-click / a modifier for delete and push an undo state. |
| M19 ⚠️ | Web: dropping a new image wipes labels without confirmation | `docs/app.js:956-1000` | `tab.labels = {}; undoStack = []; redoStack = []` — same class of problem as H5. |
| M20 ⚠️ | Web: canvas font string is not quoted | `docs/app.js:1102-1115` | `ctx.font = \`bold ${fontSize}px ${fontFamily}\`` — multi-word families (Times New Roman, Courier New) need quoting, otherwise the browser ignores the whole font shorthand and the export silently uses a different font. |
| M21 ⚠️ | Web: tab names collide | `docs/app.js:1395-1405` | New tabs are named `Gel ${state.tabs.length + 1}`; close "Gel 2" of 3 and the next tab is also "Gel 3". Use a monotonic counter. |
| M22 ⚠️ | Web: drag clamp uses a fixed 10 px inset | `docs/app.js:596-606` | `Math.min(tab.imageWidth - 10, …)` ignores the label's own width, so long labels can be dragged off the image. |
| M23 ⚠️ | Web: colony flood-fill is seeded on a coarse grid | `docs/app.js:1640-1712` | `const step = Math.max(1, Math.floor(minRad * 0.5))` — components that contain no grid point are never visited, so thin/small colonies are missed non-deterministically. Seed with every unvisited foreground pixel (or a queue over the binary mask). |
| M24 ⚠️ | Web: detection re-runs on every slider `input` event | `docs/app.js:1840-1856` | A full-resolution BFS per pixel-step on each slider tick = frozen UI on phone photos; debounce (~150 ms) or run on `change` only, and keep manual edits (H6). |
| M25 ⚠️ | Web: colony CSV has no RFC 4180 escaping | `docs/app.js:1923-1950` | Raw string concatenation of `fileName`, so a file named `gel, 2nd run.csv` shifts every column. |
| M26 ⚠️ | Web: image `src` set before `onload`; `src = ""` requests the page URL | `docs/app.js:330-345`, `973` | The `onload` handler is assigned after `src` (a cached data-URL can win the race → layers never render); setting `src = ""` on an `<img>` makes the browser fetch the current document as an image. Set `onload` first and use `removeAttribute("src")`. |

---

## 4. 🟢 Low / hygiene

| # | Issue | Location |
|---|---|---|
| L1 | `create_shortcut.py` interpolates `shortcut_path` / `target_bat` into a generated VBScript without escaping — a folder name containing `"` breaks (or injects into) the script; also `f"..."` strings with no placeholders (lines 26-29). | `create_shortcut.py:12-31` |
| L2 | `launch.bat` uses `pythonw` → no console, so `print()` diagnostics and Python tracebacks are invisible; no fallback error message when Python/deps are missing. | `launch.bat:3` |
| L3 | `Install_Dependencies.bat` calls bare `pip` (not `python -m pip`), does not upgrade pip, does not create a virtualenv, and only checks *that* Python exists (not ≥3.10 as documented). | `Install_Dependencies.bat:8-20` |
| L4 | `requirements.txt` lower bounds allow known-vulnerable releases (e.g. `Pillow>=9.0.0` permits 9.0.0, the version fixed by [CVE-2022-22817](https://bugzilla.redhat.com/show_bug.cgi?id=2042527) — arbitrary expression evaluation in `PIL.ImageMath.eval`). `numpy` is imported directly but not declared; there is no lock file. Note Pillow is **only** needed by `create_mock_gel.py`, not by the app. | `requirements.txt` |
| L5 | Third-party CDN assets loaded without SRI hashes + an inline `onerror` handler. PptxGenJS 3.12.0 has no known CVE, but it is pinned to a movable git tag (not an integrity hash) on a third-party CDN — a tag re-point or CDN compromise = script execution in the page. | `docs/index.html:12-16`, `docs/index.html:25` |
| L6 | Web autosave silently stops working once images are big: the whole base64 image is written to `localStorage` (5-10 MB quota) — the failure is a `console.warn` only, so users believe their work is saved. Use IndexedDB or store only labels + a file-name reference. | `docs/app.js:1000-1065` |
| L7 | `toggle_profile_panel()` / `sync_profile_button_state()` use `isVisible()`, which is `False` whenever the top-level window is hidden/minimised → the toolbar toggle shows the wrong state. Use `isHidden()`/an explicit flag. | `main_window.py:1830-1845` |
| L8 | Grid overlay: the offset modulo logic re-implements the draw loop twice (desktop) and rebuilds the full SVG string on every slider tick (web, thousands of DOM nodes for 5 px spacing on a big image). | `canvas.py:790-830`, `docs/app.js:415-465` |
| L9 | Committed binaries in the repo (`mock_gel.png` 325 KB, `user_gel.jpg` 102 KB) and no `LICENSE`, no CI, no tests. `.gitignore` covers `*.json.bak` but not generated `*_labels.json` / `*_processed.png` / `*_annotated.png` outputs. | repo root |
| L10 | User-visible strings still say "MVP" ("Gel Electrophoresis Image Labeler - MVP", About dialog) and the About box is the only documentation of the toolbar emoji buttons — no tooltips in the web UI for the icons. | `main_window.py:323, 1876-1890` |

---

## 5. Feature-level gaps worth calling out

1. **No "Save Project"** — labels live in memory until the user exports JSON. Everything about C1/C2/C3/H3/H9 matters because of this.
2. **No unsaved-changes protection when switching tabs inside an image-load flow** (H5) and **no redo** in the desktop app (`undo_stack` only; the web app has redo but see H1/M17).
3. **Undo is per-tab and capped at 50 states**, but the *session* autosave never records the undo stacks, so recovery loses history.
4. **The web and desktop implementations have drifted** (different defaults, different undo models, different CFU defaults: desktop dilution default `10⁰`, `docs` circ default 0.35 vs 0.40; `docs` CSV has no neutralisation). There is no shared source of truth for the label/colony schema.
5. **Accessibility/UX**: 18 px colour-only swatches, emoji-only toolbar buttons, no keyboard focus order in the web app, `<label for>` pointing at a hidden input with no visible focus ring.

---

## 6. Suggested order of work

1. **C1, C2, C3, H9, M2** — stop losing data (session path, rotation overwrite, crash guard, recovery semantics, atomic writes).
2. **C4, C5, H10** — untrusted-input handling (localStorage validation, CSV neutralisation, JSON schema validation).
3. **H1, H2, H3, H4, H6, H5** — fix the broken core flows (web boot, paste, dirty tracking, paint crash, manual colonies, open-image confirmation).
4. **H7, H8, M10, M23** — robustness/performance (folder loading, rotate error handling, PPTX leak, flood-fill seeding).
5. **Everything else** — hygiene, unused imports, dependency pinning + CI (pyflakes/eslint/`pip-audit`).

A ready-to-paste remediation prompt is in **`FIX_PROMPT.md`**.
