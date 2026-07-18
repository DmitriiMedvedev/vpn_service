import time
import requests
import grpc
import os
import subprocess
import json

# Xray gRPC API stubs (need to be generated or implemented manually, using subprocess for stats is a fallback)
# For simplicity in this example, we'll use xray api via CLI because generating gRPC stubs in pure python
# requires proto files which adds complexity to the docker image.

ADMIN_API_URL = os.getenv("ADMIN_API_URL", "http://admin_server:8000")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "default_secret_key")
NODE_IP = os.getenv("NODE_IP", "127.0.0.1")

HEADERS = {"X-Admin-API-Key": ADMIN_API_KEY}

def get_xray_stats():
    try:
        # Run xray api command to get stats
        result = subprocess.run(["xray", "api", "statsquery", "-server=127.0.0.1:10085"], capture_output=True, text=True)
        if result.returncode != 0:
            print("Error getting stats:", result.stderr)
            return []

        stats_data = json.loads(result.stdout)

        # Parse output and aggregate by UUID
        # Format: "name": "user>>>UUID>>>traffic>>>downlink", "value": 12345
        traffic_map = {}
        for stat in stats_data.get("stat", []):
            name_parts = stat["name"].split(">>>")
            if len(name_parts) == 4 and name_parts[0] == "user":
                uuid = name_parts[1]
                direction = name_parts[3] # uplink or downlink
                value = int(stat.get("value", 0))

                if uuid not in traffic_map:
                    traffic_map[uuid] = {"downloaded_bytes": 0, "uploaded_bytes": 0}

                if direction == "downlink":
                    traffic_map[uuid]["downloaded_bytes"] += value
                elif direction == "uplink":
                    traffic_map[uuid]["uploaded_bytes"] += value

        # Reset stats in xray so we don't double count
        subprocess.run(["xray", "api", "statsquery", "-server=127.0.0.1:10085", "-reset=true"], capture_output=True)

        stats_list = [{"uuid": k, "downloaded_bytes": v["downloaded_bytes"], "uploaded_bytes": v["uploaded_bytes"]} for k, v in traffic_map.items()]
        return stats_list

    except Exception as e:
        print(f"Failed to fetch or parse stats: {e}")
        return []

def report_stats(stats):
    if not stats:
        return
    try:
        payload = {
            "node_ip": NODE_IP,
            "stats": stats
        }
        res = requests.post(f"{ADMIN_API_URL}/api/nodes/stats", json=payload, headers=HEADERS)
        res.raise_for_status()
    except Exception as e:
        print(f"Failed to report stats: {e}")

def sync_users():
    try:
        res = requests.get(f"{ADMIN_API_URL}/api/nodes/sync", headers=HEADERS)
        res.raise_for_status()
        active_uuids = res.json().get("active_uuids", [])

        # We need to update Xray config with these active users.
        # Xray API allows dynamic user addition/removal, or we rewrite config and restart.
        # Rewriting config is easier for this scale.

        with open("/app/xray/config.json", "r") as f:
            config = json.load(f)

        # Find vless inbound
        for inbound in config["inbounds"]:
            if inbound.get("protocol") == "vless":
                # Rebuild clients list
                inbound["settings"]["clients"] = [{"id": uuid, "flow": "xtls-rprx-vision"} for uuid in active_uuids]
                break

        with open("/app/xray/config.json", "w") as f:
            json.dump(config, f, indent=2)

        # Restart Xray process (assuming managed by systemd, supervisor, or simply kill and start in our bash script)
        # In our docker setup, we can kill the xray process and let the start.sh loop restart it,
        # or handle it gracefully here.
        subprocess.run(["pkill", "xray"]) # SIGHUP might reload config depending on version, otherwise pkill xray.

    except Exception as e:
        print(f"Failed to sync users: {e}")

def main():
    print("Starting Node Agent...")
    while True:
        stats = get_xray_stats()
        report_stats(stats)
        sync_users()
        time.sleep(600) # 10 minutes

if __name__ == "__main__":
    main()
