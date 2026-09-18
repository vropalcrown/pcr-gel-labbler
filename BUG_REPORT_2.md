# 🧪 Gel Labeler — Bug Audit, Pass 2 (deep dive)

**Repo:** `vropalcrown/pcr-gel-labbler` @ `36111ca` · branch `arena/01a0b592-pcr-gel-labbler`
**Date:** 2026-09-18 · Companion to `BUG_REPORT.md` (pass 1)

Pass 1 was a broad read-through. This pass targeted the areas a read-through misses:
**Qt object lifetimes, the Qt-vs-OpenCV image pipeline, the dead `cv_detector` module,
appended-deck geometry, and browser storage failure modes** — and it found things pass 1 did not,
including **two reproducible hard crashes (SIGSEGV, exit code 139)**.

New IDs are `N*` so they never collide with pass 1 (`C/H/M/L`).

## Evidence method (pass 2)

* App executed headless (`QT_QPA_PLATFORM=minimal`, `PyQt6 6.11`, `opencv 4.14` & `5.0`, `numpy`,
  `Pillow`, `python-pptx`), driven with real `QTest` mouse events; `faulthandler` enabled so that
  native crashes produce a stack.
* `docs/app.js` executed in **jsdom** with a deliberately throwing `localStorage`.
* Synthetic fixtures: EXIF-oriented JPEG, 16-bit TIFF, CMYK JPEG, alpha PNG, grayscale PNG,
  structured "plate" photos (0.8 / 3.1 / 12.2 MP) and pure-noise images.

Repro scripts are described inline; each finding is marked ✅ (executed, with the observed output)
or ⚠️ (code reading only).

---

## 🔴 N1 ✅ — **SIGSEGV: the colony counter crashes the app when a second plate image is loaded**

`gel_labeler/gui/colony_counter_dialog.py:34-44` (`set_image`), `:52-60` (`draw_dish_boundary`),
`:62-100` (`render_markers`), reached from `:449-491` (`trigger_live_detection`)

`set_image()` calls `self.scene.clear()` but leaves `self.dish_ring_item` (and the
`marker_items` list) pointing at C++ objects that the scene has already destroyed. The next
detection run calls `draw_dish_boundary()` → `self.scene.removeItem(self.dish_ring_item)` on a stale
pointer.

**Repro (verified):** open the colony counter → *Load Plate Image* → detection runs → *Load Plate
Image* again → the next detection (automatic) aborts the process:

```
QGraphicsScene::removeItem: item 0x25c5cd30's scene (0xb1) is different from this scene (0x25bd0ad0)
Fatal Python error: Segmentation fault
  File "gel_labeler/gui/colony_counter_dialog.py", line 57 in draw_dish_boundary
  File "gel_labeler/gui/colony_counter_dialog.py", line 77 in render_markers
  File "gel_labeler/gui/colony_counter_dialog.py", line 491 in trigger_live_detection
EXIT CODE: 139
```

Loading several plates in one session is the normal workflow (a plate series), so this is reachable
by any user within a minute of use. Under `pythonw` there is no traceback at all — the window just
vanishes.

**Fix:** in `set_image()` (and anywhere else that clears the scene) reset *every* item reference:
`self.bg_pixmap_item = self.dish_ring_item = None; self.marker_items.clear()`; in
`draw_dish_boundary()`/`render_markers()` guard with
`if self.dish_ring_item is not None and self.dish_ring_item.scene() is self.scene:` before calling
`removeItem`. Same audit for `GelCanvas.clear_canvas()` (see N2).

---

## 🔴 N2 ✅ — **SIGSEGV: the gel canvas crashes after a reload while a span/ladder/align marker is pending**

`gel_labeler/gui/canvas.py:104-113` (`clear_canvas`), `:656-675` (`cancel_span_mode`), `:677-707`
(`cancel_ladder_mode`), `:709-736` (`enter_align_mode`/`cancel_align_mode`)

Identical root cause to N1, in the main labeling view: `clear_canvas()` (called by
`load_project_image()`, i.e. on **undo, rotate, reopen, load JSON**) does `scene.clear()` without
clearing `self.temp_marker`. Any later `cancel_*_mode()` (right-click) removes a destroyed item.

**Repro (verified):** enter *Mark Well Boundaries* → click once (marker appears) → trigger any
reload (Ctrl+Z, rotate, reopen the image) → right-click to cancel:

