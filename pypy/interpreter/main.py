from pypy.objspace.std import StdObjSpace
from pypy.objspace.trivial import TrivialObjSpace
from pypy.interpreter import executioncontext, baseobjspace
from pypy.interpreter import pyframe

import sys

def run_string(source, fname):
    try:
        space = StdObjSpace()
        code = compile(source, fname, 'exec')
        ec = executioncontext.ExecutionContext(space)

        w_globals = ec.make_standard_w_globals()

        space.setitem(w_globals,
                      space.wrap("__name__"),
                      space.wrap("__main__"))
        
        frame = pyframe.PyFrame(space, code, w_globals, w_globals)
    except baseobjspace.OperationError, operationerr:
        raise PyPyError(operationerr)
    else:
        ec.eval_frame(frame)

def run_file(fname):
    ifile = open(fname)
    run_string(ifile.read(), fname)

def main(argv=None):
    if argv is None:
        argv = sys.argv

    try:
        run_file(argv[1])
    except baseobjspace.OperationError, operationerr:
        # XXX insert exception info into the application-level sys.last_xxx
        operationerr.print_detailed_traceback(space)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
    
