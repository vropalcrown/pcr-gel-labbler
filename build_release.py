"""
Build script to compile Gel Labeler into a standalone, commercial-grade Windows executable.
Run with: python build_release.py
"""
import os
import sys
import subprocess

def build():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    icon_path = os.path.join("gel_labeler", "gui", "logo.ico")
    logo_png_path = os.path.join("gel_labeler", "gui", "logo.png")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--windowed",
        "--name=GelLabeler",
        f"--icon={icon_path}",
        f"--add-data={icon_path};gel_labeler/gui",
        f"--add-data={logo_png_path};gel_labeler/gui",
        "--clean",
        "--noconfirm",
        "run.py"
    ]
    
    print("Building Gel Labeler standalone executable...")
    result = subprocess.run(cmd)
    if result.returncode == 0:
        exe_path = os.path.abspath(os.path.join("dist", "GelLabeler", "GelLabeler.exe"))
        print(f"\n[SUCCESS] Build completed successfully!")
        print(f"Executable location: {exe_path}")
    else:
        print(f"\n[ERROR] Build failed with return code {result.returncode}")
        sys.exit(result.returncode)

if __name__ == "__main__":
    build()
