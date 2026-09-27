"""A real WebSocket server implementing CollectiveOS's /robot/ws wire
protocol (see CollectiveOS/src/robot_stream.py), for experiments that need
to exercise PAR's *real* CollectiveOSBridge network client (connect, auth,
send, recv, timeout) against controllable network conditions - not just the
in-process fake bridge in fault_bridge.py. Used for E12 (communication
robustness), E24 (multi-robot scale), E25 (auth/request isolation).

Auth here rejects at the HTTP-upgrade stage (via `process_request`) rather
than CollectiveOS's own accept-then-close-4401 style, since both paths land
in the same generic "connection failed" branch of CollectiveOSBridge.run_task
- what matters for these experiments is that PAR's client handles rejection
cleanly, not which of the two rejection styles produced it.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlsplit

from websockets.datastructures import Headers
from websockets.http11 import Response
from websockets.sync.server import serve


@dataclass
class FakeACSServer:
    expected_token: str = "test-token"
    reply_text: str = "the requested information"
    reply_status: str = "done"
    latency: float = 0.0
    drop_connection: bool = False   # close mid-task, before replying
    host: str = "localhost"
    port: int = 0  # 0 = OS picks a free port

    connections_seen: int = field(default_factory=int, init=False)
    concurrent_peak: int = field(default_factory=int, init=False)
    _active: int = field(default_factory=int, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _server: object | None = field(default=None, init=False)
    _thread: threading.Thread | None = field(default=None, init=False)

    def _check_auth(self, connection, request):
        query = parse_qs(urlsplit(request.path).query)
        token = (query.get("token") or [""])[0]
        if token != self.expected_token:
            return Response(403, "Forbidden", Headers(), b"unauthorized")
        return None

    def _handler(self, websocket) -> None:
        with self._lock:
            self.connections_seen += 1
            self._active += 1
            self.concurrent_peak = max(self.concurrent_peak, self._active)
        try:
            websocket.send(json.dumps({"type": "ack", "message": "Robot stream connected."}))
            for raw in websocket:
                try:
                    message = json.loads(raw)
                except (TypeError, ValueError):
                    websocket.send(json.dumps({"type": "error", "message": "Invalid JSON."}))
                    continue
                if message.get("type") != "task":
                    websocket.send(json.dumps({"type": "error", "message": f"unknown type: {message.get('type')!r}"}))
                    continue
                if self.latency:
                    time.sleep(self.latency)
                if self.drop_connection:
                    return  # close without replying - simulates a mid-task disconnect
                websocket.send(json.dumps({
                    "type": "reply",
                    "text": self.reply_text,
                    "status": self.reply_status,
                    "steps": 1,
                    "demo_path": "",
                    "triggered": True,
                }))
        finally:
            with self._lock:
                self._active -= 1

    def start(self) -> str:
        self._server = serve(self._handler, self.host, self.port, process_request=self._check_auth)
        actual_host, actual_port = self._server.socket.getsockname()[:2]
        self.port = actual_port
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return f"ws://{actual_host}:{actual_port}/robot/ws"

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()

    def __enter__(self) -> "FakeACSServer":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()
