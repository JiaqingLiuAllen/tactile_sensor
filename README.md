# Tactile Sensor Matrix

7x7 tactile sensor matrix scanning and visualization tools for an ESP32 dev board with CD74HC4067 multiplexers and an external AD7276 ADC.

## Project Structure

```text
arduino/    ESP32 sketches
python/     live visualization, replay, and HTML export scripts
data/       recorded CSV/HTML outputs
reference/  external course/reference materials
```

## Current ADC Setup

The current AD7276 wiring used by the ADC sketches is:

```text
AD7276 SCLK  -> ESP32 GPIO18
AD7276 SDATA -> ESP32 GPIO19
AD7276 CS    -> ESP32 GPIO4 / D4
AD7276 VIN   -> VADC node
```

## Arduino Sketches

Stable version:

```bash
arduino-cli compile --upload --port /dev/cu.usbserial-0001 --fqbn "esp32:esp32:esp32:UploadSpeed=115200" arduino/matrix_scanning_binary_adc_stable
```

Measured update rate: about 72 FPS for the full 7x7 matrix.

Fast version:

```bash
arduino-cli compile --upload --port /dev/cu.usbserial-0001 --fqbn "esp32:esp32:esp32:UploadSpeed=115200" arduino/matrix_scanning_binary_adc_fast
```

Measured update rate: about 1000 FPS for the full 7x7 matrix.

## Python Viewer

The ADC viewers use the same binary frame protocol as the ESP32 sketches. The fast viewer is configured for the current high-speed AD7276 sketch at 1,500,000 baud, so it can receive and record the current high-frequency ADC stream.

Run the matching live viewer:

```bash
python3 python/vis_7x7_binary_adc_stable.py
python3 python/vis_7x7_binary_adc_fast.py
```

The viewer records CSV files into `data/` and exports an HTML replay when it exits.

## Replay / Export

```bash
python3 python/replay_7x7_csv.py
python3 python/export_7x7_html.py
```

## Common Commands

Upload and view the stable ADC version:

```bash
arduino-cli compile --upload --port /dev/cu.usbserial-0001 --fqbn "esp32:esp32:esp32:UploadSpeed=115200" arduino/matrix_scanning_binary_adc_stable
python3 python/vis_7x7_binary_adc_stable.py
```

Upload and view the fast ADC version:

```bash
arduino-cli compile --upload --port /dev/cu.usbserial-0001 --fqbn "esp32:esp32:esp32:UploadSpeed=115200" arduino/matrix_scanning_binary_adc_fast
python3 python/vis_7x7_binary_adc_fast.py
```

Replay the newest recorded 7x7 CSV:

```bash
python3 python/replay_7x7_csv.py
```
