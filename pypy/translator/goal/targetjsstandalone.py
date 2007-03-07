"""
A simple standalone target for the javascript interpreter.
"""

import sys
from pypy.rlib.streamio import open_file_as_stream
from pypy.lang.js.interpreter import *
from pypy.lang.js.jsobj import ExecutionReturned

# __________  Entry point  __________

interp = Interpreter()

def entry_point(argv):
    if len(argv) == 2:
        f = open_file_as_stream(argv[1])
        interp.run(load_source(f.readall()))
        return 0
    elif argv[0] == 'foo':
        raise ExecutionReturned(None)
    else:
        print "Usage: %s jsourcefile" % argv[0]
        return 1

# _____ Define and setup target ___

def target(driver, args):
    driver.exe_name = 'js-%(backend)s'
    return entry_point, None

if __name__ == '__main__':
    entry_point(sys.argv)
