"""CADPilot Bridge - Autodesk Fusion 360 Add-In Entrypoint.

This Add-In hosts a lightweight JSON-RPC 2.0 server on a background thread,
and executes modeling tools safely on Fusion's main thread via CustomEvent callbacks.
"""

import sys
import os
import traceback

# Ensure addin root is in sys.path
current_dir = os.path.dirname(os.path.realpath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from core.server import BridgeServerManager
from core.dispatcher import ToolDispatcher

try:
    import adsk.core
    import adsk.fusion
    IN_FUSION = True
except ImportError:
    IN_FUSION = False

# Global state handles for Add-In lifecycle
CUSTOM_EVENT_ID = "CADPilotBridge_MainThreadEvent"
server_manager = None
tool_dispatcher = None
custom_event = None
event_handler = None
handlers = []


def log_to_palette(message: str):
    """Outputs text to Fusion's Text Commands palette."""
    if not IN_FUSION:
        print(f"[CADPilotBridge] {message}")
        return

    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        text_palette = ui.palettes.itemById("TextCommands")
        if text_palette:
            text_palette.writeText(f"[CADPilotBridge] {message}")
    except Exception:
        print(f"[CADPilotBridge] {message}")


if IN_FUSION:
    class BridgeCustomEventHandler(adsk.core.CustomEventHandler):
        """Processes CAD operations on Fusion 360's main UI thread."""

        def __init__(self, srv_mgr: BridgeServerManager, disp: ToolDispatcher):
            super().__init__()
            self.srv_mgr = srv_mgr
            self.disp = disp

        def notify(self, args: adsk.core.CustomEventArgs):
            try:
                correlation_id = args.additionalInfo
                server = self.srv_mgr.server
                if not server:
                    return

                # Retrieve request payload
                with server._lock:
                    pending = server.pending_requests.get(correlation_id)

                if not pending:
                    return

                payload = pending.get("payload", {})
                method = payload.get("method", "unknown")
                log_to_palette(f"Main thread executing tool: '{method}'")

                # Dispatch on MAIN THREAD
                response = self.disp.dispatch(payload)

                # Send back to waiting HTTP thread
                server.complete_request(correlation_id, response)

            except Exception as e:
                log_to_palette(f"Error in main thread event handler: {traceback.format_exc()}")


def run(context):
    """Called by Fusion 360 when the Add-In is loaded/started."""
    global server_manager, tool_dispatcher, custom_event, event_handler

    try:
        log_to_palette("Starting CADPilot Bridge Add-In...")

        tool_dispatcher = ToolDispatcher()
        server_manager = BridgeServerManager(host="127.0.0.1", port=9090, timeout_seconds=30.0)

        if IN_FUSION:
            app = adsk.core.Application.get()

            # Register custom event for main-thread synchronization
            custom_event = app.registerCustomEvent(CUSTOM_EVENT_ID)
            event_handler = BridgeCustomEventHandler(server_manager, tool_dispatcher)
            custom_event.add(event_handler)
            handlers.append(event_handler)

            # Delegate to trigger the custom event
            def trigger_main_thread(correlation_id: str):
                app.fireCustomEvent(CUSTOM_EVENT_ID, correlation_id)

            server_manager.start(request_delegate=trigger_main_thread)
        else:
            # Standalone mode (for mock / dry-run outside Fusion)
            def direct_dispatch(correlation_id: str):
                server = server_manager.server
                with server._lock:
                    pending = server.pending_requests.get(correlation_id)
                if pending:
                    resp = tool_dispatcher.dispatch(pending["payload"])
                    server.complete_request(correlation_id, resp)

            server_manager.start(request_delegate=direct_dispatch)

        log_to_palette(f"JSON-RPC server listening on http://{server_manager.host}:{server_manager.port}")

    except Exception:
        log_to_palette(f"Failed to start CADPilot Bridge:\n{traceback.format_exc()}")


def stop(context):
    """Called by Fusion 360 when the Add-In is stopped/unloaded."""
    global server_manager, custom_event, event_handler

    try:
        log_to_palette("Stopping CADPilot Bridge Add-In...")

        if server_manager:
            server_manager.stop()
            server_manager = None

        if IN_FUSION and custom_event:
            app = adsk.core.Application.get()
            if event_handler:
                custom_event.remove(event_handler)
                event_handler = None
            app.unregisterCustomEvent(CUSTOM_EVENT_ID)
            custom_event = None

        log_to_palette("CADPilot Bridge stopped cleanly.")

    except Exception:
        log_to_palette(f"Error stopping CADPilot Bridge:\n{traceback.format_exc()}")


if __name__ == "__main__":
    # Allows running standalone for testing
    import time
    print("Running CADPilotBridge in standalone test mode...")
    run(None)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop(None)

