# -*- coding: utf-8 -*-
"""
7x7 live sensor heatmap viewer for the binary Arduino protocol.
"""

import atexit
import csv
import queue
import struct
import threading
import time
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("MacOSX")

import matplotlib.animation as animation
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import serial
from matplotlib.cm import ScalarMappable

from export_7x7_html import export_csv_to_html


# === Serial config ===
SERIAL_PORT = "/dev/cu.usbserial-0001"
BAUD_RATE = 921600
SERIAL_TIMEOUT_SEC = 0.2

# === Binary protocol ===
MAGIC = b"M7XB"
PROTOCOL_VERSION = 1
PAYLOAD_TYPE_ADC_U16 = 1
MATRIX_ROWS = 7
MATRIX_COLS = 7
ADC_MAX_VALUE = 4095.0
ADC_REF_VOLTAGE = 3.3

METADATA_FORMAT = "<BBBBII"
METADATA_BYTES = struct.calcsize(METADATA_FORMAT)
VALUE_COUNT = MATRIX_ROWS * MATRIX_COLS
PAYLOAD_BYTES = VALUE_COUNT * 2
FRAME_BODY_BYTES = METADATA_BYTES + PAYLOAD_BYTES
FRAME_REST_BYTES = FRAME_BODY_BYTES + 2

# === Display options ===
VMIN = 0.0
VMAX = 3.3
PLOT_INTERVAL_MS = 33
DEBUG_EVERY = 25
BAR_WIDTH = 0.75
SHOW_NUMBERS = True
VOLTAGE_DECIMALS = 2
TEXT_Z_OFFSET_FRACTION = 0.02

# === Recording options ===
DATA_DIR = Path(__file__).resolve().parent / "data"
RUN_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CSV_PATH = DATA_DIR / f"matrix_7x7_binary_{RUN_TIMESTAMP}.csv"
CSV_FLUSH_EVERY = 50
AUTO_EXPORT_HTML = True

DATA_DIR.mkdir(exist_ok=True)
csv_file = CSV_PATH.open("w", newline="", encoding="utf-8")
csv_writer = csv.writer(csv_file)
csv_header = (
    ["timestamp_iso", "elapsed_sec", "host_frame_index",
     "device_frame_index", "device_millis", "value_unit"]
    + [f"R{i+1}C{j+1}" for i in range(MATRIX_ROWS) for j in range(MATRIX_COLS)]
)
csv_writer.writerow(csv_header)
csv_file.flush()
recording_start_time = time.time()


def close_csv():
    if not csv_file.closed:
        csv_file.flush()
        csv_file.close()


atexit.register(close_csv)

print(f"Recording binary matrix frames to {CSV_PATH}")

# === Open serial ===
print(f"Opening {SERIAL_PORT} at {BAUD_RATE} baud...")
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=SERIAL_TIMEOUT_SEC)
ser.reset_input_buffer()
time.sleep(1.0)
ser.reset_input_buffer()
print("Serial port ready. Waiting for binary frames...")

# === Colormap and 3D figure ===
cmap = mcolors.LinearSegmentedColormap.from_list("custom", ["red", "yellow", "green"])
norm = mcolors.Normalize(vmin=VMIN, vmax=VMAX)
scalar_mappable = ScalarMappable(norm=norm, cmap=cmap)
fig = plt.figure(figsize=(MATRIX_COLS * 1.8, MATRIX_ROWS * 0.85))
ax_matrix = fig.add_subplot(121)
ax_bar = fig.add_subplot(122, projection="3d")

matrix = np.zeros((MATRIX_ROWS, MATRIX_COLS), dtype=float)
heatmap = ax_matrix.imshow(matrix, cmap=cmap, norm=norm,
                           origin="upper", interpolation="nearest")
x_positions, y_positions = np.meshgrid(np.arange(MATRIX_COLS), np.arange(MATRIX_ROWS))
x_positions = x_positions.ravel()
y_positions = y_positions.ravel()
z_positions = np.zeros(VALUE_COUNT)
dx = np.full(VALUE_COUNT, BAR_WIDTH)
dy = np.full(VALUE_COUNT, BAR_WIDTH)


def display_label(value_unit):
    if value_unit == "V":
        return "Voltage (V)"
    return value_unit


def update_display_scale(matrix_data, value_unit):
    zmin = VMIN
    zmax = VMAX
    norm.vmin = zmin
    norm.vmax = zmax
    scalar_mappable.set_clim(zmin, zmax)
    colorbar.update_normal(scalar_mappable)
    colorbar.set_label(display_label(value_unit))
    heatmap.set_clim(zmin, zmax)
    ax_bar.set_zlabel(display_label(value_unit))
    ax_bar.set_zlim(zmin, zmax)


