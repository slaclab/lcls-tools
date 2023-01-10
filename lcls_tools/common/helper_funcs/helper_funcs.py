from datetime import datetime


def sleep(seconds_to_wait: float):
    start = datetime.now()
    while (datetime.now() - start).total_seconds() < seconds_to_wait:
        pass
