#!/bin/sh
python translate_pypy.py --backend=llvm --text --batch targetpypystandalone $*
