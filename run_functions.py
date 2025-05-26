import os
from pathlib import Path
import subprocess
import webbrowser

def run_crop():
    # this file is Fooocus/entry_with_update.py
    here     = Path(__file__).resolve().parent          # …\Fooocus
    project  = here.parent                              # …\Fooocus_win64_2-5-0\Fooocus_win64_2-5-0
    bat_path = project / "crop.bat"
    if not bat_path.exists():
        raise FileNotFoundError(f"Could not find {bat_path}")
    subprocess.Popen([str(bat_path)], cwd=str(project), shell=True)

def run_prompt():
    here     = Path(__file__).resolve().parent
    project  = here.parent
    bat_path = project / "prompt.bat"
    if not bat_path.exists():
        raise FileNotFoundError(f"Could not find {bat_path}")
    # First open the browser window directly from Python
    webbrowser.open("http://localhost:7863")
    # Then run the batch file
    subprocess.Popen([str(bat_path)], cwd=str(project), shell=True)
    
def run_reorganize():
    here     = Path(__file__).resolve().parent
    project  = here.parent
    bat_path = project / "reorganize.bat"
    if not bat_path.exists():
        raise FileNotFoundError(f"Could not find {bat_path}")
    subprocess.Popen([str(bat_path)], cwd=str(project), shell=True)

def run_browse():
    here     = Path(__file__).resolve().parent
    project  = here.parent
    bat_path = project / "browse.bat"
    if not bat_path.exists():
        raise FileNotFoundError(f"Could not find {bat_path}")
    subprocess.Popen([str(bat_path)], cwd=str(project), shell=True)

def run_wildcard():
    here     = Path(__file__).resolve().parent
    project  = here.parent
    bat_path = project / "wildcard.bat"
    if not bat_path.exists():
        raise FileNotFoundError(f"Could not find {bat_path}")
    # First open the browser window directly from Python
    webbrowser.open("http://localhost:7862")
    # Then run the batch file
    subprocess.Popen([str(bat_path)], cwd=str(project), shell=True)
