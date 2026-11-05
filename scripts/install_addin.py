"""Installation script for CADPilot Fusion 360 Add-In.

Detects Autodesk Fusion 360's AddIns directory on macOS or Windows and creates
a symbolic link (or directory copy) pointing to `addin/`.
"""

import os
import sys
import platform
import shutil


def find_fusion_addin_directory() -> str:
    system = platform.system()
    home = os.path.expanduser("~")

    candidate_paths = []

    if system == "Darwin":  # macOS
        candidate_paths = [
            os.path.join(home, "Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns"),
            os.path.join(home, "Library/Application Support/Autodesk/Autodesk Fusion/API/AddIns"),
            os.path.join(home, "Library/Application Support/Autodesk/Fusion 360/API/AddIns")
        ]
    elif system == "Windows":
        appdata = os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming"))
        candidate_paths = [
            os.path.join(appdata, "Autodesk", "Autodesk Fusion 360", "API", "AddIns"),
            os.path.join(appdata, "Autodesk", "Autodesk Fusion", "API", "AddIns")
        ]
    else:
        print(f"[!] Unsupported operating system for direct Fusion installation: {system}")
        sys.exit(1)

    for path in candidate_paths:
        if os.path.exists(path):
            return path

    # If not found yet, default to standard primary path and create it
    primary = candidate_paths[0]
    os.makedirs(primary, exist_ok=True)
    return primary


def install_addin():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    addin_source = os.path.join(repo_root, "addin")

    if not os.path.exists(addin_source):
        print(f"[!] Source addin directory not found at: {addin_source}")
        sys.exit(1)

    addins_dir = find_fusion_addin_directory()
    target_link = os.path.join(addins_dir, "CADPilotBridge")

    print(f"Target Fusion AddIns Directory: {addins_dir}")

    # Remove existing link/directory if present
    if os.path.islink(target_link) or os.path.isfile(target_link):
        os.unlink(target_link)
    elif os.path.isdir(target_link):
        shutil.rmtree(target_link)

    # Attempt symlink first
    try:
        os.symlink(addin_source, target_link, target_is_directory=True)
        print(f"✅ Successfully created symlink:\n   {target_link} -> {addin_source}")
    except Exception as e:
        print(f"[i] Symlink failed ({e}), attempting directory copy...")
        shutil.copytree(addin_source, target_link)
        print(f"✅ Successfully copied add-in to:\n   {target_link}")

    print("\nNext Steps:")
    print("1. Open Autodesk Fusion 360.")
    print("2. Press 'Shift + S' (or go to Utilities > Add-Ins > Scripts and Add-Ins).")
    print("3. Select the 'Add-Ins' tab.")
    print("4. Select 'CADPilotBridge' and click 'Run'.")
    print("5. Open the Text Palette ('Cmd + Option + C' or 'Ctrl + Alt + C') to see server logs.")


if __name__ == "__main__":
    install_addin()

