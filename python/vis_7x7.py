# -*- coding: utf-8 -*-
"""
7x7 live sensor heatmap viewer - macOS native backend.
"""

import matplotlib
matplotlib.use('MacOSX')   # <-- native macOS backend, much more reliable than Tk

import re
import csv
import atexit
import serial
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import threading
import queue
import time
import matplotlib.animation as animation
from pathlib import Path
from datetime import datetime

# === Serial config ===
SERIAL_PORT = '/dev/cu.usbserial-0001'
BAUD_RATE = 250000
SERIAL_TIMEOUT_SEC = 0.2

# === Sensor matrix size ===
MATRIX_ROWS = 7
MATRIX_COLS = 7

# === Display options ===
VMIN = 0.0
VMAX = 3.3
SHOW_NUMBERS = True
DECIMALS = 2
DEBUG_EVERY = 8

# === Recording options ===
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RUN_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CSV_PATH = DATA_DIR / f"matrix_7x7_{RUN_TIMESTAMP}.csv"

DATA_DIR.mkdir(exist_ok=True)
csv_file = CSV_PATH.open("w", newline="", encoding="utf-8")
csv_writer = csv.writer(csv_file)
csv_header = (
    ["timestamp_iso", "elapsed_sec", "frame_index"]
    + [f"R{i+1}C{j+1}" for i in range(MATRIX_ROWS) for j in range(MATRIX_COLS)]
)
csv_writer.writerow(csv_header)
csv_file.flush()
recording_start_time = time.time()
atexit.register(csv_file.close)

print(f"Recording matrix frames to {CSV_PATH}")

# === Open serial and flush startup garbage ===
print(f"Opening {SERIAL_PORT} at {BAUD_RATE} baud...")
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=SERIAL_TIMEOUT_SEC)
ser.reset_input_buffer()
time.sleep(1.0)
ser.reset_input_buffer()
ser.readline()
print("Serial port ready and aligned.")

# === Colormap and figure ===
cmap = mcolors.LinearSegmentedColormap.from_list("custom", ["red", "yellow", "green"])
fig, ax = plt.subplots(figsize=(MATRIX_COLS * 0.6, MATRIX_ROWS * 0.6))

# Initialize with mid-range so heatmap is visible from the start
matrix = np.full((MATRIX_ROWS, MATRIX_COLS), (VMIN + VMAX) / 2, dtype=float)

heatmap = ax.imshow(matrix, cmap=cmap, vmin=VMIN, vmax=VMAX,
                    origin='upper', interpolation='nearest')
cbar = plt.colorbar(heatmap, label="Voltage (V)")
plt.title(f"{MATRIX_ROWS}x{MATRIX_COLS} Matrix Voltage Visualization")

ax.set_xticks(np.arange(MATRIX_COLS))
ax.set_yticks(np.arange(MATRIX_ROWS))
ax.set_xticklabels([f"C{j+1}" for j in range(MATRIX_COLS)])
ax.set_yticklabels([f"R{i+1}" for i in range(MATRIX_ROWS)])
ax.set_xticks(np.arange(-0.5, MATRIX_COLS, 1), minor=True)
ax.set_yticks(np.arange(-0.5, MATRIX_ROWS, 1), minor=True)
ax.grid(which="minor", color="white", linewidth=0.5)
ax.tick_params(axis='x', labelrotation=45)

cell_texts = None
if SHOW_NUMBERS:
    cell_texts = [[ax.text(j, i, "", ha="center", va="center",
                           color="black", fontsize=9)
                   for j in range(MATRIX_COLS)] for i in range(MATRIX_ROWS)]

# === Frame queue ===
data_queue: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=1)

def _queue_latest(q, item):
    try:
        if q.full():
            _ = q.get_nowait()
    except Exception:
        pass
    q.put_nowait(item)

def update_plot(_frame):
    if not data_queue.empty():
        new_matrix, elapsed_sec = data_queue.get()
        heatmap.set_data(new_matrix)
        ax.set_title(
            f"{MATRIX_ROWS}x{MATRIX_COLS} Matrix Voltage Visualization | "
            f"t={elapsed_sec:.3f}s ({elapsed_sec * 1000:.0f} ms)"
        )
        if cell_texts is not None:
            for i in range(MATRIX_ROWS):
                for j in range(MATRIX_COLS):
                    cell_texts[i][j].set_text(f"{new_matrix[i, j]:.{DECIMALS}f}")
    # Return all artists that were updated; required for some backends
    artists = [heatmap]
    if cell_texts is not None:
        for row in cell_texts:
            artists.extend(row)
    return artists

# === Parsing ===
_sep_re = re.compile(r'[,\s;]+')
_trim_re = re.compile(r'[\[\]\{\}]')

def _parse_numeric_line(raw_bytes):
    if not raw_bytes:
        return []
    line = raw_bytes.decode('utf-8', errors='ignore').strip()
    if not line:
        return []
    line = _trim_re.sub('', line)
    parts = [p for p in _sep_re.split(line) if p]
    vals = []
    for tok in parts:
        try:
            vals.append(float(tok))
        except ValueError:
            pass
    return vals

frames_ok = 0
frames_dropped = 0

def record_matrix(matrix_data, frame_index):
    now = time.time()
    elapsed_sec = now - recording_start_time
    row = (
        [datetime.now().isoformat(timespec="milliseconds"),
         f"{elapsed_sec:.3f}",
         frame_index]
        + [f"{value:.6f}" for value in matrix_data.flatten()]
    )
    csv_writer.writerow(row)
    csv_file.flush()
    return elapsed_sec

def parse_matrix_after_header(max_lines=20):
    rows = []
    for _ in range(max_lines):
        raw = ser.readline()
        vals = _parse_numeric_line(raw)
        if len(vals) >= MATRIX_COLS:
            rows.append(vals[:MATRIX_COLS])
            if len(rows) == MATRIX_ROWS:
                return np.array(rows, dtype=float)
    return None

def read_serial_forever():
    global frames_ok, frames_dropped
    while True:
        try:
            raw = ser.readline()
            if not raw:
                continue
            line = raw.decode('utf-8', errors='ignore').strip()
            if not line:
                continue
            if line.lower().startswith("matrix updated"):
                parsed = parse_matrix_after_header()
                if parsed is not None:
                    frames_ok += 1
                    elapsed_sec = record_matrix(parsed, frames_ok)
                    _queue_latest(data_queue, (parsed, elapsed_sec))
                    if frames_ok <= 3 or frames_ok % 50 == 0:
                        print(f"[ok] frame #{frames_ok} parsed, "
                              f"min={parsed.min():.3f} max={parsed.max():.3f}")
                else:
                    frames_dropped += 1
                    if frames_dropped % DEBUG_EVERY == 0:
                        print(f"[debug] dropped {frames_dropped} frames so far")
        except Exception as e:
            print(f"Serial read error: {e}")
            time.sleep(0.1)

data_thread = threading.Thread(target=read_serial_forever, daemon=True)
data_thread.start()

print("Starting plot...")
ani = animation.FuncAnimation(fig, update_plot, interval=50,
                              blit=False, cache_frame_data=False)
plt.tight_layout()
plt.show()