# 🧬 Molecular Biology Suite — Gel Labeler, Master Mixer, Protocols & Plate Designer

A high-performance, publication-ready bioinformatics desktop suite designed for molecular biology and biochemistry laboratories.

---

## 🌟 Modules Included in the Suite

### 1. 🧬 Gel Electrophoresis Annotator
* **Multi-Tab Workspace**: Open and analyze multiple gel images simultaneously.
* **Fast Well & Lane Marking**: 2-click well boundary span marking with automatic lane spacing and custom rotation.
* **Direct Label Placement**: Double-click or right-click to place single labels, molecular ladders, and sample tags.
* **PowerPoint Export**: Direct 16:9 widescreen presentation export with editable native PowerPoint text boxes.
* **CSV & JSON Persistence**: Tabular data export and project persistence.

### 2. 🧪 Master Mixer (PCR & Reaction Recipe Calculator)
* **Streamlined 4-Column Layout**: Component name, 1x volume, master mix inclusion checkbox, and total volume.
* **Auto-Water Balancing**: Automatically calculates required nuclease-free water volume to reach target reaction volume.
* **Pipetting Margin**: Configurable excess percentage (e.g. +10%) or reaction count multiplier.
* **Custom User Presets**: Save and manage your laboratory master mix recipes persistently in AppData.
* **Standard Presets Included**: Taq PCR, High-Fidelity Q5/Phusion, SYBR Green qPCR, Restriction Enzyme Digest, and Reverse Transcription cDNA synthesis.

### 3. 📋 Lab Protocols & Interactive SOP Runner
* **Custom SOP Checklist**: Clean slate out-of-the-box allowing researchers to create, edit, save, import, and export protocols.
* **Step Timers & Audio Alert**: Countdown timers for incubation steps with completion chime.
* **Persistent Storage**: Saves custom protocols to local AppData.

### 4. 🧫 AI Vision Colony & Seed Counter
* **Automated Counting**: Distance transform and watershed segmentation to split clustered colonies.
* **Dish Auto-Masking**: Detects circular petri dish boundaries and ignores rim glare.
* **Interactive Touch-Up**: Left-click to add missed colonies, Right-click to remove false positives.
* **CFU/mL Calculator**: Real-time concentration estimation with dilution factor scaling.

### 5. ▦ Multiwell Plate Designer & Labeler
* **Flexible Plate Formats**: 6-, 12-, 24-, 48-, 96-, 384-well plates and custom $R \times C$ grid dimensions.
* **Multi-Selection**: Click, Ctrl+Click, Shift+Click bounding box range, and rubberband drag-box selection.
* **Batch Editing**: Assign titles, roles (*Sample, Standard, Control, Blank, Positive, Negative, Treated*), concentrations, and color swatches.
* **Auto-Numbering Series**: Automatically numbers selected wells (e.g., "Sample 01", "Sample 02") across rows or columns.
* **Dual CSV & High-Res PNG Export**: Export 2D grid matrix CSVs, relational sample tables, or 300 DPI high-resolution diagram images.

---

## 🚀 How to Run the App (For Users Downloading from GitHub)

### Option A: Running from Source (Requires Python 3.10+)
1. **Download or Clone this Repository**:
   ```bash
   git clone https://github.com/vropalcrown/pcr-gel-labbler.git
   cd pcr-gel-labbler
   ```
2. **One-Click Dependency Installation**:
   - Double-click **`Install_Dependencies.bat`** (or run `pip install -r requirements.txt`).
3. **Launch the Application**:
   - Double-click **`launch.bat`** (or **`launch.vbs`** for zero-terminal silent startup).
   - *(Optional)* Double-click **`Create_Desktop_Shortcut.bat`** to generate a desktop shortcut with the official logo!

### Option B: Standalone Windows Executable (No Python Required)
* Download the compiled standalone release (`GelLabeler.exe`) from the **[GitHub Releases](https://github.com/vropalcrown/pcr-gel-labbler/releases)** tab.
* Unzip and double-click `GelLabeler.exe` to run immediately on any Windows PC.

---

## 🌐 Zero-Install Web Version (Browser)
Access the lightweight online browser version directly at:
**[https://vropalcrown.github.io/pcr-gel-labbler/](https://vropalcrown.github.io/pcr-gel-labbler/)**

---

## 🛠️ Developer Setup & Testing

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run test suite
python -m unittest discover -s tests -v

# 3. Static analysis lint check
python -m pyflakes run.py create_mock_gel.py create_shortcut.py gel_labeler/

# 4. Build standalone Windows executable
python build_release.py
```
