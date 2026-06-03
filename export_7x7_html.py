# -*- coding: utf-8 -*-
"""
Export a saved 7x7 matrix CSV as a self-contained interactive HTML replay.

The generated HTML embeds every CSV frame and provides a slider, play/pause,
and step controls. It uses browser canvas only, so it has no runtime
dependencies beyond a modern browser.
"""

import argparse
import csv
import json
from pathlib import Path


MATRIX_ROWS = 7
MATRIX_COLS = 7
VMIN = 0.0
VMAX = 3.3
DEFAULT_FRAME_INTERVAL_MS = 50


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>7x7 Matrix Replay</title>
  <style>
    :root {
      color-scheme: light;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    body {
      margin: 0;
      padding: 18px;
      background: #f6f7f9;
      color: #1f2933;
    }
    .panel {
      max-width: 1240px;
      margin: 0 auto;
      background: white;
      border: 1px solid #d9dee7;
      border-radius: 12px;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
      padding: 18px;
    }
    h1 {
      margin: 0 0 6px;
      font-size: 20px;
      font-weight: 650;
    }
    .meta {
      color: #52606d;
      font-size: 13px;
      margin-bottom: 14px;
    }
    .plots {
      display: grid;
      grid-template-columns: minmax(360px, 1fr) minmax(460px, 1.2fr);
      gap: 18px;
      align-items: start;
    }
    .plotBox {
      border: 1px solid #e1e6ef;
      border-radius: 10px;
      padding: 10px;
      background: #fbfcfe;
    }
    .plotTitle {
      font-size: 14px;
      font-weight: 650;
      margin: 0 0 8px;
    }
    canvas {
      width: 100%;
      height: auto;
      display: block;
      background: white;
      border-radius: 8px;
    }
    .controls {
      margin-top: 16px;
      display: grid;
      grid-template-columns: auto auto auto 1fr auto;
      gap: 10px;
      align-items: center;
    }
    button, select {
      border: 1px solid #b8c2cc;
      border-radius: 8px;
      background: white;
      color: #1f2933;
      padding: 7px 10px;
      font-size: 13px;
    }
    button:hover {
      background: #f0f4f8;
    }
    input[type="range"] {
      width: 100%;
    }
    .readout {
      margin-top: 10px;
      font-size: 13px;
      color: #334e68;
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
    }
  </style>
</head>
<body>
  <div class="panel">
    <h1>7x7 Matrix Replay</h1>
    <div class="meta" id="meta"></div>

    <div class="plots">
      <div class="plotBox">
        <div class="plotTitle">2D matrix voltage</div>
        <canvas id="heatmap" width="460" height="460"></canvas>
      </div>
      <div class="plotBox">
        <div class="plotTitle">3D-style voltage bars</div>
        <canvas id="bars" width="640" height="460"></canvas>
      </div>
    </div>

    <div class="controls">
      <button id="prevBtn" type="button">Prev</button>
      <button id="playBtn" type="button">Play</button>
      <button id="nextBtn" type="button">Next</button>
      <input id="slider" type="range" min="0" max="0" value="0" step="1">
      <select id="speed">
        <option value="0.25">0.25x</option>
        <option value="0.5">0.5x</option>
        <option value="1" selected>1x</option>
        <option value="2">2x</option>
        <option value="4">4x</option>
      </select>
    </div>
    <div class="readout" id="readout"></div>
  </div>

  <script>
    const DATA = __DATA_JSON__;
    const rows = DATA.rows;
    const cols = DATA.cols;
    const vmin = DATA.vmin;
    const vmax = DATA.vmax;
    const unit = DATA.unit || "V";
    const heatmap = document.getElementById("heatmap");
    const heatCtx = heatmap.getContext("2d");
    const bars = document.getElementById("bars");
    const barCtx = bars.getContext("2d");
    const slider = document.getElementById("slider");
    const playBtn = document.getElementById("playBtn");
    const speedSelect = document.getElementById("speed");
    const readout = document.getElementById("readout");
    const meta = document.getElementById("meta");

    let frameIndex = 0;
    let playing = false;
    let timer = null;

    slider.max = Math.max(DATA.frames.length - 1, 0);
    meta.textContent = `${DATA.source_name} | ${DATA.frames.length} frames | duration ${DATA.duration_sec.toFixed(3)} s | nominal ${DATA.nominal_fps.toFixed(1)} fps`;

    function clamp(value, lo, hi) {
      return Math.max(lo, Math.min(hi, value));
    }

    function lerp(a, b, t) {
      return a + (b - a) * t;
    }

    function colorFor(value) {
      const t = clamp((value - vmin) / (vmax - vmin || 1), 0, 1);
      let r, g, b;
      if (t < 0.5) {
        const k = t / 0.5;
        r = 255;
        g = lerp(0, 230, k);
        b = 0;
      } else {
        const k = (t - 0.5) / 0.5;
        r = lerp(255, 0, k);
        g = lerp(230, 160, k);
        b = 0;
      }
      return `rgb(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)})`;
    }

    function shadeColor(rgb, factor) {
      const nums = rgb.match(/\d+/g).map(Number);
      return `rgb(${nums.map(v => Math.round(clamp(v * factor, 0, 255))).join(",")})`;
    }

    function drawHeatmap(frame) {
      const pad = 46;
      const grid = Math.min(heatmap.width - pad * 1.5, heatmap.height - pad * 1.5);
      const cell = grid / rows;
      const x0 = pad;
      const y0 = pad * 0.65;
      heatCtx.clearRect(0, 0, heatmap.width, heatmap.height);
      heatCtx.font = "12px -apple-system, BlinkMacSystemFont, sans-serif";
      heatCtx.textAlign = "center";
      heatCtx.textBaseline = "middle";

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const value = frame.values[r * cols + c];
          const x = x0 + c * cell;
          const y = y0 + r * cell;
          heatCtx.fillStyle = colorFor(value);
          heatCtx.fillRect(x, y, cell, cell);
          heatCtx.strokeStyle = "rgba(255,255,255,0.85)";
          heatCtx.strokeRect(x, y, cell, cell);
          heatCtx.fillStyle = "#111827";
          heatCtx.fillText(value.toFixed(2), x + cell / 2, y + cell / 2);
        }
      }

      heatCtx.fillStyle = "#334e68";
      for (let c = 0; c < cols; c++) {
        heatCtx.fillText(`C${c + 1}`, x0 + c * cell + cell / 2, y0 + grid + 18);
      }
      for (let r = 0; r < rows; r++) {
        heatCtx.fillText(`R${r + 1}`, x0 - 18, y0 + r * cell + cell / 2);
      }
    }

    function project(col, row) {
      const originX = 318;
      const originY = 340;
      const stepX = 42;
      const stepY = 22;
      return {
        x: originX + (col - row) * stepX,
        y: originY + (col + row) * stepY * 0.55
      };
    }

    function drawBar(base, width, depth, height, color) {
      const topY = base.y - height;
      barCtx.fillStyle = shadeColor(color, 0.78);
      barCtx.beginPath();
      barCtx.moveTo(base.x - width / 2, base.y);
      barCtx.lineTo(base.x + width / 2, base.y);
      barCtx.lineTo(base.x + width / 2, topY);
      barCtx.lineTo(base.x - width / 2, topY);
      barCtx.closePath();
      barCtx.fill();

      barCtx.fillStyle = shadeColor(color, 0.60);
      barCtx.beginPath();
      barCtx.moveTo(base.x + width / 2, base.y);
      barCtx.lineTo(base.x + width / 2 + depth, base.y - depth * 0.55);
      barCtx.lineTo(base.x + width / 2 + depth, topY - depth * 0.55);
      barCtx.lineTo(base.x + width / 2, topY);
      barCtx.closePath();
      barCtx.fill();

      barCtx.fillStyle = color;
      barCtx.beginPath();
      barCtx.moveTo(base.x - width / 2, topY);
      barCtx.lineTo(base.x + width / 2, topY);
      barCtx.lineTo(base.x + width / 2 + depth, topY - depth * 0.55);
      barCtx.lineTo(base.x - width / 2 + depth, topY - depth * 0.55);
      barCtx.closePath();
      barCtx.fill();

      barCtx.strokeStyle = "rgba(15,23,42,0.18)";
      barCtx.strokeRect(base.x - width / 2, topY, width, height);
    }

    function drawBars(frame) {
      barCtx.clearRect(0, 0, bars.width, bars.height);
      barCtx.font = "11px -apple-system, BlinkMacSystemFont, sans-serif";
      barCtx.textAlign = "center";
      barCtx.textBaseline = "bottom";

      const maxBarHeight = 150;
      const barWidth = 23;
      const barDepth = 16;
      const ordered = [];
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          ordered.push({r, c, order: r + c});
        }
      }
      ordered.sort((a, b) => a.order - b.order);

      for (const cell of ordered) {
        const value = frame.values[cell.r * cols + cell.c];
        const h = clamp((value - vmin) / (vmax - vmin || 1), 0, 1) * maxBarHeight;
        const base = project(cell.c, cell.r);
        const color = colorFor(value);
        drawBar(base, barWidth, barDepth, h, color);
        barCtx.fillStyle = "#111827";
        barCtx.fillText(value.toFixed(2), base.x + barDepth / 2, base.y - h - barDepth * 0.55 - 3);
      }

      barCtx.fillStyle = "#334e68";
      barCtx.textBaseline = "middle";
      barCtx.fillText("Voltage bars", bars.width / 2, 22);
    }

    function render(index) {
      frameIndex = clamp(index, 0, DATA.frames.length - 1);
      const frame = DATA.frames[frameIndex];
      drawHeatmap(frame);
      drawBars(frame);
      slider.value = frameIndex;
      readout.innerHTML = [
        `frame ${frameIndex + 1}/${DATA.frames.length}`,
        `t=${frame.t.toFixed(3)}s`,
        frame.timestamp ? frame.timestamp : "",
        `min=${Math.min(...frame.values).toFixed(3)} ${unit}`,
        `max=${Math.max(...frame.values).toFixed(3)} ${unit}`
      ].filter(Boolean).map(s => `<span>${s}</span>`).join("");
    }

    function playNext() {
      if (!playing) return;
      if (frameIndex >= DATA.frames.length - 1) {
        playing = false;
        playBtn.textContent = "Play";
        return;
      }
      render(frameIndex + 1);
      const speed = Number(speedSelect.value) || 1;
      timer = setTimeout(playNext, Math.max(1, DATA.frame_interval_ms / speed));
    }

    playBtn.addEventListener("click", () => {
      playing = !playing;
      playBtn.textContent = playing ? "Pause" : "Play";
      if (playing) playNext();
      else if (timer) clearTimeout(timer);
    });
    document.getElementById("prevBtn").addEventListener("click", () => render(frameIndex - 1));
    document.getElementById("nextBtn").addEventListener("click", () => render(frameIndex + 1));
    slider.addEventListener("input", () => render(Number(slider.value)));

    render(0);
  </script>
