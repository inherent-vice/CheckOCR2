"""Worker thread helpers."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class WorkerHandle:
    thread: threading.Thread

    @property
    def is_alive(self) -> bool:
        return self.thread.is_alive()

    def join(self, timeout: float | None = None) -> None:
        self.thread.join(timeout=timeout)


def start_daemon_worker(
    target: Callable[..., Any],
    *args: Any,
    name: str | None = None,
    **kwargs: Any,
) -> WorkerHandle:
    thread = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True, name=name)
    thread.start()
    return WorkerHandle(thread)
