import py
import os
import sys

from pypy.translator.llvm2.genllvm import compile_function
from pypy.translator.translator import Translator

def p():
    print 'Running on top of CPython:'
    entry_point()

def c():
    print "Running genc'd version on top of CPython:"
    t = Translator(entry_point)    
    a = t.annotate([])
    t.specialize()
    f = t.ccompile()
    f()

def l(name):
    compile_function(entry_point, [])

    # generate runnable bytecode with the following command
    print 'Generating standalone LLVM bytecode:'
    cmd = "llvmc -O5 -Tasm=-enable-correct-eh-support -v -L /usr/lib/ -lm -lgc /tmp/usession-current/main_optimized.bc -o %s" % name
    print cmd
    os.system(cmd)

    # run with the following command
    print 'Running standalone LLVM bytecode:'
    cmd = "./%s" % name
    print cmd
    os.system(cmd)

def run(ep, name="go"):
    global entry_point
    entry_point = ep
    
    run_all = True
    if len(sys.argv) > 1:
        if sys.argv[1] == "p":
            c()
            run_all = False
        elif sys.argv[1] == "c":
            c()
            run_all = False
        elif sys.argv[1] == "l":
            l(name)
            run_all = False
            
    if run_all:
        l(name)
        c()
        p()
