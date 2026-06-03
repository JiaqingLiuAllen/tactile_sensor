# -*- coding: utf-8 -*-
"""
Replay saved 7x7 matrix CSV data as an animation.
"""

import argparse
import csv
from pathlib import Path

import matplotlib.animation as animation
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np


MATRIX_ROWS = 7
MATRIX_COLS = 7
VMIN = 0.0
VMAX = 3.3
SHOW_NUMBERS = True
DECIMALS = 2
DEFAULT_FRAME_INTERVAL_MS = 50
BAR_WIDTH = 0.75
TEXT_Z_OFFSET_FRACTION = 0.02


def latest_csv(data_dir):
    csv_files = sorted(data_dir.glob("matrix_7x7_*.csv"), key=lambda path: path.stat().st_mtime)
    if not csv_files:
        raise SystemExit(f"No matrix CSV files found in {data_dir}")
    return csv_files[-1]


def load_frames(csv_path):
    value_columns = [f"R{i+1}C{j+1}" for i in range(MATRIX_ROWS) for j in range(MATRIX_COLS)]
    frames = []
    display_times = []
    timestamps = []

    with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        fieldnames = reader.fieldnames or []
        missing_columns = [column for column in value_columns if column not in reader.fieldnames]
        if missing_columns:
            raise SystemExit(f"{csv_path} is missing columns: {', '.join(missing_columns[:5])}")

        for row in reader:
            values = [float(row[column]) for column in value_columns]
            frames.append(np.array(values, dtype=float).reshape((MATRIX_ROWS, MATRIX_COLS)))
            if "device_millis" in fieldnames and row.get("device_millis"):
                display_times.append(float(row["device_millis"]) / 1000)
            else:
                display_times.append(
                    float(row.get("elapsed_sec") or len(frames) * DEFAULT_FRAME_INTERVAL_MS / 1000)
                )
            timestamps.append(row.get("timestamp_iso", ""))

    if not frames:
        raise SystemExit(f"{csv_path} has no matrix frames")

    return frames, display_times, timestamps


def choose_frame_interval_ms(display_times, speed, fixed_interval_ms):
    if fixed_interval_ms is not None:
        return fixed_interval_ms
    if len(display_times) < 2:
        return DEFAULT_FRAME_INTERVAL_MS

    duration_sec = display_times[-1] - display_times[0]
    if duration_sec <= 0:
        return DEFAULT_FRAME_INTERVAL_MS

    frame_interval_ms = duration_sec * 1000 / (len(display_times) - 1) / speed
    return max(1, int(round(frame_interval_ms)))


