# 🚀 Gel Labeler — Feature Roadmap

Ideas are ordered by **value ÷ effort** and filtered by one hard constraint: the app is
**offline-first and backend-free** (desktop = PyQt6, web = static files on GitHub Pages).
Anything that needs a server is flagged as such in Tier 5.

Effort: **S** ≈ a day · **M** ≈ a few days · **L** ≈ 1–2 weeks.

---

## Tier 0 — Things that are already half-built (best value in the repo)

| # | Feature | Why | Effort |
|---|---|---|---|
| 0.1 | **Auto-detect lanes/wells** | `gel_labeler/core/cv_detector.py` is a complete, working implementation (smoothed intensity profile → peak finding → median-spacing interpolation of empty lanes) that **is never imported anywhere**. Expose it as a "🎯 Auto-detect lanes" button: click the well row, type the expected lane count, and the span/grid generators get exact X coordinates. | **S** |
| 0.2 | **Batch-apply a layout** | Multi-tab, the label-pattern parser and `compile_projects_to_pptx()` already exist. Add "apply this pattern/font/spacing to all open tabs" (and to a folder) → one button turns 30 gels into 30 labeled PNGs + one deck + one CSV. | **M** |
| 0.3 | **Real redo** | The desktop app has `undo_stack` only; the web app has redo but its undo is broken (see audit H1/M17). Symmetrical undo/redo + a small history panel. | **S** |
| 0.4 | **A real project file (`.gelproj`)** | Today the only persistence is "export labels to JSON", and the autosave path is broken (audit C1). A single project file that holds the image reference (or an embedded copy), labels, colony results, grid/adjustment settings, and view state; double-click to reopen. | **M** |
| 0.5 | **Finish the densitometry that is already 60% there** | `LaneProfilePanel` already computes a per-lane intensity profile and can export CSV/PNG. Add peak detection + baseline so it becomes quantitative, not just a pretty curve (see 1.2). | **M** |

---

## Tier 1 — Features that make it a *real* gel-analysis tool

### 1.1 Band sizing (bp estimation) — the single most-requested lab feature
The ladder lane is already labeled with sizes; the app already stores each label's Y.
Add a **semi-log regression** (`log10(bp)` vs migration distance `Rf`) fitted on the ladder
labels, then for every non-ladder label (or detected band):
* estimated size in bp + R²/interpolation error,
* optional "expected size" per lane → automatic **✔ match / ⚠ off-target** flag,
* `Rf` and relative-front distance columns in the CSV export.

That is the difference between "a labeling tool" and "a gel documentation tool". — **M**

### 1.2 Quantitative densitometry (band intensity)
On top of the existing lane profile: band detection (peaks with baseline subtraction), integrated
density per band, **% of lane total**, and normalisation to a reference band (e.g. a housekeeping
amplicon or the ladder band of the same size). Export a sample × band table. This is what people
currently boot up ImageJ for. — **M/L**

### 1.3 Control rule engine → automatic PASS/FAIL badge
A tiny rules engine: "NC must have no band", "PC must have a band at 450 ± 10 bp", "every sample
must show exactly 1 band between 400 and 500 bp". The app then stamps each gel with a verdict and
colours the offending lanes. For diagnostic/QC labs this prevents the classic embarrassments
(mislabeled NC, wrong panel in a figure). — **M**

### 1.4 Sample manifest → auto-label lanes
Import a CSV/XLSX (or paste a column) of sample IDs in lane order and label the whole row in one
click; keep the manifest attached to the project so the sample table can be exported with the
figure. Pairs perfectly with 0.1 + 0.2 for 96-well plates. — **S/M**

### 1.5 Image enhancement panel (non-destructive)
Nothing in the current UI touches pixels. Add exposure-style controls for the *display and export*
layer: invert (EtBr/UV vs. white-light gels), brightness/contrast/gamma, **rolling-ball background
subtraction** (kills the smeared background that hides faint bands), CLAHE, and a "burn adjustments
into export" toggle. This is often the difference between "band not visible" and "band clearly
there". — **M**

### 1.6 Better photographic input
The 2-click alignment already deskews to a horizontal reference; extend it to a **4-point
perspective correction** (drag the four gel corners) so badly photographed gels become rectangular,
and add a batch "apply the same correction to the rest of this series". — **M**

### 1.7 Colony counter: make the numbers defensible
* **Calibrate the plate** (enter the dish diameter in mm) → colony area in mm², density/mm².
* **Statistical validity flag**: warn when the count is outside the conventional 30–300 CFU window.
* **Multiple-plate weighted mean**: enter counts from several dilutions → single CFU/mL with the
  standard weighted-average formula.
* **TNTC / crowding detection**: saturation estimate on the masked dish area → "too numerous to count,
  plate the next dilution".
* **Size histogram + pick list**: mean/median radius and a coordinate list of the largest colonies
  (useful for picking or for picking-robot input). — **S/M each**

---

## Tier 2 — Workflow, reporting & lab reality

