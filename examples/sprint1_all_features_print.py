"""Beginner print demo: no Redis, database or Ollama needed."""
from app.reliability.resilience import retry_call

def main():
    attempts = 0
    def ask_ai():
        nonlocal attempts
        attempts += 1
        print(f"Attempt {attempts}: asking AI")
        if attempts < 3:
            print("Server busy; retrying")
            raise TimeoutError("Temporary error")
        print("AI answered successfully")
        return "Welcome to AriNova"

    answer = retry_call(ask_ai, retryable=lambda error: isinstance(error, TimeoutError),
                        attempts=3, base_delay=0, sleep=lambda _: None)
    print("Final answer:", answer)
    print("Cancellation: set a flag; each workflow step checks it.")
    print("Recovery: inspect saved checkpoints; never blindly repeat external actions.")
    print("Dead-letter: failed jobs remain available for admin inspection.")
    print("Replay: Redis reserves a job ID to block simultaneous replays.")
    print("Idempotency: the same request key should return its original result.")
    print("Deadline: stop starting new steps when the time budget expires.")

if __name__ == "__main__":
    main()
