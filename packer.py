import cv2
# import rpack
import os
import glob
from rectpack import newPacker
import pickle
import numpy as np
import argparse
parser = argparse.ArgumentParser(description='Montage creator with rectpack')
parser.add_argument('--width', help='Output image width', default=5200, type=int)
parser.add_argument('--aspect', help='Output image aspect ratio, \
    e.g. height = <width> * <aspect>', default=1.0, type=float)
parser.add_argument('--output', help='Output image name', default='output.png')
parser.add_argument('--input_dir', help='Input directory with images', default='./')
parser.add_argument('--debug', help='Draw "debug" info', default=False, type=bool)
parser.add_argument('--border', help='Border around images in px', default=2, type=int)
args = parser.parse_args()
files = sum([glob.glob(os.path.join(args.input_dir, '*.' + e)) for e in ['jpg', 'jpeg', 'png']], [])
print('found %d files in %s' % (len(files), args.input_dir))
print('getting images sizes...')
for count in range(100):
    sizes = [(im_file, cv2.imread(im_file).shape) for im_file in files]
    # NOTE: you could pick a different packing algo by setting pack_algo=..., e.g. pack_algo=rectpack.SkylineBlWm
    packer = newPacker(rotation=False)
    for i, r in enumerate(sizes):
        packer.add_rect(r[1][1] + args.border * 2, r[1][0] + args.border * 2, rid=i)
    out_w = args.width
    aspect_ratio_wh = args.aspect
    out_h = int(out_w * aspect_ratio_wh)
    packer.add_bin(out_w, out_h)
    print('packing...')
    packer.pack()
    output_im = np.full((out_h, out_w, 3), 255, np.uint8)
    used = []
    for rect in packer.rect_list():
        b, x, y, w, h, rid = rect
        orig_file_name = sizes[rid][0]
        used.append(orig_file_name)
        im = cv2.imread(orig_file_name, cv2.IMREAD_COLOR)
        output_im[out_h - y - h + args.border : out_h - y - args.border, x + args.border:x+w - args.border] = im
        if args.debug:
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
    print('used %d of %d images' % (len(used), len(files)))
    files = unusedfiles
    filename = f"{(args.output).split('.')[0]}_{count}.png"
    print(f'writing image output as {filename}:...')
    cv2.imwrite(filename, output_im)
    if(len(files) == 0):
        print("Out of images")
        break
print('done.')
