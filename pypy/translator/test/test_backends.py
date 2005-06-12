'''
Test conditions that all backends should do correct.
'''

import autopath, os, sys, py
from pypy.translator.translator import Translator
from pypy.rpython.rtyper import *
from pypy.rpython.rarithmetic import *
from pypy.translator.test.snippet import *


py.test.skip("the Translator and back-ends depend on too many conditions "
             "to test the back-ends generically")
# e.g. some back-ends require annotation and/or specialization to be done
#      while some require it *not* to be done.  GenCL for example has no
#      chance to understand a specialized graph.  (That's why the test still
#      used to pass: forty_two is basically an empty function, so
#      specializing it makes no difference.  Now the RTyper produces a few
#      helper functions in all cases.)


backends = 'source c cl llvm pyrex'.split()
deterministic_backends = 'source cl llvm pyrex'.split()
functions = 'forty_two'.split() #XXX add more functions here when RPythonTyper can handle them

regenerate_code = '''def test_regenerate_%(function)s_%(backend)s():
    t = Translator(%(function)s)
    t.simplify()
    a = t.annotate([])
    a.simplify()
    t.specialize()
    first  = t.%(backend)s()
    second = t.%(backend)s()
    if %(backend)r in deterministic_backends:
        if first != second:
            print '<FIRST>\\n'  + first  + '\\n</FIRST>\\n'
            print '<SECOND>\\n' + second + '\\n</SECOND>\\n'
            #t.view()
        assert first == second'''

for backend in backends:
    for function in functions:
        exec regenerate_code % vars()
