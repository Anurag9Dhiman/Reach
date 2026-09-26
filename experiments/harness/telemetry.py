"""Collects TelemetryEvents in memory instead of just logging them, so
experiment scripts can compute metrics (success rate, latency, safety
outcome distribution) directly from a completed Runtime.run_task() call
without parsing log lines."""
from __future__ import annotations

from par.telemetry.events import TelemetryEvent
from par.telemetry.logger import TelemetryLogger


class CollectingTelemetryLogger(TelemetryLogger):
    def __init__(self, verbose: bool = False) -> None:
        super().__init__()
        self.verbose = verbose
        self.events: list[TelemetryEvent] = []

    def log(self, event: TelemetryEvent) -> None:
        self.events.append(event)
        if self.verbose:
            super().log(event)

    def reset(self) -> None:
        self.events = []
