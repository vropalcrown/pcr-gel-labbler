import os
import subprocess

def create_desktop_shortcut():
    script_dir = os.path.abspath(os.path.dirname(__file__))
    target_bat = os.path.join(script_dir, "launch.bat")
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut_path = os.path.join(desktop, "Gel Labeler.lnk")
    
    # Escape quotes for VBScript
    vbs_target = target_bat.replace('"', '""')
    vbs_workdir = script_dir.replace('"', '""')
    vbs_shortcut = shortcut_path.replace('"', '""')
    
    vbs_content = f'''Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{vbs_shortcut}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{vbs_target}"
oLink.WorkingDirectory = "{vbs_workdir}"
oLink.Description = "Gel Labeler - PCR Gel Genie & AI Colony Counter"
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

