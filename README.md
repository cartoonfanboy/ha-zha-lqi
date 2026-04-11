# Zigbee LQI Dashboard — Home Assistant

A Lovelace dashboard showing the signal quality (LQI) and last-seen time for every device on your ZHA Zigbee network. No cloud, no add-on — reads from ZHA's SQLite database and HA's recorder.

---

## Screenshot

*Table showing all Zigbee devices with colour-coded signal bars and last-seen timestamps*

---

## What It Shows

| Column | Description |
|--------|-------------|
| Device | Friendly name from HA device registry |
| Last Seen | How long ago the device was last active (colour-coded) |
| Signal | Visual bar (0–255 LQI scale) |
| LQI | Raw Link Quality Indicator value |

**Colour coding:**

| Colour | LQI | Last Seen |
|--------|-----|-----------|
| Green | ≥ 150 | ≤ 10 min |
| Yellow | ≥ 100 | ≤ 30 min |
| Orange | ≥ 60 | ≤ 2 hours |
| Red | < 60 | > 2 hours |

Summary bar at the top shows device count and how many are strong / fair / weak / stale.

Devices are sorted worst signal first so problem devices are immediately visible.

---

## How It Works

A Python script (`scripts/zha_lqi.py`) reads from three local sources:

1. **HA recorder DB** (`home-assistant_v2.db`) — real-time LQI from ZHA diagnostic sensors (primary source, accurate per-device link quality)
2. **ZHA SQLite DB** (`zigbee.db`) — neighbour table LQI as fallback for devices without a diagnostic sensor, plus `last_seen` timestamps
3. **Device/entity registry** — maps IEEE addresses to friendly names and links LQI sensor entities to devices

A `command_line` sensor runs this script every 5 minutes and stores the result as a JSON attribute. The Lovelace view uses `custom:button-card` with a JavaScript template to render the table in the browser.

### Why two LQI sources?

The neighbour table in `zigbee.db` shows how well *other* routers see a device — not how well the device itself connects. This can differ significantly from the actual link quality. ZHA's built-in LQI diagnostic sensors report the real link quality directly from the device, so these are used when available.

---

## Requirements

### HA Integration
- **ZHA** (Zigbee Home Automation) — built into Home Assistant, must be active

### HACS Frontend
- [button-card](https://github.com/custom-cards/button-card) — provides `custom:button-card`

---

## Setup

### Step 1 — Enable ZHA LQI diagnostic sensors

For the most accurate LQI readings, enable the LQI diagnostic sensor on each of your Zigbee devices:

1. Go to **Settings > Devices & Services > ZHA**
2. Click each device > **Sensors** tab > find the `LQI` sensor > enable it

Or enable them all at once by editing `.storage/core.entity_registry` — set `disabled_by` to `null` for every entity whose `entity_id` matches `_lqi` or `_lqi_N`. Restart HA after.

Devices without an enabled LQI sensor fall back to the neighbour table automatically.

### Step 2 — Copy the script

Copy `scripts/zha_lqi.py` into your HA config scripts folder:

```
/config/scripts/zha_lqi.py
```

### Step 3 — Add the package sensor

Copy `packages/zigbee_status.yaml` into your packages folder, then ensure packages are enabled in `configuration.yaml`:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

> **Note:** If your HA config directory is not `/config` (e.g. the Claude Code add-on uses `/homeassistant`), update the `DB`, `RECORDER_DB`, `DEVICE_REG`, and `ENTITY_REG` paths at the top of `zha_lqi.py`.

### Step 4 — Restart Home Assistant

After restart, check **Developer Tools > States** for `sensor.zigbee_lqi_data` — it should show a timestamp as its state and have a `devices` attribute listing your Zigbee devices.

### Step 5 — Add the Lovelace view

1. Open your dashboard > three-dot menu > **Edit Dashboard** > **Raw configuration editor**
2. Under `views:`, paste the contents of `lovelace/zigbee_view.yaml` as a new list item
3. Save

---

## Troubleshooting

**Sensor shows "No ZHA data yet"**
- Check that `zigbee.db` exists at `/config/zigbee.db`
- Run the script manually to see errors: `python3 /config/scripts/zha_lqi.py`

**All LQI values show "—"**
- No LQI diagnostic sensors are enabled and the neighbour table is empty
- Enable LQI sensors per Step 1, or wait for ZHA to build its neighbour table (happens after devices have been active for a while)

**LQI values look wrong / much lower than expected**
- The device's LQI diagnostic sensor is not enabled — the script is falling back to the neighbour table, which shows a different (often lower) value
- Enable the LQI sensor for that device in ZHA and restart HA

**Device names show IEEE addresses instead of names**
- The device hasn't been named in HA, or the device registry path is wrong in the script

---

## No Support

This dashboard is shared as-is with no support provided.

---

*Built with [Claude Code](https://claude.ai/claude-code)*