```
after first click: temp_marker set? True | span_first_point: set
after reload: temp_marker python ref still set? True
QGraphicsScene::removeItem: item 0xfb92a50's scene (...) is different from this scene (...)
Fatal Python error: Segmentation fault
  File "gel_labeler/gel_labeler/gui/canvas.py", line 671 in cancel_span_mode
EXIT CODE: 139
```

The same three `cancel_*` methods (`:671`, `:701`, `:717`) share the defect, and the mode flags /
`*_first_point` values are also **not reset**, so after loading a new image a half-finished span can
be completed on it, interpolating labels between a point from the *previous* image and the new click.

**Fix:** in `clear_canvas()` null the temp marker and reset `span_mode`/`ladder_mode`/`align_mode`
plus their first points; add a small helper `_remove_temp_marker()` that checks
`marker.scene() is self.scene` before `removeItem`; use it in all four call sites.

> **One root cause, two crashes.** A single "reset item references when the scene is cleared"
> change (plus the guard) fixes N1, N2 and the related Qt warnings. Add a regression test that
> loads two images and cancels a pending mode.

---

## 🔴 N3 ✅ — **Phone photos (EXIF orientation) put every colony marker and the dish outline outside the image; the densitometry profile silently reads the wrong column**

`gel_labeler/gui/colony_counter_dialog.py:432-447` (`open_image_dialog`),
`gel_labeler/core/project.py:88-96` (`load_image`), `gel_labeler/gui/profile_panel.py:225-240`

The app builds the **display / coordinate system from Qt** (`QPixmap`/`QImage` +
`image_width/height`) and the **analysis from OpenCV** (`cv2.imread`). The two disagree whenever the
file carries an EXIF orientation tag — which is every photo taken with a phone or a camera in
portrait:

| Path | Result for a 200×100 JPEG with `Orientation = 6` |
|---|---|
| `QPixmap` / `QImage` (display, scene rect, labels, exports) | **200 × 100 — not rotated** |
| `cv2.imread` (detection, `gray_data`, dish circle) | **100 × 200 — rotated** (OpenCV honours EXIF by default) |

**Repro (verified):** a synthetic portrait "phone photo" (6 blobs, EXIF 6) into the colony counter:

```
cv2.imread shape (h,w): (200, 100)   -> cv2 ROTATED the image
GUI scene / pixmap (w,h): 200 100    -> Qt did NOT rotate
detected colonies: 2
marker coordinates: x 29..69  y 100..100
scene rect (from Qt pixmap): x 0..200  y 0..100
markers OUTSIDE the displayed image rectangle: 2/2
dish circle (CV space): (50, 100, 46)
```

Every marker and the dashed dish ring are drawn in the wrong place (or off-canvas entirely) —
while the *count* looks plausible, so the user trusts a broken overlay.

Same class of defect in the gel view: `project.image_width/height` = 200×100 (Qt) but
`gray_data.shape` = (200, 100) rows×cols → for any label with `x > 99` the profile panel clamps to
column 99 and plots the **same wrong column** for every lane on the right half of the image:

```
project.image_width/height (from Qt): 200 100
project.gray_data shape (h,w)        : (200, 100)
profile length sampled for a label at x=150: 200 -> clamped to the 99 px edge, i.e. the wrong column
```

**Fix:** make the orientation policy explicit and identical on both sides. Either normalise once at
load (read with `QImageReader(path); reader.setAutoTransform(True)` and store the rotated image, then
`cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)`), or
force both to ignore EXIF and apply the transform once in Qt, then feed the *same* array to all
consumers. Add a unit test that loads an EXIF-oriented fixture and asserts
`(gray.shape[1], gray.shape[0]) == (image_width, image_height)`.

---

## 🔴 N4 ✅ — **The web app dies completely when `localStorage` access throws — including the "double-click `docs/index.html`" workflow the README recommends**

`docs/app.js:1069` (`recoverSession`), reached from `initializeApplication()` at `:1965`

```js
function recoverSession() {
    const stored = localStorage.getItem(LOCAL_STORAGE_KEY);   // ← outside the try/catch below
    if (!stored) return false;
    try { ... } catch (e) { ... }
}
```

Browsers throw `SecurityError` on `localStorage` access when storage is disabled — which is exactly
what happens for `file://` documents in Chromium (opaque origin), with cookies/site-data blocked, and
in private mode on older Safari. Because `app.js` is a single IIFE with no top-level guard, the throw
aborts the whole script: no tabs, no canvas, no error message.

**Repro (verified, jsdom with a throwing `localStorage`):**

