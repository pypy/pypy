import types, operator
from pypy.interpreter import pyframe, baseobjspace
from pypy.interpreter.error import OperationError
from pypy.objspace.flow.objspace import UnwrapException
from pypy.objspace.flow.model import Constant


def sc_import(space, fn, args):
    w_name, w_glob, w_loc, w_frm = args.fixedunpack(4)
    return space.wrap(__import__(space.unwrap(w_name),
                                 space.unwrap(w_glob),
                                 space.unwrap(w_loc),
                                 space.unwrap(w_frm)))

def sc_operator(space, fn, args):
    # XXX do this more cleanly
    args_w, kwds_w = args.unpack()
    assert kwds_w == {}
    opname = fn.__name__.replace('__', '')
    return space.do_operation(opname, *args_w)


def setup(space):
    # fn = pyframe.normalize_exception.get_function(space)
    # this is now routed through the objspace, directly.
    # space.specialcases[fn] = sc_normalize_exception
    if space.do_imports_immediately:
        space.specialcases[__import__] = sc_import
    for opname in ['lt', 'le', 'eq', 'ne', 'gt', 'ge', 'is_']:
        space.specialcases[getattr(operator, opname)] = sc_operator
