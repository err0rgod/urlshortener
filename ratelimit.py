import time
import threading
from collections import defaultdict


class tokenbucket:
    def __init__(self,max_tokens : int, refill_rate : int, interval : int) -> None:
        assert max_tokens > 0, "max_tokens must be positive"
        assert refill_rate > 0, "refill_rate must be positive"
        assert interval > 0, "interval must be positive"

        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.interval  = interval
        self.tokens = max_tokens
        self.refilled_at = time.time()
        self.lock = threading.Lock()

    def _refill(self):
        now = time.time()
        elapsed = now - self.refilled_at
        if elapsed >= self.interval:
            num_refills = int(elapsed // self.interval)
            self.tokens = min(
                self.max_tokens,
                self.tokens + num_refills * self.refill_rate
            )
            self.refilled_at += num_refills * self.interval

    def alllow_request(self,tokens : int = 1) -> bool:
        with self.lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
        
    def get_remaining(self)-> int:
        with self.lock:
            self._refill()
            return self.tokens
        
    def get_reset_time(self) -> int:
        with self.lock:
            return self.refilled_at + self.interval
        


class rateLimiterStore:
    def __init__(self, max_tokens : int, refill_rate : int , interval : int) -> None:
        self.max_tokens  = max_tokens
        self.refill_rate =  refill_rate
        self.interval  =  interval
        self._buckets = dict[str,tokenbucket] = {}
        self._lock =  threading.lock()

    def get_bucket(self,key : str) -> tokenbucket:
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = tokenbucket(
                    max_tokens=self.max_tokens,
                    refill_rate= self.refill_rate,
                    interval=self.interval
                )
                return self._buckets[key]