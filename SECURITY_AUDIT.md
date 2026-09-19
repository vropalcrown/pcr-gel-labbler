# 🔐 Gel Labeler — Security Audit

**Target:** `vropalcrown/pcr-gel-labbler` @ `e124d1a` (branch `arena/01a0b592-pcr-gel-labbler`)
**Date:** 2026-09-18 · **Scope:** the whole repository — PyQt6 desktop app (`gel_labeler/`), static web app (`docs/`), Windows helper scripts, dependency set, and the distribution/deployment chain.
**Companion documents:** `BUG_REPORT.md` (functional bugs pass 1), `BUG_REPORT_2.md` (functional bugs pass 2). Findings here are security-framed and use `S*` IDs; overlaps are cross-referenced, not repeated.

**Method:** manual source review + live execution (app driven headless with real Qt events; web app driven in jsdom with adversarial `localStorage`), dependency audit (`pip-audit`, OSV, public advisory data), filesystem/permission inspection, and secret scanning (`git log --all --diff-filter=A` + credential-pattern grep over the full history).

**Evidence legend:** ✅ verified by execution · ⚠️ verified by code reading / arithmetic · ℹ️ informational.
**Severity:** Critical → High → Medium → Low → Info. CVSS v3.1 scores are indicative and assume the local user running the app on their own machine.

---

## 1. Executive summary

Gel Labeler is a **local, single-user, offline** desktop tool with no server, no accounts, no telemetry and no sensitive credentials — which removes whole categories of risk (no authn/authz, no SQLi, no SSRF, no session hijacking, no remote attack surface on the desktop binary). Those are real strengths and they are verified below.

What remains is a different profile: **it is a tool whose entire job is to open files produced by other people** (gel images, label JSONs, plate photos) **and to produce files that other people open** (CSV/XLSX, PPTX, PNG, JSON). Every finding in this audit follows from that duality.

| # | Finding | Severity | Status |
|---|---|---|---|
| S1 | Untrusted `labels.json` aborts the whole application (validated: `exit code 134`) | **High** | ✅ |
| S2 | Dependency floors permit image-decoder versions with published memory-corruption CVEs (`opencv-python`, `PyQt6/Qt`); no lock file | **High** | ✅/ℹ️ |
| S3 | Stored DOM-XSS in the web app via `localStorage` (GitHub Pages shares one origin) | **High** | ✅ |
| S4 | CSV/formula injection in every CSV export (desktop + web) | **High** | ✅ |
| S5 | Distribution chain: unsigned ZIP/USB + `pip`/`python` resolved from the current folder + unverified `requirements.txt` | **High** | ⚠️ |
| S6 | VBScript injection through a folder name in `create_shortcut.py` (then executed via `cscript`) | **Medium** | ✅ (construction) |
| S7 | World-readable artifacts containing lab data and absolute paths (`0o644` session/CSV) | **Medium** | ✅ |
| S8 | Path traversal in default export filenames derived from untrusted label text | **Medium** | ✅ |
| S9 | Resource exhaustion: unbounded label counts (typo `1-50000` → ≈1.3 GB, hostile JSON has no cap) | **Medium** | ✅ (measured) |
| S10 | No SRI/CSP for the web app's third-party scripts; one CDN tag can take over the page and its saved images | **Medium** | ✅ |
| S11 | Third-party asset loads (Google Fonts, cdnjs, jsDelivr) leak lab usage metadata; "offline" claim is inaccurate | **Low** | ✅ |
| S12 | No global exception policy → every bug is an availability incident with no forensic trail | **Low** | ✅ |
| S13 | Insecure temporary-file handling in autosave (predictable `.tmp`, `remove`+`rename` race) | **Low** | ✅ |
| S14 | PII/info disclosure: real Windows username hard-coded in source, absolute user paths written into exports | **Low** | ✅ |
| S15 | No release integrity artifacts (no CI, no SBOM, no hashes, no signing) for a USB/ZIP-distributed binary | **Info** | ℹ️ |

**Bottom line:** nothing here is remotely exploitable against a user who never opens a file from someone else. For a lab tool, that is the normal case — so treat **S1–S5 as the remediation priority**: two of them (S1, S3) are *verified working* denial-of-service/code-execution primitives reachable from a file a colleague sends, and S2 is the classic "open this gel photo" vector.

---

## 2. System model

### 2.1 Assets worth protecting

