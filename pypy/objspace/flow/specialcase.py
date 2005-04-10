import types, operator
from pypy.interpreter import pyframe, baseobjspace
from pypy.interpreter.error import OperationError
from pypy.objspace.flow.objspace import UnwrapException
from pypy.objspace.flow.model import Constant
from pypy.objspace.flow.operation import OperationName, Arity


def sc_import(space, fn, args):
    w_name, w_glob, w_loc, w_frm = args.fixedunpack(4)
    return space.wrap(__import__(space.unwrap(w_name),
                                 space.unwrap(w_glob),
                                 space.unwrap(w_loc),
                                 space.unwrap(w_frm)))

def sc_operator(space, fn, args):
    args_w, kwds_w = args.unpack()
    assert kwds_w == {}, "should not call %r with keyword arguments" % (fn,)
    opname = OperationName[fn]
    if len(args_w) != Arity[opname]:
        if opname == 'pow' and len(args_w) == 2:
            args_w = args_w + [Constant(None)]
        elif opname == 'getattr' and len(args_w) == 3:
            return space.do_operation('simple_call', Constant(getattr), *args_w)
        else:
            raise Exception, "should call %r with exactly %d arguments" % (
                fn, Arity[opname])
    if space.builtins_can_raise_exceptions:
        # in this mode, avoid constant folding and raise an implicit Exception
        w_result = space.do_operation(opname, *args_w)
        space.handle_implicit_exceptions([Exception])
        return w_result
    else:
        # in normal mode, completely replace the call with the underlying
        # operation and its limited implicit exceptions semantic
        return getattr(space, opname)(*args_w)


def setup(space):
    # fn = pyframe.normalize_exception.get_function(space)
    # this is now routed through the objspace, directly.
    # space.specialcases[fn] = sc_normalize_exception
    if space.do_imports_immediately:
        space.specialcases[__import__] = sc_import
    # turn calls to built-in functions to the corresponding operation,
    # if possible
    for fn in OperationName:
        space.specialcases[fn] = sc_operator