def format_display_value(value, value_unit):
    return f"{value:.{VOLTAGE_DECIMALS}f}"


def draw_bars(matrix_data):
    heights = matrix_data.ravel()
    colors = cmap(norm(heights))
    return ax_bar.bar3d(x_positions, y_positions, z_positions, dx, dy,
                        heights, color=colors, shade=True)


def draw_matrix_labels(matrix_data, value_unit):
    if not SHOW_NUMBERS:
        return []

    labels = []
    for row in range(MATRIX_ROWS):
        for col in range(MATRIX_COLS):
            labels.append(
                ax_matrix.text(col, row,
                               format_display_value(matrix_data[row, col], value_unit),
                               ha="center", va="center",
                               fontsize=8, color="black")
            )
    return labels


def draw_value_labels(matrix_data, value_unit):
    if not SHOW_NUMBERS:
        return []

    z_span = max(norm.vmax - norm.vmin, 1.0)
    z_offset = z_span * TEXT_Z_OFFSET_FRACTION
    labels = []
    for row in range(MATRIX_ROWS):
        for col in range(MATRIX_COLS):
            value = matrix_data[row, col]
            labels.append(
                ax_bar.text(col + BAR_WIDTH / 2, row + BAR_WIDTH / 2,
                            value + z_offset, format_display_value(value, value_unit),
                            ha="center", va="bottom", fontsize=6, color="black")
            )
    return labels


bar_collection = draw_bars(matrix)
matrix_labels = draw_matrix_labels(matrix, "V")
value_labels = []
colorbar = fig.colorbar(scalar_mappable, ax=[ax_matrix, ax_bar],
                        shrink=0.75, pad=0.06)
colorbar.set_label(display_label("V"))
fig.suptitle(f"{MATRIX_ROWS}x{MATRIX_COLS} Binary Matrix Visualization")
ax_matrix.set_xticks(np.arange(MATRIX_COLS))
ax_matrix.set_yticks(np.arange(MATRIX_ROWS))
ax_matrix.set_xticklabels([f"C{j+1}" for j in range(MATRIX_COLS)])
ax_matrix.set_yticklabels([f"R{i+1}" for i in range(MATRIX_ROWS)])
ax_matrix.set_xticks(np.arange(-0.5, MATRIX_COLS, 1), minor=True)
ax_matrix.set_yticks(np.arange(-0.5, MATRIX_ROWS, 1), minor=True)
ax_matrix.grid(which="minor", color="white", linewidth=0.5)
ax_matrix.tick_params(axis="x", labelrotation=45)

ax_bar.set_xlabel("Column")
ax_bar.set_ylabel("Row")
ax_bar.set_zlabel(display_label("V"))
ax_bar.set_xlim(-0.25, MATRIX_COLS - 0.25)
ax_bar.set_ylim(MATRIX_ROWS - 0.25, -0.25)
ax_bar.set_zlim(VMIN, VMAX)
ax_bar.set_xticks(np.arange(MATRIX_COLS) + BAR_WIDTH / 2)
ax_bar.set_yticks(np.arange(MATRIX_ROWS) + BAR_WIDTH / 2)
ax_bar.set_xticklabels([f"C{j+1}" for j in range(MATRIX_COLS)])
ax_bar.set_yticklabels([f"R{i+1}" for i in range(MATRIX_ROWS)])
ax_bar.tick_params(axis="x", labelrotation=45)
ax_bar.view_init(elev=30, azim=-55)

# === Frame queue for display only ===
data_queue = queue.Queue(maxsize=1)
stop_event = threading.Event()


def _queue_latest(q, item):
    try:
        if q.full():
            _ = q.get_nowait()
        q.put_nowait(item)
    except queue.Full:
        pass


def update_plot(_frame):
    global bar_collection, matrix_labels, value_labels

    if not data_queue.empty():
        new_matrix, value_unit, host_elapsed_sec, device_millis, host_fps = data_queue.get()
        bar_collection.remove()
        for label in matrix_labels:
            label.remove()
        for label in value_labels:
            label.remove()
        update_display_scale(new_matrix, value_unit)
        heatmap.set_data(new_matrix)
        matrix_labels = draw_matrix_labels(new_matrix, value_unit)
        bar_collection = draw_bars(new_matrix)
        value_labels = draw_value_labels(new_matrix, value_unit)
        title_suffix = (
            f"t={host_elapsed_sec:.3f}s ({host_elapsed_sec * 1000:.0f} ms) | "
            f"device={device_millis} ms | "
            f"{host_fps:.1f} fps | "
            f"raw {new_matrix.min():.3f}-{new_matrix.max():.3f} {value_unit}"
        )
        fig.suptitle(
            f"{MATRIX_ROWS}x{MATRIX_COLS} Binary Matrix Visualization | "
            f"{title_suffix}"
        )

    return [heatmap, bar_collection, *matrix_labels, *value_labels]


