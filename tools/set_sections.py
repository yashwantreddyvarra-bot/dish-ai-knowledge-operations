import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
qf = ROOT / "questions.json"
d = json.loads(qf.read_text(encoding="utf-8"))
for q in d["questions"]:
    i = q["id"]
    q["section"] = "Products" if i <= 25 else ("Self-service" if i <= 38 else "Payment")
qf.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
print("sections set for", len(d["questions"]), "questions")
