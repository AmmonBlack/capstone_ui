from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, FigureCanvasAgg
import matplotlib, time, sys, pickle
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import PySimpleGUI as sg
import numpy as np
from capstone_ui import Pressure_Test_UI

test = Pressure_Test_UI()

# Check the true and Falses (NOT IMPLEMENTED) # This could be cleaned up <<<<<<<<<<<<<<<<<<<<<<<<<
test_layout = test.make_timer_layout()
test_layout.extend(test.make_plot_layout())
print(test_layout)

test_window = sg.Window("Test Window", test_layout, finalize=True)
start_time = int(round(time.time() * 100))

while True:
    current_time = int(round(time.time() * 100)) - start_time
    event, values = test_window.read(timeout=10)
    test._timer_checker(test_window, event, values, current_time)
