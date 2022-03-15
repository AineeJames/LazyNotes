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
import io
from PIL import Image

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
        window['-PROG-'].update(page.number+1, len(doc))
        window['-BARPERCENT-'].update(f"{int(page.number/len(doc) * 100)}%")
        pix = page.get_pixmap(matrix=mat)
        pix.save(outputpath / f"page-{page.number}.png")
    window['-PROG-'].update(0, 1)
    window['-BARPERCENT-'].update("0%")
    window['-ML-'+sg.WRITE_ONLY_KEY].print("Completed conversion...")
    imgcrop(outputpath)
    window.write_event_value('-THREAD DONE-', 'done')

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
    window['-ML-'+sg.WRITE_ONLY_KEY].print(f"Searching for boxes in {len(onlyfiles)} files...")

    cropnum = 0
    # box area threshholds
    areaminthresh = 25_000  # best val so far:  25_000
    for i in range(len(onlyfiles)):

        window['-PROG-'].update(i+1, len(onlyfiles))
        window['-BARPERCENT-'].update(f"{int(i/len(onlyfiles) * 100)}%")

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

                extractedimgpath = Path.cwd() / 'extracted' / f"crop_{cropnum}.png"
                cv2.imwrite(str(extractedimgpath), cropped_box_sized)

    window['-PROG-'].update(0, 1)
    window['-BARPERCENT-'].update("0%")

    window['-ML-'+sg.WRITE_ONLY_KEY].print(f"Produced {cropnum} boxes...")
    window['-ML-'+sg.WRITE_ONLY_KEY].print(f"Removing duplicate boxes...")
    search = dif(str(extractedpath), delete=True, silent_del=True, show_output=False)
    window['-ML-'+sg.WRITE_ONLY_KEY].print(f"Done removing duplicates...")

def printinstructs():
    window['-ML-'+sg.WRITE_ONLY_KEY].print("\nInstructions:", text_color='lightblue')
    window['-ML-'+sg.WRITE_ONLY_KEY].print("\ty = keep file\n\tn = exclude file from note sheet", text_color='lightblue')
    window['-ML-'+sg.WRITE_ONLY_KEY].print("\t< = go back to the previous imgage\n\t> = move to the next image", text_color='lightblue')
    window['-ML-'+sg.WRITE_ONLY_KEY].print("\tq = quit selection, all files are considered", text_color='lightblue')
    window['-ML-'+sg.WRITE_ONLY_KEY].print("\tenter = confirm selections", text_color='lightblue')

def getextractednum():
    extractedpath = Path.cwd() / 'extracted' 
    num = len(listdir(extractedpath))
    return num

def handleselection():
    while True:
        extpath = Path.cwd() / 'extracted'
        extfiles = [f for f in listdir(str(extpath)) if isfile(join(str(extpath), f))]
        box_path = Path.cwd() / 'extracted' / extfiles[currfilenum]
        image = Image.open(box_path)
        image.thumbnail((700, 700))
        bio = io.BytesIO()
        image.save(bio, format="PNG")
        window["-BOXIMAGE-"].update(data=bio.getvalue())

currfilenum = 0

# DarkGrey14
sg.theme('DarkGrey14')

# All the stuff inside your window.
layout = [  [sg.Text("LazyNotes Notesheet Generator", font = ("Bahnschrift", 30))],
            [sg.Text("Choose a *.pdf file to process...", font = ("Bahnschrift", 12)), sg.FileBrowse(file_types = (("PDF Files", "*.pdf"),), key = '-INPDF-', font = ("Bahnschrift", 12))],
            [sg.Button('Confirm Selection', key = '-CONFIRMPDF-', font = ("Bahnschrift", 12))],
            [sg.MLine(key='-ML-'+ sg.WRITE_ONLY_KEY, size=(100, 8), font = ("Bahnschrift", 10))], 
            [sg.ProgressBar(1, orientation='h', size=(20,20), key='-PROG-'), sg.Text("0%", key = "-BARPERCENT-", font = ("Bahnschrift", 10))],
            [sg.Image('', size=(0,0), key = "-BOXIMAGE-")]  ]

# Create the Window
window = sg.Window('LazyNotes', layout, element_justification='c', return_keyboard_events=True, use_default_focus=False)

# Event Loop to process "events" and get the "values" of the inputs
while True:

    event, values = window.Read()

    if event == sg.WIN_CLOSED: # if user closes window or clicks cancel
        break

    if len(event) == 1: # keyboard input
        numoffiles = getextractednum()
        if (event == 'y'):
            fileselectlist[currfilenum - 1] = 'y'
            if (currfilenum < numoffiles - 1):
                currfilenum += 1
        elif (event == 'n'):
            fileselectlist[currfilenum - 1] = 'n'
            if (currfilenum < numoffiles - 1):
                currfilenum += 1

    if event is not None: # handle arrow keys
        numoffiles = getextractednum()
        if (event == "Right:39" and currfilenum < numoffiles - 1):
            currfilenum += 1
        elif (event == "Left:37" and currfilenum > 0):
            currfilenum -= 1

    if event == '-CONFIRMPDF-' and values['-INPDF-'] != "":  
        window['-ML-'+sg.WRITE_ONLY_KEY].print(f"Converting {values['-INPDF-']} to images...")
        threading.Thread(target=pdftoimg, args=(values['-INPDF-'],), daemon=True).start()
    elif event == '-CONFIRMPDF-' and values['-INPDF-'] == "":
        window['-ML-'+sg.WRITE_ONLY_KEY].print("Please select the PDF you wish to process...", text_color='red')

    if event == '-THREAD DONE-':
        printinstructs()
        fileselectlist = [None] * getextractednum()
        threading.Thread(target=handleselection, daemon=True).start()

window.close()