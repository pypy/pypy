import py
import os
import sys

from pypy.translator.llvm2.genllvm import compile_module
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
    compile_module(entry_point, [], standalone=True, exe_name=name)
    print 'Running standalone (llvm-based) executable:'
    cmd = "/tmp/usession-current/%s" % name
    print cmd
    os.system(cmd)

def run(ep, name="go"):
    global entry_point
    entry_point = ep
    
    run_all = True
    if len(sys.argv) > 1:
        if sys.argv[1] == "p":
            p()
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
