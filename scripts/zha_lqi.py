#!/usr/bin/env python3
"""Read ZHA device LQI from local SQLite DB + device registry. No HTTP needed."""
import json
import sqlite3
import sys
from datetime import datetime, timezone

DB = "/config/zigbee.db"
DEVICE_REG = "/config/.storage/core.device_registry"


def main():
    try:
        # Load device registry for friendly names
        with open(DEVICE_REG) as f:
            reg = json.load(f)

        name_map = {}  # ieee -> display name
        for d in reg["data"]["devices"]:
            for ident in d.get("identifiers", []):
                if ident[0] == "zha":
                    ieee = ident[1]
                    name_map[ieee] = d.get("name_by_user") or d.get("name") or ieee

        conn = sqlite3.connect(DB)

        # Get last_seen for all devices
        last_seen_map = {}
        for ieee, last_seen in conn.execute("SELECT ieee, last_seen FROM devices_v15"):
            last_seen_map[ieee] = last_seen

        # Build best LQI per device: take max LQI across all neighbor entries for that device
        lqi_map = {}  # ieee -> best lqi
        for device_ieee, ieee, lqi in conn.execute(
            "SELECT device_ieee, ieee, lqi FROM neighbors_v15 WHERE lqi IS NOT NULL"
        ):
            # lqi here = quality of link FROM device_ieee TO ieee
            current = lqi_map.get(ieee)
            if current is None or lqi > current:
                lqi_map[ieee] = lqi

        conn.close()

        output = []
        for ieee, last_seen in last_seen_map.items():
            name = name_map.get(ieee, ieee)
            lqi = lqi_map.get(ieee)
            # Convert unix timestamp (seconds) to ISO string for JS new Date()
            if last_seen is not None:
                try:
                    last_seen = datetime.fromtimestamp(float(last_seen), tz=timezone.utc).isoformat()
                except (ValueError, OSError):
                    last_seen = None
            output.append({
                "name": name,
                "lqi": lqi,
                "last_seen": last_seen,
                "ieee": ieee,
            })

        # Sort worst LQI first (None = unknown, put at end)
        output.sort(key=lambda x: (x["lqi"] is None, x["lqi"] if x["lqi"] is not None else 0))

        result = {
            "count": len(output),
            "devices": output,
            "updated": datetime.now(timezone.utc).strftime("%H:%M"),
        }
        print(json.dumps(result))

    except Exception as e:
        print(json.dumps({"error": str(e), "count": 0, "devices": []}))
        sys.exit(1)


if __name__ == "__main__":
    main()
