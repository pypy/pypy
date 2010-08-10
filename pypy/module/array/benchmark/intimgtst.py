#!/usr/bin/python
from time import time

from array import array, simple_array

def f(img, intimg):
    l=0
    i=640    
    while i<640*480:
        l+=img[i]
        intimg[i]=intimg[i-640]+l
        i+=1
    return l



if True:
    img=array('d','\x00'*640*480*8)
    intimg=array('d','\x00'*640*480*8)
else:
    img=simple_array(640*480)
    intimg=simple_array(640*480)

start=time()
for l in range(500): f(img, intimg)
print time()-start
