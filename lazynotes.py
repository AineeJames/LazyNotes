import cv2
import time  # for framerate
import numpy as np
from tqdm import tqdm
from os import listdir, remove
from os.path import isfile, join
from difPy import dif
import subprocess
import math

# get a list of all the files to process
onlyfiles = [f for f in listdir("slides") if isfile(join("slides", f))]
print(f"Number of files to capture: {len(onlyfiles)}")

# clear the extracted directory
extfiles = [f for f in listdir("extracted") if isfile(join("extracted", f))]
print(f"Clearing {len(extfiles)} files in the ./extracted directory...")
for i in range(len(extfiles)):
    remove(f"extracted/{extfiles[i]}")

# remove output file if it exists
try:
    print("Removing output file...")
    remove("output.png")
except:
    print("Output file not found, continuing...")

cropnum = 0

# box area threshholds
areaminthresh = 25_000  # best val so far:  75_000

print("Capturing boxes:")
for i in tqdm(range(len(onlyfiles))):

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

print("Deleting duplicate files, please wait...")
search = dif("extracted", delete=True, silent_del=True)

print("Running packer...")

args = [
    "python3",
    "packer.py",
    "--input_dir",
    "extracted",
    "--width",
    "4000",
    "--aspect",
    f"{math.sqrt(2)}",
    "--border",
    "3"
]
subprocess.run(args)