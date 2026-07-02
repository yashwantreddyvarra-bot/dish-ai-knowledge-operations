# desktop.py - opens the DISH Assistant as a normal desktop window.
# Run:  python desktop.py   (or double-click the "DISH Assistant" Desktop icon)
# A normal app window titled "DISH POS Assistant" opens in the centre of your screen.
# Colleagues open the printed http://<your-ip>:5000/widget link in their own browser.
import sys, socket, threading, time, ctypes
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import webview          # pip install pywebview
import server           # the Flask app (server.app)

PORT = 5000

# --- correct coordinates on high-DPI / scaled displays ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try: ctypes.windll.user32.SetProcessDPIAware()
    except Exception: pass

def screen_size():
    try:
        u = ctypes.windll.user32
        return int(u.GetSystemMetrics(0)), int(u.GetSystemMetrics(1))
    except Exception:
        return 1920, 1080

SW, SH = screen_size()
WIN_W = 400
WIN_H = min(680, SH - 120)

def win_pos():
    # centre of the screen, never off-screen
    return max(0, (SW - WIN_W) // 2), max(0, (SH - WIN_H) // 3)

def _port_open(host, port):
    s = socket.socket(); s.settimeout(0.4)
    try: s.connect((host, port)); return True
    except Exception: return False
    finally:
        try: s.close()
        except Exception: pass

def _start_server():
    server.app.run(host="0.0.0.0", port=PORT, threaded=True, use_reloader=False)

def _lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close(); return ip
    except Exception:
        return "127.0.0.1"

class Api:
    """Called from the page (window.pywebview.api.*)."""
    def minimize(self):
        try: webview.windows[0].minimize()
        except Exception: pass
    def close(self):
        try: webview.windows[0].destroy()
        except Exception: pass
    # kept so older button handlers don't error
    def expand(self): pass
    def collapse(self): self.minimize()

if __name__ == "__main__":
    if not _port_open("127.0.0.1", PORT):
        threading.Thread(target=_start_server, daemon=True).start()
        for _ in range(60):
            if _port_open("127.0.0.1", PORT): break
            time.sleep(0.25)

    ip = _lan_ip()
    host = socket.gethostname()
    print("=" * 60)
    print("  DISH POS Assistant - window is opening")
    print("  On this PC        :  the window opens in the centre of your screen")
    print("  Share (by name)   :  http://%s:%d/widget" % (host, PORT))
    print("  Share (by IP)     :  http://%s:%d/widget" % (ip, PORT))
    print("  (colleagues on the same Wi-Fi open either link in any browser)")
    print("=" * 60)

    x, y = win_pos()
    webview.create_window(
        "DISH POS Assistant",
        "http://127.0.0.1:%d/widget" % PORT,
        js_api=Api(),
        x=x, y=y, width=WIN_W, height=WIN_H,
        frameless=False, on_top=True, resizable=True,
        min_size=(340, 480), background_color="#FFFFFF",
    )
    webview.start()
