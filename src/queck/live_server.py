import asyncio
import subprocess
import sys

import websockets


class LiveServer:
    """Live server to host a directory with live reloads using websockets."""

    def __init__(self, directory, port=8080, ws_port=8765):
        self.clients = set()
        self.directory = directory
        self.port = port
        self.ws_port = ws_port

    async def websocket_handler(self, websocket):
        # Register client
        self.clients.add(websocket)
        print(f"New WebSocket connection. Total connections: {len(self.clients)}")
        try:
            async for message in websocket:
                print(message)
        except websockets.ConnectionClosed:
            print("WebSocket connection closed")
        finally:
            # Unregister client
            self.clients.remove(websocket)

    # Function to send a reload signal to all connected clients
    async def send_reload_signal(self):
        if self.clients:
            print("Sending reload signal to clients...")
            await asyncio.gather(*[client.send("reload") for client in self.clients])

    # Start WebSocket server
    async def start_websocket_server(self):
        async with websockets.serve(self.websocket_handler, "localhost", self.ws_port):
            print(f"WebSocket server running on ws://localhost:{self.ws_port}")
            await asyncio.Future()  # Keep server running

    # Main function to start both HTTP and WebSocket servers
    def start_http_server(self):
        self.http_server_process = subprocess.Popen(
            [sys.executable, "-m", "http.server", "-d", self.directory, str(self.port)]
        )

    def start(self):
        self.start_http_server()
        self.ws_server_task = asyncio.create_task(self.start_websocket_server())

    def close(self):
        self.http_server_process.terminate()
        self.ws_server_task.cancel()
        self.clients = set()
