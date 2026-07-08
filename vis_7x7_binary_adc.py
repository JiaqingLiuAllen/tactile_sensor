# -*- coding: utf-8 -*-
"""
AD7276 version of the 7x7 binary live viewer.

The ESP32 ADC sketch keeps the same serial binary protocol as
vis_7x7_binary.py, so this file runs the existing viewer unchanged.
"""

from pathlib import Path
import runpy


runpy.run_path(str(Path(__file__).with_name("vis_7x7_binary.py")), run_name="__main__")
