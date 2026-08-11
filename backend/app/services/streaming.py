from typing import List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Keeps track of all active analyst live feed websocket connections
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WebSocket] Connected a new client. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"[WebSocket] Disconnected a client. Active connections: {len(self.active_connections)}")

    async def broadcast(self, data: dict):
        """
        Broadcasts simulated transaction data to all active WebSocket listeners.
        """
        closed_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                print(f"[WebSocket] Error broadcasting to connection: {e}")
                closed_connections.append(connection)
                
        # Clean up any dead connections encountered
        for conn in closed_connections:
            self.disconnect(conn)

manager = ConnectionManager()
