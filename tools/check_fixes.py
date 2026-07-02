import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from intelligence import agent

QS = [
    "set Baileys to 6.50 euros",
    "change the price of 7-Up to 2.80",
    "set the flat white to 3.20",
    "change Bombay Gin to 8",
    "change the price of Zombie Smoothie to 9",
    "add a halloumi burger containing milk, gluten and sesame",
    "add a chai oat latte for 3.90 and put it on the menu",
]
lines = ["price-edit patterns: %d (expect 7)" % len(agent._PRICE_EDIT_AMT),
         "has _is_price_change_intent: %s" % hasattr(agent, "_is_price_change_intent"),
         "has _extract_allergens: %s" % hasattr(agent, "_extract_allergens"), ""]
for q in QS:
    pl = agent.plan(q); p = pl.get("params", {}) or {}
    lines.append("%-48s -> guides=%s name=%r type=%r allergens=%r" % (
        q, pl.get("guides"), p.get("product_name"), p.get("type"), p.get("allergens")))
out = "\n".join(lines)
print(out)
(Path(__file__).resolve().parent / "check_fixes_out.txt").write_text(out, encoding="utf-8")
