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
    """Special-case for 'raise' statements.  Case-by-case analysis:

    * raise Class
       - with a constant Class, it is easy to recognize.
         But we don't normalize: the associated value is None.

    * raise Class(...)
       - when the class is instantiated in-place, we can figure that out

    * raise Instance
       - assumes that it's not a class, and raises an exception whose class
         is variable and whose value is Instance.

    * raise Class, Arg
       - assumes that Arg is the value you want for the exception, and
         that Class is exactly the exception class.  No check or normalization.
    """
    assert len(args.args_w) == 3 and args.kwds_w == {}
    w_arg1, w_arg2, w_tb = args.args_w

    # w_arg3 (the traceback) is ignored and replaced with None
    # if it is a Variable, because pyopcode.py tries to unwrap it.
    # It means that we ignore the 'tb' argument of 'raise' in most cases.
    if not isinstance(w_tb, Constant):
        w_tb = space.w_None

    if w_arg2 != space.w_None:
        # raise Class, Arg: no normalization
        return (w_arg1, w_arg2, w_tb)

    etype = getconstclass(space, w_arg1)
    if etype is not None:
        # raise Class
        return (w_arg1, space.w_None, w_tb)

    # raise Class(..)?  We need a hack to figure out of which class it is.
    # Normally, Instance should have been created by the previous operation
    # which should be a simple_call(<Class>, ...).
    # Fetch the <Class> out of there.  (This doesn't work while replaying)
    if space.executioncontext.crnt_ops:
        spaceop = space.executioncontext.crnt_ops[-1]
        if (spaceop.opname == 'simple_call' and
            spaceop.result is w_arg1):
            w_type = spaceop.args[0]
            return (w_type, w_arg1, w_tb)

    # raise Instance.  Fall-back.
    w_type = space.do_operation('type', w_arg1)
    return (w_type, w_arg1, w_tb)
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
