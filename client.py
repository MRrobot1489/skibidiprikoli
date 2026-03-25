import asyncio
import json
import socket
import uuid

import mss
import mss.tools
import websockets
from websockets.asyncio.client import ClientConnection


SERVER_URL = "ws://192.168.1.224:8765"
RECONNECT_DELAY = 3
CLIENT_ID = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"


def take_screenshot_bytes() -> bytes:
    with mss.mss() as sct:
        mon = sct.monitors[1]
        shot = sct.grab(mon)
        return mss.tools.to_png(shot.rgb, shot.size)


async def handle_server_commands(ws: ClientConnection) -> None:
    print(f"[+] Ready. Waiting for commands as client_id={CLIENT_ID}")
    async for message in ws:
        if isinstance(message, bytes):
            print("[!] Received unexpected binary command, ignoring")
            continue

        try:
            command = json.loads(message)
        except json.JSONDecodeError:
            print("[!] Invalid JSON command, ignoring")
            continue

        action = command.get("action")
        if action != "screenshot":
            print(f"[i] Unknown action: {action}")
            continue

        print("[>] Screenshot command received")
        try:
            data = await asyncio.to_thread(take_screenshot_bytes)
            metadata = {
                "type": "screenshot",
                "client_id": CLIENT_ID,
                "size": len(data),
            }
            await ws.send(json.dumps(metadata))
            await ws.send(data)
            print(f"[+] Screenshot sent ({len(data)} bytes)")
        except Exception as exc:
            print(f"[!] Failed to capture/send screenshot: {exc}")


async def run_client() -> None:
    while True:
        try:
            print(f"[i] Connecting to {SERVER_URL} ...")
            async with websockets.connect(SERVER_URL, max_size=None) as ws:
                print("[+] Connected to server")
                await handle_server_commands(ws)
        except (ConnectionRefusedError, websockets.ConnectionClosed, OSError) as exc:
            print(f"[!] Connection lost/failed: {exc}")
        except Exception as exc:
            print(f"[!] Unexpected client error: {exc}")

        print(f"[i] Reconnecting in {RECONNECT_DELAY}s...")
        await asyncio.sleep(RECONNECT_DELAY)


if __name__ == "__main__":
    try:
        asyncio.run(run_client())
    except KeyboardInterrupt:
        print("\n[i] Client stopped by user.")
