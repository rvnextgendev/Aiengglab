"""Beginner-friendly Sprint 1 demo. No network, Ollama, or database required.

Run: python examples/sprint1_print_demo.py
"""
from app.reliability.resilience import CircuitBreaker, CircuitOpen, retry_call


def demo_retry():
    print("\n=== 1. RETRY DEMO ===")
    attempts = 0

    def temporary_failure():
        nonlocal attempts
        attempts += 1
        print(f"Attempt {attempts}: calling Ollama (simulated)")
        if attempts < 3:
            print("Temporary error: server busy")
            raise TimeoutError("Simulated timeout")
        print("Success: received an answer!")
        return "AriNova allows returns within 14 days."

    answer = retry_call(
        temporary_failure,
        retryable=lambda exc: isinstance(exc, TimeoutError),
        attempts=3,
        base_delay=0,  # Demo only: do not wait between attempts.
        sleep=lambda seconds: None,
    )
    print("Final answer:", answer)


def demo_circuit_breaker():
    print("\n=== 2. CIRCUIT BREAKER DEMO ===")
    breaker = CircuitBreaker(failure_threshold=2, recovery_seconds=30)

    def failing_provider():
        print("Calling provider (simulated)")
        raise TimeoutError("Provider unavailable")

    for attempt in range(1, 4):
        print(f"Request {attempt}")
        try:
            retry_call(
                failing_provider,
                retryable=lambda exc: isinstance(exc, TimeoutError),
                attempts=1,
                breaker=breaker,
            )
        except CircuitOpen:
            print("Circuit OPEN: skipped provider call")
        except TimeoutError:
            print("Provider failed")


if __name__ == "__main__":
    demo_retry()
    demo_circuit_breaker()
