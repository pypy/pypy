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

        w_mainmodule = space.newmodule(space.wrap("__main__"))
        w_globals = space.getattr(w_mainmodule, space.wrap("__dict__"))
        space.setitem(w_globals, space.wrap("__builtins__"),
                      ec.get_w_builtins())
        
        frame = pyframe.PyFrame(space, code, w_globals, w_globals)
    except baseobjspace.OperationError, operationerr:
        raise baseobjspace.PyPyError(space, operationerr)
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
    except baseobjspace.PyPyError, pypyerr:
        # XXX insert exception info into the application-level sys.last_xxx
        pypyerr.operationerr.print_detailed_traceback(pypyerr.space)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
    
