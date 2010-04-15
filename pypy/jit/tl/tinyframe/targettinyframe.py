
from pypy.jit.tl.tinyframe import main

def entry_point(argv):
    main(argv[0], argv[1:])
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None
