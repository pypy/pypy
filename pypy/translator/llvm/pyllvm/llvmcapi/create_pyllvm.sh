#!/bin/bash

python setup.py build_ext -i -q

if [ -f ~/projects/ctypes/ctypes/wrap/h2xml.py ] 
then 
    python ~/projects/ctypes/ctypes/wrap/h2xml.py llvmcapi.h -q -I . -o llvmcapi.xml
    python ~/projects/ctypes/ctypes/wrap/xml2py.py llvmcapi.xml -l llvmcapi.so -o pyllvm.tmp
    sed -e s/from\ ctypes\ import/from\ cc\ import/ pyllvm.tmp > pyllvm.py
    rm -f pyllvm.tmp llvmcapi.xml
fi
