"""
A simple standalone target for the scheme interpreter.
"""

import autopath
import sys
from pypy.rlib.streamio import open_file_as_stream
from pypy.lang.scheme.ssparser import parse
from pypy.lang.scheme.object import SchemeQuit
from pypy.lang.scheme.execution import ExecutionContext

# __________  Entry point  __________


def entry_point(argv):
    if len(argv) == 2:
        f = open_file_as_stream(argv[1])
        t = parse(f.readall())
        ctx = ExecutionContext()
        try:
            for sexpr in t:
                w_retval = sexpr.eval(ctx)
                print w_retval.to_string()
        except SchemeQuit, e:
            return 0

        return 0
    else:
        print "Usage: %s schemesourcefile" % argv[0]
        return 1

# _____ Define and setup target ___

def target(driver, args):
    driver.exe_name = 'ss-%(backend)s'
    return entry_point, None

if __name__ == '__main__':
    entry_point(sys.argv)