def build_animation(frames, display_times, timestamps, frame_interval_ms, source_name):
    cmap = mcolors.LinearSegmentedColormap.from_list("custom", ["red", "yellow", "green"])
    norm = mcolors.Normalize(vmin=VMIN, vmax=VMAX)
    fig = plt.figure(figsize=(MATRIX_COLS * 1.8, MATRIX_ROWS * 0.85))
    ax_matrix = fig.add_subplot(121)
    ax_bar = fig.add_subplot(122, projection="3d")

    heatmap = ax_matrix.imshow(frames[0], cmap=cmap, norm=norm,
                               origin="upper", interpolation="nearest")
    fig.colorbar(heatmap, ax=[ax_matrix, ax_bar], shrink=0.75,
                 pad=0.06, label="Voltage (V)")

    ax_matrix.set_xticks(np.arange(MATRIX_COLS))
    ax_matrix.set_yticks(np.arange(MATRIX_ROWS))
    ax_matrix.set_xticklabels([f"C{j+1}" for j in range(MATRIX_COLS)])
    ax_matrix.set_yticklabels([f"R{i+1}" for i in range(MATRIX_ROWS)])
    ax_matrix.set_xticks(np.arange(-0.5, MATRIX_COLS, 1), minor=True)
    ax_matrix.set_yticks(np.arange(-0.5, MATRIX_ROWS, 1), minor=True)
    ax_matrix.grid(which="minor", color="white", linewidth=0.5)
    ax_matrix.tick_params(axis="x", labelrotation=45)

    x_positions, y_positions = np.meshgrid(np.arange(MATRIX_COLS), np.arange(MATRIX_ROWS))
    x_positions = x_positions.ravel()
    y_positions = y_positions.ravel()
    z_positions = np.zeros(MATRIX_ROWS * MATRIX_COLS)
    dx = np.full(MATRIX_ROWS * MATRIX_COLS, BAR_WIDTH)
    dy = np.full(MATRIX_ROWS * MATRIX_COLS, BAR_WIDTH)

    ax_bar.set_xlabel("Column")
    ax_bar.set_ylabel("Row")
    ax_bar.set_zlabel("Voltage (V)")
    ax_bar.set_xlim(-0.25, MATRIX_COLS - 0.25)
    ax_bar.set_ylim(MATRIX_ROWS - 0.25, -0.25)
    ax_bar.set_zlim(VMIN, VMAX)
    ax_bar.set_xticks(np.arange(MATRIX_COLS) + BAR_WIDTH / 2)
    ax_bar.set_yticks(np.arange(MATRIX_ROWS) + BAR_WIDTH / 2)
    ax_bar.set_xticklabels([f"C{j+1}" for j in range(MATRIX_COLS)])
    ax_bar.set_yticklabels([f"R{i+1}" for i in range(MATRIX_ROWS)])
    ax_bar.tick_params(axis="x", labelrotation=45)
    ax_bar.view_init(elev=30, azim=-55)

    def draw_bars(matrix):
        heights = matrix.ravel()
        colors = cmap(norm(heights))
        return ax_bar.bar3d(x_positions, y_positions, z_positions, dx, dy,
                            heights, color=colors, shade=True)

    matrix_labels = []
    bar_labels = []
    if SHOW_NUMBERS:
        for row in range(MATRIX_ROWS):
            for col in range(MATRIX_COLS):
                matrix_labels.append(
                    ax_matrix.text(col, row, "", ha="center", va="center",
                                   color="black", fontsize=8)
                )

    bar_collection = draw_bars(frames[0])

    def update(frame_index):
        nonlocal bar_collection, bar_labels
        matrix = frames[frame_index]
        heatmap.set_data(matrix)
        bar_collection.remove()
        for label in bar_labels:
            label.remove()
        bar_labels = []
        bar_collection = draw_bars(matrix)

        artists = [heatmap, bar_collection]
        if SHOW_NUMBERS:
            z_offset = max(VMAX - VMIN, 1.0) * TEXT_Z_OFFSET_FRACTION
            for row in range(MATRIX_ROWS):
                for col in range(MATRIX_COLS):
                    label_index = row * MATRIX_COLS + col
                    value = matrix[row, col]
                    matrix_labels[label_index].set_text(f"{value:.{DECIMALS}f}")
                    artists.append(matrix_labels[label_index])
                    bar_labels.append(
                        ax_bar.text(col + BAR_WIDTH / 2, row + BAR_WIDTH / 2,
                                    value + z_offset, f"{value:.{DECIMALS}f}",
                                    ha="center", va="bottom",
                                    fontsize=6, color="black")
                    )
            artists.extend(bar_labels)

        elapsed_sec = display_times[frame_index] - display_times[0]
        timestamp_text = f" | {timestamps[frame_index]}" if timestamps[frame_index] else ""
        fig.suptitle(
            f"{source_name} | t={elapsed_sec:.3f}s "
            f"({elapsed_sec * 1000:.0f} ms){timestamp_text}"
        )
        return artists

    update(0)
    ani = animation.FuncAnimation(fig, update, frames=len(frames),
                                  interval=frame_interval_ms, blit=False,
                                  repeat=True, cache_frame_data=False)
    plt.tight_layout()
    return fig, ani


def parse_args():
    parser = argparse.ArgumentParser(description="Replay saved 7x7 matrix CSV data.")
    parser.add_argument("csv_path", nargs="?", type=Path,
                        help="CSV file to replay. Defaults to the newest data/matrix_7x7_*.csv")
    parser.add_argument("--data-dir", type=Path,
                        default=Path(__file__).resolve().parent / "data",
                        help="Directory used when csv_path is omitted.")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="Playback speed multiplier. Every CSV frame is still shown.")
    parser.add_argument("--interval-ms", type=int, default=None,
                        help="Override per-frame interval. Every CSV frame is still shown.")
    parser.add_argument("--save", type=Path, default=None,
                        help="Optional output path ending in .gif or .mp4.")
    parser.add_argument("--show", action="store_true",
                        help="Show the animation window after saving.")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.speed <= 0:
        raise SystemExit("--speed must be greater than 0")

    csv_path = args.csv_path or latest_csv(args.data_dir)
    frames, display_times, timestamps = load_frames(csv_path)
    frame_interval_ms = choose_frame_interval_ms(display_times, args.speed, args.interval_ms)

    print(f"Replaying {len(frames)} frames from {csv_path}")
    print(f"CSV duration: {display_times[-1] - display_times[0]:.3f} s")
    print(f"Per-frame interval: {frame_interval_ms} ms")
    print("Replay displays every CSV frame in order without skipping.")

    fig, ani = build_animation(frames, display_times, timestamps,
                               frame_interval_ms, csv_path.name)

    if args.save:
        suffix = args.save.suffix.lower()
        if suffix == ".gif":
            ani.save(args.save, writer="pillow", fps=max(1, int(1000 / frame_interval_ms)))
        elif suffix == ".mp4":
            ani.save(args.save, writer="ffmpeg", fps=max(1, int(1000 / frame_interval_ms)))
        else:
            raise SystemExit("--save output must end in .gif or .mp4")
        print(f"Saved animation to {args.save}")

    if args.show or args.save is None:
        plt.show()
    else:
        plt.close(fig)


if __name__ == "__main__":
    main()
