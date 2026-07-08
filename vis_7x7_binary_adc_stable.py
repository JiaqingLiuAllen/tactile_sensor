# -*- coding: utf-8 -*-
"""
Stable AD7276 7x7 viewer.
"""

import os
from pathlib import Path
import runpy


os.environ["TACTILE_BAUD_RATE"] = "921600"
os.environ["TACTILE_PLOT_INTERVAL_MS"] = "33"
os.environ["TACTILE_CSV_PREFIX"] = "matrix_7x7_binary_adc_stable"

runpy.run_path(str(Path(__file__).with_name("vis_7x7_binary.py")), run_name="__main__")
