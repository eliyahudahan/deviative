#!/usr/bin/env python3
"""
בדיקת aisstream.io - San Pedro Bay (LA)
"""

import os
import sys
import json
import asyncio
import websockets
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("AISSTREAM_API_KEY")
if not API_KEY:
    print("❌ AISSTREAM_API_KEY not found in .env")
    sys.exit(1)

BOUNDING_BOX = [
    [[33.772292, -118.356139], [33.673490, -118.095731]]
]

async def main():
    print("="*60)
    print("🧪 aisstream.io - San Pedro Bay (LA)")
    print("="*60)
    
    try:
        ws = await websockets.connect("wss://stream.aisstream.io/v0/stream")
        print("🔗 Connected")
        
        await ws.send(json.dumps({
            "APIKey": API_KEY,
            "BoundingBoxes": BOUNDING_BOX,
            "FilterMessageTypes": ["PositionReport"]
        }))
        print("✅ Subscribed to San Pedro Bay")
        print("📡 Waiting for data...\n")
        
        vessels = {}
        for i in range(10):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=3)
                data = json.loads(msg)
                
                if "MetaData" not in data:
                    continue
                
                meta = data["MetaData"]
                pos = data["Message"]["PositionReport"]
                
                mmsi = meta["MMSI"]
                name = meta["ShipName"].strip()
                lat = pos["Latitude"]
                lon = pos["Longitude"]
                sog = pos["Sog"]
                cog = pos["Cog"]
                
                if mmsi not in vessels:
                    vessels[mmsi] = name
                    print(f"   🚢 {name} (MMSI:{mmsi})")
                    print(f"      📍 {lat:.5f}, {lon:.5f} | SOG:{sog}kt | COG:{cog}°")
                
            except asyncio.TimeoutError:
                break
        
        print(f"\n📊 Unique vessels seen: {len(vessels)}")
        if len(vessels) > 0:
            print("✅ aisstream.io WORKS! Live AIS data available.")
        else:
            print("⚠️ No vessels found. Check bounding box.")
            
        await ws.close()
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())