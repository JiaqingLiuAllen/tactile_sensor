import matplotlib
import serial
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import threading
import queue
import time
import matplotlib.animation as animation

matplotlib.use('TkAgg')  # Use TkAgg backend for GUI

SERIAL_PORT = '/dev/cu.usbserial-0001'     # Change this based on your ESP32 port
BAUD_RATE = 250000       # Match the ESP32 code
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.05)

cmap = mcolors.LinearSegmentedColormap.from_list("custom", ["red", "yellow", "green"])  # Create a red-yellow-green gradient color map
fig, ax = plt.subplots()                   # Create the plot figure and axes
# HERE
matrix = np.zeros((3, 3))                  # Initialize an empty 4x4 matrix
heatmap = ax.imshow(matrix, cmap=cmap, vmin=0, vmax=3.3)  # Plot the heatmap with defined colormap and voltage range
cbar = plt.colorbar(heatmap, label="Voltage (V)")         # Add a colorbar legend to the side

# HERE
ax.set_xticks(np.arange(3))                             # Set X-axis ticks from 0 to 3
ax.set_yticks(np.arange(3))                             # Set Y-axis ticks from 0 to 3
ax.set_xticklabels(["CH1", "CH2", "CH3"])        # Label columns as CH1–CH4
ax.set_yticklabels(["CH1", "CH2", "CH3"])        # Label rows as CH1–CH4
plt.title("NxN Matrix Voltage Visualization")           # Add a title to the plot

cell_texts = [[ax.text(j, i, "", ha="center", va="center", color="black", fontsize=12)
               for j in range(3)] for i in range(4)]

data_queue = queue.Queue()

def update_plot(frame):                               # This function runs every 50 ms from the animation timer
    if not data_queue.empty():                        # If new matrix data is available
        new_matrix = data_queue.get()                 # Retrieve the newest matrix from the queue
        heatmap.set_data(new_matrix)                  # Update heatmap color data

        for i in range(3):                            # Loop over rows
            for j in range(3):                        # Loop over columns
                cell_texts[i][j].set_text(f"{new_matrix[i][j]:.2f}")  # Update cell text with 2 decimal places

    plt.draw()                                        # Redraw the figure

def read_arduino_data():                                           # Define a background function for continuous serial reading
    while True:                                                    # Infinite loop
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()  # Read a line from serial, decode it
            if "Matrix updated:" in line:                          # If the trigger line is received
                new_matrix = np.zeros((3, 3))                      # Initialize new matrix to fill

                for i in range(3):                                 # Expect 4 lines of row data
                    row_data = ser.readline().decode('utf-8', errors='ignore').strip().split(",")  # Read and split by comma
                    if len(row_data) == 3:                         # Ensure exactly 4 values per row
                        new_matrix[i] = [float(val) for val in row_data]  # Convert strings to floats and store

                data_queue.put(new_matrix)                         # Push the matrix into the data queue
        except Exception as e:                                     # If there's an error, print it
            print(f"Serial read error: {e}")                       # Print error to console

data_thread = threading.Thread(target=read_arduino_data, daemon=True)  # Create a daemon thread that runs serial reading
data_thread.start()                                                    # Start the thread

ani = animation.FuncAnimation(fig, update_plot, interval=50)  # Start the animation; update every 50ms (20Hz)
plt.show()                                                     # Show the matplotlib GUI window