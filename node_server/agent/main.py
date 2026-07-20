import time
import requests
import os
import subprocess
import json

ADMIN_API_URL = os.getenv("ADMIN_API_URL", "http://admin_server:8000")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "default_secret_key")
NODE_IP = os.getenv("NODE_IP", "127.0.0.1")

HEADERS = {"X-Admin-API-Key": ADMIN_API_KEY}

current_users = set()

def get_xray_stats(reset=False):
    try:
        cmd = ["/usr/local/bin/xray", "api", "statsquery", "-server=127.0.0.1:10085"]
        if reset:
            cmd.append("-reset=true")

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("Error getting stats:", result.stderr)
            return []

        stats_data = json.loads(result.stdout)
        traffic_map = {}
        for stat in stats_data.get("stat", []):
            name_parts = stat["name"].split(">>>")
            if len(name_parts) == 4 and name_parts[0] == "user":
                uuid = name_parts[1]
                direction = name_parts[3]
                value = int(stat.get("value", 0))

                if uuid not in traffic_map:
                    traffic_map[uuid] = {"downloaded_bytes": 0, "uploaded_bytes": 0}

                if direction == "downlink":
                    traffic_map[uuid]["downloaded_bytes"] += value
                elif direction == "uplink":
                    traffic_map[uuid]["uploaded_bytes"] += value

        stats_list = [{"uuid": k, "downloaded_bytes": v["downloaded_bytes"], "uploaded_bytes": v["uploaded_bytes"]} for k, v in traffic_map.items()]
        return stats_list

    except Exception as e:
        print(f"Failed to fetch or parse stats: {e}")
        return []

def report_stats(stats):
    if not stats:
        return True
    try:
        payload = {
            "node_ip": NODE_IP,
            "stats": stats
        }
        res = requests.post(f"{ADMIN_API_URL}/api/nodes/stats", json=payload, headers=HEADERS, timeout=10)
        res.raise_for_status()
        return True
    except Exception as e:
        print(f"Failed to report stats: {e}")
        return False

def sync_users():
    global current_users
    try:
        res = requests.get(f"{ADMIN_API_URL}/api/nodes/sync", headers=HEADERS, timeout=10)
        res.raise_for_status()
        active_uuids = set(res.json().get("active_uuids", []))

        if active_uuids == current_users:
            return

        print("Users changed, updating Xray config...")
        current_users = active_uuids

        with open("/app/xray/config.json", "r") as f:
            config = json.load(f)

        for inbound in config["inbounds"]:
            if inbound.get("protocol") == "vless":
                inbound["settings"]["clients"] = [{"id": uuid, "email": uuid, "flow": "xtls-rprx-vision"} for uuid in active_uuids]
                break

        with open("/app/xray/config.json", "w") as f:
            json.dump(config, f, indent=2)

        subprocess.run(["/usr/bin/pkill", "xray"])

    except Exception as e:
        print(f"Failed to sync users: {e}")

def apply_env_configs():
    try:
        with open("/app/xray/config.json", "r") as f:
            config = json.load(f)

        private_key = os.getenv("REALITY_PRIVATE_KEY")
        short_id = os.getenv("REALITY_SHORT_ID")

        if private_key and short_id:
            for inbound in config.get("inbounds", []):
                if inbound.get("protocol") == "vless":
                    if "streamSettings" in inbound and "realitySettings" in inbound["streamSettings"]:
                        inbound["streamSettings"]["realitySettings"]["privateKey"] = private_key
                        inbound["streamSettings"]["realitySettings"]["shortIds"] = [short_id]

        with open("/app/xray/config.json", "w") as f:
            json.dump(config, f, indent=2)

    except Exception as e:
        print(f"Error applying env config: {e}")

def main():
    print("Starting Node Agent...")
    apply_env_configs()
    pending_stats = {}

    while True:
        stats = get_xray_stats(reset=True)

        for stat in stats:
            uuid = stat["uuid"]
            if uuid not in pending_stats:
                pending_stats[uuid] = {"downloaded_bytes": 0, "uploaded_bytes": 0}
            pending_stats[uuid]["downloaded_bytes"] += stat["downloaded_bytes"]
            pending_stats[uuid]["uploaded_bytes"] += stat["uploaded_bytes"]

        if pending_stats:
            stats_to_report = [{"uuid": k, "downloaded_bytes": v["downloaded_bytes"], "uploaded_bytes": v["uploaded_bytes"]} for k, v in pending_stats.items()]
            success = report_stats(stats_to_report)
            if success:
                pending_stats.clear()

        sync_users()
        time.sleep(600) # 10 minutes

if __name__ == "__main__":
    main()
