import asyncio
import websockets
import json
import logging

VISUALIZER_URI = "ws://localhost:8000/ws"

async def _send_to_visualizer(data: dict):
    """
    Connects to the visualizer WebSocket server and sends data.
    """
    try:
        async with websockets.connect(VISUALIZER_URI) as websocket:
            await websocket.send(json.dumps(data))
            # Optional: Wait for a response if the server sends one
            # response = await websocket.recv()
            # logging.info(f"Received from visualizer: {response}")
    except (websockets.exceptions.ConnectionClosedError, ConnectionRefusedError) as e:
        # This is not critical, the agent can continue without the visualizer.
        # logging.warning(f"Could not connect to the visualizer at {VISUALIZER_URI}. {e}")
        pass # Suppress logging for now to avoid clutter
    except Exception as e:
        logging.error(f"An unexpected error occurred in the visualizer client: {e}")

def emit_status(agent_id: str, state: str, data: dict = None):
    """
    Emits a status update to the visualizer backend.
    This is a synchronous wrapper around the async send function.

    Args:
        agent_id: The ID of the agent emitting the status (e.g., "Planner", "Coder").
        state: The current state of the agent (e.g., "thinking", "success").
        data: An optional dictionary containing payload data (e.g., code, critique).
    """
    if data is None:
        data = {}

    message = {
        "agent_id": agent_id,
        "state": state,
        "payload": data
    }

    # Run the async send function in a new event loop
    # This is a simple way to call async code from a sync context.
    # --- DISABLED FOR V0.40 VERIFICATION ---
    # try:
    #     asyncio.run(_send_to_visualizer(message))
    # except RuntimeError:
    #     # If an event loop is already running, use create_task
    #     loop = asyncio.get_running_loop()
    #     loop.create_task(_send_to_visualizer(message))
    pass
