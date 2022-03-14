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
import logging
import threading

def pdftoimg(pdfpath):
    doc = fitz.open(pdfpath)
    outputpath = Path.cwd() / 'pdftoimg'
    try:
        outputpath.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        pass
    for f in listdir(outputpath):
        remove(join(outputpath, f))
    for page in doc:
        pix = page.get_pixmap()
        pix.save(outputpath / f"page-{page.number}.png")
    window['-ML-'+sg.WRITE_ONLY_KEY].print("Completed conversion...", text_color='green')

sg.theme('Black')

# All the stuff inside your window.
layout = [  [sg.Text("Choose a file..."), sg.FileBrowse(file_types = (("PDF Files", "*.pdf"),), key = '-INPDF-')],
            [sg.Button('Confirm Selection', key = '-CONFIRMPDF-')],
            [sg.MLine(key='-ML-'+ sg.WRITE_ONLY_KEY, size=(100, 8))]  ]

# Create the Window
window = sg.Window('LazyNotes', layout, element_justification='c')

# window['-ML-'+sg.WRITE_ONLY_KEY].print('\n', end='')
 
# Event Loop to process "events" and get the "values" of the inputs
while True:

    event, values = window.Read()

    if event == sg.WIN_CLOSED: # if user closes window or clicks cancel
        break

    if event == '-CONFIRMPDF-' and values['-INPDF-'] != "":  
        window['-ML-'+sg.WRITE_ONLY_KEY].print(f"Converting {values['-INPDF-']} to images...", text_color='green')
        threading.Thread(target=pdftoimg, args=(values['-INPDF-'],), daemon=True).start()
    elif event == '-CONFIRMPDF-' and values['-INPDF-'] == "":
        window['-ML-'+sg.WRITE_ONLY_KEY].print("Please select the PDF you wish to process...", text_color='red')

window.close()