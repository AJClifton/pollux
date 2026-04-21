import threading

from app.core.metrics import coalescer_in_flight, coalescer_waits_total


class RequestCoalescer:
    """Deduplicates concurrent identical calls. If a call for a given key is already
    in-flight, subsequent callers wait for and share the same result."""

    def __init__(self, name):
        self._name = name
        self._lock = threading.Lock()
        self._in_flight = {}

    def execute(self, key, func, *args, **kwargs):
        """Execute func(*args, **kwargs) with deduplication based on key.

        If another thread is already executing a call with the same key,
        this thread waits and returns the shared result.
        """
        with self._lock:
            if key in self._in_flight:
                event, slot = self._in_flight[key]
                is_leader = False
            else:
                event = threading.Event()
                slot = {"result": None, "error": None}
                self._in_flight[key] = (event, slot)
                is_leader = True

        if not is_leader:
            coalescer_waits_total.labels(coalescer=self._name).inc()
            event.wait()
            if slot["error"] is not None:
                raise slot["error"]
            return slot["result"]

        coalescer_in_flight.labels(coalescer=self._name).inc()
        try:
            result = func(*args, **kwargs)
            with self._lock:
                _, slot = self._in_flight[key]
                slot["result"] = result
            return result
        except Exception as e:
            with self._lock:
                _, slot = self._in_flight[key]
                slot["error"] = e
            raise
        finally:
            with self._lock:
                event_to_set, _ = self._in_flight.pop(key)
            event_to_set.set()
            coalescer_in_flight.labels(coalescer=self._name).dec()


forecast_coalescer = RequestCoalescer("forecast")
geocode_coalescer = RequestCoalescer("geocode")
