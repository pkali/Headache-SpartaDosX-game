#!/usr/bin/env python3

import sys
import argparse
from PIL import Image
import PIL.ImageOps  
import array
import progressbar

parser = argparse.ArgumentParser(description='Generate ATASCII from 2 col bitmap.')
parser.add_argument('-c','--charset', required=True, help='Atari charset (1KiB binary file)')
parser.add_argument('-b','--bitmap', required=True, help='Bitmap file (320x200, 1bit)')
parser.add_argument('-o','--output', required=True, help='Output ATASCII file')
parser.add_argument('-i','--inverse', action="store_true", help='Inverse bits of the source picture')

args = parser.parse_args()

#forbidden INTERNAL code charactes
forbidden = [27+64, 28+64, 29+64, 30+64, 31+64,  125, 126, 127, 155+64, 156+64, 157+64, 158+64, 159+64, 253, 254, 255]


def compare_bitmaps(a,b):
    #by size of bitmap a
    mx = a.size[0]
    my = a.size[1]
    pa = a.load()
    pb = b.load()
    result = 0
    for x in range(mx):
        for y in range(my):
            if pa[x,y] == pb[x,y]:
                result += 1
            else:
                result -= 1
    return result
                




with open(args.charset, "rb") as f:
    byt = f.read(1024)

full_charset = bytes(byt)
#inverse video
for integer in byt:
    full_charset += (~integer & 0xff).to_bytes(1, byteorder='big', signed=False) 

#2KiB atari charset with inverse video loaded into full_charset now

# convert it into 256 Image objects
chars = []
for i in range(256):
    src_char = full_charset[i*8:(i+1)*8]
    im = Image.new("1", (8,8), color=0)
    px = im.load()
    y=0
    for byte in src_char:
        for bit in range(8):
            pixel = (byte >> bit) & 1
            #pixels are coming from right to left!!!
            if pixel==1:
                px[7-bit,y] = (1,1,1)
        y += 1
    chars.append(im)


#load picture
bitmap = Image.open(args.bitmap).convert('1')

if args.inverse:
    im = bitmap.convert('L')
    im = PIL.ImageOps.invert(im)
    bitmap = im.convert('1')

#print(bitmap.size)
#bitmap.show()
xbytes = bitmap.size[0] // 8
ybytes = bitmap.size[1] // 8

bar = progressbar.ProgressBar()

px = bitmap.load()
result = []
for y in bar(range(ybytes)):
    line = []
    for x in range(xbytes):
        im = bitmap.crop((x*8,y*8,(x+1)*8,(y+1)*8))
        similarity = []
        for char in chars:
            similarity.append(compare_bitmaps(char, im))
        
        
        best = similarity.index(max(similarity))
        if best in forbidden:
            #need second largest
            bests = {similarity[i]:i for i in range(len(similarity))} #conversion do dict
            for simil in sorted(bests, reverse=True):
                best = bests[simil]
                if best not in forbidden:
                    break
        line.append(best)
    result.append(line)


#write binary result
bin_array = array.array('B')
for line in result:
    for char in line:
        #conver INTERNAL code to ATASCII
        if 64 <= char <= 95 or 64+128 <= char <= 95+128:
            char -= 64
        elif 0 <= char <= 63 or 0+128 <= char <= 63+128:
            char += 32
        bin_array.append(char)
    bin_array.append(155) #ATASCII EOL

with open(args.output, 'wb') as f:
    bin_array.tofile(f)
