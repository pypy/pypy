from pypy.objspace.std import StdObjSpace
from pypy.objspace.trivial import TrivialObjSpace
import executioncontext, baseobjspace, pyframe

import sys

def run_string(source, fname):
    try:
        space = StdObjSpace()
        code = compile(source, fname, 'exec')
        ec = executioncontext.ExecutionContext(space)

        w_mainmodule = space.newmodule(space.wrap("__main__"))
        w_globals = space.getattr(w_mainmodule, space.wrap("__dict__"))
        space.setitem(w_globals, space.wrap("__builtins__"),
                      ec.get_w_builtins())
        
        frame = pyframe.PyFrame(space, code, w_globals, w_globals)
    except baseobjspace.OperationError, operationerr:
        raise baseobjspace.PyPyError(space, operationerr)
    else:
        try:
            ec.eval_frame(frame)
        except baseobjspace.OperationError, operationerr:
            operationerr.space = space
            raise

def run_file(fname):
    ifile = open(fname)
    run_string(ifile.read(), fname)

def main(argv=None):
    if argv is None:
        argv = sys.argv

    try:
        run_file(argv[1])
    except baseobjspace.PyPyError, pypyerr:
        pypyerr.operationerr.print_detailed_traceback(pypyerr.space)
    except baseobjspace.OperationError, operationerr:
        operationerr.print_detailed_traceback(operationerr.space)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
    
