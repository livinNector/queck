import subprocess
import websockets
import asyncio

PORT = 8080
WS_PORT = 8765


# WebSocket handler for live reloads
clients = set()


async def websocket_handler(websocket, path):
    # Register client
    clients.add(websocket)
    print(f"New WebSocket connection. Total connections: {len(clients)}")
    try:
        async for message in websocket:
            # Handle incoming messages if needed
            pass
    except websockets.ConnectionClosed:
        print("WebSocket connection closed")
    finally:
        # Unregister client
        clients.remove(websocket)


# Function to send a reload signal to all connected clients
async def send_reload_signal():
    if clients:
        print("Sending reload signal to clients...")
        await asyncio.gather(*[client.send("reload") for client in clients])


# Start WebSocket server
async def websocket_server():
    async with websockets.serve(websocket_handler, "localhost", WS_PORT):
        print(f"WebSocket server running on ws://localhost:{WS_PORT}")
        await asyncio.Future()  # Keep server running

# Main function to start both HTTP and WebSocket servers
def start_http_server(directory):
    subprocess.Popen(["python", "-m","http.server","-d", directory, str(PORT)])
