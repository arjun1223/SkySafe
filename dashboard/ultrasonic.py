"""Same median + exponential filter as the optional firmware distance channel."""
import math
from collections import deque
from .config import DISTANCE_FILTER_ALPHA, DISTANCE_MEDIAN_SAMPLES, DISTANCE_MIN_MM, DISTANCE_MAX_MM


class DistanceFilter:
    def __init__(self):
        self.values = deque(maxlen=DISTANCE_MEDIAN_SAMPLES)
        self.value = None

    def add(self, distance):
        if not isinstance(distance, (int,float)) or not math.isfinite(distance) or not DISTANCE_MIN_MM <= distance <= DISTANCE_MAX_MM:
            return False
        self.values.append(distance)
        mid = sorted(self.values)[len(self.values)//2]  # firmware uses upper median while warming
        self.value = mid if self.value is None else self.value+DISTANCE_FILTER_ALPHA*(mid-self.value)
        return True

    @property
    def ready(self):
        return len(self.values) == DISTANCE_MEDIAN_SAMPLES