```
### localStorage throws (file://, blocked cookies, old Safari private mode)
  tab bar items : 0            <-- the app never initialised
  status text   : "Gel Labeler ready."   (the static HTML text, nothing more)
  errors        : Uncaught [SecurityError: The operation is insecure.]
```

This matters because `README.md` explicitly advertises *"Or double-click `docs/index.html` in any
browser"* as the zero-install path.

**Fix:** wrap every `localStorage` access (get, set, remove) in a `safeStorage` helper that returns
`null` on failure, degrade to an in-memory session, and show a one-line banner ("Session saving is
unavailable in this browser — export your work with *Export PNG / PPTX*"). Wrap `initializeApplication()`
in `try/catch` so a single failure still renders the UI.

---

## 🟠 N5 ✅ — **Session recovery silently discards the image link (and hides all labels) when the image file is not reachable at that moment**

`gel_labeler/gui/main_window.py:975-1010` (`check_and_recover_session`), `:930-940`
(`serialize_session`)

Recovery only calls `project.load_image(...)` `if img_path and os.path.exists(img_path)` — and
`load_image()` is what sets `image_path`. So if the gel lives on a USB stick or a synced folder that
isn't mounted at launch, the recovered tab has `image_path = None`, **no canvas is created and none
of the recovered labels are drawn** (they exist only in `project.labels`), and the very next
2-minute autosave serialises `image_path: null`, permanently destroying the image↔label association.

**Repro (verified):**

```
after recovery: image_path = None
                labels kept = ['L1']
                canvas items rendered = 0 (image could not be loaded)
after the next autosave, the session file now says:
   image_path = None  <- the image link is gone for good
```

To the user the tab simply looks empty: the natural reaction is "my work is gone", and there is no
"relink image" action anywhere in the UI.

**Fix:** keep the path even when the file is missing (set `project.image_path`/dimensions from the
session and only skip the pixel load), render a "Image not found — *Relink…*" placeholder tab, and
offer a file dialog to relink. Never write `null` over a stored path that the user hasn't changed.

---

## 🟠 N6 ✅ — **A label whose text contains "ladder" can never be rotated — the user's choice is silently overridden**

`gel_labeler/core/label.py:21` (constructor), `:55-66` (`update_style`), mirrored in
`docs/app.js:512-524`

```python
self.rotation = 270.0 if "ladder" in text.lower() else rotation          # ctor: always wins
...
if text is not None:
    self.text = text
    if "ladder" in text.lower():
        self.rotation = 270.0                                            # edit: always wins
if rotation is not None and (text is None or "ladder" not in text.lower()):
    self.rotation = rotation                                             # ignored for ladders
```

**Repro (verified):**

```
GelLabel("Ladder (100bp)", rotation=0)  -> 270.0      (user asked for 0)
update_style(rotation=0)                -> 0.0        (inconsistent: this path DOES allow it)
update_style(text="Ladder", rotation=45)-> 270.0      (edit dialog is ignored)
"My ladder marker" in a horizontal tier -> 270.0      (unintended match, silently vertical)
```

So in the *Edit Label* dialog the rotation dropdown does nothing for any label containing "ladder",
and a legitimately horizontal tier label such as "My ladder marker" or "Ladderless control" is
rotated 270° behind the user's back. The same substring rule is in the web app.

**Fix:** treat "ladder" as a *default*, not a rule — set 270° only when the caller passes the default
rotation (or when the label is created by the ladder tool), and honour an explicit rotation from the
dialog. Never match on substrings for layout decisions; use an explicit `is_ladder` flag on the label
if the app needs the distinction.

---

## 🟠 N7 ✅ — **Colony detection runs synchronously on the GUI thread and can freeze the app for minutes**

`gel_labeler/gui/colony_counter_dialog.py:449-491` (`trigger_live_detection`) — invoked from every
slider `valueChanged`, every spinbox change, every checkbox toggle (`:283, 293, 300, 309, 315, 326,
333, 341`)

Measured on this machine (single-threaded, in-process):

| Input | Time |
|---|---|
| 0.8 MP structured plate (300 colonies) | **0.09 s** |
| 3.1 MP structured plate | **0.53 s** |
| 12.2 MP structured plate (phone photo) | **2.37 s** |
| 0.8 MP high-noise image | **12.7 s** |
| 3.1 MP high-noise image | **203 s (3.4 min)** |
| 12.2 MP high-noise image | did not finish in 4.5 min |

Drag the *Sensitivity* slider across a noisy plate photo and the window locks up: Qt cannot repaint,
the slider stops tracking the mouse, and Windows greys the title bar with "not responding". Users will
force-kill the app (losing unsaved state — and note the autosave doesn't work: pass-1 C1).

**Fix:** run detection in a `QThreadPool`/`QRunnable` worker with a generation counter (discard stale
results), debounce slider input (~150 ms, react on `sliderReleased`/committed value), downscale large
images for detection and scale the coordinates back, and show a busy indicator. Also stop re-running
detection on every marker-style change.

---

## 🟡 N8 ✅ — **`SettingsDialog` returns a font size the widget clamped away**

`gel_labeler/gui/settings_dialog.py:66-69, 104-110, 180-190`

`selected_font_size` is set from the caller and never re-derived from the spin box, which clamps to
8…72. Any caller passing an out-of-range value (e.g. a label loaded from a hand-edited JSON — see
pass-1 H10) gets that value straight back and applies it to every subsequent label.

**Repro (verified):** `SettingsDialog(initial_font_size=300)` shows `72` in the spin box but
`get_values()` returns `300`.

**Fix:** clamp in `__init__` (`self.selected_font_size = max(8, min(72, int(initial_font_size)))`)
and read the value from `self.size_spin.value()` in `get_values()`. Align the ranges with the
toolbar spin box (6…72).

---

## 🟡 N9 ✅ — **Appending to a 4:3 deck produces slides that overflow the right edge**

`gel_labeler/core/project.py:411-520` (`compile_projects_to_pptx`)

The layout maths hard-codes a 16:9 slide (`slide_w_in = 13.33`, `slide_h_in = 7.5`, `avail_h_in =
5.7`), but when `existing_pptx_path` is given the presentation keeps *its own* dimensions while the
computed `Inches()` offsets stay absolute.

**Repro (arithmetic on the real formula, 800×600 gel + title):** the picture spans
`x = 2.865 … 10.465 in`. On a standard 10 × 7.5 in (4:3) deck that overshoots the right edge by
**+0.465 in** — the gel is clipped and the labels are stretched off-slide.

**Fix:** derive `slide_w_in`/`slide_h_in` from `prs.slide_width`/`prs.slide_height` (converting EMU
to inches) instead of constants, and compute the available height from the title height rather than
a magic 5.7.

---

## 🟡 N10 ✅ — **After a paste, deleting a "ghost" deletes the real label and leaves undeletable orphans**

`gel_labeler/gui/main_window.py:1585-1615` (`paste_labels`) + `canvas.py:485-505`
(`_do_delete_label`) — escalation of pass-1 H2

Because `populate_labels()` re-creates *every* label (and overwrites `label_items[id]` with the newest
copy), the scene holds duplicates that share one `GelLabel` object. Removing that id then deletes the
model object and one graphic while the other keeps rendering.

**Repro (verified):**

```
scene items after paste: 3 | project labels: 2 | tracked in label_items: 2
after deleting that id once:
  project labels: 1 | scene items still visible: 2 | tracked: 1
  ORPHAN on screen: 'S1' at (100, 100) | selectable: True
  ORPHAN on screen: 'S1' at (100, 100) | selectable: True
a second delete of the same id removes nothing more: 2 items left
```

The orphans are selectable, draggable and editable but exist in no model — they will not be exported
and will silently vanish on the next reload.

**Fix:** fix the paste path (create items only for the new labels, or clear+rebuild once) and make
`_do_delete_label` remove **all** scene items whose `label_data.id` matches, not just the tracked one.

---

## 🟡 N11 ⚠️ — Export row order is insertion order, not reading order

`gel_labeler/core/project.py:201-215` (`export_to_csv`), `:165-180` (`to_dict`) — verified:

```
label_id,text,pixel_x,pixel_y,... | ...C,300,100,... | ...A,100,100,... | ...B,200,100,...
```

Labels are exported in the order they were placed (dict insertion order), so a plate labeled
right-to-left or bottom-to-top produces a scrambled sample table that no longer matches lane order.
There is no sort option in the UI.

**Fix:** sort by (tier/`y` band, then `x`) — the "decks" logic already exists in `align_all_labels()`
and in the Enter-key cycling code — and expose "sort export by position / by placement" as a choice.

---

## 🟡 N12 ✅ — Web autosave re-serialises the whole image on every interaction

`docs/app.js:1000-1065` (`autosaveSession`), called from ~15 handlers (label add/delete/drag-end,
undo/redo, every grid slider, font/colour changes…)

Measured: a single 4032×3024 phone photo + 200 labels produces a **2.02 MB** JSON payload, and
`JSON.stringify` alone costs ~9 ms; the `localStorage.setItem` that follows is a synchronous write of
the same 2 MB. Per interaction, on the UI thread. Past the 5–10 MB quota the write throws, is caught,
and only `console.warn`-ed — the user keeps working believing their session is saved (pass-1 L6).

**Fix:** store labels + a file reference, not the base64 pixels; move to IndexedDB (async, far larger
quota); debounce autosave (e.g. 500 ms trailing, plus on `visibilitychange`); and surface persistent
save failures in the status bar.

---

## 🟡 N13 ⚠️ — Small correctness/robustness defects found while testing

| # | Issue | Location |
|---|---|---|
| N13.1 | `pixmap.save(file_path)` (line 530) result ignored → an unwritable path or unsupported extension fails silently after the "exporting…" message. | `colony_counter_dialog.py:508-532` |
| N13.2 | The same ignored-return pattern in the gel exporter is masked by `QImage.save()` on an unfilled buffer (pass-1 M8). | `main_window.py:1429-1460` |
| N13.3 | `if not self.raw_cv_image is not None or not self.canvas.colonies:` — correct by accident, unreadable; rewrite as `is None`. | `colony_counter_dialog.py:509` |
| N13.4 | Colour-swatch active-state comparison assumes 6-digit hex; `#FFF`/8-digit colours from a JSON file never highlight. | `main_window.py:1730-1760`, `settings_dialog.py:104-110` |
| N13.5 | Grid overlay spacing slider allows 5 px while the drawing loop rebuilds the entire SVG string per tick → thousands of nodes per keystroke for a big image. | `docs/app.js:415-465` |
| N13.6 | `elements.gelImageDisplay.src = ""` (no image) makes the browser request the page itself as an image; `onload` is also assigned after `src` in the load path. | `docs/app.js:330-345, 973` |
| N13.7 | `mock_gel.png`/`user_gel.jpg` are committed test images with no test referencing them; `user_gel.jpg` is referenced nowhere. | repo root |

---

## ✅ Checked and found clean (so you don't re-audit them)

* **Format handling:** PNG (gray / RGBA), JPEG (RGB / CMYK), 16-bit TIFF, 8-bit TIFF — Qt and OpenCV
  agree on dimensions for all of them, and `detect_colonies()` neither crashes nor misbehaves on them
  (16-bit is down-converted to 8-bit by `cv2.imread`, so `adaptiveThreshold` is safe).
* **`cv_detector.py` numeric path:** the 1-D `GaussianBlur` profile works on both OpenCV 4.14
  (returns `(N,1)`, `.flatten()` handles it) and 5.0 — no crash. (The module is still dead code — see
  `FEATURE_ROADMAP.md` 0.1 — and its `Tuple[float, float]` return order differs from the function
  name's promise, worth a docstring fix when you wire it up.)
* **Undo/redo & delete paths (desktop):** `save_undo_state`/`undo` round-trips correctly for add,
  delete, drag, batch span/ladder generation, alignment, paste and image rotation; `_in_batch_operation`
  is properly reset in `finally`.
* **`ColonyObject`/CFU maths:** `calculate_cfu` guards `volume <= 0`; the dilution mapping (`10**idx`)
  matches the combo ordering; the disk/dish radius clamp is correct.
* **Pattern parser:** `1-5`, `S1-S3`, `5-1`, `1 - 3`, `10-10`, non-numeric literals (`NC`, `P-`, `A-1`)
  all behave as documented (an unbounded `1-100000` is possible — flagged in pass 1).
* **No `eval`/`exec`/`pickle`/`shell=True`/`os.system` anywhere in the Python code.**

---

## Suggested fixes order for pass-2 items

1. **N1 + N2** — one "reset item references on scene clear" change + a guard helper + a regression
   test. Two hard crashes for the price of one small patch. *(highest value in this document)*
2. **N3** — make the EXIF policy explicit on both image paths; verify with an oriented fixture.
3. **N4** — `safeStorage` wrapper + `try/catch` around `initializeApplication()`.
4. **N5** — keep unreachable paths, add a "Relink image…" action.
5. **N7** — move detection to a worker thread with debounce (also fixes H6's UX complaints).
6. **N6, N8, N9, N10, N11, N12** — small, localised behaviour fixes.
7. **N13.*** — hygiene.

Add these IDs to the checklist in `FIX_PROMPT.md` when you implement them.
