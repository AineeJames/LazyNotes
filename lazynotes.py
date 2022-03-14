import cv2
import time  # for framerate
import numpy as np
from tqdm import tqdm
from os import listdir, remove
from os.path import isfile, join, isdir
from difPy import dif
import subprocess
import math
import glob
from pathlib import Path
from fpdf import FPDF
import sys
import tkinter as tk
import PySimpleGUI as sg

sg.theme('DarkGrey3')

# All the stuff inside your window.
layout = [  [sg.Text("Choose a file..."), sg.FileBrowse(file_types = (("PDF Files", "*.pdf"),), key = '-INPDF-')],
            [sg.Button('Confirm Selection', key = '-CONFIRMPDF-')] ]

# Create the Window
window = sg.Window('LazyNotes', layout, element_justification='c')
 
# Event Loop to process "events" and get the "values" of the inputs
while True:

    event, values = window.Read()

    if event == sg.WIN_CLOSED: # if user closes window or clicks cancel
        break

    if event == '-CONFIRMPDF-':
        pdffilepath = values['-INPDF-']  
        print(f"chosen: {pdffilepath}")

window.close()