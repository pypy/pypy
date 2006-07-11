"""
A simple standalone target.

The target below specifies None as the argument types list.
This is a case treated specially in driver.py . If the list
of input types is empty, it is meant to be a list of strings,
actually implementing argv of the executable.
"""

import os, sys

def debug(msg): 
    os.write(2, "debug: " + msg + '\n')

# __________  Entry point  __________

def sum(seq):
    total = 0
    for i in range(len(seq)):
        total += seq[i]
    return total

def entry_point(argv):
    result = sum([1, 2, 3, 4])
    result += sum([5, 6, 7, 8])
    debug(str(result))
    return 0


# _____ Define and setup target ___

def target(*args):
    return entry_point, None

if __name__ == '__main__':
    from pypy.translator.interactive import Translation

    t = Translation(entry_point)
    t.view()
    t.annotate([str])
    t.view()
    t.rtype(backend="c")
    t.view()
    t.backendopt()
    t.view()
    f = t.compile_c()
    f("")

