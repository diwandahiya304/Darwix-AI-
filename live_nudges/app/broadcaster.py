"""Thread-safe pub/sub used to fan out pipeline events to WebSocket
clients. The pipeline (app/pipeline.py) is deliberately synchronous —
real-time audio pacing is just `time.sleep` between chunks, which is
simpler to share correctly between the CLI (scripts/run_call.py),
tests, and the server than making the whole audio/ASR/signal path
async for no benefit. `app/main.py` runs a call on a background thread
and bridges this queue into the WebSocket's asyncio world with
`asyncio.to_thread(queue.get)`."""

from __future__ import annotations

import queue
import threading


class Broadcaster:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: list[queue.Queue] = []

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue()
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def publish(self, event: dict) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for q in subscribers:
            q.put(event)