| Asset | Where | Why it matters |
|---|---|---|
| Gel/plate **images** (may show patient samples, unpublished data) | user's disk; `localStorage` (web) as base64 | confidentiality + research integrity |
| **Label metadata** (sample IDs, patient/sample names typed as labels) | `*_labels.json`, `.autosave_session.json`, `.gelproj` | same as above; weaker obvious sensitivity, so it travels by email |
| **Colony counts / CFU/mL** | CSV, PPTX, screenshots | scientific conclusions; integrity matters |
| Exports handed to reviewers/publishers | PPTX/PDF/PNG/CSV | integrity (figure tampering), injection into Excel/PowerPoint |
| The user's **workstation** | desktop app process | any memory-corruption or script-execution primitive lands here |

### 2.2 Actors

* **A1 — the user** (trusted, but can be tricked).
* **A2 — a colleague/collaborator** who sends a gel image plus its `labels.json`/session (semi-trusted: this is the documented workflow).
* **A3 — a distributor** (USB stick, ZIP, "here's the folder, double-click `launch.bat`") — untrusted.
* **A4 — a malicious web page/script** running on the same origin as the published web app (GitHub Pages: *every* project page of the account shares an origin).
* **A5 — another local user** on a shared/multi-user machine (matters for the `0o644` artifacts, S7).

### 2.3 Attack surface

| Surface | Entry point | Notes |
|---|---|---|
| Image files | `QImage(path)`, `QPixmap(path)` (`main_window.py:1050, 1102`, `canvas.py:75`, `colony_counter_dialog.py:441`), `cv2.imread()` (`project.py:95,131`, `colony_counter_dialog.py:437`, `cv_detector.py:24`) | two independent decoders, both native C/C++; file-dialog extension filters are cosmetic |
| Label JSON / session JSON | `project.load_from_json`, `main_window.check_and_recover_session` | **no schema validation** |
| Existing PPTX (append mode) | `pptx.Presentation(path)` | zip/XML parsing of an untrusted deck |
| `localStorage` session (web) | `recoverSession()` | no validation → S3 |
| Generated artifacts (CSV/PPTX) | opened in Excel/PowerPoint by third parties | S4 |
| Distribution chain | `.bat` files, `create_shortcut.py`, `requirements.txt`, CDN assets | S5, S6, S10 |
| Local filesystem | session/export writes | S7, S8, S13 |

**Not present (verified):** network services, listening sockets, remote APIs, update mechanism, authentication, database, cloud upload, telemetry. `docs/app.js` contains **no** `fetch`/`XMLHttpRequest`/`WebSocket`/`sendBeacon`/`EventSource` — file inputs are read locally with `FileReader` and never transmitted. Exact commands in §9.

---

## 3. Findings

### S1 ✅ — Untrusted label JSON aborts the application (availability / data loss)

**CWE-20 (improper input validation) → CWE-617 (reachable assertion) · High · CVSS ≈ 5.5 (AV:L/AC:L/PR:N/UI:R/S:U/C:N/I:N/A:H)**

`GelProject.load_from_json()` copies attacker-controlled JSON straight into the model and `GelLabel.from_dict()` performs no type/range checks. The values are then handed to Qt inside a slot, and PyQt6 turns an unhandled exception in a slot into `qFatal()` → **SIGABRT**.

Verified end-to-end through the real user path (*Load Label Data (JSON)* → `QTimer.singleShot(0, canvas.deferred_reload)`), using a `labels.json` with `"font_size": "big"`:

```
TypeError: arguments did not match any overloaded call: QFont(...)
  File "gel_labeler/gui/label_item.py", line 48, in refresh
  File "gel_labeler/gui/canvas.py", line 469, in create_label_item
Fatal Python error: Aborted
EXIT CODE: 134
```

* A string `font_size` or `font_family`, a `color` that is not a hex string (the PPTX path raises `ValueError: invalid literal for int() with base 16: 'gh'` for 6-char non-hex values such as `"ghijkl"`), a missing/duplicate `id`, or a `text` of unbounded length are all accepted by the loader.
* Consequence: a file received from a collaborator (A2) crashes the app with no message (the launcher uses `pythonw`, so the traceback is invisible), and — because autosave is broken by bug-report C1 — any unsaved work is lost.
* `main_window.check_and_recover_session()` applies the same trust to `.autosave_session.json`.

**Remediation:** validate on import with an explicit schema (types, ranges, hex-colour regex, unique IDs, length caps, coordinate bounds: the authors already know the values — `config.DEFAULT_*` and the `8..72` widget range); reject with a dialog naming the bad field; push an undo state before replacing; add the global exception hook from C3 so a future unknown field cannot abort the process.

---

### S2 ✅/ℹ️ — Dependency floors admit image decoders with known CVEs; no lock file

