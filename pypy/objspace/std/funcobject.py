from pypy.objspace.std.objspace import *
import pypy.interpreter.pyframe


class W_FuncObject(object):
    def __init__(w_self, w_code, w_globals, w_defaultarguments, w_closure):
        w_self.w_code = w_code
        w_self.w_globals = w_globals
        w_self.w_defaultarguments = w_defaultarguments
        w_self.w_closure = w_closure


def func_call(space, w_function, w_arguments, w_keywords):
    ec = space.getexecutioncontext()
    bytecode = space.unwrap(w_function.w_code)
    w_locals = space.newdict([])
    frame = pypy.interpreter.pyframe.PyFrame(space, bytecode,
                                             w_function.w_globals, w_locals)
    import sys; print >> sys.stderr, '((((((((((((((((('
    frame.setargs(w_arguments, w_keywords,
                  w_defaults = w_function.w_defaultarguments,
                  w_closure = w_function.w_closure)
    import sys; print >> sys.stderr, ')))))))))))))))))'
    w_result = ec.eval_frame(frame)
    return w_result

StdObjSpace.call.register(func_call, W_FuncObject, W_ANY, W_ANY)
