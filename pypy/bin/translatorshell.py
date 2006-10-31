#!/usr/bin/env python 


"""PyPy Translator Frontend

Glue script putting together the various pieces of the translator.
Can be used for interactive testing of the translator.

Example:

    t = Translation(func)
    t.view()                           # control flow graph

    t.annotate([int])                  # pass the list of args types
    t.view()                           # graph + annotations under the mouse

    t.rtype()                          # use low level operations 
    f = t.compile_c()                  # C compilation
    assert f(arg) == func(arg)         # sanity check (for C)
    

Some functions are provided for the benefit of interactive testing.
Try dir(snippet) for list of current snippets.
"""

import autopath, os, sys
from pypy.translator.interactive import Translation
from pypy.rpython.rtyper import *
from pypy.rlib.rarithmetic import *

import py

def setup_readline():
    import readline
    try:
        import rlcompleter2
        rlcompleter2.setup()
    except ImportError:
        import rlcompleter
        readline.parse_and_bind("tab: complete")
    import os
    histfile = os.path.join(os.environ["HOME"], ".pypytrhist")
    try:
        getattr(readline, "clear_history", lambda : None)()
        readline.read_history_file(histfile)
    except IOError:
        pass
    import atexit
    atexit.register(readline.write_history_file, histfile)

if __name__ == '__main__':
    try:
        setup_readline()
    except ImportError, err:
        print "Disabling readline support (%s)" % err
    from pypy.translator.test import snippet
    from pypy.rpython.rtyper import RPythonTyper

    if (os.getcwd() not in sys.path and
        os.path.curdir not in sys.path):
        sys.path.insert(0, os.getcwd())

    print __doc__

    import os
    os.putenv("PYTHONINSPECT", "1")


