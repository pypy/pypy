import autopath
from pypy.interpreter import executioncontext, module
from pypy.interpreter.error import OperationError
import sys

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
        w_code = compile(source, filename, cmd, 0, 0)

        w_main = space.wrap('__main__')
        mainmodule = module.Module(space, w_main)
        space.setitem(space.sys.w_modules, w_main, mainmodule)

        w_globals = mainmodule.w_dict

        pycode = space.interpclass_w(w_code)
        retval = pycode.exec_code(space, w_globals, w_globals)
        if eval:
            return retval
        else:
            return

    except OperationError, operationerr:
        operationerr.record_interpreter_traceback()
        raise

def run_string(source, filename='<string>', space=None):
    _run_eval_string(source, filename, space, False)

def eval_string(source, filename='<string>', space=None):
    return _run_eval_string(source, filename, space, True)

def run_file(filename, space=None):
    if __name__=='__main__':
        print "Running %r with %r" % (filename, space)
    istring = open(filename).read()
    run_string(istring, filename, space)
