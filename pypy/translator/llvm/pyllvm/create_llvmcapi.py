#!/usr/bin/env python
import os

WRAPDIR = "/Users/eric/projects/ctypes/ctypes/wrap" #XXX get rid of this hardcoded path

if os.path.exists(WRAPDIR + "/h2xml.py"):
    print "h2xml.py"
    os.system("python " + WRAPDIR + "/h2xml.py ../llvmcapi/include/llvmcapi.h -q -I. -I/opt/local/include -D_GNU_SOURCE -D__STDC_LIMIT_MACROS -o llvmcapi.xml")
    print "xml2py.py"
    os.system("python " + WRAPDIR + "/xml2py.py llvmcapi.xml -l ../llvmcapi/llvmcapi.so -o llvmcapi.tmp1")
    print "massage output"
    os.system("sed -e s/from\ ctypes\ import/from\ cc\ import/ llvmcapi.tmp1 > llvmcapi.tmp2")
    os.system("sed -e s/assert\ alignment.*// llvmcapi.tmp2 > llvmcapi.py")
    print "cleanup some files"
    os.system("rm -f llvmcapi.tmp* llvmcapi.xml")
    print "created llvmcapi.py"
else:
    print "skipping llvmcapi.py creation"
