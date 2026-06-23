import time
import threading

class TokenBucket:
    """
    A thread-safe implementation of the Token Bucket algorithm for rate limiting.
    Allows traffic bursts up to a capacity limit and replenishes tokens linearly over time.
    """
    def __init__(self, max_tokens: int, refill_rate: int, interval: int) -> None:
        """
        Args:
            max_tokens (int): Maximum burst size (max tokens bucket can hold).
            refill_rate (int): Number of tokens to replenish per interval.
            interval (int): Duration of the replenishment interval in seconds.
        """
        assert max_tokens > 0, "max_tokens must be positive"
        assert refill_rate > 0, "refill_rate must be positive"
        assert interval > 0, "interval must be positive"

        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.interval = interval
        self.tokens = max_tokens
        self.refilled_at = time.time()
        self.lock = threading.Lock()  # Synchronizes token updates across concurrent threads

    def _refill(self):
        """
        Replenishes tokens based on the time elapsed since the last replenishment.
        Must be called inside a locked context.
        """
        now = time.time()
        elapsed = now - self.refilled_at
        if elapsed >= self.interval:
            num_refills = int(elapsed // self.interval)
            self.tokens = min(
                self.max_tokens,
                self.tokens + num_refills * self.refill_rate
            )
            self.refilled_at += num_refills * self.interval

    def allow_request(self, tokens: int = 1) -> bool:
        """
        Checks if the bucket has enough tokens to fulfill the request.
        Consumes tokens if available.
        
        Returns:
            bool: True if request is allowed, False otherwise.
        """
        with self.lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
        
    def get_remaining(self) -> int:
        """
        Returns the number of remaining tokens available in the bucket.
        """
        with self.lock:
            self._refill()
            return self.tokens
        
    def get_reset_time(self) -> int:
        """
        Returns the UNIX timestamp of the next replenishment cycle.
        """
        with self.lock:
            self._refill()
            return self.refilled_at + self.interval
        


class RateLimiterStore:
    """
    Manages client IP-to-TokenBucket mapping, ensuring thread-safe access.
    """
    def __init__(self, max_tokens: int, refill_rate: int, interval: int) -> None:
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.interval = interval
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = threading.Lock()

    def get_bucket(self, key: str) -> TokenBucket:
        """
        Retrieves or initializes a TokenBucket for a specific key (client IP).
        
        Args:
            key (str): Typically the client IP address.
            
        Returns:
            TokenBucket: The rate limiting bucket for the client.
        """
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = TokenBucket(
                    max_tokens=self.max_tokens,
                    refill_rate=self.refill_rate,
                    interval=self.interval
                )
            return self._buckets[key]