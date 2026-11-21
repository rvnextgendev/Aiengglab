"""Easy console demo: cancellation, recovery inventory, deadlines and failed jobs."""
import tempfile
import os
from app.reliability.workflow_control import register, cancel, inventory, is_cancelled
from app.reliability.deadline import deadline, check, OperationCancelled

def main():
    with tempfile.TemporaryDirectory() as folder:
        os.environ["WORKFLOW_CONTROL_PATH"] = os.path.join(folder, "controls.sqlite")
        thread_id = "a" * 32
        print("1. Start workflow:", thread_id)
        register(thread_id, "arinova", "user-1")
        print("2. Recovery inventory:", inventory("arinova"))
        print("3. User requests cancellation")
        cancel(thread_id, "arinova", "user-1")
        print("4. Cancel flag:", is_cancelled(thread_id))
        print("5. Worker checks cancellation before next step")
        try:
            with deadline(10, cancelled=lambda: is_cancelled(thread_id)):
                check()
                print("Running next step")
        except OperationCancelled:
            print("STOP: workflow cancelled; next step was not run")
        print("6. Failed jobs: RQ registry retains exhausted jobs for admin review")
        print("7. Replay: admin can queue a new job using the protected API")
        print("Note: this demo does not connect to Redis or invoke an LLM")

if __name__ == "__main__":
    main()
