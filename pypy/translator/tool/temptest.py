import sys

import autopath

from pypy.translator.translator import *
from pypy.translator.test import snippet as test

from pypy.translator.tool import tracer
tracer.trace(AnnotationSet)
tracer.trace(RPythonAnnotator)

def h(lst):
    lst += [5]

def calling_h():
    a = []
    h(a)
    return a


t = Translator(calling_h)  #  test.poor_man_rev_range)
t.simplify()
a = t.annotate([])
lines = []
for key, value in a.bindings.items():
    lines.append('%r: %r' % (key, value))
lines.sort()
for line in lines:
    print line
print '-'*50
print a.heap
sys.stdout.flush()

print '-'*50
print t.pyrex()

t.gv()
