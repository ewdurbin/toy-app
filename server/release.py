import os
import random
import sys
import time

TASKS = [
    "Checking database connectivity",
    "Running schema migrations",
    "Validating configuration",
    "Warming up caches",
    "Verifying environment variables",
    "Compiling static assets",
    "Running sanity checks",
    "Synchronizing state",
    "Flushing stale sessions",
    "Finalizing deployment",
]

def main():
    duration = random.uniform(1, 3)
    random.shuffle(TASKS)
    tasks = TASKS[: random.randint(4, len(TASKS))]
    interval = duration / len(tasks)

    print(f"Starting release phase ({len(tasks)} steps)...")
    for i, task in enumerate(tasks, 1):
        print(f"[{i}/{len(tasks)}] {task}...", flush=True)
        time.sleep(interval * random.uniform(0.6, 1.4))
        print(f"  done.", flush=True)

    print("\n--- Environment Variables ---")
    for key in sorted(os.environ):
        print(f"  {key}={os.environ[key]}")
    print("---\n")

    print("Release phase complete.")

if __name__ == "__main__":
    main()
