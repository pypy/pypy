#!/usr/bin/env python
import os

WRAPDIR = "/Users/eric/projects/ctypes/ctypes/wrap" #XXX get rid of this hardcoded path

if os.path.exists(WRAPDIR + "/h2xml.py"):
    print "creating llvmcapi.py"
    os.system("python " + WRAPDIR + "/h2xml.py ../llvmcapi/include/llvmcapi.h -q -I . -o llvmcapi.xml")
    os.system("python " + WRAPDIR + "/xml2py.py llvmcapi.xml -l ../llvmcapi/llvmcapi.so -o llvmcapi.tmp")
    os.system("sed -e s/from\ ctypes\ import/from\ cc\ import/ llvmcapi.tmp > llvmcapi.py")
    os.system("rm -f llvmcapi.tmp llvmcapi.xml")
    print "done"
else:
    print "skipping llvmcapi.py creation"
