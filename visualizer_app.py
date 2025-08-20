import asyncio
import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- FastAPI App Initialization ---
app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info(f"New client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logging.info(f"Client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        # We don't want to send the message back to the sender (the agent)
        # but for this simple case, we'll broadcast to all.
        # A more robust implementation might distinguish between agent and viewer clients.
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logging.info(f"Received message: {data}")
            # When a message is received, broadcast it to all clients.
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logging.info("Client disconnected due to WebSocketDisconnect.")
    except Exception as e:
        manager.disconnect(websocket)
        logging.error(f"An error occurred in the websocket endpoint: {e}", exc_info=True)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# --- Mount the frontend directory ---
# This will serve the index.html, style.css, and main.js files
app.mount("/static", StaticFiles(directory="brain_map_frontend"), name="static")

@app.get("/")
async def read_root():
    return FileResponse('brain_map_frontend/index.html')

# To run this application:
# uvicorn visualizer_app:app --reload

if __name__ == "__main__":
    import uvicorn
    logging.info("Starting FastAPI server for visualizer...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
