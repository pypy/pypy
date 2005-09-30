#!/bin/sh
export RTYPERORDER=order,module-list.pedronis 
python translate_pypy_new.py targetpypystandalone --backend=llvm --text --batch --no-run $*
