import logging
import random
import time

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}',
)
logger = logging.getLogger(__name__)


def main():
    logger.info("Worker started")
    while True:
        delay = random.uniform(5, 30)
        time.sleep(delay)
        task = random.choice(["reticulating splines", "compacting data", "syncing widgets", "crunching numbers", "polishing pixels"])
        duration = round(random.uniform(0.1, 2.0), 2)
        logger.info(f"Working on: {task}")
        time.sleep(duration)
        logger.info(f"Finished: {task} ({duration}s)")


if __name__ == "__main__":
    main()