| # | Feature | Why | Effort |
|---|---|---|---|
| 2.1 | **One-page PDF lab report** | Image + label table + CFU calc + method parameters + a "reviewed by" line, generated with `reportlab`/`QPdfWriter` (no server needed). The PPTX exporter already proves the layout maths. | M |
| 2.2 | **Excel (.xlsx) export** | What labs actually want; also sidesteps CSV-formula-injection (audit C5). | S |
| 2.3 | **Vector + poster export** | SVG/PDF label layers (resolution-independent figures) and a 2×/4× PNG export scale for conference posters. | S/M |
| 2.4 | **Protocol/template library** | Save a lane pattern + font + spacing + colour scheme as a named "protocol" (e.g. "Multiplex A panel, 8 lanes") and re-apply it in one click. | S |
| 2.5 | **Figure legend & annotation objects** | Arrows, boxes, brackets, scale bars, a legend box ("L = ladder, NC = negative control") and a caption text block — all of which currently have to be added in PowerPoint afterwards. | M |
| 2.6 | **Real clipboard interop** | Copy/paste labels uses an internal Python list, so it can't cross app instances. Put JSON on the system clipboard with a custom MIME type. | S |
| 2.7 | **Two-gel compare mode** | Side-by-side or blink/overlay-difference of two images (two exposures, two runs, before/after). | M |
| 2.8 | **Provenance / audit trail** | Log who changed what and when, and embed a PNG `tEXt` chunk + sidecar JSON with the parameters used, so a reviewer can reproduce the figure. Also useful for the "reviewed by" line in 2.1. | M |
| 2.9 | **Keyboard-first authoring** | Numeric keypad places labels, `Tab` jumps to the next lane, `Ctrl+D` duplicates, `G` toggles the grid, snapping to grid/neighbours while dragging (the grid is currently visual-only), and smart alignment guides. | S/M |

---

## Tier 3 — Platform & distribution

| # | Feature | Why | Effort |
|---|---|---|---|
| 3.1 | **Touch + mobile web app** | `docs/app.js` has zero `pointer`/`touch` handlers — it is unusable on a phone/tablet, which is exactly where a bench photo gets taken. Pointer Events + pinch-zoom + long-press-to-delete + bigger hit targets. | M |
| 3.2 | **Installable PWA + offline cache** | `manifest.json` + service worker → the lab can install it on a tablet and use it with no network. | S |
| 3.3 | **Camera capture in the web app** | `<input capture>` / `getUserMedia` → photograph the gel and annotate it immediately. | S |
| 3.4 | **IndexedDB instead of localStorage** | Fixes the 5 MB quota that silently kills autosave for real gel photos (audit L6) and removes a whole class of stored-XSS risk (audit C4). | M |
| 3.5 | **CLI / headless mode** | `gel-labeler annotate --image gel.png --pattern "Ladder,1-29" --size 12 --out fig.png` — enables scripting, batch pipelines and reproducible figures. Also makes the app testable in CI. | M |
| 3.6 | **One-file installers via CI** | PyInstaller builds for Windows/macOS/Linux + SHA-256 sums, published by a GitHub Action on tag. Kills the "copy the folder to a USB stick" workflow and the manual `pip install` step. | M |
| 3.7 | **File association for `.gelproj`** | Double-click a project → it opens (needs 0.4 + 3.6). | S |
| 3.8 | **Plugin hook** | A tiny `plugins/` discovery convention so labs can add custom exports/rules without forking. | M |
| 3.9 | **Light theme, high-DPI, accessibility, i18n** | The UI is emoji-only toolbar buttons + tiny colour swatches; add ARIA labels/focus rings in the web app, `Ctrl+=`/`Ctrl+-` font scaling, and (optionally) Malayalam/Hindi locale files. | S/M |

---

## Tier 4 — Bigger bets (only if you want to go beyond a single-user tool)

| # | Feature | Note |
|---|---|---|
| 4.1 | **On-device ML segmentation** | A small ONNX U-Net for band/colony segmentation would beat the current hand-tuned CV (audit M23 shows the flood-fill misses colonies). Runs offline via `onnxruntime` (desktop) / `onnxruntime-web` (browser) — no server, no data leaves the machine. | L |
| 4.2 | **Plate/panel designer** | A 96-well plate map (samples, controls, replicates) that drives lane labelling and exports with the figure. Natural next step after 1.4. | M |
| 4.3 | **Review/share links** | A read-only HTML export (single self-contained file with the image + labels embedded) that can be emailed or dropped in a lab wiki — no backend needed if it's a static file. | M |
| 4.4 | **Multi-user sync / cloud review** | Requires a backend + auth + GDPR-ish handling of patient-adjacent data. Recommend **against** unless the tool is moving into a regulated lab setting; it breaks the current zero-install, offline pitch. | L+ |
| 4.5 | **Statistics across experiments** | Aggregate CFU/mL or band intensities across a folder/study into a QC dashboard (Levey-Jennings charts for control bands). | L |

---

## Suggested release plan

**v1.1 — "Don't lose my work" (fix-first release)**
Audit Phase 1 + 0.4 (`.gelproj`) + 0.3 (redo) + 2.9 (keyboard). Everything else depends on users
trusting the app with their data.

**v1.2 — "Gel analysis"**
0.1 (auto-detect lanes) + 1.1 (bp sizing) + 1.4 (manifest import) + 1.5 (enhancement) +
2.2 (xlsx) + 2.4 (templates).

**v1.3 — "Bench-ready"**
1.2 (densitometry) + 1.3 (control rules) + 1.7 (colony statistics) + 2.1 (PDF report) +
3.1–3.4 (touch/PWA/camera/IndexedDB) + 3.6 (installers).

**v2.0 — "Pipeline"**
3.5 (CLI) + 0.2 (batch mode) + 2.7 (compare) + 2.8 (provenance) + 4.1 (ML, optional).

---

## What I would *not* build

* **Accounts, telemetry, cloud upload by default** — the "no install, no server, nothing leaves your
  laptop" property is this project's main advantage over GelAnalyzer/ImageJ+plugins. Keep it.
* **A generic image editor** — the enhancement panel (1.5) is already at the edge of the mission;
  Photoshop-style tools would dilute the product.
* **Auto-interpretation of results** (e.g. "sample is positive") without a human-visible rule set —
  in a lab context an unexplainable verdict is worse than no verdict.
