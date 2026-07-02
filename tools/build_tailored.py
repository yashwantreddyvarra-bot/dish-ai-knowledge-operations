"""Proof that the guide is generated dynamically from the question's product.
Builds Q1 live with a given product NAME and rebuilds its PDF+video.
Usage: python -m tools.build_tailored "Burger" 7.50
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

name = sys.argv[1] if len(sys.argv) > 1 else "Burger"
price = sys.argv[2] if len(sys.argv) > 2 else "7.50"
print("Building Q1 live with NAME=%r PRICE=%r ..." % (name, price))
from capture import engine
engine.main(qid=1, headless=False, extra_vars={"NAME": name, "PRICE": price})
from generate import doc_generator
doc_generator.build(1)
# save fresh-inode proof copies (dodge any stale read cache) of key frames
import shutil, re, time
safe = re.sub(r"[^A-Za-z0-9]+", "_", name)
stamp = time.strftime("%H%M%S")
for stepn, tag in [("05", "name"), ("06", "group"), ("11", "search"), ("18", "menu")]:
    src = ROOT / "output" / "vframes" / "q01" / ("step_%s.png" % stepn)
    if src.exists():
        dst = ROOT / "output" / ("proof_%s_%s_%s.png" % (tag, safe, stamp))
        shutil.copy(src, dst)
        print("PROOF -> %s" % dst.name)
print("DONE - the form screenshots should now show %r" % name)
