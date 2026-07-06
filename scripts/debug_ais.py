#!/usr/bin/env python3
import os
import sys
import json
import asyncio
import websockets
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("AISSTREAM_API_KEY")

BOUNDING_BOX = [[[33.772292, -118.356139], [33.673490, -118.095731]]]

async def main():
    print("📡 Connecting...")
    ws = await websockets.connect("wss://stream.aisstream.io/v0/stream")
    
    await ws.send(json.dumps({
        "APIKey": API_KEY,
        "BoundingBoxes": BOUNDING_BOX,
        "FilterMessageTypes": ["PositionReport"]
    }))
    print("✅ Subscribed. Receiving...")
    
    for _ in range(3):
        msg = await asyncio.wait_for(ws.recv(), timeout=5)
        data = json.loads(msg)
        print("\n📦 RAW MESSAGE:")
        print(json.dumps(data, indent=2)[:1000])

if __name__ == "__main__":
    asyncio.run(main())