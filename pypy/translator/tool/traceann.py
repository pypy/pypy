"""

- annotate and translate snippet producing tracing of calls
to AnnotationSet and RPythonAnnotator
- print bindings and final annotation set
and pyrex 

- display flow graph

call it like:

traceann <snippet-name> <types...>  >result.txt 2>trace.txt

"""

import sys

import autopath

from pypy.translator.translator import *
from pypy.translator.test import snippet as test

from pypy.translator.tool import tracer
tracer.trace(AnnotationSet)
tracer.trace(RPythonAnnotator)

try:
    snippet_name = sys.argv[1]
except IndexError:
    snippet_name = "call_five"

argtypes = []

for argtype in sys.argv[2:]:
    argtypes.append(eval(argtype))

t = Translator(getattr(test,snippet_name))
t.simplify()
a = t.annotate(argtypes)
lines = []
for key, value in a.bindings.items():
    lines.append('%r: %r' % (key, value))
for cl, attrdict in a.classes.items():
    lines.append('%s: %r' % (cl.__name__,attrdict))
lines.sort()
for line in lines:
    print line
print '-'*50
print a.heap
sys.stdout.flush()

print '-'*50
print t.pyrex()

t.gv()
