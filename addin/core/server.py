"""Zero-dependency HTTP JSON-RPC 2.0 Server for CADPilot Bridge.

Runs inside Fusion 360 bundled Python standard library on a background daemon thread.
Synchronizes with the Fusion main UI thread via thread-safe Events and CustomEvent triggers.
"""

import http.server
import json
import logging
import threading
import uuid
from typing import Dict, Any, Optional, Callable
from .errors import PARSE_ERROR, OPERATION_TIMEOUT

logger = logging.getLogger("CADPilotBridge.Server")


class BridgeRequestHandler(http.server.BaseHTTPRequestHandler):
    """Handles incoming HTTP POST JSON-RPC 2.0 requests."""

    def log_message(self, format: str, *args: Any):
        # Suppress default stdlib stderr logging in favor of palette / custom logger
        pass

    def do_OPTIONS(self):
        """Handle CORS pre-flight if invoked from web UIs (e.g. Streamlit / browser)."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        """Processes JSON-RPC POST requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception as e:
            self._send_json({
                "jsonrpc": "2.0",
                "error": {
                    "code": PARSE_ERROR,
                    "message": f"Parse error: Invalid JSON received ({str(e)})."
                },
                "id": None
            }, status_code=400)
            return

        server: "CADPilotServer" = self.server  # type: ignore

        # Delegate execution to the main thread via the server's bridge delegate
        response = server.execute_request(payload)
        self._send_json(response, status_code=200)

    def _send_json(self, data: Dict[str, Any], status_code: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


class CADPilotServer(http.server.ThreadingHTTPServer):
    """Custom HTTPServer maintaining request synchronization across threads."""

    def __init__(
        self,
        server_address: tuple,
        request_delegate: Optional[Callable[[Dict[str, Any]], None]] = None,
        timeout_seconds: float = 30.0
    ):
        super().__init__(server_address, BridgeRequestHandler)
        self.request_delegate = request_delegate
        self.timeout_seconds = timeout_seconds
        self.pending_requests: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def execute_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Submits request to main thread and waits for completion."""
        req_id = payload.get("id")
        correlation_id = str(uuid.uuid4())

        completion_event = threading.Event()

        with self._lock:
            self.pending_requests[correlation_id] = {
                "event": completion_event,
                "payload": payload,
                "response": None
            }

        # Fire delegate (which calls app.fireCustomEvent in Fusion, or direct in test)
        if self.request_delegate:
            try:
                self.request_delegate(correlation_id)
            except Exception as exc:
                with self._lock:
                    self.pending_requests.pop(correlation_id, None)
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Failed to signal Fusion main thread: {str(exc)}"
                    },
                    "id": req_id
                }
        else:
            # Standalone fallback if no delegate hooked
            with self._lock:
                self.pending_requests.pop(correlation_id, None)
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "No main thread delegate registered."
                },
                "id": req_id
            }

        # Wait for the main thread to complete the CAD operation
        finished = completion_event.wait(timeout=self.timeout_seconds)

        with self._lock:
            pending = self.pending_requests.pop(correlation_id, None)

        if not finished or not pending or pending.get("response") is None:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": OPERATION_TIMEOUT,
                    "message": f"Operation timed out after {self.timeout_seconds}s waiting for Fusion main thread.",
                    "data": {
                        "hint": "The Fusion 360 main UI thread may be busy or displaying a modal dialog. Retry the call."
                    }
                },
                "id": req_id
            }

        return pending["response"]

    def complete_request(self, correlation_id: str, response: Dict[str, Any]):
        """Called by the main-thread event handler to fulfill a waiting request."""
        with self._lock:
            pending = self.pending_requests.get(correlation_id)
            if pending:
                pending["response"] = response
                pending["event"].set()


class BridgeServerManager:
    """Manages the background daemon thread running the HTTP server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9090, timeout_seconds: float = 30.0):
        self.host = host
        self.port = port
        self.timeout_seconds = timeout_seconds
        self.server: Optional[CADPilotServer] = None
        self.server_thread: Optional[threading.Thread] = None

    def start(self, request_delegate: Callable[[str], None]):
        """Starts HTTP server listening on daemon thread."""
        self.server = CADPilotServer(
            (self.host, self.port),
            request_delegate=request_delegate,
            timeout_seconds=self.timeout_seconds
        )
        self.server_thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True,
            name="CADPilotBridge-HTTP-Daemon"
        )
        self.server_thread.start()

    def stop(self):
        """Stops the HTTP server cleanly."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=2.0)
            self.server_thread = None

