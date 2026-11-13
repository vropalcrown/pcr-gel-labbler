import os
import sys
import shutil
import subprocess

def create_desktop_shortcut():
    script_dir = os.path.abspath(os.path.dirname(__file__))
    run_py = os.path.join(script_dir, "run.py")
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut_path = os.path.join(desktop, "Gel Labeler.lnk")
    
    exe_path = os.path.join(script_dir, "dist", "GelLabeler", "GelLabeler.exe")
    if os.path.exists(exe_path):
        target_path = exe_path
        arguments = ""
        work_dir = os.path.dirname(exe_path)
    else:
        # Locate pythonw.exe (GUI subsystem, completely avoids terminal console popup)
        pythonw_path = shutil.which("pythonw")
        if not pythonw_path:
            cand = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            pythonw_path = cand if os.path.exists(cand) else sys.executable
        target_path = pythonw_path
        arguments = f'"{run_py}"'
        work_dir = script_dir
        
    icon_file = os.path.join(script_dir, "gel_labeler", "gui", "logo.ico")
    
    # Escape quotes for VBScript
    vbs_target = target_path.replace('"', '""')
    vbs_workdir = work_dir.replace('"', '""')
    vbs_shortcut = shortcut_path.replace('"', '""')
    vbs_icon = icon_file.replace('"', '""')
    vbs_args = arguments.replace('"', '""')
    
    vbs_content = f'''Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{vbs_shortcut}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{vbs_target}"
oLink.Arguments = "{vbs_args}"
oLink.WorkingDirectory = "{vbs_workdir}"
oLink.Description = "Gel Labeler - Professional Gel Electrophoresis Suite"
oLink.IconLocation = "{vbs_icon},0"
oLink.WindowStyle = 1
oLink.Save
'''
    
    temp_vbs = os.path.join(script_dir, "_make_shortcut.vbs")
    with open(temp_vbs, "w", encoding="utf-8") as f:
        f.write(vbs_content)
        
    try:
        subprocess.run(["cscript", "//nologo", temp_vbs], check=True)
        print("\n=======================================================")
        print(" [SUCCESS] Shortcut created on your Desktop:")
        print(f" {shortcut_path}")
        print("=======================================================\n")
    finally:
        if os.path.exists(temp_vbs):
            os.remove(temp_vbs)

if __name__ == "__main__":
    create_desktop_shortcut()

