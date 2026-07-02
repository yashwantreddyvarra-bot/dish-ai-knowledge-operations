# make_launcher.py - creates a one-double-click Desktop shortcut for the bubble.
# Run once:  python make_launcher.py
import os, sys, subprocess

here = os.path.dirname(os.path.abspath(__file__))
desktop = os.path.join(os.path.expanduser("~"), "Desktop", "DISH Assistant.lnk")
py = sys.executable  # the python.exe currently running this

def q(s): return s.replace("'", "''")

ps = ";".join([
    "$W = New-Object -ComObject WScript.Shell",
    "$S = $W.CreateShortcut('%s')" % q(desktop),
    "$S.TargetPath = '%s'" % q(py),
    "$S.Arguments = 'desktop.py'",
    "$S.WorkingDirectory = '%s'" % q(here),
    "$S.WindowStyle = 7",                       # launch the console minimised
    "$S.Description = 'DISH POS Knowledge Assistant'",
    "$S.Save()",
])

subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], check=True)
print("Created Desktop shortcut ->", desktop)
print("Double-click 'DISH Assistant' on your Desktop to launch the bubble.")
