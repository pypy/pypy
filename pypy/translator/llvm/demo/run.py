import py
import os
import sys

from pypy.annotation.model import SomeList, SomeString
from pypy.annotation.listdef import ListDef

from pypy.translator.llvm.genllvm import genllvm_compile

def p():
    print 'Running on top of CPython:'
    entry_point([])

def l(name):
    s_list_of_strings = SomeList(ListDef(None, SomeString()))
    s_list_of_strings.listdef.resize()
    exe_path = genllvm_compile(entry_point, [s_list_of_strings],
                               exe_name=name, standalone=True)
    print 'Running standalone (llvm-based) executable:'
    print exe_path
    os.system(exe_path)

def run(ep, name="go"):
    global entry_point
    entry_point = ep
    
    run_all = True
    if len(sys.argv) > 1:
        if sys.argv[1] == "p":
            p()
            run_all = False
        elif sys.argv[1] == "l":
            l(name)
            run_all = False
            
    if run_all:
        l(name)
        p()
