import py
import os
import sys

from pypy.annotation.model import SomeList, SomeString
from pypy.annotation.listdef import ListDef

from pypy.translator.translator import TranslationContext
from pypy.translator.c.genc import CStandaloneBuilder
from pypy.translator.c.gc import BoehmGcPolicy
    
from pypy.translator.llvm.genllvm import genllvm_compile

def p():
    print 'Running on top of CPython:'
    entry_point([])

def c(name):
    s_list_of_strings = SomeList(ListDef(None, SomeString()))
    s_list_of_strings.listdef.resize()
    t = TranslationContext()
    t.buildannotator().build_types(entry_point, [s_list_of_strings])
    t.buildrtyper().specialize()
    from pypy.translator.backendopt.all import backend_optimizations
    backend_optimizations(t)
    cbuilder = CStandaloneBuilder(t, entry_point, gcpolicy=BoehmGcPolicy)
    cbuilder.generate_source()
    cbuilder.compile()
    os.system("XXX")
    
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
        elif sys.argv[1] == "c":
            c(name)
            run_all = False
            
    if run_all:
        l(name)
        c(name)
        p()
