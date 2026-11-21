"""Run with: python -m app.advanced_rag.worker"""
from rq import Worker
from app.advanced_rag.jobs import connection

def main():
    Worker(["arinova-ingestion"], connection=connection()).work()

if __name__ == "__main__":
    main()
