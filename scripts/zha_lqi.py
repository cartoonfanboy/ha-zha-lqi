#!/usr/bin/env python3
"""Read ZHA device LQI from HA diagnostic sensors (primary) + neighbour table (fallback)."""
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone

DB = "/config/zigbee.db"
RECORDER_DB = "/config/home-assistant_v2.db"
DEVICE_REG = "/config/.storage/core.device_registry"
ENTITY_REG = "/config/.storage/core.entity_registry"


def get_lqi_from_recorder():
    """Return {entity_id: lqi} from latest valid states in the recorder DB."""
    try:
        conn = sqlite3.connect(f"file:{RECORDER_DB}?mode=ro", uri=True)
        # Get the most recent non-unknown state per _lqi entity
        rows = conn.execute("""
            SELECT s.entity_id, st.state
            FROM states st
            JOIN states_meta s ON st.metadata_id = s.metadata_id
            JOIN (
                SELECT metadata_id, MAX(last_updated_ts) AS max_ts
                FROM states
                WHERE state NOT IN ('unknown', 'unavailable')
                GROUP BY metadata_id
            ) latest ON st.metadata_id = latest.metadata_id AND st.last_updated_ts = latest.max_ts
            WHERE s.entity_id LIKE '%_lqi%'
        """).fetchall()
        conn.close()
        result = {}
        for eid, state in rows:
            if re.search(r'_lqi(_\d+)?$', eid):
                try:
                    result[eid] = int(float(state))
                except (ValueError, TypeError):
                    pass
        return result
    except Exception:
        return {}


def main():
    try:
        # Load device registry: device_id -> ieee, name
        with open(DEVICE_REG) as f:
            reg = json.load(f)

        device_id_to_ieee = {}
        name_map = {}  # ieee -> display name
        for d in reg["data"]["devices"]:
            for ident in d.get("identifiers", []):
                if ident[0] == "zha":
                    ieee = ident[1]
                    device_id_to_ieee[d["id"]] = ieee
                    name_map[ieee] = d.get("name_by_user") or d.get("name") or ieee

        # Load entity registry: entity_id -> device_id (for _lqi sensors)
        with open(ENTITY_REG) as f:
            ereg = json.load(f)

        entity_to_device = {}
        for e in ereg["data"]["entities"]:
            eid = e.get("entity_id", "")
            if re.search(r'_lqi(_\d+)?$', eid) and e.get("device_id"):
                entity_to_device[eid] = e["device_id"]

        # Get LQI values from recorder DB (most recent valid state per sensor)
        ha_lqi_states = get_lqi_from_recorder()

        # Map ieee -> lqi from HA diagnostic sensors (accurate, real-time)
        sensor_lqi_map = {}  # ieee -> lqi
        for eid, lqi in ha_lqi_states.items():
            dev_id = entity_to_device.get(eid)
            if dev_id:
                ieee = device_id_to_ieee.get(dev_id)
                if ieee:
                    sensor_lqi_map[ieee] = lqi

        # Neighbour table LQI as fallback
        conn = sqlite3.connect(DB)

        last_seen_map = {}
        for ieee, last_seen in conn.execute("SELECT ieee, last_seen FROM devices_v15"):
            last_seen_map[ieee] = last_seen

        neighbour_lqi_map = {}
        for device_ieee, ieee, lqi in conn.execute(
            "SELECT device_ieee, ieee, lqi FROM neighbors_v15 WHERE lqi IS NOT NULL"
        ):
            current = neighbour_lqi_map.get(ieee)
            if current is None or lqi > current:
                neighbour_lqi_map[ieee] = lqi

        conn.close()

        output = []
        for ieee, last_seen in last_seen_map.items():
            name = name_map.get(ieee, ieee)
            # Prefer HA diagnostic sensor LQI; fall back to neighbour table
            lqi = sensor_lqi_map.get(ieee) or neighbour_lqi_map.get(ieee)
            lqi_source = "sensor" if ieee in sensor_lqi_map else "neighbour"
            if last_seen is not None:
                try:
                    last_seen = datetime.fromtimestamp(float(last_seen), tz=timezone.utc).isoformat()
                except (ValueError, OSError):
                    last_seen = None
            output.append({
                "name": name,
                "lqi": lqi,
                "lqi_source": lqi_source,
                "last_seen": last_seen,
                "ieee": ieee,
            })

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
