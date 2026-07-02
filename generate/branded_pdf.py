# DISH-style how-to PDF renderer (matches the official iorad layout).
from pathlib import Path
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ORANGE = HexColor("#EC6A38"); INK = HexColor("#384D60")
GREY = HexColor("#9aa5b0"); LIGHT = HexColor("#e5e7eb"); GREEN = HexColor("#1c7c40")
PAGE = landscape(A4); W, H = PAGE

def _logo(c, x, y):
    c.setFillColor(ORANGE); c.roundRect(x, y, 26, 26, 6, fill=1, stroke=0)
    c.setFillColor(HexColor("#ffffff")); c.setFont("Helvetica-Bold", 16); c.drawCentredString(x+13, y+6, "D")
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 15); c.drawString(x+34, y+8, "D I S H")

def _header(c, title, note=None, note_color=GREY):
    top = H - 52; _logo(c, 40, top-4)
    c.setStrokeColor(LIGHT); c.setLineWidth(1); c.line(150, top-8, 150, top+26)
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 16); c.drawString(166, top+4, title)
    if note:
        c.setFillColor(note_color); c.setFont("Helvetica-Bold", 8); c.drawRightString(W-40, top+18, note)

def _icon(c, x, y, action):
    c.setLineWidth(1.4)
    if action == "info":
        c.setStrokeColor(ORANGE); c.setFillColor(HexColor("#ffffff")); c.rect(x, y, 18, 18, fill=1, stroke=1)
        c.setFillColor(ORANGE); c.setFont("Helvetica-Bold", 12); c.drawCentredString(x+9, y+4, "i")
    else:
        c.setStrokeColor(ORANGE); c.setFillColor(HexColor("#ffffff")); c.roundRect(x+3, y, 12, 18, 6, fill=1, stroke=1)
        c.setStrokeColor(ORANGE); c.setLineWidth(1.2); c.line(x+9, y+9, x+9, y+14)

def _caption(c, x, y, max_w, text, highlight):
    hi = set((highlight or "").lower().replace("+", "").split()); words = text.split()
    c.setFont("Helvetica", 13); space = c.stringWidth(" ", "Helvetica", 13); cx, cy = x, y
    for w in words:
        ww = c.stringWidth(w, "Helvetica", 13)
        if cx + ww > x + max_w: cx = x; cy -= 18
        clean = w.strip(".,").lower()
        c.setFillColor(ORANGE if (highlight and clean in hi) else INK); c.drawString(cx, cy, w); cx += ww + space

def _shot(c, step, path):
    ax, ay, aw, ah = 60, 40, W-120, H-200
    if not path or not Path(path).exists():
        c.setStrokeColor(LIGHT); c.setFillColor(HexColor("#fafafa")); c.roundRect(ax, ay, aw, ah, 8, fill=1, stroke=1)
        c.setFillColor(GREY); c.setFont("Helvetica-Oblique", 12); c.drawCentredString(W/2, ay+ah/2, "screenshot pending capture"); return
    try:
        img = ImageReader(path); iw, ih = img.getSize(); sc = min(aw/iw, ah/ih); dw, dh = iw*sc, ih*sc
        dx = ax+(aw-dw)/2; dy = ay+(ah-dh)/2
        c.drawImage(img, dx, dy, width=dw, height=dh, preserveAspectRatio=True, mask="auto")
    except Exception:
        c.setStrokeColor(LIGHT); c.setFillColor(HexColor("#fafafa")); c.roundRect(ax, ay, aw, ah, 8, fill=1, stroke=1)
        c.setFillColor(GREY); c.setFont("Helvetica-Oblique", 12); c.drawCentredString(W/2, ay+ah/2, "screenshot pending capture")
        return
    bbox = step.get("bbox")
    if bbox and len(bbox) == 4:
        bx, by, bw, bh = bbox; rx = dx+bx*sc; ry = dy+(ih-(by+bh))*sc
        c.setStrokeColor(ORANGE); c.setLineWidth(2.5); c.roundRect(rx, ry, bw*sc, bh*sc, 4, fill=0, stroke=1)

def _page_no(c, n, total):
    c.setFillColor(GREY); c.setFont("Helvetica", 9); c.drawRightString(W-40, 22, f"{n} of {total}")

def build_branded_pdf(script, shots_by_step, out_path, source_note=None, live=False):
    title = script.get("title", "How-to guide"); steps = script["steps"]; total = len(steps)+1
    nc = GREEN if live else GREY
    c = canvas.Canvas(str(out_path), pagesize=PAGE)
    for i, s in enumerate(steps, 1):
        _header(c, title, source_note, nc); _icon(c, 40, H-96, s.get("action", "click"))
        _caption(c, 72, H-88, W-140, s["caption"], s.get("highlight", "")); _shot(c, s, shots_by_step.get(s["step"]))
        _page_no(c, i, total); c.showPage()
    _header(c, title, source_note, nc); c.setFillColor(INK); c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(W/2, H/2+10, "You're all set.")
    c.setFillColor(nc); c.setFont("Helvetica", 11); c.drawCentredString(W/2, H/2-14, source_note or "")
    _page_no(c, total, total); c.showPage(); c.save(); return out_path
