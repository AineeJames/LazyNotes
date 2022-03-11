import cv2
import time # for framerate
import numpy as np
from tqdm import tqdm
from os import listdir
from os.path import isfile, join
import math

onlyfiles = [f for f in listdir("slides") if isfile(join("slides", f))]
print(f"Num of files to capture: {len(onlyfiles)}")

cropnum = 0

for i in tqdm(range(len(onlyfiles))):

    img = cv2.imread(f"slides/{onlyfiles[i]}", cv2.IMREAD_UNCHANGED)
    
    #print('Original Dimensions : ',img.shape)
    
    scale_percent = 50 # percent of original size
    width = int(img.shape[1] * scale_percent / 100)
    height = int(img.shape[0] * scale_percent / 100)
    dim = (width, height)
    
    # resize image
    img = cv2.resize(img, dim, interpolation = cv2.INTER_AREA)
    #print('New Dimensions : ',img.shape)

    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

    dst = cv2.Canny(gray, 50, 200, None, 3)
    
    # Copy edges to the images that will display the results in BGR
    cdst = cv2.cvtColor(dst, cv2.COLOR_GRAY2BGR)
    cdstP = np.copy(cdst)
    
    lines = cv2.HoughLines(dst, 1, np.pi / 180, 100, None, 0, 0)
    
    if lines is not None:
        for i in range(0, len(lines)):
            rho = lines[i][0][0]
            theta = lines[i][0][1]
            a = math.cos(theta)
            b = math.sin(theta)
            x0 = a * rho
            y0 = b * rho
            pt1 = (int(x0 + 1000*(-b)), int(y0 + 1000*(a)))
            pt2 = (int(x0 - 1000*(-b)), int(y0 - 1000*(a)))
            cv2.line(cdst, pt1, pt2, (0,0,255), 1, cv2.LINE_AA)

    cv2.imshow("dadn", cdst)
    cv2.waitKey(0)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    # cv2.imshow("boxes", mask)
    # cv2.imshow("final image", res_final)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()