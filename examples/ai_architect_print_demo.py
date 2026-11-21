"""Follow every architecture layer without Ollama, Redis or PostgreSQL."""
from app.architecture.reference_pipeline import Request, run

def retrieve(tenant, question):
    print("2. Retrieval: tenant =", tenant, "question =", question)
    return [{"source":"returns.pdf:1",
             "text":"Eligible returns within 14 days. Email help@example.com"}]

def generate(question, hits, provider):
    print("4. Provider:", provider, "received:", hits[0]["text"])
    return "Eligible returns within 14 days [returns.pdf:1]"

def observe(**event):
    print("6. Monitoring:", {k: round(v,2) if isinstance(v,float) else v
                              for k,v in event.items()})

print("1. API/auth: received tenant-scoped request")
result = run(Request("tenant-a","What is the return period?"),
             retrieve,generate,observe)
print("3. Guardrail: evidence was redacted before the LLM")
print("5. Evaluation:", result["status"])
print("7. API response:",result["answer"])
print("8. Next: add durable LangGraph approval when an action needs a human")
