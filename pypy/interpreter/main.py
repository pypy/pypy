from pypy.objspace.std import StdObjSpace
from pypy.objspace.trivial import TrivialObjSpace
from pypy.interpreter import executioncontext, baseobjspace
from pypy.interpreter import pyframe

import sys

def main(argv=None):
    if argv is None:
        argv = sys.argv

    fname = argv[1]

    space = StdObjSpace()
    ifile = open(fname)
    code = compile(ifile.read(), fname, 'exec')
    ec = executioncontext.ExecutionContext(space)

    w_globals = ec.make_standard_w_globals()
    frame = pyframe.PyFrame(space, code, w_globals, w_globals)
    try:
        ec.eval_frame(frame)
    except baseobjspace.OperationError, operationerr:
        # XXX insert exception info into the application-level sys.last_xxx
        operationerr.print_detailed_traceback(space)
    
if __name__ == '__main__':
    sys.exit(main(sys.argv))
    
