from collections import OrderedDict
from typing import DefaultDict, Dict, Generic, Iterator, Tuple, TypeVar

K = TypeVar("K")
V = TypeVar("V")

__all__ = ["LFUCache"]


class LFUCache(Generic[K, V]):
    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("Capacity must be positive")

        self.capacity = capacity
        self.cache: Dict[K, Tuple[V, int]] = {}  # To store key-value pairs
        self.freq_count: DefaultDict[int, OrderedDict[K, V]] = DefaultDict(
            OrderedDict
        )  # To store frequency of each key
        self.min_freq = 0  # To keep track of the minimum frequency

    def get(self, key: K) -> V:
        if key in self.cache:
            value, freq = self.cache[key]
            # Update frequency and move the key to the next frequency bucket
            self.freq_count[freq].pop(key)
            if not self.freq_count[freq]:  # If the current frequency has no keys, update min_freq
                del self.freq_count[freq]
                if freq == self.min_freq:
                    self.min_freq += 1
            freq += 1
            self.freq_count[freq][key] = value
            self.cache[key] = (value, freq)
            return value
        raise KeyError(f"Key {key} not found")

    def put(self, key: K, value: V) -> None:
        if key in self.cache:
            _, freq = self.cache[key]
            # Update frequency and move the key to the next frequency bucket
            self.freq_count[freq].pop(key)
            if not self.freq_count[freq]:
                del self.freq_count[freq]
                if freq == self.min_freq:
                    self.min_freq += 1
            freq += 1
            self.freq_count[freq][key] = value
            self.cache[key] = (value, freq)
        else:
            # Check if cache is full, evict the least frequently used item
            if len(self.cache) == self.capacity:
                evicted_key, _ = self.freq_count[self.min_freq].popitem(last=False)
                del self.cache[evicted_key]

            # Add the new key-value pair with frequency 1
            self.cache[key] = (value, 1)
            self.freq_count[1][key] = value
            self.min_freq = 1

    def remove_key(self, key: K) -> None:
        if key in self.cache:
            _, freq = self.cache[key]
            self.freq_count[freq].pop(key)
            if not self.freq_count[freq]:  # If the current frequency has no keys, update min_freq
                del self.freq_count[freq]
                if freq == self.min_freq:
                    self.min_freq += 1
            del self.cache[key]

    def __iter__(self) -> Iterator[K]:
        yield from self.cache
