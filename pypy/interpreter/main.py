import autopath
from pypy.tool import option
from pypy.interpreter import executioncontext, baseobjspace, gateway, module
from pypy.interpreter.error import OperationError, PyPyError
import sys, os

def _run_eval_string(source, filename, space, eval):
    if eval:
        cmd = 'eval'
    else:
        cmd = 'exec'
        
    try:
        if space is None:
            from pypy.objspace.std import StdObjSpace
            space = StdObjSpace()

        compile = space.builtin.compile
        w = space.wrap
        w_code = compile(w(source), w(filename), w(cmd),
                         w(0), w(0))

        ec = executioncontext.ExecutionContext(space)

        mainmodule = module.Module(space, space.wrap("__main__"))
        w_globals = mainmodule.w_dict
       
    except OperationError, operationerr:
        operationerr.record_interpreter_traceback()
        raise PyPyError(space, operationerr)
    else:
        pycode = space.unwrap(w_code)
        retval = pycode.exec_code(space, w_globals, w_globals)
        if eval:
            return retval
        else:
            return
    
def run_string(source, filename='<string>', space=None):
    _run_eval_string(source, filename, space, False)

def eval_string(source, filename='<string>', space=None):
    return _run_eval_string(source, filename, space, True)

def run_file(filename, space=None):
    if __name__=='__main__':
        print "Running %r with %r" % (filename, space)
    istring = open(filename).read()
    run_string(istring, filename, space)

def main(argv=None):
    if argv is None:
        argv = sys.argv

    argv = option.process_options(option.get_standard_options(),
                                  option.Options)
    space = option.objspace()
    try:
        run_file(argv[0], space)
    except PyPyError, pypyerr:
        pypyerr.operationerr.print_detailed_traceback(pypyerr.space)

if __name__ == '__main__':
    main(sys.argv)
    