</body>
</html>
"""


def latest_csv(data_dir):
    csv_files = sorted(data_dir.glob("matrix_7x7_*.csv"), key=lambda path: path.stat().st_mtime)
    if not csv_files:
        raise SystemExit(f"No matrix CSV files found in {data_dir}")
    return csv_files[-1]


def load_csv_data(csv_path):
    value_columns = [f"R{i+1}C{j+1}" for i in range(MATRIX_ROWS) for j in range(MATRIX_COLS)]
    frames = []
    times = []
    unit = "V"

    with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        fieldnames = reader.fieldnames or []
        missing_columns = [column for column in value_columns if column not in fieldnames]
        if missing_columns:
            raise SystemExit(f"{csv_path} is missing columns: {', '.join(missing_columns[:5])}")

        for row in reader:
            values = [round(float(row[column]), 6) for column in value_columns]
            if row.get("value_unit"):
                unit = row["value_unit"]
            if "device_millis" in fieldnames and row.get("device_millis"):
                time_sec = float(row["device_millis"]) / 1000
            else:
                time_sec = float(row.get("elapsed_sec") or len(frames) * DEFAULT_FRAME_INTERVAL_MS / 1000)
            times.append(time_sec)
            frames.append({
                "timestamp": row.get("timestamp_iso", ""),
                "values": values,
            })

    if not frames:
        raise SystemExit(f"{csv_path} has no matrix frames")

    start_time = times[0]
    duration_sec = max(times[-1] - start_time, 0.0)
    frame_interval_ms = (
        duration_sec * 1000 / (len(frames) - 1)
        if len(frames) > 1 and duration_sec > 0
        else DEFAULT_FRAME_INTERVAL_MS
    )
    nominal_fps = 1000 / frame_interval_ms if frame_interval_ms > 0 else 0

    for frame, time_sec in zip(frames, times):
        frame["t"] = round(time_sec - start_time, 6)

    return {
        "source_name": csv_path.name,
        "rows": MATRIX_ROWS,
        "cols": MATRIX_COLS,
        "vmin": VMIN,
        "vmax": VMAX,
        "unit": unit,
        "duration_sec": round(duration_sec, 6),
        "frame_interval_ms": max(1, round(frame_interval_ms, 3)),
        "nominal_fps": round(nominal_fps, 3),
        "frames": frames,
    }


def export_csv_to_html(csv_path, output_path=None):
    csv_path = Path(csv_path)
    output_path = Path(output_path) if output_path else csv_path.with_suffix(".html")
    data = load_csv_data(csv_path)
    html = HTML_TEMPLATE.replace("__DATA_JSON__", json.dumps(data, separators=(",", ":")))
    output_path.write_text(html, encoding="utf-8")
    return output_path


def parse_args():
    parser = argparse.ArgumentParser(description="Export 7x7 matrix CSV data to interactive HTML.")
    parser.add_argument("csv_path", nargs="?", type=Path,
                        help="CSV file to export. Defaults to newest data/matrix_7x7_*.csv")
    parser.add_argument("--data-dir", type=Path,
                        default=Path(__file__).resolve().parent / "data",
                        help="Directory used when csv_path is omitted.")
    parser.add_argument("-o", "--output", type=Path,
                        help="Output HTML path. Defaults to CSV path with .html suffix.")
    return parser.parse_args()


def main():
    args = parse_args()
    csv_path = args.csv_path or latest_csv(args.data_dir)
    output_path = export_csv_to_html(csv_path, args.output)
    print(f"Exported interactive replay to {output_path}")


if __name__ == "__main__":
    main()
