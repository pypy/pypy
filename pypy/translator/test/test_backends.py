'''
Test conditions that all backends should do correct.
'''

import autopath, os, sys, py
from pypy.translator.translator import Translator
from pypy.rpython.rtyper import *
from pypy.rpython.rarithmetic import *
from pypy.translator.test.snippet import *


backends = 'source c cl llvm pyrex'.split()
functions = 'forty_two'.split() #XXX add more functions here when RPythonTyper can handle them

regenerate_code = '''def test_regenerate_%(function)s_%(backend)s():
    t = Translator(%(function)s)
    t.simplify()
    a = t.annotate([])
    a.simplify()
    typer = RPythonTyper(t.annotator)
    typer.specialize()
    first  = t.%(backend)s()
    second = t.%(backend)s()
    if first != second:
        print '<FIRST>\\n'  + first  + '\\n</FIRST>\\n'
        print '<SECOND>\\n' + second + '\\n</SECOND>\\n'
        #t.view()
    assert first == second'''

for backend in backends:
    for function in functions:
        exec regenerate_code % vars()
