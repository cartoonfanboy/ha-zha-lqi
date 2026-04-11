# Zigbee LQI Dashboard — Home Assistant

A clean, full-page Lovelace dashboard showing the signal quality (LQI) and last-seen time for every device on your ZHA Zigbee network. No cloud, no add-on — reads directly from the ZHA SQLite database.

---

## Screenshot

*Full-page table showing all Zigbee devices with colour-coded signal bars and last-seen timestamps*

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

A Python script (`scripts/zha_lqi.py`) reads directly from two local files — no HTTP calls needed:

- `zigbee.db` — ZHA's SQLite database (LQI from the `neighbors_v15` table, last_seen from `devices_v15`)
- `.storage/core.device_registry` — maps IEEE addresses to friendly names

A `command_line` sensor runs this script every 5 minutes and stores the result as a JSON attribute. The Lovelace view uses `custom:button-card` with a JavaScript template to render the table entirely in the browser.

---

## Requirements

### HA Integration
- **ZHA** (Zigbee Home Automation) — built into Home Assistant, must be active

### HACS Frontend
- [button-card](https://github.com/custom-cards/button-card) — provides `custom:button-card`

---

## Setup

### Step 1 — Copy the script

Copy `scripts/zha_lqi.py` into your HA config scripts folder:

```
/config/scripts/zha_lqi.py
```

Make sure it's readable by HA.

### Step 2 — Add the package sensor

Copy `packages/zigbee_status.yaml` into your packages folder, then ensure packages are enabled in `configuration.yaml`:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

If your HA config directory is not `/config` (e.g. you're using the Claude Code add-on where it's `/homeassistant`), update the `command` path in the package file accordingly.

### Step 3 — Restart Home Assistant

This loads the `command_line` sensor. After restart, check **Developer Tools > States** for `sensor.zigbee_lqi_data` — it should show a timestamp as its state and have a `devices` attribute with your Zigbee devices.

### Step 4 — Add the Lovelace view

1. Open your dashboard > three-dot menu > **Edit Dashboard** > **Raw configuration editor**
2. Under `views:`, paste the contents of `lovelace/zigbee_view.yaml` as a new list item
3. Save

---

## Troubleshooting

**Sensor shows "No ZHA data yet"**
- Check that `zigbee.db` exists at `/config/zigbee.db` (or adjust the `DB` path at the top of `zha_lqi.py`)
- Run the script manually to see any errors: `python3 /config/scripts/zha_lqi.py`

**All LQI values show "—"**
- ZHA may not have built its neighbor table yet — this populates after devices have been active for a while
- Routers (mains-powered devices) contribute to the neighbor table; battery devices often don't

**Device names show IEEE addresses instead of names**
- The device hasn't been named in HA, or the device registry path is wrong in the script

---

## No Support

This dashboard is shared as-is with no support provided.

---

*Built with [Claude Code](https://claude.ai/claude-code)*
