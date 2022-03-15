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
    zoom_x = 2.0  # horizontal zoom
    zoom_y = 2.0  # vertical zoom
    mat = fitz.Matrix(zoom_x, zoom_y)
    doc = fitz.open(pdfpath)
    outputpath = Path.cwd() / 'pdftoimg'
    try:
        outputpath.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        pass
    for f in listdir(outputpath):
        remove(join(outputpath, f))
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        pix.save(outputpath / f"page-{page.number}.png")
    window['-ML-'+sg.WRITE_ONLY_KEY].print("Completed conversion...")
    imgcrop(outputpath)

def imgcrop(imgpath):
    extractedpath = Path.cwd() / 'extracted' 
    window['-ML-'+sg.WRITE_ONLY_KEY].print(f"Extracting boxes to {extractedpath}...")
    try:
        extractedpath.mkdir(parents=True, exist_ok=False) 
    except FileExistsError:
        pass
    window['-ML-'+sg.WRITE_ONLY_KEY].print("Clearing extracted directory...")
    for f in listdir(extractedpath):
        remove(join(extractedpath, f))

    # get a list of all the files to process
    onlyfiles = [f for f in listdir(imgpath) if isfile(join(imgpath, f))]
    window['-ML-'+sg.WRITE_ONLY_KEY].print(f"Finding boxes in {len(onlyfiles)} files...")

    cropnum = 0
    # box area threshholds
    areaminthresh = 25_000  # best val so far:  25_000
    for i in range(len(onlyfiles)):

        # read img path and process the image
        currimgpath = imgpath / onlyfiles[i]
        img = cv2.imread(str(currimgpath), cv2.IMREAD_UNCHANGED)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh_inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        blur = cv2.GaussianBlur(thresh_inv, (1, 1), 0)
        thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        contours = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]

        mask = np.ones(img.shape[:2], dtype="uint8") * 255
        for c in contours:

            # estimate the number of sides based on the contour
            peri = cv2.arcLength(c, True) 
            vertices = cv2.approxPolyDP(c, 0.02 * peri, True)
            sides = len(vertices) 

            # get the bounding rect
            x, y, w, h = cv2.boundingRect(c)

            if w * h > areaminthresh and sides == 4:

                cv2.rectangle(mask, (x, y), (x + w, y + h), (0, 0, 255), -1)
                cropped_box = img[y : y + h, x : x + w]

                cropnum += 1

                # scale the cropped box back up for output
                scale_percent = 125
                width = int(cropped_box.shape[1] * scale_percent / 100)
                height = int(cropped_box.shape[0] * scale_percent / 100)
                dim = (width, height)
                cropped_box_sized = cv2.resize(cropped_box, dim, interpolation = cv2.INTER_AREA)

                extractedimgpath = Path.cwd() / 'extracted' / f"crop_{cropnum}.jpg"
                cv2.imwrite(str(extractedimgpath), cropped_box_sized)

# DarkGrey14
sg.theme('DarkGrey14')

# All the stuff inside your window.
layout = [  [sg.Text("Choose a *.pdf file to process...", font = ("Bahnschrift", 12)), sg.FileBrowse(file_types = (("PDF Files", "*.pdf"),), key = '-INPDF-', font = ("Bahnschrift", 12))],
            [sg.Button('Confirm Selection', key = '-CONFIRMPDF-', font = ("Bahnschrift", 12))],
            [sg.MLine(key='-ML-'+ sg.WRITE_ONLY_KEY, size=(100, 8), font = ("Bahnschrift", 10))]  ]

# Create the Window
window = sg.Window('LazyNotes', layout, element_justification='c')

# window['-ML-'+sg.WRITE_ONLY_KEY].print('\n', end='')
 
# Event Loop to process "events" and get the "values" of the inputs
while True:

    event, values = window.Read()

    if event == sg.WIN_CLOSED: # if user closes window or clicks cancel
        break

    if event == '-CONFIRMPDF-' and values['-INPDF-'] != "":  
        window['-ML-'+sg.WRITE_ONLY_KEY].print(f"Converting {values['-INPDF-']} to images...")
        threading.Thread(target=pdftoimg, args=(values['-INPDF-'],), daemon=True).start()
    elif event == '-CONFIRMPDF-' and values['-INPDF-'] == "":
        window['-ML-'+sg.WRITE_ONLY_KEY].print("Please select the PDF you wish to process...", text_color='red')

window.close()