frames_ok = 0
frames_bad = 0
device_frame_gaps = 0
last_device_frame = None
last_report_time = time.time()
last_report_frame = 0
last_host_fps = 0.0


def read_exact(size):
    chunks = bytearray()
    while len(chunks) < size:
        chunk = ser.read(size - len(chunks))
        if not chunk:
            return None
        chunks.extend(chunk)
    return bytes(chunks)


def read_next_frame():
    sync = bytearray()
    while True:
        byte = ser.read(1)
        if not byte:
            return None

        sync.append(byte[0])
        if len(sync) > len(MAGIC):
            del sync[0]
        if bytes(sync) == MAGIC:
            break

    rest = read_exact(FRAME_REST_BYTES)
    if rest is None:
        return None

    body = rest[:FRAME_BODY_BYTES]
    expected_checksum = struct.unpack_from("<H", rest, FRAME_BODY_BYTES)[0]
    actual_checksum = sum(body) & 0xFFFF
    if actual_checksum != expected_checksum:
        return None

    version, rows, cols, payload_type, device_frame_index, device_millis = (
        struct.unpack_from(METADATA_FORMAT, body, 0)
    )
    if (version != PROTOCOL_VERSION or rows != MATRIX_ROWS or
            cols != MATRIX_COLS):
        return None

    payload = body[METADATA_BYTES:]
    raw_values = np.frombuffer(payload, dtype="<u2").astype(np.float32)
    raw_matrix = raw_values.reshape((MATRIX_ROWS, MATRIX_COLS))

    if payload_type == PAYLOAD_TYPE_ADC_U16:
        data_matrix = raw_matrix * (ADC_REF_VOLTAGE / ADC_MAX_VALUE)
        value_unit = "V"
    else:
        return None

    return data_matrix, value_unit, device_frame_index, device_millis


def record_matrix(matrix_data, value_unit, host_frame_index, device_frame_index, device_millis):
    now = time.time()
    row = (
        [datetime.now().isoformat(timespec="milliseconds"),
         f"{now - recording_start_time:.3f}",
         host_frame_index,
         device_frame_index,
         device_millis,
         value_unit]
        + [f"{value:.6f}" for value in matrix_data.flatten()]
    )
    csv_writer.writerow(row)
    if host_frame_index % CSV_FLUSH_EVERY == 0:
        csv_file.flush()


def read_serial_forever():
    global frames_ok, frames_bad, device_frame_gaps
    global last_device_frame, last_report_time, last_report_frame, last_host_fps

    while not stop_event.is_set():
        try:
            parsed = read_next_frame()
            if parsed is None:
                frames_bad += 1
                if frames_bad % DEBUG_EVERY == 0:
                    print(f"[debug] bad/timeout frames so far: {frames_bad}")
                continue

            matrix_data, value_unit, device_frame_index, device_millis = parsed
            frames_ok += 1

            if last_device_frame is not None and device_frame_index > last_device_frame + 1:
                device_frame_gaps += device_frame_index - last_device_frame - 1
            last_device_frame = device_frame_index

            record_matrix(matrix_data, value_unit, frames_ok, device_frame_index, device_millis)

            now = time.time()
            host_elapsed_sec = now - recording_start_time
            elapsed = now - last_report_time
            if elapsed >= 1.0:
                last_host_fps = (frames_ok - last_report_frame) / elapsed
                last_report_time = now
                last_report_frame = frames_ok

            _queue_latest(data_queue, (matrix_data, value_unit, host_elapsed_sec,
                                       device_millis, last_host_fps))

            if frames_ok <= 3 or frames_ok % 200 == 0:
                print(f"[ok] host #{frames_ok}, device #{device_frame_index}, "
                      f"fps={last_host_fps:.1f}, gaps={device_frame_gaps}, "
                      f"min={matrix_data.min():.3f} max={matrix_data.max():.3f} {value_unit}")
        except Exception as exc:
            print(f"Serial read error: {exc}")
            time.sleep(0.1)


data_thread = threading.Thread(target=read_serial_forever, daemon=True)
data_thread.start()

print("Starting plot...")
ani = animation.FuncAnimation(fig, update_plot, interval=PLOT_INTERVAL_MS,
                              blit=False, cache_frame_data=False)
plt.tight_layout()
plt.show()

stop_event.set()
try:
    ser.close()
except Exception:
    pass
data_thread.join(timeout=1.0)
csv_file.flush()

if AUTO_EXPORT_HTML:
    try:
        html_path = export_csv_to_html(CSV_PATH)
        print(f"Exported interactive replay to {html_path}")
    except Exception as exc:
        print(f"HTML export failed: {exc}")
