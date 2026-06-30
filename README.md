# Gel Electrophoresis Image Labeler (MVP)

A modular, clean, and expandable Python desktop application built with **PyQt6** for labeling wells and lanes in PCR agar gel electrophoresis images.

---

## Key Features

1. **Pixel-Locked Coordinates**: All label coordinates `(x, y)` and font sizes are stored relative to the original image dimensions, ensuring scaling the window does not affect annotation resolution or placement.
2. **Interactive Canvas**:
   - **Click to Add**: Left-clicking on empty spaces of the gel image prompts a settings dialog to add a text label.
   - **Drag & Drop**: Click and drag any label to align it perfectly above the corresponding well. Labels are constrained within the image boundaries.
   - **Pan & Zoom**: Standard navigation for high-res images:
     - **Zoom**: `Ctrl + Mouse Wheel`
     - **Pan**: Drag with `Middle Mouse Button`
     - **Zoom to Fit**: `Ctrl + 0` or Toolbar button
3. **Advanced Text Legibility**: Outlines/drop shadows are automatically rendered behind text labels to ensure they are readable against both fluorescent bands and dark backgrounds.
4. **Data & Image Export**:
   - **Save Labeled Image**: Exports a high-resolution version of the gel with labels burned directly into the pixels using native vector rendering.
   - **Save Label Data (JSON)**: Saves annotations as a JSON database for future reloading or parsing.
   - **Export CSV Spreadsheet**: Exports label locations, sizes, and colors in a clean CSV format for analysis pipelines.

---

## Directory Structure

```
gel_labeler/
├── requirements.txt         # Package dependencies
├── run.py                   # Main launcher script
├── create_mock_gel.py       # Helper script to generate a synthetic gel image
└── gel_labeler/
    ├── __init__.py
    ├── config.py            # Global constants (colors, QSS dark mode styles)
    ├── core/
    │   ├── __init__.py
    │   ├── label.py         # GelLabel data model representing a label
    │   └── project.py       # State manager (image, active labels database)
    └── gui/
        ├── __init__.py
        ├── main_window.py   # Application frame, menus, toolbar, dialogs
        ├── canvas.py        # Graphics View for rendering and interactive events
        ├── label_item.py    # Custom draggable, right-clickable label item
        └── settings_dialog.py # Dialog to adjust text, colors, and font sizes
```

---

## Installation & Setup

### 1. Set Workspace (Recommended)
Open this folder in your IDE workspace:
`C:\Users\DEVANANDAN K C\.gemini\antigravity\scratch\gel_labeler`

### 2. Install Dependencies
Make sure you have Python 3 installed. Install dependencies using pip:
```bash
pip install -r requirements.txt
```

### 3. Generate a Mock Gel Image
If you do not have a gel image handy, run the helper script to generate a synthetic agar gel image (`mock_gel.png`):
```bash
python create_mock_gel.py
```

### 4. Run the Application
Start the Gel Labeler editor:
```bash
python run.py
```

---

## Using the Application

1. **Load Image**: Click **Open Gel Image** and select `mock_gel.png` (or any image).
2. **Add Label**: Click directly above a well (on the dark background). A dialog will appear. Enter text (e.g., `Lane 1`), select a high-contrast color, adjust the size, and click **Apply**.
3. **Adjust Position**: Click and drag the label to align it exactly above the well.
4. **Modify/Delete Label**: Right-click on any existing label to edit its properties or delete it.
5. **Export Labeled Image**: Click **Export Image** to save the annotated gel.
6. **Export Database**: Click **Export CSV** or **File -> Save Label Data (JSON)** to export coordinates.
