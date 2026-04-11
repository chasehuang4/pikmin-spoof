#!/usr/bin/env python3
"""
GPS Spoof — persistent connection version.
Uses pymobiledevice3 Python API directly for fast joystick updates.

Terminal 1: sudo python3 -m pymobiledevice3 remote start-tunnel
Terminal 2: python3 gps_spoof.py --rsd <HOST> <PORT>
Then open:  http://localhost:8765
"""

import argparse
import asyncio
import json
import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler


# ── Persistent Location Controller ────────────────────────────────────────────

class LocationController:
    """
    Maintains a single persistent connection to the device.
    set_location() is non-blocking and always uses the latest coordinate.
    """

    def __init__(self, rsd_host: str, rsd_port: int):
        self.rsd_host = rsd_host
        self.rsd_port = rsd_port
        self.connected = False
        self.status = 'Connecting to device...'
        self._latest: tuple | None = None
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._event: asyncio.Event | None = None

        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def set_location(self, lat: float, lon: float):
        """Called from HTTP handler thread — non-blocking."""
        with self._lock:
            self._latest = (lat, lon)
        if self._loop and self._event:
            self._loop.call_soon_threadsafe(self._event.set)

    def _run(self):
        asyncio.run(self._async_main())

    async def _async_main(self):
        from pymobiledevice3.remote.remote_service_discovery import RemoteServiceDiscoveryService
        from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
        from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation

        self._loop = asyncio.get_running_loop()
        self._event = asyncio.Event()

        try:
            async with RemoteServiceDiscoveryService((self.rsd_host, self.rsd_port)) as rsd:
                async with DvtProvider(rsd) as dvt:
                    async with LocationSimulation(dvt) as loc:
                        self.connected = True
                        self.status = 'Phone connected successfully'
                        print('  Device connected. Ready to spoof.')

                        while True:
                            await self._event.wait()
                            self._event.clear()

                            with self._lock:
                                if self._latest is None:
                                    continue
                                lat, lon = self._latest
                                self._latest = None

                            await loc.set(lat, lon)

        except Exception as e:
            self.connected = False
            self.status = 'Phone disconnected'
            print(f'  Connection error: {e}')


controller: LocationController | None = None


# ── Favorites ──────────────────────────────────────────────────────────────────

FAVORITES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'favorites.json')
favorites: list = []

def load_favorites():
    global favorites
    try:
        with open(FAVORITES_FILE) as f:
            favorites = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        favorites = []

def save_favorites():
    with open(FAVORITES_FILE, 'w') as f:
        json.dump(favorites, f, indent=2)


# ── HTML ───────────────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>GPS Spoof</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
body { display: flex; height: 100vh; background: #1c1c1e; color: #fff; overflow: hidden; }

#panel {
  width: 300px; min-width: 300px;
  display: flex; flex-direction: column;
  background: #2c2c2e; border-right: 1px solid #3a3a3c;
  overflow-y: auto;
}
.panel-header {
  padding: 16px; border-bottom: 1px solid #3a3a3c;
  display: flex; align-items: center; gap: 14px;
}
.panel-header h1 { margin-bottom: 4px; }
.panel-header h1 { font-size: 17px; font-weight: 700; }
.section { padding: 20px 16px; border-bottom: 1px solid #3a3a3c; }
.section-label {
  font-size: 11px; font-weight: 600; color: #8e8e93;
  text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 12px;
}

#status-bar {
  display: flex; align-items: flex-start; gap: 8px;
  font-size: 12px; color: #aeaeb2; line-height: 1.4;
}
#dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #ff453a; flex-shrink: 0; margin-top: 3px;
  transition: background 0.3s;
}
#dot.active { background: #30d158; }
#dot.connecting { background: #ff9f0a; }

