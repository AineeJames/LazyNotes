import cv2
import time # for framerate
import numpy as np
from tqdm import tqdm
from os import listdir
from os.path import isfile, join
from difPy import dif
import subprocess
import math

onlyfiles = [f for f in listdir("slides") if isfile(join("slides", f))]
print(f"Number of files to capture: {len(onlyfiles)}")

cropnum = 0

for i in tqdm(range(len(onlyfiles))):

    img = cv2.imread(f"slides/{onlyfiles[i]}", cv2.IMREAD_UNCHANGED)
    
    #print('Original Dimensions : ',img.shape)
    
    scale_percent = 20 # percent of original size
    width = int(img.shape[1] * scale_percent / 100)
    height = int(img.shape[0] * scale_percent / 100)
    dim = (width, height)
    
    # resize image
    img = cv2.resize(img, dim, interpolation = cv2.INTER_AREA)
    #print('New Dimensions : ',img.shape)

    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

    thresh_inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)[1]

    # Blur the image
    blur = cv2.GaussianBlur(thresh_inv,(1,1),0)

    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]
    # cv2.imshow("thresh", thresh)

    # find contours
    contours = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]

    mask = np.ones(img.shape[:2], dtype="uint8") * 255
    for c in contours:
        # get the bounding rect
        x, y, w, h = cv2.boundingRect(c)
        if w*h>25000/3:
            cv2.rectangle(mask, (x, y), (x+w, y+h), (0, 0, 255), -1)
            # print(f"x: {x}, y: {y}, w: {w}, h: {h}\n")
            cropped_box = img[y:y+h, x:x+w]
            
            cropnum += 1
            cv2.imwrite(f"extracted/crop_{cropnum}.jpg", cropped_box)

            # cv2.imshow("crop", cropped_box)
            # cv2.waitKey(0)

    res_final = cv2.bitwise_and(img, img, mask=cv2.bitwise_not(mask))

print(f"Produced {cropnum} cropped images.")

print("Deleting duplicate files, please wait...")
search = dif("extracted", delete=True, silent_del=True)

print("Running packer...")
args = ['python3', 'packer.py', '--input_dir', 'extracted', '--width', '2500', '--aspect', f'{math.sqrt(2)}', '--border', '3']
subprocess.run(args)

    # cv2.imshow("boxes", mask)
    # cv2.imshow("final image", res_final)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()