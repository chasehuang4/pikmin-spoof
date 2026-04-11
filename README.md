# Pikmin Spoof — GPS Location Spoofer for iPhone

Spoof your iPhone's GPS location from a Mac. No Xcode required.

---

## How It Works

This project uses **pymobiledevice3** to communicate with the iPhone over a USB tunnel and override its GPS location in real time.

There are two components:

1. **`gps_spoof.py`** — A Python HTTP server (port 8765) that maintains a persistent connection to the iPhone via pymobiledevice3's DVT location simulation API. It also serves a full web UI so you can control location from any browser.

2. **`GPSSpoofMac/`** — Swift source files for a macOS app (not compiled/used). All functionality is available through the web UI.

> **Design decision: No Xcode.** This project deliberately avoids a compiled macOS app. Everything is driven by the Python server and its built-in web UI, accessible at `http://localhost:8765`. This keeps setup simple and the code easy to modify.

---

## Requirements

- macOS
- Python 3.10+
- iPhone connected via USB
- [pymobiledevice3](https://github.com/doronz88/pymobiledevice3)

Install pymobiledevice3:

```bash
pip3 install pymobiledevice3
```

---

## Setup & Usage

### Step 1 — Start the tunnel (Terminal 1)

Run this once and keep the terminal open:

```bash
sudo python3 -m pymobiledevice3 remote start-tunnel
```

After a moment it will print an RSD address and port, for example:

```
Interface: ...
RSD Address: fd1a:48e:cc16::1
RSD Port: 58981
```

Keep this terminal open the entire session.

### Step 2 — Start the GPS server (Terminal 2)

Use the RSD address and port printed in Terminal 1:

```bash
python3 /path/to/gps_spoof.py --rsd <RSD_ADDRESS> <RSD_PORT>
```

Example:

```bash
python3 gps_spoof.py --rsd fd1a:48e:cc16::1 58981
```

> The RSD address and port change every session — always read the fresh values from Terminal 1.

### Step 3 — Open the Web UI

Open your browser and go to:

```
http://localhost:8765
```

---

## Web UI Features

### Jump to Coordinate
Enter a latitude and longitude manually and click **Jump** to teleport instantly.

### Click on Map
Click anywhere on the map to walk to that location. The GPS smoothly moves toward the clicked point at the configured speed.

### Joystick
Drag the joystick to move in any direction continuously. Release to stop. Speed is determined by the speed slider.

### Speed Slider
Adjust movement speed in km/h. Presets for reference:
- Walking ≈ 5 km/h
- Running ≈ 12 km/h
- Cycling ≈ 25 km/h
- Fast test ≈ 80+ km/h

### Stop Spoofing
Click **Stop Spoofing** to stop sending fake coordinates. To fully restore real GPS, disconnect the USB cable.

---

## Troubleshooting

**"Address already in use" on port 8765**
A previous instance of `gps_spoof.py` is still running. Kill it:
```bash
lsof -ti:8765 | xargs kill -9
```

**Status shows "⚠️ Connection error"**
- Make sure Terminal 1 (the tunnel) is still running
- Try unplugging and replugging the USB cable
- Re-run both terminals with fresh RSD values

**Joystick or map click does nothing**
- Make sure the Python server is running (Terminal 2)
- Check the status indicator in the top-left of the web UI — it should be green
- Reload the page at `http://localhost:8765`

---

## Project Structure

```
gps_spoof.py          Python server + web UI (the main program)
GPSSpoofMac/          Swift source files (not compiled, kept for reference)
  ContentView.swift
  LocationSpoofer.swift
  JoystickView.swift
  GPSSpoofApp.swift
```
