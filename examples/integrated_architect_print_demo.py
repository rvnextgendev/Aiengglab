"""Integrated POC walkthrough without live Postgres, Redis or Ollama."""
from uuid import uuid4
from tempfile import TemporaryDirectory
import os
from app.ai_workflows import feedback
from app.ai_workflows.integrated import approval_preview
from app.ai_quality.guardrails import apply_answer_policy
from app.observability.sprint4 import record, summary

with TemporaryDirectory() as directory:
    os.environ["WORKFLOW_FEEDBACK_SQLITE_PATH"] = directory + "/feedback.sqlite"
    os.environ["AI_USAGE_SQLITE_PATH"] = directory + "/usage.sqlite"
    tenant = "arinova-demo"
    thread = uuid4().hex
    print("1. UPLOAD: POST /rag/upload -> Redis RQ -> PostgreSQL chunks")
    print("2. SEARCH: LangGraph retrieve() searches only tenant:", tenant)
    hits = [{"source":"returns.pdf:page-1:chunk-0",
             "text":"Eligible returns within 14 days. Contact help@example.com"}]
    print("3. APPROVAL: LangGraph interrupt() pauses, thread_id:", thread)
    print("   Reviewer preview:", approval_preview({"sources":hits}))
    print("4. RESUME: reviewer approves via POST /rag/workflows/{thread_id}/approval")
    answer = "Eligible returns within 14 days [returns.pdf:page-1:chunk-0]"
    verdict = apply_answer_policy(answer, hits)
    print("5. EVALUATION:", verdict["quality_status"])
    print("   Answer:", verdict["answer"])
    print("6. FEEDBACK:", feedback.submit(thread, tenant, "learner", 5, "Helpful"))
    print("   Saved feedback:", feedback.list_for_workflow(thread, tenant))
    record(tenant, "durable_answer", "ollama", 123, True, 200, len(answer))
    print("7. MONITORING:", summary(tenant))
    print("NOTE: Upload, LangGraph resume, and model call are illustrated here.")
    print("Use the actual /rag endpoints for the live integrated workflow.")
