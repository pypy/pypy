#!/bin/sh
export RTYPERORDER=order,module-list.pedronis 
# stopping on the first error
#python translate_pypy.py -no-c -no-o -text -fork2
# running it all 
#python translate_pypy.py target_pypy-llvm -text -llvm $*
python translate_pypy_new.py targetpypystandalone --backend=llvm --pygame --batch --fork=fork2 $*


# How to work in parallel:
# There is an environment variable to be set with your personal random seed.
# Seeds taken so far are
# Armin: 42, Samuele: 46, Chris: 49, Arre: 97, hpk/rxe: 23
# Under Windows, use
# SET RTYPERSEED=xx
# where xx is your seed. When you run translate_pypy, you will get a message
# with your seed, if everything is fine. The purpose of the seed is to
# shuffle the annotated blocks, in order to create different errors.

# To get the above RTYPER problems, do:: 

#     RTYPERORDER=order,SOMEFILE 
#     # stopping on the first error
#     python translate_pypy.py -no-c -no-o -fork -text  -t-insist

#     # seeing things in the graph
#     python translate_pypy.py -no-c -no-o 

# In the SOMEFILE you put: 
#     pypy.rpython.rarithmetic.ovfcheck_float_to_int 
