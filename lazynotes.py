import cv2
import time  # for framerate
import numpy as np
from tqdm import tqdm
from os import listdir, remove
from os.path import isfile, join
from difPy import dif
import subprocess
import math
import glob
from pathlib import Path
from fpdf import FPDF
import sys
pdf = FPDF() # initialize pdf library

# create output path
path = Path.cwd() / 'output' 
try:
    path.mkdir(parents=True, exist_ok=False)
except FileExistsError:
    print("Output folder is already there")
else:
    print("Output folder was created")

# get a list of all the files to process
onlyfiles = [f for f in listdir("slides") if isfile(join("slides", f))]
print(f"Number of files to capture: {len(onlyfiles)}")

# clear the extracted directory
extfiles = [f for f in listdir("extracted") if isfile(join("extracted", f))]
print(f"Clearing {len(extfiles)} files in the ./extracted directory...")
for i in range(len(extfiles)):
    remove(f"extracted/{extfiles[i]}")


for filename in glob.glob("./output/output*"):
    remove(filename) 

cropnum = 0

# box area threshholds
areaminthresh = 25_000  # best val so far:  75_000

print("Capturing boxes:")
for i in tqdm(range(len(onlyfiles)), colour="blue"):

    img = cv2.imread(f"slides/{onlyfiles[i]}", cv2.IMREAD_UNCHANGED)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    thresh_inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # Blur the image
    blur = cv2.GaussianBlur(thresh_inv, (1, 1), 0)

    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    # cv2.imshow("thresh", thresh)

    # find contours
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

            cv2.imwrite(f"extracted/crop_{cropnum}.jpg", cropped_box_sized)

    res_final = cv2.bitwise_and(img, img, mask=cv2.bitwise_not(mask))

print(f"Produced {cropnum} cropped images.")

search = dif("extracted", delete=True, silent_del=True)

# let user approve or deny image
extractedfiles = [(f, "none") for f in listdir("extracted/") if isfile(join("extracted/", f))] # ("file", ' ')
print(f"Number of files to approve: {len(extractedfiles)}")
print("\nInstructions:")
print("\ty = keep file\n\tn = exclude file from note sheet")
print("\t, (<) = go back to the previous imgage\n\t. (>) = move to the next image")
print("\tenter = confirm selections\n")

currFile = 0
while True:
    imagepath = Path.cwd() / "extracted" / extractedfiles[currFile][0]
    currimage = cv2.imread(str(imagepath), cv2.IMREAD_UNCHANGED)
    cv2.putText(currimage, f"Selection: {extractedfiles[currFile][1]}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, 2)
    cv2.imshow(str(imagepath), currimage)
    res = cv2.waitKey(0) & 0xFF
    cv2.destroyAllWindows()

    if (res == ord(',')): # left arrow key
        if (currFile != 0):
            currFile -= 1
        else:
            print("cannot go back, at first image")

    elif (res == ord('.')): # right arrow key
        if (currFile != len(extractedfiles) - 1):
            currFile += 1
        else:
            print("reached the end, hit enter to generate note sheet")

    elif (res == ord('y')):
        tuplelist = list(extractedfiles[currFile])
        tuplelist[1] = "keep"
        extractedfiles[currFile] = tuple(tuplelist)
        if (currFile != len(extractedfiles) - 1):
            currFile += 1
        else:
            print("reached the end, hit enter to generate note sheet")

    elif (res == ord('n')):
        tuplelist = list(extractedfiles[currFile])
        tuplelist[1] = "exclude"
        extractedfiles[currFile] = tuple(tuplelist)
        if (currFile != len(extractedfiles) - 1):
            currFile += 1
        else:
            print("reached the end, hit enter to generate note sheet")

    elif (res == 13): # enter key
        noneCount = 0
        for f in range(len(extractedfiles)):
            imagepath = Path.cwd() / "extracted" / extractedfiles[f][0]
            if (extractedfiles[f][1] == "none"):
                noneCount += 1
                print(f"Provide a selection for {imagepath}")
                currFile = f
                break
        if (noneCount == 0):
            break
            
cv2. destroyAllWindows()   

# TODO delete all y files to extracted
for f in range(len(extractedfiles)):
    imagepath = Path.cwd() / "extracted" / extractedfiles[f][0]
    if (extractedfiles[f][1] == "exclude"):
        print(f"Removing: {imagepath}")
        remove(imagepath)

print("Running packer...")
args = [
    f"{sys.executable}",
    "packer.py",
    "--input_dir",
    "extracted",
    "--width",
    "4000",
    "--aspect",
    f"{math.sqrt(2)}",
    "--border",
    "3",
    "--output",
    "output/output.png"
]
subprocess.run(args)

print("Creating pdf...")
outfiles = [f for f in listdir("output") if isfile(join("output", f))]
for file in outfiles:
    filepath = Path.cwd() / "output" / file
    pdf.add_page()
    pdf.image(str(filepath), 0, 0, 210, 297)
pdfpath = Path.cwd() / "output" / "output.pdf"
pdf.output(pdfpath, "F")
