from pypy.objspace.std import StdObjSpace
from pypy.module.builtin import Builtin
from pypy.interpreter import executioncontext, baseobjspace, pyframe
import sys

def run_string(source, fname):
    try:
        space = StdObjSpace()

        compile = space.builtin.compile
        w=space.wrap
        w_code = compile(w(source), w(fname), w('exec'),
                         w(0), w(0))

        ec = executioncontext.ExecutionContext(space)

        w_mainmodule = space.newmodule(space.wrap("__main__"))
        w_globals = space.getattr(w_mainmodule, space.wrap("__dict__"))
        space.setitem(w_globals, space.wrap("__builtins__"), space.w_builtins)
        
        frame = pyframe.PyFrame(space, space.unwrap(w_code),
                                w_globals, w_globals)
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
    
