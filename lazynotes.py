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
import threading
import io
from PIL import Image
from rectpack import newPacker
import pickle
import logging
logging.basicConfig(filename='log.txt', encoding='utf-8', level=logging.CRITICAL)

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

                extractedimgpath = Path.cwd() / 'extracted' / f"crop_{cropnum:06}.png"
                cv2.imwrite(str(extractedimgpath), cropped_box_sized)

    window['-PROG-'].update(0, 1)
    window['-BARPERCENT-'].update("0%")

    if (cropnum > 0):
        window['-ML-'+sg.WRITE_ONLY_KEY].print(f"Produced {cropnum} boxes...")
        window['-ML-'+sg.WRITE_ONLY_KEY].print(f"Removing duplicate boxes...")
        search = dif(str(extractedpath), delete=True, silent_del=True, show_output=False)
        window['-ML-'+sg.WRITE_ONLY_KEY].print(f"Done removing duplicates...")
    else:
        wprint("Could not find any boxes in the given .pdf...")
        wprint("Please try a different file...")

def printinstructs():
    window['-ML-'+sg.WRITE_ONLY_KEY].print("\nInstructions:", text_color='lightblue')
    window['-ML-'+sg.WRITE_ONLY_KEY].print("\ty = keep file\n\tn = exclude file from note sheet", text_color='lightblue')
    window['-ML-'+sg.WRITE_ONLY_KEY].print("\t< = go back to the previous imgage\n\t> = move to the next image", text_color='lightblue')
    window['-ML-'+sg.WRITE_ONLY_KEY].print("\tq = quit selection, all files are considered", text_color='lightblue')
    window['-ML-'+sg.WRITE_ONLY_KEY].print("\tg = confirm selections, and generate", text_color='lightblue')

def getextractednum():
    extractedpath = Path.cwd() / 'extracted' 
    num = len(listdir(extractedpath))
    return num

def handleselection():
    while not sel_done:
        if (user_can_input == True):
            extpath = Path.cwd() / 'extracted'
            extfiles = [f for f in listdir(str(extpath)) if isfile(join(str(extpath), f))]
            extfiles.sort()
            box_path = Path.cwd() / 'extracted' / extfiles[currfilenum]
            image = Image.open(box_path)
            image.thumbnail((700, 700))
            bio = io.BytesIO()
            image.save(bio, format="PNG")
            window["-BOXIMAGE-"].update(data=bio.getvalue())
            window["-SELECTION-"].update(f"Selection: {fileselectlist[currfilenum]}")
           
    window["-BOXIMAGE-"].update('')
    window["-SELECTION-"].update("")

def removeselected(select_list):
    extpath = Path.cwd() / 'extracted'
    extfiles = [f for f in listdir(str(extpath)) if isfile(join(str(extpath), f))]
    extfiles.sort()
    logging.info(f"After removal list: {extfiles}")
    for i, s in enumerate(select_list):
        if (s == 'exclude'):
            delpath = Path.cwd() / 'extracted' / extfiles[i]
            window['-ML-'+sg.WRITE_ONLY_KEY].print(f"Deleting {delpath}...")
            remove(delpath)

def wprint(message):
     window['-ML-'+sg.WRITE_ONLY_KEY].print(message)

