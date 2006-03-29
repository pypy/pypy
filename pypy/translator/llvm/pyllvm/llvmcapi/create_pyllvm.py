#!/usr/bin/env python
import os

os.system("python setup.py build_ext -i -q")

WRAPDIR = "/Users/eric/projects/ctypes/ctypes/wrap" #XXX get rid of this hardcoded path

if os.path.exists(WRAPDIR + "/h2xml.py"):
    os.system("python " + WRAPDIR + "/h2xml.py lib/llvmcapi.h -q -I . -o llvmcapi.xml")
    os.system("python " + WRAPDIR + "/xml2py.py llvmcapi.xml -l llvmcapi.so -o pyllvm.tmp")
    os.system("sed -e s/from\ ctypes\ import/from\ cc\ import/ pyllvm.tmp > pyllvm.py")
    os.system("rm -f pyllvm.tmp llvmcapi.xml")
    print "created pyllvm.py"
else:
    print "skipping pyllvm.py creation"
