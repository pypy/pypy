"""
A simple standalone target for the scheme interpreter.
"""

import autopath
import sys
from pypy.rlib.streamio import open_file_as_stream
from pypy.lang.scheme.ssparser import parse
from pypy.rlib.parsing.makepackrat import BacktrackException
from pypy.lang.scheme.object import SchemeQuit, ContinuationReturn
from pypy.lang.scheme.execution import ExecutionContext

# __________  Entry point  __________


def entry_point(argv):
    if len(argv) == 2:
        code = open_file_as_stream(argv[1]).readall()
        try:
            t = parse(code)
        except BacktrackException:
            #(line, col) = e.error.get_line_column(code)
            #expected = " ".join(e.error.expected)
            print "parse error"
            return 1

        #this should not be necessary here
        assert isinstance(t, list)
        ctx = ExecutionContext()
        try:
            for sexpr in t:
                try:
                    w_retval = sexpr.eval(ctx)
                    print w_retval.to_string()
                except ContinuationReturn, e:
                    print e.result.to_string()

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