.field-label { font-size: 11px; color: #8e8e93; margin-bottom: 3px; }
.input-row { display: flex; gap: 8px; margin-bottom: 16px; }
.input-group { flex: 1; }
input[type=text] {
  width: 100%; padding: 7px 10px;
  background: #1c1c1e; border: 1px solid #3a3a3c;
  border-radius: 8px; color: #fff; font-size: 13px; outline: none;
}
input[type=text]:focus { border-color: #0a84ff; }
.btn-row { display: flex; gap: 8px; align-items: stretch; }
.btn-row button { padding-top: 8px; padding-bottom: 8px; }
button {
  padding: 8px 14px; border: none; border-radius: 8px;
  font-size: 13px; font-weight: 600; cursor: pointer; transition: opacity 0.15s;
  display: inline-flex; align-items: center; justify-content: center; line-height: 1;
}
button:active { opacity: 0.7; }
.btn-blue { background: #0a84ff; color: #fff; }
.btn-gray { background: #3a3a3c; color: #fff; }
.btn-red  { background: #ff453a; color: #fff; width: 100%; padding: 11px; font-size: 14px; }
#error-msg { font-size: 11px; color: #ff453a; margin-top: 6px; display: none; }

.speed-row { display: flex; align-items: center; gap: 10px; }
input[type=range] { flex: 1; accent-color: #0a84ff; }
#speed-label { font-size: 12px; color: #aeaeb2; width: 52px; text-align: right; }
.speed-hint { font-size: 11px; color: #636366; margin-top: 6px; }

#joystick-wrap { display: flex; justify-content: center; padding-top: 4px; }
#joystick {
  position: relative; width: 110px; height: 110px;
  border-radius: 50%; background: #1c1c1e;
  border: 2px solid #3a3a3c; cursor: pointer; user-select: none;
}
#knob {
  position: absolute; width: 40px; height: 40px;
  border-radius: 50%; background: #0a84ff;
  top: 35px; left: 35px;
  box-shadow: 0 2px 12px rgba(10,132,255,0.5);
}
.dir {
  position: absolute; font-size: 10px; font-weight: 700;
  color: #636366; pointer-events: none;
}
.hint { font-size: 11px; color: #636366; text-align: center; margin-top: 8px; }
#map { flex: 1; }
.fav-save-row { display: flex; gap: 8px; margin-bottom: 10px; }
.fav-save-row input { flex: 1; }
.fav-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px; background: #1c1c1e;
  border-radius: 8px; margin-bottom: 6px;
}
.fav-info { flex: 1; min-width: 0; }
.fav-name { font-size: 13px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fav-coords { font-size: 10px; color: #636366; font-family: monospace; margin-top: 2px; }
.fav-actions { display: flex; gap: 5px; flex-shrink: 0; }
.btn-sm { padding: 5px 9px; font-size: 12px; }
#fav-empty { font-size: 11px; color: #636366; text-align: center; padding: 4px 0; }
.map-overlay {
  background: rgba(28,28,30,0.82);
  backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px; padding: 8px 12px;
  font-size: 11px; color: #ffffff;
  pointer-events: none; line-height: 1.75;
  white-space: nowrap;
}
.leaflet-control-recenter {
  background: #000 !important; color: #fff !important;
  display: flex !important; align-items: center; justify-content: center;
}
.leaflet-control-recenter:hover { background: #333 !important; color: #fff !important; }
.map-overlay .wp-badge {
  font-size: 12px; font-weight: 600; color: #0a84ff;
  margin-bottom: 4px; display: none;
}
</style>
</head>
<body>

<div id="panel">
  <div class="panel-header">
    <span style="font-size:22px;">📍</span>
    <div>
      <h1>GPS Spoof</h1>
      <div style="font-size:11px;color:#636366;">iPhone location simulator</div>
    </div>
  </div>

  <div class="section">
    <div class="section-label">Status</div>
    <div id="status-bar">
      <div id="dot" class="connecting"></div>
      <span id="status-text">Connecting to device...</span>
    </div>
    <div id="status-coord" style="font-size:11px;color:#8e8e93;margin-top:14px;font-family:monospace;">📍 37.7749, -122.4194</div>
  </div>

  <div class="section">
    <div class="section-label">Jump to Coordinate</div>
    <div class="input-row">
      <div class="input-group">
        <div class="field-label">Latitude</div>
        <input type="text" id="lat" value="37.7749" placeholder="e.g. 37.7749">
      </div>
      <div class="input-group">
        <div class="field-label">Longitude</div>
        <input type="text" id="lon" value="-122.4194" placeholder="e.g. -122.4194">
      </div>
    </div>
    <div class="btn-row">
      <button class="btn-blue btn-sm" onclick="jump()">Jump</button>
      <button class="btn-gray btn-sm" onclick="useCurrent()">Update Current</button>
    </div>
    <div id="error-msg">Invalid — Lat: -90…90 · Lon: -180…180</div>
  </div>

  <div class="section">
    <div class="section-label">Favorites</div>
    <div class="fav-save-row">
      <input type="text" id="fav-name" placeholder="Name this spot…">
      <button class="btn-blue btn-sm" onclick="saveFavorite()">Save</button>
    </div>
    <div id="fav-list">
      <div id="fav-empty">No favorites saved yet</div>
    </div>
  </div>

  <div class="section">
    <div class="section-label">Movement Speed</div>
    <div class="speed-row">
      <input type="range" id="speed" min="1" max="200" value="20" oninput="onSpeedChange()">
      <div id="speed-label">20 km/h</div>
    </div>
    <div class="speed-hint">Walking ≈ 5 · Running ≈ 12 · Cycling ≈ 25 · Fast test ≈ 80+</div>
  </div>

  <div class="section">
    <div class="section-label">Joystick</div>
    <div id="joystick-wrap">
      <div>
        <div id="joystick">
          <span class="dir" style="top:7px;left:50%;transform:translateX(-50%)">N</span>
          <span class="dir" style="bottom:7px;left:50%;transform:translateX(-50%)">S</span>
          <span class="dir" style="left:7px;top:50%;transform:translateY(-50%)">W</span>
          <span class="dir" style="right:7px;top:50%;transform:translateY(-50%)">E</span>
          <div id="knob"></div>
        </div>
        <div class="hint">Drag to move</div>
      </div>
    </div>
  </div>

  <div class="section">
    <button class="btn-red" onclick="stopSpoofing()">⏹ Stop Spoofing</button>
    <div style="font-size:11px;color:#636366;margin-top:8px;text-align:center;">
      Disconnect USB cable to fully restore real GPS
    </div>
  </div>
</div>

<div id="map"></div>

<script>
const map = L.map('map').setView([37.7749, -122.4194], 16);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19, attribution: '© OpenStreetMap'
}).addTo(map);
const marker = L.marker([37.7749, -122.4194], { draggable: true }).addTo(map);
marker.on('dragstart', () => { stopWalk(); stopJoystick(); });
marker.on('dragend', () => {
  const { lat, lng } = marker.getLatLng();
  updateDisplay(lat, lng);
  sendLocation(lat, lng);
  document.getElementById('lat').value = lat.toFixed(6);
  document.getElementById('lon').value = lng.toFixed(6);
});

// ── Map overlay ───────────────────────────────────────────
const overlayCtrl = L.control({ position: 'bottomleft' });
overlayCtrl.onAdd = () => {
  const div = L.DomUtil.create('div', 'map-overlay');
  div.innerHTML =
    '<div class="wp-badge" id="wp-badge"></div>' +
    '<div>Click map — add waypoint</div>' +
    '<div>Click numbered pin — remove</div>';
  return div;
};
overlayCtrl.addTo(map);

const recenterCtrl = L.control({ position: 'topleft' });
recenterCtrl.onAdd = () => {
  const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
  const a = L.DomUtil.create('a', 'leaflet-control-recenter', container);
  a.href = '#';
  a.title = 'Center map on current position';
  a.innerHTML = '<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="7" cy="7" r="3"/><line x1="7" y1="0" x2="7" y2="4"/><line x1="7" y1="10" x2="7" y2="14"/><line x1="0" y1="7" x2="4" y2="7"/><line x1="10" y1="7" x2="14" y2="7"/></svg>';
  L.DomEvent.disableClickPropagation(container);
  L.DomEvent.on(a, 'click', L.DomEvent.preventDefault);
  a.addEventListener('click', () => map.setView([curLat, curLon], 16));
  return container;
};
recenterCtrl.addTo(map);

function updateWaypointCount() {
  const el = document.getElementById('wp-badge');
  if (!el) return;
  if (waypoints.length > 0) {
    el.textContent = waypoints.length + ' waypoint' + (waypoints.length === 1 ? '' : 's') + ' queued';
    el.style.display = 'block';
  } else {
    el.style.display = 'none';
  }
}

let curLat = 37.7749, curLon = -122.4194, speed = 20; // km/h
let jVec = { dx: 0, dy: 0 }, jRunning = false, jActive = false;
let waypoints = [], walkActive = false, walkTarget = null, waypointMarkers = [], routeLine = null, leadLine = null;

// ── Background-safe timer (Web Worker ignores tab visibility throttling) ───────
const bgTick = new Worker(URL.createObjectURL(new Blob(
  ['setInterval(()=>self.postMessage(null),100);'],
  { type: 'application/javascript' }
)));
bgTick.onmessage = () => {
  if (walkActive) tickWalk();
  if (jRunning)   tickJoystick();
};

// ── Status polling ────────────────────────────────────────
async function pollStatus() {
  try {
    const res = await fetch('/status', { method: 'POST',
      headers: {'Content-Type':'application/json'}, body: '{}' });
    const d = await res.json();
    document.getElementById('status-text').textContent = d.status;
    const dot = document.getElementById('dot');
    dot.className = d.connected ? 'active' : (d.status.includes('Connecting') ? 'connecting' : '');
  } catch(e) {}
}
setInterval(pollStatus, 1000);
pollStatus();

// ── Helpers ───────────────────────────────────────────────
function updateDisplay(lat, lon) {
  curLat = lat; curLon = lon;
  marker.setLatLng([lat, lon]);
  map.panTo([lat, lon]);
  const coordEl = document.getElementById('status-coord');
  if (coordEl) coordEl.textContent = '📍 ' + lat.toFixed(5) + ', ' + lon.toFixed(5);
}

function showError(show) {
  document.getElementById('error-msg').style.display = show ? 'block' : 'none';
}

async function sendLocation(lat, lon) {
  try {
    await fetch('/jump', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ lat, lon })
    });
  } catch(e) {}
}

async function jump() {
  const lat = parseFloat(document.getElementById('lat').value);
  const lon = parseFloat(document.getElementById('lon').value);
  if (isNaN(lat)||isNaN(lon)||lat<-90||lat>90||lon<-180||lon>180) { showError(true); return; }
  showError(false);
  updateDisplay(lat, lon);
  await sendLocation(lat, lon);
}

function useCurrent() {
  document.getElementById('lat').value = curLat.toFixed(6);
  document.getElementById('lon').value = curLon.toFixed(6);
}

function onSpeedChange() {
  speed = parseInt(document.getElementById('speed').value);
  document.getElementById('speed-label').textContent = speed + ' km/h';
}

function stopSpoofing() {
  stopJoystick();
  stopWalk();
}

// ── Waypoint Route ────────────────────────────────────────
function numberedIcon(n) {
  return L.divIcon({
    className: '',
    html: `<div style="background:#0a84ff;color:#fff;width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;box-shadow:0 2px 8px rgba(0,0,0,0.5);cursor:pointer;">${n}</div>`,
    iconSize: [26, 26], iconAnchor: [13, 13]
  });
}

function updateRouteLine() {
  if (routeLine) { map.removeLayer(routeLine); routeLine = null; }
  if (waypoints.length >= 2) {
    routeLine = L.polyline(waypoints.map(w => [w.lat, w.lon]), {
      color: '#0a84ff', weight: 3, opacity: 0.65, dashArray: '8, 10'
    }).addTo(map);
  }
}

function updateLeadLine() {
  if (leadLine) { map.removeLayer(leadLine); leadLine = null; }
  if (waypoints.length > 0) {
    leadLine = L.polyline([[curLat, curLon], [waypoints[0].lat, waypoints[0].lon]], {
      color: '#0a84ff', weight: 3, opacity: 0.65, dashArray: '8, 10'
    }).addTo(map);
  }
}

function renumberMarkers() {
  waypointMarkers.forEach((m, i) => m.setIcon(numberedIcon(i + 1)));
}

function removeWaypoint(idx) {
  if (idx < 0 || idx >= waypoints.length) return;
  waypoints.splice(idx, 1);
  map.removeLayer(waypointMarkers[idx]);
  waypointMarkers.splice(idx, 1);
  renumberMarkers();
  updateRouteLine();
  updateLeadLine();
  updateWaypointCount();
  if (waypoints.length === 0) {
    walkActive = false; walkTarget = null;
  } else if (idx === 0) {
    walkActive = false;
    walkTarget = waypoints[0];
    walkActive = true;
  }
}

function addWaypoint(lat, lon) {
  waypoints.push({ lat, lon });
  const m = L.marker([lat, lon], { icon: numberedIcon(waypoints.length) }).addTo(map);
  m.on('click', e => { L.DomEvent.stopPropagation(e); removeWaypoint(waypointMarkers.indexOf(m)); });
  m.bindTooltip('Click to remove', { direction: 'top', offset: [0, -10] });
  waypointMarkers.push(m);
  updateRouteLine();
  updateLeadLine();
  updateWaypointCount();
  if (!walkActive) {
    walkTarget = waypoints[0];
    walkActive = true;
  }
}

function stopWalk() {
  walkActive = false; walkTarget = null;
  waypointMarkers.forEach(m => map.removeLayer(m));
  waypointMarkers = []; waypoints = [];
  if (routeLine) { map.removeLayer(routeLine); routeLine = null; }
  if (leadLine) { map.removeLayer(leadLine); leadLine = null; }
  updateWaypointCount();
}

function tickWalk() {
  if (!walkTarget) { stopWalk(); return; }
  const mpt = (speed / 3.6) * 0.1;
  const latDeg = 111000;
  const lonDeg = 111000 * Math.cos(curLat * Math.PI / 180);
  const dLat = walkTarget.lat - curLat;
  const dLon = walkTarget.lon - curLon;
  const distM = Math.hypot(dLat * latDeg, dLon * lonDeg);
  if (distM <= mpt) {
    updateDisplay(walkTarget.lat, walkTarget.lon);
    sendLocation(walkTarget.lat, walkTarget.lon);
    map.removeLayer(waypointMarkers[0]);
    waypoints.shift(); waypointMarkers.shift();
    renumberMarkers(); updateRouteLine(); updateWaypointCount();
    walkActive = false;
    if (waypoints.length > 0) {
      walkTarget = waypoints[0];
      walkActive = true;
    } else {
      walkTarget = null;
    }
    updateLeadLine();
    return;
  }
  const ratio = mpt / distM;
  const newLat = curLat + dLat * ratio;
  const newLon = curLon + dLon * ratio;
  updateDisplay(newLat, newLon);
  sendLocation(newLat, newLon);
  updateLeadLine();
}

map.on('click', e => {
  document.getElementById('lat').value = e.latlng.lat.toFixed(6);
  document.getElementById('lon').value = e.latlng.lng.toFixed(6);
  addWaypoint(e.latlng.lat, e.latlng.lng);
});

// ── Joystick ──────────────────────────────────────────────
const joystick = document.getElementById('joystick');
const knob = document.getElementById('knob');
const MAX_R = 48;

function moveKnob(e) {
  const r = joystick.getBoundingClientRect();
  let dx = e.clientX - (r.left + r.width/2);
  let dy = e.clientY - (r.top + r.height/2);
  const dist = Math.hypot(dx, dy);
  if (dist > MAX_R) { dx = dx/dist*MAX_R; dy = dy/dist*MAX_R; }
  knob.style.left = (75-27+dx)+'px';
  knob.style.top  = (75-27+dy)+'px';
  jVec = { dx: dx/MAX_R, dy: dy/MAX_R };
}

function resetKnob() {
  knob.style.left = '48px'; knob.style.top = '48px';
  jVec = { dx: 0, dy: 0 };
}

joystick.addEventListener('mousedown', e => { stopWalk(); jActive=true; moveKnob(e); startJoystick(); });
document.addEventListener('mousemove', e => { if(jActive) moveKnob(e); });
document.addEventListener('mouseup', () => { if(!jActive) return; jActive=false; resetKnob(); stopJoystick(); });

function startJoystick() { jRunning = true; }
function stopJoystick()  { jRunning = false; }

function tickJoystick() {
  if(jVec.dx===0 && jVec.dy===0) return;
  const mpt = (speed / 3.6) * 0.1; // km/h → m/s → meters per 100ms tick
  const latDeg = 111000;
  const lonDeg = 111000 * Math.cos(curLat * Math.PI/180);
  const newLat = curLat + (-jVec.dy * mpt / latDeg);
  const newLon = curLon + ( jVec.dx * mpt / lonDeg);
  updateDisplay(newLat, newLon);
  sendLocation(newLat, newLon); // fire and forget — server takes latest only
}

document.getElementById('lat').addEventListener('keydown', e => { if(e.key==='Enter') jump(); });
document.getElementById('lon').addEventListener('keydown', e => { if(e.key==='Enter') jump(); });
document.getElementById('fav-name').addEventListener('keydown', e => { if(e.key==='Enter') saveFavorite(); });

// ── Favorites ─────────────────────────────────────────────
let favData = [];

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

async function loadFavorites() {
  try {
    const res = await fetch('/favorites');
    favData = await res.json();
    renderFavorites();
  } catch(e) {}
}

function renderFavorites() {
  const list = document.getElementById('fav-list');
  const empty = document.getElementById('fav-empty');
  list.querySelectorAll('.fav-item').forEach(el => el.remove());
  if (favData.length === 0) { empty.style.display = 'block'; return; }
  empty.style.display = 'none';
  favData.forEach((f, i) => {
    const div = document.createElement('div');
    div.className = 'fav-item';
    div.innerHTML =
      `<div class="fav-info">` +
        `<div class="fav-name">${escHtml(f.name)}</div>` +
        `<div class="fav-coords">${f.lat.toFixed(5)}, ${f.lon.toFixed(5)}</div>` +
      `</div>` +
      `<div class="fav-actions">` +
        `<button class="btn-blue btn-sm" onclick="goToFavorite(${i})">Go</button>` +
        `<button class="btn-gray btn-sm" onclick="deleteFavorite(${i})">✕</button>` +
      `</div>`;
    list.appendChild(div);
  });
}

async function saveFavorite() {
  const nameEl = document.getElementById('fav-name');
  const name = nameEl.value.trim();
  if (!name) { nameEl.focus(); return; }
  await fetch('/favorites/add', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ name, lat: curLat, lon: curLon })
  });
  nameEl.value = '';
  await loadFavorites();
}

