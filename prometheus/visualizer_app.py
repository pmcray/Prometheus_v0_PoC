import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info(f"New connection. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logging.info(f"Client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # The server's primary job is to broadcast messages from the agent
            # to the frontend. It can also receive messages from the frontend if needed.
            data = await websocket.receive_text()
            logging.info(f"Received message from a client: {data}")
            # For now, we'll just echo it back to all clients
            await manager.broadcast(f"Echo: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logging.error(f"An error occurred in the websocket endpoint: {e}")
        manager.disconnect(websocket)

@app.get("/")
async def read_root():
    return {"message": "Prometheus Visualizer Backend is running. Connect to the /ws endpoint."}

if __name__ == "__main__":
    import uvicorn
    logging.info("Starting Prometheus Visualizer Backend...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
