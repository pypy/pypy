import sys
from ctypes import *

# __________ the standard C library __________

# LoadLibrary is deprecated in ctypes, this should be removed at some point
if "load" in dir(cdll):
    cdll_load = cdll.load
else:
    cdll_load = cdll.LoadLibrary

if sys.platform == 'win32':
    libc = cdll_load('msvcrt.dll')
elif sys.platform == 'linux2':
    libc = cdll_load('libc.so.6')
elif sys.platform == 'darwin':
    libc = cdll_load('libc.dylib') 
else:
    raise ImportError("don't know how to load the c lib for %s" % sys.platform)
# ____________________________________________


