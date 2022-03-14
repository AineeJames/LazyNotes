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
import fitz

def pdftoimg(pdfpath):
    doc = fitz.open(pdfpath)
    for page in doc:
        pix = page.get_pixmap()
        pix.save("page-%i.png" % page.number)

sg.theme('Black')

# All the stuff inside your window.
layout = [  [sg.Text("Choose a file..."), sg.FileBrowse(file_types = (("PDF Files", "*.pdf"),), key = '-INPDF-')],
            [sg.Button('Confirm Selection', key = '-CONFIRMPDF-')],
            [sg.Output(size=(100,10), key='-PRGMOUT-')]  ]

# Create the Window
window = sg.Window('LazyNotes', layout, element_justification='c')
 
# Event Loop to process "events" and get the "values" of the inputs
while True:

    event, values = window.Read()

    if event == sg.WIN_CLOSED: # if user closes window or clicks cancel
        break

    if event == '-CONFIRMPDF-' and values['-INPDF-'] != "":  
        print(f"Converting {values['-INPDF-']} to images...")
        pdftoimg(values['-INPDF-'])
    elif event == '-CONFIRMPDF-' and values['-INPDF-'] == "":
        print("Please select the PDF you wish to process...")

window.close()