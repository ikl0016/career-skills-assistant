import argparse, json
from agent import Session

p = argparse.ArgumentParser()
p.add_argument("--employee", default="E001", help="Simulated sign-in (E001, E002, E003)")
args = p.parse_args()

session = Session(args.employee)
print(f"Signed in as {args.employee}. Type 'quit' to exit.")

while True:
    q = input("\nYou: ").strip()
    if not q:                       # ignore empty input instead of calling the model
        continue
    if q.lower() in {"quit", "exit"}:
        break
    r = session.ask(q)
    print("\nAssistant:", r["message"])
    if r["recommendations"]:
        print(json.dumps(r["recommendations"], indent=2))
    last = session.log[-1] if session.log else {}
    print(f"[tools: {[t['tool'] for t in session.trace]} | "
          f"valid JSON: {r['valid']} | {last.get('ms')} ms, {last.get('tokens')} tokens]")
