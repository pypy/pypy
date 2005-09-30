#!/bin/sh
export RTYPERORDER=order,module-list.pedronis 
python translate_pypy.py targetpypystandalone -o -llvm -boehm -text -batch -fork2 $*
