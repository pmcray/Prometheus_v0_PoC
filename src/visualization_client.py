import asyncio
import json
import logging
import websockets
from .visualization_data import AssemblyState

class VisualizationClient:
    def __init__(self, server_uri="ws://localhost:8765"):
        self.server_uri = server_uri
        logging.info(f"VisualizationClient configured for {self.server_uri}")

    def send_state(self, state: AssemblyState):
        """
        Connects, sends a single state update, and disconnects.
        This is a synchronous wrapper for the async websocket call.
        """
        try:
            # asyncio.run() creates a new event loop for each call.
            # This is not highly performant, but it is simple and robust
            # for integrating with the existing synchronous agent code.
            asyncio.run(self._send(state))
        except Exception as e:
            # This will catch connection errors if the server isn't running,
            # preventing the agent from crashing.
            logging.warning(f"Failed to send state to visualization server: {e}")

    async def _send(self, state: AssemblyState):
        async with websockets.connect(self.server_uri) as websocket:
            await websocket.send(state.model_dump_json())
            # Short sleep to ensure message is sent before connection is closed.
            await asyncio.sleep(0.1)
