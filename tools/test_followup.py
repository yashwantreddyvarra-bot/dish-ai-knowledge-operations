"""Drives the real server chat (with memory) through follow-up + tricky flows and prints
the guide each lands on, so we can see routing without the browser."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import server  # noqa
client = server.app.test_client()


def ask(m):
    r = client.post("/api/chat", json={"message": m, "polish": False}).get_json() or {}
    return r.get("qid"), (r.get("title") or "")[:42], r.get("action")


print("=" * 70)
print("FLOW 1 - memory / follow-up")
for m in ["add a spicy chicken wrap as a food", "now restrict it to lunch only"]:
    qid, title, act = ask(m)
    print("  '%s'\n     -> Q%s %s (%s)" % (m, qid, title, act))
print("  EXPECT: follow-up -> Q17 (time periods), NOT Q3 (sales restrictions)")

print("=" * 70)
print("FLOW 2 - fresh conversation, tricky one-offs")
server.CHAT_MEMORY.clear()
for m in ["the kitchen keeps printing paper for every order, make it stop",
          "I want to change how much something costs",
          "add a passion fruit mocktail for 6.50, list its allergens, show it on the lunch menu"]:
    qid, title, act = ask(m)
    print("  '%s'\n     -> Q%s %s (%s)" % (m, qid, title, act))
print("  EXPECT: printing->Q21 ; change-cost->clarify ; mocktail->Q1 merge")
print("=" * 70)
