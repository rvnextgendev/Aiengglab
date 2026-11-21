"""Beginner-friendly Sprint 2/3/4 demonstration without live services."""
from app.ai_quality.sprint3 import scan_evidence, redact_pii, evaluate
from app.ai_quality.evaluation import evaluate_dataset
from app.observability.sprint4 import record, summary
import tempfile
import os

print("SPRINT 2: Human approval")
print("1. Save a workflow checkpoint")
print("2. Pause with interrupt()")
print("3. Reviewer approves, then Command(resume=True) continues")
print("4. PostgreSQL checkpointer keeps progress after restart")
print()
hits = [{"source":"policy.pdf:page-1","text":"Return within 14 days. Contact help@example.com"}]
print("SPRINT 3: AI safety")
print("Evidence scan:",scan_evidence(hits))
print("PII redaction:",redact_pii(hits[0]["text"]))
print("Citation check:",evaluate("Return within 14 days [policy.pdf:page-1]",hits))
print("Evaluation:",evaluate_dataset([{"hits":hits,"answer":"Return within 14 days [policy.pdf:page-1]","expected_citation_pass":True}]))
print()
print("SPRINT 4: Monitoring")
with tempfile.TemporaryDirectory() as directory:
    os.environ["AI_USAGE_SQLITE_PATH"] = os.path.join(directory,"usage.sqlite")
    record("demo-tenant","answer","ollama",120,True,100,60)
    print("Usage summary:",summary("demo-tenant"))
print("Note: token counts are estimates, not provider billing totals.")
