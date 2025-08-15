import asyncio
import json
import logging
import websockets
from typing import Set

class VisualizationServer:
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.connected_clients: Set[websockets.WebSocketServerProtocol] = set()
        self.brain_map_state = {}
        logging.info(f"VisualizationServer initialized to run on {self.host}:{self.port}")

    async def _register(self, websocket: websockets.WebSocketServerProtocol):
        """Registers a new client."""
        self.connected_clients.add(websocket)
        logging.info(f"New client connected: {websocket.remote_address}. Total clients: {len(self.connected_clients)}")
        # Send the current state to the new client
        await websocket.send(json.dumps(self.brain_map_state))

    async def _unregister(self, websocket: websockets.WebSocketServerProtocol):
        """Unregisters a client."""
        self.connected_clients.remove(websocket)
        logging.info(f"Client disconnected: {websocket.remote_address}. Total clients: {len(self.connected_clients)}")

    async def _broadcast_state(self):
        """Broadcasts the current brain map state to all connected clients."""
        if self.connected_clients:
            state_json = json.dumps(self.brain_map_state)
            tasks = [asyncio.create_task(client.send(state_json)) for client in self.connected_clients]
            await asyncio.wait(tasks)

    async def _handler(self, websocket: websockets.WebSocketServerProtocol):
        """Handles incoming WebSocket connections and messages."""
        await self._register(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    # Assuming the message is an AssemblyState object
                    component_id = data.get("component_id")
                    if component_id:
                        self.brain_map_state[component_id] = data
                        await self._broadcast_state()
                    else:
                        logging.warning(f"Received message without component_id: {data}")
                except json.JSONDecodeError:
                    logging.error(f"Could not decode JSON from message: {message}")
        finally:
            await self._unregister(websocket)

    async def start(self):
        """Starts the WebSocket server."""
        logging.info("Starting visualization server...")
        server = await websockets.serve(self._handler, self.host, self.port)
        await server.wait_closed()

    def run_in_background(self):
        """Runs the server in a background thread."""
        import threading

        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.start())

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
        logging.info("Visualization server started in background thread.")