def pack():

    outputpath = Path.cwd() / 'output' 
    try:
        outputpath.mkdir(parents=True, exist_ok=False) 
    except FileExistsError:
        pass
    window['-ML-'+sg.WRITE_ONLY_KEY].print("Clearing output directory...")
    for f in listdir(outputpath):
        remove(join(outputpath, f))

    input_dir = str(Path.cwd() / 'extracted')
    border = 3
    width = 4000
    aspect = math.sqrt(2)
    debug = False
    output_dir = str(Path.cwd() / 'output')

    files = sum([glob.glob(join(input_dir, '*.' + e)) for e in ['jpg', 'jpeg', 'png']], [])
    wprint('Found %d files in %s...' % (len(files), input_dir))
    wprint('Getting images sizes...')
    for count in range(100):
        sizes = [(im_file, cv2.imread(im_file).shape) for im_file in files]
        # NOTE: you could pick a different packing algo by setting pack_algo=..., e.g. pack_algo=rectpack.SkylineBlWm
        packer = newPacker(rotation=False)
        for i, r in enumerate(sizes):
            packer.add_rect(r[1][1] + border * 2, r[1][0] + border * 2, rid=i)
        out_w = width
        aspect_ratio_wh = aspect
        out_h = int(out_w * aspect_ratio_wh)
        packer.add_bin(out_w, out_h)
        wprint('Packing...')
        packer.pack()
        output_im = np.full((out_h, out_w, 3), 255, np.uint8)
        used = []
        for rect in packer.rect_list():
            b, x, y, w, h, rid = rect
            orig_file_name = sizes[rid][0]
            used.append(orig_file_name)
            im = cv2.imread(orig_file_name, cv2.IMREAD_COLOR)
            output_im[out_h - y - h + border : out_h - y - border, x + border:x+w - border] = im
            if debug:
                cv2.rectangle(output_im, (x,out_h - y - h), (x+w,out_h - y), (255,0,0), 3)
                cv2.putText(output_im, "%d"%rid, (x, out_h - y), cv2.FONT_HERSHEY_PLAIN, 3.0, (0,0,255), 2)
        unusedfiles = []
        for file in files:
            fileused = False
            for usedfile in used:
                if file == usedfile:
                    fileused = True
            if(not fileused):
                unusedfiles.append(file)
        wprint('Used %d of %d images...' % (len(used), len(files)))
        files = unusedfiles
        filename = str(Path.cwd() / 'output' / f'out_{count}.png')
        # filename = f"{output_dir}out_{count}.png"
        # filename = f"{(output).split('.')[0]}_{count}.png"
        wprint(f'Writing image output as {filename}...')
        cv2.imwrite(filename, output_im)
        if(len(files) == 0):
            wprint("Packer ran out of images...")
            break
    wprint('Done packing...')

currfilenum = 0
user_can_input = False
sel_done = False

# DarkGrey14
sg.theme('DarkGrey14')

# All the stuff inside your window.
layout = [  [sg.Text("LazyNotes Notesheet Generator", font = ("Bahnschrift", 30))],
            [sg.Text("Choose a *.pdf file to process...", font = ("Bahnschrift", 12)), sg.FileBrowse(file_types = (("PDF Files", "*.pdf"),), key = '-INPDF-', font = ("Bahnschrift", 12))],
            [sg.Button('Confirm Selection', key = '-CONFIRMPDF-', font = ("Bahnschrift", 12))],
            [sg.MLine(key='-ML-'+ sg.WRITE_ONLY_KEY, size=(100, 8), font = ("Bahnschrift", 10))], 
            [sg.ProgressBar(1, orientation='h', size=(20,20), key='-PROG-'), sg.Text("0%", key = "-BARPERCENT-", font = ("Bahnschrift", 10))],
            [sg.Image('', size=(0,0), key = "-BOXIMAGE-")],
            [sg.Text('', font = ("Bahnschrift", 12), key = '-SELECTION-' )]  ]

# Create the Window
window = sg.Window('LazyNotes', layout, element_justification='c', return_keyboard_events=True, use_default_focus=False)

# Event Loop to process "events" and get the "values" of the inputs
while True:

    event, values = window.Read()
    print(event)

    if event == sg.WIN_CLOSED: # if user closes window or clicks cancel
        break

    if len(event) == 1 and user_can_input == True: # keyboard input
        numoffiles = getextractednum()
        if (event == 'y'):
            fileselectlist[currfilenum] = 'keep'
            if (currfilenum < numoffiles - 1):
                currfilenum += 1
        elif (event == 'n'):
            fileselectlist[currfilenum] = 'exclude'
            if (currfilenum < numoffiles - 1):
                currfilenum += 1
        elif (event == 'q'):
            sel_done = True
            user_can_input == False
            window['-ML-'+sg.WRITE_ONLY_KEY].print(f"Ignoring selection, considering all boxes for note sheet...")
            pack()
        elif (event == 'g'):
            unselected_box = False
            for i, s in enumerate(fileselectlist):
                if (s == 'no selection'):
                    unselected_box = True
                    currfilenum = i
                    print(f"no selection for index: {i}")
                    window['-ML-'+sg.WRITE_ONLY_KEY].print(f"Please provide a selection for this image...")
                    printinstructs()
                    break
            if (unselected_box == False):
                user_can_input == False
                sel_done = True
                removeselected(fileselectlist)
                pack()

    if event is not None and user_can_input == True: # handle arrow keys
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
        fileselectlist = ['no selection'] * getextractednum()
        user_can_input = True
        threading.Thread(target=handleselection, daemon=True).start()

window.close()