**CWE-1104 (use of unmaintained/unpinned components) · High · CVSS n/a (supply-chain precondition, impact = the decoder CVE)**

`requirements.txt` declares only lower bounds:

```
PyQt6>=6.4.0
Pillow>=9.0.0
opencv-python>=4.5.0
python-pptx>=1.0.2
```

* **`pip-audit -r requirements.txt` → "No known vulnerabilities found" (today's resolver installs current versions, e.g. PyQt6 6.11.0, opencv 4.14.0.94, Pillow 12.3.0).** The risk is the *floor*: nothing in the repo prevents an offline wheel cache, an old internal mirror, an `--index-url` pin, or a `pip install` from an old snapshot from producing the vulnerable set — and there is no lock file or hash pinning to make the build reproducible.
* **`opencv-python` floor permits decoders with published, serious CVEs**, all reachable because the app feeds user-supplied images to `cv2.imread`:
  * **CVE-2023-4863** (libwebp heap buffer overflow, exploited in the wild) — opencv-python bundles vulnerable libwebp **before 4.8.1.78** ([Vulert advisory list](https://vulert.com/vuln-db/pypi/opencv-python)).
  * **CVE-2025-53644** — OpenCV **4.10.0 and 4.11.0**: uninitialized stack pointer → **arbitrary heap buffer write when reading a crafted JPEG**; fixed in 4.12.0; CVSS v3.1 `AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` ([NVD](https://nvd.nist.gov/vuln/detail/cve-2025-53644)).
  * Older `imgcodecs` memory-corruption issues (out-of-bounds reads/writes in BMP/PNG/PXM handling) affect the 3.x–4.x line ([cvedetails](https://www.cvedetails.com/vulnerability-list/vendor_id-16327/product_id-36994/Opencv-Opencv.html)).
* **`PyQt6>=6.4.0` = bundling Qt 6.4.0 (Sept 2022)**, which is affected by image-format CVEs fixed later in the 6.x line, e.g. **CVE-2024-25580** (KTX buffer overflow, fixed 6.5.5/6.6.2) and **CVE-2025-5683** — "*If `QImage` is passed a specifically crafted [ICNS] image file, then it will trigger a crash*", affected 6.3.0–6.5.9 / 6.6.0–6.8.4 / 6.9.0, fixed 6.5.10/6.8.5/6.9.1 ([Qt security advisory](https://www.qt.io/blog/security-advisory-recently-discovered-issue-in-icns-image-format-handling-impacts-qt), [stack.watch Qt CVE list](https://stack.watch/product/qt/qt/)). `QImage(path)` is exactly what this app calls.
* **`Pillow>=9.0.0`** permits **CVE-2022-22817** (arbitrary expression evaluation in `PIL.ImageMath.eval`, fixed 9.0.1 — [Red Hat](https://bugzilla.redhat.com/show_bug.cgi?id=20422817), [Mageia/OSV](https://osv.dev/vulnerability/MGASA-2022-0166)) and **CVE-2022-24303** (*"Pillow before 9.0.1 allows attackers to delete files because spaces in temporary pathnames are mishandled"*, fixed 9.0.1). Pillow is imported **only** by `create_mock_gel.py` (a developer utility, not imported by the app), so its real-world blast radius is small — but it should be raised or dropped from runtime requirements.
* `numpy` is imported directly by the app but **not declared at all**.

**Remediation:** raise floors to the fixed versions (`opencv-python>=4.12.0`, `PyQt6>=6.5.10`, `Pillow>=9.0.1` or drop it), add `numpy`, generate a hash-pinned lock file (`pip-compile --generate-hashes` or `uv pip compile`), and add `pip-audit` + `ruff/pyflakes` as CI gates. Move Pillow into an optional `dev` extra. Consider `opencv-python-headless` (smaller, no GUI/X11 dependencies) since the app uses its own Qt viewport.

---

### S3 ✅ — Stored DOM-XSS in the published web app (session → `innerHTML`)

**CWE-79 · High · CVSS ≈ 6.1 (AV:N/AC:L/PR:N/UI:R, scope-changed in the GH-Pages context)**

`docs/app.js:1069-1081` restores `localStorage["pcr_gel_genie_session"]` **without validating anything**, and `renderActiveTabGrid()` (`:415-465`) interpolates `tab.gridColor` into `innerHTML`:

```js
svgContent += `<line ... stroke="${tab.gridColor}" ... />`;
elements.gridOverlaySvg.innerHTML = svgContent;
```

PoC executed in jsdom with `gridColor = '"><img src="nope404.png" onerror="window.__PWNED=1"><b x="'`:

```
grid overlay innerHTML: <line x1="0" ... stroke=""></line><img src="nope404.png" onerror="window.__PWNED=1"><b x="" ... stroke-width="1">
injected <img> element inside SVG : true
```

* `<img>` is an HTML "breakout" tag in foreign (SVG) content, so a real parser instantiates `HTMLImageElement` and fires `onerror` → arbitrary JS with the page origin.
* **Why it is not merely self-XSS:** the app is served as a **GitHub Pages project site**. All project pages under `https://<user>.github.io/` share **one origin and therefore one `localStorage`**. Any XSS, vulnerable dependency, or third-party script on *any* other page of that account can write `pcr_gel_genie_session` and obtain script execution inside the Gel Labeler page — where `tab.imageSrc` holds the user's gel images in base64 and can be exfiltrated in one line.
* Aggravating factors: no CSP (S10) and third-party scripts loaded from CDNs (S11).
* Other `innerHTML` sinks with the same class of risk: `docs/app.js:228, 231, 261, 1026, 1028, 1586, 1716`.

**Remediation:** (1) validate/normalise the whole restored session — key allow-list, type checks, numeric ranges, colour regex `^#[0-9a-fA-F]{3,8}$`, caps on `tabs`/`labels`/string lengths; (2) build the SVG with `document.createElementNS` + `setAttribute` (never `innerHTML` with interpolated values); (3) replace the other `innerHTML` uses with `textContent`/DOM APIs; (4) add the CSP from S10 so an injected inline handler cannot execute even if a sink is missed.

---

### S4 ✅ — CSV / spreadsheet formula injection in all exports

**CWE-1236 · High · CVSS ≈ 7.0 (AV:L/AC:L/PR:N/UI:R/S:C/C:H/I:H/A:N — the victim is whoever opens the file)**

Label text, colony file names and image paths are written into CSV without neutralisation, in three places:

* `gel_labeler/core/project.py:201-215` (label database export)
* `gel_labeler/gui/colony_counter_dialog.py:548-566` (colony report)
* `docs/app.js:1923-1950` (web colony report — additionally no RFC 4180 escaping at all, so a file name containing `,` or `"` corrupts the table structure)

Verified output for a label named `=cmd|'/c calc'!A0`:

```
label_id,text,pixel_x,pixel_y,color,font_size,font_family
25d4b713-…,=cmd|'/c calc'!A0,5,5,not-a-color,big,
```

Excel/LibreOffice/Sheets evaluate cells starting with `= + - @`, tabs or CR — the classic DDE/`cmd` execution and remote-content/data-exfiltration vector, and here the *sender* is a trusted colleague (A2) while the *victim* opens the file in a spreadsheet. Exports are the app's main shareable artefact, so this is a realistic path.

**Remediation:** prefix risky cells with a single quote (or emit as `="…"` text), quote/escape per RFC 4180 on both platforms, add a UTF-8 BOM for Excel, and prefer real `.xlsx` output (openpyxl) where cell types are unambiguous.

---

### S5 ⚠️ — Distribution chain: unsigned folder + `pip`/`python` resolved from the current directory

**CWE-494 (download of code without integrity check) / CWE-426 (untrusted search path) · High**

The README instructs users to *"copy the entire folder to the other laptop (or run directly from the USB drive)"*, then double-click `Install_Dependencies.bat` (which runs `pip install -r requirements.txt`) and `launch.bat` (which runs `pythonw run.py`). Nothing verifies the folder's provenance or the contents of `requirements.txt`.

* **No integrity check on the distribution:** whoever can modify the USB folder / ZIP / git clone runs arbitrary code as the user with zero friction. There is no signing, no hash list, no release process (S15).
* **Windows resolves `pip` and `python` from the current directory first.** `Install_Dependencies.bat:19` calls bare `pip`, and the script begins with `cd /d "%~dp0"` — so a `pip.bat`/`pip.exe`/`python.exe` placed next to the script (trivially includable in a "shared folder") is executed instead of the real one. The same applies to `create_shortcut.py`'s `subprocess.run(["cscript", ...])` and `launch.bat`'s `pythonw run.py`.
* `requirements.txt` is a **code-execution manifest** (arbitrary packages, sdist build steps) and is editable in the same folder.

**Remediation:** ship signed, hash-verified releases (PyInstaller + GitHub Actions artifacts with SHA-256 sums, ideally Authenticode-signed); make the launcher verify a manifest before running; use `python -m pip` (never bare `pip`) and `python -m pip install --require-hashes -r requirements.lock`; avoid `cd /d "%~dp0"` before resolving tools or use absolute paths to the interpreter; state prominently in the README that **only the released archive** should be run.

---

### S6 ✅ — VBScript injection via a folder name, executed by `cscript`

**CWE-94 (code injection) · Medium · CVSS ≈ 6.5 (AV:L/AC:H/PR:L/UI:R — needs a crafted folder name)**

`create_shortcut.py:16-38` builds a VBScript by f-string interpolation of three paths, writes it into the program folder and executes it:

```python
vbs_content = f'''Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{shortcut_path}"
...
oLink.TargetPath = "{target_bat}"
oLink.WorkingDirectory = "{script_dir}"
...'''
```

Verified construction with a folder containing a double quote (`/tmp/My "Quoted" Folder`):

```
oLink.TargetPath = "/tmp/My "Quoted" Folder/launch.bat"
```

The quote terminates the string literal, so everything after it is parsed as **VBScript statements** — a folder name/authorship path (e.g. from an extracted ZIP, or a synced folder name) becomes an arbitrary-script-execution primitive that the tool then runs on itself (`cscript //nologo _make_shortcut.vbs`). The generated file is also written into the (user-writable, potentially shared or USB) program directory before execution, so it can be planted/read there.

**Remediation:** don't generate VBScript — use `win32com.client.Dispatch("WScript.Shell")` (pywin32) or PowerShell with `-EncodedCommand`/proper argument quoting; if VBScript must stay, escape `"` as `""` and reject paths containing quotes/CR/LF; create the temp file with `tempfile.NamedTemporaryFile(dir=..., delete=False)` and restrictive permissions.

---

### S7 ✅ — World-readable artifacts contain lab data and absolute paths

**CWE-276 (incorrect default permissions) · Medium**

Files are created with the process umask (0o022 ⇒ `0o644`), verified:

```
process umask: 0o022
  session file      : 0o644 (others can read: True)
  CSV export        : 0o644
  session content includes the absolute image path and label text: True | True
```

The session/autosave file contains sample labels (`Patient-042 / sample 7`) and absolute paths, and — per bug C1 — is currently written into a shared scratch directory on the developer's machine. On a multi-user workstation or a shared lab PC (A5), any other account can read the user's work.

**Remediation:** create the session/autosave file with `os.open(..., O_CREAT|O_WRONLY|O_TRUNC, 0o600)` (or `os.chmod` after), store it under the user's app-data directory, and document that exports inherit the user's umask (optionally offer a "restrict permissions" toggle for sensitive work).

---

### S8 ✅ — Path traversal in default export filenames derived from untrusted label text

**CWE-22 (partial) · Medium**

`profile_panel.py:270-300` derives the *suggested* filename from label text:

```python
f"profile_{self.selected_label.text.replace(' ', '_')}.csv"
```

Verified: a label named `../../../../tmp/pwned` yields

```
suggested filename: profile_../../../../tmp/pwned.csv
```

`QFileDialog` pre-fills that string; a user who simply presses **Enter** writes outside the intended directory (and Windows additionally rejects `: * ? " < > |`). Label text is attacker-influenceable (it comes from an imported `labels.json`, i.e. A2).

**Remediation:** sanitise with a strict allow-list (`re.sub(r'[^A-Za-z0-9._-]', '_', text)[:64]`), strip leading dots/slashes, and always join with the chosen directory.

---

### S9 ✅ — Resource exhaustion from unbounded label counts

**CWE-400 · Medium (availability; from a typo or a hostile JSON)**

The lane-pattern parser has no upper bound, and neither the pattern dialog nor the JSON importer caps the number of labels:

```
pattern 1-26      ->     26 labels
pattern 1-50000   ->  50000 labels in 0.004 s      # free to construct …
```

Turning them into scene items is the expensive part (each label = `QGraphicsTextItem` + `QGraphicsDropShadowEffect`), measured in the real canvas:

| labels | model build | scene items | peak RSS |
|---|---|---|---|
| 500 | 0.00 s | 0.07 s | 119 MB |
| 2 000 | 0.01 s | 0.28 s | 153 MB |
| 5 000 | 0.02 s | 0.66 s | 221 MB |

Extrapolating, one `1-50000` entry costs ≈ **1.3 GB and ~7 s of frozen UI** (and the JSON importer accepts the same, with no cap: a 2 000-label hostile file loads in 0.04 s and is then rendered). Repeated on a memory-constrained laptop this is a hard OOM kill.

**Remediation:** cap pattern expansion (e.g. 5 000 lanes, warn above 1 000), cap labels per project and per imported file, stream/paginate rendering (or replace `QGraphicsTextItem` + drop-shadow effect with a lightweight `QGraphicsSimpleTextItem`/custom-drawn item for large documents), and show progress with cancel.

---

### S10 ✅ — Missing CSP and SRI: one compromised CDN asset owns the page and its images

**CWE-353 / CWE-829 · Medium**

Verified gaps in `docs/index.html`: **no `Content-Security-Policy`** (header or meta), **no `integrity=`/SRI** on any CDN asset, **no `Referrer-Policy`**, and an inline `onerror` handler at `index.html:25`. Third-party origins loaded on every page view:

```
https://cdn.jsdelivr.net/gh/gitbrent/pptxgenjs@3.12.0/dist/pptxgen.bundle.js
https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css
https://fonts.googleapis.com / https://fonts.gstatic.com
```

The jsDelivr URL resolves a **Git tag**, not a content hash: if the tag is re-pointed, the package is republished, or the CDN is compromised, the attacker gets arbitrary JS in a page whose `localStorage` contains the user's base64 gel images (and which, per S3, is also a script-injection sink). PptxGenJS 3.12.0 itself has no published advisory ([Snyk](https://security.snyk.io/package/npm/pptxgenjs)), so the exposure is the delivery path, not the library.

**Remediation:** vendor `pptxgen.bundle.js` + the icon font into `docs/vendor/` and load them locally (also makes the app genuinely offline/PWA-capable); if CDNs must be used, add `integrity="sha384-…" crossorigin="anonymous"` and pin exact versions; add a `<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; img-src 'self' data: blob:; font-src 'self' https://fonts.gstatic.com; connect-src 'none'; object-src 'none'; base-uri 'none'">` and remove inline handlers.

---

### S11 ✅ — Third-party asset loads leak usage metadata (and belie the "offline" claim)

**Privacy · Low**

The web app is marketed as the zero-install/local option, but every page load contacts Google (`fonts.googleapis.com`, `fonts.gstatic.com`), Cloudflare (cdnjs) and jsDelivr, disclosing the user's IP, User-Agent and referring URL. No `Referrer-Policy` is set. The **images themselves are never uploaded** (verified: no `fetch`/`XHR`/`WebSocket`/`sendBeacon` in `app.js`; all three file inputs use `FileReader`), so this is metadata leakage, not data leakage. The same gap makes the "double-click `index.html` offline" workflow incomplete (fonts/icons fail to load).

**Remediation:** self-host the two fonts and the icon webfont (or drop Font Awesome for inline SVG icons), add `referrer-policy: no-referrer` / `<meta name="referrer" content="no-referrer">`, and update the README to describe the app as "no upload" rather than "no network".

---

### S12 ✅ — No crash policy: every bug is an availability incident, with no forensic trail

**CWE-248/391 · Low**

Verified: an exception inside a Qt slot or `paintEvent` aborts the process (`exit code 134`; reproduced via the profile panel's `ZeroDivisionError`, `profile_panel.py:111`). There is no `sys.excepthook`, no `qInstallMessageHandler`, no crash log, and `launch.bat` uses `pythonw` (stdout discarded). From a security standpoint this means (a) **fail-open on availability** — a malicious or merely malformed input causes a silent, unexplained shutdown, which per C1 destroys unsaved work; (b) **no evidence** for the user or an administrator that a file was what triggered it.

**Remediation:** global exception hook logging to `<app-data>/crash.log` with the loaded file path, a non-fatal error dialog, and `try/except` around decode/import/export paths so failure is graceful and attributable.

---

### S13 ✅ — Insecure temporary-file handling in autosave

**CWE-377/367 · Low**

`main_window.py:945-963` writes `f"{path}.tmp"` in a predictable location and then does `os.remove(path)` + `os.rename(temp_path, path)`. On a shared directory (which the hard-coded C1 path is), another local user can pre-create the `.tmp` name — a symlink there makes the app write the session through it — and the remove/rename pair is a window in which a crash leaves no session (the "atomic" comment in the docstring is not accurate). Errors are swallowed with a bare `except Exception: pass`.

**Remediation:** `tempfile.NamedTemporaryFile(dir=os.path.dirname(path), delete=False, mode="w")` + `os.replace()` (atomic on POSIX and Windows) + explicit error surfacing.

---

### S14 ✅ — Information disclosure: real username in source, absolute paths in exports

**CWE-200/209 · Low**

* `main_window.py:921` contains the author's real Windows account name and a private directory path (`C:\Users\DEVANANDAN K C\...`) in a public repository.
* `project.to_dict()`/`serialize_session()` write the **absolute path** of the image into every exported `*_labels.json` and session file (`"image_path": "/home/…/gel.png"`); CSV reports from the colony dialog record the source image path too. Every artefact a user shares therefore discloses their directory layout, OS username and sometimes the customer/project folder name.

**Remediation:** remove the hard-coded path entirely (use app-data dirs); store the file *name* (plus a relative path when the image sits next to the JSON) instead of an absolute path, with an explicit "include full path" opt-in; strip paths from colony CSV reports.

---

### S15 ℹ️ — No release integrity artifacts or CI gates

**Info**

No `.github/workflows`, no tests, no SBOM, no signed builds, no hashes published for the ZIP/USB distribution that the README promotes (see S5). All published artefacts are whatever was on the author's disk. A minimal CI (lint + `pip-audit` + pytest + `node --check docs/app.js` + jsdom smoke test + `sha256sum` on release assets) would provide both regression safety and a verifiable provenance story.

---

## 4. Dependency & supply-chain summary

| Component | Declared | Audit result | Action |
|---|---|---|---|
| PyQt6 | `>=6.4.0` | floor = Qt 6.4.0 (2022); image-format CVEs fixed later (CVE-2024-25580, CVE-2025-5683) | raise floor, keep current |
| opencv-python | `>=4.5.0` | floor < 4.8.1.78 (CVE-2023-4863 libwebp, exploited ITW); 4.10/4.11 affected by CVE-2025-53644 (crafted JPEG heap write) | raise to `>=4.12.0`, prefer `-headless` |
| Pillow | `>=9.0.0` | CVE-2022-22817 (ImageMath RCE), CVE-2022-24303 (arbitrary file deletion) fixed in 9.0.1; only used by `create_mock_gel.py` | `>=9.0.1` or move to `dev` extra |
| python-pptx | `>=1.0.2` | no advisory found | pin + hash |
| numpy | *not declared* | imported directly by the app | add explicit constraint |
| pptxgenjs 3.12.0 (CDN) | tag, no SRI | no advisory for the package ([Snyk](https://security.snyk.io/package/npm/pptxgenjs)); delivery path is the risk | vendor + SRI |
| Font Awesome 6.4.0 / Google Fonts (CDN) | no SRI | n/a | vendor locally (privacy, S11) |

`pip-audit -r requirements.txt` and `pip-audit -r <current lockless set>` currently report **no known vulnerabilities** for the versions a today-resolver installs — the exposure is the un-pinned floor plus the absence of any automated gate. Recommendation: `pip-compile --generate-hashes` (or `uv`) + monthly `pip-audit` in CI + a documented upgrade cadence. Note `pip-audit` could not resolve the *floor* versions itself (old wheels are not available for modern Python), which is precisely why the floors must be raised in the manifest rather than trusted to the resolver.

---

## 5. Privacy & data-protection notes

1. **No data leaves the machine** (verified: zero network-egress APIs in `app.js`, no HTTP client in the Python code, no telemetry, no analytics, no accounts). This is the project's strongest privacy property — keep it, and say so precisely in the README ("no upload"; the page does load fonts/icons from CDNs, S11).
2. **Sensitive data is stored in plain text** in the session/autosave file and in `*_labels.json`; label text is free-form, so sample or patient identifiers will end up there. If the tool is used with identifiable data, document that exports are the user's responsibility and add the permission fix (S7).
3. **Exports leak absolute paths** (S14) — a small but real disclosure when figures/data are shared.
4. **GitHub Pages publishing surface** is limited to 4 files (`docs/index.html`, `app.js`, `style.css`, `logo.png`) and contains no user data or secrets. ✅ Verified.
5. **Committed binaries** (`mock_gel.png` 325 KB, `user_gel.jpg` 102 KB) are sample data with no metadata check performed; if they ever came from a real experiment they may carry EXIF (device, timestamps, possibly GPS). Recommend stripping metadata from any sample shipped in the repo (the web app's exports use canvas rendering, so they strip EXIF implicitly — desktop PNG export preserves nothing from the source file either, good).

---

## 6. What is already good (verified)

* **No secrets or credentials anywhere**, including full git history — every file ever committed was enumerated and the tree grepped for API keys, tokens, passwords and private keys: none found. ✅
* **No dangerous primitives in Python:** no `eval`/`exec`/`pickle`/`marshal`/`os.system`/`shell=True` anywhere. ✅
* **No SQL, no HTML rendering of untrusted data on the desktop side** (Qt text items render plain text, not markup), so no desktop-side injection sink for label text.
* **No remote attack surface:** the desktop app opens no sockets; the web app has no backend and performs no uploads. ✅
* **Published artefact set is minimal** (4 files, no data). ✅
* **File-dialog filters** restrict the picker to image extensions (cosmetic only — see S2 — but it does reduce casual exposure).
* **`ColonyDetector.detect_colonies()` handles `None`/tiny inputs gracefully** and returns `[], None` rather than raising (verified with four adversarial formats: 16-bit TIFF, CMYK JPEG, RGBA PNG, grayscale PNG — the latter three yield 0 objects and no exception).
* `.gitignore` correctly excludes `__pycache__`, `*.json.bak`, `.autosave_session.json`, IDE folders and OS artefacts.

---

## 7. Hardening backlog (ordered)

| Priority | Action | Addresses | Effort |
|---|---|---|---|
| 1 | Validate every imported JSON (schema: types, ranges, hex colour, unique IDs, caps) and never let a bad field reach Qt | S1 | S |
| 2 | Neutralise CSV/formula-injection cells + RFC 4180 quoting on both platforms | S4 | S |
| 3 | Validate and DOM-build instead of `innerHTML`; add CSP + vendor CDN assets | S3, S10, S11 | S/M |
| 4 | Raise dependency floors, add `numpy`, generate a hash-pinned lock file, add CI gates (`pip-audit`, pyflakes, jsdom smoke test, `node --check`) | S2, S15 | S |
| 5 | Global exception hook + crash log; wrap decode/import/export | S12 (+ bug C3) | S |
| 6 | Session/autosave: user-data dir, `0o600`, `NamedTemporaryFile` + `os.replace` | S7, S13 (+ bug C1) | S |
| 7 | Sanitise filename derivation; store relative image paths; drop full paths from exports | S8, S14 | S |
| 8 | Caps + progress for pattern expansion and JSON import | S9 | S/M |
| 9 | Replace bare `pip`/`python` with `-m` invocations; add `--require-hashes`; drop VBScript generation (use pywin32/PowerShell with proper quoting) | S5, S6 | S |
| 10 | Signed, hash-published releases; README warning about running only released archives | S5, S15 | M |
| 11 | Threat-model note in the README: "files from collaborators are untrusted input" | all | S |

---

## 8. Residual risk after the above

* **Third-party image decoders remain the main residual risk** (Qt + OpenCV are large C/C++ surfaces). Mitigations are version currency, running the app as an unprivileged desktop user, and never opening files from untrusted origins — no sandboxing is present or planned. For a lab tool used on internal, trusted data this is an acceptable risk; document it.
* **Full disk encryption / OS account hygiene** dominate the confidentiality of stored gel data; application-layer controls cannot substitute for them.
* **GitHub Pages origin sharing** is inherent to publishing the web app under a user-origin path; the CSP fix (S10) and session validation (S3) reduce but do not eliminate the blast radius of a sibling-page compromise. Publishing under a dedicated custom domain would isolate the origin if that ever becomes a concern.

---

## 9. Appendix — reproduce every verification in this report

```bash
# Environment used: Python 3.11, PyQt6 6.11.0, opencv-python-headless 4.14.0.94, numpy 2.4.6,
# Pillow 12.3.0, python-pptx 1.0.2; PyQt6 run headless with QT_QPA_PLATFORM=minimal.

# Dependency & supply chain
pip-audit -r requirements.txt                       # "No known vulnerabilities found" (latest resolver)
pip-audit --no-deps -r min-versions.txt             # floor versions (see §4 for the known CVEs)

# Secrets & history
git log --all --pretty=format: --name-only --diff-filter=A | sort -u
grep -rniE '(api[_-]?key|secret|passwd|password|token|BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16})' . \
  --exclude-dir=.git --exclude='*.md'

# S1 — hostile labels.json aborts the app (expect EXIT CODE: 134)
python3 -X faulthandler sec3.py       # loads {"font_size": "big"} then QTimer.singleShot(0, canvas.deferred_reload)

# S4 — CSV injection (expect the raw formula in the output)
python3 sec_csv.py                    # load_from_json({'text': "=cmd|'/c calc'!A0"}) → export_to_csv

# S3 — stored XSS (expect: injected <img> element inside SVG : true)
node poc6.js                          # jsdom + poisoned pcr_gel_genie_session → renderActiveTabGrid()

# S7 — permissions of created files
python3 sec1.py                       # prints oct(mode) for the session file and CSV exports

# S8/S9 — path traversal & resource growth
python3 sec1.py; python3 sec2.py      # suggested filename + label-count/RSS scaling table

# S6 — VBScript injection (prints the generated script for a folder containing a quote)
python3 sec4.py
```

*(Scripts are the throw-away harnesses used during this audit; each is self-contained and prints the evidence lines quoted above.)*
