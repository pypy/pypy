import types, operator
from pypy.interpreter import pyframe, baseobjspace
from pypy.interpreter.error import OperationError
from pypy.objspace.flow.objspace import UnwrapException
from pypy.objspace.flow.model import Constant


def getconstclass(space, w_cls):
    try:
        ecls = space.unwrap(w_cls)
    except UnwrapException:
        pass
    else:
        if isinstance(ecls, (type, types.ClassType)):
            return ecls
    return None


def sc_normalize_exception(space, fn, args):
    """Special-case for 'raise' statements.

    Only accept the following syntaxes:
    * raise Class
    * raise Class, Arg
    * raise Class(...)
    """
    assert len(args.args_w) == 2 and args.kwds_w == {}
    w_arg1, w_arg2 = args.args_w
    etype = getconstclass(space, w_arg1)
    if etype is not None:
        # raise Class or raise Class, Arg: no normalization
        return (w_arg1, w_arg2)
    else:
        # raise Instance: we need a hack to figure out of which class it is.
        # Normally, Instance should have been created by the previous operation
        # which should be a simple_call(<Class>, ...).
        # Fetch the <Class> out of there.  (This doesn't work while replaying)
        spaceop = space.executioncontext.crnt_ops[-1]
        assert spaceop.opname == 'simple_call'
        assert spaceop.result is w_arg1
        w_type = spaceop.args[0]
        return (w_type, w_arg2)
    # this function returns a real tuple that can be handled
    # by FlowObjSpace.unpacktuple()

def sc_import(space, fn, args):
    assert len(args.args_w) == 4 and args.kwds_w == {}
    unwrapped_args = []
    for w_arg in args.args_w:
        assert isinstance(w_arg, Constant)
        unwrapped_args.append(space.unwrap(w_arg))
    return space.wrap(__import__(*unwrapped_args))

def sc_operator(space, fn, args):
    # XXX do this more cleanly
    assert args.kwds_w == {}
    opname = fn.__name__.replace('__', '')
    return space.do_operation(opname, *args.args_w)

def setup(space):
    fn = pyframe.normalize_exception.get_function(space)
    space.specialcases[fn] = sc_normalize_exception
    space.specialcases[__import__] = sc_import
    for opname in ['lt', 'le', 'eq', 'ne', 'gt', 'ge', 'is_']:
        space.specialcases[getattr(operator, opname)] = sc_operator
