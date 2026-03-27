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

    for i, task in enumerate(tasks, 1):
        print(f"[{i}/{len(tasks)}] {task}...", flush=True)
        time.sleep(0.25)
        print(f"  done.", flush=True)

if __name__ == "__main__":
    main()
