# 🧪 Super Lab Suite — PCR Gel Genie & AI Vision Colony Counter

A modular, publication-ready bioinformatics desktop and web suite designed for molecular biology labs.

---

## 🌟 Modules Included

### 1. ⚡ PCR Gel Genie
* **Gel Electrophoresis Annotation**: High-contrast, outline-rendered well and band labeling.
* **Modeless Visual Reference Grid**: Customizable spacing, offsets, and color presets (`Ctrl + G`).
* **Interactive Densitometry**: Real-time lane profile intensity graph and CSV peak data export.
* **16:9 Widescreen PowerPoint Export**: Multi-deck compilation into editable PowerPoint presentations.

### 2. 🧫 AI Vision Colony & Seed Counter
* **Automated Counting**: Distance transform and watershed segmentation to split clustered colonies and seeds.
* **Petri Dish Auto-Masking**: Automatically detects circular dish boundaries to ignore edge glare.
* **Interactive Touch-Up**: Left-click to add missed markers, Right-click to delete false positives.
* **CFU/mL Calculator**: Real-time concentration computation ($\text{CFU/mL} = \frac{\text{Count} \times \text{Dilution}}{\text{Volume}}$).

---

## 🚀 How to Share & Run on Any Laptop (USB / Network)

When copying the `gel_labeler` folder to a USB stick or another computer:

### 1. 🖥️ Running on Another Laptop:
1. Copy the entire `gel_labeler` folder to the other laptop (or run directly from the USB drive).
2. Open the folder and **double-click `launch.bat`**.
   * *`launch.bat` will automatically check for required libraries and launch the app!*
3. *(Optional)* **Double-click `Create_Desktop_Shortcut.bat`** to create a fresh desktop shortcut on that laptop.

### 2. 🌐 Zero-Install Web Version (Browser):
If the other computer does not have Python installed, you can simply:
* Open the online web app: **[https://vropalcrown.github.io/pcr-gel-labbler/](https://vropalcrown.github.io/pcr-gel-labbler/)**
* Or double-click **`docs/index.html`** in any browser.

---

## 🛠️ Manual Installation (Developers)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run Desktop App
python run.py
```
