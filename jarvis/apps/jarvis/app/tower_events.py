"""Small in-process invalidation bus. Durable commands remain in SQLite."""
import threading


class TowerEvents:
    def __init__(self):
        self.condition = threading.Condition()
        self.sequence = 0
        self.closed = False
        self.slots = threading.BoundedSemaphore(12)

    def notify(self):
        with self.condition:
            self.sequence += 1
            self.condition.notify_all()

    def wait(self, previous):
        with self.condition:
            self.condition.wait_for(lambda: self.closed or self.sequence != previous, timeout=5)
            return self.sequence

    def close(self):
        with self.condition:
            self.closed = True
            self.condition.notify_all()
