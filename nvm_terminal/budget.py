"""Budget tracker — extracted from buyer.py."""
import threading
from datetime import datetime, timezone


class Budget:
    def __init__(self, max_daily: int = 0, max_per_request: int = 0):
        self._lock = threading.Lock()
        self._max_daily = max_daily
        self._max_per_request = max_per_request
        self._daily_spend = 0
        self._total_spend = 0
        self._purchase_count = 0
        self._current_day = datetime.now(timezone.utc).date()
        self._purchases: list[dict] = []

    def _reset_if_new_day(self):
        today = datetime.now(timezone.utc).date()
        if today != self._current_day:
            self._daily_spend = 0
            self._current_day = today

    def can_spend(self, credits: int) -> tuple[bool, str]:
        with self._lock:
            self._reset_if_new_day()
            if self._max_per_request > 0 and credits > self._max_per_request:
                return False, f"Costs {credits} but per-request limit is {self._max_per_request}"
            if self._max_daily > 0 and (self._daily_spend + credits) > self._max_daily:
                remaining = self._max_daily - self._daily_spend
                return False, f"Costs {credits} but only {remaining} left in daily budget"
            return True, "OK"

    def record(self, credits: int, seller: str, query: str):
        with self._lock:
            self._reset_if_new_day()
            self._daily_spend += credits
            self._total_spend += credits
            self._purchase_count += 1
            self._purchases.append({
                "credits": credits, "seller": seller,
                "query": query[:80], "time": datetime.now(timezone.utc).isoformat(),
            })

    def status(self) -> dict:
        with self._lock:
            self._reset_if_new_day()
            u = "unlimited"
            return {
                "daily_limit": self._max_daily or u,
                "daily_spent": self._daily_spend,
                "daily_remaining": (self._max_daily - self._daily_spend) if self._max_daily else u,
                "per_request_limit": self._max_per_request or u,
                "total_spent": self._total_spend,
                "purchases": self._purchase_count,
                "recent": self._purchases[-5:],
            }

    def to_dict(self) -> dict:
        return self.status()