async function deleteFavorite(idx) {
  await fetch('/favorites/delete', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ index: idx })
  });
  await loadFavorites();
}

async function goToFavorite(idx) {
  const f = favData[idx];
  if (!f) return;
  stopWalk();
  updateDisplay(f.lat, f.lon);
  document.getElementById('lat').value = f.lat.toFixed(6);
  document.getElementById('lon').value = f.lon.toFixed(6);
  await sendLocation(f.lat, f.lon);
}

loadFavorites();
</script>
</body>
</html>"""


# ── HTTP Server ────────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == '/favorites':
            data = json.dumps(favorites).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(HTML.encode('utf-8'))

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if self.path == '/status':
            data = {
                'connected': controller.connected if controller else False,
                'status': controller.status if controller else 'No controller'
            }
        elif self.path == '/favorites/add':
            favorites.append({'name': body['name'], 'lat': body['lat'], 'lon': body['lon']})
            save_favorites()
            data = {'ok': True}
        elif self.path == '/favorites/delete':
            idx = body.get('index', -1)
            if 0 <= idx < len(favorites):
                favorites.pop(idx)
                save_favorites()
            data = {'ok': True}
        else:  # /jump
            lat, lon = body['lat'], body['lon']
            if controller:
                controller.set_location(lat, lon)
            data = {
                'ok': True,
                'status': controller.status if controller else 'ok'
            }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rsd', nargs=2, metavar=('HOST', 'PORT'), required=True,
                        help='RSD address and port from: sudo python3 -m pymobiledevice3 remote start-tunnel')
    args = parser.parse_args()

    rsd_host, rsd_port = args.rsd[0], int(args.rsd[1])
    load_favorites()
    controller = LocationController(rsd_host, rsd_port)

    port = 8765
    server = HTTPServer(('localhost', port), Handler)

    print()
    print('  GPS Spoof is running!')
    print(f'  Open in browser → http://localhost:{port}')
    print()
    print('  Waiting for device connection...')
    print('  Press Ctrl+C to stop.')
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
