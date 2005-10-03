#!/bin/sh
#export RTYPERORDER=order,module-list.pedronis 
python translate_pypy.py targetpypystandalone --backend=llvm --text --batch $*
