"""
PredictHub — OBS Stream Controller
Usage:
    python tools/obs_controller.py scenes                  (list scenes)
    python tools/obs_controller.py switch "Scene Name"     (switch scene)
    python tools/obs_controller.py text "Source" "Text"    (update text overlay)
    python tools/obs_controller.py markets                 (update market overlay with live data)
    python tools/obs_controller.py start                   (start streaming)
    python tools/obs_controller.py stop                    (stop streaming)
"""

import sys
import os
import json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def get_client():
    import obsws_python as obs
    return obs.ReqClient(
        host=os.getenv('OBS_HOST', 'localhost'),
        port=int(os.getenv('OBS_PORT', 4455)),
        password=os.getenv('OBS_PASSWORD', '')
    )

def list_scenes():
    """List all available scenes"""
    cl = get_client()
    scenes = cl.get_scene_list()
    print("Available scenes:")
    for s in scenes.scenes:
        print(f"  - {s['sceneName']}")
    return scenes

def switch_scene(scene_name):
    """Switch to a specific scene"""
    cl = get_client()
    cl.set_current_program_scene(scene_name)
    print(json.dumps({"status": "switched", "scene": scene_name}))

def update_text(source_name, text):
    """Update a text source in OBS"""
    cl = get_client()
    cl.set_input_settings(
        input_name=source_name,
        input_settings={"text": text}
    )
    print(json.dumps({"status": "text_updated", "source": source_name, "text": text[:50]}))

def update_market_overlay():
    """Update market data overlay with live Polymarket data"""
    markets_file = os.path.join(os.path.dirname(__file__), '..', 'reports', 'daily-markets.json')

    if not os.path.exists(markets_file):
        print("No market data found. Run: python polymarket_api.py export")
        return

    with open(markets_file, 'r') as f:
        markets = json.load(f)

    cl = get_client()

    for i, market in enumerate(markets[:5]):
        q = market.get('question', 'Unknown')[:60]
        yes = float(market.get('yes_price', 0))
        pct = f"{int(yes * 100)}%"

        try:
            cl.set_input_settings(
                input_name=f"market_{i}_name",
                input_settings={"text": q}
            )
            cl.set_input_settings(
                input_name=f"market_{i}_price",
                input_settings={"text": pct}
            )
        except Exception as e:
            print(f"Could not update market_{i}: {e}")

    print(json.dumps({"status": "overlay_updated", "markets_count": min(len(markets), 5)}))

def start_stream():
    cl = get_client()
    cl.start_stream()
    print(json.dumps({"status": "stream_started"}))

def stop_stream():
    cl = get_client()
    cl.stop_stream()
    print(json.dumps({"status": "stream_stopped"}))

def start_recording():
    cl = get_client()
    cl.start_record()
    print(json.dumps({"status": "recording_started"}))

def stop_recording():
    cl = get_client()
    resp = cl.stop_record()
    print(json.dumps({"status": "recording_stopped", "path": str(resp)}))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python obs_controller.py [scenes|switch|text|markets|start|stop]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'scenes':
        list_scenes()
    elif cmd == 'switch':
        switch_scene(sys.argv[2])
    elif cmd == 'text':
        update_text(sys.argv[2], sys.argv[3])
    elif cmd == 'markets':
        update_market_overlay()
    elif cmd == 'start':
        start_stream()
    elif cmd == 'stop':
        stop_stream()
    elif cmd == 'record':
        start_recording()
    elif cmd == 'stoprecord':
        stop_recording()
    else:
        print(f"Unknown command: {cmd}")
